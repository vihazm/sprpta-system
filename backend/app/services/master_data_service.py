"""Master data for the administrator (UC-AD-02, F-57): areas, routes and stands, vehicles, permits, people,
categories, severities and mediums.

Every kind is handled the same way: a paged search, add, edit, and deactivate or reactivate. Records are never
deleted, because complaints refer to them. Level 1 already reads only active records, so a change shows there at
once. Every change is written to the audit trail with the old and new values. The few rules of a particular kind
live in its check function below.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased

from app.core.roles import UserRole
from app.models import (
    Area,
    ComplaintCategory,
    ComplaintMedium,
    Permit,
    Person,
    RouteStand,
    Severity,
    User,
    Vehicle,
)
from app.schemas.admin_master_data import (
    AreaFields,
    CategoryFields,
    EntityCount,
    NameOnly,
    PermitFields,
    PersonFields,
    RecordList,
    RouteStandFields,
    VehicleFields,
)
from app.services import audit_service
from app.services.auth_service import Principal
from app.services.complaint_lookup_service import find_vehicle

PAGE_SIZE = 10


class MasterDataError(Exception):
    """A rule the request breaks; the route turns it into a clean HTTP error."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


# ---------------------------------------------------------------- the rules of each kind


def _must_exist(db: Session, model, row_id: int | None, what: str) -> None:
    row = db.get(model, row_id) if row_id else None
    if row_id and (row is None or not row.is_active):
        raise MasterDataError(422, "not_found", f"Choose an active {what}.")


def _check_area(db: Session, data: AreaFields, area: Area | None, active: bool) -> None:
    if area and area.is_active and not active:
        # Complaints are forwarded by the vehicle's area, so an area still in use must stay on.
        in_use = db.scalar(select(func.count()).select_from(Vehicle).where(Vehicle.registered_area_id == area.id, Vehicle.is_active))
        officer = db.scalar(select(User.id).where(User.area_id == area.id, User.role == UserRole.L2, User.is_active))
        if in_use or officer:
            raise MasterDataError(
                409, "area_in_use", "Move its active vehicles and its Level 2 officer to another area first."
            )


def _check_route(db: Session, data: RouteStandFields, route: RouteStand | None, active: bool) -> None:
    _must_exist(db, Area, data.area_id, "area")


def _check_vehicle(db: Session, data: VehicleFields, vehicle: Vehicle | None, active: bool) -> None:
    _must_exist(db, Area, data.registered_area_id, "registered area")
    _must_exist(db, Person, data.owner_person_id, "owner")
    # L1 finds a bus ignoring spaces and dashes, so "NA-1234" and "NA 1234" are the same bus.
    same = find_vehicle(db, data.vehicle_number)
    if same and (vehicle is None or same.id != vehicle.id):
        raise MasterDataError(409, "already_exists", f"Vehicle {same.vehicle_number} is already registered.")


def _check_permit(db: Session, data: PermitFields, permit: Permit | None, active: bool) -> None:
    _must_exist(db, Vehicle, data.vehicle_id, "vehicle")
    _must_exist(db, Person, data.holder_person_id, "permit holder")
    _must_exist(db, RouteStand, data.route_stand_id, "route")


def _check_severity(db: Session, data: NameOnly, severity: Severity | None, active: bool) -> None:
    # The code keys on the four ranks, so the list is fixed. Their time targets are edited under Settings.
    if severity is None:
        raise MasterDataError(409, "fixed_list", "The four severities are fixed. You can rename them.")
    if not active:
        raise MasterDataError(409, "fixed_list", "Severities cannot be deactivated.")


def _check_medium(db: Session, data: NameOnly, medium: ComplaintMedium | None, active: bool) -> None:
    if medium and medium.is_system and (not active or data.name != medium.name):
        raise MasterDataError(409, "system_medium", f"{medium.name} is used by the complainant portal and cannot be changed.")


# ---------------------------------------------------------------- the kinds


@dataclass(frozen=True)
class Entity:
    model: type
    fields: type[BaseModel]
    label: str  # used in messages, for example "vehicle"
    search: tuple  # columns a search matches
    order: tuple
    check: Callable | None = None
    joins: tuple = ()  # (model, on clause, labelled column) for names shown beside a row
    read_only: tuple[str, ...] = ()  # shown, not edited


Owner = aliased(Person)
Holder = aliased(Person)
VehicleOfPermit = aliased(Vehicle)
AreaOfRow = aliased(Area)

ENTITIES: dict[str, Entity] = {
    "areas": Entity(Area, AreaFields, "area", (Area.name,), (Area.name,), _check_area),
    "routes": Entity(
        RouteStand,
        RouteStandFields,
        "route or stand",
        (RouteStand.name,),
        (RouteStand.kind, RouteStand.name),
        _check_route,
        joins=((AreaOfRow, AreaOfRow.id == RouteStand.area_id, AreaOfRow.name.label("area_name")),),
    ),
    "vehicles": Entity(
        Vehicle,
        VehicleFields,
        "vehicle",
        (Vehicle.vehicle_number, Owner.full_name),
        (Vehicle.vehicle_number,),
        _check_vehicle,
        joins=(
            (AreaOfRow, AreaOfRow.id == Vehicle.registered_area_id, AreaOfRow.name.label("area_name")),
            (Owner, Owner.id == Vehicle.owner_person_id, Owner.full_name.label("owner_name")),
        ),
    ),
    "permits": Entity(
        Permit,
        PermitFields,
        "permit",
        (Permit.permit_number, VehicleOfPermit.vehicle_number, Holder.full_name),
        (Permit.permit_number,),
        _check_permit,
        joins=(
            (VehicleOfPermit, VehicleOfPermit.id == Permit.vehicle_id, VehicleOfPermit.vehicle_number.label("vehicle_number")),
            (Holder, Holder.id == Permit.holder_person_id, Holder.full_name.label("holder_name")),
            (RouteStand, RouteStand.id == Permit.route_stand_id, RouteStand.name.label("route_name")),
        ),
    ),
    "people": Entity(
        Person,
        PersonFields,
        "person",
        (Person.full_name, Person.staff_number, Person.phone),
        (Person.full_name, Person.id),
    ),
    "categories": Entity(ComplaintCategory, CategoryFields, "category", (ComplaintCategory.name,), (ComplaintCategory.name,)),
    "severities": Entity(
        Severity, NameOnly, "severity", (Severity.name,), (Severity.rank,), _check_severity, read_only=("rank",)
    ),
    "mediums": Entity(
        ComplaintMedium,
        NameOnly,
        "medium",
        (ComplaintMedium.name,),
        (ComplaintMedium.name,),
        _check_medium,
        read_only=("is_system",),
    ),
}


# ---------------------------------------------------------------- reading


def _joined(query, entity: Entity):
    for model, on, _ in entity.joins:
        query = query.outerjoin(model, on)
    return query


def _out(entity: Entity, row) -> dict[str, Any]:
    record, *names = row
    return {
        "id": record.id,
        "is_active": record.is_active,
        **{name: getattr(record, name) for name in (*entity.fields.model_fields, *entity.read_only)},
        **{column.key: name for (_, _, column), name in zip(entity.joins, names, strict=True)},
    }


def _rows(entity: Entity):
    return _joined(select(entity.model, *(column for _, _, column in entity.joins)), entity)


def counts(db: Session) -> list[EntityCount]:
    """How many records of each kind there are, for the cards of the hub."""
    result = []
    for key, entity in ENTITIES.items():
        total, active = db.execute(
            select(func.count(), func.count().filter(entity.model.is_active)).select_from(entity.model)
        ).one()
        result.append(EntityCount(key=key, total=total, active=active))
    return result


def list_records(db: Session, key: str, *, search: str, status: str | None, page: int, page_size: int) -> RecordList:
    entity = ENTITIES[key]
    model = entity.model
    conditions = []
    term = search.strip()
    if term:
        conditions.append(or_(*(column.icontains(term, autoescape=True) for column in entity.search)))

    by_status = dict(
        db.execute(
            _joined(select(model.is_active, func.count()).select_from(model), entity)
            .where(*conditions)
            .group_by(model.is_active)
        ).all()
    )
    counts_ = {"active": by_status.get(True, 0), "inactive": by_status.get(False, 0)}
    counts_["all"] = counts_["active"] + counts_["inactive"]

    if status:
        conditions.append(model.is_active.is_(status == "active"))
    total = counts_[status or "all"]
    page = min(page, max(1, -(-total // page_size)))  # a page past the end shows the last one
    rows = db.execute(
        _rows(entity).where(*conditions).order_by(*entity.order).limit(page_size).offset((page - 1) * page_size)
    ).all()
    return RecordList(
        items=[_out(entity, row) for row in rows], total=total, page=page, page_size=page_size, counts=counts_
    )


def _record(db: Session, entity: Entity, record_id: int) -> dict[str, Any]:
    return _out(entity, db.execute(_rows(entity).where(entity.model.id == record_id)).one())


# ---------------------------------------------------------------- changing


def _save(db: Session, entity: Entity, record, *, admin: Principal, action: str, changes: dict) -> dict[str, Any]:
    try:
        db.flush()  # gives a new record its id
        audit_service.record(
            db, admin, action=action, entity_type=entity.model.__tablename__, entity_id=record.id,
            details={"changes": changes},
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        raise MasterDataError(409, "already_exists", f"That {entity.label} already exists.") from None
    return _record(db, entity, record.id)


def create_record(db: Session, admin: Principal, key: str, values: dict[str, Any]) -> dict[str, Any]:
    entity = ENTITIES[key]
    data = entity.fields.model_validate(values)
    if entity.check:
        entity.check(db, data, None, True)
    record = entity.model(**data.model_dump())
    db.add(record)
    changes = {name: [None, value] for name, value in data.model_dump(mode="json").items()}
    return _save(db, entity, record, admin=admin, action="master_data.create", changes=changes)


def update_record(
    db: Session, admin: Principal, key: str, record_id: int, values: dict[str, Any], *, active: bool
) -> dict[str, Any]:
    entity = ENTITIES[key]
    record = db.get(entity.model, record_id)
    if record is None:
        raise MasterDataError(404, "not_found", f"That {entity.label} does not exist.")
    data = entity.fields.model_validate(values)
    if entity.check:
        entity.check(db, data, record, active)

    new = {**data.model_dump(mode="json"), "is_active": active}
    old = {name: getattr(record, name) for name in new}
    changes = {name: [old[name], value] for name, value in new.items() if old[name] != value}
    if not changes:
        return _record(db, entity, record.id)
    for name, value in {**data.model_dump(), "is_active": active}.items():
        setattr(record, name, value)
    return _save(db, entity, record, admin=admin, action="master_data.update", changes=changes)
