"""Request and response shapes of the complainant portal: sign-up and the complainant's own complaints."""

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.admin_users import MAX_ID, NoNul

Text = Annotated[str, NoNul]


# ---------------------------------------------------------------- sign-up


class SignUpRequest(BaseModel):
    name: Text = Field(min_length=1, max_length=120, pattern=r"\S")
    identifier: Text = Field(min_length=1, max_length=254)  # an email address or a mobile number
    password: str = Field(min_length=8, max_length=128)


class CodeSent(BaseModel):
    channel: Literal["email", "sms"]
    resend_after: int  # seconds before another code can be asked for


class ResendRequest(BaseModel):
    identifier: Text = Field(min_length=1, max_length=254)


class VerifyRequest(BaseModel):
    identifier: Text = Field(min_length=1, max_length=254)
    code: str = Field(pattern=r"^\d{6}$")


# ---------------------------------------------------------------- the complainant's complaints


class PortalComplaintForm(BaseModel):
    """The portal form (UI-CP-04). Severity, vehicle checking and the reference number are Level 1's job."""

    complaint_date: date
    target_type_id: int = Field(ge=1, le=MAX_ID)
    subject: Text = Field(min_length=1, max_length=200, pattern=r"\S")
    vehicle_number: Text | None = Field(default=None, max_length=20)
    area_id: int = Field(ge=1, le=MAX_ID)
    route_stand_id: int | None = Field(default=None, ge=1, le=MAX_ID)
    category_id: int = Field(ge=1, le=MAX_ID)
    description: Text = Field(min_length=1, max_length=5000, pattern=r"\S")


class Named(BaseModel):
    id: int
    name: str


class PortalTarget(Named):
    code: str


class PortalCategory(Named):
    target_ids: list[int]  # the targets it is approved for; empty means every target


class PortalPlace(Named):
    kind: str
    area_id: int | None


class PortalOptions(BaseModel):
    areas: list[Named]
    targets: list[PortalTarget]
    categories: list[PortalCategory]
    routes_stands: list[PortalPlace]


class PortalVehicle(BaseModel):
    """A vehicle offered while the complainant types a number."""

    vehicle_number: str
    vehicle_type: str
    area_id: int
    area_name: str


class PortalAttachment(BaseModel):
    id: int
    file_name: str
    mime_type: str
    size_bytes: int


class PortalComplaint(BaseModel):
    id: int
    reference_number: str | None  # none until Level 1 has registered it
    subject: str
    complaint_date: date | None
    submitted_at: datetime
    step: int  # 1 Submitted, 2 Received, 3 Action in progress, 4 Closed
    status_label: str
    outcome: Literal["open", "closed", "not_accepted"]
    step_dates: list[datetime | None]  # when each of the four steps was reached; none if not yet
    # Only what the person gave or can see; never staff notes or the severity.
    target_name: str | None
    category_name: str | None
    area_name: str | None
    route_stand_name: str | None
    vehicle_number: str | None
    description: str | None
    attachments: list[PortalAttachment]
    can_delete: bool  # only while Level 1 has not checked it yet
