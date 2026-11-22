"""Request and response shapes of the administrator's master data screens (UI-AD-04 and UI-AD-05).

Each kind of record has one model of the fields the administrator can set. A listed row carries the same names, so
the form can be filled straight from it, plus a few names looked up for display (the area of a vehicle, for example).
"""

from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field

from app.core.enums import PersonType, PlaceKind, VehicleType
from app.schemas.admin_users import MAX_ID, NoNul

EntityKey = Literal["areas", "routes", "vehicles", "permits", "people", "categories", "severities", "mediums"]


def _blank_is_none(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip() or None
    return value


def _one_spaced(text: str) -> str:
    return " ".join(text.split())


Name = Annotated[str, NoNul, AfterValidator(_one_spaced), Field(min_length=1, max_length=120)]
# Vehicle and permit numbers are kept in capitals with single spaces, as L1 searches them.
Number = Annotated[str, NoNul, AfterValidator(lambda text: _one_spaced(text).upper()), Field(min_length=1, max_length=30)]
OptionalText = Annotated[Annotated[str, NoNul, Field(max_length=500)] | None, BeforeValidator(_blank_is_none)]
RecordId = Annotated[int, Field(ge=1, le=MAX_ID)]


class Fields(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class AreaFields(Fields):
    name: Name


class RouteStandFields(Fields):
    kind: PlaceKind
    name: Name
    area_id: RecordId | None = None


class VehicleFields(Fields):
    vehicle_number: Number
    vehicle_type: VehicleType
    registered_area_id: RecordId  # forwarding goes by this area, so it is required
    owner_person_id: RecordId | None = None


class PermitFields(Fields):
    permit_number: Number
    vehicle_id: RecordId
    holder_person_id: RecordId | None = None
    route_stand_id: RecordId | None = None


class PersonFields(Fields):
    full_name: Name
    person_type: PersonType
    staff_number: OptionalText = None
    phone: OptionalText = None


class CategoryFields(Fields):
    name: Name
    description: OptionalText = None


class NameOnly(Fields):
    """Severities and mediums: only the name is edited here (the time targets belong to Settings)."""

    name: Name


class RecordBody(BaseModel):
    values: dict[str, Any]  # checked against the fields of the kind of record
    is_active: bool = True


class RecordList(BaseModel):
    items: list[dict[str, Any]]
    total: int  # matching the search and status
    page: int
    page_size: int
    counts: dict[str, int]  # matching the search: all, active and inactive


class EntityCount(BaseModel):
    key: EntityKey
    total: int
    active: int
