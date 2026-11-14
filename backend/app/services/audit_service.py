"""Writes the append-only audit trail (DB doc 5.1). One call, one row, in the caller's transaction."""

from typing import Any

from sqlalchemy.orm import Session

from app.core.enums import ComplaintStatus
from app.models import AuditLog
from app.services.auth_service import Principal


def record(
    db: Session,
    principal: Principal,
    *,
    action: str,  # for example complaint.forward
    entity_type: str,
    entity_id: int,
    complaint_id: int | None = None,
    from_status: ComplaintStatus | None = None,
    to_status: ComplaintStatus | None = None,
    reason: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Add the row; the caller commits it together with the change it describes."""
    is_staff = principal.kind == "staff"
    db.add(
        AuditLog(
            actor_user_id=principal.id if is_staff else None,
            actor_account_id=None if is_staff else principal.id,
            actor_role=principal.role,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            complaint_id=complaint_id,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            details=details,
        )
    )
