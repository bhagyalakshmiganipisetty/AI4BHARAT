from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CommentBase(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class CommentCreate(CommentBase):
    issue_id: UUID


class CommentCreateForIssue(CommentBase):
    pass


class CommentUpdate(CommentBase):
    pass


class CommentOut(CommentBase):
    id: UUID
    issue_id: UUID
    author_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
