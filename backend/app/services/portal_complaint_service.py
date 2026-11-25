"""The complainant's own complaints (UC-CP-03, UC-CP-04): lodge one and follow it.

A portal complaint starts as "submitted" and gets no reference number: Level 1
checks it first (that is what guards the portal against fake accounts). The
complainant only ever sees four simple steps, never the ten internal statuses,
and never staff notes or the severity.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.enums import ComplaintStatus
from app.core.timezone import LOCAL
from app.models import (
    Area,
    ComplainantAccount,
    Complaint,
    ComplaintAttachment,
    ComplaintCategory,
    ComplaintMedium,
    ComplaintTargetType,
    RouteStand,
    Vehicle,
)
from app.schemas.portal import (
    Named,
    PortalAttachment,
    PortalCategory,
    PortalComplaint,
    PortalComplaintForm,
    PortalOptions,
    PortalPlace,
    PortalTarget,
    PortalVehicle,
)
from app.services import audit_service
from app.services import complaint_attachment_service as attachments
from app.services import complaint_lookup_service as lookup
from app.services.auth_service import Principal
from app.services.complaint_intake_service import ComplaintError

LIST_LIMIT = 200
SUGGESTION_LIMIT = 8

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
        attachments=[
            PortalAttachment.model_validate(a, from_attributes=True)
            for a in db.scalars(
                select(ComplaintAttachment)
                .where(ComplaintAttachment.complaint_id == c.id, ComplaintAttachment.removed_at.is_(None))
                .order_by(ComplaintAttachment.id)
            )
        ],
        can_delete=_is_open(c),
    )


def _is_open(c: Complaint) -> bool:
    """Level 1 has not checked it yet, so the complainant may still change it, add or remove files, or delete it."""
    return c.status == ComplaintStatus.SUBMITTED and c.withdrawn_at is None


def _own(db: Session, principal: Principal, complaint_id: int, *, lock: bool = False) -> Complaint:
    """The caller's own complaint. Someone else's, a deleted one and a missing one all look the same: not found."""
    query = select(Complaint).where(
        Complaint.id == complaint_id,
        Complaint.complainant_account_id == principal.id,
        Complaint.status != ComplaintStatus.DRAFT,
        Complaint.withdrawn_at.is_(None),
    )
    c = db.scalar(query.with_for_update() if lock else query)
    if c is None:
        raise ComplaintError(404, "not_found", "That complaint does not exist.")
    return c


def _own_open(db: Session, principal: Principal, complaint_id: int) -> Complaint:
    c = _own(db, principal, complaint_id, lock=True)
    if not _is_open(c):
        raise ComplaintError(
            409, "already_checked", "SPRPTA has already started on this complaint, so it can no longer be changed."
        )
    return c


def list_own(db: Session, principal: Principal) -> list[PortalComplaint]:
    rows = db.scalars(
        select(Complaint)
        .where(
            Complaint.complainant_account_id == principal.id,
            Complaint.status != ComplaintStatus.DRAFT,
            Complaint.withdrawn_at.is_(None),
        )
        .order_by(Complaint.id.desc())
        .limit(LIST_LIMIT)
    )
    return [_out(db, c) for c in rows]


def get_own(db: Session, principal: Principal, complaint_id: int) -> PortalComplaint:
    return _out(db, _own(db, principal, complaint_id))


# ---------------------------------------------------------------- deleting


def withdraw(db: Session, principal: Principal, complaint_id: int) -> None:
    """Delete a complaint that Level 1 has not checked yet.

    The row stays in the complaints table, marked withdrawn, with its files and its audit trail: nothing about a
    complaint is ever removed. Staff lists leave it out. Once SPRPTA has started on it, it can no longer be deleted.
    """
    c = _own_open(db, principal, complaint_id)
    c.withdrawn_at = datetime.now(LOCAL)
    audit_service.record(
        db, principal, action="complaint.withdraw_portal", entity_type="complaints", entity_id=c.id,
        complaint_id=c.id, from_status=c.status, to_status=c.status, reason="Deleted by the complainant",
    )
    db.commit()


# ---------------------------------------------------------------- evidence files


def add_file(db: Session, principal: Principal, complaint_id: int, *, file: BinaryIO, file_name: str, mime_type: str) -> PortalAttachment:
    c = _own_open(db, principal, complaint_id)
    saved = attachments.store_attachment(
        db, principal, c, file=file, file_name=file_name, mime_type=mime_type, description=None
    )
    return PortalAttachment.model_validate(saved, from_attributes=True)


def _find_file(db: Session, complaint: Complaint, attachment_id: int) -> ComplaintAttachment:
    a = db.scalar(
        select(ComplaintAttachment).where(
            ComplaintAttachment.id == attachment_id,
            ComplaintAttachment.complaint_id == complaint.id,
            ComplaintAttachment.removed_at.is_(None),
        )
    )
    if a is None:
        raise ComplaintError(404, "not_found", "That file does not exist.")
    return a


def remove_file(db: Session, principal: Principal, complaint_id: int, attachment_id: int) -> None:
    c = _own_open(db, principal, complaint_id)
    a = _find_file(db, c, attachment_id)
    a.removed_at = datetime.now(LOCAL)
    audit_service.record(
        db, principal, action="attachment.remove", entity_type="complaint_attachments", entity_id=a.id,
        complaint_id=c.id, details={"file_name": a.file_name},
    )
    db.commit()


def open_file(db: Session, principal: Principal, complaint_id: int, attachment_id: int) -> tuple[Path, str, str]:
    """Where a file of the caller's own complaint is stored, its name and its type."""
    a = _find_file(db, _own(db, principal, complaint_id), attachment_id)
    root = attachments.storage_root().resolve()
    path = (root / a.storage_path).resolve()
    if root not in path.parents:  # the stored path never points outside the upload folder; refuse if it ever did
        raise ComplaintError(404, "not_found", "That file does not exist.")
    return path, a.file_name, a.mime_type


# ---------------------------------------------------------------- finding a vehicle while typing


def suggest_vehicles(db: Session, text: str) -> list[PortalVehicle]:
    """Vehicles whose number starts with what was typed. Spaces, dashes and capitals do not matter."""
    typed = re.sub(r"[\s-]", "", text).upper()
    if not typed:
        return []
    plain = func.upper(func.replace(func.replace(Vehicle.vehicle_number, " ", ""), "-", ""))
    prefix = typed.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
    rows = db.execute(
        select(Vehicle, Area.name)
        .join(Area, Area.id == Vehicle.registered_area_id)
        .where(Vehicle.is_active, plain.like(prefix, escape="\\"))
        .order_by(Vehicle.vehicle_number)
        .limit(SUGGESTION_LIMIT)
    )
    return [
        PortalVehicle(
            vehicle_number=v.vehicle_number, vehicle_type=v.vehicle_type.value, area_id=v.registered_area_id, area_name=area
        )
        for v, area in rows
    ]


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
