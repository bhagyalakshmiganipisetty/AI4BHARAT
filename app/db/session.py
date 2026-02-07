from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

Base = declarative_base()

_engine = None
_SessionLocal = None


def _create_engine():
    db_url = settings.database_url
    connect_args = {}
    if settings.env.lower() == "test":
        db_url = "sqlite+pysqlite:///:memory:"
        connect_args = {"check_same_thread": False}
    return create_engine(db_url, pool_pre_ping=True, future=True, connect_args=connect_args)


def get_engine():
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine


def get_session_local():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine(), future=True)
    return _SessionLocal


def SessionLocal():
    return get_session_local()()


def get_db():
    db = get_session_local()()
    try:
        yield db
    finally:
        db.close()
