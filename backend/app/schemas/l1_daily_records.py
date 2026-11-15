"""Request and response shapes of the daily bus operation records Level 1 officers enter (Pending Verification)."""

from datetime import date, datetime, time

from pydantic import BaseModel, Field

from app.core.enums import DutyRecordStatus
from app.schemas.l1_complaints import Id, Text

# What the officer sees for each step. A record entered by Level 1 starts as a draft: it is waiting for Admin.
STATUS_LABEL = {
    DutyRecordStatus.DRAFT: "Pending Verification",
    DutyRecordStatus.APPROVED: "Verified, not published",
    DutyRecordStatus.PUBLISHED: "Published",
}


class DailyRecordIn(BaseModel):
    """One trip of a bus on a date. Nobody is marked verified here: Admin does that when approving."""

    service_date: date
    vehicle_number: Text = Field(min_length=1, max_length=20)
    route_stand_id: Id
    departure_time: time
    end_time: time | None = None
    origin: Text = Field(min_length=1, max_length=100, pattern=r"\S")
    destination: Text = Field(min_length=1, max_length=100, pattern=r"\S")
    owner_person_id: Id | None = None
    driver_person_id: Id | None = None
    driver_start: time | None = None
    driver_end: time | None = None
    conductor_person_id: Id | None = None
    conductor_start: time | None = None
    conductor_end: time | None = None
    remarks: Text | None = Field(default=None, max_length=1000)


class DailyRecordOut(BaseModel):
    id: int
    status: DutyRecordStatus
    status_label: str
    service_date: date
    vehicle_number: str
    permit_number: str
    route_stand_id: int
    route: str
    origin: str
    destination: str
    area_name: str | None  # the office / district: the bus's registered area
    departure_time: time
    end_time: time | None
    owner_person_id: int | None
    owner_name: str | None
    driver_person_id: int | None
    driver_name: str | None
    driver_start: time | None
    driver_end: time | None
    conductor_person_id: int | None
    conductor_name: str | None
    conductor_start: time | None
    conductor_end: time | None
    remarks: str | None
    entered_by: str | None
    created_at: datetime
    verification_status: str  # Pending Verification, Verified or Published, as the record stands
    editable: bool  # the officer's own record that is still pending


class DailyRecordList(BaseModel):
    items: list[DailyRecordOut]
    total: int
    page: int
    page_size: int
