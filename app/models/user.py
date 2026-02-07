import enum
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, Enum, String
import uuid

from app.db.session import Base
from app.db.types import GUID
from app.services.pii import decrypt_pii, encrypt_pii, hash_pii


class UserRole(str, enum.Enum):
    developer = "developer"
    manager = "manager"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email_encrypted = Column(String(512), nullable=False)
    email_hash = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.developer)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_login = Column(DateTime, nullable=True)

    @property
    def email(self) -> str:
        return decrypt_pii(self.email_encrypted)

    @email.setter
    def email(self, value: str) -> None:
        self.email_encrypted = encrypt_pii(value)
        self.email_hash = hash_pii(value)
