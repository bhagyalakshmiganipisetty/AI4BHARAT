from datetime import datetime, timedelta, timezone
import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.config import settings
from app.models import User
from app.services import security
from app.services import token_store


def authenticate_user(db: Session, username: str, password: str) -> User:
    user = db.query(User).filter(User.username == username).first()
    if token_store.store.inc_failure(username, window=900) > 10:
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED, detail="Account temporarily locked"
        )
    if not user or not security.verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    token_store.store.clear_failure(username)
    user.last_login = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    return user


def create_token_pair(user_id: str) -> tuple[str, str, int]:
    user_id = str(user_id)
    access_exp = timedelta(minutes=settings.access_token_expire_minutes)
    refresh_exp = timedelta(days=settings.refresh_token_expire_days)
    access = security.create_token(
        user_id, token_type="access", expires_delta=access_exp
    )
    refresh_jti = str(uuid.uuid4())
    refresh = security.create_token(
        user_id, token_type="refresh", expires_delta=refresh_exp, jti=refresh_jti
    )
    token_store.store.add_refresh_session(
        user_id, refresh_jti, int(refresh_exp.total_seconds())
    )
    return access, refresh, int(access_exp.total_seconds())


def blacklist_refresh(token: str, exp_seconds: int) -> None:
    token_store.store.add(token, exp_seconds)


def is_blacklisted(token: str) -> bool:
    return token_store.store.exists(token)


def _token_ttl_seconds(token: str) -> int | None:
    try:
        payload = security.decode_token(token)
    except Exception:
        return None
    exp = payload.get("exp")
    if not isinstance(exp, int):
        return None
    now = int(datetime.now(timezone.utc).timestamp())
    return exp - now


def blacklist_access(token: str) -> None:
    ttl_seconds = _token_ttl_seconds(token)
    if ttl_seconds and ttl_seconds > 0:
        token_store.store.add(token, ttl_seconds)


def is_access_blacklisted(token: str) -> bool:
    return token_store.store.exists(token)


def enforce_refresh_active(user_id: str, jti: str | None) -> None:
    user_id = str(user_id)
    if not jti or not token_store.store.is_refresh_active(user_id, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Stale refresh token"
        )


def rotate_refresh_session(user_id: str, old_jti: str) -> str:
    user_id = str(user_id)
    refresh_exp = timedelta(days=settings.refresh_token_expire_days)
    new_jti = str(uuid.uuid4())
    token_store.store.rotate_refresh_session(
        user_id, old_jti, new_jti, int(refresh_exp.total_seconds())
    )
    return new_jti


def remove_refresh_session(user_id: str, jti: str) -> None:
    token_store.store.remove_refresh_session(str(user_id), jti)


def revoke_all_refresh(user_id: str) -> None:
    token_store.store.revoke_all_refresh(str(user_id))


def revoke_all_access(user_id: str) -> None:
    ttl_seconds = int(
        timedelta(minutes=settings.access_token_expire_minutes).total_seconds()
    )
    revoked_at = int(datetime.now(timezone.utc).timestamp())
    token_store.store.set_access_revoked_at(str(user_id), revoked_at, ttl_seconds)


def get_access_revoked_at(user_id: str) -> int | None:
    return token_store.store.get_access_revoked_at(str(user_id))
