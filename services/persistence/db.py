"""Engine/session management. SQLite for dev/test, Postgres/TimescaleDB in deployment."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base


def make_engine(url: str, *, echo: bool = False) -> Engine:
    """Create an engine. An in-memory SQLite URL is pinned to one shared connection."""
    if url in ("sqlite://", "sqlite:///:memory:"):
        return create_engine(url, echo=echo, future=True,
                              connect_args={"check_same_thread": False}, poolclass=StaticPool)
    return create_engine(url, echo=echo, future=True)


def init_db(engine: Engine) -> None:
    """Create all tables. Deployment uses Alembic migrations instead (see migrations/)."""
    Base.metadata.create_all(engine)


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
