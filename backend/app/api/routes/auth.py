"""Authentication endpoints: /api/auth/login, /refresh, /logout, /me."""

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import (
    ACCESS_COOKIE,
    REFRESH_COOKIE,
    client_ip,
    error,
    get_current_principal,
)
from app.core.config import settings
from app.core.security import decode_access_token, hash_token
from app.db.session import get_db
from app.services import auth_service
from app.models import Area
from app.services.auth_service import AuthFailure, IssuedTokens, Principal

router = APIRouter(prefix="/api/auth", tags=["auth"])

REFRESH_PATH = "/api/auth"  # the refresh cookie is only ever sent to auth endpoints


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class UserOut(BaseModel):
    id: int
    name: str
    role: str
    area_id: int | None
    area_name: str | None
    kind: str


class SessionOut(BaseModel):
    user: UserOut
    redirect_to: str


def _session_out(p: Principal, db: Session) -> SessionOut:
    area = db.get(Area, p.area_id) if p.area_id else None
    return SessionOut(
        user=UserOut(
            id=p.id,
            name=p.name,
            role=p.role,
            area_id=p.area_id,
            area_name=area.name if area else None,
            kind=p.kind,
        ),
        redirect_to=p.landing_path,
    )


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


def _set_cookies(response: Response, issued: IssuedTokens) -> None:
    common = {"httponly": True, "samesite": "lax", "secure": settings.secure_cookies}
    response.set_cookie(
        ACCESS_COOKIE,
        issued.access_token,
        max_age=settings.access_token_minutes * 60,
        path="/",
        **common,
    )
    if issued.refresh_token is not None:
        response.set_cookie(
            REFRESH_COOKIE,
            issued.refresh_token,
            max_age=issued.refresh_max_age,
            path=REFRESH_PATH,
            **common,
        )


def _clear_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)


def _fail(exc: AuthFailure) -> HTTPException:
    http = error(exc.status, exc.code, exc.message)
    if exc.retry_after:
        http.detail["retry_after"] = exc.retry_after
        http.headers = {"Retry-After": str(exc.retry_after)}
    return http


@router.post("/login", response_model=SessionOut)
def login(
    body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)
) -> SessionOut:
    _no_store(response)
    try:
        issued = auth_service.login(
            db, body.identifier, body.password, client_ip(request), request.headers.get("user-agent")
        )
    except AuthFailure as exc:
        raise _fail(exc) from None
    _set_cookies(response, issued)
    return _session_out(issued.principal, db)


@router.post("/refresh", response_model=SessionOut)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)) -> SessionOut:
    _no_store(response)
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise error(401, "session_expired", "Your session has ended. Please sign in again.")
    try:
        issued = auth_service.refresh(db, token, client_ip(request))
    except AuthFailure as exc:
        raise _fail(exc) from None
    _set_cookies(response, issued)
    return _session_out(issued.principal, db)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> dict[str, bool]:
    """End this browser's session. Always succeeds, even if already signed out."""
    _no_store(response)
    session_id = None
    access = request.cookies.get(ACCESS_COOKIE)
    if access:
        try:
            # An expired token still tells us which session to end.
            session_id = decode_access_token(access, verify_exp=False).session_id
        except jwt.InvalidTokenError:
            session_id = None
    refresh_cookie = request.cookies.get(REFRESH_COOKIE)
    digest = hash_token(refresh_cookie) if refresh_cookie else None
    auth_service.logout(db, session_id, digest, client_ip(request))
    _clear_cookies(response)
    return {"ok": True}


@router.get("/me", response_model=SessionOut)
def me(
    response: Response,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> SessionOut:
    _no_store(response)
    return _session_out(principal, db)
