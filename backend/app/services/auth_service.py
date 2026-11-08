"""Login, refresh, logout and session checks (UC-C01, UC-C02).

Design (see the login plan):
- a short-lived access JWT plus a server-side session row (`auth_sessions`)
  holding a rotating, hashed refresh token;
- every request re-checks the session row and the account, so logout and
  deactivation take effect immediately;
- lockout after repeated failures, a per-IP failure limiter, and the same
  generic error for "no such account" and "wrong password".
"""

import ipaddress
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.identifiers import normalise_identifier
from app.core.rate_limit import login_failures
from app.core.roles import COMPLAINANT_ROLE, landing_path
from app.core.security import (
    AccessClaims,
    create_access_token,
    hash_token,
    new_refresh_token,
    password_needs_rehash,
    hash_password,
    verify_password,
)
from app.models import AuthSession, ComplainantAccount, UsageLog, User

Account = User | ComplainantAccount


class AuthFailure(Exception):
    """A login/session problem that maps to a clean HTTP error."""

    def __init__(
        self, status: int, code: str, message: str, retry_after: int | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.retry_after = retry_after


def _invalid_credentials() -> AuthFailure:
    return AuthFailure(401, "invalid_credentials", "Incorrect email, phone number or password.")


def _session_expired() -> AuthFailure:
    return AuthFailure(401, "session_expired", "Your session has ended. Please sign in again.")


def _locked(seconds: int) -> AuthFailure:
    minutes = max(1, -(-seconds // 60))
    unit = "minute" if minutes == 1 else "minutes"
    return AuthFailure(
        423,
        "account_locked",
        f"Too many failed attempts. Try again in {minutes} {unit}.",
        retry_after=seconds,
    )


@dataclass(frozen=True)
class Principal:
    """The signed-in person, as loaded from the database on each request."""

    kind: str  # "staff" or "cp"
    id: int
    role: str  # l1, l2, l3, admin, implementing_staff, cp
    name: str
    area_id: int | None
    session_id: int

    @property
    def landing_path(self) -> str:
        return landing_path(self.role)


@dataclass(frozen=True)
class IssuedTokens:
    principal: Principal
    access_token: str
    refresh_token: str | None  # None when only the access token was renewed
    refresh_max_age: int  # seconds the refresh cookie should live


def _now() -> datetime:
    return datetime.now(UTC)


def _clean_ip(ip: str | None) -> str | None:
    try:
        return str(ipaddress.ip_address(ip)) if ip else None
    except ValueError:
        return None


def _principal_for(account: Account, session_id: int) -> Principal:
    if isinstance(account, User):
        return Principal("staff", account.id, account.role.value, account.full_name,
                         account.area_id, session_id)
    name = account.display_name or account.email or account.phone or "Complainant"
    return Principal("cp", account.id, COMPLAINANT_ROLE, name, None, session_id)


def _log(db: Session, event: str, account: Account | None, ip: str | None, resource: str) -> None:
    db.add(
        UsageLog(
            user_id=account.id if isinstance(account, User) else None,
            account_id=account.id if isinstance(account, ComplainantAccount) else None,
            event_type=event,
            resource=resource,
            ip_address=_clean_ip(ip),
        )
    )


def _find_account(db: Session, kind: str, value: str) -> Account | None:
    """Staff first, then complainants (DB doc 2.2)."""
    user = db.scalar(select(User).where(User.login == value).with_for_update())
    if user is not None:
        return user
    column = ComplainantAccount.email if kind == "email" else ComplainantAccount.phone
    return db.scalar(select(ComplainantAccount).where(column == value).with_for_update())


def _is_usable(account: Account | None) -> bool:
    if account is None or not account.is_active:
        return False
    return not (isinstance(account, ComplainantAccount) and account.verified_at is None)


def _issue(db: Session, account: Account, sess: AuthSession, refresh: str | None) -> IssuedTokens:
    principal = _principal_for(account, sess.id)
    claims = AccessClaims(principal.id, principal.kind, principal.role, principal.area_id, sess.id)
    remaining = int((sess.idle_expires_at - _now()).total_seconds())
    return IssuedTokens(principal, create_access_token(claims), refresh, max(remaining, 0))


def _revoke(db: Session, sess: AuthSession, reason: str) -> None:
    if sess.revoked_at is None:
        sess.revoked_at = _now()
        sess.revoke_reason = reason


def _purge_old_sessions(db: Session, now: datetime) -> None:
    """Housekeeping on login: there is no background worker."""
    cutoff = now - timedelta(days=30)
    db.execute(
        delete(AuthSession).where(
            or_(AuthSession.idle_expires_at < cutoff, AuthSession.revoked_at < cutoff)
        )
    )


# ------------------------------------------------------------------ login


def login(
    db: Session, identifier: str, password: str, ip: str | None, user_agent: str | None
) -> IssuedTokens:
    ip_key = ip or "unknown"
    wait = login_failures.retry_after(ip_key)
    if wait:
        raise AuthFailure(
            429, "too_many_attempts", "Too many failed attempts. Please wait and try again.", wait
        )

    parsed = normalise_identifier(identifier)
    account = _find_account(db, *parsed) if parsed else None
    now = _now()

    if account is not None and account.locked_until and account.locked_until > now:
        _log(db, "login_failed", account, ip, "POST /api/auth/login (locked)")
        db.commit()
        raise _locked(int((account.locked_until - now).total_seconds()) + 1)

    if not verify_password(password, account.password_hash if account else None):
        login_failures.record_failure(ip_key)
        just_locked = False
        if account is not None:
            account.failed_login_count += 1
            if account.failed_login_count >= settings.max_failed_logins:
                account.locked_until = now + timedelta(minutes=settings.lockout_minutes)
                account.failed_login_count = 0
                just_locked = True
        _log(db, "login_failed", account, ip, "POST /api/auth/login")
        db.commit()
        if just_locked:
            raise _locked(settings.lockout_minutes * 60)
        raise _invalid_credentials()

    # Correct password from here on, so it is safe to explain the account state.
    assert account is not None
    if not account.is_active:
        _log(db, "login_failed", account, ip, "POST /api/auth/login (deactivated)")
        db.commit()
        raise AuthFailure(
            403, "account_disabled", "This account has been deactivated. Contact the SPRPTA office."
        )
    if isinstance(account, ComplainantAccount) and account.verified_at is None:
        _log(db, "login_failed", account, ip, "POST /api/auth/login (unverified)")
        db.commit()
        raise AuthFailure(403, "account_not_verified", "This account has not been verified yet.")

    account.failed_login_count = 0
    account.locked_until = None
    account.last_login_at = now
    if password_needs_rehash(account.password_hash):
        account.password_hash = hash_password(password)

    raw, hashed = new_refresh_token()
    absolute = now + timedelta(hours=settings.session_absolute_hours)
    sess = AuthSession(
        user_id=account.id if isinstance(account, User) else None,
        account_id=account.id if isinstance(account, ComplainantAccount) else None,
        refresh_token_hash=hashed,
        last_used_at=now,
        idle_expires_at=min(now + timedelta(minutes=settings.session_idle_minutes), absolute),
        absolute_expires_at=absolute,
        ip_address=_clean_ip(ip),
        user_agent=(user_agent or "")[:300] or None,
    )
    db.add(sess)
    db.flush()
    _log(db, "login", account, ip, "POST /api/auth/login")
    _purge_old_sessions(db, now)
    issued = _issue(db, account, sess, raw)
    db.commit()
    return issued


# ------------------------------------------------------------------ refresh


def _account_for_session(db: Session, sess: AuthSession) -> Account | None:
    if sess.user_id is not None:
        return db.get(User, sess.user_id)
    return db.get(ComplainantAccount, sess.account_id)


def refresh(db: Session, raw_token: str, ip: str | None) -> IssuedTokens:
    """Swap a refresh token for a new access token (and a new refresh token)."""
    digest = hash_token(raw_token)
    now = _now()
    sess = db.scalar(
        select(AuthSession).where(AuthSession.refresh_token_hash == digest).with_for_update()
    )

    if sess is not None:
        if sess.revoked_at is not None:
            raise _session_expired()
        if now >= sess.idle_expires_at or now >= sess.absolute_expires_at:
            _revoke(db, sess, "expired")
            db.commit()
            raise _session_expired()
        account = _account_for_session(db, sess)
        if not _is_usable(account):
            _revoke(db, sess, "deactivated")
            db.commit()
            raise _session_expired()

        new_raw, new_hash = new_refresh_token()
        sess.previous_token_hash = sess.refresh_token_hash
        sess.rotated_at = now
        sess.refresh_token_hash = new_hash
        sess.last_used_at = now
        sess.idle_expires_at = min(
            now + timedelta(minutes=settings.session_idle_minutes), sess.absolute_expires_at
        )
        issued = _issue(db, account, sess, new_raw)
        db.commit()
        return issued

    # Not the current token: maybe the one just replaced by a parallel request.
    previous = db.scalar(
        select(AuthSession).where(AuthSession.previous_token_hash == digest).with_for_update()
    )
    if previous is not None and previous.revoked_at is None:
        within_grace = (
            previous.rotated_at is not None
            and now - previous.rotated_at <= timedelta(seconds=settings.refresh_grace_seconds)
        )
        account = _account_for_session(db, previous)
        if within_grace and now < previous.absolute_expires_at and _is_usable(account):
            # Renew only the access token; the winning request already set the
            # new refresh cookie.
            return _issue(db, account, previous, None)
        # An old token came back after the grace period: treat it as stolen.
        _revoke(db, previous, "reuse_detected")
        db.commit()
    raise _session_expired()


# ------------------------------------------------------------------ logout


def logout(db: Session, session_id: int | None, refresh_digest: str | None, ip: str | None) -> None:
    """End one session (this browser). Safe to call twice."""
    sess = None
    if session_id is not None:
        sess = db.get(AuthSession, session_id)
    if sess is None and refresh_digest:
        sess = db.scalar(
            select(AuthSession).where(AuthSession.refresh_token_hash == refresh_digest)
        )
    if sess is None or sess.revoked_at is not None:
        return
    _revoke(db, sess, "logout")
    account = _account_for_session(db, sess)
    _log(db, "logout", account, ip, "POST /api/auth/logout")
    db.commit()


# ------------------------------------------------------------------ per request


def principal_for_claims(db: Session, claims: AccessClaims) -> Principal:
    """Confirm the session is live and the account is still allowed in.

    The role comes from the database, not the token, so a role change applies
    on the very next request.
    """
    sess = db.get(AuthSession, claims.session_id)
    now = _now()
    if sess is None or sess.revoked_at is not None or now >= sess.absolute_expires_at:
        raise _session_expired()
    owner_id = sess.user_id if claims.kind == "staff" else sess.account_id
    if owner_id != claims.subject:
        raise _session_expired()
    account = _account_for_session(db, sess)
    if not _is_usable(account):
        raise _session_expired()
    return _principal_for(account, sess.id)
