from setuptools import setup, find_packages

setup(
    name="chatbot_memory",
    version="0.1.0",
    packages=['.'],
    install_requires=[
        "chromadb",
        "sentence-transformers",
        "mysql-connector-python",
        "huggingface_hub",
        "datasets"
    ],
    author="broadfield-dev",
    author_email="your.email@example.com",
    description="A memory management package with short-term and long-term storage",
    url="https://github.com/broadfield-dev/chatbot_memory",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
