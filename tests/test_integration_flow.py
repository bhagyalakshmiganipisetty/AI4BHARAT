from datetime import timedelta

from app.models import User, UserRole
from app.services.security import create_token, hash_password


def _create_user(db_session, role: UserRole, username: str) -> User:
    user = User(username=username, password_hash=hash_password("Manager123!"), role=role)
    user.email = f"{username}@example.com"
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _auth_headers(user_id: str) -> dict[str, str]:
    token = create_token(user_id, "access", timedelta(minutes=15))
    return {"Authorization": f"Bearer {token}"}


def test_project_issue_flow(client, db_session):
    manager = _create_user(db_session, UserRole.manager, "manager1")
    headers = _auth_headers(str(manager.id))

    project_resp = client.post(
        "/api/projects",
        json={"name": "Demo", "description": "Demo project"},
        headers=headers,
    )
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    issue_resp = client.post(
        f"/api/projects/{project_id}/issues",
        json={"title": "Bug 1", "description": "Steps", "priority": "high"},
        headers=headers,
    )
    assert issue_resp.status_code == 201
    issue_id = issue_resp.json()["id"]

    update_resp = client.patch(
        f"/api/issues/{issue_id}",
        json={"status": "in_progress"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["status"] == "in_progress"
