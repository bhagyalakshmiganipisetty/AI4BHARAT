from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api import deps
from app.models import User, UserRole
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    PasswordChangeRequest,
)
from app.schemas.user import UserOut
from app.services import auth as auth_service, security
from app.services.audit import audit_log
from app.services.pii import hash_pii
from app.core.config import settings
from app.core.limiter import limiter
from app.api.responses import UNAUTHORIZED, FORBIDDEN, RATE_LIMITED

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer(auto_error=False)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_sensitive)
def register(
    payload: RegisterRequest, request: Request, db: Session = Depends(deps.get_db)
):
    email_hash = hash_pii(payload.email)
    if (
        db.query(User)
        .filter((User.username == payload.username) | (User.email_hash == email_hash))
        .first()
    ):
        raise HTTPException(status_code=400, detail="Username or email already exists")
    hashed = security.hash_password(payload.password)
    user = User(
        username=payload.username, password_hash=hashed, role=UserRole.developer
    )
    user.email = payload.email
    db.add(user)
    db.commit()
    db.refresh(user)
    audit_log("register", str(user.id), request.client.host if request.client else None)
    return user


@router.post("/login", response_model=TokenPair, responses=UNAUTHORIZED | RATE_LIMITED)
@limiter.limit(settings.rate_limit_login)
def login(request: Request, payload: LoginRequest, db: Session = Depends(deps.get_db)):
    try:
        user = auth_service.authenticate_user(db, payload.username, payload.password)
    except HTTPException:
        audit_log(
            "login_failed",
            None,
            request.client.host if request.client else None,
            username=payload.username,
        )
        raise
    access, refresh, expires_in = auth_service.create_token_pair(str(user.id))
    audit_log(
        "login_success", str(user.id), request.client.host if request.client else None
    )
    return TokenPair(access_token=access, refresh_token=refresh, expires_in=expires_in)


@router.post("/refresh", response_model=TokenPair, responses=UNAUTHORIZED)
@limiter.limit(settings.rate_limit_sensitive)
def refresh(payload: RefreshRequest, request: Request):
    data = security.decode_token(payload.refresh_token)
    if data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    auth_service.enforce_refresh_active(data.get("sub"), data.get("jti"))
    if auth_service.is_blacklisted(payload.refresh_token):
        raise HTTPException(status_code=401, detail="Token revoked")
    user_id = data.get("sub")
    new_jti = auth_service.rotate_refresh_session(user_id, data.get("jti"))
    access = security.create_token(
        user_id,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    refresh = security.create_token(
        user_id,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_expire_days),
        jti=new_jti,
    )
    auth_service.blacklist_refresh(
        payload.refresh_token, settings.refresh_token_expire_days * 24 * 3600
    )
    audit_log("refresh", user_id, request.client.host if request.client else None)
    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=204, responses=UNAUTHORIZED)
@limiter.limit(settings.rate_limit_sensitive)
def logout(
    payload: RefreshRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
):
    access_token = credentials.credentials if credentials else None
    if access_token:
        try:
            access_payload = security.decode_token(access_token)
        except Exception:
            access_payload = None
        if access_payload and access_payload.get("type") == "access":
            auth_service.blacklist_access(access_token)

    if auth_service.is_blacklisted(payload.refresh_token):
        return None
    data = security.decode_token(payload.refresh_token)
    if data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    auth_service.enforce_refresh_active(data.get("sub"), data.get("jti"))
    auth_service.blacklist_refresh(
        payload.refresh_token, settings.refresh_token_expire_days * 24 * 3600
    )
    auth_service.remove_refresh_session(data.get("sub"), data.get("jti"))
    audit_log(
        "logout", data.get("sub"), request.client.host if request.client else None
    )
    return None


@router.post("/logout-all", status_code=204, responses=UNAUTHORIZED)
@limiter.limit(settings.rate_limit_sensitive)
def logout_all(request: Request, current_user: User = Depends(deps.get_current_user)):
    auth_service.revoke_all_refresh(current_user.id)
    auth_service.revoke_all_access(current_user.id)
    audit_log(
        "logout_all",
        str(current_user.id),
        request.client.host if request.client else None,
    )
    return None


@router.post("/change-password", status_code=204, responses=UNAUTHORIZED | FORBIDDEN)
@limiter.limit(settings.rate_limit_sensitive)
def change_password(
    payload: PasswordChangeRequest,
    request: Request,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db),
):
    if not security.verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid current password")
    current_user.password_hash = security.hash_password(payload.new_password)
    db.add(current_user)
    db.commit()
    auth_service.revoke_all_refresh(current_user.id)
    auth_service.revoke_all_access(current_user.id)
    audit_log(
        "change_password",
        str(current_user.id),
        request.client.host if request.client else None,
    )
    return None


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(deps.get_current_user)):
    return current_user
