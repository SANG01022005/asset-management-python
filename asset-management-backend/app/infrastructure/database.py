"""
app/infrastructure/database.py
Database connection với retry logic.
"""
import sys
import time
import logging
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.critical("❌ DATABASE_URL not found in environment / .env file.")
    sys.exit(1)

Base = declarative_base()
SessionLocal = None
engine = None


def connect_with_retry(max_retries: int = 5):
    """Attempt to connect to the database with exponential backoff."""
    global engine, SessionLocal

    for attempt in range(1, max_retries + 1):
        logger.info("🔄 Database connection attempt %d/%d...", attempt, max_retries)
        try:
            engine = create_engine(
                DATABASE_URL,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
            )
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine,
            )
            logger.info("✅ Database connected successfully!")
            return engine

        except Exception as e:
            wait_time = 2 ** (attempt - 1)
            logger.warning("⚠️  Attempt %d failed: %s", attempt, e)
            if attempt < max_retries:
                logger.info("⏳ Retrying in %ds...", wait_time)
                time.sleep(wait_time)
            else:
                logger.critical("❌ All %d connection attempts failed.", max_retries)
                sys.exit(1)


def get_db():
    """FastAPI dependency — yields a DB session, closes it after the request."""
    if SessionLocal is None:
        raise RuntimeError("Database is not initialized. Call connect_with_retry() first.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()