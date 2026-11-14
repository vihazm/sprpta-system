"""The Level 1 recommendation form (UC-L1-11, System Flow section 5.3).

L1 only enters a recommendation: it starts as New, and from then on L2 and L3
see it and only L3 changes its status. Nothing here reads one back.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.enums import RecommendationType
from app.core.timezone import LOCAL
from app.models import ComplaintMedium, Person, Recommendation
from app.schemas.l1_recommendations import RecommendationForm, RecommendationSaved
from app.services import audit_service
from app.services.auth_service import Principal
from app.services.complaint_intake_service import ComplaintError, must_exist

TITLE_LENGTH = 80


def _title(details: str) -> str:
    """The first line of the details, shortened. The form has no title of its own."""
    first = details.strip().splitlines()[0].strip()
    return first if len(first) <= TITLE_LENGTH else first[: TITLE_LENGTH - 3].rstrip() + "..."


def create_recommendation(db: Session, principal: Principal, data: RecommendationForm) -> RecommendationSaved:
    must_exist(db, ComplaintMedium, data.medium_id, "medium", ComplaintMedium.is_system.is_(False))
    if data.received_date and data.received_date > datetime.now(LOCAL).date():
        raise ComplaintError(422, "future_date", "The date cannot be in the future.")

    commendation = data.recommendation_type == RecommendationType.COMMENDATION
    if commendation and data.subject_person_id is None:
        raise ComplaintError(422, "person_required", "Choose the person who is being commended.")
    person_id = data.subject_person_id if commendation else None  # only a commendation names a person
    must_exist(db, Person, person_id, "person")

    recommendation = Recommendation(
        recommendation_type=data.recommendation_type,
        title=_title(data.details),
        details=data.details.strip(),
        medium_id=data.medium_id,
        received_date=data.received_date,
        subject_person_id=person_id,
        entered_by_user_id=principal.id,
    )
    db.add(recommendation)
    db.flush()
    audit_service.record(
        db, principal, action="recommendation.create", entity_type="recommendations", entity_id=recommendation.id,
        details={"recommendation_type": data.recommendation_type.value},
    )
    db.commit()
    return RecommendationSaved(
        id=recommendation.id,
        recommendation_type=recommendation.recommendation_type,
        status=recommendation.status,
        title=recommendation.title,
        created_at=recommendation.created_at,
    )
