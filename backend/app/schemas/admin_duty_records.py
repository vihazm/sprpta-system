"""Request and response shapes of the daily operation records (System Admin only)."""

from datetime import date, datetime, time

from pydantic import BaseModel, Field

from app.core.enums import DutyRecordStatus
from app.schemas.l1_complaints import Id, Text


class TripIn(BaseModel):
    """A daily trip, saved as a draft. Who was on duty is optional: a missing person stays Unavailable."""

    service_date: date
    vehicle_number: Text = Field(min_length=1, max_length=20)
    route_stand_id: Id
    departure_time: time
    origin: Text = Field(min_length=1, max_length=100, pattern=r"\S")
    destination: Text = Field(min_length=1, max_length=100, pattern=r"\S")
    permit_number: Text | None = Field(default=None, max_length=40)  # the bus's own permit when left out
    driver_person_id: Id | None = None
    conductor_person_id: Id | None = None


class TripOut(BaseModel):
    id: int
    service_date: date
    vehicle_number: str
    permit_number: str
    route: str
    departure_time: time
    origin: str
    destination: str
    status: DutyRecordStatus
    driver: str | None
    conductor: str | None
    duty_verified: bool
    published_at: datetime | None


class TripList(BaseModel):
    items: list[TripOut]
    total: int


class OwnerAssignmentIn(BaseModel):
    vehicle_number: Text = Field(min_length=1, max_length=20)
    owner_person_id: Id
    valid_from: date
    valid_to: date | None = None  # empty while the ownership still holds


class OwnerAssignmentOut(BaseModel):
    id: int
    vehicle_number: str
    owner: str
    valid_from: date
    valid_to: date | None
    status: DutyRecordStatus
    published_at: datetime | None
