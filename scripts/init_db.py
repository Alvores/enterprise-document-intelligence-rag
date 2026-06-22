import sys
import os
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from backend.app.db.connection import db_manager
from backend.app.core.logging import logger

def initialize_database():
    """Creates the necessary relational tables for the RAG platform."""
    create_documents_table_sql = """
    CREATE TABLE IF NOT EXISTS documents (
        id UUID PRIMARY KEY,
        filename VARCHAR(255) NOT NULL,
        file_hash VARCHAR(64) UNIQUE NOT NULL,
        chunk_count INTEGER NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_file_hash ON documents(file_hash);
    """
    
    try:
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(create_documents_table_sql)
            conn.commit()
            logger.info("Documents tracking table verified/created successfully.")
    except Exception as e:
        logger.error("Failed to initialize database tables", extra={"error": str(e)})
        sys.exit(1)

if __name__ == "__main__":
    initialize_database()