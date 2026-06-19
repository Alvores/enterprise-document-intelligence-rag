import psycopg2
from psycopg2 import pool
from contextlib import contextmanager
from backend.app.core.config import settings
from backend.app.core.logging import logger

class DatabaseManager:
    def __init__(self):
        self.pool = None

    def initialize_pool(self):
        try:
            logger.info("Initializing PostgreSQL threaded connection pool...")
            self.pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=settings.DATABASE_URL
            )
            logger.info("Connection pool established successfully.")
        except Exception as e:
            logger.critical("Failed to connect to PostgreSQL", extra={"error": str(e)})
            raise e

    @contextmanager
    def get_connection(self):
        if not self.pool:
            self.initialize_pool()
            
        conn = self.pool.getconn()
        try:
            yield conn
        finally:
            self.pool.putconn(conn)

db_manager = DatabaseManager()