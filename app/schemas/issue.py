from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from app.models.issue import IssuePriority, IssueStatus


class IssueBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(max_length=5000)
    status: IssueStatus = IssueStatus.open
    priority: IssuePriority = IssuePriority.medium
    due_date: date | None = None


class IssueCreate(IssueBase):
    project: UUID
    assignee: UUID | None = None


class IssueCreateForProject(IssueBase):
    assignee: UUID | None = None


class IssueUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    status: IssueStatus | None = None
    priority: IssuePriority | None = None
    assignee: UUID | None = None
    due_date: date | None = None


class IssueOut(IssueBase):
    id: UUID
    project: UUID
    reporter: UUID
    assignee: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
