"""Request and response shapes of the Level 1 complaint form (Quick entry, UC-L1-01 to UC-L1-10)."""

from datetime import date, datetime, time
from typing import Annotated, Literal

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
    mobile: Text | None = Field(default=None, max_length=20)
    email: Text | None = Field(default=None, max_length=254)
    complaint_date: date | None = None  # the incident date; taken from the daily record when one is selected
    incident_time: time | None = None  # only when it differs from the trip time
    incident_location: Text | None = Field(default=None, max_length=200)
    vehicle_number: Text | None = Field(default=None, max_length=20)
    # The daily record chosen in the Bus & Permit Lookup. It is the only thing the client sends about it: the
    # permit, owner, route and duty details are read from the database, never taken from the request.
    trip_id: Id | None = None
    # Who the complaint is against (separate from the issue category above). Needed to forward. The person, when
    # one is picked, must be of the right type for the target; whether they are verified is worked out by the
    # server, never taken from the request.
    target_type_id: Id | None = None
    # Who is complaining, when known: a passenger, or someone with a role in the service.
    complainant_type: Literal["passenger", "driver", "conductor", "owner", "other"] | None = None
    # Made once for each new complaint by the form. Sending a create again with the same key returns the complaint
    # that was already made, so a retry cannot leave two. Ignored when changing a saved complaint.
    client_request_id: Text | None = Field(default=None, min_length=8, max_length=64)
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


class TargetOption(Named):
    code: str  # driver, conductor, owner, bus_service, other


class CategoryOption(Named):
    # The targets this category is approved for. Empty means it is open to every target.
    target_ids: list[int]


class FormOptions(BaseModel):
    mediums: list[Named]
    categories: list[CategoryOption]
    targets: list[TargetOption]
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
    owner_person_id: int | None  # the registered owner on the vehicle record, for confirming an owner complaint
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
    must_decide: bool  # a close match has to be decided before forwarding; a weak one is shown but optional


# ---------------------------------------------------------------- the complaint


class AttachmentOut(BaseModel):
    id: int
    file_name: str
    mime_type: str
    size_bytes: int
    description: str | None
    created_at: datetime


class DutySnapshotOut(BaseModel):
    """The verified daily record as it was when the complaint was saved."""

    trip_id: int
    service_date: date
    bus_number: str
    permit_number: str
    route: str
    origin: str
    destination: str
    departure_time: time
    owner_person_id: int | None
    owner_name: str | None
    driver_person_id: int | None  # only a verified person is ever here
    driver_name: str | None
    conductor_person_id: int | None
    conductor_name: str | None
    verification_status: str


# How well the accused person is established. Worked out from the data by the server, never sent by the client.
AccusedStatus = Literal["verified_duty", "registered_owner", "directory_only", "unidentified", "none"]


class ComplaintOut(BaseModel):
    id: int
    reference_number: str | None  # none while a draft
    status: ComplaintStatus
    via_portal: bool  # sent by a complainant through the portal
    medium_id: int | None
    is_anonymous: bool
    complainant_name: str | None
    mobile: str | None
    email: str | None
    complaint_date: date | None
    incident_time: time | None
    incident_location: str | None
    trip_id: int | None  # the daily record the complaint was saved against
    duty: DutySnapshotOut | None
    vehicle_number: str | None
    vehicle: VehicleLookup | None  # set once the number matches a vehicle record
    permit_id: int | None
    owner_person_id: int | None
    subject_person_id: int | None
    subject_person_text: str | None
    subject_person_name: str | None  # the linked person's name, or the name as it was written
    route_stand_id: int | None
    category_id: int | None
    category_name: str | None
    target_type_id: int | None  # who the complaint is against
    complainant_type: str | None
    # What checking the bus against the daily records found: verified, corrected (the number given was wrong),
    # unverified, not_found, not_operated or trip_cancelled. The number as typed stays in vehicle_number.
    bus_verification: str | None
    target_code: str | None
    target_name: str | None
    accused_status: AccusedStatus
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
