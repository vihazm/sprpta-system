"""Staff accounts: /api/admin/users (admin only)."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy.orm import Session

from app.api.deps import error, get_current_principal, require_roles
from app.core.roles import UserRole
from app.db.session import get_db
from app.schemas.admin_users import MAX_ID, NewUser, NoNul, UserChanges, UserList, UserOut, UsersSummary
from app.services import admin_users_service as users
from app.services.admin_users_service import UserError
from app.services.auth_service import Principal

router = APIRouter(prefix="/api/admin/users", tags=["admin"], dependencies=[Depends(require_roles("admin"))])


UserId = Annotated[int, Path(ge=1, le=MAX_ID)]


def _fail(exc: UserError) -> HTTPException:
    return error(exc.status, exc.code, exc.message)


@router.get("/summary", response_model=UsersSummary)
def summary(response: Response, db: Session = Depends(get_db)) -> UsersSummary:
    response.headers["Cache-Control"] = "no-store"
    return users.summary(db)


@router.get("", response_model=UserList)
def list_users(
    response: Response,
    search: Annotated[str, NoNul, Query(max_length=100)] = "",
    status: Literal["active", "inactive", "locked"] | None = None,
    role: UserRole | None = None,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
) -> UserList:
    response.headers["Cache-Control"] = "no-store"
    return users.list_users(db, search=search, status=status, role=role, page=page)


@router.post("", response_model=UserOut, status_code=201)
def create_user(
    body: NewUser, admin: Principal = Depends(get_current_principal), db: Session = Depends(get_db)
) -> UserOut:
    try:
        return users.create_user(db, admin.id, body)
    except UserError as exc:
        raise _fail(exc) from None


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: UserId,
    body: UserChanges,
    admin: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> UserOut:
    try:
        return users.update_user(db, admin.id, user_id, body)
    except UserError as exc:
        raise _fail(exc) from None


@router.post("/{user_id}/unlock", response_model=UserOut)
def unlock_user(user_id: UserId,db: Session = Depends(get_db)) -> UserOut:
    try:
        return users.unlock_user(db, user_id)
    except UserError as exc:
        raise _fail(exc) from None
