import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)
user_id_ctx: ContextVar[str | None] = ContextVar("user_id", default=None)
client_ip_ctx: ContextVar[str | None] = ContextVar("client_ip", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_ctx.get()
        user_id = user_id_ctx.get()
        client_ip = client_ip_ctx.get()
        if request_id:
            payload["request_id"] = request_id
        if user_id:
            payload["user_id"] = user_id
        if client_ip:
            payload["client_ip"] = client_ip
        event = getattr(record, "event", None)
        if event is not None:
            payload["event"] = event
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
