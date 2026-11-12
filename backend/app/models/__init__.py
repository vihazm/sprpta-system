"""Import every model here so Alembic and metadata.create_all see them."""

from app.models.area import Area
from app.models.audit_log import AuditLog
from app.models.auth_session import AuthSession
from app.models.complainant_account import ComplainantAccount
from app.models.complaint import (
    CaseDecision,
    Complaint,
    ComplaintAttachment,
    DuplicateCheck,
    Escalation,
    ImplementationRecord,
    SolutionDocument,
)
from app.models.health_check import HealthCheck
from app.models.health_event import HealthEvent
from app.models.master_data import (
    ComplaintCategory,
    ComplaintMedium,
    Permit,
    Person,
    RouteStand,
    Severity,
    Vehicle,
)
from app.models.messaging import MessageTemplate, OutboundMessage
from app.models.otp_code import OtpCode
from app.models.rating import RatingAppeal, RatingSnapshot
from app.models.recommendation import Recommendation
from app.models.system_setting import SystemSetting
from app.models.usage_log import UsageLog
from app.models.user import User

__all__ = [
    "Area",
    "AuditLog",
    "AuthSession",
    "CaseDecision",
    "ComplainantAccount",
    "Complaint",
    "ComplaintAttachment",
    "ComplaintCategory",
    "ComplaintMedium",
    "DuplicateCheck",
    "Escalation",
    "HealthCheck",
    "HealthEvent",
    "ImplementationRecord",
    "MessageTemplate",
    "OtpCode",
    "OutboundMessage",
    "Permit",
    "Person",
    "RatingAppeal",
    "RatingSnapshot",
    "Recommendation",
    "RouteStand",
    "Severity",
    "SolutionDocument",
    "SystemSetting",
    "UsageLog",
    "User",
    "Vehicle",
]
