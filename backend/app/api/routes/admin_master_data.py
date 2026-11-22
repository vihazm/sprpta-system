"""Master data: /api/admin/master-data (admin only)."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import error, get_current_principal, require_roles
from app.db.session import get_db
from app.schemas.admin_master_data import EntityCount, EntityKey, RecordBody, RecordList
from app.schemas.admin_users import MAX_ID, NoNul
from app.services import master_data_service as master_data
from app.services.auth_service import Principal
from app.services.master_data_service import MasterDataError

router = APIRouter(
    prefix="/api/admin/master-data", tags=["admin"], dependencies=[Depends(require_roles("admin"))]
)

RecordId = Annotated[int, Path(ge=1, le=MAX_ID)]


def _fail(exc: MasterDataError) -> HTTPException:
    return error(exc.status, exc.code, exc.message)


def _invalid(exc: ValidationError) -> RequestValidationError:
    # Reported like any other bad body, under body.values.
    return RequestValidationError([{**e, "loc": ("body", "values", *e["loc"])} for e in exc.errors(include_url=False)])


@router.get("", response_model=list[EntityCount])
def counts(response: Response, db: Session = Depends(get_db)) -> list[EntityCount]:
    response.headers["Cache-Control"] = "no-store"
    return master_data.counts(db)


@router.get("/{entity}", response_model=RecordList)
def list_records(
    entity: EntityKey,
    response: Response,
    search: Annotated[str, NoNul, Query(max_length=100)] = "",
    status: Literal["active", "inactive"] | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(master_data.PAGE_SIZE, ge=1, le=100),
    db: Session = Depends(get_db),
) -> RecordList:
    response.headers["Cache-Control"] = "no-store"
    return master_data.list_records(db, entity, search=search, status=status, page=page, page_size=page_size)


@router.post("/{entity}", status_code=201)
def create_record(
    entity: EntityKey,
    body: RecordBody,
    admin: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        return master_data.create_record(db, admin, entity, body.values)
    except ValidationError as exc:
        raise _invalid(exc) from None
    except MasterDataError as exc:
        raise _fail(exc) from None


@router.put("/{entity}/{record_id}")
def update_record(
    entity: EntityKey,
    record_id: RecordId,
    body: RecordBody,
    admin: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    try:
        return master_data.update_record(db, admin, entity, record_id, body.values, active=body.is_active)
    except ValidationError as exc:
        raise _invalid(exc) from None
    except MasterDataError as exc:
        raise _fail(exc) from None
