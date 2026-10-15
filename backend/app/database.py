import logging
import os
from urllib.parse import quote_plus
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / ".env")
logger = logging.getLogger(__name__)


def _database_url() -> str:
    """Build a database URL from DATABASE_URL or individual DB_* values."""
    override = os.getenv("DATABASE_URL")
    if override:
        return override

    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "3306")
    name = os.getenv("DB_NAME", "word_dictionary")
    return (
        f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{name}?charset=utf8mb4"
    )


SQLALCHEMY_DATABASE_URL = _database_url()
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db() -> None:
    """Create missing tables without deleting or resetting existing data.

    Use a migration tool for future schema changes.
    """
    from app.models.word import UserSearchHistory, Word  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database tables are ready.")


def get_db():
    """Yield a SQLAlchemy session and always close it."""
    db_session = SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()
