"""The complainant's own complaints: /api/cp/complaints (portal users only)."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Path as PathParam, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import error, require_roles
from app.db.session import get_db
from app.schemas.admin_users import MAX_ID, NoNul
from app.schemas.portal import (
    PortalAttachment,
    PortalComplaint,
    PortalComplaintForm,
    PortalOptions,
    PortalVehicle,
)
from app.services import portal_complaint_service as service
from app.services.auth_service import Principal
from app.services.complaint_intake_service import ComplaintError


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(
    prefix="/api/cp/complaints",
    tags=["cp"],
    dependencies=[Depends(_no_store)],
)

ComplaintId = Annotated[int, PathParam(ge=1, le=MAX_ID)]
FileId = Annotated[int, PathParam(ge=1, le=MAX_ID)]
Complainant = Annotated[Principal, Depends(require_roles("cp"))]


def _fail(exc: ComplaintError) -> HTTPException:
    return error(exc.status, exc.code, exc.message)


@router.get("/options", response_model=PortalOptions)
def form_options(_: Complainant, db: Session = Depends(get_db)) -> PortalOptions:
    return service.options(db)


@router.get("/lookup/vehicles", response_model=list[PortalVehicle])
def find_vehicles(
    _: Complainant,
    q: Annotated[str, NoNul, Query(max_length=20)] = "",
    db: Session = Depends(get_db),
) -> list[PortalVehicle]:
    """Vehicle numbers that start with what the complainant has typed so far."""
    return service.suggest_vehicles(db, q)


@router.get("", response_model=list[PortalComplaint])
def my_complaints(principal: Complainant, db: Session = Depends(get_db)) -> list[PortalComplaint]:
    return service.list_own(db, principal)


@router.post("", response_model=PortalComplaint, status_code=status.HTTP_201_CREATED)
def submit(body: PortalComplaintForm, principal: Complainant, db: Session = Depends(get_db)) -> PortalComplaint:
    try:
        return service.submit(db, principal, body)
    except ComplaintError as exc:
        raise _fail(exc) from None


@router.get("/{complaint_id}", response_model=PortalComplaint)
def one_complaint(complaint_id: ComplaintId, principal: Complainant, db: Session = Depends(get_db)) -> PortalComplaint:
    try:
        return service.get_own(db, principal, complaint_id)
    except ComplaintError as exc:
        raise _fail(exc) from None


@router.delete("/{complaint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_complaint(complaint_id: ComplaintId, principal: Complainant, db: Session = Depends(get_db)) -> Response:
    """Delete a complaint Level 1 has not checked yet. The record stays in the database, marked as withdrawn."""
    try:
        service.withdraw(db, principal, complaint_id)
    except ComplaintError as exc:
        raise _fail(exc) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------- evidence files


@router.post("/{complaint_id}/attachments", response_model=PortalAttachment, status_code=status.HTTP_201_CREATED)
def add_file(
    complaint_id: ComplaintId,
    principal: Complainant,
    file: UploadFile = File(),
    db: Session = Depends(get_db),
) -> PortalAttachment:
    try:
        return service.add_file(
            db,
            principal,
            complaint_id,
            file=file.file,
            file_name=file.filename or "file",
            mime_type=(file.content_type or "").split(";")[0].strip().lower(),
        )
    except ComplaintError as exc:
        raise _fail(exc) from None


@router.get("/{complaint_id}/attachments/{attachment_id}/file")
def view_file(complaint_id: ComplaintId, attachment_id: FileId, principal: Complainant, db: Session = Depends(get_db)):
    """The file itself, so it can be shown or opened in the browser. Only the owner of the complaint can ask."""
    try:
        path, name, media_type = service.open_file(db, principal, complaint_id, attachment_id)
    except ComplaintError as exc:
        raise _fail(exc) from None
    if not Path(path).is_file():
        raise error(404, "file_missing", "The file could not be found on the server.")
    return FileResponse(
        path,
        media_type=media_type,
        filename=name,
        content_disposition_type="inline",
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.delete("/{complaint_id}/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_file(
    complaint_id: ComplaintId, attachment_id: FileId, principal: Complainant, db: Session = Depends(get_db)
) -> Response:
    try:
        service.remove_file(db, principal, complaint_id, attachment_id)
    except ComplaintError as exc:
        raise _fail(exc) from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
