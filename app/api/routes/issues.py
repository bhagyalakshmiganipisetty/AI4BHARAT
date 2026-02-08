import enum
import uuid
from datetime import date, datetime
from uuid import UUID
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api import deps
from app.api.permissions import require_issue_update_permission
from app.api.query import SEARCH_PATTERN, SORT_PATTERN, apply_pagination, apply_sort
from app.models import Comment, Issue, IssuePriority, IssueStatus, Project, User
from app.schemas.issue import IssueCreate, IssueOut, IssueUpdate
from app.services.audit import audit_log
from app.services.security import sanitize_markdown

router = APIRouter(prefix="/issues", tags=["issues"])


@router.get("/", response_model=list[IssueOut])
def list_issues(
    status_filter: IssueStatus | None = Query(default=None, alias="status"),
    priority: IssuePriority | None = Query(default=None),
    assignee: UUID | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200, pattern=SEARCH_PATTERN),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    sort: str | None = Query(default=None, pattern=SORT_PATTERN),
    db: Session = Depends(deps.get_db),
    _: User = Depends(deps.get_current_user),
):
    q = db.query(Issue)
    if status_filter:
        q = q.filter(Issue.status == status_filter)
    if priority:
        q = q.filter(Issue.priority == priority)
    if assignee:
        q = q.filter(Issue.assignee == assignee)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(Issue.title.ilike(like), Issue.description.ilike(like)))
    q = apply_sort(
        q,
        sort,
        {
            "created_at": Issue.created_at,
            "updated_at": Issue.updated_at,
            "priority": Issue.priority,
            "status": Issue.status,
            "due_date": Issue.due_date,
        },
    )
    q = apply_pagination(q, page, limit)
    return q.all()


@router.get("/{issue_id}", response_model=IssueOut)
def get_issue(
    issue_id: UUID,
    db: Session = Depends(deps.get_db),
    _: User = Depends(deps.get_current_user),
):
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return issue


@router.post("/", response_model=IssueOut, status_code=status.HTTP_201_CREATED)
def create_issue(
    payload: IssueCreate,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    project = db.get(Project, payload.project)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    issue = Issue(
        title=payload.title,
        description=sanitize_markdown(payload.description),
        priority=payload.priority,
        project=payload.project,
        reporter=current_user.id,
        assignee=payload.assignee,
        due_date=payload.due_date,
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    audit_log(
        "issue_create",
        str(current_user.id),
        request.client.host if request.client else None,
        issue_id=str(issue.id),
        project=str(project.id),
    )
    return issue


@router.patch("/{issue_id}", response_model=IssueOut)
def update_issue(
    payload: IssueUpdate,
    request: Request,
    db: Session = Depends(deps.get_db),
    issue: Issue = Depends(require_issue_update_permission),
    current_user: User = Depends(deps.get_current_user),
):
    data = payload.model_dump(exclude_unset=True)

    if "status" in data:
        _enforce_transition(issue, data["status"], db)

    changes: dict[str, dict[str, Any]] = {}
    for field, value in data.items():
        if field == "description":
            value = sanitize_markdown(value)
        previous = _serialize_audit_value(getattr(issue, field))
        next_value = _serialize_audit_value(value)
        if previous == next_value:
            continue
        changes[field] = {"from": previous, "to": next_value}
        setattr(issue, field, value)
    db.commit()
    db.refresh(issue)
    audit_log(
        "issue_update",
        str(current_user.id),
        request.client.host if request.client else None,
        issue_id=str(issue.id),
        project=str(issue.project),
        fields=list(changes.keys()),
        changes=changes,
    )
    return issue


def _serialize_audit_value(value: Any) -> Any:
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _enforce_transition(issue: Issue, new_status: IssueStatus, db: Session) -> None:
    allowed = {
        IssueStatus.open: {IssueStatus.in_progress},
        IssueStatus.in_progress: {IssueStatus.resolved},
        IssueStatus.resolved: {IssueStatus.closed, IssueStatus.reopened},
        IssueStatus.closed: {IssueStatus.reopened},
        IssueStatus.reopened: {IssueStatus.in_progress},
    }
    if new_status == issue.status:
        return
    valid_next = allowed.get(issue.status, set())
    if new_status not in valid_next:
        raise HTTPException(status_code=400, detail="Invalid status transition")
    if issue.priority == IssuePriority.critical and new_status == IssueStatus.closed:
        comment_count = db.query(Comment).filter(Comment.issue_id == issue.id).count()
        if comment_count == 0:
            raise HTTPException(
                status_code=400,
                detail="Critical issues require a comment before closing",
            )
