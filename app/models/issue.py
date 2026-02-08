import enum
import uuid
from datetime import date, datetime, timezone
from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.db.types import GUID


class IssueStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"
    reopened = "reopened"


class IssuePriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Issue(Base):
    __tablename__ = "issues"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(IssueStatus), nullable=False, default=IssueStatus.open)
    priority = Column(Enum(IssuePriority), nullable=False, default=IssuePriority.medium)
    project = Column(
        GUID(), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    reporter = Column(
        GUID(), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    assignee = Column(
        GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    due_date = Column(Date, nullable=True)
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    project_ref = relationship("Project", foreign_keys=[project])
    reporter_user = relationship("User", foreign_keys=[reporter])
    assignee_user = relationship("User", foreign_keys=[assignee])
    comments = relationship(
        "Comment", cascade="all, delete-orphan", back_populates="issue"
    )
