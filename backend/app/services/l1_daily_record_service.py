"""Daily bus operation records entered by Level 1 officers.

A record entered here is a draft ("Pending Verification"): nobody on it is verified and the Bus & Permit Lookup does
not show it. Only System Admin approves (which verifies the people on duty) and publishes, through the admin routes.
An officer sees, edits and reopens only the records they entered, and only while they are pending.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import DutyRecordStatus, PersonType
from app.core.timezone import LOCAL
from app.models import Area, DailyTrip, Permit, Person, RouteStand, TripDuty, User, Vehicle
from app.schemas.l1_daily_records import STATUS_LABEL, DailyRecordIn, DailyRecordList, DailyRecordOut
from app.services import audit_service
from app.services import complaint_lookup_service as lookup
from app.services.auth_service import Principal
from app.services.duty_record_service import DutyRecordError, _person, _vehicle

PAGE_SIZE = 20


def _verification(trip: DailyTrip) -> str:
    return {
        DutyRecordStatus.DRAFT: "Pending Verification",
        DutyRecordStatus.APPROVED: "Verified",
        DutyRecordStatus.PUBLISHED: "Published",
    }[trip.status]


def _out(db: Session, trip: DailyTrip, officer: Principal) -> DailyRecordOut:
    duty = db.scalar(select(TripDuty).where(TripDuty.trip_id == trip.id))
    vehicle = db.get(Vehicle, trip.vehicle_id)
    name = lambda person_id: db.scalar(select(Person.full_name).where(Person.id == person_id)) if person_id else None  # noqa: E731
    return DailyRecordOut(
        id=trip.id,
        status=trip.status,
        status_label=STATUS_LABEL[trip.status],
        service_date=trip.service_date,
        vehicle_number=vehicle.vehicle_number,
        permit_number=db.scalar(select(Permit.permit_number).where(Permit.id == trip.permit_id)),
        route_stand_id=trip.route_stand_id,
        route=db.scalar(select(RouteStand.name).where(RouteStand.id == trip.route_stand_id)),
        origin=trip.origin,
        destination=trip.destination,
        area_name=db.scalar(select(Area.name).where(Area.id == vehicle.registered_area_id)),
        departure_time=trip.departure_time,
        end_time=trip.end_time,
        owner_person_id=trip.owner_person_id,
        owner_name=name(trip.owner_person_id),
        driver_person_id=duty.driver_person_id if duty else None,
        driver_name=name(duty.driver_person_id) if duty else None,
        driver_start=duty.driver_start if duty else None,
        driver_end=duty.driver_end if duty else None,
        conductor_person_id=duty.conductor_person_id if duty else None,
        conductor_name=name(duty.conductor_person_id) if duty else None,
        conductor_start=duty.conductor_start if duty else None,
        conductor_end=duty.conductor_end if duty else None,
        remarks=trip.remarks,
        entered_by=db.scalar(select(User.full_name).where(User.id == trip.created_by_user_id)),
        created_at=trip.created_at,
        verification_status=_verification(trip),
        editable=trip.created_by_user_id == officer.id and trip.status == DutyRecordStatus.DRAFT,
    )


def _own(db: Session, officer: Principal, record_id: int, *, lock: bool = False) -> DailyTrip:
    query = select(DailyTrip).where(DailyTrip.id == record_id, DailyTrip.created_by_user_id == officer.id)
    trip = db.scalar(query.with_for_update() if lock else query)
    if trip is None:  # another officer's record is reported as missing, not as forbidden
        raise DutyRecordError(404, "not_found", "That record was not found among the records you entered.")
    return trip


def _checked(db: Session, data: DailyRecordIn):
    """Everything the request names is looked up again here; nothing from the screen is trusted."""
    if data.service_date > datetime.now(LOCAL).date():
        raise DutyRecordError(422, "future_date", "The operation date cannot be in the future.")
    vehicle = _vehicle(db, data.vehicle_number)
    permit = lookup.active_permit(db, vehicle)
    if permit is None:
        raise DutyRecordError(422, "no_permit", "This bus has no active permit on record.")
    if db.scalar(select(RouteStand.id).where(RouteStand.id == data.route_stand_id, RouteStand.is_active)) is None:
        raise DutyRecordError(422, "unknown_route", "Choose a valid route.")
    owner = _person(db, data.owner_person_id, PersonType.OWNER, "owner")
    driver = _person(db, data.driver_person_id, PersonType.DRIVER, "driver")
    conductor = _person(db, data.conductor_person_id, PersonType.CONDUCTOR, "conductor")
    if driver is None and (data.driver_start or data.driver_end):
        raise DutyRecordError(422, "duty_without_person", "Choose the driver before entering the driver's duty times.")
    if conductor is None and (data.conductor_start or data.conductor_end):
        raise DutyRecordError(
            422, "duty_without_person", "Choose the conductor before entering the conductor's duty times."
        )
    return vehicle, permit, owner, driver, conductor


def _apply_duty(db: Session, trip: DailyTrip, data: DailyRecordIn, driver, conductor) -> None:
    duty = db.scalar(select(TripDuty).where(TripDuty.trip_id == trip.id))
    if driver is None and conductor is None:
        if duty is not None:
            db.delete(duty)
        return
    if duty is None:
        duty = TripDuty(trip_id=trip.id)
        db.add(duty)
    duty.driver_person_id = driver.id if driver else None
    duty.conductor_person_id = conductor.id if conductor else None
    duty.driver_start, duty.driver_end = (data.driver_start, data.driver_end) if driver else (None, None)
    duty.conductor_start, duty.conductor_end = (data.conductor_start, data.conductor_end) if conductor else (None, None)


def _save(db: Session, conflict: str) -> None:
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise DutyRecordError(409, "duplicate_trip", conflict) from None


DUPLICATE = "That bus already has a trip at that time on that date. Open the existing record instead."


def create(db: Session, officer: Principal, data: DailyRecordIn) -> DailyRecordOut:
    vehicle, permit, owner, driver, conductor = _checked(db, data)
    trip = DailyTrip(
        service_date=data.service_date,
        vehicle_id=vehicle.id,
        permit_id=permit.id,
        route_stand_id=data.route_stand_id,
        departure_time=data.departure_time,
        end_time=data.end_time,
        origin=data.origin.strip(),
        destination=data.destination.strip(),
        owner_person_id=owner.id if owner else None,
        remarks=(data.remarks or "").strip() or None,
        created_by_user_id=officer.id,
        status=DutyRecordStatus.DRAFT,
    )
    db.add(trip)
    _save(db, DUPLICATE)
    _apply_duty(db, trip, data, driver, conductor)  # the trip, its duty row and the audit row go in together
    audit_service.record(
        db, officer, action="trip.create", entity_type="daily_trips", entity_id=trip.id,
        details={"vehicle": vehicle.vehicle_number, "service_date": data.service_date.isoformat(), "by": "level1"},
    )
    db.commit()
    return _out(db, trip, officer)


def update(db: Session, officer: Principal, record_id: int, data: DailyRecordIn) -> DailyRecordOut:
    trip = _own(db, officer, record_id, lock=True)
    if trip.status != DutyRecordStatus.DRAFT:
        raise DutyRecordError(409, "not_editable", "This record is no longer pending, so it can no longer be changed.")
    vehicle, permit, owner, driver, conductor = _checked(db, data)
    trip.service_date = data.service_date
    trip.vehicle_id, trip.permit_id = vehicle.id, permit.id
    trip.route_stand_id = data.route_stand_id
    trip.departure_time, trip.end_time = data.departure_time, data.end_time
    trip.origin, trip.destination = data.origin.strip(), data.destination.strip()
    trip.owner_person_id = owner.id if owner else None
    trip.remarks = (data.remarks or "").strip() or None
    _save(db, DUPLICATE)
    _apply_duty(db, trip, data, driver, conductor)
    audit_service.record(
        db, officer, action="trip.update", entity_type="daily_trips", entity_id=trip.id,
        details={"vehicle": vehicle.vehicle_number, "by": "level1"},
    )
    db.commit()
    return _out(db, trip, officer)


def get(db: Session, officer: Principal, record_id: int) -> DailyRecordOut:
    return _out(db, _own(db, officer, record_id), officer)


def list_mine(
    db: Session, officer: Principal, *, service_date, search: str | None, status: DutyRecordStatus | None, page: int
) -> DailyRecordList:
    conditions = [DailyTrip.created_by_user_id == officer.id]
    if service_date:
        conditions.append(DailyTrip.service_date == service_date)
    if status:
        conditions.append(DailyTrip.status == status)
    query = select(DailyTrip).join(Vehicle, Vehicle.id == DailyTrip.vehicle_id).where(*conditions)
    if search and search.strip():
        query = query.where(Vehicle.vehicle_number.ilike(f"%{search.strip()}%"))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.order_by(DailyTrip.service_date.desc(), DailyTrip.departure_time.desc(), DailyTrip.id.desc())
        .limit(PAGE_SIZE)
        .offset((page - 1) * PAGE_SIZE)
    ).all()
    return DailyRecordList(items=[_out(db, t, officer) for t in rows], total=total, page=page, page_size=PAGE_SIZE)
