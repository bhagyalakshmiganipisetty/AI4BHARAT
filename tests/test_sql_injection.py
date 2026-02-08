from datetime import timedelta

from app.models import Issue, IssuePriority, Project, User, UserRole
from app.services.security import create_token, hash_password


def _auth_headers(user_id: str) -> dict[str, str]:
    token = create_token(user_id, "access", timedelta(minutes=15))
    return {"Authorization": f"Bearer {token}"}


def test_login_rejects_sql_injection(client, db_session):
    user = User(
        username="loginuser",
        email="loginuser@example.com",
        password_hash=hash_password("User123!"),
        role=UserRole.developer,
    )
    db_session.add(user)
    db_session.commit()

    resp = client.post(
        "/api/auth/login",
        json={"username": "' OR 1=1 --", "password": "DoesntMatter1!"},
    )
    assert resp.status_code == 401


def test_search_does_not_bypass_filters(client, db_session):
    manager = User(
        username="sqlmgr",
        email="sqlmgr@example.com",
        password_hash=hash_password("Manager123!"),
        role=UserRole.manager,
    )
    db_session.add(manager)
    db_session.flush()

    p1 = Project(name="Alpha", description="Alpha project", created_by_id=manager.id)
    p2 = Project(name="Beta", description="Beta project", created_by_id=manager.id)
    db_session.add_all([p1, p2])
    db_session.flush()

    issue = Issue(
        title="Normal issue",
        description="Normal description",
        project=p1.id,
        reporter=manager.id,
        priority=IssuePriority.low,
    )
    db_session.add(issue)
    db_session.commit()

    headers = _auth_headers(str(manager.id))
    resp_all = client.get("/api/projects", headers=headers)
    assert resp_all.status_code == 200
    assert len(resp_all.json()) == 2

    injection = "' OR 1=1 --"
    resp_search = client.get(
        "/api/projects", params={"search": injection}, headers=headers
    )
    assert resp_search.status_code == 422

    resp_issue_all = client.get("/api/issues", headers=headers)
    assert resp_issue_all.status_code == 200
    assert len(resp_issue_all.json()) == 1

    resp_issue_search = client.get(
        "/api/issues", params={"search": injection}, headers=headers
    )
    assert resp_issue_search.status_code == 422
