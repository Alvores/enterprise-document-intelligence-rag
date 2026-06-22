import os
from pathlib import Path
from dotenv import load_dotenv

# Automatically locate the .env file at the project root
ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
load_dotenv(dotenv_path=ROOT_DIR / ".env")

class Settings:
    APP_NAME: str = "Enterprise Document Intelligence RAG"
    APP_VERSION: str = "0.1.0"
    
    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set")
    
    # Ollama Configuration
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")

    # RAG Configuration
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "384"))
    
    # Chunking Strategy
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "512"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))
    
    # File Upload Constraints
    MAX_FILE_SIZE_BYTES: int = int(os.getenv("MAX_FILE_SIZE_BYTES", str(50 * 1024 * 1024))) # 50MB

settings = Settings()