from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_serializer
from app.models.user import UserRole
from app.services.security import mask_email


class UserBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    role: UserRole
    is_active: bool = True


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserOut(UserBase):
    id: UUID
    created_at: datetime
    last_login: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("email")
    def serialize_email(self, email: EmailStr) -> str:
        return mask_email(str(email))
