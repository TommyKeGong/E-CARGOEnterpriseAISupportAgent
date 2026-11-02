"""Database helpers."""

from collections.abc import Generator
from os import environ

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def database_url_from_env() -> str:
    if "DATABASE_URL" not in environ:
        raise RuntimeError("DATABASE_URL must be configured for database operations")
    return environ["DATABASE_URL"]


def create_database_engine(database_url: str | None = None) -> Engine:
    return create_engine(database_url or database_url_from_env(), pool_pre_ping=True)


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db_session() -> Generator[Session, None, None]:
    """Yield a request-scoped database session for read-only API handlers."""
    session = session_factory(create_database_engine())()
    try:
        yield session
    finally:
        session.close()
