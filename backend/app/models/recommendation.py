from datetime import date, datetime

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, ForeignKey, Identity, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.enums import RecommendationStatus, RecommendationType
from app.db.base import Base
from app.db.types import RecommendationStatusType, RecommendationTypeType


class Recommendation(Base):
    """DB doc 4.1: improvement suggestions and commendations entered by L1.

    Visible to L2 and L3 only, and only L3 changes the status. The field list
    is not in the client's knowledge base, so these columns are proposals.
    """

    __tablename__ = "recommendations"
    __table_args__ = (
        # Only a commendation names a person.
        CheckConstraint(
            "recommendation_type = 'commendation' OR subject_person_id IS NULL",
            name="person_only_for_commendation",
        ),
        CheckConstraint(
            "status <> 'commendation_verified' OR recommendation_type = 'commendation'",
            name="verified_only_for_commendation",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    recommendation_type: Mapped[RecommendationType] = mapped_column(RecommendationTypeType)
    status: Mapped[RecommendationStatus] = mapped_column(RecommendationStatusType, server_default="new")
    title: Mapped[str] = mapped_column(Text)
    details: Mapped[str] = mapped_column(Text)
    medium_id: Mapped[int | None] = mapped_column(ForeignKey("complaint_mediums.id"))  # how it reached SPRPTA
    received_date: Mapped[date | None] = mapped_column(Date)
    subject_person_id: Mapped[int | None] = mapped_column(ForeignKey("people.id"))  # the person commended
    entered_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # the L1 who entered it
    status_changed_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))  # must be an L3 user
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # the rating counts commendations by this date
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
