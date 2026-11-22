"""The recommendation register as Level 2 sees it (UC-L2-08): read-only, since only Level 3 changes a status.

Recommendations carry no area, so every officer sees all of them.
"""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.enums import RecommendationStatus, RecommendationType
from app.models import ComplaintMedium, Person, Recommendation, User
from app.schemas.l2_cases import RecommendationRow
from app.schemas.l2_recommendations import RecommendationDetail, RecommendationPage
from app.services.complaint_intake_service import ComplaintError

PAGE_SIZE = 10


def _row(r: Recommendation) -> RecommendationRow:
    return RecommendationRow.model_validate(r, from_attributes=True)


def latest(db: Session, *, limit: int) -> list[RecommendationRow]:
    rows = db.scalars(select(Recommendation).order_by(Recommendation.created_at.desc(), Recommendation.id.desc()).limit(limit))
    return [_row(r) for r in rows]


def list_recommendations(
    db: Session,
    *,
    recommendation_type: RecommendationType | None,
    status: RecommendationStatus | None,
    search: str,
    page: int,
) -> RecommendationPage:
    base = []
    if recommendation_type:
        base.append(Recommendation.recommendation_type == recommendation_type)
    term = search.strip()
    if term:
        commended = select(Person.id).where(Person.full_name.icontains(term, autoescape=True))
        base.append(
            or_(
                Recommendation.title.icontains(term, autoescape=True),
                Recommendation.details.icontains(term, autoescape=True),
                Recommendation.subject_person_id.in_(commended),
            )
        )
    rows = db.execute(
        select(Recommendation.status, func.count()).where(*base).group_by(Recommendation.status)
    ).all()
    counts = {s.value: 0 for s in RecommendationStatus}
    counts.update({s.value: n for s, n in rows})
    counts["all"] = sum(counts.values())

    if status:
        base.append(Recommendation.status == status)
    total = counts[status.value] if status else counts["all"]
    page = min(page, max(1, -(-total // PAGE_SIZE)))
    items = db.scalars(
        select(Recommendation)
        .where(*base)
        .order_by(Recommendation.created_at.desc(), Recommendation.id.desc())
        .limit(PAGE_SIZE)
        .offset((page - 1) * PAGE_SIZE)
    )
    return RecommendationPage(items=[_row(r) for r in items], total=total, page=page, page_size=PAGE_SIZE, counts=counts)


def get_recommendation(db: Session, recommendation_id: int) -> RecommendationDetail:
    r = db.get(Recommendation, recommendation_id)
    if r is None:
        raise ComplaintError(404, "not_found", "That recommendation does not exist.")
    medium = db.get(ComplaintMedium, r.medium_id) if r.medium_id else None
    person = db.get(Person, r.subject_person_id) if r.subject_person_id else None
    entered_by = db.get(User, r.entered_by_user_id)
    return RecommendationDetail(
        id=r.id,
        recommendation_type=r.recommendation_type,
        status=r.status,
        title=r.title,
        details=r.details,
        medium=medium.name if medium else None,
        received_date=r.received_date,
        person=person.full_name if person else None,
        entered_by=entered_by.full_name if entered_by else "Unknown",
        created_at=r.created_at,
        status_changed_at=r.status_changed_at,
    )
