"""What the complaint form looks things up in (UC-L1-02, UC-L1-03): lists, records and possible duplicates."""

from difflib import SequenceMatcher

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import PersonType
from app.models import (
    Area,
    Complaint,
    ComplaintCategory,
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
    FormOptions,
    Named,
    PersonLookup,
    RouteStandOption,
    SeverityOption,
    VehicleLookup,
)

MAX_DUPLICATES = 5


def form_options(db: Session) -> FormOptions:
    """The choices behind the form's drop-downs. Portal is left out: only the portal uses it."""
    mediums = db.scalars(
        select(ComplaintMedium)
        .where(ComplaintMedium.is_active, ComplaintMedium.is_system.is_(False))
        .order_by(ComplaintMedium.id)
    )
    categories = db.scalars(select(ComplaintCategory).where(ComplaintCategory.is_active).order_by(ComplaintCategory.id))
    severities = db.scalars(select(Severity).where(Severity.is_active).order_by(Severity.rank))
    places = db.scalars(select(RouteStand).where(RouteStand.is_active).order_by(RouteStand.name))
    return FormOptions(
        mediums=[Named(id=m.id, name=m.name) for m in mediums],
        categories=[Named(id=c.id, name=c.name) for c in categories],
        severities=[SeverityOption(id=s.id, name=s.name, forward_days=s.forward_days) for s in severities],
        routes_stands=[RouteStandOption(id=p.id, name=p.name, kind=p.kind.value, area_id=p.area_id) for p in places],
    )


def find_vehicle(db: Session, number: str) -> Vehicle | None:
    """An active vehicle by its number, ignoring case, spaces and hyphens (ND-7782, nd 7782 and ND7782 match)."""
    wanted = "".join(number.split()).replace("-", "").upper()
    if not wanted:
        return None
    stored = func.upper(func.replace(func.replace(Vehicle.vehicle_number, " ", ""), "-", ""))
    return db.scalar(select(Vehicle).where(stored == wanted, Vehicle.is_active))


def active_permit(db: Session, vehicle: Vehicle) -> Permit | None:
    return db.scalar(select(Permit).where(Permit.vehicle_id == vehicle.id, Permit.is_active).order_by(Permit.id))


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
    candidates = [
        DuplicateCandidate(
            id=other.id,
            reference_number=other.reference_number,
            subject=other.subject,
            status=other.status,
            match=round(SequenceMatcher(None, mine, (other.subject or "").lower()).ratio() * 100),
            link_type=chosen.get(other.id),
        )
        for other in earlier
    ]
    return sorted(candidates, key=lambda c: c.match, reverse=True)[:MAX_DUPLICATES]
