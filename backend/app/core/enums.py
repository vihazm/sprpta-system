"""Fixed lists the code depends on (DB doc 1.2). Each is a PostgreSQL enumeration.

`user_role` lives in app.core.roles. The enumerations for the AI (RAG) module
(policy_version_status, ai_suggestion_status) are added with those tables.
"""

from enum import StrEnum


class ComplaintStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    INCOMPLETE = "incomplete"
    FORWARDED = "forwarded"
    UNDER_REVIEW = "under_review"
    AWAITING_IMPLEMENTATION = "awaiting_implementation"
    DONE_AWAITING_APPROVAL = "done_awaiting_approval"
    ESCALATED = "escalated"
    CLOSED = "closed"
    REJECTED = "rejected"


class RejectionType(StrEnum):
    INVALID = "invalid"
    SPAM = "spam"
    OUT_OF_JURISDICTION = "out_of_jurisdiction"
    DUPLICATE = "duplicate"


class DuplicateLinkType(StrEnum):
    NOT_DUPLICATE = "not_duplicate"
    DUPLICATE_OF = "duplicate_of"
    RELATED = "related"


class DecisionAction(StrEnum):
    WARNING = "warning"
    FINE = "fine"
    SUSPENSION = "suspension"
    LEGAL_ACTION = "legal_action"
    NO_ACTION = "no_action"


class DecisionOutcome(StrEnum):
    SUBSTANTIATED = "substantiated"
    PARTLY_SUBSTANTIATED = "partly_substantiated"
    NOT_SUBSTANTIATED = "not_substantiated"


class RecommendationType(StrEnum):
    IMPROVEMENT = "improvement"
    COMMENDATION = "commendation"


class RecommendationStatus(StrEnum):
    NEW = "new"
    ACKNOWLEDGED = "acknowledged"
    UNDER_CONSIDERATION = "under_consideration"
    ACCEPTED_IMPLEMENTED = "accepted_implemented"
    DECLINED = "declined"
    COMMENDATION_VERIFIED = "commendation_verified"


class MessageType(StrEnum):
    REGISTERED = "registered"
    DECIDED = "decided"
    CLOSED = "closed"
    OTP = "otp"


class MessageChannel(StrEnum):
    SMS = "sms"
    EMAIL = "email"


class MessageState(StrEnum):
    SENT = "sent"
    FAILED = "failed"


class PersonType(StrEnum):
    DRIVER = "driver"
    CONDUCTOR = "conductor"
    SPRPTA_STAFF = "sprpta_staff"
    OWNER = "owner"


class VehicleType(StrEnum):
    BUS = "bus"
    TRISHAW = "trishaw"


class PlaceKind(StrEnum):
    ROUTE = "route"
    STAND = "stand"


class RatingBand(StrEnum):
    EXCELLENT = "excellent"
    GOOD = "good"
    NEEDS_IMPROVEMENT = "needs_improvement"
    POOR = "poor"


class AppealStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
