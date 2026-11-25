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

    # --- evidence files; a relative folder is inside backend/ ---
    upload_dir: str = "uploads"

    # --- daily backups (see app/scripts/backup.py); a relative folder is inside backend/ ---
    backup_dir: str = "backups"
    backup_keep: int = 14  # the newest backups kept; older ones are deleted
    pg_dump_path: str = "pg_dump"  # the full path when pg_dump is not on PATH

    # --- lockout and rate limiting ---
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    ip_failure_limit: int = 20
    ip_failure_window_minutes: int = 10

    # --- complainant sign-up codes (one-time passwords) ---
    otp_minutes: int = 10  # how long a code works
    otp_max_attempts: int = 5  # wrong guesses before a new code is needed
    otp_resend_seconds: int = 60  # wait before another code can be asked for

    # --- email (sign-up codes). Leave SMTP_HOST empty to keep codes in the backend terminal (development only). ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""  # shown as the sender; defaults to SMTP_USER
    smtp_ssl: bool = False  # True for port 465 (implicit SSL); False uses STARTTLS, normally on port 587

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
    def email_configured(self) -> bool:
        return bool(self.smtp_host and (self.smtp_from or self.smtp_user))

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
