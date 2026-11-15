"""Lists of complaints for Level 1: the Complaints page, the dashboard cards and Find reference.

Only what Level 1 may see is returned: the entry details and where the case went. Nothing from Level 2's
review (reasoning, decision, AI output) is read here.
"""

from datetime import datetime, timedelta

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.enums import ComplaintStatus
from app.core.timezone import LOCAL
from app.models import (
    Area,
    Complaint,
    ComplaintCategory,
    ComplaintDutySnapshot,
    ComplaintTargetType,
    DuplicateCheck,
    Person,
    Severity,
    User,
)
from app.schemas.l1_dashboard import ComplaintPage, ComplaintRow, ListFilter, ReferenceHit, Scope, TargetFilter
from app.services.complaint_lookup_service import DUPLICATE_WINDOW_DAYS

PAGE_SIZE = 10
EDITABLE = (ComplaintStatus.DRAFT, ComplaintStatus.INCOMPLETE)
# Every case that has left Level 1 (forwarded, or since moved on by Level 2 or Level 3).
LEFT_LEVEL_ONE = (
    ComplaintStatus.FORWARDED,
    ComplaintStatus.UNDER_REVIEW,
    ComplaintStatus.AWAITING_IMPLEMENTATION,
    ComplaintStatus.DONE_AWAITING_APPROVAL,
    ComplaintStatus.ESCALATED,
    ComplaintStatus.CLOSED,
)


def undecided_duplicate():
    """True for a complaint with an earlier registered case on the same bus that Level 1 has not yet decided on."""
    earlier = aliased(Complaint)
    decided = exists().where(DuplicateCheck.complaint_id == Complaint.id, DuplicateCheck.candidate_complaint_id == earlier.id)
    return exists().where(
        earlier.vehicle_id == Complaint.vehicle_id,
        earlier.id != Complaint.id,
        earlier.reference_number.is_not(None),
        func.coalesce(earlier.registered_at, earlier.created_at) >= datetime.now(LOCAL) - timedelta(days=DUPLICATE_WINDOW_DAYS),
        ~decided,
    )


def _filter_condition(name: ListFilter):
    if name == "forwarded":
        return Complaint.status.in_(LEFT_LEVEL_ONE)
    if name == "duplicates":
        return and_(Complaint.status.in_(EDITABLE), undecided_duplicate())
    return Complaint.status == ComplaintStatus(name)


def accused_status(complaint: Complaint, target: ComplaintTargetType | None, snapshot: ComplaintDutySnapshot | None) -> str:
    """How well the accused person is established, from the data and never from what the client says."""
    person = complaint.subject_person_id
    if person is not None:
        on_duty = None
        if snapshot is not None and target is not None:
            on_duty = {"driver": snapshot.driver_person_id, "conductor": snapshot.conductor_person_id}.get(target.code)
        if on_duty is not None and person == on_duty:
            return "verified_duty"  # the person the verified daily record puts on duty
        if target is not None and target.code == "owner" and person == complaint.owner_person_id:
            return "registered_owner"  # the owner on the authoritative record
        return "directory_only"  # a real person from master data, but not established for this bus and date
    return "unidentified" if complaint.subject_person_text else "none"


def _target_condition(name: str):
    if name == "unclassified":
        return Complaint.target_type_id.is_(None)
    return Complaint.target_type_id == select(ComplaintTargetType.id).where(ComplaintTargetType.code == name).scalar_subquery()


def list_complaints(
    db: Session,
    *,
    status: ListFilter | None,
    target: TargetFilter | None,
    scope: Scope,
    officer_id: int,
    search: str,
    page: int,
    category_id: int | None = None,
    verification: str | None = None,
) -> ComplaintPage:
    base = []
    if category_id is not None:
        base.append(Complaint.category_id == category_id)
    if verification == "failed":  # the bus could not be verified against the daily records
        base.append(Complaint.bus_verification.in_(("not_found", "not_operated", "trip_cancelled", "unverified")))
    elif verification == "non_operating":  # the bus did not operate, or the trip was cancelled
        base.append(Complaint.bus_verification.in_(("not_operated", "trip_cancelled")))
    if scope == "mine":
        base.append(Complaint.entered_by_user_id == officer_id)  # only what this officer registered
    term = search.strip()
    if term:
        base.append(
            or_(
                Complaint.reference_number.icontains(term, autoescape=True),
                Complaint.subject.icontains(term, autoescape=True),
                Complaint.complainant_name.icontains(term, autoescape=True),
                Complaint.vehicle_number_entered.icontains(term, autoescape=True),
            )
        )
    by_target = [_target_condition(target)] if target else []
    by_status = [_filter_condition(status)] if status else []

    def count(*conditions) -> int:
        return db.scalar(select(func.count()).select_from(Complaint).where(*conditions)) or 0

    counts = {"all": count(*base, *by_target)}
    for name in ("draft", "incomplete", "submitted", "forwarded", "rejected", "duplicates"):
        counts[name] = count(*base, *by_target, _filter_condition(name))
    target_counts = {"all": count(*base, *by_status)}
    for name in ("driver", "conductor", "owner", "bus_service", "other", "unclassified"):
        target_counts[name] = count(*base, *by_status, _target_condition(name))

    total = counts[status] if status else counts["all"]
    page = min(page, max(1, -(-total // PAGE_SIZE)))  # a page past the end shows the last one
    rows = db.execute(
        select(Complaint, Area.name, Severity.name, undecided_duplicate(), ComplaintTargetType, ComplaintCategory.name,
               Person.full_name, ComplaintDutySnapshot)
        .outerjoin(Area, Area.id == Complaint.area_id)
        .outerjoin(Severity, Severity.id == Complaint.severity_id)
        .outerjoin(ComplaintTargetType, ComplaintTargetType.id == Complaint.target_type_id)
        .outerjoin(ComplaintCategory, ComplaintCategory.id == Complaint.category_id)
        .outerjoin(Person, Person.id == Complaint.subject_person_id)
        .outerjoin(ComplaintDutySnapshot, ComplaintDutySnapshot.complaint_id == Complaint.id)
        .where(*base, *by_target, *by_status)
        .order_by(Complaint.updated_at.desc(), Complaint.id.desc())
        .limit(PAGE_SIZE)
        .offset((page - 1) * PAGE_SIZE)
    ).all()
    items = [
        ComplaintRow(
            id=c.id,
            reference_number=c.reference_number,
            status=c.status,
            subject=c.subject,
            vehicle_number=c.vehicle_number_entered,
            target_code=t.code if t else None,
            target_name=t.name if t else None,
            accused_name=person_name or c.subject_person_text,
            accused_status=accused_status(c, t, snapshot),
            category_name=category,
            complainant=c.complainant_name,
            area_name=area,
            severity_name=severity,
            complaint_date=c.complaint_date,
            updated_at=c.updated_at,
            editable=c.status in EDITABLE,
            possible_duplicate=dup and c.status in EDITABLE,
            bus_verification=c.bus_verification,
            synthetic=c.synthetic_batch_id is not None,
        )
        for c, area, severity, dup, t, category, person_name, snapshot in rows
    ]
    return ComplaintPage(items=items, total=total, page=page, page_size=PAGE_SIZE, counts=counts, target_counts=target_counts)

def find_by_reference(db: Session, reference: str) -> ReferenceHit | None:
    """The case with this reference number (any case that has one), or None."""
    row = db.execute(
        select(Complaint, Area.name, User.full_name)
        .outerjoin(Area, Area.id == Complaint.area_id)
        .outerjoin(User, User.id == Complaint.assigned_l2_user_id)
        .where(func.upper(Complaint.reference_number) == reference.strip().upper())
    ).one_or_none()
    if row is None:
        return None
    complaint, area, officer = row
    return ReferenceHit(
        id=complaint.id,
        reference_number=complaint.reference_number,
        status=complaint.status,
        editable=complaint.status in EDITABLE,
        subject=complaint.subject,
        area_name=area,
        forwarded_to=officer,
        forwarded_at=complaint.forwarded_at,
    )
