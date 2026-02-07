from datetime import timedelta

from app.models import User, UserRole
from app.services.security import hash_password, create_token
from app.services import auth as auth_service


def seed_user(db):
    u = User(username="authu", email="authu@x.com", password_hash=hash_password("User123!"), role=UserRole.developer)
    db.add(u)
    db.commit()
    return u


def auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_refresh_rotation_blacklists_old(client, db_session):
    user = seed_user(db_session)
    access, refresh, _ = auth_service.create_token_pair(str(user.id))

    # first refresh succeeds
    resp = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    new_refresh = resp.json()["refresh_token"]

    # old refresh now invalid
    resp_old = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert resp_old.status_code == 401

    # new refresh works
    resp_new = client.post("/api/auth/refresh", json={"refresh_token": new_refresh})
    assert resp_new.status_code == 200


def test_logout_all_invalidates_refresh(client, db_session):
    user = seed_user(db_session)
    access, refresh, _ = auth_service.create_token_pair(str(user.id))
    token = create_token(str(user.id), "access", timedelta(minutes=5))
    # logout-all
    resp = client.post("/api/auth/logout-all", headers=auth_header(token))
    assert resp.status_code == 204
    resp = client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 401


def test_logout_revokes_access_token(client, db_session):
    user = seed_user(db_session)
    access, refresh, _ = auth_service.create_token_pair(str(user.id))

    resp = client.post("/api/auth/logout", json={"refresh_token": refresh}, headers=auth_header(access))
    assert resp.status_code == 204
    resp = client.get("/api/auth/me", headers=auth_header(access))
    assert resp.status_code == 401
