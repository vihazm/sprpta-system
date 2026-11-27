"""Complainant sign-up and password reset, both with a one-time code (UC-CP-01, UC-CP-02).

Sign-up: the person gives a name, an email or phone number and a password. A six
digit code goes to that email or phone; once it is entered the account is
verified and signed in. Until then the account cannot log in.

Password reset: a verified account asks for a code, then sends it back with a
new password. Every session of the account is ended.

Staff accounts are managed by the System Administrator, so a staff email or
phone number is told so (check_not_staff) instead of getting a code or a new
account. This does show which addresses belong to staff; every request here is
counted per IP address, so they cannot be guessed in bulk.

Codes are stored only as a keyed hash, expire after a few minutes, allow a few
wrong guesses and can be asked for again after a short wait. The code goes out
through the messaging service, with the wording of the Verification code template
(printed in the backend terminal until SMS and email are connected).
"""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.enums import MessageChannel
from app.core.identifiers import normalise_identifier
from app.core.security import hash_password
from app.models import AuthSession, ComplainantAccount, OtpCode, User
from app.services import auth_service, messaging_service
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


STAFF_ACCOUNT = (
    "This email or number belongs to a staff account. Staff accounts and passwords are managed by the "
    "System Administrator, so please contact them."
)


def _invalid_code() -> SignupError:
    return SignupError(400, "invalid_code", "That code is not correct or has expired. Check it or ask for a new one.")


# ---------------------------------------------------------------- codes


def _hash_code(account_id: int, code: str) -> str:
    key = settings.jwt_secret.encode()
    return hmac.new(key, f"{account_id}:{code}".encode(), hashlib.sha256).hexdigest()


def _deliver(
    db: Session, account: ComplainantAccount, channel: MessageChannel, recipient: str, code: str, purpose: str
) -> None:
    """Send the code through the messaging service, which logs it without the code itself."""
    error = messaging_service.send_code(db, account.id, channel, recipient, code, f"{purpose} code")
    if error:
        db.commit()
        raise SignupError(503, "code_not_sent", "We could not send a code right now. Please try again later.")


def _issue_code(db: Session, account: ComplainantAccount, purpose: str = "sign-up") -> int:
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
    _deliver(db, account, channel, recipient, code, purpose)
    db.commit()
    return settings.otp_resend_seconds


def _latest_code(db: Session, account_id: int) -> OtpCode | None:
    return db.scalar(
        select(OtpCode)
        .where(OtpCode.complainant_account_id == account_id)
        .order_by(OtpCode.id.desc())
        .limit(1)
    )


def _wait_before_resend(db: Session, account: ComplainantAccount) -> int:
    """Seconds before another code may be sent to this account (0 when it may be sent now)."""
    last = _latest_code(db, account.id)
    if last is None:
        return 0
    return max(0, settings.otp_resend_seconds - int((_now() - last.created_at).total_seconds()))


def _use_code(db: Session, account: ComplainantAccount, code: str) -> None:
    """Accept the account's latest code once, or count a wrong guess and refuse."""
    otp = _latest_code(db, account.id)
    if otp is None or otp.consumed_at is not None or otp.expires_at <= _now():
        raise _invalid_code()
    if otp.attempts >= settings.otp_max_attempts:
        raise SignupError(429, "too_many_codes", "Too many wrong codes. Ask for a new code.")
    if not hmac.compare_digest(otp.code_hash, _hash_code(account.id, code)):
        otp.attempts += 1
        db.commit()
        raise _invalid_code()
    otp.consumed_at = _now()


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


def _staff_login(db: Session, value: str) -> bool:
    return db.scalar(select(User.id).where(User.login == value)) is not None


def check_not_staff(db: Session, identifier: str) -> None:
    """Refuse a staff email or phone number: staff cannot sign up or reset their password here.

    Anything that is not a valid email or mobile number is left for the next page to point out.
    """
    parsed = normalise_identifier(identifier)
    if parsed is not None and _staff_login(db, parsed[1]):
        raise SignupError(409, "staff_account", STAFF_ACCOUNT)


def sign_up(db: Session, name: str, identifier: str, password: str) -> tuple[str, int]:
    """Create the account (not yet usable) and send its code. Returns (channel, resend wait in seconds)."""
    check_not_staff(db, identifier)
    kind, value = _parse(identifier)
    column = ComplainantAccount.email if kind == "email" else ComplainantAccount.phone
    existing = db.scalar(select(ComplainantAccount).where(column == value).with_for_update())

    if existing is not None and (existing.verified_at or not existing.is_active):
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
    wait = _wait_before_resend(db, account)
    if wait:
        raise SignupError(429, "resend_too_soon", f"Please wait {wait} seconds before asking for a new code.", wait)
    return _issue_code(db, account)


def verify_code(db: Session, identifier: str, code: str, ip: str | None, user_agent: str | None) -> IssuedTokens:
    """Check the code, activate the account and sign it in."""
    kind, value = _parse(identifier)
    account = _pending_account(db, kind, value)
    if account is None:
        raise _invalid_code()
    _use_code(db, account, code)
    account.verified_at = _now()
    return auth_service.start_session(db, account, ip, user_agent)


# ---------------------------------------------------------------- forgotten password


def _verified_account(db: Session, kind: str, value: str) -> ComplainantAccount | None:
    """The verified, active account with this email or phone, locked for this request."""
    column = ComplainantAccount.email if kind == "email" else ComplainantAccount.phone
    account = db.scalar(select(ComplainantAccount).where(column == value).with_for_update())
    if account is None or account.verified_at is None or not account.is_active:
        return None
    return account


def request_reset(db: Session, identifier: str) -> tuple[str, int]:
    """Send a reset code. Returns (channel, resend wait in seconds).

    The answer is the same whether or not a complainant account exists, so nobody can use this to find out who is
    registered. A staff address is refused. Asking again too soon sends nothing and only returns the time left.
    """
    check_not_staff(db, identifier)
    kind, value = _parse(identifier)
    channel = "email" if kind == "email" else "sms"
    account = _verified_account(db, kind, value)
    if account is None:
        return channel, settings.otp_resend_seconds
    wait = _wait_before_resend(db, account)
    return channel, wait or _issue_code(db, account, "password reset")


def reset_password(db: Session, identifier: str, code: str, password: str) -> None:
    """Check the code and set the new password. Every session of the account ends and any lock is lifted."""
    kind, value = _parse(identifier)
    account = _verified_account(db, kind, value)
    if account is None:
        raise _invalid_code()
    _use_code(db, account, code)
    account.password_hash = hash_password(password)
    account.failed_login_count = 0
    account.locked_until = None
    db.execute(
        update(AuthSession)
        .where(AuthSession.account_id == account.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=_now(), revoke_reason="password_reset")
    )
    db.commit()
