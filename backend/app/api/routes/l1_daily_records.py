"""Daily bus operation records entered by Level 1: /api/l1/daily-records (add, list, reopen and edit your own)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import error, get_current_principal, require_roles
from app.core.enums import DutyRecordStatus
from app.db.session import get_db
from app.schemas.admin_users import MAX_ID
from app.schemas.l1_daily_records import DailyRecordIn, DailyRecordList, DailyRecordOut
from app.services import l1_daily_record_service as records
from app.services.auth_service import Principal
from app.services.duty_record_service import DutyRecordError

def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"  # every answer here names people on duty


router = APIRouter(
    prefix="/api/l1/daily-records",
    tags=["level 1"],
    dependencies=[Depends(require_roles("l1")), Depends(_no_store)],
)

RecordId = Annotated[int, Path(ge=1, le=MAX_ID)]


def _fail(exc: DutyRecordError) -> HTTPException:
    return error(exc.status, exc.code, exc.message)


@router.get("", response_model=DailyRecordList)
def list_mine(
    service_date: date | None = None,
    search: Annotated[str | None, Query(max_length=40)] = None,
    status: DutyRecordStatus | None = None,
    page: Annotated[int, Query(ge=1, le=10_000)] = 1,
    officer: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> DailyRecordList:
    return records.list_mine(db, officer, service_date=service_date, search=search, status=status, page=page)


@router.post("", response_model=DailyRecordOut, status_code=201)
def create_record(
    body: DailyRecordIn, officer: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> DailyRecordOut:
    try:
        return records.create(db, officer, body)
    except DutyRecordError as exc:
        raise _fail(exc) from None


@router.get("/{record_id}", response_model=DailyRecordOut)
def get_record(
    record_id: RecordId, officer: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> DailyRecordOut:
    try:
        return records.get(db, officer, record_id)
    except DutyRecordError as exc:
        raise _fail(exc) from None


@router.put("/{record_id}", response_model=DailyRecordOut)
def update_record(
    record_id: RecordId,
    body: DailyRecordIn,
    officer: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> DailyRecordOut:
    try:
        return records.update(db, officer, record_id, body)
    except DutyRecordError as exc:
        raise _fail(exc) from None
