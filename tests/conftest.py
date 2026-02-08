import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _ensure_jwt_keys() -> None:
    key_dir = ROOT / ".tmp" / "test_keys"
    key_dir.mkdir(parents=True, exist_ok=True)
    private_key_path = key_dir / "jwt_private.pem"
    public_key_path = key_dir / "jwt_public.pem"
    if not private_key_path.exists() or not public_key_path.exists():
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        private_key_path.write_bytes(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        public_key_path.write_bytes(
            key.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            )
        )
    os.environ.setdefault("JWT_PRIVATE_KEY_PATH", str(private_key_path))
    os.environ.setdefault("JWT_PUBLIC_KEY_PATH", str(public_key_path))
    os.environ.setdefault("ENV", "test")


_ensure_jwt_keys()

from app.db.session import Base
from app.main import app
from app.api import deps


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(
        "sqlite+pysqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture(scope="function")
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    SessionTesting = sessionmaker(bind=connection, autoflush=False, autocommit=False)
    session = SessionTesting()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[deps.get_db] = override_get_db
    return TestClient(app)
