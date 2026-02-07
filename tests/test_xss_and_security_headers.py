from datetime import timedelta

from app.models import User, UserRole
from app.services.security import create_token, hash_password


def _auth_headers(user_id: str) -> dict[str, str]:
    token = create_token(user_id, "access", timedelta(minutes=15))
    return {"Authorization": f"Bearer {token}"}


def _assert_sanitized(value: str) -> None:
    assert "<" not in value
    assert ">" not in value
    assert "onerror" not in value.lower()
    assert "onload" not in value.lower()


def test_csp_header_present(client):
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert resp.headers.get("content-security-policy") == "default-src 'self'"


def test_markdown_fields_are_sanitized(client, db_session):
    manager = User(
        username="xssmgr",
        email="xssmgr@example.com",
        password_hash=hash_password("Manager123!"),
        role=UserRole.manager,
    )
    db_session.add(manager)
    db_session.commit()
    headers = _auth_headers(str(manager.id))

    project_resp = client.post(
        "/api/projects",
        json={"name": "XSS Project", "description": "<script>alert(1)</script>alpha"},
        headers=headers,
    )
    assert project_resp.status_code == 201
    _assert_sanitized(project_resp.json()["description"])
    project_id = project_resp.json()["id"]

    issue_resp = client.post(
        f"/api/projects/{project_id}/issues",
        json={
            "title": "XSS Issue",
            "description": "<img src=x onerror=alert(1)>issue",
            "priority": "high",
        },
        headers=headers,
    )
    assert issue_resp.status_code == 201
    _assert_sanitized(issue_resp.json()["description"])
    issue_id = issue_resp.json()["id"]

    update_resp = client.patch(
        f"/api/issues/{issue_id}",
        json={"description": "<svg onload=alert(1)>updated</svg>"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    _assert_sanitized(update_resp.json()["description"])

    comment_resp = client.post(
        f"/api/issues/{issue_id}/comments",
        json={"content": "<b>note</b><script>alert(1)</script>"},
        headers=headers,
    )
    assert comment_resp.status_code == 201
    _assert_sanitized(comment_resp.json()["content"])
