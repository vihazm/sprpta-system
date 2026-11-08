"""Shared FastAPI dependencies: who is calling, and are they allowed.

Teammates: protect a route with `Depends(require_roles("l2"))` (or
`Depends(get_current_principal)` for any signed-in user). `principal.area_id`
is set for L2 officers, for filtering by area.
"""

from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.services.auth_service import AuthFailure, Principal, principal_for_claims

ACCESS_COOKIE = "sprpta_at"
REFRESH_COOKIE = "sprpta_rt"


def error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def client_ip(request: Request) -> str | None:
    """The caller's IP. Behind the Next.js proxy the real client is the last
    entry of X-Forwarded-For (the proxy appends it)."""
    if settings.trust_forwarded_for:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else None


def get_current_principal(request: Request, db: Session = Depends(get_db)) -> Principal:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise error(401, "not_authenticated", "Please sign in.")
    try:
        claims = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise error(401, "token_expired", "Your access token has expired.") from None
    except jwt.InvalidTokenError:
        raise error(401, "invalid_token", "Your sign-in is not valid. Please sign in again.") from None
    try:
        return principal_for_claims(db, claims)
    except AuthFailure as exc:
        raise error(exc.status, exc.code, exc.message) from None


def require_roles(*roles: str) -> Callable[[Principal], Principal]:
    """Allow only the listed roles (l1, l2, l3, admin, implementing_staff, cp)."""

    def checker(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.role not in roles:
            raise error(403, "forbidden", "You do not have access to this resource.")
        return principal

    return checker
