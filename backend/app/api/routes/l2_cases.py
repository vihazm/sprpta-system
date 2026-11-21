"""The Level 2 area officer's cases: /api/l2/cases (area officers only, own area only)."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path as PathParam, Query, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import error, get_current_principal, require_roles
from app.db.session import get_db
from app.schemas.admin_users import MAX_ID, NoNul
from app.schemas.l2_cases import (
    CaseDetail,
    CaseFilter,
    CasePage,
    CaseSort,
    DecisionBody,
    EscalateBody,
    SeverityFilter,
    SolutionDocumentBody,
)
from app.services import l2_case_service as cases
from app.services.auth_service import Principal
from app.services.complaint_intake_service import ComplaintError


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(
    prefix="/api/l2/cases",
    tags=["l2"],
    dependencies=[Depends(require_roles("l2")), Depends(_no_store)],
)


ComplaintId = Annotated[int, PathParam(ge=1, le=MAX_ID)]
OtherId = Annotated[int, PathParam(ge=1, le=MAX_ID)]


def _fail(exc: ComplaintError) -> HTTPException:
    return error(exc.status, exc.code, exc.message)


def _file(path: Path, name: str, media_type: str) -> FileResponse:
    if not path.is_file():
        raise error(404, "file_missing", "The file could not be found on the server.")
    return FileResponse(
        path,
        media_type=media_type,
        filename=name,
        content_disposition_type="inline",  # opens in the browser, where it can be printed or saved
        headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )


@router.get("", response_model=CasePage)
def list_cases(
    status: CaseFilter | None = None,
    severity: SeverityFilter | None = None,
    search: Annotated[str, NoNul, Query(max_length=100)] = "",
    sort: CaseSort = "urgent",
    page: int = Query(1, ge=1),
    officer: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> CasePage:
    try:
        return cases.list_cases(db, officer, status=status, severity=severity, search=search, sort=sort, page=page)
    except ComplaintError as exc:
        raise _fail(exc) from None


@router.get("/{complaint_id}", response_model=CaseDetail)
def get_case(
    complaint_id: ComplaintId, officer: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> CaseDetail:
    try:
        return cases.get_case(db, officer, complaint_id)
    except ComplaintError as exc:
        raise _fail(exc) from None


@router.post("/{complaint_id}/review", response_model=CaseDetail)
def start_review(
    complaint_id: ComplaintId, officer: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> CaseDetail:
    """Called when the officer opens a case: a Forwarded case becomes Under review."""
    try:
        return cases.start_review(db, officer, complaint_id)
    except ComplaintError as exc:
        raise _fail(exc) from None


@router.put("/{complaint_id}/decision", response_model=CaseDetail)
def record_decision(
    complaint_id: ComplaintId,
    body: DecisionBody,
    officer: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> CaseDetail:
    try:
        return cases.record_decision(db, officer, complaint_id, body)
    except ComplaintError as exc:
        raise _fail(exc) from None


@router.post("/{complaint_id}/solution-document", response_model=CaseDetail, status_code=201)
def create_solution_document(
    complaint_id: ComplaintId,
    body: SolutionDocumentBody,
    officer: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> CaseDetail:
    try:
        return cases.create_solution_document(db, officer, complaint_id, body)
    except ComplaintError as exc:
        raise _fail(exc) from None


@router.get("/{complaint_id}/solution-document")
def solution_document(
    complaint_id: ComplaintId, officer: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> FileResponse:
    try:
        path, name = cases.solution_document_file(db, officer, complaint_id)
    except ComplaintError as exc:
        raise _fail(exc) from None
    return _file(path, name, "application/pdf")


@router.post("/{complaint_id}/escalate", response_model=CaseDetail)
def escalate(
    complaint_id: ComplaintId,
    body: EscalateBody,
    officer: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> CaseDetail:
    try:
        return cases.escalate(db, officer, complaint_id, body)
    except ComplaintError as exc:
        raise _fail(exc) from None


@router.get("/{complaint_id}/attachments/{attachment_id}")
def attachment(
    complaint_id: ComplaintId,
    attachment_id: OtherId,
    officer: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> FileResponse:
    try:
        path, name, media_type = cases.attachment_file(db, officer, complaint_id, attachment_id)
    except ComplaintError as exc:
        raise _fail(exc) from None
    return _file(path, name, media_type)
