from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api import deps
from app.api.permissions import get_issue, require_comment_author
from app.models import Comment, Issue, User
from app.schemas.comment import (
    CommentCreate,
    CommentCreateForIssue,
    CommentOut,
    CommentUpdate,
)
from app.services.audit import audit_log
from app.services.security import sanitize_markdown

router = APIRouter(tags=["comments"])


@router.get("/issues/{issue_id}/comments", response_model=list[CommentOut])
def list_issue_comments(
    issue: Issue = Depends(get_issue),
    db: Session = Depends(deps.get_db),
    _: User = Depends(deps.get_current_user),
):
    return db.query(Comment).filter(Comment.issue_id == issue.id).all()


@router.get("/comments/issue/{issue_id}", response_model=list[CommentOut])
def list_comments_legacy(
    issue_id: UUID,
    db: Session = Depends(deps.get_db),
    _: User = Depends(deps.get_current_user),
):
    return db.query(Comment).filter(Comment.issue_id == issue_id).all()


@router.post(
    "/issues/{issue_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def add_issue_comment(
    issue_id: UUID,
    payload: CommentCreateForIssue,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    comment = Comment(
        content=sanitize_markdown(payload.content) or "",
        issue_id=issue.id,
        author_id=current_user.id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    audit_log(
        "comment_add",
        str(current_user.id),
        request.client.host if request.client else None,
        comment_id=str(comment.id),
        issue_id=str(issue.id),
    )
    return comment


@router.post(
    "/comments", response_model=CommentOut, status_code=status.HTTP_201_CREATED
)
def add_comment_legacy(
    payload: CommentCreate,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    issue = db.get(Issue, payload.issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    comment = Comment(
        content=sanitize_markdown(payload.content) or "",
        issue_id=payload.issue_id,
        author_id=current_user.id,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    audit_log(
        "comment_add",
        str(current_user.id),
        request.client.host if request.client else None,
        comment_id=str(comment.id),
        issue_id=str(issue.id),
    )
    return comment


@router.patch("/comments/{comment_id}", response_model=CommentOut)
def edit_comment(
    payload: CommentUpdate,
    request: Request,
    comment: Comment = Depends(require_comment_author),
    db: Session = Depends(deps.get_db),
):
    comment.content = sanitize_markdown(payload.content) or ""
    db.commit()
    db.refresh(comment)
    audit_log(
        "comment_edit",
        str(comment.author_id),
        request.client.host if request.client else None,
        comment_id=str(comment.id),
        issue_id=str(comment.issue_id),
    )
    return comment
