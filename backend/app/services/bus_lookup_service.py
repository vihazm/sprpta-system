"""Bus & Permit Lookup (Feature 06): what the published daily records say about a bus on a date.

Only published records are read. Who drove or conducted is shown only when Admin has verified the duty
record; otherwise the answer is Unverified or Unavailable, never a guess. The registered owner comes from
an approved ownership record that covers the date, else from the vehicle record.
"""

from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import DutyRecordStatus
from app.core.timezone import LOCAL
from app.models import Area, BusNonOperation, DailyTrip, OwnerAssignment, Permit, Person, RouteStand, TripDuty, Vehicle
from app.schemas.l1_bus_lookup import (
    BusSearch,
    DutyPerson,
    RegisteredOwner,
    TripDetails,
    TripSummary,
)
from app.services import complaint_lookup_service as lookup
from app.services.complaint_intake_service import ComplaintError

_UNAVAILABLE = DutyPerson(person_id=None, name=None, status="unavailable")


def search_trips(db: Session, service_date: date, bus_number: str) -> BusSearch:
    """The published trips of a bus on a date, earliest first."""
    if service_date > datetime.now(LOCAL).date():
        raise ComplaintError(422, "future_date", "The incident date cannot be in the future.")
    vehicle = lookup.find_vehicle(db, bus_number)
    if vehicle is None:
        raise ComplaintError(404, "vehicle_not_found", "No vehicle on record has that number.")

    rows = db.execute(
        select(DailyTrip, Permit.permit_number, RouteStand.name)
        .join(Permit, Permit.id == DailyTrip.permit_id)
        .join(RouteStand, RouteStand.id == DailyTrip.route_stand_id)
        .where(
            DailyTrip.vehicle_id == vehicle.id,
            DailyTrip.service_date == service_date,
            DailyTrip.status == DutyRecordStatus.PUBLISHED,
        )
        .order_by(DailyTrip.departure_time, DailyTrip.id)
    ).all()
    status, reason = "operated", None
    if not rows:
        stopped = db.scalar(
            select(BusNonOperation).where(
                BusNonOperation.vehicle_id == vehicle.id,
                BusNonOperation.start_date <= service_date,
                BusNonOperation.end_date >= service_date,
            ).order_by(BusNonOperation.id)
        )
        status, reason = ("did_not_operate", stopped.reason) if stopped else ("no_record", None)
    elif all(trip.trip_status == "cancelled" for trip, _p, _r in rows):
        status = "cancelled"
    return BusSearch(
        service_date=service_date,
        vehicle=lookup.vehicle_lookup(db, vehicle),
        trips=[
            TripSummary(
                id=trip.id,
                bus_number=vehicle.vehicle_number,
                permit_number=permit_number,
                route=route,
                departure_time=trip.departure_time,
                trip_status=trip.trip_status,
                direction=trip.direction,
                synthetic=trip.synthetic_batch_id is not None,
            )
            for trip, permit_number, route in rows
        ],
        operation_status=status,
        non_operation_reason=reason,
    )


def _owner(db: Session, vehicle: Vehicle, on: date) -> RegisteredOwner:
    assignment = db.scalar(
        select(OwnerAssignment)
        .where(
            OwnerAssignment.vehicle_id == vehicle.id,
            OwnerAssignment.status == DutyRecordStatus.PUBLISHED,
            OwnerAssignment.valid_from <= on,
            (OwnerAssignment.valid_to.is_(None)) | (OwnerAssignment.valid_to >= on),
        )
        .order_by(OwnerAssignment.valid_from.desc(), OwnerAssignment.id.desc())
    )
    if assignment is not None:
        person = db.get(Person, assignment.owner_person_id)
        return RegisteredOwner(person_id=person.id, name=person.full_name, source="assignment")
    person = db.get(Person, vehicle.owner_person_id) if vehicle.owner_person_id else None
    if person is not None:
        return RegisteredOwner(person_id=person.id, name=person.full_name, source="vehicle_record")
    return RegisteredOwner(person_id=None, name=None, source=None)


def _on_duty(db: Session, person_id: int | None, duty: TripDuty | None) -> DutyPerson:
    if duty is None or person_id is None:
        return _UNAVAILABLE
    if duty.verified_at is None:
        return DutyPerson(person_id=None, name=None, status="unverified")
    person = db.get(Person, person_id)
    return DutyPerson(person_id=person.id, name=person.full_name, status="verified")


def trip_details(db: Session, trip_id: int) -> TripDetails:
    """The selected record in full. A record that is not published (or was withdrawn) is not found."""
    trip = db.scalar(
        select(DailyTrip).where(DailyTrip.id == trip_id, DailyTrip.status == DutyRecordStatus.PUBLISHED)
    )
    if trip is None:
        raise ComplaintError(404, "trip_not_found", "That record is not available. Search again.")
    vehicle = db.get(Vehicle, trip.vehicle_id)
    permit = db.get(Permit, trip.permit_id)
    route = db.get(RouteStand, trip.route_stand_id)
    duty = db.scalar(select(TripDuty).where(TripDuty.trip_id == trip.id))
    driver = _on_duty(db, duty.driver_person_id if duty else None, duty)
    conductor = _on_duty(db, duty.conductor_person_id if duty else None, duty)

    if duty is None:
        verification = "Unavailable"
    elif driver.status == "verified" and conductor.status == "verified":
        verification = "Verified"
    else:
        verification = "Unverified"

    return TripDetails(
        trip_id=trip.id,
        service_date=trip.service_date,
        vehicle_id=vehicle.id,
        bus_number=vehicle.vehicle_number,
        area_id=vehicle.registered_area_id,
        area_name=db.scalar(select(Area.name).where(Area.id == vehicle.registered_area_id)),
        permit_id=permit.id,
        permit_number=permit.permit_number,
        route_stand_id=route.id,
        route=route.name,
        origin=trip.origin,
        destination=trip.destination,
        departure_time=trip.departure_time,
        arrival_time=trip.end_time,
        actual_departure=trip.actual_departure,
        actual_arrival=trip.actual_arrival,
        trip_status=trip.trip_status,
        direction=trip.direction,
        synthetic=trip.synthetic_batch_id is not None,
        owner=_owner(db, vehicle, trip.service_date),
        driver=driver,
        conductor=conductor,
        verification_status=verification,
    )
