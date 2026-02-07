from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    is_archived: bool | None = None


class ProjectOut(ProjectBase):
    id: UUID
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    created_by_id: UUID

    model_config = ConfigDict(from_attributes=True)
