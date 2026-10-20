import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

# Deterministic constraint names so hand-written migrations, create_all()
# and alembic autogenerate all produce identical DDL.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}


class Base(DeclarativeBase):
    naming_convention = NAMING_CONVENTION


def normalize_database_url(url: str) -> str:
    """Accept Render-style postgres:// URLs and route them to psycopg 3."""
    url = url.strip()
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


def database_url() -> str | None:
    url = os.getenv("DATABASE_URL", "").strip()
    return normalize_database_url(url) if url else None


def _build_engine(url: str) -> Engine:
    kwargs: dict = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
    return create_engine(url, **kwargs)


_engine: Engine | None = None
_session_factory: sessionmaker | None = None


def get_engine() -> Engine | None:
    """Build (and cache) the engine from DATABASE_URL on first use.

    Returns None when DATABASE_URL is unset — persistence is optional so
    local dev and the existing test suite run without Postgres.
    """
    global _engine, _session_factory
    if _engine is None:
        url = database_url()
        if not url:
            return None
        _engine = _build_engine(url)
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> sessionmaker | None:
    get_engine()
    return _session_factory


def reset_engine() -> None:
    """Dispose of the cached engine (used by tests when swapping DATABASE_URL)."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def db_enabled() -> bool:
    return get_engine() is not None


@contextmanager
def session_scope():
    """Commit-on-success session; rolls back and re-raises on error."""
    factory = get_session_factory()
    if factory is None:
        yield None
        return
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
