"""Request and response shapes of the Level 1 Bus & Permit Lookup (Date + Bus Number)."""

from datetime import date, time
from typing import Literal

from pydantic import BaseModel

from app.schemas.l1_complaints import VehicleLookup

# Nobody on a record is ever guessed: a person is shown only when Admin has verified the duty record.
PersonStatus = Literal["verified", "unverified", "unavailable"]
VerificationStatus = Literal["Verified", "Unverified", "Unavailable"]
# What the records say about the bus on the date: it ran, every trip was cancelled, it did not operate (with a
# reason), or there is no record at all. Only the last is "no matching record".
OperationStatus = Literal["operated", "cancelled", "did_not_operate", "no_record"]
TripStatus = Literal["completed", "cancelled", "partial"]


class TripSummary(BaseModel):
    """One row of the results table, for choosing between several trips or duty shifts."""

    id: int
    bus_number: str
    permit_number: str
    route: str
    departure_time: time
    trip_status: TripStatus = "completed"
    direction: str | None = None
    synthetic: bool = False  # simulated development data, not an official record


class BusSearch(BaseModel):
    service_date: date
    vehicle: VehicleLookup
    trips: list[TripSummary]  # empty when no published record exists for that bus on that date
    operation_status: OperationStatus = "no_record"
    non_operation_reason: str | None = None  # why the bus did not operate


class DutyPerson(BaseModel):
    person_id: int | None  # set only for a verified person
    name: str | None
    status: PersonStatus


class RegisteredOwner(BaseModel):
    person_id: int | None
    name: str | None
    # From an approved ownership record for that date, or from the vehicle record. Never both guessed.
    source: Literal["assignment", "vehicle_record"] | None


class TripDetails(BaseModel):
    """The selected record. The ids are what the New complaint form is filled in from."""

    trip_id: int
    service_date: date
    vehicle_id: int
    bus_number: str
    area_id: int
    area_name: str
    permit_id: int
    permit_number: str
    route_stand_id: int
    route: str
    origin: str
    destination: str
    departure_time: time
    arrival_time: time | None = None
    actual_departure: time | None = None
    actual_arrival: time | None = None
    trip_status: TripStatus = "completed"
    direction: str | None = None
    synthetic: bool = False
    owner: RegisteredOwner
    driver: DutyPerson
    conductor: DutyPerson
    verification_status: VerificationStatus
