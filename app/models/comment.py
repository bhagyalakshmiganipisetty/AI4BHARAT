import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.db.types import GUID


class Comment(Base):
    __tablename__ = "comments"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    content = Column(Text, nullable=False)
    issue_id = Column(
        GUID(), ForeignKey("issues.id", ondelete="CASCADE"), nullable=False
    )
    author_id = Column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    issue = relationship("Issue", back_populates="comments")
    author = relationship("User")
