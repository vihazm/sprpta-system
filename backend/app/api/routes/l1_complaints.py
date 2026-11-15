"""The Level 1 complaint form: /api/l1/complaints (office staff only)."""

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import error, get_current_principal, require_roles
from app.core.enums import ComplaintStatus, PersonType
from app.db.session import get_db
from app.schemas.admin_users import MAX_ID, NoNul
from app.schemas.l1_dashboard import ComplaintPage, ListFilter, ReferenceHit, Scope, TargetFilter
from app.schemas.l1_complaints import (
    AttachmentOut,
    CategoryOption,
    ComplaintForm,
    ComplaintOut,
    DuplicateCandidate,
    DuplicateChoice,
    FormOptions,
    PersonLookup,
    RejectBody,
    TargetOption,
    VehicleLookup,
)
from app.services import complaint_attachment_service as attachments
from app.services import complaint_intake_service as intake
from app.services import complaint_list_service as lists
from app.services import complaint_lookup_service as lookup
from app.services.auth_service import Principal
from app.services.complaint_intake_service import ComplaintError


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(
    prefix="/api/l1/complaints",
    tags=["l1"],
    dependencies=[Depends(require_roles("l1")), Depends(_no_store)],
)

ComplaintId = Annotated[int, Path(ge=1, le=MAX_ID)]
OtherId = Annotated[int, Path(ge=1, le=MAX_ID)]


def _fail(exc: ComplaintError) -> HTTPException:
    return error(exc.status, exc.code, exc.message)


# ---------------------------------------------------------------- lookups (declared first: fixed paths)


@router.get("/options", response_model=FormOptions)
def form_options(db: Session = Depends(get_db)) -> FormOptions:
    return lookup.form_options(db)


@router.get("/lookup/vehicle", response_model=VehicleLookup)
def find_vehicle(number: Annotated[str, NoNul, Query(min_length=1, max_length=20)], db: Session = Depends(get_db)):
    vehicle = lookup.find_vehicle(db, number)
    if vehicle is None:
        raise error(404, "vehicle_not_found", "No vehicle on record has that number.")
    return lookup.vehicle_lookup(db, vehicle)


@router.get("/lookup/people", response_model=list[PersonLookup])
def find_people(
    search: Annotated[str, NoNul, Query(max_length=100)] = "",
    person_type: PersonType | None = None,
    db: Session = Depends(get_db),
) -> list[PersonLookup]:
    return lookup.search_people(db, search=search, person_type=person_type)


# ---------------------------------------------------------------- the complaint


@router.get("/by-reference", response_model=ReferenceHit)
def find_by_reference(
    reference: Annotated[str, NoNul, Query(min_length=1, max_length=40)], db: Session = Depends(get_db)
) -> ReferenceHit:
    hit = lists.find_by_reference(db, reference)
    if hit is None:
        raise error(404, "reference_not_found", "No complaint has that reference number.")
    return hit


@router.get("/targets", response_model=list[TargetOption])
def targets(db: Session = Depends(get_db)) -> list[TargetOption]:
    """Who a complaint can be against."""
    return lookup.list_targets(db)


@router.get("/categories", response_model=list[CategoryOption])
def categories(target_id: Annotated[int | None, Query(ge=1, le=MAX_ID)] = None, db: Session = Depends(get_db)) -> list[CategoryOption]:
    """The issue categories open to a target (every category where none has been approved for it)."""
    return lookup.allowed_categories(db, target_id)


@router.get("", response_model=ComplaintPage)
def list_complaints(
    status: ListFilter | None = None,
    target: TargetFilter | None = None,
    scope: Scope = "mine",
    search: Annotated[str, NoNul, Query(max_length=100)] = "",
    page: int = Query(1, ge=1),
    officer: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ComplaintPage:
    return lists.list_complaints(
        db, status=status, target=target, scope=scope, officer_id=officer.id, search=search, page=page
    )


@router.post("", response_model=ComplaintOut, status_code=201)
def create_draft(
    body: ComplaintForm, user: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> ComplaintOut:
    try:
        return intake.create_draft(db, user, body)
    except ComplaintError as exc:
        raise _fail(exc) from None


@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(complaint_id: ComplaintId, db: Session = Depends(get_db)) -> ComplaintOut:
    try:
        return intake.get_complaint(db, complaint_id)
    except ComplaintError as exc:
        raise _fail(exc) from None


@router.put("/{complaint_id}", response_model=ComplaintOut)
def update_complaint(
    complaint_id: ComplaintId,
    body: ComplaintForm,
    user: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ComplaintOut:
    try:
        return intake.update_complaint(db, user, complaint_id, body)
    except ComplaintError as exc:
        raise _fail(exc) from None


@router.post("/{complaint_id}/incomplete", response_model=ComplaintOut)
def save_incomplete(
    complaint_id: ComplaintId, user: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> ComplaintOut:
    try:
        return intake.save_incomplete(db, user, complaint_id)
    except ComplaintError as exc:
        raise _fail(exc) from None


@router.post("/{complaint_id}/forward", response_model=ComplaintOut)
def forward(
    complaint_id: ComplaintId, user: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> ComplaintOut:
    try:
        return intake.forward(db, user, complaint_id)
    except ComplaintError as exc:
        raise _fail(exc) from None


@router.post("/{complaint_id}/reject", response_model=ComplaintOut)
def reject(
    complaint_id: ComplaintId,
    body: RejectBody,
    user: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> ComplaintOut:
    try:
        return intake.reject(db, user, complaint_id, body)
    except ComplaintError as exc:
        raise _fail(exc) from None


# ---------------------------------------------------------------- duplicate check


@router.get("/{complaint_id}/duplicates", response_model=list[DuplicateCandidate])
def possible_duplicates(complaint_id: ComplaintId, db: Session = Depends(get_db)) -> list[DuplicateCandidate]:
    try:
        return intake.get_duplicates(db, complaint_id)
    except ComplaintError as exc:
        raise _fail(exc) from None


@router.put("/{complaint_id}/duplicates/{candidate_id}", response_model=list[DuplicateCandidate])
def decide_duplicate(
    complaint_id: ComplaintId,
    candidate_id: OtherId,
    body: DuplicateChoice,
    user: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[DuplicateCandidate]:
    try:
        return intake.decide_duplicate(db, user, complaint_id, candidate_id, body.link_type)
    except ComplaintError as exc:
        raise _fail(exc) from None


# ---------------------------------------------------------------- evidence


@router.post("/{complaint_id}/attachments", response_model=AttachmentOut, status_code=201)
def add_attachment(
    complaint_id: ComplaintId,
    file: UploadFile = File(),
    description: Annotated[str | None, Form(max_length=200)] = None,
    user: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> AttachmentOut:
    try:
        return attachments.add_attachment(
            db,
            user,
            complaint_id,
            file=file.file,
            file_name=file.filename or "file",
            mime_type=(file.content_type or "").split(";")[0].strip().lower(),
            description=description,
        )
    except ComplaintError as exc:
        raise _fail(exc) from None


@router.delete("/{complaint_id}/attachments/{attachment_id}", status_code=204)
def remove_attachment(
    complaint_id: ComplaintId,
    attachment_id: OtherId,
    user: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> Response:
    try:
        attachments.remove_attachment(db, user, complaint_id, attachment_id)
    except ComplaintError as exc:
        raise _fail(exc) from None
    return Response(status_code=204)
