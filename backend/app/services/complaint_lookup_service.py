"""What the complaint form looks things up in (UC-L1-02, UC-L1-03): lists, records and possible duplicates."""

from datetime import datetime, timedelta
from difflib import SequenceMatcher

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import PersonType
from app.core.timezone import LOCAL
from app.models import (
    Area,
    Complaint,
    ComplaintCategory,
    ComplaintCategoryTarget,
    ComplaintTargetType,
    ComplaintMedium,
    DuplicateCheck,
    Permit,
    Person,
    RouteStand,
    Severity,
    Vehicle,
)
from app.schemas.l1_complaints import (
    DuplicateCandidate,
    CategoryOption,
    FormOptions,
    Named,
    PersonLookup,
    RouteStandOption,
    SeverityOption,
    TargetOption,
    VehicleLookup,
)

MAX_DUPLICATES = 5
# Only cases registered in this many days count as possible duplicates of a new complaint on the same bus.
DUPLICATE_WINDOW_DAYS = 30
# A possible duplicate matching at least this much has to be decided before forwarding. Weaker ones are still shown.
MUST_DECIDE_MATCH = 40


def form_options(db: Session) -> FormOptions:
    """The choices behind the form's drop-downs. Portal is left out: only the portal uses it."""
    mediums = db.scalars(
        select(ComplaintMedium)
        .where(ComplaintMedium.is_active, ComplaintMedium.is_system.is_(False))
        .order_by(ComplaintMedium.id)
    )
    severities = db.scalars(select(Severity).where(Severity.is_active).order_by(Severity.rank))
    places = db.scalars(select(RouteStand).where(RouteStand.is_active).order_by(RouteStand.name))
    return FormOptions(
        mediums=[Named(id=m.id, name=m.name) for m in mediums],
        categories=_categories(db),
        targets=list_targets(db),
        severities=[SeverityOption(id=s.id, name=s.name, forward_days=s.forward_days) for s in severities],
        routes_stands=[RouteStandOption(id=p.id, name=p.name, kind=p.kind.value, area_id=p.area_id) for p in places],
    )


def _categories(db: Session) -> list[CategoryOption]:
    approved: dict[int, list[int]] = {}
    for category_id, target_id in db.execute(select(ComplaintCategoryTarget.category_id, ComplaintCategoryTarget.target_type_id)):
        approved.setdefault(category_id, []).append(target_id)
    rows = db.scalars(select(ComplaintCategory).where(ComplaintCategory.is_active).order_by(ComplaintCategory.id))
    return [CategoryOption(id=c.id, name=c.name, target_ids=approved.get(c.id, [])) for c in rows]


def list_targets(db: Session) -> list[TargetOption]:
    """Who a complaint can be against."""
    rows = db.scalars(
        select(ComplaintTargetType).where(ComplaintTargetType.is_active).order_by(ComplaintTargetType.sort_order)
    )
    return [TargetOption(id=t.id, name=t.name, code=t.code) for t in rows]


def allowed_categories(db: Session, target_id: int | None) -> list[CategoryOption]:
    """The issue categories open to a target. Where no mapping has been approved for it, that is every category."""
    options = _categories(db)
    if target_id is None:
        return options
    mapped = [c for c in options if target_id in c.target_ids]
    has_mapping = db.scalar(select(ComplaintCategoryTarget.category_id).where(ComplaintCategoryTarget.target_type_id == target_id).limit(1))
    return mapped if has_mapping is not None else options


def find_vehicle(db: Session, number: str) -> Vehicle | None:
    """An active vehicle by its number, ignoring case, spaces and hyphens (ND-7782, nd 7782 and ND7782 match)."""
    wanted = "".join(number.split()).replace("-", "").upper()
    if not wanted:
        return None
    stored = func.upper(func.replace(func.replace(Vehicle.vehicle_number, " ", ""), "-", ""))
    return db.scalar(select(Vehicle).where(stored == wanted, Vehicle.is_active))


def active_permit(db: Session, vehicle: Vehicle) -> Permit | None:
    return db.scalar(select(Permit).where(Permit.vehicle_id == vehicle.id, Permit.is_active).order_by(Permit.id))


def find_permit_vehicle(db: Session, number: str) -> Vehicle | None:
    """The active vehicle holding the permit with this number (spaces and case ignored), or None."""
    wanted = "".join(number.split()).upper()
    permit = db.scalar(
        select(Permit).where(func.upper(func.replace(Permit.permit_number, " ", "")) == wanted, Permit.is_active)
    )
    vehicle = db.get(Vehicle, permit.vehicle_id) if permit else None
    return vehicle if vehicle is not None and vehicle.is_active else None


def vehicle_lookup(db: Session, vehicle: Vehicle) -> VehicleLookup:
    permit = active_permit(db, vehicle)
    owner = db.get(Person, vehicle.owner_person_id) if vehicle.owner_person_id else None
    past = db.scalar(
        select(func.count())
        .select_from(Complaint)
        .where(Complaint.vehicle_id == vehicle.id, Complaint.reference_number.is_not(None))
    )
    return VehicleLookup(
        id=vehicle.id,
        vehicle_number=vehicle.vehicle_number,
        vehicle_type=vehicle.vehicle_type,
        area_id=vehicle.registered_area_id,
        area_name=db.scalar(select(Area.name).where(Area.id == vehicle.registered_area_id)),
        permit_number=permit.permit_number if permit else None,
        owner_name=owner.full_name if owner else None,
        owner_person_id=owner.id if owner else None,
        past_complaints=past or 0,
    )


def search_people(db: Session, *, search: str, person_type: PersonType | None) -> list[PersonLookup]:
    term = search.strip()
    if not term:
        return []
    query = select(Person).where(Person.is_active, Person.full_name.icontains(term, autoescape=True))
    if person_type:
        query = query.where(Person.person_type == person_type)
    people = db.scalars(query.order_by(Person.full_name).limit(10))
    return [PersonLookup(id=p.id, full_name=p.full_name, person_type=p.person_type) for p in people]


def duplicate_candidates(db: Session, complaint: Complaint) -> list[DuplicateCandidate]:
    """Earlier registered complaints against the same vehicle, the most alike first.

    Nothing is merged or deleted: L1 records a choice for each one separately.
    """
    if complaint.vehicle_id is None:
        return []
    earlier = db.scalars(
        select(Complaint).where(
            Complaint.vehicle_id == complaint.vehicle_id,
            Complaint.id != complaint.id,
            Complaint.reference_number.is_not(None),
            func.coalesce(Complaint.registered_at, Complaint.created_at) >= datetime.now(LOCAL) - timedelta(days=DUPLICATE_WINDOW_DAYS),
        )
    )
    chosen = dict(
        db.execute(
            select(DuplicateCheck.candidate_complaint_id, DuplicateCheck.link_type).where(
                DuplicateCheck.complaint_id == complaint.id
            )
        ).all()
    )
    mine = (complaint.subject or "").lower()
    candidates = []
    for other in earlier:
        match = round(SequenceMatcher(None, mine, (other.subject or "").lower()).ratio() * 100)
        candidates.append(
            DuplicateCandidate(
                id=other.id,
                reference_number=other.reference_number,
                subject=other.subject,
                status=other.status,
                match=match,
                link_type=chosen.get(other.id),
                must_decide=match >= MUST_DECIDE_MATCH,
            )
        )
    return sorted(candidates, key=lambda c: c.match, reverse=True)[:MAX_DUPLICATES]
