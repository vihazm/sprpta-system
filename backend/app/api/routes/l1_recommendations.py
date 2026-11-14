"""The Level 1 recommendation form: /api/l1/recommendations (office staff only).

There is deliberately no way to read one back: L1 cannot view a recommendation after entry.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import error, get_current_principal, require_roles
from app.db.session import get_db
from app.schemas.l1_recommendations import RecommendationForm, RecommendationSaved
from app.services import recommendation_service
from app.services.auth_service import Principal
from app.services.complaint_intake_service import ComplaintError

router = APIRouter(prefix="/api/l1/recommendations", tags=["l1"], dependencies=[Depends(require_roles("l1"))])


@router.post("", response_model=RecommendationSaved, status_code=201)
def create_recommendation(
    body: RecommendationForm, user: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> RecommendationSaved:
    try:
        return recommendation_service.create_recommendation(db, user, body)
    except ComplaintError as exc:
        raise error(exc.status, exc.code, exc.message) from None
