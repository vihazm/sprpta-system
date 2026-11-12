"""The core tables of the Database Structure Document: columns and database-level rules."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.core.enums import (
    ComplaintStatus,
    DecisionAction,
    DecisionOutcome,
    DuplicateLinkType,
    MessageChannel,
    MessageState,
    MessageType,
    PersonType,
    RatingBand,
    RecommendationStatus,
    RecommendationType,
    RejectionType,
    VehicleType,
)
from app.core.roles import UserRole
from app.models import (
    Area,
    AuditLog,
    CaseDecision,
    Complaint,
    ComplaintAttachment,
    ComplaintCategory,
    ComplaintMedium,
    DuplicateCheck,
    Escalation,
    ImplementationRecord,
    MessageTemplate,
    OtpCode,
    OutboundMessage,
    Permit,
    Person,
    RatingAppeal,
    RatingSnapshot,
    Recommendation,
    RouteStand,
    Severity,
    SolutionDocument,
    SystemSetting,
    Vehicle,
)
from tests.conftest import make_complainant, make_user

# Every non-AI table of the document with its columns, in the document's order.
# created_at / updated_at close the list where the document gives them.
TS = ["created_at", "updated_at"]
EXPECTED_COLUMNS = {
    "otp_codes": ["id", "complainant_account_id", "channel", "code_hash", "expires_at", "attempts", "consumed_at", "created_at"],
    "routes_stands": ["id", "kind", "name", "area_id", "is_active", *TS],
    "vehicles": ["id", "vehicle_number", "vehicle_type", "registered_area_id", "owner_person_id", "is_active", *TS],
    "permits": ["id", "permit_number", "vehicle_id", "holder_person_id", "is_active", *TS],
    "people": ["id", "full_name", "person_type", "staff_number", "phone", "team_label", "is_active", *TS],
    "complaint_categories": ["id", "name", "description", "is_active", *TS],
    "severities": ["id", "name", "rank", "forward_days", "decide_days", "close_days", "rating_weight", "is_active", *TS],
    "complaint_mediums": ["id", "name", "is_system", "is_active", *TS],
    "complaints": [
        "id", "reference_number", "status", "submitted_via_portal", "complainant_account_id", "entered_by_user_id",
        "checked_by_user_id", "medium_id", "is_anonymous", "complainant_name", "contact_phone", "contact_email",
        "complaint_date", "subject", "description", "category_id", "severity_id", "subject_person_id",
        "subject_person_text", "vehicle_number_entered", "vehicle_id", "permit_id", "owner_person_id",
        "route_stand_id", "area_id", "assigned_l2_user_id", "rejection_type", "rejection_reason",
        "duplicate_of_complaint_id", "registered_at", "forwarded_at", "review_started_at", "decided_at",
        "escalated_at", "done_at", "closed_at", "rejected_at", "paused_since", "paused_total", *TS,
    ],
    "complaint_attachments": [
        "id", "complaint_id", "file_name", "storage_path", "mime_type", "size_bytes", "description",
        "uploaded_by_user_id", "uploaded_by_account_id", "removed_at", "created_at",
    ],
    "duplicate_checks": ["id", "complaint_id", "candidate_complaint_id", "link_type", "decided_by_user_id", "decided_at"],
    "escalations": ["id", "complaint_id", "escalated_by_user_id", "reason", "escalated_at"],
    "case_decisions": [
        "id", "complaint_id", "decided_by_user_id", "action", "reasoning", "outcome", "ai_suggestion_id",
        "ai_followed", "decided_at",
    ],
    "solution_documents": [
        "id", "complaint_id", "decision_id", "summary_text", "verdict_text", "solution_details", "pdf_path",
        "generated_by_user_id", "generated_at",
    ],
    "implementation_records": [
        "id", "complaint_id", "solution_document_id", "done_by_user_id", "done_note", "done_at",
        "approved_by_user_id", "approved_at",
    ],
    "recommendations": [
        "id", "recommendation_type", "status", "title", "details", "medium_id", "received_date",
        "subject_person_id", "entered_by_user_id", "status_changed_by_user_id", "status_changed_at",
        "verified_at", *TS,
    ],
    "message_templates": ["id", "message_type", "channel", "subject", "body", "is_active", "updated_by_user_id", *TS],
    "outbound_messages": [
        "id", "complaint_id", "complainant_account_id", "message_type", "channel", "recipient", "body", "state",
        "error_detail", "attempted_at",
    ],
    "audit_log": [
        "id", "occurred_at", "actor_user_id", "actor_account_id", "actor_role", "action", "entity_type",
        "entity_id", "complaint_id", "from_status", "to_status", "reason", "details",
    ],
    "system_settings": ["key", "value", "description", "updated_by_user_id", "updated_at"],
    "rating_snapshots": [
        "id", "person_id", "computed_at", "window_start", "window_end", "penalty", "credits", "score", "band",
        "formula_version", "breakdown", "trigger",
    ],
    "rating_appeals": [
        "id", "person_id", "complaint_id", "reason", "status", "recorded_by_user_id", "lodged_at",
        "resolved_by_user_id", "resolved_at", "resolution", "snapshot_before_id", "snapshot_after_id",
    ],
}


def test_every_table_has_the_documented_columns(db):
    inspector = inspect(db.get_bind())
    for table, columns in EXPECTED_COLUMNS.items():
        assert [c["name"] for c in inspector.get_columns(table)] == columns, table


def test_ids_are_always_generated_identities(db):
    inspector = inspect(db.get_bind())
    for table in EXPECTED_COLUMNS:
        if table == "system_settings":
            continue  # keyed by name
        id_column = next(c for c in inspector.get_columns(table) if c["name"] == "id")
        assert id_column["identity"]["always"] is True, table


def test_the_ai_tables_are_not_built_yet(db):
    names = set(inspect(db.get_bind()).get_table_names())
    for table in ("policy_documents", "policy_versions", "policy_clauses", "ai_suggestions", "ai_suggestion_clauses"):
        assert table not in names


# ------------------------------------------------------------------ helpers


def _commit_fails(db, *rows):
    db.add_all(rows)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


@pytest.fixture
def staff(db, galle):
    return {
        "l1": make_user(db, "l1@sprpta.test", UserRole.L1),
        "l2": make_user(db, "l2@sprpta.test", UserRole.L2, area_id=galle.id),
        "l3": make_user(db, "l3@sprpta.test", UserRole.L3),
        "is": make_user(db, "is@sprpta.test", UserRole.IMPLEMENTING_STAFF),
    }


@pytest.fixture
def routing(db, galle):
    """Everything a forwarded complaint points at."""
    severity = Severity(name="High", rank=2, forward_days=1, decide_days=3, close_days=7, rating_weight=4)
    category = ComplaintCategory(name="Rude behaviour")
    medium = ComplaintMedium(name="Email")
    owner = Person(full_name="Owner One", person_type=PersonType.OWNER)
    db.add_all([severity, category, medium, owner])
    db.commit()
    vehicle = Vehicle(
        vehicle_number="NB-1234", vehicle_type=VehicleType.BUS, registered_area_id=galle.id, owner_person_id=owner.id
    )
    db.add(vehicle)
    db.commit()
    return {"severity": severity, "category": category, "medium": medium, "vehicle": vehicle, "area": galle}


def _forwarded(staff, routing, **extra) -> Complaint:
    return Complaint(
        status=ComplaintStatus.FORWARDED,
        reference_number=extra.pop("reference_number", "SPRPTA-2026-000001"),
        severity_id=routing["severity"].id,
        category_id=routing["category"].id,
        medium_id=routing["medium"].id,
        vehicle_id=routing["vehicle"].id,
        area_id=routing["area"].id,
        assigned_l2_user_id=staff["l2"].id,
        **extra,
    )


@pytest.fixture
def complaint(db, staff, routing) -> Complaint:
    row = _forwarded(staff, routing)
    db.add(row)
    db.commit()
    return row


# ------------------------------------------------------------------ master data


def test_master_data_defaults_and_uniqueness(db, galle):
    medium = ComplaintMedium(name="Portal", is_system=True)
    plain = ComplaintMedium(name="Letter")
    db.add_all([medium, plain])
    db.commit()
    assert medium.is_system is True and plain.is_system is False and plain.is_active is True
    _commit_fails(db, ComplaintMedium(name="Portal"))
    _commit_fails(db, Vehicle(vehicle_number="A", vehicle_type=VehicleType.BUS, registered_area_id=galle.id),
                  Vehicle(vehicle_number="A", vehicle_type=VehicleType.BUS, registered_area_id=galle.id))


def test_vehicle_needs_a_registered_area(db):
    _commit_fails(db, Vehicle(vehicle_number="NB-1", vehicle_type=VehicleType.BUS))


def test_route_or_stand_is_unique_within_an_area(db, galle):
    db.add(RouteStand(kind="route", name="Galle to Matara", area_id=galle.id))
    db.commit()
    _commit_fails(db, RouteStand(kind="route", name="Galle to Matara", area_id=galle.id))
    db.add(RouteStand(kind="stand", name="Galle to Matara", area_id=galle.id))  # a different kind is fine
    db.commit()


def test_permit_belongs_to_a_vehicle(db, routing):
    db.add(Permit(permit_number="P-1", vehicle_id=routing["vehicle"].id))
    db.commit()
    _commit_fails(db, Permit(permit_number="P-1", vehicle_id=routing["vehicle"].id))
    _commit_fails(db, Permit(permit_number="P-2"))


def test_severity_names_are_unique(db):
    db.add(Severity(name="Low", rank=4, forward_days=3, decide_days=14, close_days=30, rating_weight=1))
    db.commit()
    _commit_fails(db, Severity(name="Low", rank=5, forward_days=1, decide_days=1, close_days=1, rating_weight=1))


# ------------------------------------------------------------------ complaints


def test_a_draft_needs_nothing_else(db):
    row = Complaint()
    db.add(row)
    db.commit()
    assert row.status == ComplaintStatus.DRAFT
    assert row.reference_number is None
    assert row.is_anonymous is False and row.submitted_via_portal is False
    assert str(row.paused_total) == "0:00:00"
    assert row.created_at is not None and row.updated_at is not None


def test_forwarded_needs_routing_details(db, staff, routing):
    db.add(_forwarded(staff, routing))
    db.commit()
    broken = _forwarded(staff, routing, reference_number="SPRPTA-2026-000002")
    broken.vehicle_id = None
    _commit_fails(db, broken)
    no_officer = _forwarded(staff, routing, reference_number="SPRPTA-2026-000003")
    no_officer.assigned_l2_user_id = None
    _commit_fails(db, no_officer)


def test_reference_number_is_required_after_draft_and_submitted(db):
    _commit_fails(db, Complaint(status=ComplaintStatus.INCOMPLETE))
    db.add_all([Complaint(status=ComplaintStatus.SUBMITTED), Complaint(status=ComplaintStatus.DRAFT)])
    db.commit()
    db.add(Complaint(status=ComplaintStatus.INCOMPLETE, reference_number="SPRPTA-2026-000010"))
    db.commit()


def test_reference_numbers_are_unique(db):
    db.add(Complaint(status=ComplaintStatus.INCOMPLETE, reference_number="SPRPTA-2026-000020"))
    db.commit()
    _commit_fails(db, Complaint(status=ComplaintStatus.INCOMPLETE, reference_number="SPRPTA-2026-000020"))


def test_rejection_needs_a_type_and_a_reason(db):
    _commit_fails(db, Complaint(status=ComplaintStatus.REJECTED))
    _commit_fails(db, Complaint(status=ComplaintStatus.REJECTED, rejection_type=RejectionType.SPAM))
    db.add(Complaint(status=ComplaintStatus.REJECTED, rejection_type=RejectionType.SPAM, rejection_reason="Spam"))
    db.commit()


def test_a_duplicate_rejection_names_the_earlier_case(db, complaint):
    _commit_fails(
        db,
        Complaint(status=ComplaintStatus.REJECTED, rejection_type=RejectionType.DUPLICATE, rejection_reason="Same"),
    )
    db.add(
        Complaint(
            status=ComplaintStatus.REJECTED,
            rejection_type=RejectionType.DUPLICATE,
            rejection_reason="Same",
            duplicate_of_complaint_id=complaint.id,
        )
    )
    db.commit()


def test_an_anonymous_complaint_has_no_contact(db):
    _commit_fails(db, Complaint(is_anonymous=True, complainant_name="Someone"))
    _commit_fails(db, Complaint(is_anonymous=True, contact_email="a@b.lk"))
    db.add(Complaint(is_anonymous=True))
    db.commit()


def test_complaint_text_accepts_sinhala_and_tamil(db):
    row = Complaint(subject="බස් රථය", description="பேருந்து சேவை", complainant_name="Kasun")
    db.add(row)
    db.commit()
    db.refresh(row)
    assert row.subject == "බස් රථය" and row.description == "பேருந்து சேவை"


def test_complaints_have_the_documented_indexes(db):
    indexes = inspect(db.get_bind()).get_indexes("complaints")
    names = {i["name"] for i in indexes if i["name"].startswith("ix_")}  # the unique reference number is separate
    assert names == {
        "ix_complaints_status", "ix_complaints_area_status", "ix_complaints_l2_officer_status",
        "ix_complaints_vehicle", "ix_complaints_subject_person", "ix_complaints_complainant_account",
        "ix_complaints_severity_registered",
    }


# ------------------------------------------------------------------ attachments, duplicates, escalation


def test_an_attachment_has_exactly_one_uploader(db, complaint, staff):
    account = make_complainant(db, "cp@sprpta.test")
    base = dict(complaint_id=complaint.id, file_name="a.pdf", storage_path="x/a.pdf", mime_type="application/pdf", size_bytes=10)
    _commit_fails(db, ComplaintAttachment(**base))
    _commit_fails(
        db, ComplaintAttachment(**base, uploaded_by_user_id=staff["l1"].id, uploaded_by_account_id=account.id)
    )
    db.add_all(
        [
            ComplaintAttachment(**base, uploaded_by_user_id=staff["l1"].id),
            ComplaintAttachment(**base, uploaded_by_account_id=account.id),
        ]
    )
    db.commit()


def test_duplicate_checks(db, complaint, staff, routing):
    other = _forwarded(staff, routing, reference_number="SPRPTA-2026-000002")
    db.add(other)
    db.commit()
    link = dict(decided_by_user_id=staff["l1"].id, link_type=DuplicateLinkType.RELATED)
    _commit_fails(db, DuplicateCheck(complaint_id=complaint.id, candidate_complaint_id=complaint.id, **link))
    db.add(DuplicateCheck(complaint_id=other.id, candidate_complaint_id=complaint.id, **link))
    db.commit()
    _commit_fails(db, DuplicateCheck(complaint_id=other.id, candidate_complaint_id=complaint.id, **link))


def test_a_case_is_escalated_once_with_a_reason(db, complaint, staff):
    _commit_fails(db, Escalation(complaint_id=complaint.id, escalated_by_user_id=staff["l2"].id, reason=""))
    db.add(Escalation(complaint_id=complaint.id, escalated_by_user_id=staff["l2"].id, reason="Serious allegation"))
    db.commit()
    _commit_fails(db, Escalation(complaint_id=complaint.id, escalated_by_user_id=staff["l2"].id, reason="Again"))


# ------------------------------------------------------------------ decision, solution, implementation


def _decision(complaint, staff, **extra) -> CaseDecision:
    return CaseDecision(
        complaint_id=complaint.id,
        decided_by_user_id=staff["l2"].id,
        action=DecisionAction.WARNING,
        reasoning="Evidence supports it",
        outcome=DecisionOutcome.SUBSTANTIATED,
        **extra,
    )


def test_one_decision_per_complaint(db, complaint, staff):
    db.add(_decision(complaint, staff))
    db.commit()
    _commit_fails(db, _decision(complaint, staff))


def test_ai_followed_needs_a_suggestion(db, complaint, staff):
    _commit_fails(db, _decision(complaint, staff, ai_followed=True))
    db.add(_decision(complaint, staff, ai_suggestion_id=1, ai_followed=False))
    db.commit()


def test_solution_document_and_implementation_record(db, complaint, staff):
    decision = _decision(complaint, staff)
    db.add(decision)
    db.commit()
    document = SolutionDocument(
        complaint_id=complaint.id,
        decision_id=decision.id,
        summary_text="Summary",
        verdict_text="Verdict",
        pdf_path="docs/1.pdf",
        generated_by_user_id=staff["l2"].id,
    )
    db.add(document)
    db.commit()
    record = dict(complaint_id=complaint.id, solution_document_id=document.id, done_by_user_id=staff["is"].id, done_note="Done")
    # an approver without a time (and the other way round) is rejected
    _commit_fails(db, ImplementationRecord(**record, approved_by_user_id=staff["l2"].id))
    _commit_fails(db, ImplementationRecord(**record, approved_at=datetime.now(UTC)))
    db.add(ImplementationRecord(**record))
    db.commit()
    _commit_fails(db, ImplementationRecord(**record))  # one record per complaint


# ------------------------------------------------------------------ recommendations


def test_recommendation_rules(db, staff):
    person = Person(full_name="Driver One", person_type=PersonType.DRIVER)
    db.add(person)
    db.commit()
    base = dict(title="Shade", details="Add benches", entered_by_user_id=staff["l1"].id)
    new = Recommendation(recommendation_type=RecommendationType.IMPROVEMENT, **base)
    db.add(new)
    db.commit()
    assert new.status == RecommendationStatus.NEW
    _commit_fails(db, Recommendation(recommendation_type=RecommendationType.IMPROVEMENT, subject_person_id=person.id, **base))
    _commit_fails(
        db,
        Recommendation(
            recommendation_type=RecommendationType.IMPROVEMENT, status=RecommendationStatus.COMMENDATION_VERIFIED, **base
        ),
    )
    db.add(
        Recommendation(
            recommendation_type=RecommendationType.COMMENDATION,
            status=RecommendationStatus.COMMENDATION_VERIFIED,
            subject_person_id=person.id,
            **base,
        )
    )
    db.commit()


# ------------------------------------------------------------------ messaging


def test_one_template_per_type_and_channel(db):
    db.add(MessageTemplate(message_type=MessageType.REGISTERED, channel=MessageChannel.SMS, body="Ref {reference_number}"))
    db.commit()
    _commit_fails(db, MessageTemplate(message_type=MessageType.REGISTERED, channel=MessageChannel.SMS, body="Again"))
    db.add(MessageTemplate(message_type=MessageType.REGISTERED, channel=MessageChannel.EMAIL, subject="Registered", body="Ref"))
    db.commit()


def test_a_case_never_gets_the_same_message_twice(db, complaint):
    base = dict(complaint_id=complaint.id, channel=MessageChannel.SMS, recipient="0771234567", body="Ref")
    db.add(OutboundMessage(message_type=MessageType.REGISTERED, state=MessageState.FAILED, **base))
    db.add(OutboundMessage(message_type=MessageType.REGISTERED, state=MessageState.FAILED, **base))  # failures never block
    db.add(OutboundMessage(message_type=MessageType.REGISTERED, state=MessageState.SENT, **base))
    db.commit()
    _commit_fails(db, OutboundMessage(message_type=MessageType.REGISTERED, state=MessageState.SENT, **base))
    db.add(OutboundMessage(message_type=MessageType.DECIDED, state=MessageState.SENT, **base))
    db.commit()


def test_only_otp_messages_can_skip_the_complaint(db):
    account = make_complainant(db, "otp@sprpta.test")
    base = dict(channel=MessageChannel.EMAIL, recipient="otp@sprpta.test", body="Code ****", state=MessageState.SENT)
    _commit_fails(db, OutboundMessage(message_type=MessageType.REGISTERED, **base))
    db.add(OutboundMessage(message_type=MessageType.OTP, complainant_account_id=account.id, **base))
    db.commit()


def test_otp_code_defaults(db):
    account = make_complainant(db, "signup@sprpta.test")
    code = OtpCode(
        complainant_account_id=account.id, channel=MessageChannel.EMAIL, code_hash="h", expires_at=datetime.now(UTC)
    )
    db.add(code)
    db.commit()
    assert code.attempts == 0 and code.consumed_at is None


# ------------------------------------------------------------------ audit log, settings, rating


def test_the_audit_log_cannot_be_changed(db, complaint, staff):
    entry = AuditLog(
        actor_user_id=staff["l1"].id,
        actor_role="l1",
        action="complaint.forward",
        entity_type="complaint",
        entity_id=complaint.id,
        complaint_id=complaint.id,
        from_status=ComplaintStatus.INCOMPLETE,
        to_status=ComplaintStatus.FORWARDED,
        details={"old": None, "new": "forwarded"},
    )
    db.add(entry)
    db.commit()
    assert entry.occurred_at is not None
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text("UPDATE audit_log SET action = 'x'"))
    db.rollback()
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text("DELETE FROM audit_log"))
    db.rollback()
    assert db.query(AuditLog).count() == 1


def test_audit_entries_keep_their_order_and_real_time(db):
    db.add_all([AuditLog(actor_role="system", action=f"step.{n}", entity_type="test") for n in range(3)])
    db.commit()
    rows = db.query(AuditLog).order_by(AuditLog.id).all()
    assert [r.occurred_at for r in rows] == sorted(r.occurred_at for r in rows)
    assert len({r.occurred_at for r in rows}) == 3  # clock_timestamp(), not one transaction time


def test_system_settings_are_keyed_by_name(db):
    db.add(SystemSetting(key="rating.credit_cap", value=10, description="Cap on credits"))
    db.add(SystemSetting(key="rating.band_limits", value={"excellent": 90, "good": 75}))
    db.commit()
    assert db.get(SystemSetting, "rating.credit_cap").value == 10
    _commit_fails(db, SystemSetting(key="rating.credit_cap", value=5))


def _snapshot(person, **extra) -> RatingSnapshot:
    return RatingSnapshot(
        person_id=person.id,
        window_start=datetime(2025, 11, 12).date(),
        window_end=datetime(2026, 11, 12).date(),
        penalty=5,
        credits=1,
        score=extra.pop("score", 77),
        band=RatingBand.GOOD,
        formula_version=1,
        breakdown={"complaints": []},
        trigger="viewed",
        **extra,
    )


def test_rating_snapshot_and_appeal(db, complaint, staff):
    person = Person(full_name="Driver Two", person_type=PersonType.DRIVER)
    db.add(person)
    db.commit()
    _commit_fails(db, _snapshot(person, score=101))
    _commit_fails(db, _snapshot(person, score=-1))
    before, after = _snapshot(person), _snapshot(person, score=80)
    db.add_all([before, after])
    db.commit()
    appeal = RatingAppeal(
        person_id=person.id,
        complaint_id=complaint.id,
        reason="Wrong driver",
        recorded_by_user_id=staff["l3"].id,
        snapshot_before_id=before.id,
        snapshot_after_id=after.id,
    )
    db.add(appeal)
    db.commit()
    assert appeal.status.value == "open"
