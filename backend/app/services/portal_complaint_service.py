"""The complainant's own complaints (UC-CP-03, UC-CP-04): lodge one and follow it.

A portal complaint starts as "submitted" and gets no reference number: Level 1
checks it first (that is what guards the portal against fake accounts). The
complainant only ever sees four simple steps, never the ten internal statuses,
and never staff notes or the severity.
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import ComplaintStatus
from app.core.timezone import LOCAL
from app.models import (
    Area,
    ComplainantAccount,
    Complaint,
    ComplaintCategory,
    ComplaintMedium,
    ComplaintTargetType,
    RouteStand,
)
from app.schemas.portal import (
    Named,
    PortalCategory,
    PortalComplaint,
    PortalComplaintForm,
    PortalOptions,
    PortalPlace,
    PortalTarget,
)
from app.services import audit_service
from app.services import complaint_lookup_service as lookup
from app.services.auth_service import Principal
from app.services.complaint_intake_service import ComplaintError

LIST_LIMIT = 200

# Internal status to the four steps the complainant sees. Closed and rejected both end the case.
_STEP = {
    ComplaintStatus.SUBMITTED: 1,
    ComplaintStatus.INCOMPLETE: 2,
    ComplaintStatus.FORWARDED: 2,
    ComplaintStatus.UNDER_REVIEW: 2,
    ComplaintStatus.AWAITING_IMPLEMENTATION: 3,
    ComplaintStatus.DONE_AWAITING_APPROVAL: 3,
    ComplaintStatus.ESCALATED: 3,
    ComplaintStatus.CLOSED: 4,
    ComplaintStatus.REJECTED: 4,
}
_LABEL = {
    1: "Submitted (awaiting Level 1 check)",
    2: "Received",
    3: "Action in progress",
    4: "Closed",
}


def step_of(status: ComplaintStatus) -> int:
    """The step a complaint with this internal status shows. A draft is never shown to the complainant."""
    return _STEP[status]


# ---------------------------------------------------------------- reading


def options(db: Session) -> PortalOptions:
    areas = db.scalars(select(Area).where(Area.is_active).order_by(Area.name))
    places = db.scalars(select(RouteStand).where(RouteStand.is_active).order_by(RouteStand.name))
    return PortalOptions(
        areas=[Named(id=a.id, name=a.name) for a in areas],
        targets=[PortalTarget(id=t.id, name=t.name, code=t.code) for t in lookup.list_targets(db)],
        categories=[PortalCategory(id=c.id, name=c.name, target_ids=c.target_ids) for c in lookup.allowed_categories(db, None)],
        routes_stands=[PortalPlace(id=p.id, name=p.name, kind=p.kind.value, area_id=p.area_id) for p in places],
    )


def _name(db: Session, model, row_id: int | None) -> str | None:
    return db.scalar(select(model.name).where(model.id == row_id)) if row_id else None


def _out(db: Session, c: Complaint) -> PortalComplaint:
    step = step_of(c.status)
    rejected = c.status == ComplaintStatus.REJECTED
    return PortalComplaint(
        id=c.id,
        reference_number=c.reference_number,
        subject=c.subject or "",
        complaint_date=c.complaint_date,
        submitted_at=c.created_at,
        step=step,
        status_label="Closed (not accepted)" if rejected else _LABEL[step],
        outcome="not_accepted" if rejected else ("closed" if step == 4 else "open"),
        step_dates=[c.created_at, c.registered_at, c.decided_at, c.closed_at or c.rejected_at],
        target_name=_name(db, ComplaintTargetType, c.target_type_id),
        category_name=_name(db, ComplaintCategory, c.category_id),
        area_name=_name(db, Area, c.area_id),
        route_stand_name=_name(db, RouteStand, c.route_stand_id),
        vehicle_number=c.vehicle_number_entered,
        description=c.description,
    )


def list_own(db: Session, principal: Principal) -> list[PortalComplaint]:
    rows = db.scalars(
        select(Complaint)
        .where(
            Complaint.complainant_account_id == principal.id,
            Complaint.status != ComplaintStatus.DRAFT,
        )
        .order_by(Complaint.id.desc())
        .limit(LIST_LIMIT)
    )
    return [_out(db, c) for c in rows]


def get_own(db: Session, principal: Principal, complaint_id: int) -> PortalComplaint:
    c = db.scalar(
        select(Complaint).where(
            Complaint.id == complaint_id,
            Complaint.complainant_account_id == principal.id,
            Complaint.status != ComplaintStatus.DRAFT,
        )
    )
    if c is None:  # someone else's complaint looks the same as one that does not exist
        raise ComplaintError(404, "not_found", "That complaint does not exist.")
    return _out(db, c)


# ---------------------------------------------------------------- lodging


def _active(db: Session, model, row_id: int, label: str):
    row = db.scalar(select(model).where(model.id == row_id, model.is_active))
    if row is None:
        raise ComplaintError(422, f"unknown_{label}", f"Choose a valid {label}.")
    return row


def submit(db: Session, principal: Principal, data: PortalComplaintForm) -> PortalComplaint:
    """Save a new complaint as Submitted, awaiting the Level 1 check."""
    if data.complaint_date > datetime.now(LOCAL).date():
        raise ComplaintError(422, "future_date", "The date cannot be in the future.")
    target = _active(db, ComplaintTargetType, data.target_type_id, "target")
    _active(db, ComplaintCategory, data.category_id, "category")
    if data.category_id not in {c.id for c in lookup.allowed_categories(db, target.id)}:
        raise ComplaintError(422, "invalid_category", f"That category is not used for a {target.name.lower()} complaint.")
    area = _active(db, Area, data.area_id, "area")
    if data.route_stand_id is not None:
        place = _active(db, RouteStand, data.route_stand_id, "route_stand")
        if place.area_id is not None and place.area_id != area.id:
            raise ComplaintError(422, "route_not_in_area", "That route or stand is not in the chosen area.")

    portal = db.scalar(select(ComplaintMedium).where(ComplaintMedium.is_system, ComplaintMedium.name == "Portal"))
    account = db.get(ComplainantAccount, principal.id)
    if portal is None or account is None:
        raise ComplaintError(503, "portal_unavailable", "The portal cannot take complaints right now.")

    number = (data.vehicle_number or "").strip().upper() or None
    complaint = Complaint(
        status=ComplaintStatus.SUBMITTED,
        submitted_via_portal=True,
        complainant_account_id=account.id,
        medium_id=portal.id,
        complainant_name=account.display_name,
        contact_phone=account.phone,
        contact_email=account.email,
        complaint_date=data.complaint_date,
        target_type_id=target.id,
        category_id=data.category_id,
        subject=data.subject.strip(),
        description=data.description.strip(),
        area_id=area.id,
        route_stand_id=data.route_stand_id,
        vehicle_number_entered=number,
    )
    db.add(complaint)
    db.flush()
    audit_service.record(
        db, principal, action="complaint.submit_portal", entity_type="complaints", entity_id=complaint.id,
        complaint_id=complaint.id, to_status=ComplaintStatus.SUBMITTED,
    )
    db.commit()
    return _out(db, complaint)
