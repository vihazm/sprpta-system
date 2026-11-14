"""The Level 1 complaint form (UC-L1-01 to UC-L1-10): save, finish later, forward or reject.

Statuses follow the System Flow Document section 3.3. L1 may only move a
complaint out of Draft or Incomplete, and every move is written to the audit
trail. The reference number is issued when the complaint is first saved as
Incomplete or forwarded; that moment also starts the time-target clock, and
Incomplete pauses it. The registration message to the complainant belongs to
the messaging module, which is not built yet.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ComplaintStatus, DuplicateLinkType, RejectionType
from app.core.identifiers import normalise_identifier
from app.core.roles import UserRole
from app.core.timezone import LOCAL
from app.models import (
    Area,
    Complaint,
    ComplaintAttachment,
    ComplaintCategory,
    ComplaintMedium,
    DuplicateCheck,
    Person,
    RouteStand,
    Severity,
    User,
    Vehicle,
)
from app.schemas.l1_complaints import (
    AttachmentOut,
    ComplaintForm,
    ComplaintListItem,
    ComplaintOut,
    DuplicateCandidate,
    RejectBody,
)
from app.services import audit_service
from app.services import complaint_lookup_service as lookup
from app.services.auth_service import Principal

EDITABLE = (ComplaintStatus.DRAFT, ComplaintStatus.INCOMPLETE)
LIST_LIMIT = 100


class ComplaintError(Exception):
    """A rule the request breaks; the route turns it into a clean HTTP error."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


# ---------------------------------------------------------------- reading


def _out(db: Session, complaint: Complaint) -> ComplaintOut:
    vehicle = db.get(Vehicle, complaint.vehicle_id) if complaint.vehicle_id else None
    officer = db.get(User, complaint.assigned_l2_user_id) if complaint.assigned_l2_user_id else None
    area = db.get(Area, complaint.area_id) if complaint.area_id else None
    person = db.get(Person, complaint.subject_person_id) if complaint.subject_person_id else None
    earlier = db.get(Complaint, complaint.duplicate_of_complaint_id) if complaint.duplicate_of_complaint_id else None
    attachments = db.scalars(
        select(ComplaintAttachment)
        .where(ComplaintAttachment.complaint_id == complaint.id, ComplaintAttachment.removed_at.is_(None))
        .order_by(ComplaintAttachment.id)
    )
    return ComplaintOut(
        id=complaint.id,
        reference_number=complaint.reference_number,
        status=complaint.status,
        medium_id=complaint.medium_id,
        is_anonymous=complaint.is_anonymous,
        complainant_name=complaint.complainant_name,
        contact=complaint.contact_phone or complaint.contact_email,
        complaint_date=complaint.complaint_date,
        vehicle_number=complaint.vehicle_number_entered,
        vehicle=lookup.vehicle_lookup(db, vehicle) if vehicle else None,
        subject_person_id=complaint.subject_person_id,
        subject_person_text=complaint.subject_person_text,
        subject_person_name=person.full_name if person else complaint.subject_person_text,
        route_stand_id=complaint.route_stand_id,
        category_id=complaint.category_id,
        severity_id=complaint.severity_id,
        subject=complaint.subject,
        description=complaint.description,
        area_id=complaint.area_id,
        area_name=area.name if area else None,
        assigned_l2_name=officer.full_name if officer else None,
        rejection_type=complaint.rejection_type,
        rejection_reason=complaint.rejection_reason,
        duplicate_of_reference=earlier.reference_number if earlier else None,
        registered_at=complaint.registered_at,
        forwarded_at=complaint.forwarded_at,
        rejected_at=complaint.rejected_at,
        attachments=[AttachmentOut.model_validate(a, from_attributes=True) for a in attachments],
        created_at=complaint.created_at,
        updated_at=complaint.updated_at,
    )


def find_complaint(db: Session, complaint_id: int, *, lock: bool = False) -> Complaint:
    query = select(Complaint).where(Complaint.id == complaint_id)
    complaint = db.scalar(query.with_for_update() if lock else query)
    if complaint is None:
        raise ComplaintError(404, "not_found", "That complaint does not exist.")
    return complaint


def find_editable(db: Session, complaint_id: int) -> Complaint:
    """The complaint, locked for this request, if L1 may still change it."""
    complaint = find_complaint(db, complaint_id, lock=True)
    if complaint.status not in EDITABLE:
        raise ComplaintError(
            409, "not_editable", "Only a draft or an incomplete complaint can be changed. This one is already past that."
        )
    return complaint


def get_complaint(db: Session, complaint_id: int) -> ComplaintOut:
    return _out(db, find_complaint(db, complaint_id))


def get_duplicates(db: Session, complaint_id: int) -> list[DuplicateCandidate]:
    return lookup.duplicate_candidates(db, find_complaint(db, complaint_id))


def list_open(db: Session, status: ComplaintStatus | None) -> list[ComplaintListItem]:
    """Drafts and incomplete complaints, to reopen and finish (UC-L1-06)."""
    wanted = [status] if status in EDITABLE else list(EDITABLE)
    rows = db.scalars(
        select(Complaint).where(Complaint.status.in_(wanted)).order_by(Complaint.updated_at.desc()).limit(LIST_LIMIT)
    )
    return [
        ComplaintListItem(
            id=c.id,
            reference_number=c.reference_number,
            status=c.status,
            subject=c.subject,
            vehicle_number=c.vehicle_number_entered,
            updated_at=c.updated_at,
        )
        for c in rows
    ]


# ---------------------------------------------------------------- saving the form


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def must_exist(db: Session, model, row_id: int | None, label: str, *conditions) -> None:
    """The form may only point at an active row of a lookup table; anything else is a 422."""
    if row_id is None:
        return
    if db.scalar(select(model.id).where(model.id == row_id, model.is_active, *conditions)) is None:
        raise ComplaintError(422, f"unknown_{label}", f"Choose a valid {label}.")


def _contact(raw: str | None) -> tuple[str | None, str | None]:
    """The phone and the email to store for what L1 typed in the contact box."""
    raw = _clean(raw)
    if raw is None:
        return None, None
    parsed = normalise_identifier(raw)
    if parsed is None:
        raise ComplaintError(422, "invalid_contact", "Enter a valid email address or a Sri Lankan mobile number.")
    kind, value = parsed
    return (value, None) if kind == "phone" else (None, value)


def _apply_form(db: Session, complaint: Complaint, data: ComplaintForm) -> None:
    must_exist(db, ComplaintMedium, data.medium_id, "medium", ComplaintMedium.is_system.is_(False))
    must_exist(db, ComplaintCategory, data.category_id, "category")
    must_exist(db, Severity, data.severity_id, "severity")
    must_exist(db, RouteStand, data.route_stand_id, "route_stand")
    must_exist(db, Person, data.subject_person_id, "person")
    if data.complaint_date and data.complaint_date > datetime.now(LOCAL).date():
        raise ComplaintError(422, "future_date", "The date cannot be in the future.")

    complaint.is_anonymous = data.is_anonymous
    if data.is_anonymous:
        complaint.complainant_name = complaint.contact_phone = complaint.contact_email = None
    else:
        complaint.complainant_name = _clean(data.complainant_name)
        complaint.contact_phone, complaint.contact_email = _contact(data.contact)

    complaint.medium_id = data.medium_id
    complaint.complaint_date = data.complaint_date
    complaint.subject_person_id = data.subject_person_id
    complaint.subject_person_text = _clean(data.subject_person_text)
    complaint.route_stand_id = data.route_stand_id
    complaint.category_id = data.category_id
    complaint.severity_id = data.severity_id
    complaint.subject = _clean(data.subject)
    complaint.description = _clean(data.description)

    # The permit, owner and area come from the vehicle record, not from what L1 typed.
    number = _clean(data.vehicle_number)
    vehicle = lookup.find_vehicle(db, number) if number else None
    permit = lookup.active_permit(db, vehicle) if vehicle else None
    complaint.vehicle_number_entered = number
    complaint.vehicle_id = vehicle.id if vehicle else None
    complaint.permit_id = permit.id if permit else None
    complaint.owner_person_id = vehicle.owner_person_id if vehicle else None
    complaint.area_id = vehicle.registered_area_id if vehicle else None


def create_draft(db: Session, principal: Principal, data: ComplaintForm) -> ComplaintOut:
    complaint = Complaint(status=ComplaintStatus.DRAFT, entered_by_user_id=principal.id)
    _apply_form(db, complaint, data)
    db.add(complaint)
    db.flush()  # gives the complaint its id for the audit row
    audit_service.record(
        db, principal, action="complaint.create", entity_type="complaints", entity_id=complaint.id,
        complaint_id=complaint.id, to_status=ComplaintStatus.DRAFT,
    )
    db.commit()
    return _out(db, complaint)


def update_complaint(db: Session, complaint_id: int, data: ComplaintForm) -> ComplaintOut:
    complaint = find_editable(db, complaint_id)
    _apply_form(db, complaint, data)
    db.commit()
    return _out(db, complaint)


# ---------------------------------------------------------------- moving it on


def _issue_reference(complaint: Complaint, now: datetime) -> None:
    """Give the complaint its reference number and start its clock, once."""
    if complaint.reference_number is None:
        complaint.reference_number = f"SPRPTA-{now.astimezone(LOCAL).year}-{complaint.id:06d}"
        complaint.registered_at = now


def _move(db: Session, principal: Principal, complaint: Complaint, to: ComplaintStatus, action: str, **audit) -> None:
    audit_service.record(
        db, principal, action=action, entity_type="complaints", entity_id=complaint.id,
        complaint_id=complaint.id, from_status=complaint.status, to_status=to, **audit,
    )
    complaint.status = to


def save_incomplete(db: Session, principal: Principal, complaint_id: int) -> ComplaintOut:
    """Draft to Incomplete: issues the reference number and pauses the clock."""
    complaint = find_editable(db, complaint_id)
    if complaint.status != ComplaintStatus.DRAFT:
        raise ComplaintError(409, "already_incomplete", "This complaint is already incomplete.")
    now = datetime.now(LOCAL)
    _issue_reference(complaint, now)
    complaint.paused_since = now
    _move(db, principal, complaint, ComplaintStatus.INCOMPLETE, "complaint.incomplete")
    db.commit()
    return _out(db, complaint)


def _missing_details(complaint: Complaint) -> list[str]:
    needed = {
        "medium": complaint.medium_id,
        "date": complaint.complaint_date,
        "a vehicle that is on record": complaint.vehicle_id,
        "route or stand": complaint.route_stand_id,
        "category": complaint.category_id,
        "severity": complaint.severity_id,
        "subject": complaint.subject,
        "description": complaint.description,
    }
    if not complaint.is_anonymous:
        needed["complainant name"] = complaint.complainant_name
    return [label for label, value in needed.items() if not value]


def forward(db: Session, principal: Principal, complaint_id: int) -> ComplaintOut:
    """Send a complete complaint to the Level 2 officer of the vehicle's area (UC-L1-09)."""
    complaint = find_editable(db, complaint_id)
    missing = _missing_details(complaint)
    if missing:
        raise ComplaintError(422, "missing_details", f"Still needed before forwarding: {', '.join(missing)}.")

    marked_duplicate = db.scalar(
        select(DuplicateCheck.id).where(
            DuplicateCheck.complaint_id == complaint.id, DuplicateCheck.link_type == DuplicateLinkType.DUPLICATE_OF
        )
    )
    if marked_duplicate:
        raise ComplaintError(409, "marked_duplicate", "This is marked as a duplicate. Reject it with a reason instead.")
    if any(c.link_type is None for c in lookup.duplicate_candidates(db, complaint)):
        raise ComplaintError(
            409, "duplicate_undecided", "Choose for every possible duplicate whether it is a duplicate, related or not."
        )

    officer = db.scalar(select(User).where(User.role == UserRole.L2, User.is_active, User.area_id == complaint.area_id))
    if officer is None:
        raise ComplaintError(409, "no_officer", "There is no active Level 2 officer for this area yet.")

    now = datetime.now(LOCAL)
    _issue_reference(complaint, now)
    if complaint.paused_since:  # finishing an incomplete complaint resumes the clock
        complaint.paused_total += now - complaint.paused_since
        complaint.paused_since = None
    complaint.assigned_l2_user_id = officer.id
    complaint.forwarded_at = now
    _move(
        db, principal, complaint, ComplaintStatus.FORWARDED, "complaint.forward",
        details={"assigned_l2_user_id": officer.id},
    )
    db.commit()
    return _out(db, complaint)


def reject(db: Session, principal: Principal, complaint_id: int, data: RejectBody) -> ComplaintOut:
    """Reject before forwarding (UC-L1-07). Final: nobody can reinstate it."""
    complaint = find_editable(db, complaint_id)
    earlier = None
    if data.rejection_type == RejectionType.DUPLICATE:
        reference = _clean(data.duplicate_of_reference)
        earlier = db.scalar(select(Complaint).where(Complaint.reference_number == reference)) if reference else None
        if earlier is None or earlier.id == complaint.id:
            raise ComplaintError(422, "unknown_duplicate", "Give the reference number of the earlier case.")
        _set_duplicate_choice(db, principal, complaint, earlier, DuplicateLinkType.DUPLICATE_OF)

    complaint.rejection_type = data.rejection_type
    complaint.rejection_reason = data.reason.strip()
    complaint.duplicate_of_complaint_id = earlier.id if earlier else None
    complaint.rejected_at = datetime.now(LOCAL)
    _move(
        db, principal, complaint, ComplaintStatus.REJECTED, "complaint.reject",
        reason=complaint.rejection_reason, details={"rejection_type": data.rejection_type.value},
    )
    db.commit()
    return _out(db, complaint)


# ---------------------------------------------------------------- the duplicate check


def _set_duplicate_choice(
    db: Session, principal: Principal, complaint: Complaint, candidate: Complaint, link_type: DuplicateLinkType
) -> None:
    check = db.scalar(
        select(DuplicateCheck).where(
            DuplicateCheck.complaint_id == complaint.id, DuplicateCheck.candidate_complaint_id == candidate.id
        )
    )
    if check is None:
        check = DuplicateCheck(complaint_id=complaint.id, candidate_complaint_id=candidate.id)
        db.add(check)
    elif check.link_type == link_type:
        return  # already recorded: nothing new to audit
    check.link_type = link_type
    check.decided_by_user_id = principal.id
    db.flush()
    audit_service.record(
        db, principal, action="duplicate.decide", entity_type="duplicate_checks", entity_id=check.id,
        complaint_id=complaint.id,
        details={"candidate_complaint_id": candidate.id, "link_type": link_type.value},
    )


def decide_duplicate(
    db: Session, principal: Principal, complaint_id: int, candidate_id: int, link_type: DuplicateLinkType
) -> list[DuplicateCandidate]:
    """Record L1's choice for one possible duplicate: not a duplicate, a duplicate, or related (UC-L1-03)."""
    complaint = find_editable(db, complaint_id)
    candidate = db.scalar(
        select(Complaint).where(
            Complaint.id == candidate_id, Complaint.id != complaint.id, Complaint.reference_number.is_not(None)
        )
    )
    if candidate is None:
        raise ComplaintError(404, "not_found", "That earlier complaint does not exist.")
    _set_duplicate_choice(db, principal, complaint, candidate, link_type)
    db.commit()
    return lookup.duplicate_candidates(db, complaint)
