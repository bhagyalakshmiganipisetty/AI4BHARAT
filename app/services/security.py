import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import jwt
import bleach
import bcrypt

from app.core.config import settings


def verify_password_complexity(password: str) -> bool:
    return bool(re.match(settings.password_complexity_regex, password))


def hash_password(password: str) -> str:
    if len(password) < settings.password_min_length or not verify_password_complexity(
        password
    ):
        raise ValueError("Password does not meet complexity requirements")
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("Password exceeds bcrypt maximum length")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _load_key(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Key file missing: {path}")
    return path.read_text()


PRIVATE_KEY_CACHE: str | None = None
PUBLIC_KEY_CACHE: str | None = None


def get_private_key() -> str:
    global PRIVATE_KEY_CACHE
    if PRIVATE_KEY_CACHE is None:
        PRIVATE_KEY_CACHE = _load_key(settings.jwt_private_key_path)
    return PRIVATE_KEY_CACHE


def get_public_key() -> str:
    global PUBLIC_KEY_CACHE
    if PUBLIC_KEY_CACHE is None:
        PUBLIC_KEY_CACHE = _load_key(settings.jwt_public_key_path)
    return PUBLIC_KEY_CACHE


def create_token(
    subject: str, token_type: str, expires_delta: timedelta, jti: str | None = None
) -> str:
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
    }
    if jti:
        payload["jti"] = jti
    payload["exp"] = int((now + expires_delta).timestamp())
    return jwt.encode(payload, get_private_key(), algorithm=settings.jwt_alg)


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, get_public_key(), algorithms=[settings.jwt_alg])
    except jwt.PyJWTError as exc:
        raise ValueError("Invalid token") from exc


def sanitize_markdown(text: str | None) -> str | None:
    """Escape markdown/HTML to prevent XSS in rendered responses."""
    if text is None:
        return None
    return bleach.clean(text, tags=[], attributes={}, strip=True)


def mask_sensitive(value: str, visible: int = 4) -> str:
    if not value:
        return value
    if len(value) <= visible:
        return "*" * len(value)
    return f"{value[:visible]}***"


def mask_email(email: str) -> str:
    if not email:
        return email
    if "@" not in email:
        return mask_sensitive(email)
    local, _, domain = email.partition("@")
    if not local or not domain:
        return mask_sensitive(email)
    masked_local = f"{local[0]}***"
    return f"{masked_local}@{domain}"
