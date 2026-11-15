"""Daily operation records, kept by System Admin: trips, who was on duty, and bus ownership.

A record moves draft, approved, published, one step at a time, and every step is written to the audit
trail. Approving a trip also verifies the people on its duty record. Level 1 sees only published records
(see bus_lookup_service), so nothing here is visible to the officers until Admin publishes it.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.core.enums import DutyRecordStatus, PersonType
from app.core.timezone import LOCAL
from app.models import DailyTrip, OwnerAssignment, Permit, Person, RouteStand, TripDuty, Vehicle
from app.schemas.admin_duty_records import OwnerAssignmentIn, OwnerAssignmentOut, TripIn, TripList, TripOut
from app.services import audit_service
from app.services import complaint_lookup_service as lookup
from app.services.auth_service import Principal

LIST_LIMIT = 200


class DutyRecordError(Exception):
    """A rule the request breaks; the route turns it into a clean HTTP error."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


# ---------------------------------------------------------------- checks


def _vehicle(db: Session, number: str) -> Vehicle:
    vehicle = lookup.find_vehicle(db, number)
    if vehicle is None:
        raise DutyRecordError(422, "unknown_vehicle", "No vehicle on record has that number.")
    return vehicle


def _person(db: Session, person_id: int | None, kind: PersonType, label: str) -> Person | None:
    if person_id is None:
        return None
    person = db.scalar(select(Person).where(Person.id == person_id, Person.is_active, Person.person_type == kind))
    if person is None:
        raise DutyRecordError(422, f"unknown_{label}", f"Choose a valid {label} from the records.")
    return person


def _commit(db: Session, conflict: str) -> None:
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise DutyRecordError(409, "conflict", conflict) from None


# ---------------------------------------------------------------- trips


def _trip_rows():
    driver, conductor = aliased(Person), aliased(Person)
    return (
        select(DailyTrip, Vehicle.vehicle_number, Permit.permit_number, RouteStand.name, driver.full_name,
               conductor.full_name, TripDuty.verified_at)
        .join(Vehicle, Vehicle.id == DailyTrip.vehicle_id)
        .join(Permit, Permit.id == DailyTrip.permit_id)
        .join(RouteStand, RouteStand.id == DailyTrip.route_stand_id)
        .outerjoin(TripDuty, TripDuty.trip_id == DailyTrip.id)
        .outerjoin(driver, driver.id == TripDuty.driver_person_id)
        .outerjoin(conductor, conductor.id == TripDuty.conductor_person_id)
    )


def _trip_out(row) -> TripOut:
    trip, bus, permit, route, driver, conductor, verified_at = row
    return TripOut(
        id=trip.id,
        service_date=trip.service_date,
        vehicle_number=bus,
        permit_number=permit,
        route=route,
        departure_time=trip.departure_time,
        origin=trip.origin,
        destination=trip.destination,
        status=trip.status,
        driver=driver,
        conductor=conductor,
        duty_verified=verified_at is not None,
        published_at=trip.published_at,
    )


def get_trip(db: Session, trip_id: int) -> TripOut:
    row = db.execute(_trip_rows().where(DailyTrip.id == trip_id)).one_or_none()
    if row is None:
        raise DutyRecordError(404, "not_found", "That trip does not exist.")
    return _trip_out(row)


def list_trips(db: Session, *, service_date, status: DutyRecordStatus | None) -> TripList:
    conditions = []
    if service_date:
        conditions.append(DailyTrip.service_date == service_date)
    if status:
        conditions.append(DailyTrip.status == status)
    total = db.scalar(select(func.count()).select_from(DailyTrip).where(*conditions)) or 0
    rows = db.execute(
        _trip_rows()
        .where(*conditions)
        .order_by(DailyTrip.service_date.desc(), DailyTrip.departure_time, DailyTrip.id)
        .limit(LIST_LIMIT)
    ).all()
    return TripList(items=[_trip_out(r) for r in rows], total=total)


def create_trip(db: Session, admin: Principal, data: TripIn) -> TripOut:
    vehicle = _vehicle(db, data.vehicle_number)
    if data.permit_number:
        permit = db.scalar(
            select(Permit).where(Permit.permit_number == data.permit_number.strip(), Permit.vehicle_id == vehicle.id)
        )
        if permit is None:
            raise DutyRecordError(422, "permit_mismatch", "That permit does not belong to this bus.")
    else:
        permit = lookup.active_permit(db, vehicle)
        if permit is None:
            raise DutyRecordError(422, "no_permit", "This bus has no active permit on record.")
    if db.scalar(select(RouteStand.id).where(RouteStand.id == data.route_stand_id, RouteStand.is_active)) is None:
        raise DutyRecordError(422, "unknown_route", "Choose a valid route.")
    driver = _person(db, data.driver_person_id, PersonType.DRIVER, "driver")
    conductor = _person(db, data.conductor_person_id, PersonType.CONDUCTOR, "conductor")

    trip = DailyTrip(
        service_date=data.service_date,
        vehicle_id=vehicle.id,
        permit_id=permit.id,
        route_stand_id=data.route_stand_id,
        departure_time=data.departure_time,
        origin=data.origin.strip(),
        destination=data.destination.strip(),
        created_by_user_id=admin.id,
    )
    db.add(trip)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise DutyRecordError(
            409, "duplicate_trip", "That bus already has a trip at that time on that date."
        ) from None
    if driver or conductor:
        db.add(
            TripDuty(
                trip_id=trip.id,
                driver_person_id=driver.id if driver else None,
                conductor_person_id=conductor.id if conductor else None,
            )
        )
    audit_service.record(
        db, admin, action="trip.create", entity_type="daily_trips", entity_id=trip.id,
        details={"vehicle": vehicle.vehicle_number, "service_date": data.service_date.isoformat()},
    )
    _commit(db, "That trip could not be saved. Try again.")
    return get_trip(db, trip.id)


def _step(db: Session, admin: Principal, trip_id: int, *, frm: DutyRecordStatus, to: DutyRecordStatus) -> TripOut:
    trip = db.scalar(select(DailyTrip).where(DailyTrip.id == trip_id).with_for_update())
    if trip is None:
        raise DutyRecordError(404, "not_found", "That trip does not exist.")
    _advance(trip, admin, frm, to)
    if to == DutyRecordStatus.APPROVED:
        duty = db.scalar(select(TripDuty).where(TripDuty.trip_id == trip.id))
        if duty is not None:  # approving verifies the people on duty
            duty.verified_by_user_id, duty.verified_at = admin.id, datetime.now(LOCAL)
    audit_service.record(
        db, admin, action=f"trip.{to.value}", entity_type="daily_trips", entity_id=trip.id,
        details={"from": frm.value, "to": to.value},
    )
    _commit(db, "That trip was just changed by someone else. Refresh and try again.")
    return get_trip(db, trip.id)


def _advance(row, admin: Principal, frm: DutyRecordStatus, to: DutyRecordStatus) -> None:
    """Move a trip or an ownership record one step on, as Admin."""
    if row.status != frm:
        raise DutyRecordError(
            409, "wrong_status", f"Only a {frm.value} record can be made {to.value}. This one is {row.status.value}."
        )
    now = datetime.now(LOCAL)
    if to == DutyRecordStatus.APPROVED:
        row.approved_by_user_id, row.approved_at = admin.id, now
    else:
        row.published_by_user_id, row.published_at = admin.id, now
    row.status = to


def approve_trip(db: Session, admin: Principal, trip_id: int) -> TripOut:
    return _step(db, admin, trip_id, frm=DutyRecordStatus.DRAFT, to=DutyRecordStatus.APPROVED)


def publish_trip(db: Session, admin: Principal, trip_id: int) -> TripOut:
    return _step(db, admin, trip_id, frm=DutyRecordStatus.APPROVED, to=DutyRecordStatus.PUBLISHED)


# ---------------------------------------------------------------- ownership


def _assignment_out(db: Session, row: OwnerAssignment) -> OwnerAssignmentOut:
    return OwnerAssignmentOut(
        id=row.id,
        vehicle_number=db.scalar(select(Vehicle.vehicle_number).where(Vehicle.id == row.vehicle_id)),
        owner=db.scalar(select(Person.full_name).where(Person.id == row.owner_person_id)),
        valid_from=row.valid_from,
        valid_to=row.valid_to,
        status=row.status,
        published_at=row.published_at,
    )


def create_owner_assignment(db: Session, admin: Principal, data: OwnerAssignmentIn) -> OwnerAssignmentOut:
    vehicle = _vehicle(db, data.vehicle_number)
    owner = _person(db, data.owner_person_id, PersonType.OWNER, "owner")
    if data.valid_to is not None and data.valid_to < data.valid_from:
        raise DutyRecordError(422, "invalid_period", "The end date cannot be before the start date.")
    row = OwnerAssignment(
        vehicle_id=vehicle.id, owner_person_id=owner.id, valid_from=data.valid_from, valid_to=data.valid_to,
        created_by_user_id=admin.id,
    )
    db.add(row)
    db.flush()
    audit_service.record(
        db, admin, action="owner_assignment.create", entity_type="owner_assignments", entity_id=row.id,
        details={"vehicle": vehicle.vehicle_number, "owner_person_id": owner.id},
    )
    _commit(db, "That ownership record could not be saved. Try again.")
    return _assignment_out(db, row)


def _step_assignment(
    db: Session, admin: Principal, assignment_id: int, *, frm: DutyRecordStatus, to: DutyRecordStatus
) -> OwnerAssignmentOut:
    row = db.scalar(select(OwnerAssignment).where(OwnerAssignment.id == assignment_id).with_for_update())
    if row is None:
        raise DutyRecordError(404, "not_found", "That ownership record does not exist.")
    _advance(row, admin, frm, to)
    audit_service.record(
        db, admin, action=f"owner_assignment.{to.value}", entity_type="owner_assignments", entity_id=row.id,
        details={"from": frm.value, "to": to.value},
    )
    _commit(db, "That record was just changed by someone else. Refresh and try again.")
    return _assignment_out(db, row)


def approve_owner_assignment(db: Session, admin: Principal, assignment_id: int) -> OwnerAssignmentOut:
    return _step_assignment(db, admin, assignment_id, frm=DutyRecordStatus.DRAFT, to=DutyRecordStatus.APPROVED)


def publish_owner_assignment(db: Session, admin: Principal, assignment_id: int) -> OwnerAssignmentOut:
    return _step_assignment(db, admin, assignment_id, frm=DutyRecordStatus.APPROVED, to=DutyRecordStatus.PUBLISHED)
