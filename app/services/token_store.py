"""Token blacklist/rotation store with Redis fallback."""
from __future__ import annotations

import time
from typing import Protocol

import redis

from app.core.config import settings


class Store(Protocol):
    def add(self, token: str, ttl_seconds: int) -> None: ...
    def exists(self, token: str) -> bool: ...
    def inc_failure(self, key: str, window: int) -> int: ...
    def clear_failure(self, key: str) -> None: ...
    def add_refresh_session(self, user_id: str, jti: str, ttl_seconds: int) -> None: ...
    def rotate_refresh_session(self, user_id: str, old_jti: str, new_jti: str, ttl_seconds: int) -> None: ...
    def remove_refresh_session(self, user_id: str, jti: str) -> None: ...
    def is_refresh_active(self, user_id: str, jti: str) -> bool: ...
    def revoke_all_refresh(self, user_id: str) -> None: ...
    def list_refresh_sessions(self, user_id: str) -> list[str]: ...
    def set_access_revoked_at(self, user_id: str, revoked_at: int, ttl_seconds: int) -> None: ...
    def get_access_revoked_at(self, user_id: str) -> int | None: ...


class InMemoryStore:
    def __init__(self):
        self._data: dict[str, float] = {}
        self._fails: dict[str, tuple[int, float]] = {}
        self._refresh: dict[str, dict[str, float]] = {}
        self._access_revoked: dict[str, tuple[int, float]] = {}

    def add(self, token: str, ttl_seconds: int) -> None:
        self._data[token] = time.time() + ttl_seconds

    def exists(self, token: str) -> bool:
        now = time.time()
        expired = [k for k, exp in self._data.items() if exp <= now]
        for k in expired:
            self._data.pop(k, None)
        return token in self._data

    def inc_failure(self, key: str, window: int) -> int:
        now = time.time()
        count, expiry = self._fails.get(key, (0, now + window))
        if expiry < now:
            count = 0
            expiry = now + window
        count += 1
        self._fails[key] = (count, expiry)
        return count

    def clear_failure(self, key: str) -> None:
        self._fails.pop(key, None)

    def add_refresh_session(self, user_id: str, jti: str, ttl_seconds: int) -> None:
        self._refresh.setdefault(user_id, {})[jti] = time.time() + ttl_seconds

    def rotate_refresh_session(self, user_id: str, old_jti: str, new_jti: str, ttl_seconds: int) -> None:
        self.remove_refresh_session(user_id, old_jti)
        self.add_refresh_session(user_id, new_jti, ttl_seconds)

    def remove_refresh_session(self, user_id: str, jti: str) -> None:
        sessions = self._refresh.get(user_id, {})
        sessions.pop(jti, None)
        if not sessions:
            self._refresh.pop(user_id, None)

    def is_refresh_active(self, user_id: str, jti: str) -> bool:
        now = time.time()
        sessions = self._refresh.get(user_id)
        if not sessions:
            return False
        expired = [k for k, exp in sessions.items() if exp <= now]
        for k in expired:
            sessions.pop(k, None)
        if not sessions:
            self._refresh.pop(user_id, None)
        return jti in sessions

    def revoke_all_refresh(self, user_id: str) -> None:
        self._refresh.pop(user_id, None)

    def list_refresh_sessions(self, user_id: str) -> list[str]:
        sessions = self._refresh.get(user_id, {})
        now = time.time()
        active = [jti for jti, exp in sessions.items() if exp > now]
        self._refresh[user_id] = {jti: sessions[jti] for jti in active}
        return active

    def set_access_revoked_at(self, user_id: str, revoked_at: int, ttl_seconds: int) -> None:
        self._access_revoked[user_id] = (revoked_at, time.time() + ttl_seconds)

    def get_access_revoked_at(self, user_id: str) -> int | None:
        data = self._access_revoked.get(user_id)
        if not data:
            return None
        revoked_at, expires_at = data
        if expires_at <= time.time():
            self._access_revoked.pop(user_id, None)
            return None
        return revoked_at


class RedisStore:
    def __init__(self, url: str):
        self.client = redis.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )

    def add(self, token: str, ttl_seconds: int) -> None:
        self.client.setex(f"blacklist:{token}", ttl_seconds, "1")

    def exists(self, token: str) -> bool:
        return bool(self.client.get(f"blacklist:{token}"))

    def inc_failure(self, key: str, window: int) -> int:
        redis_key = f"loginfail:{key}"
        pipe = self.client.pipeline()
        pipe.incr(redis_key)
        pipe.expire(redis_key, window)
        count, _ = pipe.execute()
        return int(count)

    def clear_failure(self, key: str) -> None:
        self.client.delete(f"loginfail:{key}")

    def add_refresh_session(self, user_id: str, jti: str, ttl_seconds: int) -> None:
        key = f"refresh:{user_id}:{jti}"
        set_key = f"refreshset:{user_id}"
        pipe = self.client.pipeline()
        pipe.setex(key, ttl_seconds, "1")
        pipe.sadd(set_key, jti)
        pipe.expire(set_key, ttl_seconds)
        pipe.execute()

    def rotate_refresh_session(self, user_id: str, old_jti: str, new_jti: str, ttl_seconds: int) -> None:
        self.remove_refresh_session(user_id, old_jti)
        self.add_refresh_session(user_id, new_jti, ttl_seconds)

    def remove_refresh_session(self, user_id: str, jti: str) -> None:
        key = f"refresh:{user_id}:{jti}"
        set_key = f"refreshset:{user_id}"
        pipe = self.client.pipeline()
        pipe.delete(key)
        pipe.srem(set_key, jti)
        pipe.execute()

    def is_refresh_active(self, user_id: str, jti: str) -> bool:
        key = f"refresh:{user_id}:{jti}"
        return bool(self.client.get(key))

    def revoke_all_refresh(self, user_id: str) -> None:
        set_key = f"refreshset:{user_id}"
        jtis = self.client.smembers(set_key)
        if not jtis:
            return
        pipe = self.client.pipeline()
        for jti in jtis:
            pipe.delete(f"refresh:{user_id}:{jti}")
        pipe.delete(set_key)
        pipe.execute()

    def list_refresh_sessions(self, user_id: str) -> list[str]:
        set_key = f"refreshset:{user_id}"
        jtis = list(self.client.smembers(set_key))
        active = []
        for jti in jtis:
            if self.is_refresh_active(user_id, jti):
                active.append(jti)
            else:
                self.client.srem(set_key, jti)
        return active

    def set_access_revoked_at(self, user_id: str, revoked_at: int, ttl_seconds: int) -> None:
        self.client.setex(f"accessrevoked:{user_id}", ttl_seconds, str(revoked_at))

    def get_access_revoked_at(self, user_id: str) -> int | None:
        value = self.client.get(f"accessrevoked:{user_id}")
        return int(value) if value else None


def get_store() -> Store:
    try:
        store = RedisStore(settings.redis_url)
        store.client.ping()
        return store
    except Exception:
        return InMemoryStore()


store: Store = get_store()
