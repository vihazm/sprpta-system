"""Import every model here so Alembic and metadata.create_all see them."""

from app.models.area import Area
from app.models.auth_session import AuthSession
from app.models.complainant_account import ComplainantAccount
from app.models.health_check import HealthCheck
from app.models.health_event import HealthEvent
from app.models.usage_log import UsageLog
from app.models.user import User

__all__ = [
    "Area",
    "AuthSession",
    "ComplainantAccount",
    "HealthCheck",
    "HealthEvent",
    "UsageLog",
    "User",
]
