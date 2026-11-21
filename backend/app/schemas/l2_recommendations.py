"""Response shapes of the read-only recommendation register for Level 2 (UC-L2-08)."""

from datetime import date, datetime

from pydantic import BaseModel

from app.core.enums import RecommendationStatus, RecommendationType
from app.schemas.l2_cases import RecommendationRow


class RecommendationPage(BaseModel):
    items: list[RecommendationRow]
    total: int
    page: int
    page_size: int
    counts: dict[str, int]  # per status, plus "all", matching the type and the search


class RecommendationDetail(BaseModel):
    id: int
    recommendation_type: RecommendationType
    status: RecommendationStatus
    title: str
    details: str
    medium: str | None
    received_date: date | None
    person: str | None  # the person commended
    entered_by: str
    created_at: datetime
    status_changed_at: datetime | None
