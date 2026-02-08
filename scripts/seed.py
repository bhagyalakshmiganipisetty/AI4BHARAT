"""Seed database with sample users/projects/issues/comments."""

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models import User, UserRole, Project, Issue, IssuePriority
from app.services.security import hash_password


def run():
    db: Session = SessionLocal()
    try:
        admin = User(
            username="admin",
            email="admin@example.com",
            password_hash=hash_password("Admin123!"),
            role=UserRole.admin,
        )
        dev = User(
            username="dev",
            email="dev@example.com",
            password_hash=hash_password("Dev123!a"),
            role=UserRole.developer,
        )
        db.add_all([admin, dev])
        db.flush()

        proj = Project(
            name="Platform", description="Platform bugs", created_by_id=admin.id
        )
        db.add(proj)
        db.flush()

        issue = Issue(
            title="Sample bug",
            description="Demo issue",
            project=proj.id,
            reporter=dev.id,
            assignee=admin.id,
            priority=IssuePriority.high,
        )
        db.add(issue)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()
