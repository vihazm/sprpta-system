"""The complaint core (DB doc section 3): the complaint and what happens to it.

Statuses and their transitions are enforced by the backend and each one is
written to audit_log. The checks below are a second line of defence.
"""

from datetime import date, datetime, timedelta

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Interval,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import (
    ComplaintStatus,
    DecisionAction,
    DecisionOutcome,
    DuplicateLinkType,
    RejectionType,
)
from app.db.base import Base
from app.db.types import (
    ComplaintStatusType,
    DecisionActionType,
    DecisionOutcomeType,
    DuplicateLinkTypeType,
    RejectionTypeType,
)

# Statuses from "forwarded" onward: the case has been routed to an L2 officer.
_ROUTED = "('forwarded', 'under_review', 'awaiting_implementation', 'done_awaiting_approval', 'escalated', 'closed')"


class Complaint(Base):
    """DB doc 3.1: one row per complaint, entered by L1 or submitted through the portal.

    Overdue is not stored: it is computed at read time from registered_at,
    paused_total, paused_since and the severity targets.
    """

    __tablename__ = "complaints"
    __table_args__ = (
        # A reference number exists for every status except draft, submitted
        # and a rejected row that never had one.
        CheckConstraint(
            "status IN ('draft', 'submitted', 'rejected') OR reference_number IS NOT NULL",
            name="reference_number_issued",
        ),
        CheckConstraint(
            f"status NOT IN {_ROUTED} OR (severity_id IS NOT NULL AND category_id IS NOT NULL "
            "AND medium_id IS NOT NULL AND vehicle_id IS NOT NULL AND area_id IS NOT NULL "
            "AND assigned_l2_user_id IS NOT NULL)",
            name="routed_has_details",
        ),
        CheckConstraint(
            "status <> 'rejected' OR (rejection_type IS NOT NULL AND rejection_reason IS NOT NULL)",
            name="rejected_has_reason",
        ),
        CheckConstraint(
            "rejection_type IS DISTINCT FROM 'duplicate' OR duplicate_of_complaint_id IS NOT NULL",
            name="duplicate_has_earlier_case",
        ),
        CheckConstraint(
            "NOT is_anonymous OR (complainant_name IS NULL AND contact_phone IS NULL "
            "AND contact_email IS NULL)",
            name="anonymous_has_no_contact",
        ),
        Index("ix_complaints_status", "status"),
        Index("ix_complaints_area_status", "area_id", "status"),
        Index("ix_complaints_l2_officer_status", "assigned_l2_user_id", "status"),
        Index("ix_complaints_vehicle", "vehicle_id"),
        Index("ix_complaints_subject_person", "subject_person_id"),
        Index("ix_complaints_complainant_account", "complainant_account_id"),
        Index("ix_complaints_severity_registered", "severity_id", "registered_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    # Issued at forwarding or when saved as Incomplete. Format SPRPTA-YYYY-NNNNNN is proposed.
    reference_number: Mapped[str | None] = mapped_column(Text, unique=True)
    status: Mapped[ComplaintStatus] = mapped_column(ComplaintStatusType, server_default="draft")
    submitted_via_portal: Mapped[bool] = mapped_column(Boolean, server_default=false())
    complainant_account_id: Mapped[int | None] = mapped_column(ForeignKey("complainant_accounts.id"))
    entered_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # the L1 who entered it
    checked_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # the L1 who checked a portal submission
    medium_id: Mapped[int | None] = mapped_column(ForeignKey("complaint_mediums.id"))
    is_anonymous: Mapped[bool] = mapped_column(Boolean, server_default=false())
    complainant_name: Mapped[str | None] = mapped_column(Text)
    contact_phone: Mapped[str | None] = mapped_column(Text)
    contact_email: Mapped[str | None] = mapped_column(Text)
    complaint_date: Mapped[date | None] = mapped_column(Date)  # incident or receipt date: still to be confirmed
    subject: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("complaint_categories.id"))
    severity_id: Mapped[int | None] = mapped_column(ForeignKey("severities.id"))
    # The person the complaint is about; the rating attaches to this.
    subject_person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    subject_person_text: Mapped[str | None] = mapped_column(Text)  # name as written when no record matches
    vehicle_number_entered: Mapped[str | None] = mapped_column(Text)  # number as typed
    vehicle_id: Mapped[int | None] = mapped_column(ForeignKey("vehicles.id"))
    permit_id: Mapped[int | None] = mapped_column(ForeignKey("permits.id"))
    owner_person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    route_stand_id: Mapped[int | None] = mapped_column(ForeignKey("routes_stands.id"))
    area_id: Mapped[int | None] = mapped_column(ForeignKey("areas.id"))  # copied from the vehicle's registered area
    assigned_l2_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    rejection_type: Mapped[RejectionType | None] = mapped_column(RejectionTypeType)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    duplicate_of_complaint_id: Mapped[int | None] = mapped_column(ForeignKey("complaints.id"))
    registered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # starts the time-target clock
    forwarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    paused_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # set while Incomplete
    paused_total: Mapped[timedelta] = mapped_column(Interval, server_default=text("interval '0'"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ComplaintAttachment(Base):
    """DB doc 3.2: evidence attached to a complaint. Removal is soft (removed_at)."""

    __tablename__ = "complaint_attachments"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(uploaded_by_user_id, uploaded_by_account_id) = 1",
            name="one_uploader",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"))
    file_name: Mapped[str] = mapped_column(Text)
    storage_path: Mapped[str] = mapped_column(Text)  # location in file storage
    mime_type: Mapped[str] = mapped_column(Text)
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    description: Mapped[str | None] = mapped_column(Text)  # for example "original message"
    uploaded_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    uploaded_by_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("complainant_accounts.id", name="fk_complaint_attachments_uploaded_by_account_id_accounts")
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # only while Draft, Incomplete or Submitted
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DuplicateCheck(Base):
    """DB doc 3.3: L1's decision on each possible duplicate. Nothing is merged or deleted."""

    __tablename__ = "duplicate_checks"
    __table_args__ = (
        UniqueConstraint("complaint_id", "candidate_complaint_id", name="uq_duplicate_checks_complaint_candidate"),
        CheckConstraint("complaint_id <> candidate_complaint_id", name="not_itself"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"))  # the complaint being registered
    candidate_complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"))  # the earlier case shown
    link_type: Mapped[DuplicateLinkType] = mapped_column(DuplicateLinkTypeType)
    decided_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Escalation(Base):
    """DB doc 3.4: L2 passes a case to L3. A case is escalated at most once and never returns."""

    __tablename__ = "escalations"
    __table_args__ = (CheckConstraint("length(reason) > 0", name="reason_not_empty"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), unique=True)
    escalated_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # the L2 officer
    reason: Mapped[str] = mapped_column(Text)
    escalated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CaseDecision(Base):
    """DB doc 3.5: the decision by L2, or by L3 on an escalated case.

    ai_suggestion_id has no foreign key yet: the table it points to belongs to
    the AI (RAG) module, which is not built. The key is added with that table.
    """

    __tablename__ = "case_decisions"
    __table_args__ = (
        CheckConstraint("ai_suggestion_id IS NOT NULL OR ai_followed IS NULL", name="followed_needs_suggestion"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), unique=True)  # one decision per complaint
    decided_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # L2 or L3
    action: Mapped[DecisionAction] = mapped_column(DecisionActionType)
    reasoning: Mapped[str] = mapped_column(Text)
    outcome: Mapped[DecisionOutcome] = mapped_column(DecisionOutcomeType)  # feeds the rating
    ai_suggestion_id: Mapped[int | None] = mapped_column(BigInteger)
    ai_followed: Mapped[bool | None] = mapped_column(Boolean)  # null when no suggestion was requested
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SolutionDocument(Base):
    """DB doc 3.6: the PDF generated from the decision (case ID, summary, verdict)."""

    __tablename__ = "solution_documents"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), unique=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("case_decisions.id"))
    summary_text: Mapped[str] = mapped_column(Text)  # complaint summary printed on the PDF
    verdict_text: Mapped[str] = mapped_column(Text)  # verdict printed on the PDF
    solution_details: Mapped[str | None] = mapped_column(Text)  # free text from the form
    pdf_path: Mapped[str] = mapped_column(Text)  # generated PDF in file storage
    generated_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImplementationRecord(Base):
    """DB doc 3.7: the ground-level "Mark as done" and the approval that closes the case."""

    __tablename__ = "implementation_records"
    __table_args__ = (
        CheckConstraint(
            "(approved_by_user_id IS NULL) = (approved_at IS NULL)",
            name="approval_complete",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), unique=True)
    solution_document_id: Mapped[int] = mapped_column(
        ForeignKey("solution_documents.id", name="fk_implementation_records_solution_document_id_solution_docs")
    )
    done_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # implementing staff, shown as "done by"
    done_note: Mapped[str] = mapped_column(Text)  # how it was carried out
    done_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    approved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # L2, or L3 for its own cases
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # closes the case
