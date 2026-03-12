import sys
import time
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in .env file.")
    sys.exit(1)

Base = declarative_base()
SessionLocal = None
engine = None


def connect_with_retry(max_retries: int = 5):
    """
    Attempt to connect to the database with exponential backoff.
    Retries after 1s, 2s, 4s, 8s, 16s before giving up.
    """
    global engine, SessionLocal

    for attempt in range(1, max_retries + 1):
        print(f"🔄 Database connection attempt {attempt}/{max_retries}...")
        try:
            engine = create_engine(
                DATABASE_URL,
                pool_pre_ping=True,
                pool_size=10,
                max_overflow=20,
            )

            # Verify connection is actually alive
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine,
            )

            print("✅ Database connected successfully!")
            return engine

        except Exception as e:
            wait_time = 2 ** (attempt - 1)  # 1s, 2s, 4s, 8s, 16s
            print(f"⚠️  Attempt {attempt} failed: {e}")

            if attempt < max_retries:
                print(f"⏳ Retrying in {wait_time}s...\n")
                time.sleep(wait_time)
            else:
                print(f"\n❌ All {max_retries} connection attempts failed. Shutting down.")
                sys.exit(1)


def get_db():
    """
    FastAPI dependency that provides a database session per request.
    Ensures the session is properly closed after each request.
    """
    if SessionLocal is None:
        raise RuntimeError("Database is not initialized. Call connect_with_retry() first.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize connection on module load
connect_with_retry(max_retries=5)