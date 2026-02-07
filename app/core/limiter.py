from app.core.config import settings


class _NoopLimiter:
    def limit(self, *_args, **_kwargs):
        def decorator(func):
            return func

        return decorator


if settings.env.lower() == "test":
    limiter = _NoopLimiter()
else:
    from slowapi import Limiter
    from slowapi.util import get_remote_address

    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[settings.rate_limit_global],
        headers_enabled=False,
    )
