"""The complainant's own complaints: /api/cp/complaints (portal users only)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status
from sqlalchemy.orm import Session

from app.api.deps import error, require_roles
from app.db.session import get_db
from app.schemas.admin_users import MAX_ID
from app.schemas.portal import PortalComplaint, PortalComplaintForm, PortalOptions
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

ComplaintId = Annotated[int, Path(ge=1, le=MAX_ID)]
Complainant = Annotated[Principal, Depends(require_roles("cp"))]


def _fail(exc: ComplaintError) -> HTTPException:
    return error(exc.status, exc.code, exc.message)


@router.get("/options", response_model=PortalOptions)
def form_options(_: Complainant, db: Session = Depends(get_db)) -> PortalOptions:
    return service.options(db)


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
