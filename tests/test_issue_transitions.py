from datetime import timedelta

from app.models import Issue, IssuePriority, IssueStatus, Project, User, UserRole, Comment
from app.services.security import hash_password
from app.services import auth as auth_service, security as sec


def seed_basic(db):
    admin = User(username="admin", email="a@a.com", password_hash=hash_password("Admin123!"), role=UserRole.admin)
    reporter = User(username="rep", email="r@a.com", password_hash=hash_password("Rep123!a"), role=UserRole.developer)
    db.add_all([admin, reporter])
    db.flush()
    proj = Project(name="P1", description="demo", created_by_id=admin.id)
    db.add(proj)
    db.flush()
    issue = Issue(title="Bug", description="desc", project=proj.id, reporter=reporter.id, priority=IssuePriority.critical)
    db.add(issue)
    db.commit()
    return admin, reporter, proj, issue


def auth_header(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_invalid_transition_rejected(client, db_session):
    admin, reporter, proj, issue = seed_basic(db_session)
    # simulate login by forging token
    token = sec.create_token(str(reporter.id), "access", timedelta(minutes=5))
    resp = client.patch(f"/api/issues/{issue.id}", json={"status": "closed"}, headers=auth_header(token))
    assert resp.status_code == 400
    assert "Invalid status transition" in resp.json()["error"]["message"]


def test_critical_requires_comment_before_close(client, db_session):
    admin, reporter, proj, issue = seed_basic(db_session)
    token = sec.create_token(str(admin.id), "access", timedelta(minutes=5))
    # move through valid transitions before closing
    progress = client.patch(f"/api/issues/{issue.id}", json={"status": "in_progress"}, headers=auth_header(token))
    assert progress.status_code == 200
    resolved = client.patch(f"/api/issues/{issue.id}", json={"status": "resolved"}, headers=auth_header(token))
    assert resolved.status_code == 200
    resp = client.patch(f"/api/issues/{issue.id}", json={"status": "closed"}, headers=auth_header(token))
    assert resp.status_code == 400
    assert "require a comment" in resp.json()["error"]["message"]

    # add comment then close
    c = Comment(content="note", issue_id=issue.id, author_id=admin.id)
    db_session.add(c)
    db_session.commit()
    resp = client.patch(f"/api/issues/{issue.id}", json={"status": "closed"}, headers=auth_header(token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"
