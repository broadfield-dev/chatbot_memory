from abc import ABC, abstractmethod
from datasets import Dataset, load_dataset
from huggingface_hub import login
import sqlite3
import mysql.connector
import os

class MemoryBackend(ABC):
    @abstractmethod
    def initialize(self):
        pass

    @abstractmethod
    def add(self, text, metadata):
        pass

    @abstractmethod
    def update(self, id, metadata):
        pass

    @abstractmethod
    def query(self, text=None):
        pass

class SQLiteBackend(MemoryBackend):
    def __init__(self, db_path="memory.db"):
        self.db_path = db_path

    def initialize(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS long_term (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT UNIQUE,
                    truthfulness REAL,
                    importance REAL,
                    timestamp TEXT,
                    last_accessed TEXT
                )
            """)

    def add(self, text, metadata):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO long_term (text, truthfulness, importance, timestamp, last_accessed) VALUES (?, ?, ?, ?, ?)",
                (text, metadata["truthfulness"], metadata["importance"], metadata["timestamp"], metadata["last_accessed"])
            )

    def update(self, id, metadata):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE long_term SET truthfulness=?, importance=?, timestamp=?, last_accessed=? WHERE id=?",
                (metadata["truthfulness"], metadata["importance"], metadata["timestamp"], metadata["last_accessed"], id)
            )

    def query(self, text=None):
        with sqlite3.connect(self.db_path) as conn:
            if text:
                cursor = conn.execute("SELECT id, text, truthfulness, importance, timestamp, last_accessed FROM long_term WHERE text LIKE ?", (f"%{text}%",))
            else:
                cursor = conn.execute("SELECT id, text, truthfulness, importance, timestamp, last_accessed FROM long_term")
            return [(row[0], {"truthfulness": row[2], "importance": row[3], "timestamp": row[4], "last_accessed": row[5]}) for row in cursor.fetchall()]

class MySQLBackend(MemoryBackend):
    def __init__(self, host, user, password, database):
        self.config = {"host": host, "user": user, "password": password, "database": database}

    def initialize(self):
        with mysql.connector.connect(**self.config) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS long_term (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    text TEXT UNIQUE,
                    truthfulness FLOAT,
                    importance FLOAT,
                    timestamp VARCHAR(255),
                    last_accessed VARCHAR(255)
                )
            """)
            conn.commit()

    def add(self, text, metadata):
        with mysql.connector.connect(**self.config) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT IGNORE INTO long_term (text, truthfulness, importance, timestamp, last_accessed) VALUES (%s, %s, %s, %s, %s)",
                (text, metadata["truthfulness"], metadata["importance"], metadata["timestamp"], metadata["last_accessed"])
            )
            conn.commit()

    def update(self, id, metadata):
        with mysql.connector.connect(**self.config) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE long_term SET truthfulness=%s, importance=%s, timestamp=%s, last_accessed=%s WHERE id=%s",
                (metadata["truthfulness"], metadata["importance"], metadata["timestamp"], metadata["last_accessed"], id)
            )
            conn.commit()

    def query(self, text=None):
        with mysql.connector.connect(**self.config) as conn:
            cursor = conn.cursor()
            if text:
                cursor.execute("SELECT id, text, truthfulness, importance, timestamp, last_accessed FROM long_term WHERE text LIKE %s", (f"%{text}%",))
            else:
                cursor.execute("SELECT id, text, truthfulness, importance, timestamp, last_accessed FROM long_term")
            return [(row[0], {"truthfulness": row[2], "importance": row[3], "timestamp": row[4], "last_accessed": row[5]}) for row in cursor.fetchall()]

class HuggingFaceBackend(MemoryBackend):
    def __init__(self, dataset_name, token):
        self.dataset_name = dataset_name
        self.token = token
        self.dataset = None

    def initialize(self):
        login(self.token)
        try:
            self.dataset = load_dataset(self.dataset_name, split="train")
        except:
            self.dataset = Dataset.from_dict({"text": [], "truthfulness": [], "importance": [], "timestamp": [], "last_accessed": []})

    def add(self, text, metadata):
        new_row = {"text": text, **metadata}
        self.dataset = self.dataset.add_item(new_row)
        self.dataset.push_to_hub(self.dataset_name, token=self.token)

    def update(self, id, metadata):
        data = self.dataset[id]
        updated_row = {**data, **metadata}
        self.dataset = self.dataset.map(lambda x, idx: updated_row if idx == id else x, with_indices=True)
        self.dataset.push_to_hub(self.dataset_name, token=self.token)

    def query(self, text=None):
        if text:
            return [(i, row) for i, row in enumerate(self.dataset) if text in row["text"]]
        return [(i, row) for i, row in enumerate(self.dataset)]
