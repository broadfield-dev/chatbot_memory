import logging
from typing import Dict, List, Any, Optional
import mysql.connector
from datetime import datetime

logger = logging.getLogger(__name__)

class MySQLBackend:
    def __init__(self, host: str, user: str, password: str, database: str):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        try:
            from memory_analyze import analyze_data
            self.HAS_ANALYZE = True
            self.analyze_data = analyze_data
            logger.info('memory_analyze successfully imported')
        except ImportError:
            self.HAS_ANALYZE = False
            self.analyze_data = None
            logger.warning('memory_analyze not installed; using default truthfulness=0.5, importance=0.5')

    def initialize(self):
        conn = mysql.connector.connect(
            host=self.host, user=self.user, password=self.password, database=self.database
        )
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS long_term (
                id INT AUTO_INCREMENT PRIMARY KEY,
                text TEXT,
                truthfulness FLOAT DEFAULT 0.5,
                importance FLOAT DEFAULT 0.5,
                sentiment ENUM('positive', 'negative', 'neutral') DEFAULT 'neutral',
                source VARCHAR(50),
                parent INT,
                timestamp VARCHAR(255),
                last_accessed VARCHAR(255),
                UNIQUE KEY text_unique (text(255)),
                FOREIGN KEY (parent) REFERENCES long_term(id) ON DELETE SET NULL
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()

    def add(self, text: str, metadata: Dict[str, Any]) -> int:
        conn = mysql.connector.connect(
            host=self.host, user=self.user, password=self.password, database=self.database
        )
        cursor = conn.cursor()
        timestamp = metadata.get('timestamp', datetime.now().isoformat())
        last_accessed = metadata.get('last_accessed', timestamp)
        
        truthfulness = metadata.get('truthfulness', 0.5)
        importance = metadata.get('importance', 0.5)
        sentiment = metadata.get('sentiment', 'neutral')
        source = metadata.get('type', 'unknown')
        parent = metadata.get('parent', None)

        cursor.execute("""
            INSERT INTO long_term (text, truthfulness, importance, sentiment, source, parent, timestamp, last_accessed)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                truthfulness = VALUES(truthfulness),
                importance = VALUES(importance),
                sentiment = VALUES(sentiment),
                source = VALUES(source),
                parent = VALUES(parent),
                last_accessed = %s
        """, (text, truthfulness, importance, sentiment, source, parent, timestamp, last_accessed, last_accessed))
        
        cursor.execute("SELECT LAST_INSERT_ID()")
        id_ = cursor.fetchone()[0] or cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        return id_

    def update(self, id_: int, metadata: Dict[str, Any]):
        conn = mysql.connector.connect(
            host=self.host, user=self.user, password=self.password, database=self.database
        )
        cursor = conn.cursor()
        updates = []
        params = []
        for key, value in metadata.items():
            if key in ['truthfulness', 'importance', 'sentiment', 'source', 'parent', 'last_accessed']:
                updates.append(f"{key} = %s")
                params.append(value)
        if updates:
            params.append(id_)
            cursor.execute(f"UPDATE long_term SET {', '.join(updates)} WHERE id = %s", params)
            conn.commit()
        cursor.close()
        conn.close()

    def query(self, query_text: str, top_k: int = 5) -> List[tuple]:
        conn = mysql.connector.connect(
            host=self.host, user=self.user, password=self.password, database=self.database
        )
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, text, truthfulness, importance, sentiment, source, parent, timestamp, last_accessed
            FROM long_term
            WHERE text LIKE %s
            ORDER BY importance DESC, last_accessed DESC
            LIMIT %s
        """, (f"%{query_text}%", top_k))
        results = [(id_, {'text': text, 'truthfulness': truthfulness, 'importance': importance,
                          'sentiment': sentiment, 'source': source, 'parent': parent,
                          'timestamp': timestamp, 'last_accessed': last_accessed})
                   for id_, text, truthfulness, importance, sentiment, source, parent, timestamp, last_accessed in cursor.fetchall()]
        cursor.close()
        conn.close()
        return results

class MemoryManager:
    def __init__(self, long_term_backend: MySQLBackend, max_short_term_size: int = 50, analyze_kwargs: Dict[str, Any] = None):
        self.long_term_backend = long_term_backend
        self.short_term = {'documents': [], 'metadatas': []}
        self.max_short_term_size = max_short_term_size
        self.analyze_kwargs = analyze_kwargs or {}

    def process_content(self, source: str, content: str, query: str, parent_id: Optional[int] = None):
        # Analyze content for initial values if package is available
        if self.long_term_backend.HAS_ANALYZE:
            analysis = self.long_term_backend.analyze_data(source, content, query, **self.analyze_kwargs)
            if not analysis or 'text' not in analysis[0]:
                logger.error(f"Analysis failed for content: {content}")
                analysis = [{'text': content, 'truthfulness': 0.5, 'importance': 0.5, 'sentiment': 'neutral'}]
        else:
            analysis = [{'text': content, 'truthfulness': 0.5, 'importance': 0.5, 'sentiment': 'neutral'}]
        
        fact = analysis[0]
        metadata = {
            'truthfulness': fact.get('truthfulness', 0.5),
            'importance': fact.get('importance', 0.5),
            'sentiment': fact.get('sentiment', 'neutral'),
            'source': source,
            'parent': parent_id,
            'timestamp': datetime.now().isoformat(),
            'last_accessed': datetime.now().isoformat()
        }

        # Add to short-term memory
        if content not in self.short_term['documents']:
            self.short_term['documents'].append(content)
            self.short_term['metadatas'].append(metadata)
            if len(self.short_term['documents']) > self.max_short_term_size:
                oldest_doc = self.short_term['documents'].pop(0)
                oldest_meta = self.short_term['metadatas'].pop(0)
                self.long_term_backend.add(oldest_doc, oldest_meta)

        # Update long-term if exists
        existing = self.long_term_backend.query(content, top_k=1)
        if existing:
            id_, existing_meta = existing[0]
            # Reassess values if analysis is available
            if self.long_term_backend.HAS_ANALYZE:
                new_analysis = self.long_term_backend.analyze_data(source, content, query, **self.analyze_kwargs)
                if new_analysis and 'text' in new_analysis[0]:
                    new_fact = new_analysis[0]
                    updated_meta = {
                        'truthfulness': new_fact.get('truthfulness', existing_meta['truthfulness']),
                        'importance': new_fact.get('importance', existing_meta['importance']),
                        'sentiment': new_fact.get('sentiment', existing_meta['sentiment']),
                        'source': source,
                        'last_accessed': datetime.now().isoformat()
                    }
                    self.long_term_backend.update(id_, updated_meta)
            else:
                updated_meta = {
                    'source': source,
                    'last_accessed': datetime.now().isoformat()
                }
                self.long_term_backend.update(id_, updated_meta)

    def get_short_term(self) -> Dict[str, List]:
        return self.short_term

    def get_long_term(self, query_text: str, top_k: int = 5) -> List[tuple]:
        results = self.long_term_backend.query(query_text, top_k)
        # Update last_accessed and reassess values on access if analysis is available
        for id_, metadata in results:
            if self.long_term_backend.HAS_ANALYZE:
                new_analysis = self.long_term_backend.analyze_data(metadata['source'], metadata['text'], query_text, **self.analyze_kwargs)
                if new_analysis and 'text' in new_analysis[0]:
                    new_fact = new_analysis[0]
                    updated_meta = {
                        'truthfulness': new_fact.get('truthfulness', metadata['truthfulness']),
                        'importance': new_fact.get('importance', metadata['importance']),
                        'sentiment': new_fact.get('sentiment', metadata['sentiment']),
                        'last_accessed': datetime.now().isoformat()
                    }
                    self.long_term_backend.update(id_, updated_meta)
            else:
                updated_meta = {'last_accessed': datetime.now().isoformat()}
                self.long_term_backend.update(id_, updated_meta)
        return self.long_term_backend.query(query_text, top_k)
