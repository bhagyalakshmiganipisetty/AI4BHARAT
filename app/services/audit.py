import logging
from typing import Any

from app.services.security import mask_sensitive


logger = logging.getLogger("audit")


def audit_log(event: str, user_id: str | None, ip: str | None, **details: Any) -> None:
    safe_details = {}
    for key, value in details.items():
        if key in {"token", "access_token", "refresh_token", "password"} and isinstance(
            value, str
        ):
            safe_details[key] = mask_sensitive(value)
        else:
            safe_details[key] = value
    payload = {
        "event": event,
        "user_id": user_id,
        "ip": ip,
        "details": safe_details,
    }
    logger.info("audit", extra={"event": payload})
