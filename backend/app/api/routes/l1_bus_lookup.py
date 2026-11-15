"""The Level 1 Bus & Permit Lookup: /api/l1/bus-lookup (office staff only). Reads published records only."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import error, require_roles
from app.db.session import get_db
from app.schemas.admin_users import MAX_ID, NoNul
from app.schemas.l1_bus_lookup import BusSearch, TripDetails
from app.services import bus_lookup_service
from app.services.complaint_intake_service import ComplaintError


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


router = APIRouter(
    prefix="/api/l1/bus-lookup",
    tags=["l1"],
    dependencies=[Depends(require_roles("l1")), Depends(_no_store)],
)


def _fail(exc: ComplaintError) -> HTTPException:
    return error(exc.status, exc.code, exc.message)


@router.get("/trips", response_model=BusSearch)
def search_trips(
    service_date: date,
    bus_number: Annotated[str, NoNul, Query(min_length=1, max_length=20)],
    db: Session = Depends(get_db),
) -> BusSearch:
    try:
        return bus_lookup_service.search_trips(db, service_date, bus_number)
    except ComplaintError as exc:
        raise _fail(exc) from None


@router.get("/trips/{trip_id}", response_model=TripDetails)
def trip_details(trip_id: Annotated[int, Path(ge=1, le=MAX_ID)], db: Session = Depends(get_db)) -> TripDetails:
    try:
        return bus_lookup_service.trip_details(db, trip_id)
    except ComplaintError as exc:
        raise _fail(exc) from None
