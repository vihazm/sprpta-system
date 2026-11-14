"""Request and response shapes of the Level 1 complaint form (Quick entry, UC-L1-01 to UC-L1-10)."""

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.core.enums import ComplaintStatus, DuplicateLinkType, PersonType, RejectionType, VehicleType
from app.schemas.admin_users import MAX_ID, NoNul

Id = Annotated[int, Field(ge=1, le=MAX_ID)]
Text = Annotated[str, NoNul]


# ---------------------------------------------------------------- the form


class ComplaintForm(BaseModel):
    """Everything L1 can fill in. Every field is optional: a draft may be saved half empty.

    The vehicle is sent as the number L1 typed; the permit, owner and area are
    filled in from the vehicle record by the backend.
    """

    medium_id: Id | None = None
    is_anonymous: bool = False  # an anonymous complaint has no name and no contact
    complainant_name: Text | None = Field(default=None, max_length=120)
    contact: Text | None = Field(default=None, max_length=254)  # a mobile number or an email address
    complaint_date: date | None = None
    vehicle_number: Text | None = Field(default=None, max_length=20)
    subject_person_id: Id | None = None  # the driver, conductor or staff member, when a record matches
    subject_person_text: Text | None = Field(default=None, max_length=120)  # the name as given otherwise
    route_stand_id: Id | None = None
    category_id: Id | None = None
    severity_id: Id | None = None
    subject: Text | None = Field(default=None, max_length=200)
    description: Text | None = Field(default=None, max_length=5000)


class RejectBody(BaseModel):
    rejection_type: RejectionType
    reason: Text = Field(min_length=1, max_length=1000, pattern=r"\S")
    duplicate_of_reference: Text | None = Field(default=None, max_length=40)  # required for a duplicate


class DuplicateChoice(BaseModel):
    link_type: DuplicateLinkType


# ---------------------------------------------------------------- what the form shows


class Named(BaseModel):
    id: int
    name: str


class SeverityOption(Named):
    forward_days: int  # 0 means the same day


class RouteStandOption(Named):
    kind: str
    area_id: int | None


class FormOptions(BaseModel):
    mediums: list[Named]
    categories: list[Named]
    severities: list[SeverityOption]
    routes_stands: list[RouteStandOption]


class VehicleLookup(BaseModel):
    id: int
    vehicle_number: str
    vehicle_type: VehicleType
    area_id: int
    area_name: str
    permit_number: str | None
    owner_name: str | None
    past_complaints: int


class PersonLookup(BaseModel):
    id: int
    full_name: str
    person_type: PersonType


class DuplicateCandidate(BaseModel):
    id: int
    reference_number: str
    subject: str | None
    status: ComplaintStatus
    match: int  # 0 to 100, how alike the two subjects are
    link_type: DuplicateLinkType | None  # L1's choice so far, if any


# ---------------------------------------------------------------- the complaint


class AttachmentOut(BaseModel):
    id: int
    file_name: str
    mime_type: str
    size_bytes: int
    description: str | None
    created_at: datetime


class ComplaintOut(BaseModel):
    id: int
    reference_number: str | None  # none while a draft
    status: ComplaintStatus
    medium_id: int | None
    is_anonymous: bool
    complainant_name: str | None
    contact: str | None
    complaint_date: date | None
    vehicle_number: str | None
    vehicle: VehicleLookup | None  # set once the number matches a vehicle record
    subject_person_id: int | None
    subject_person_text: str | None
    subject_person_name: str | None  # the linked person's name, or the name as it was written
    route_stand_id: int | None
    category_id: int | None
    severity_id: int | None
    subject: str | None
    description: str | None
    area_id: int | None
    area_name: str | None
    assigned_l2_name: str | None
    rejection_type: RejectionType | None
    rejection_reason: str | None
    duplicate_of_reference: str | None
    registered_at: datetime | None
    forwarded_at: datetime | None
    rejected_at: datetime | None
    attachments: list[AttachmentOut]
    created_at: datetime
    updated_at: datetime


class ComplaintListItem(BaseModel):
    id: int
    reference_number: str | None
    status: ComplaintStatus
    subject: str | None
    vehicle_number: str | None
    updated_at: datetime
