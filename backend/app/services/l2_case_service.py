"""The Level 2 area officer's cases (UC-L2-01, 02, 04, 05 and 07).

An officer sees only the cases of their own area, from Forwarded onward. Opening a Forwarded case moves it to
Under review. The officer then records a decision and creates the solution document, which moves the case to
Awaiting implementation, or escalates it to Level 3 with a reason. Every move is written to the audit trail.

Overdue is a flag, never a status: a case is overdue when the time target of its stage has passed, counted in
calendar days from registration without the time it spent Incomplete. Decide-by applies until the officer records
a decision, and close-by after that. The AI suggestion and Approve (which needs the implementing staff portal) are
not built yet, and neither is the messaging module, so the decision message (MSG-2) is not sent here.
"""

from datetime import datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import DateTime, and_, case, false, func, or_, select, type_coerce
from sqlalchemy.orm import Session

from app.core.enums import ComplaintStatus, DecisionAction, DecisionOutcome
from app.core.timezone import LOCAL
from app.models import (
    Area,
    AuditLog,
    CaseDecision,
    Complaint,
    ComplaintAttachment,
    ComplaintCategory,
    ComplaintDutySnapshot,
    ComplaintMedium,
    ComplaintTargetType,
    DuplicateCheck,
    Escalation,
    Permit,
    Person,
    RouteStand,
    Severity,
    SolutionDocument,
    User,
    Vehicle,
)
from app.schemas.l2_cases import (
    AttachmentInfo,
    CaseDetail,
    CaseFilter,
    CasePage,
    CaseRow,
    CaseSort,
    DashboardOut,
    DecisionBody,
    DecisionOut,
    DuplicateDecision,
    EarlierCase,
    EscalateBody,
    EscalationOut,
    HistoryEntry,
    SeverityFilter,
    SolutionDocumentBody,
    SolutionDocumentOut,
    TimeTarget,
)
from app.services import audit_service, l2_recommendation_service, solution_pdf
from app.services.auth_service import Principal
from app.services.complaint_attachment_service import storage_root
from app.services.complaint_intake_service import ComplaintError

PAGE_SIZE = 10
ROUTED = (
    ComplaintStatus.FORWARDED,
    ComplaintStatus.UNDER_REVIEW,
    ComplaintStatus.AWAITING_IMPLEMENTATION,
    ComplaintStatus.DONE_AWAITING_APPROVAL,
    ComplaintStatus.ESCALATED,
    ComplaintStatus.CLOSED,
)
DECIDING = (ComplaintStatus.FORWARDED, ComplaintStatus.UNDER_REVIEW)
IMPLEMENTING = (ComplaintStatus.AWAITING_IMPLEMENTATION, ComplaintStatus.DONE_AWAITING_APPROVAL)

# The four severities by rank. The names can be edited by the administrator, the ranks cannot.
SEVERITY_KEYS = {1: "critical", 2: "high", 3: "medium", 4: "low"}
SEVERITY_RANKS = {key: rank for rank, key in SEVERITY_KEYS.items()}


def severity_key(rank: int) -> str:
    return SEVERITY_KEYS.get(rank, "medium")

ACTION_LABEL = {
    DecisionAction.WARNING: "Warning",
    DecisionAction.FINE: "Fine",
    DecisionAction.SUSPENSION: "Suspension",
    DecisionAction.LEGAL_ACTION: "Legal action",
    DecisionAction.NO_ACTION: "No action",
}
OUTCOME_LABEL = {
    DecisionOutcome.SUBSTANTIATED: "substantiated",
    DecisionOutcome.PARTLY_SUBSTANTIATED: "partly substantiated",
    DecisionOutcome.NOT_SUBSTANTIATED: "not substantiated",
}


# ---------------------------------------------------------------- time targets


def _awaiting_decision():
    """True for a case the officer has not decided yet."""
    return and_(Complaint.status.in_(DECIDING), Complaint.decided_at.is_(None))


def _due_at():
    """When the time target of the case's current stage passes; empty once Level 2 has no target left."""
    days = case(
        (_awaiting_decision(), Severity.decide_days),
        (Complaint.status.in_((*DECIDING, *IMPLEMENTING)), Severity.close_days),
    )
    due = Complaint.registered_at + Complaint.paused_total + func.make_interval(0, 0, 0, days)
    return type_coerce(due, DateTime(timezone=True))


def _overdue():
    return func.coalesce(_due_at() < func.now(), false())


def _due_kind(c: Complaint) -> str | None:
    if c.status in DECIDING:
        return "close" if c.decided_at else "decide"
    return "close" if c.status in IMPLEMENTING else None


# ---------------------------------------------------------------- the officer's area


def _area_id(officer: Principal) -> int:
    if officer.area_id is None:
        raise ComplaintError(403, "no_area", "Your account has no area yet. Ask the administrator to set one.")
    return officer.area_id


def _in_area(officer: Principal) -> list:
    return [Complaint.area_id == _area_id(officer), Complaint.status.in_(ROUTED)]


def _find(db: Session, officer: Principal, complaint_id: int, *, lock: bool = False) -> Complaint:
    """The case, if it belongs to the officer's area. Any other case is reported as missing."""
    query = select(Complaint).where(Complaint.id == complaint_id, *_in_area(officer))
    complaint = db.scalar(query.with_for_update() if lock else query)
    if complaint is None:
        raise ComplaintError(404, "not_found", "That case does not exist in your area.")
    return complaint


def _count(db: Session, *conditions) -> int:
    query = select(func.count()).select_from(Complaint).join(Severity, Severity.id == Complaint.severity_id)
    return db.scalar(query.where(*conditions)) or 0


def _counts(db: Session, conditions: list) -> dict[str, int]:
    rows = db.execute(
        select(Complaint.status, func.count())
        .join(Severity, Severity.id == Complaint.severity_id)
        .where(*conditions)
        .group_by(Complaint.status)
    ).all()
    counts = {status.value: 0 for status in ROUTED}
    counts.update({status.value: n for status, n in rows})
    counts["all"] = sum(counts.values())
    counts["overdue"] = _count(db, *conditions, _overdue())
    return counts


def _rows(db: Session, conditions: list, *, sort: CaseSort, limit: int, offset: int = 0) -> list[CaseRow]:
    due = _due_at()
    order = (
        [_overdue().desc(), due.asc().nulls_last(), Severity.rank, Complaint.id]
        if sort == "urgent"
        else [Complaint.forwarded_at.desc(), Complaint.id.desc()]
    )
    rows = db.execute(
        select(Complaint, Severity.rank, due)
        .join(Severity, Severity.id == Complaint.severity_id)
        .where(*conditions)
        .order_by(*order)
        .limit(limit)
        .offset(offset)
    ).all()
    now = datetime.now(LOCAL)
    return [
        CaseRow(
            id=c.id,
            reference_number=c.reference_number,
            status=c.status,
            subject=c.subject,
            vehicle_number=c.vehicle_number_entered,
            severity=severity_key(rank),
            forwarded_at=c.forwarded_at,
            due_kind=_due_kind(c),
            due_at=due_at,
            overdue=due_at is not None and due_at < now,
        )
        for c, rank, due_at in rows
    ]


# ---------------------------------------------------------------- lists


def list_cases(
    db: Session,
    officer: Principal,
    *,
    status: CaseFilter | None,
    severity: SeverityFilter | None,
    search: str,
    sort: CaseSort,
    page: int,
) -> CasePage:
    base = _in_area(officer)
    if severity:
        base.append(Severity.rank == SEVERITY_RANKS[severity])
    term = search.strip()
    if term:
        base.append(
            or_(
                Complaint.reference_number.icontains(term, autoescape=True),
                Complaint.subject.icontains(term, autoescape=True),
                Complaint.vehicle_number_entered.icontains(term, autoescape=True),
            )
        )
    counts = _counts(db, base)
    if status == "overdue":
        base.append(_overdue())
    elif status:
        base.append(Complaint.status == ComplaintStatus(status))

    total = counts[status] if status else counts["all"]
    page = min(page, max(1, -(-total // PAGE_SIZE)))  # a page past the end shows the last one
    items = _rows(db, base, sort=sort, limit=PAGE_SIZE, offset=(page - 1) * PAGE_SIZE)
    return CasePage(items=items, total=total, page=page, page_size=PAGE_SIZE, counts=counts)


def dashboard(db: Session, officer: Principal) -> DashboardOut:
    area = _in_area(officer)
    now = datetime.now(LOCAL)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month = today.replace(day=1)
    waiting = [*area, _awaiting_decision()]

    next_case = _rows(db, waiting, sort="urgent", limit=1)
    average = db.scalar(
        select(func.avg(func.extract("epoch", Complaint.decided_at - Complaint.registered_at))).where(
            Complaint.area_id == _area_id(officer), Complaint.decided_at >= month
        )
    )
    targets = db.scalars(select(Severity).where(Severity.is_active).order_by(Severity.rank))
    return DashboardOut(
        counts=_counts(db, area),
        arrived_today=_count(db, *area, Complaint.forwarded_at >= today),
        decided_today=db.scalar(
            select(func.count())
            .select_from(CaseDecision)
            .where(CaseDecision.decided_by_user_id == officer.id, CaseDecision.decided_at >= today)
        )
        or 0,
        closed_this_month=_count(db, *area, Complaint.closed_at >= month),
        urgent=_count(db, *waiting, Severity.rank == 1),
        next_case_id=next_case[0].id if next_case else None,
        overdue=_rows(db, [*area, _overdue()], sort="urgent", limit=5),
        average_decide_days=round(float(average) / 86400, 1) if average is not None else None,
        targets=[
            TimeTarget(severity=severity_key(s.rank), forward_days=s.forward_days, decide_days=s.decide_days, close_days=s.close_days)
            for s in targets
        ],
        recommendations=l2_recommendation_service.latest(db, limit=4),
    )


# ---------------------------------------------------------------- one case


def _name(db: Session, model, row_id: int | None, attribute: str = "name") -> str | None:
    row = db.get(model, row_id) if row_id else None
    return getattr(row, attribute) if row else None


def _user_name(db: Session, user_id: int | None) -> str:
    return _name(db, User, user_id, "full_name") or "Unknown"


def _earlier(db: Session, c: Complaint) -> list[EarlierCase]:
    """Earlier cases of this area against the same vehicle or the same person, with what was decided.

    Only cases that reached Level 2 are listed (not drafts, incomplete or rejected ones), and only the officer's own
    area, so a case is never shown to an officer who could not open it.
    """
    same = [Complaint.vehicle_id == c.vehicle_id]
    if c.subject_person_id:
        same.append(Complaint.subject_person_id == c.subject_person_id)
    rows = db.execute(
        select(Complaint, CaseDecision)
        .outerjoin(CaseDecision, CaseDecision.complaint_id == Complaint.id)
        .where(
            or_(*same),
            Complaint.id != c.id,
            Complaint.area_id == c.area_id,
            Complaint.status.in_(ROUTED),
            Complaint.registered_at < c.registered_at,
        )
        .order_by(Complaint.registered_at.desc())
        .limit(10)
    ).all()
    return [
        EarlierCase(
            id=e.id,
            reference_number=e.reference_number,
            subject=e.subject,
            status=e.status,
            registered_at=e.registered_at,
            action=d.action if d else None,
            outcome=d.outcome if d else None,
        )
        for e, d in rows
    ]


def _history(db: Session, complaint_id: int) -> list[HistoryEntry]:
    rows = db.execute(
        select(AuditLog, User.full_name)
        .outerjoin(User, User.id == AuditLog.actor_user_id)
        .where(AuditLog.complaint_id == complaint_id)
        .order_by(AuditLog.id)
    ).all()
    return [
        HistoryEntry(
            occurred_at=a.occurred_at,
            actor_name=name,
            actor_role=a.actor_role,
            action=a.action,
            from_status=a.from_status,
            to_status=a.to_status,
            reason=a.reason,
        )
        for a, name in rows
    ]


def _detail(db: Session, c: Complaint) -> CaseDetail:
    severity = db.get(Severity, c.severity_id)
    due_at = db.scalar(
        select(_due_at()).select_from(Complaint).join(Severity, Severity.id == Complaint.severity_id).where(Complaint.id == c.id)
    )
    vehicle = db.get(Vehicle, c.vehicle_id) if c.vehicle_id else None
    history = _history(db, c.id)
    forwarded = next((h for h in reversed(history) if h.action == "complaint.forward"), None)
    attachments = db.scalars(
        select(ComplaintAttachment)
        .where(ComplaintAttachment.complaint_id == c.id, ComplaintAttachment.removed_at.is_(None))
        .order_by(ComplaintAttachment.id)
    )
    duplicates = db.execute(
        select(DuplicateCheck.link_type, Complaint.reference_number)
        .join(Complaint, Complaint.id == DuplicateCheck.candidate_complaint_id)
        .where(DuplicateCheck.complaint_id == c.id)
        .order_by(DuplicateCheck.id)
    ).all()
    decision = db.scalar(select(CaseDecision).where(CaseDecision.complaint_id == c.id))
    document = db.scalar(select(SolutionDocument).where(SolutionDocument.complaint_id == c.id))
    escalation = db.scalar(select(Escalation).where(Escalation.complaint_id == c.id))
    duty = db.scalar(select(ComplaintDutySnapshot).where(ComplaintDutySnapshot.complaint_id == c.id))

    return CaseDetail(
        id=c.id,
        reference_number=c.reference_number,
        status=c.status,
        severity=severity_key(severity.rank),
        due_kind=_due_kind(c),
        due_at=due_at,
        overdue=due_at is not None and due_at < datetime.now(LOCAL),
        subject=c.subject,
        description=c.description,
        category=_name(db, ComplaintCategory, c.category_id),
        target=_name(db, ComplaintTargetType, c.target_type_id),
        accused=_name(db, Person, c.subject_person_id, "full_name") or c.subject_person_text,
        medium=_name(db, ComplaintMedium, c.medium_id),
        is_anonymous=c.is_anonymous,
        complainant=c.complainant_name,
        has_contact=bool(c.contact_phone or c.contact_email),
        complainant_type=c.complainant_type,
        complaint_date=c.complaint_date,
        incident_time=c.incident_time,
        incident_location=c.incident_location,
        bus_verification=c.bus_verification,
        driver_on_duty=duty.driver_name if duty else None,
        conductor_on_duty=duty.conductor_name if duty else None,
        vehicle_number=vehicle.vehicle_number if vehicle else c.vehicle_number_entered,
        vehicle_type=vehicle.vehicle_type.value if vehicle else None,
        permit_number=_name(db, Permit, c.permit_id, "permit_number"),
        owner=_name(db, Person, c.owner_person_id, "full_name"),
        route_stand=_name(db, RouteStand, c.route_stand_id),
        area=_name(db, Area, c.area_id),
        registered_at=c.registered_at,
        forwarded_at=c.forwarded_at,
        forwarded_by=forwarded.actor_name if forwarded else None,
        attachments=[AttachmentInfo.model_validate(a, from_attributes=True) for a in attachments],
        earlier=_earlier(db, c),
        duplicates=[DuplicateDecision(reference_number=ref, link_type=link) for link, ref in duplicates],
        history=history,
        decision=DecisionOut(
            action=decision.action,
            outcome=decision.outcome,
            reasoning=decision.reasoning,
            decided_by=_user_name(db, decision.decided_by_user_id),
            decided_at=decision.decided_at,
        )
        if decision
        else None,
        solution_document=SolutionDocumentOut(
            summary_text=document.summary_text,
            verdict_text=document.verdict_text,
            solution_details=document.solution_details,
            generated_by=_user_name(db, document.generated_by_user_id),
            generated_at=document.generated_at,
        )
        if document
        else None,
        escalation=EscalationOut(
            reason=escalation.reason,
            escalated_by=_user_name(db, escalation.escalated_by_user_id),
            escalated_at=escalation.escalated_at,
        )
        if escalation
        else None,
    )


def get_case(db: Session, officer: Principal, complaint_id: int) -> CaseDetail:
    return _detail(db, _find(db, officer, complaint_id))


# ---------------------------------------------------------------- moving it on


def _move(db: Session, officer: Principal, c: Complaint, to: ComplaintStatus, action: str, **audit) -> None:
    audit_service.record(
        db, officer, action=action, entity_type="complaints", entity_id=c.id,
        complaint_id=c.id, from_status=c.status, to_status=to, **audit,
    )
    c.status = to


def _start_review(db: Session, officer: Principal, c: Complaint) -> None:
    if c.status == ComplaintStatus.FORWARDED:
        c.review_started_at = datetime.now(LOCAL)
        _move(db, officer, c, ComplaintStatus.UNDER_REVIEW, "complaint.review")


def _must_be_deciding(c: Complaint) -> None:
    if c.status not in DECIDING:
        raise ComplaintError(409, "not_deciding", "This case is past the decision step.")


def start_review(db: Session, officer: Principal, complaint_id: int) -> CaseDetail:
    """Opening a Forwarded case moves it to Under review. Any other case is left as it is."""
    c = _find(db, officer, complaint_id, lock=True)
    _start_review(db, officer, c)
    db.commit()
    return _detail(db, c)


def record_decision(db: Session, officer: Principal, complaint_id: int, body: DecisionBody) -> CaseDetail:
    """Record the officer's decision (UC-L2-04). It can be changed until the solution document is created."""
    c = _find(db, officer, complaint_id, lock=True)
    _must_be_deciding(c)
    _start_review(db, officer, c)
    now = datetime.now(LOCAL)
    decision = db.scalar(select(CaseDecision).where(CaseDecision.complaint_id == c.id))
    previous = (
        {"action": decision.action.value, "outcome": decision.outcome.value, "reasoning": decision.reasoning}
        if decision
        else None
    )
    if decision is None:
        decision = CaseDecision(complaint_id=c.id)
        db.add(decision)
    decision.decided_by_user_id = officer.id
    decision.action = body.action
    decision.outcome = body.outcome
    decision.reasoning = body.reasoning.strip()
    decision.decided_at = now  # no AI suggestion was asked for, so ai_followed stays empty
    c.decided_at = c.decided_at or now  # the first decision ends the decide-by target; a change does not restart it
    db.flush()
    audit_service.record(
        db, officer, action="decision.update" if previous else "decision.create", entity_type="case_decisions",
        entity_id=decision.id, complaint_id=c.id,
        details={
            "previous": previous,
            "new": {"action": body.action.value, "outcome": body.outcome.value, "reasoning": decision.reasoning},
        },
    )
    db.commit()
    return _detail(db, c)


def create_solution_document(
    db: Session, officer: Principal, complaint_id: int, body: SolutionDocumentBody
) -> CaseDetail:
    """Generate the PDF from the decision (UC-L2-05). The case moves to Awaiting implementation."""
    c = _find(db, officer, complaint_id, lock=True)
    _must_be_deciding(c)
    decision = db.scalar(select(CaseDecision).where(CaseDecision.complaint_id == c.id))
    if decision is None:
        raise ComplaintError(409, "no_decision", "Record the decision before creating the solution document.")

    now = datetime.now(LOCAL)
    verdict = f"{ACTION_LABEL[decision.action]}. The complaint is {OUTCOME_LABEL[decision.outcome]}."
    pdf = solution_pdf.render(
        reference=c.reference_number,
        area=_name(db, Area, c.area_id) or "",
        vehicle=_name(db, Vehicle, c.vehicle_id, "vehicle_number") or c.vehicle_number_entered or "",
        officer=officer.name,
        generated_at=now,
        summary=body.summary.strip(),
        verdict=verdict,
        reasoning=decision.reasoning,
        solution_details=body.solution_details.strip(),
    )
    stored = Path("solution-documents") / str(c.id) / f"{uuid4().hex}.pdf"
    target = storage_root() / stored
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(pdf)
    try:
        document = SolutionDocument(
            complaint_id=c.id,
            decision_id=decision.id,
            summary_text=body.summary.strip(),
            verdict_text=verdict,
            solution_details=body.solution_details.strip(),
            pdf_path=stored.as_posix(),
            generated_by_user_id=officer.id,
        )
        db.add(document)
        db.flush()
        _move(
            db, officer, c, ComplaintStatus.AWAITING_IMPLEMENTATION, "solution_document.create",
            details={"solution_document_id": document.id},
        )
        db.commit()
    except Exception:
        db.rollback()
        target.unlink(missing_ok=True)  # no row points at the file, so do not leave it behind
        raise
    return _detail(db, c)


def escalate(db: Session, officer: Principal, complaint_id: int, body: EscalateBody) -> CaseDetail:
    """Pass the case to Level 3 with a reason (UC-L2-07). It leaves the officer's action list for good."""
    c = _find(db, officer, complaint_id, lock=True)
    _must_be_deciding(c)
    if db.scalar(select(CaseDecision.id).where(CaseDecision.complaint_id == c.id)):
        raise ComplaintError(
            409, "already_decided", "A decision is already recorded. Create the solution document instead."
        )
    reason = body.reason.strip()
    now = datetime.now(LOCAL)
    db.add(Escalation(complaint_id=c.id, escalated_by_user_id=officer.id, reason=reason, escalated_at=now))
    c.escalated_at = now
    _move(db, officer, c, ComplaintStatus.ESCALATED, "complaint.escalate", reason=reason)
    db.commit()
    return _detail(db, c)


# ---------------------------------------------------------------- files


def attachment_file(db: Session, officer: Principal, complaint_id: int, attachment_id: int) -> tuple[Path, str, str]:
    """The stored file of an attachment: path, display name and type."""
    _find(db, officer, complaint_id)
    attachment = db.scalar(
        select(ComplaintAttachment).where(
            ComplaintAttachment.id == attachment_id,
            ComplaintAttachment.complaint_id == complaint_id,
            ComplaintAttachment.removed_at.is_(None),
        )
    )
    if attachment is None:
        raise ComplaintError(404, "not_found", "That attachment does not exist.")
    return storage_root() / attachment.storage_path, attachment.file_name, attachment.mime_type


def solution_document_file(db: Session, officer: Principal, complaint_id: int) -> tuple[Path, str]:
    c = _find(db, officer, complaint_id)
    path = db.scalar(select(SolutionDocument.pdf_path).where(SolutionDocument.complaint_id == c.id))
    if path is None:
        raise ComplaintError(404, "not_found", "This case has no solution document yet.")
    return storage_root() / path, f"Solution document {c.reference_number}.pdf"
