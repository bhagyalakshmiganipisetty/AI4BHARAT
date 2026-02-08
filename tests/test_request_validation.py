from datetime import timedelta

from app.models import Project, User, UserRole
from app.services.security import create_token, hash_password


def _auth_headers(user_id: str) -> dict[str, str]:
    token = create_token(user_id, "access", timedelta(minutes=15))
    return {"Authorization": f"Bearer {token}"}


def test_rejects_non_json_content_type(client):
    resp = client.post(
        "/api/auth/register",
        data="not-json",
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status_code == 415
    assert resp.json()["error"]["code"] == "unsupported_media_type"


def test_body_size_limit(client):
    large = "a" * 1_000_001
    payload = f'{{"blob":"{large}"}}'
    resp = client.post(
        "/api/auth/register",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 413
    assert resp.json()["error"]["code"] == "payload_too_large"


def test_sort_whitelist_ignores_unknown(client, db_session):
    manager = User(
        username="sortmgr",
        email="sortmgr@example.com",
        password_hash=hash_password("Manager123!"),
        role=UserRole.manager,
    )
    db_session.add(manager)
    db_session.flush()

    db_session.add_all(
        [
            Project(
                name="Alpha", description="Alpha project", created_by_id=manager.id
            ),
            Project(name="Beta", description="Beta project", created_by_id=manager.id),
        ]
    )
    db_session.commit()

    headers = _auth_headers(str(manager.id))
    resp = client.get("/api/projects", params={"sort": "unknown"}, headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_sort_rejects_invalid_characters(client, db_session):
    user = User(
        username="sortdev",
        email="sortdev@example.com",
        password_hash=hash_password("User123!"),
        role=UserRole.developer,
    )
    db_session.add(user)
    db_session.commit()

    headers = _auth_headers(str(user.id))
    resp = client.get("/api/projects", params={"sort": "name;drop"}, headers=headers)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


def test_invalid_status_query_param_rejected(client, db_session):
    user = User(
        username="statusdev",
        email="statusdev@example.com",
        password_hash=hash_password("User123!"),
        role=UserRole.developer,
    )
    db_session.add(user)
    db_session.commit()

    headers = _auth_headers(str(user.id))
    resp = client.get("/api/issues", params={"status": "not-a-status"}, headers=headers)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"
