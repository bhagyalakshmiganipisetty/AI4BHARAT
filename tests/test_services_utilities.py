import logging
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.permissions import require_comment_author, require_project_manage
from app.core.metrics import MetricsStore
from app.models import Comment, Project, User, UserRole
from app.services import pii, security
from app.services.audit import audit_log
from app.services.token_store import InMemoryStore


def _make_user(role: UserRole, user_id=None, username="user") -> User:
    user = User(
        id=user_id or uuid4(), username=username, password_hash="hash", role=role
    )
    user.email = f"{username}@example.com"
    return user


def test_security_password_helpers():
    assert security.verify_password_complexity("Abc123!@")
    assert not security.verify_password_complexity("abc123!@")
    assert not security.verify_password_complexity("ABC123!@")
    assert not security.verify_password_complexity("Abcdef!@")
    assert not security.verify_password_complexity("Abc12345")
    assert not security.verify_password_complexity("Abc1234")

    hashed = security.hash_password("Abc123!@")
    assert security.verify_password("Abc123!@", hashed)
    assert not security.verify_password("Wrong123!", hashed)

    assert security.sanitize_markdown("<b>hi</b>") == "hi"
    assert security.mask_sensitive("secretvalue") == "secr***"
    assert security.mask_sensitive("abcd") == "****"
    assert security.mask_email("alice@example.com") == "a***@example.com"
    assert security.mask_email("not-email") == security.mask_sensitive("not-email")


def test_pii_helpers():
    assert pii.encrypt_pii("demo") == "demo"
    assert pii.decrypt_pii("demo") == "demo"
    assert pii.hash_pii("Test") == pii.hash_pii("test")
    assert len(pii.hash_pii("value")) == 64


def test_audit_log_masks_tokens(caplog):
    caplog.set_level(logging.INFO, logger="audit")
    audit_log("login", "user1", "127.0.0.1", token="secret123", note="ok")
    record = caplog.records[-1]
    details = record.event["details"]
    assert details["token"].startswith("secr")
    assert details["token"].endswith("***")
    assert details["note"] == "ok"


def test_metrics_store_snapshot():
    metrics = MetricsStore()
    metrics.record(200)
    metrics.record(500)
    snapshot = metrics.snapshot()
    assert snapshot["total_requests"] == 2
    assert snapshot["total_errors"] == 1
    assert snapshot["by_status"]["200"] == 1
    assert snapshot["by_status"]["500"] == 1


def test_inmemory_token_store_sessions():
    store = InMemoryStore()
    store.add("token", -1)
    assert not store.exists("token")

    assert store.inc_failure("user", window=60) == 1
    store.clear_failure("user")
    assert store.inc_failure("user", window=60) == 1

    store.add_refresh_session("u1", "jti1", 60)
    assert store.is_refresh_active("u1", "jti1")
    store.rotate_refresh_session("u1", "jti1", "jti2", 60)
    assert not store.is_refresh_active("u1", "jti1")
    assert store.is_refresh_active("u1", "jti2")
    store.remove_refresh_session("u1", "jti2")
    assert not store.is_refresh_active("u1", "jti2")

    store.add_refresh_session("u1", "jti3", 60)
    store.add_refresh_session("u1", "jti4", 60)
    assert set(store.list_refresh_sessions("u1")) == {"jti3", "jti4"}
    store.revoke_all_refresh("u1")
    assert store.list_refresh_sessions("u1") == []


def test_permission_helpers():
    creator_id = uuid4()
    project = Project(name="Demo", description="d", created_by_id=creator_id)
    admin = _make_user(UserRole.admin, username="admin")
    creator = _make_user(UserRole.developer, user_id=creator_id, username="creator")
    other = _make_user(UserRole.developer, username="other")

    assert require_project_manage(project, admin) is project
    assert require_project_manage(project, creator) is project
    with pytest.raises(HTTPException) as excinfo:
        require_project_manage(project, other)
    assert excinfo.value.status_code == 403

    comment = Comment(content="hi", issue_id=uuid4(), author_id=creator.id)
    assert require_comment_author(comment, creator) is comment
    with pytest.raises(HTTPException) as excinfo:
        require_comment_author(comment, other)
    assert excinfo.value.status_code == 403
