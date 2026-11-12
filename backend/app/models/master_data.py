"""Master data (DB doc 2.5 to 2.11): the lists L1 looks things up in.

`areas` is in app.models.area. Rows here are deactivated, never deleted, once
complaints refer to them.
"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    SmallInteger,
    Text,
    UniqueConstraint,
    false,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import PersonType, PlaceKind, VehicleType
from app.db.base import Base
from app.db.types import PersonTypeType, PlaceKindType, VehicleTypeType


class RouteStand(Base):
    """DB doc 2.5: a bus route or a stand."""

    __tablename__ = "routes_stands"
    __table_args__ = (UniqueConstraint("kind", "name", "area_id", name="uq_routes_stands_kind_name_area_id"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    kind: Mapped[PlaceKind] = mapped_column(PlaceKindType)
    name: Mapped[str] = mapped_column(Text)
    area_id: Mapped[int | None] = mapped_column(ForeignKey("areas.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Person(Base):
    """DB doc 2.8: drivers, conductors, SPRPTA staff and owners.

    These are the people complaints can be about and who receive ratings.
    `team_label` is a placeholder: "team" is not yet defined by the client.
    """

    __tablename__ = "people"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    full_name: Mapped[str] = mapped_column(Text)
    person_type: Mapped[PersonType] = mapped_column(PersonTypeType)
    staff_number: Mapped[str | None] = mapped_column(Text)  # for SPRPTA staff
    phone: Mapped[str | None] = mapped_column(Text)
    team_label: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Vehicle(Base):
    """DB doc 2.6: buses and trishaws.

    The registered area decides which L2 officer receives a complaint.
    """

    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    vehicle_number: Mapped[str] = mapped_column(Text, unique=True)
    vehicle_type: Mapped[VehicleType] = mapped_column(VehicleTypeType)
    registered_area_id: Mapped[int] = mapped_column(ForeignKey("areas.id"))
    owner_person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Permit(Base):
    """DB doc 2.7: a vehicle permit. More columns come once SPRPTA's real permit data is seen."""

    __tablename__ = "permits"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    permit_number: Mapped[str] = mapped_column(Text, unique=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    holder_person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ComplaintCategory(Base):
    """DB doc 2.9: admin-editable complaint categories."""

    __tablename__ = "complaint_categories"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Severity(Base):
    """DB doc 2.10: Critical, High, Medium and Low.

    Holds the time targets (calendar days from registration) and the rating
    weight, so Admin can change them without a code change. The values are
    proposed defaults, not given by the client.
    """

    __tablename__ = "severities"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    rank: Mapped[int] = mapped_column(SmallInteger)  # 1 = most severe
    forward_days: Mapped[int] = mapped_column(Integer)  # 0 means same day
    decide_days: Mapped[int] = mapped_column(Integer)
    close_days: Mapped[int] = mapped_column(Integer)
    rating_weight: Mapped[Decimal] = mapped_column(Numeric)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ComplaintMedium(Base):
    """DB doc 2.11: how a complaint reached SPRPTA (Email, Letter, WhatsApp, SMS, Portal, ...)."""

    __tablename__ = "complaint_mediums"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    is_system: Mapped[bool] = mapped_column(Boolean, server_default=false())  # true for Portal: cannot be removed
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
