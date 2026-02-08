from functools import lru_cache
from pathlib import Path
from cryptography.fernet import Fernet
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ai4b-bugtracker"
    env: str = "development"

    database_url: str = "postgresql+psycopg2://ai4b:ai4b@db:5432/bugtracker"
    redis_url: str = "redis://redis:6379/0"

    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    jwt_alg: str = "RS256"
    jwt_private_key_path: Path = Path("/run/secrets/jwt_private.pem")
    jwt_public_key_path: Path = Path("/run/secrets/jwt_public.pem")

    rate_limit_login: str = "3/minute"
    rate_limit_global: str = "100/minute"
    rate_limit_sensitive: str = "10/minute"
    password_min_length: int = 8
    password_complexity_regex: str = (
        r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[^A-Za-z0-9]).{8,}$"
    )

    cors_origins: str = "http://localhost:3000"
    cors_allow_methods: str = "GET,POST,PATCH,DELETE,OPTIONS"
    cors_allow_headers: str = "Authorization,Content-Type"
    cors_max_age: int = 600
    log_level: str = "INFO"
    pii_encryption_key: str | None = None
    pii_hash_key: str = "dev-only-pii-hash-key"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.env.lower() == "production" and not self.pii_encryption_key:
            raise ValueError("PII_ENCRYPTION_KEY is required in production")
        if self.pii_encryption_key:
            try:
                Fernet(self.pii_encryption_key.encode("utf-8"))
            except Exception as exc:
                raise ValueError(
                    "PII_ENCRYPTION_KEY must be a valid Fernet key"
                ) from exc
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_methods(self) -> list[str]:
        return [
            m.strip().upper() for m in self.cors_allow_methods.split(",") if m.strip()
        ]

    @property
    def allowed_headers(self) -> list[str]:
        return [h.strip() for h in self.cors_allow_headers.split(",") if h.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
