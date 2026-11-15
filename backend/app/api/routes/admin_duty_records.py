"""Daily operation records: /api/admin/duty-records (System Admin only: add, approve, publish)."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from sqlalchemy.orm import Session

from app.api.deps import error, get_current_principal, require_roles
from app.core.enums import DutyRecordStatus
from app.db.session import get_db
from app.schemas.admin_duty_records import OwnerAssignmentIn, OwnerAssignmentOut, TripIn, TripList, TripOut
from app.schemas.admin_users import MAX_ID
from app.services import duty_record_service as records
from app.services.auth_service import Principal
from app.services.duty_record_service import DutyRecordError

router = APIRouter(
    prefix="/api/admin/duty-records", tags=["admin"], dependencies=[Depends(require_roles("admin"))]
)

RecordId = Annotated[int, Path(ge=1, le=MAX_ID)]


def _fail(exc: DutyRecordError) -> HTTPException:
    return error(exc.status, exc.code, exc.message)


@router.get("/trips", response_model=TripList)
def list_trips(
    response: Response,
    service_date: date | None = None,
    status: DutyRecordStatus | None = None,
    db: Session = Depends(get_db),
) -> TripList:
    response.headers["Cache-Control"] = "no-store"
    return records.list_trips(db, service_date=service_date, status=status)


@router.post("/trips", response_model=TripOut, status_code=201)
def create_trip(
    body: TripIn, admin: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> TripOut:
    try:
        return records.create_trip(db, admin, body)
    except DutyRecordError as exc:
        raise _fail(exc) from None


@router.post("/trips/{trip_id}/approve", response_model=TripOut)
def approve_trip(
    trip_id: RecordId, admin: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> TripOut:
    try:
        return records.approve_trip(db, admin, trip_id)
    except DutyRecordError as exc:
        raise _fail(exc) from None


@router.post("/trips/{trip_id}/publish", response_model=TripOut)
def publish_trip(
    trip_id: RecordId, admin: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> TripOut:
    try:
        return records.publish_trip(db, admin, trip_id)
    except DutyRecordError as exc:
        raise _fail(exc) from None


@router.post("/owner-assignments", response_model=OwnerAssignmentOut, status_code=201)
def create_owner_assignment(
    body: OwnerAssignmentIn, admin: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> OwnerAssignmentOut:
    try:
        return records.create_owner_assignment(db, admin, body)
    except DutyRecordError as exc:
        raise _fail(exc) from None


@router.post("/owner-assignments/{assignment_id}/approve", response_model=OwnerAssignmentOut)
def approve_owner_assignment(
    assignment_id: RecordId, admin: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> OwnerAssignmentOut:
    try:
        return records.approve_owner_assignment(db, admin, assignment_id)
    except DutyRecordError as exc:
        raise _fail(exc) from None


@router.post("/owner-assignments/{assignment_id}/publish", response_model=OwnerAssignmentOut)
def publish_owner_assignment(
    assignment_id: RecordId, admin: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> OwnerAssignmentOut:
    try:
        return records.publish_owner_assignment(db, admin, assignment_id)
    except DutyRecordError as exc:
        raise _fail(exc) from None
