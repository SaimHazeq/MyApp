"""
SQLAlchemy engine/session management.

Uses SQLite by default (zero-config, file-based) but DATABASE_URL can be
swapped to Postgres/MySQL in production without touching any other module,
since every route depends only on the `get_db` generator below.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import get_settings

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and guarantees closure."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Called once at app startup."""
    from app.models import user, project  # noqa: F401  (ensure models are registered)
    Base.metadata.create_all(bind=engine)
