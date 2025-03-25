import chromadb
from chromadb.utils import embedding_functions
from datetime import datetime
import logging

# Check if memory_analyze is available
try:
    from memory_analyze import analyze_data
    HAS_ANALYZE = True
except ImportError:
    HAS_ANALYZE = False

class MemoryManager:
    def __init__(self, long_term_backend, max_short_term_size=50, analyze_kwargs=None):
        self.logger = logging.getLogger(__name__)
        self.max_short_term_size = max_short_term_size
        self.analyze_kwargs = analyze_kwargs or {}  # Optional kwargs for memory_analyze

        # Short-term memory setup (ChromaDB)
        self.chroma_client = chromadb.Client()
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name='all-MiniLM-L6-v2')
        self.short_term_collection = self.chroma_client.get_or_create_collection(
            'short_term', embedding_function=self.embedding_fn
        )
        
        # Long-term memory backend
        self.long_term_backend = long_term_backend
        self.long_term_backend.initialize()

    def process_content(self, source, content, query='', default_truthfulness=0.5, default_importance=0.5):
        '''Add content to short-term memory, optionally analyzing it if memory_analyze is installed.'''
        timestamp = datetime.now().isoformat()
        
        if HAS_ANALYZE:
            self.logger.debug('Using memory_analyze for content analysis')
            facts = analyze_data(source, content, query, **self.analyze_kwargs)
        else:
            self.logger.debug('memory_analyze not installed, using defaults')
            facts = [{'text': content, 'truthfulness': default_truthfulness, 'importance': default_importance}]

        for fact in facts:
            self.short_term_collection.add(
                ids=[f'{source}_{timestamp}'],
                documents=[fact['text']],
                metadatas={
                    'type': source,
                    'timestamp': timestamp,
                    'truthfulness': fact['truthfulness'],
                    'importance': fact['importance']
                }
            )
            self.consolidate_memory(fact['text'], fact['truthfulness'], fact['importance'])
        
        # Trim short-term memory if needed
        if self.short_term_collection.count() > self.max_short_term_size:
            oldest = self.short_term_collection.get(limit=1, include=['metadatas'])['metadatas'][0]['timestamp']
            self.short_term_collection.delete(ids=[f'doc_{oldest}'])

    def consolidate_memory(self, text, truthfulness, importance):
        '''Move or update memory from short-term to long-term.'''
        timestamp = datetime.now().isoformat()
        results = self.short_term_collection.query(query_texts=[text], n_results=1)
        
        if results['distances'] and results['distances'][0] and results['distances'][0][0] < 0.2:
            # Update existing long-term memory
            existing_data = self.long_term_backend.query(text)
            if existing_data:
                existing_id, existing_meta = existing_data[0]
                new_truth = min(1.0, (existing_meta['truthfulness'] + truthfulness) / 2 + 0.1)
                new_importance = min(1.0, existing_meta['importance'] + 0.05)
                self.long_term_backend.update(
                    existing_id,
                    {'truthfulness': new_truth, 'importance': new_importance, 'timestamp': timestamp, 'last_accessed': timestamp}
                )
                return True
        # Add new entry to long-term memory
        self.long_term_backend.add(
            text,
            {'truthfulness': truthfulness, 'importance': importance, 'timestamp': timestamp, 'last_accessed': timestamp}
        )
        return True

    def get_short_term(self):
        '''Retrieve all short-term memory entries.'''
        return self.short_term_collection.get(include=['documents', 'metadatas'])

    def get_long_term(self, query_text=None):
        '''Retrieve long-term memory entries, optionally filtered by query.'''
        return self.long_term_backend.query(query_text)
