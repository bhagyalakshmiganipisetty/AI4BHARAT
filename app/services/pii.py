import hashlib
import hmac
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _get_fernet() -> Optional[Fernet]:
    key = settings.pii_encryption_key
    if not key:
        return None
    if isinstance(key, str):
        key_bytes = key.encode("utf-8")
    else:
        key_bytes = key
    return Fernet(key_bytes)


def encrypt_pii(value: str) -> str:
    fernet = _get_fernet()
    if not fernet:
        return value
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_pii(value: str) -> str:
    fernet = _get_fernet()
    if not fernet:
        return value
    try:
        return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return value


def hash_pii(value: str) -> str:
    key = settings.pii_hash_key.encode("utf-8")
    return hmac.new(key, value.lower().encode("utf-8"), hashlib.sha256).hexdigest()
