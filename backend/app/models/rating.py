"""Staff rating (DB doc 5.4 and 5.5): stored results of the rating formula, and appeals against them."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import AppealStatus, RatingBand
from app.db.base import Base
from app.db.types import AppealStatusType, RatingBandType


class RatingSnapshot(Base):
    """DB doc 5.4: a stored result of the rating formula, with the formula version.

    Score = 100 - 5 x penalty + 2 x credits, limited to 0..100.
    """

    __tablename__ = "rating_snapshots"
    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="score_in_range"),
        Index("ix_rating_snapshots_person_computed", "person_id", text("computed_at DESC")),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    window_start: Mapped[date] = mapped_column(Date)  # the rolling 12 months used
    window_end: Mapped[date] = mapped_column(Date)
    penalty: Mapped[Decimal] = mapped_column(Numeric)  # sum of weights; partly substantiated counts 50%
    credits: Mapped[int] = mapped_column(Integer)  # verified commendations, capped at 10
    score: Mapped[Decimal] = mapped_column(Numeric)
    band: Mapped[RatingBand] = mapped_column(RatingBandType)
    formula_version: Mapped[int] = mapped_column(Integer)  # copied from system_settings
    # Contributing complaints with weights, pending complaints (listed, not counted), commendations.
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # outcome_change, commendation_verified, appeal, relink or viewed
    trigger: Mapped[str] = mapped_column(Text)


class RatingAppeal(Base):
    """DB doc 5.5: an appeal about a rating, recorded by L3 (how appeals arrive is still open)."""

    __tablename__ = "rating_appeals"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("people.id"))
    complaint_id: Mapped[int | None] = mapped_column(ForeignKey("complaints.id"))  # the disputed complaint, if one
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[AppealStatus] = mapped_column(AppealStatusType, server_default="open")
    recorded_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # the L3 user who recorded it
    lodged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # L3
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[str | None] = mapped_column(Text)  # what was corrected
    snapshot_before_id: Mapped[int | None] = mapped_column(ForeignKey("rating_snapshots.id"))
    snapshot_after_id: Mapped[int | None] = mapped_column(ForeignKey("rating_snapshots.id"))
