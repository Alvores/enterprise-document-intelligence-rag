import sys
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.app.core.logging import logger
from backend.app.db.connection import db_manager


def initialize_database():
    """Creates the necessary relational tables for the RAG platform."""
    create_documents_table_sql = """
    CREATE EXTENSION IF NOT EXISTS vector;
    
    CREATE TABLE IF NOT EXISTS documents (
        id UUID PRIMARY KEY,
        filename VARCHAR(255) NOT NULL,
        file_hash VARCHAR(64) UNIQUE NOT NULL,
        chunk_count INTEGER NOT NULL,
        status varchar(7) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'READY', 'FAILED')),
        gcs_uri TEXT,
        error_message TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    );
    
    ALTER TABLE documents
        ADD COLUMN IF NOT EXISTS status VARCHAR(7) NOT NULL DEFAULT 'PENDING'
            CHECK (status IN ('PENDING', 'READY', 'FAILED')),
        ADD COLUMN IF NOT EXISTS gcs_uri TEXT,
        ADD COLUMN IF NOT EXISTS error_message TEXT;

    ALTER TABLE documents
        ALTER COLUMN chunk_count SET DEFAULT 0;

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
