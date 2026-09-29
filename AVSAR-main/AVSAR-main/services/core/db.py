"""Database engine/session plumbing (SQLAlchemy 2.0, psycopg3).

One Postgres 16 + pgvector instance holds relational rows, vectors and the
tsvector BM25 index (TECH_STACK.md §1: "fewer moving parts at 3 a.m.").
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    future=True,
    # Fail fast when Postgres is gone. Without an explicit timeout a beneficiary
    # waits on a TCP connect that may never complete, which reads as a hang
    # rather than as the speakable "try again shortly" the dossier requires.
    connect_args={"connect_timeout": 3},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context-managed session for scripts/pipelines."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def ping() -> bool:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True


def pgvector_available() -> bool:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT count(*) FROM pg_extension WHERE extname = 'vector'")
        ).scalar()
    return bool(row)
