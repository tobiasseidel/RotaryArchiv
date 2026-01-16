"""
Database Setup und Session Management
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from src.rotary_archiv.config import settings

# SQLAlchemy Engine
# SQLite benötigt connect_args für Foreign Keys
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    pool_pre_ping=bool(not settings.database_url.startswith("sqlite")),
    echo=settings.debug,
    connect_args=connect_args,
)

# Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base Class für Models
Base = declarative_base()


def get_db() -> Generator:
    """
    Dependency für FastAPI: Datenbank-Session bereitstellen

    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
