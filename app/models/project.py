from datetime import datetime, timezone
import uuid
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.db.types import GUID


class Project(Base):
    __tablename__ = "projects"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(1000), nullable=True)
    created_by_id = Column(GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    is_archived = Column(Boolean, default=False, nullable=False)

    creator = relationship("User")
