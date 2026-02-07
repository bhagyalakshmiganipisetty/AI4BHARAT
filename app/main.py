import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, Response
from app.api.routes import auth, projects, issues, comments
from app.core.config import settings
from app.core.logging import client_ip_ctx, configure_logging, request_id_ctx
from app.core.limiter import limiter
from app.core.metrics import metrics

configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name)
rate_limit_enabled = settings.env.lower() != "test"
if rate_limit_enabled:
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
    max_age=settings.cors_max_age,
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    request_id_ctx.set(request_id)
    if request.client:
        client_ip_ctx.set(request.client.host)
    start = time.monotonic()
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    duration_ms = int((time.monotonic() - start) * 1000)
    logging.getLogger("access").info(
        "request",
        extra={
            "event": {
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }
        },
    )
    metrics.record(response.status_code)
    return response


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers.setdefault("Content-Security-Policy", "default-src 'self'")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("X-XSS-Protection", "1; mode=block")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if settings.env.lower() == "production":
        response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
    return response


@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > 1_000_000:
        return JSONResponse(
            status_code=413,
            content={
                "error": {
                    "code": "payload_too_large",
                    "message": "Request body too large",
                    "request_id": getattr(request.state, "request_id", None),
                }
            },
        )
    return await call_next(request)


@app.middleware("http")
async def enforce_json_content_type(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH"}:
        content_length = request.headers.get("content-length")
        has_body = False
        if content_length:
            try:
                has_body = int(content_length) > 0
            except ValueError:
                has_body = False
        if has_body:
            content_type = request.headers.get("content-type", "")
            media_type = content_type.split(";")[0].strip().lower()
            if media_type != "application/json":
                return JSONResponse(
                    status_code=415,
                    content={
                        "error": {
                            "code": "unsupported_media_type",
                            "message": "Content-Type must be application/json",
                            "request_id": getattr(request.state, "request_id", None),
                        }
                    },
                )
    return await call_next(request)


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    return {"status": "ready"}


@app.get("/metrics")
def metrics_endpoint():
    return metrics.snapshot()


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logging.getLogger("app").exception(
        "Unhandled exception",
        extra={
            "event": {
                "method": request.method,
                "path": request.url.path,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )
    message = "Internal server error"
    details = None
    if settings.env.lower() != "production":
        message = f"{exc.__class__.__name__}: {exc}"
        details = [{"type": exc.__class__.__name__}]
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_server_error",
                "message": message,
                "request_id": getattr(request.state, "request_id", None),
                "details": details,
            }
        },
    )


async def rate_limit_handler(request: Request, exc: Exception):
    retry_after = None
    detail = getattr(exc, "detail", None)
    if isinstance(detail, dict):
        if "retry_after" in detail:
            retry_after = int(detail["retry_after"])
        elif "reset" in detail:
            retry_after = max(0, int(detail["reset"] - time.time()))
    headers = {}
    if retry_after is not None:
        headers["Retry-After"] = str(retry_after)
    return JSONResponse(
        status_code=429,
        headers=headers,
        content={
            "error": {
                "code": "rate_limited",
                "message": "Too many requests",
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


if rate_limit_enabled:
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Validation error",
                "details": exc.errors(),
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"http_{exc.status_code}",
                "message": exc.detail,
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


app.include_router(auth.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(issues.router, prefix="/api")
app.include_router(comments.router, prefix="/api")
