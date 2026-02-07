from uuid import UUID
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Comment, Issue, Project, User, UserRole
from app.schemas.issue import IssueUpdate


def get_project(project_id: UUID, db: Session = Depends(get_db)) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def get_issue(issue_id: UUID, db: Session = Depends(get_db)) -> Issue:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")
    return issue


def get_comment(comment_id: UUID, db: Session = Depends(get_db)) -> Comment:
    comment = db.get(Comment, comment_id)
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found")
    return comment


def require_manager_or_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in {UserRole.manager, UserRole.admin}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return user


def require_project_manage(
    project: Project = Depends(get_project),
    user: User = Depends(get_current_user),
) -> Project:
    if user.role == UserRole.admin:
        return project
    if project.created_by_id == user.id:
        return project
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def require_issue_update_permission(
    issue_id: UUID,
    payload: IssueUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Issue:
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Issue not found")

    is_manager = user.role in {UserRole.manager, UserRole.admin}
    is_reporter = user.id == issue.reporter
    is_assignee = user.id == issue.assignee

    if not (is_manager or is_reporter or is_assignee):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    data = payload.model_dump(exclude_unset=True)
    if "assignee" in data and data["assignee"] != issue.assignee:
        if not (is_manager or is_reporter):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return issue


def require_comment_author(
    comment: Comment = Depends(get_comment),
    user: User = Depends(get_current_user),
) -> Comment:
    if comment.author_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only author can edit")
    return comment
