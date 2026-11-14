"""Request and response shapes of the Level 1 recommendation form (UC-L1-11)."""

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.core.enums import RecommendationStatus, RecommendationType
from app.schemas.l1_complaints import Id, Text


class RecommendationForm(BaseModel):
    recommendation_type: RecommendationType
    details: Text = Field(min_length=1, max_length=5000, pattern=r"\S")
    medium_id: Id | None = None  # how it reached SPRPTA
    received_date: date | None = None
    subject_person_id: Id | None = None  # the person commended; required for a commendation


class RecommendationSaved(BaseModel):
    """What L1 gets back. L1 cannot open a recommendation again, so this is only a confirmation."""

    id: int
    recommendation_type: RecommendationType
    status: RecommendationStatus
    title: str
    created_at: datetime
