"""The recommendation register for Level 2: /api/l2/recommendations (read-only)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import error, require_roles
from app.core.enums import RecommendationStatus, RecommendationType
from app.db.session import get_db
from app.schemas.admin_users import MAX_ID, NoNul
from app.schemas.l2_recommendations import RecommendationDetail, RecommendationPage
from app.services import l2_recommendation_service as recommendations
from app.services.complaint_intake_service import ComplaintError


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(
    prefix="/api/l2/recommendations",
    tags=["l2"],
    dependencies=[Depends(require_roles("l2")), Depends(_no_store)],
)


@router.get("", response_model=RecommendationPage)
def list_recommendations(
    recommendation_type: RecommendationType | None = Query(None, alias="type"),
    status: RecommendationStatus | None = None,
    search: Annotated[str, NoNul, Query(max_length=100)] = "",
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
) -> RecommendationPage:
    return recommendations.list_recommendations(
        db, recommendation_type=recommendation_type, status=status, search=search, page=page
    )


@router.get("/{recommendation_id}", response_model=RecommendationDetail)
def get_recommendation(
    recommendation_id: Annotated[int, Path(ge=1, le=MAX_ID)], db: Session = Depends(get_db)
) -> RecommendationDetail:
    try:
        return recommendations.get_recommendation(db, recommendation_id)
    except ComplaintError as exc:
        raise error(exc.status, exc.code, exc.message) from None
