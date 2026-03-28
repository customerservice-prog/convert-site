"""SQLAlchemy engine, session, and table creation."""
from __future__ import annotations

import logging
import threading
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

import config

logger = logging.getLogger(__name__)

write_lock = threading.Lock()


class Base(DeclarativeBase):
    pass


def _make_engine():
    url = config.DATABASE_URL
    if url.startswith("sqlite"):
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        connect_args = {"check_same_thread": False}
        engine = create_engine(
            url,
            connect_args=connect_args,
            pool_pre_ping=True,
        )

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ARG001
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

        return engine
    return create_engine(url, pool_pre_ping=True)


engine = _make_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    from models import Job  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("Database initialized at %s", config.DATABASE_URL)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
