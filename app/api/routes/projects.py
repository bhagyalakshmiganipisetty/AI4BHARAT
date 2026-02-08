from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api import deps
from app.api.permissions import (
    get_project,
    require_manager_or_admin,
    require_project_manage,
)
from app.api.query import SEARCH_PATTERN, SORT_PATTERN, apply_pagination, apply_sort
from app.models import Issue, IssuePriority, IssueStatus, Project, User
from app.schemas.issue import IssueCreateForProject, IssueOut
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.audit import audit_log
from app.services.security import sanitize_markdown

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=list[ProjectOut])
def list_projects(
    search: str | None = Query(default=None, max_length=200, pattern=SEARCH_PATTERN),
    is_archived: bool | None = Query(default=False),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    sort: str | None = Query(default=None, pattern=SORT_PATTERN),
    db: Session = Depends(deps.get_db),
    _: User = Depends(deps.get_current_user),
):
    q = db.query(Project)
    if is_archived is not None:
        q = q.filter(Project.is_archived == is_archived)
    if search:
        like = f"%{search}%"
        q = q.filter(or_(Project.name.ilike(like), Project.description.ilike(like)))
    q = apply_sort(
        q,
        sort,
        {
            "name": Project.name,
            "created_at": Project.created_at,
            "updated_at": Project.updated_at,
        },
    )
    q = apply_pagination(q, page, limit)
    return q.all()


@router.post("/", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(require_manager_or_admin),
):
    project = Project(
        name=payload.name,
        description=sanitize_markdown(payload.description),
        created_by_id=current_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    audit_log(
        "project_create",
        str(current_user.id),
        request.client.host if request.client else None,
        project_id=str(project.id),
    )
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project_detail(
    project: Project = Depends(get_project), _: User = Depends(deps.get_current_user)
):
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    payload: ProjectUpdate,
    request: Request,
    project: Project = Depends(require_project_manage),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field == "description":
            value = sanitize_markdown(value)
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    audit_log(
        "project_update",
        str(current_user.id),
        request.client.host if request.client else None,
        project_id=str(project.id),
        fields=list(data.keys()),
    )
    return project


@router.delete("/{project_id}", status_code=204)
def archive_project(
    request: Request,
    project: Project = Depends(require_project_manage),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    project.is_archived = True
    db.commit()
    audit_log(
        "project_archive",
        str(current_user.id),
        request.client.host if request.client else None,
        project_id=str(project.id),
    )
    return None


@router.get("/{project_id}/issues", response_model=list[IssueOut])
def list_project_issues(
    project: Project = Depends(get_project),
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
    q = db.query(Issue).filter(Issue.project == project.id)
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


@router.post(
    "/{project_id}/issues", response_model=IssueOut, status_code=status.HTTP_201_CREATED
)
def create_project_issue(
    payload: IssueCreateForProject,
    request: Request,
    project: Project = Depends(get_project),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    issue = Issue(
        title=payload.title,
        description=sanitize_markdown(payload.description),
        priority=payload.priority,
        project=project.id,
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
