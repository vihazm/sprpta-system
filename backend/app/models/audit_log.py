from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, Index, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import ComplaintStatus
from app.db.base import Base
from app.db.types import ComplaintStatusType


class AuditLog(Base):
    """DB doc 5.1: the append-only audit trail. Every action and status transition is one row.

    Append-only is enforced in the database: a trigger (see migration 0003)
    raises an error on any UPDATE or DELETE. The application's database role
    should also be limited to INSERT and SELECT on this table.
    """

    __tablename__ = "audit_log"
    __table_args__ = (
        Index("ix_audit_log_complaint_occurred", "complaint_id", "occurred_at"),
        Index("ix_audit_log_actor_user_occurred", "actor_user_id", "occurred_at"),
        Index("ix_audit_log_action", "action"),
    )

    # The identity gives a strict order; occurred_at is the real (not transaction) server time.
    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.clock_timestamp())
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # null for system or complainant actions
    actor_account_id: Mapped[int | None] = mapped_column(ForeignKey("complainant_accounts.id"))  # set for portal actions
    actor_role: Mapped[str] = mapped_column(Text)  # role at the time, or "system"
    action: Mapped[str] = mapped_column(Text)  # for example complaint.forward, decision.create
    entity_type: Mapped[str] = mapped_column(Text)  # table or object acted on
    entity_id: Mapped[int | None] = mapped_column(BigInteger)
    complaint_id: Mapped[int | None] = mapped_column(ForeignKey("complaints.id"))  # set when the row concerns a case
    from_status: Mapped[ComplaintStatus | None] = mapped_column(ComplaintStatusType)
    to_status: Mapped[ComplaintStatus | None] = mapped_column(ComplaintStatusType)
    reason: Mapped[str | None] = mapped_column(Text)  # mandatory reasons (reject, escalate, re-link) are copied here
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB)  # old and new values for edits and corrections
