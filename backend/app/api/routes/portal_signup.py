"""Complainant sign-up: /api/auth/signup, /verify-otp and /resend-otp (public, before any session exists)."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import client_ip, error
from app.api.routes.auth import SessionOut, _no_store, _session_out, _set_cookies
from app.core.rate_limit import signup_requests
from app.db.session import get_db
from app.schemas.portal import CodeSent, ResendRequest, SignUpRequest, VerifyRequest
from app.services import portal_signup_service as signup
from app.services.portal_signup_service import SignupError

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _fail(exc: SignupError) -> HTTPException:
    http = error(exc.status, exc.code, exc.message)
    if exc.retry_after:
        http.detail["retry_after"] = exc.retry_after
        http.headers = {"Retry-After": str(exc.retry_after)}
    return http


def _limit(request: Request) -> None:
    """Count this request against the caller's IP and refuse when it has asked too often."""
    ip = client_ip(request) or "unknown"
    wait = signup_requests.retry_after(ip)
    if wait:
        raise _fail(SignupError(429, "too_many_attempts", "Too many requests. Please wait and try again.", wait))
    signup_requests.record_failure(ip)


@router.post("/signup", response_model=CodeSent)
def sign_up(body: SignUpRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> CodeSent:
    _no_store(response)
    _limit(request)
    try:
        channel, wait = signup.sign_up(db, body.name, body.identifier, body.password)
    except SignupError as exc:
        raise _fail(exc) from None
    return CodeSent(channel=channel, resend_after=wait)


@router.post("/resend-otp", response_model=CodeSent)
def resend(body: ResendRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> CodeSent:
    _no_store(response)
    _limit(request)
    try:
        wait = signup.resend_code(db, body.identifier)
    except SignupError as exc:
        raise _fail(exc) from None
    channel = "email" if "@" in body.identifier else "sms"
    return CodeSent(channel=channel, resend_after=wait)


@router.post("/verify-otp", response_model=SessionOut)
def verify(body: VerifyRequest, request: Request, response: Response, db: Session = Depends(get_db)) -> SessionOut:
    _no_store(response)
    _limit(request)
    try:
        issued = signup.verify_code(db, body.identifier, body.code, client_ip(request), request.headers.get("user-agent"))
    except SignupError as exc:
        raise _fail(exc) from None
    _set_cookies(response, issued)
    return _session_out(issued.principal, db)
