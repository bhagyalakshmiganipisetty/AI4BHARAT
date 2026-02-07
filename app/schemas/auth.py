from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: str
    exp: int
    type: str
    jti: str | None = None


class LoginRequest(BaseModel):
    username: str
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class SessionInfo(BaseModel):
    user_id: str
    issued_at: datetime


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)
