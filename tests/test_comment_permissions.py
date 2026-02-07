from datetime import timedelta

from app.models import Comment, Issue, IssuePriority, Project, User, UserRole
from app.services.security import create_token, hash_password


def seed(db):
    author = User(username="u1", email="u1@x.com", password_hash=hash_password("User123!"), role=UserRole.developer)
    other = User(username="u2", email="u2@x.com", password_hash=hash_password("User123!"), role=UserRole.developer)
    db.add_all([author, other])
    db.flush()
    proj = Project(name="P2", description="demo", created_by_id=author.id)
    db.add(proj)
    db.flush()
    issue = Issue(title="Bug", description="desc", project=proj.id, reporter=author.id, priority=IssuePriority.low)
    db.add(issue)
    db.flush()
    comment = Comment(content="hello", issue_id=issue.id, author_id=author.id)
    db.add(comment)
    db.commit()
    return author, other, comment


def auth_header(user_id):
    token = create_token(str(user_id), "access", timedelta(minutes=5))
    return {"Authorization": f"Bearer {token}"}


def test_only_author_can_edit_comment(client, db_session):
    author, other, comment = seed(db_session)
    resp = client.patch(f"/api/comments/{comment.id}", json={"content": "update"}, headers=auth_header(other.id))
    assert resp.status_code == 403
    resp = client.patch(f"/api/comments/{comment.id}", json={"content": "update"}, headers=auth_header(author.id))
    assert resp.status_code == 200
    assert resp.json()["content"] == "update"
