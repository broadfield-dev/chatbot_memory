from setuptools import setup, find_packages

setup(
    name="memory_core",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "chromadb",
        "sentence-transformers",
        "mysql-connector-python",
        "huggingface_hub",
        "datasets"
    ],
    author="Your Name",
    author_email="your.email@example.com",
    description="A memory management package with short-term and long-term storage",
    url="https://github.com/username/memory_core",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
