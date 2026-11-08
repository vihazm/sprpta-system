"""CSRF guard for cookie-authenticated requests.

Cookies are SameSite=Lax, which already stops cross-site POSTs in modern
browsers. This adds a second check: a state-changing request from a browser
must come from one of our own origins.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


async def csrf_guard(request: Request, call_next):
    if request.method not in SAFE_METHODS:
        origin = request.headers.get("origin")
        if origin is not None:
            blocked = origin not in settings.allowed_origins
        else:
            # Older/non-browser clients send no Origin; reject only browsers
            # that explicitly say the request is cross-site.
            blocked = request.headers.get("sec-fetch-site") == "cross-site"
        if blocked:
            return JSONResponse(
                {"detail": {"code": "bad_origin", "message": "Request origin not allowed."}},
                status_code=403,
            )
    return await call_next(request)
