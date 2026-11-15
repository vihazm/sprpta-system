"""Synthetic (development) data support: the batch marker, bus non-operating periods and route authorizations.

Everything the synthetic generator writes carries a synthetic_batch_id, so it can be told apart from real records,
reported on, and removed without touching anything else. Nothing here is real operating history.
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

NON_OPERATION_REASONS = (
    "maintenance",
    "breakdown",
    "driver_unavailable",
    "conductor_unavailable",
    "permit_suspension",
    "service_cancellation",
    "rest_day",
    "other",
)


class SyntheticBatch(Base):
    """One run of the synthetic generator: its name, scale, seed and the assumptions it used."""

    __tablename__ = "synthetic_batches"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    scale: Mapped[str] = mapped_column(Text)
    seed: Mapped[int] = mapped_column(Integer)
    config: Mapped[dict] = mapped_column(JSONB)
    note: Mapped[str] = mapped_column(Text, server_default="Synthetic development data. Not real operating history.")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BusNonOperation(Base):
    """A period (one or more days) when a bus did not operate, and why. Inclusive of both dates."""

    __tablename__ = "bus_non_operations"
    __table_args__ = (
        CheckConstraint("end_date >= start_date", name="valid_period"),
        CheckConstraint(
            "reason IN ('" + "', '".join(NON_OPERATION_REASONS) + "')", name="known_reason"
        ),
        Index("ix_bus_non_operations_vehicle_period", "vehicle_id", "start_date", "end_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    synthetic_batch_id: Mapped[int | None] = mapped_column(ForeignKey("synthetic_batches.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RouteAuthorization(Base):
    """A bus authorized to run a route other than its permit's own, for a period (valid_to empty: still holds)."""

    __tablename__ = "route_authorizations"
    __table_args__ = (
        CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="valid_period"),
        Index("ix_route_authorizations_vehicle_from", "vehicle_id", "valid_from"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"))
    route_stand_id: Mapped[int] = mapped_column(ForeignKey("routes_stands.id"))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text)
    synthetic_batch_id: Mapped[int | None] = mapped_column(ForeignKey("synthetic_batches.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SyntheticComplaintEvent(Base):
    """The simulated history of a synthetic complaint: each status change and each bus verification.

    It is kept apart from audit_log on purpose: audit_log is append-only, so simulated rows written there could never
    be removed, and the real audit trail must not hold invented history. Real complaints never appear here.
    """

    __tablename__ = "synthetic_complaint_events"
    __table_args__ = (
        UniqueConstraint("complaint_id", "seq", name="uq_synthetic_complaint_events_complaint_id_seq"),
        Index("ix_synthetic_complaint_events_batch", "synthetic_batch_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    complaint_id: Mapped[int] = mapped_column(ForeignKey("complaints.id"))
    seq: Mapped[int] = mapped_column(SmallInteger)
    event: Mapped[str] = mapped_column(Text)  # created, status_change, bus_verification
    from_status: Mapped[str | None] = mapped_column(Text)
    to_status: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    details: Mapped[dict | None] = mapped_column(JSONB)
    synthetic_batch_id: Mapped[int] = mapped_column(ForeignKey("synthetic_batches.id"))
