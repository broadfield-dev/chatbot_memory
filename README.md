# Memory Core

A lightweight Python package for managing short-term and long-term memory with support for multiple storage backends. This package provides a flexible memory system extracted from a Flask-based application, designed for easy integration into various projects.

## Features
- **Short-Term Memory**: Uses ChromaDB for in-memory vector storage with a configurable size limit.
- **Long-Term Memory**: Supports SQLite, MySQL, and Hugging Face Hub as pluggable backends.
- **Memory Consolidation**: Automatically moves or updates data from short-term to long-term memory based on similarity.
- **Optional Analysis**: Integrates with `memory_analyze` (a separate package) for truthfulness and importance assessment if installed.

## Installation

Install `memory_core` directly from GitHub:

```bash
pip install git+https://github.com/username/memory_core.git
```

### Dependencies
- `chromadb`
- `sentence-transformers`
- `mysql-connector-python` (for MySQL backend)
- `huggingface_hub` and `datasets` (for Hugging Face backend)

No additional LLM dependencies are required unless using `memory_analyze`.

## Usage

### Basic Example (Without Analysis)
```python
from memory_core import MemoryManager, SQLiteBackend

# Use SQLite as the long-term memory backend
sqlite_backend = SQLiteBackend("memory.db")
memory = MemoryManager(long_term_backend=sqlite_backend)

# Process content with default truthfulness and importance
memory.process_content("user", "The sky is blue", "What color is the sky?")
short_term = memory.get_short_term()
long_term = memory.get_long_term()
print("Short-term:", short_term["documents"], short_term["metadatas"])
print("Long-term:", long_term)
```

### With MySQL Backend
```python
from memory_core import MemoryManager, MySQLBackend

mysql_backend = MySQLBackend(host="localhost", user="root", password="password", database="memory")
memory = MemoryManager(long_term_backend=mysql_backend)
memory.process_content("user", "Hello world")
```

### With Hugging Face Backend
```python
from memory_core import MemoryManager, HuggingFaceBackend

hf_backend = HuggingFaceBackend("username/memory_dataset", "your_hf_token")
memory = MemoryManager(long_term_backend=hf_backend)
memory.process_content("user", "Hello world")
```

## Optional Integration with `memory_analyze`
If you install the `memory_analyze` package, `memory_core` will automatically use it to assess truthfulness and importance of content. See the [`memory_analyze` README](https://github.com/username/memory_analyze) for details.

Example with analysis:
```python
from memory_core import MemoryManager, SQLiteBackend

sqlite_backend = SQLiteBackend("memory.db")
memory = MemoryManager(
    long_term_backend=sqlite_backend,
    analyze_kwargs={"model_type": "hf", "api_key": "your_hf_token"}
)
memory.process_content("user", "The sky is blue", "What color is the sky?")
```

## Configuration
- `max_short_term_size`: Limits the number of entries in short-term memory (default: 50).
- `analyze_kwargs`: Dictionary of arguments passed to `memory_analyze` if installed (e.g., `model_type`, `api_key`).

## Backends
- **SQLite**: Local file-based storage (`SQLiteBackend(db_path="memory.db")`).
- **MySQL**: Database server storage (`MySQLBackend(host, user, password, database)`).
- **Hugging Face**: Cloud-based dataset storage (`HuggingFaceBackend(dataset_name, token)`).

## Contributing
Feel free to submit issues or pull requests to the [GitHub repository](https://github.com/username/memory_core).

## License
