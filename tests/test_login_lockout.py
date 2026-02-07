from app.models import User, UserRole
from app.services.security import hash_password


def seed_user(db):
    u = User(username="lock", email="lock@x.com", password_hash=hash_password("User123!"), role=UserRole.developer)
    db.add(u)
    db.commit()
    return u


def test_lockout_after_failures(client, db_session):
    seed_user(db_session)
    for _ in range(11):
        resp = client.post("/api/auth/login", json={"username": "lock", "password": "Wrong123!"})
    assert resp.status_code == 423
    # successful login resets counter? should still fail because locked window
    resp2 = client.post("/api/auth/login", json={"username": "lock", "password": "Wrong123!"})
    assert resp2.status_code == 423
