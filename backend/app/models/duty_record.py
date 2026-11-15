"""Daily operation records: which bus ran which trip on a date, who was on duty, and who owned the bus.

Level 1 uses them to verify a complaint (Bus & Permit Lookup). Level 1 officers may add records, which stay
pending (draft) until System Admin approves and publishes them; lookups see only published records. A record moves draft, approved, published.
"""

from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import DutyRecordStatus
from app.db.base import Base
from app.db.types import DutyRecordStatusType

_APPROVED = "status = 'draft' OR (approved_by_user_id IS NOT NULL AND approved_at IS NOT NULL)"
_PUBLISHED = "status <> 'published' OR (published_by_user_id IS NOT NULL AND published_at IS NOT NULL)"


class DailyTrip(Base):
    """One trip (or duty shift) of a bus on a date. A bus can have several on the same day."""

    __tablename__ = "daily_trips"
    __table_args__ = (
        UniqueConstraint(
            "service_date", "vehicle_id", "departure_time", name="uq_daily_trips_service_date_vehicle_id_departure_time"
        ),
        CheckConstraint(_APPROVED, name="approved_has_approver"),
        CheckConstraint(_PUBLISHED, name="published_has_publisher"),
        Index("ix_daily_trips_vehicle_date", "vehicle_id", "service_date"),
        Index("ix_daily_trips_date_status", "service_date", "status"),
        Index("ix_daily_trips_created_by_date", "created_by_user_id", "service_date"),
        Index("ix_daily_trips_route_date", "route_stand_id", "service_date"),
        CheckConstraint("trip_status IN ('completed', 'cancelled', 'partial')", name="known_trip_status"),
        CheckConstraint("direction IS NULL OR direction IN ('outbound', 'return')", name="known_direction"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    service_date: Mapped[date] = mapped_column(Date)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    permit_id: Mapped[int] = mapped_column(ForeignKey("permits.id"))  # the permit the bus ran this trip under
    route_stand_id: Mapped[int] = mapped_column(ForeignKey("routes_stands.id"))
    departure_time: Mapped[time] = mapped_column(Time)
    origin: Mapped[str] = mapped_column(Text)  # as the record states it, so a trip can run part of a route
    destination: Mapped[str] = mapped_column(Text)
    end_time: Mapped[time | None] = mapped_column(Time)
    remarks: Mapped[str | None] = mapped_column(Text)
    owner_person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))  # the owner as the record states it
    # How the trip went, apart from the record's publication status below. A cancelled trip never ran.
    trip_status: Mapped[str] = mapped_column(Text, server_default="completed")
    direction: Mapped[str | None] = mapped_column(Text)  # outbound or return
    actual_departure: Mapped[time | None] = mapped_column(Time)
    actual_arrival: Mapped[time | None] = mapped_column(Time)
    synthetic_batch_id: Mapped[int | None] = mapped_column(ForeignKey("synthetic_batches.id"))  # set: simulated, not real
    status: Mapped[DutyRecordStatus] = mapped_column(DutyRecordStatusType, server_default="draft")
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    approved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class TripDuty(Base):
    """Who was on duty for a trip. Names are shown only once Admin has verified them (verified_at).

    Either person may be missing: a missing or unverified person is shown as Unavailable or
    Unverified, never guessed.
    """

    __tablename__ = "trip_duties"
    __table_args__ = (
        CheckConstraint("(verified_by_user_id IS NULL) = (verified_at IS NULL)", name="verification_complete"),
        Index("ix_trip_duties_driver", "driver_person_id"),
        Index("ix_trip_duties_conductor", "conductor_person_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("daily_trips.id"), unique=True)  # one duty row per trip
    driver_person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    conductor_person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    driver_start: Mapped[time | None] = mapped_column(Time)
    driver_end: Mapped[time | None] = mapped_column(Time)
    conductor_start: Mapped[time | None] = mapped_column(Time)
    conductor_end: Mapped[time | None] = mapped_column(Time)
    verified_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OwnerAssignment(Base):
    """Who owned a bus over a period, for when the owner changed. valid_to is empty while it still holds."""

    __tablename__ = "owner_assignments"
    __table_args__ = (
        CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="valid_period"),
        CheckConstraint(_APPROVED, name="approved_has_approver"),
        CheckConstraint(_PUBLISHED, name="published_has_publisher"),
        Index("ix_owner_assignments_vehicle_from", "vehicle_id", "valid_from"),
    )


    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    owner_person_id: Mapped[int] = mapped_column(ForeignKey("people.id"))
    synthetic_batch_id: Mapped[int | None] = mapped_column(ForeignKey("synthetic_batches.id"))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    status: Mapped[DutyRecordStatus] = mapped_column(DutyRecordStatusType, server_default="draft")
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    approved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    published_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ComplaintDutySnapshot(Base):
    """What the verified daily record said when a complaint was saved against it.

    The names are copied as text, so the complaint keeps showing who was on duty even if the daily record
    is later corrected or withdrawn. One row per complaint; saving the complaint against another trip
    replaces it, and clearing the selected bus removes it.
    """

    __tablename__ = "complaint_duty_snapshots"
    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('Verified', 'Unverified', 'Unavailable')", name="known_verification_status"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"), unique=True)
    trip_id: Mapped[int] = mapped_column(ForeignKey("daily_trips.id"))
    service_date: Mapped[date] = mapped_column(Date)
    bus_number: Mapped[str] = mapped_column(Text)
    permit_number: Mapped[str] = mapped_column(Text)  # text: permit numbers keep their leading zeros
    route_name: Mapped[str] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(Text)
    destination: Mapped[str] = mapped_column(Text)
    departure_time: Mapped[time] = mapped_column(Time)
    owner_person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    owner_name: Mapped[str | None] = mapped_column(Text)
    driver_person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    driver_name: Mapped[str | None] = mapped_column(Text)  # only a verified person is ever stored
    conductor_person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))
    conductor_name: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(Text)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())