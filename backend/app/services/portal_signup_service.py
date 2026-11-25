"""Complainant sign-up with a one-time code (UC-CP-01).

The person gives a name, an email or phone number and a password. A six digit
code goes to that email or phone; once it is entered the account is verified
and signed in. Until then the account cannot log in.

Codes are stored only as a keyed hash, expire after a few minutes, allow a few
wrong guesses and can be asked for again after a short wait. Delivery is
"console" for SMS: the code is printed in the backend terminal. Email goes out through SMTP
when SMTP_* is set in backend/.env; otherwise it is printed too. Printing is only allowed in
development; anywhere else no code is sent until a provider is connected.
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import MessageChannel, MessageState, MessageType
from app.core.identifiers import normalise_identifier
from app.core.security import hash_password
from app.models import ComplainantAccount, OtpCode, OutboundMessage, User
from app.services import auth_service, email_sender
from app.services.auth_service import IssuedTokens


class SignupError(Exception):
    """A rule the request breaks; the route turns it into a clean HTTP error."""

    def __init__(self, status: int, code: str, message: str, retry_after: int | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.retry_after = retry_after


def _now() -> datetime:
    return datetime.now(UTC)


def _invalid_code() -> SignupError:
    return SignupError(400, "invalid_code", "That code is not correct or has expired. Check it or ask for a new one.")


# ---------------------------------------------------------------- codes


def _hash_code(account_id: int, code: str) -> str:
    key = settings.jwt_secret.encode()
    return hmac.new(key, f"{account_id}:{code}".encode(), hashlib.sha256).hexdigest()


def _email_body(code: str) -> tuple[str, str]:
    """The plain text and the HTML of the sign-up email."""
    minutes = settings.otp_minutes
    text = "\n\n".join(
        [
            f"Your SPRPTA verification code is {code}.",
            f"It works for {minutes} minutes. If you did not ask for it, you can ignore this email.",
            "Southern Provincial Road Passenger Transport Authority",
        ]
    )
    html = (
        '<div style="font-family:Arial,sans-serif;max-width:28rem;color:#16181d">'
        '<p style="margin:0 0 .5rem;font-size:.8rem;letter-spacing:.08em;color:#b3112f;font-weight:bold">SPRPTA</p>'
        '<p style="margin:0 0 1rem">Your verification code is</p>'
        f'<p style="margin:0 0 1rem;font-size:2rem;letter-spacing:.3rem;font-weight:bold">{code}</p>'
        f'<p style="margin:0 0 1rem;color:#5b6574">It works for {minutes} minutes. '
        "If you did not ask for it, you can ignore this email.</p>"
        '<p style="margin:0;color:#5b6574;font-size:.85rem">Southern Provincial Road Passenger Transport Authority</p>'
        "</div>"
    )
    return text, html


def _send(channel: MessageChannel, recipient: str, code: str) -> str | None:
    """Send the code. Returns None when it went out, or a short reason when it did not."""
    if channel is MessageChannel.EMAIL and settings.email_configured:
        text, html = _email_body(code)
        try:
            email_sender.send_email(recipient, "Your SPRPTA verification code", text, html)
        except email_sender.EmailError as exc:
            return str(exc)
        return None
    if settings.is_development:
        # Console mode: the code appears in the backend terminal (used for SMS, and for email until SMTP is set up).
        if channel is MessageChannel.EMAIL:
            print("[SPRPTA] No email was sent: SMTP_HOST and SMTP_USER are not set in backend/.env.", flush=True)
        print(f"[SPRPTA sign-up code] {recipient}: {code}", flush=True)
        return None
    return "No SMS or email provider is connected."


def _deliver(db: Session, account: ComplainantAccount, channel: MessageChannel, recipient: str, code: str) -> None:
    """Send the code and log the attempt. The log never holds the code itself."""
    error = _send(channel, recipient, code)
    db.add(
        OutboundMessage(
            complainant_account_id=account.id,
            message_type=MessageType.OTP,
            channel=channel,
            recipient=recipient,
            body="Your SPRPTA verification code is ******.",
            state=MessageState.FAILED if error else MessageState.SENT,
            error_detail=error,
        )
    )
    if error:
        db.commit()
        raise SignupError(503, "code_not_sent", "We could not send a code right now. Please try again later.")


def _issue_code(db: Session, account: ComplainantAccount) -> int:
    """Replace any unused code with a new one and send it. Returns the seconds before another may be asked for."""
    now = _now()
    channel = MessageChannel.EMAIL if account.email else MessageChannel.SMS
    recipient = account.email or account.phone
    for old in db.scalars(
        select(OtpCode).where(OtpCode.complainant_account_id == account.id, OtpCode.consumed_at.is_(None))
    ):
        old.consumed_at = now
    code = f"{secrets.randbelow(10**6):06d}"
    db.add(
        OtpCode(
            complainant_account_id=account.id,
            channel=channel,
            code_hash=_hash_code(account.id, code),
            expires_at=now + timedelta(minutes=settings.otp_minutes),
        )
    )
    _deliver(db, account, channel, recipient, code)
    db.commit()
    return settings.otp_resend_seconds


def _latest_code(db: Session, account_id: int) -> OtpCode | None:
    return db.scalar(
        select(OtpCode)
        .where(OtpCode.complainant_account_id == account_id)
        .order_by(OtpCode.id.desc())
        .limit(1)
    )


# ---------------------------------------------------------------- the three steps


def _parse(identifier: str) -> tuple[str, str]:
    parsed = normalise_identifier(identifier)
    if parsed is None:
        raise SignupError(422, "invalid_identifier", "Enter a valid email address or mobile number.")
    return parsed


def _pending_account(db: Session, kind: str, value: str) -> ComplainantAccount | None:
    """The sign-up that is waiting for its code, locked for this request."""
    column = ComplainantAccount.email if kind == "email" else ComplainantAccount.phone
    account = db.scalar(select(ComplainantAccount).where(column == value).with_for_update())
    if account is None or account.verified_at is not None or not account.is_active:
        return None
    return account


def sign_up(db: Session, name: str, identifier: str, password: str) -> tuple[str, int]:
    """Create the account (not yet usable) and send its code. Returns (channel, resend wait in seconds)."""
    kind, value = _parse(identifier)
    column = ComplainantAccount.email if kind == "email" else ComplainantAccount.phone
    taken_by_staff = db.scalar(select(User.id).where(User.login == value))
    existing = db.scalar(select(ComplainantAccount).where(column == value).with_for_update())

    if taken_by_staff is not None or (existing is not None and (existing.verified_at or not existing.is_active)):
        label = "email address" if kind == "email" else "mobile number"
        raise SignupError(409, "already_registered", f"That {label} is already registered. Try signing in instead.")

    if existing is None:
        existing = ComplainantAccount(**{kind: value})
        db.add(existing)
    # A sign-up that was never finished is simply started again with the new name and password.
    existing.display_name = name.strip()
    existing.password_hash = hash_password(password)
    db.flush()
    wait = _issue_code(db, existing)
    return ("email" if kind == "email" else "sms"), wait


def resend_code(db: Session, identifier: str) -> int:
    """Send a fresh code to an unfinished sign-up. Returns the seconds before another may be asked for."""
    kind, value = _parse(identifier)
    account = _pending_account(db, kind, value)
    if account is None:
        raise SignupError(404, "no_pending_signup", "There is no sign-up waiting for a code. Please start again.")
    last = _latest_code(db, account.id)
    if last is not None:
        wait = settings.otp_resend_seconds - int((_now() - last.created_at).total_seconds())
        if wait > 0:
            raise SignupError(429, "resend_too_soon", f"Please wait {wait} seconds before asking for a new code.", wait)
    return _issue_code(db, account)


def verify_code(db: Session, identifier: str, code: str, ip: str | None, user_agent: str | None) -> IssuedTokens:
    """Check the code, activate the account and sign it in."""
    kind, value = _parse(identifier)
    account = _pending_account(db, kind, value)
    if account is None:
        raise _invalid_code()
    otp = _latest_code(db, account.id)
    now = _now()
    if otp is None or otp.consumed_at is not None or otp.expires_at <= now:
        raise _invalid_code()
    if otp.attempts >= settings.otp_max_attempts:
        raise SignupError(429, "too_many_codes", "Too many wrong codes. Ask for a new code.")

    if not hmac.compare_digest(otp.code_hash, _hash_code(account.id, code)):
        otp.attempts += 1
        db.commit()
        raise _invalid_code()

    otp.consumed_at = now
    account.verified_at = now
    return auth_service.start_session(db, account, ip, user_agent)
