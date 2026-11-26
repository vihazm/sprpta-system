"""The Level 1 complaint form (UC-L1-01 to UC-L1-10): save, finish later, forward or reject.

Statuses follow the System Flow Document section 3.3. L1 may only move a
complaint out of Draft, Incomplete or Submitted (a portal complaint it has not
checked yet), and every move is written to the audit trail. A portal complaint
goes through the same form; only who sent it and how stay as the complainant's
account gave them. The reference number is issued when the complaint is first
saved as Incomplete or forwarded; that moment also starts the time-target clock,
and Incomplete pauses it. The registration message (MSG-1) goes to the complainant
then, if a phone or email is on record.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import ComplaintStatus, DuplicateLinkType, MessageType, PersonType, RejectionType
from app.core.identifiers import normalise_identifier
from app.core.roles import UserRole
from app.core.timezone import LOCAL
from app.models import (
    Area,
    Complaint,
    ComplaintAttachment,
    ComplaintCategory,
    ComplaintDutySnapshot,
    ComplaintTargetType,
    ComplaintMedium,
    DailyTrip,
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
    ComplaintOut,
    DuplicateCandidate,
    DutySnapshotOut,
    RejectBody,
)
from app.services import audit_service, messaging_service
from app.services import complaint_lookup_service as lookup
from app.services.complaint_list_service import OPEN_AT_LEVEL_ONE, accused_status
from app.services.auth_service import Principal


class ComplaintError(Exception):
    """A rule the request breaks; the route turns it into a clean HTTP error."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


# ---------------------------------------------------------------- reading


def _duty_out(s: ComplaintDutySnapshot | None) -> DutySnapshotOut | None:
    if s is None:
        return None
    return DutySnapshotOut(
        trip_id=s.trip_id,
        service_date=s.service_date,
        bus_number=s.bus_number,
        permit_number=s.permit_number,
        route=s.route_name,
        origin=s.origin,
        destination=s.destination,
        departure_time=s.departure_time,
        owner_person_id=s.owner_person_id,
        owner_name=s.owner_name,
        driver_person_id=s.driver_person_id,
        driver_name=s.driver_name,
        conductor_person_id=s.conductor_person_id,
        conductor_name=s.conductor_name,
        verification_status=s.verification_status,
    )


def _out(db: Session, complaint: Complaint) -> ComplaintOut:
    vehicle = db.get(Vehicle, complaint.vehicle_id) if complaint.vehicle_id else None
    officer = db.get(User, complaint.assigned_l2_user_id) if complaint.assigned_l2_user_id else None
    area = db.get(Area, complaint.area_id) if complaint.area_id else None
    person = db.get(Person, complaint.subject_person_id) if complaint.subject_person_id else None
    earlier = db.get(Complaint, complaint.duplicate_of_complaint_id) if complaint.duplicate_of_complaint_id else None
    snapshot = _snapshot_of(db, complaint)
    target = db.get(ComplaintTargetType, complaint.target_type_id) if complaint.target_type_id else None
    attachments = db.scalars(
        select(ComplaintAttachment)
        .where(ComplaintAttachment.complaint_id == complaint.id, ComplaintAttachment.removed_at.is_(None))
        .order_by(ComplaintAttachment.id)
    )
    return ComplaintOut(
        id=complaint.id,
        reference_number=complaint.reference_number,
        status=complaint.status,
        via_portal=complaint.submitted_via_portal,
        registration_message_sent=complaint.id in messaging_service.sent_to(db, [complaint.id], MessageType.REGISTERED),
        medium_id=complaint.medium_id,
        is_anonymous=complaint.is_anonymous,
        complainant_name=complaint.complainant_name,
        mobile=complaint.contact_phone,
        email=complaint.contact_email,
        complaint_date=complaint.complaint_date,
        incident_time=complaint.incident_time,
        incident_location=complaint.incident_location,
        trip_id=snapshot.trip_id if snapshot else None,
        duty=_duty_out(snapshot),
        vehicle_number=complaint.vehicle_number_entered,
        vehicle=lookup.vehicle_lookup(db, vehicle) if vehicle else None,
        permit_id=complaint.permit_id,
        owner_person_id=complaint.owner_person_id,
        subject_person_id=complaint.subject_person_id,
        subject_person_text=complaint.subject_person_text,
        subject_person_name=person.full_name if person else complaint.subject_person_text,
        route_stand_id=complaint.route_stand_id,
        category_id=complaint.category_id,
        category_name=db.scalar(select(ComplaintCategory.name).where(ComplaintCategory.id == complaint.category_id)),
        target_type_id=complaint.target_type_id,
        complainant_type=complaint.complainant_type,
        bus_verification=complaint.bus_verification,
        target_code=target.code if target else None,
        target_name=target.name if target else None,
        accused_status=accused_status(complaint, target, snapshot),
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
    if complaint.withdrawn_at is not None:
        raise ComplaintError(409, "withdrawn", "The complainant deleted this complaint, so there is nothing left to check.")
    if complaint.status not in OPEN_AT_LEVEL_ONE:
        raise ComplaintError(
            409, "not_editable", "Only a draft, an incomplete or an unchecked portal complaint can be changed. This one is already past that."
        )
    return complaint


def get_complaint(db: Session, complaint_id: int) -> ComplaintOut:
    return _out(db, find_complaint(db, complaint_id))


def get_duplicates(db: Session, complaint_id: int) -> list[DuplicateCandidate]:
    return lookup.duplicate_candidates(db, find_complaint(db, complaint_id))


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


def _mobile(raw: str | None) -> str | None:
    raw = _clean(raw)
    if raw is None:
        return None
    parsed = normalise_identifier(raw)
    if parsed is None or parsed[0] != "phone":
        raise ComplaintError(422, "invalid_mobile", "Enter a valid Sri Lankan mobile number.")
    return parsed[1]


def _email(raw: str | None) -> str | None:
    raw = _clean(raw)
    if raw is None:
        return None
    parsed = normalise_identifier(raw)
    if parsed is None or parsed[0] != "email":
        raise ComplaintError(422, "invalid_email", "Enter a valid email address.")
    return parsed[1]


def _snapshot_of(db: Session, complaint: Complaint) -> ComplaintDutySnapshot | None:
    return db.scalar(select(ComplaintDutySnapshot).where(ComplaintDutySnapshot.complaint_id == complaint.id))


def _keep_snapshot(
    db: Session, principal: Principal, complaint: Complaint, snapshot: ComplaintDutySnapshot | None, trip_id: int
) -> ComplaintDutySnapshot:
    """The snapshot of the chosen daily record. A different record is read afresh and must be published."""
    if snapshot is not None and snapshot.trip_id == trip_id:
        return snapshot  # the same record as before: keep what was captured, even if it was withdrawn since

    from app.services import bus_lookup_service  # imported here: it imports ComplaintError from this module

    record = bus_lookup_service.trip_details(db, trip_id)
    if snapshot is None:
        snapshot = ComplaintDutySnapshot(complaint_id=complaint.id)
        db.add(snapshot)
    snapshot.trip_id = record.trip_id
    snapshot.service_date = record.service_date
    snapshot.bus_number = record.bus_number
    snapshot.permit_number = record.permit_number
    snapshot.route_name = record.route
    snapshot.origin = record.origin
    snapshot.destination = record.destination
    snapshot.departure_time = record.departure_time
    snapshot.owner_person_id, snapshot.owner_name = record.owner.person_id, record.owner.name
    # Only people Admin verified are stored: an unverified or missing one stays empty, never guessed.
    snapshot.driver_person_id, snapshot.driver_name = record.driver.person_id, record.driver.name
    snapshot.conductor_person_id, snapshot.conductor_name = record.conductor.person_id, record.conductor.name
    snapshot.verification_status = record.verification_status
    db.flush()
    audit_service.record(
        db, principal, action="complaint.bus_selected", entity_type="complaints", entity_id=complaint.id,
        complaint_id=complaint.id, details={"trip_id": trip_id, "bus_number": record.bus_number},
    )
    return snapshot


# The kind of person each target names. A bus or service complaint names no person; Other may name anyone.
_PERSON_FOR_TARGET = {"driver": PersonType.DRIVER, "conductor": PersonType.CONDUCTOR, "owner": PersonType.OWNER}


def _check_target(db: Session, data: ComplaintForm) -> ComplaintTargetType | None:
    """The target the complaint is against, after checking it fits the category and the person picked."""
    if data.target_type_id is None:
        return None
    target = db.scalar(
        select(ComplaintTargetType).where(ComplaintTargetType.id == data.target_type_id, ComplaintTargetType.is_active)
    )
    if target is None:
        raise ComplaintError(422, "unknown_target", "Choose who the complaint is against.")
    if data.category_id is not None and data.category_id not in {c.id for c in lookup.allowed_categories(db, target.id)}:
        raise ComplaintError(422, "invalid_category", f"That issue category is not used for a {target.name.lower()} complaint.")
    if target.code == "bus_service" and (data.subject_person_id is not None or _clean(data.subject_person_text)):
        raise ComplaintError(422, "accused_not_allowed", "A complaint against the bus or service does not name a person.")
    wanted = _PERSON_FOR_TARGET.get(target.code)
    if wanted is not None and data.subject_person_id is not None:
        person = db.get(Person, data.subject_person_id)
        if person is None or person.person_type != wanted:
            raise ComplaintError(422, "wrong_person_type", f"A {target.name.lower()} complaint needs a {wanted.value}.")
    return target


def _apply_form(db: Session, principal: Principal, complaint: Complaint, data: ComplaintForm) -> None:
    portal = complaint.submitted_via_portal
    if not portal:
        must_exist(db, ComplaintMedium, data.medium_id, "medium", ComplaintMedium.is_system.is_(False))
    must_exist(db, ComplaintCategory, data.category_id, "category")
    must_exist(db, Severity, data.severity_id, "severity")
    must_exist(db, RouteStand, data.route_stand_id, "route_stand")
    must_exist(db, Person, data.subject_person_id, "person")
    target = _check_target(db, data)
    if data.complaint_date and data.complaint_date > datetime.now(LOCAL).date():
        raise ComplaintError(422, "future_date", "The date cannot be in the future.")

    # A portal complaint keeps the Portal medium and the contact details of the account that sent it.
    if not portal:
        complaint.is_anonymous = data.is_anonymous
        if data.is_anonymous:
            complaint.complainant_name = complaint.contact_phone = complaint.contact_email = None
        else:
            complaint.complainant_name = _clean(data.complainant_name)
            complaint.contact_phone = _mobile(data.mobile)
            complaint.contact_email = _email(data.email)
        complaint.medium_id = data.medium_id

    complaint.incident_time = data.incident_time
    complaint.incident_location = _clean(data.incident_location)
    complaint.subject_person_id = data.subject_person_id
    complaint.subject_person_text = _clean(data.subject_person_text)
    complaint.category_id = data.category_id
    complaint.target_type_id = target.id if target else None
    complaint.complainant_type = data.complainant_type
    complaint.severity_id = data.severity_id
    complaint.subject = _clean(data.subject)
    complaint.description = _clean(data.description)

    number = _clean(data.vehicle_number)
    snapshot = _snapshot_of(db, complaint)
    if data.trip_id is None:
        if snapshot is not None:  # the selected bus was cleared: its verified details go with it
            db.delete(snapshot)
            audit_service.record(
                db, principal, action="complaint.bus_cleared", entity_type="complaints", entity_id=complaint.id,
                complaint_id=complaint.id, details={"trip_id": snapshot.trip_id},
            )
        vehicle = lookup.find_vehicle(db, number) if number else None
        permit = lookup.active_permit(db, vehicle) if vehicle else None
        complaint.bus_verification = "unverified" if vehicle else ("not_found" if number else None)
        if vehicle is not None and data.complaint_date is not None:
            from app.services import bus_lookup_service  # imported here: it imports ComplaintError from this module

            on_date, _reason = bus_lookup_service.bus_status_on(db, vehicle.id, data.complaint_date)
            if on_date == "did_not_operate":  # the records say the bus was not running that day
                complaint.bus_verification = "not_operated"
            elif on_date == "cancelled":
                complaint.bus_verification = "trip_cancelled"
        complaint.complaint_date = data.complaint_date
        complaint.route_stand_id = data.route_stand_id
        complaint.permit_id = permit.id if permit else None
        complaint.owner_person_id = vehicle.owner_person_id if vehicle else None
    else:
        # The daily record decides the bus, permit, owner, route and incident date. None of them is read from the
        # request, so nothing in it can pass as verified.
        trip = db.get(DailyTrip, data.trip_id)
        if trip is None:
            raise ComplaintError(404, "trip_not_found", "That record is not available. Search again.")
        snapshot = _keep_snapshot(db, principal, complaint, snapshot, trip.id)
        vehicle = db.get(Vehicle, trip.vehicle_id)
        typed = lookup.find_vehicle(db, number) if number else None
        if typed is not None and typed.id != vehicle.id:
            raise ComplaintError(422, "trip_mismatch", "The selected bus record is for another bus. Choose the bus again.")
        reported = number  # what the officer typed stays as the reported number if it was not this bus
        number = vehicle.vehicle_number
        corrected = bool(reported) and typed is None  # a number that matches no bus on record was a typing mistake
        if corrected:
            number = reported
        complaint.bus_verification = "corrected" if corrected else "verified"
        if trip.trip_status == "cancelled":  # the record says this trip did not run
            complaint.bus_verification = "trip_cancelled"
        complaint.complaint_date = trip.service_date
        complaint.route_stand_id = trip.route_stand_id
        complaint.permit_id = trip.permit_id
        complaint.owner_person_id = snapshot.owner_person_id

    complaint.vehicle_number_entered = number
    complaint.vehicle_id = vehicle.id if vehicle else None
    if vehicle or not portal:  # until the bus is found, a portal complaint keeps the area the complainant chose
        complaint.area_id = vehicle.registered_area_id if vehicle else None


def _already_created(db: Session, principal: Principal, request_id: str | None) -> Complaint | None:
    if request_id is None:
        return None
    return db.scalar(
        select(Complaint).where(Complaint.entered_by_user_id == principal.id, Complaint.client_request_id == request_id)
    )


def create_draft(db: Session, principal: Principal, data: ComplaintForm) -> ComplaintOut:
    """Save a new complaint as a draft. The complaint and its bus snapshot are saved together or not at all."""
    earlier = _already_created(db, principal, data.client_request_id)
    if earlier is not None:  # this save was sent before: hand back what it made
        return _out(db, earlier)

    complaint = Complaint(
        status=ComplaintStatus.DRAFT, entered_by_user_id=principal.id, client_request_id=data.client_request_id
    )
    db.add(complaint)
    try:
        db.flush()  # gives the complaint its id for the snapshot and the audit row; a refused form rolls it back
    except IntegrityError:  # the same save arrived twice at once, and the other one won
        db.rollback()
        earlier = _already_created(db, principal, data.client_request_id)
        if earlier is None:
            raise
        return _out(db, earlier)
    _apply_form(db, principal, complaint, data)
    audit_service.record(
        db, principal, action="complaint.create", entity_type="complaints", entity_id=complaint.id,
        complaint_id=complaint.id, to_status=ComplaintStatus.DRAFT,
    )
    db.commit()
    return _out(db, complaint)


def update_complaint(db: Session, principal: Principal, complaint_id: int, data: ComplaintForm) -> ComplaintOut:
    complaint = find_editable(db, complaint_id)
    _apply_form(db, principal, complaint, data)
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
    """Draft or Submitted to Incomplete: issues the reference number and pauses the clock."""
    complaint = find_editable(db, complaint_id)
    if complaint.status == ComplaintStatus.INCOMPLETE:
        raise ComplaintError(409, "already_incomplete", "This complaint is already incomplete.")
    now = datetime.now(LOCAL)
    _issue_reference(complaint, now)
    complaint.paused_since = now
    _move(db, principal, complaint, ComplaintStatus.INCOMPLETE, "complaint.incomplete")
    db.commit()
    messaging_service.send_case_message(db, complaint, MessageType.REGISTERED)
    return _out(db, complaint)


def _missing_details(complaint: Complaint) -> list[str]:
    needed = {
        "medium": complaint.medium_id,
        "date": complaint.complaint_date,
        "a vehicle that is on record": complaint.vehicle_id,
        "route or stand": complaint.route_stand_id,
        "category": complaint.category_id,
        "who the complaint is against": complaint.target_type_id,
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
    if any(c.link_type is None and c.must_decide for c in lookup.duplicate_candidates(db, complaint)):
        raise ComplaintError(
            409, "duplicate_undecided", "Choose for every close possible duplicate whether it is a duplicate, related or not."
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
    messaging_service.send_case_message(db, complaint, MessageType.REGISTERED)  # unless it went out at Incomplete
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
