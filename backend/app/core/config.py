"""Application settings, read from environment variables or backend/.env."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_WEAK_SECRETS = {"", "change-me", "changeme", "secret"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"  # development | production
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/sprpta_db"

    # --- JWT / sessions (values agreed in the login plan) ---
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "sprpta-api"
    jwt_audience: str = "sprpta-web"
    access_token_minutes: int = 15
    session_idle_minutes: int = 30
    session_absolute_hours: int = 12
    refresh_grace_seconds: int = 10

    # --- health checks: where the web app can be reached from the backend ---
    web_url: str = "http://localhost:3000"

    # --- lockout and rate limiting ---
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    ip_failure_limit: int = 20
    ip_failure_window_minutes: int = 10

    # --- cookies and CSRF ---
    cookie_secure: bool | None = None  # None = secure outside development
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    # The backend sits behind the Next.js proxy, which appends the real client
    # IP to X-Forwarded-For. Only enable while the backend is not reachable
    # directly from the internet.
    trust_forwarded_for: bool = True

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def secure_cookies(self) -> bool:
        if self.cookie_secure is not None:
            return self.cookie_secure
        return not self.is_development

    def validate_for_startup(self) -> None:
        if self.jwt_secret in _WEAK_SECRETS or len(self.jwt_secret) < 32:
            raise RuntimeError(
                "JWT_SECRET is missing or too short (need at least 32 characters). "
                "Set it in backend/.env. Generate one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
