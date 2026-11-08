"""Password hashing, JWT access tokens and refresh-token helpers."""

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import settings

_hasher = PasswordHasher()  # argon2id with the library's recommended parameters

# Verified against when the account does not exist, so a wrong login name and a
# wrong password take about the same time.
_DUMMY_HASH = _hasher.hash("sprpta-timing-equaliser")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


# ---------------------------------------------------------------- refresh tokens


def new_refresh_token() -> tuple[str, str]:
    """Return (raw token for the cookie, SHA-256 hash for the database)."""
    raw = secrets.token_urlsafe(48)
    return raw, hash_token(raw)


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------- access tokens


@dataclass(frozen=True)
class AccessClaims:
    subject: int  # user id or complainant account id
    kind: str  # "staff" or "cp"
    role: str
    area_id: int | None
    session_id: int


def create_access_token(claims: AccessClaims, *, expires_in: timedelta | None = None) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(claims.subject),
        "typ": claims.kind,
        "role": claims.role,
        "area_id": claims.area_id,
        "sid": claims.session_id,
        "jti": secrets.token_hex(8),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + (expires_in or timedelta(minutes=settings.access_token_minutes)),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, *, verify_exp: bool = True) -> AccessClaims:
    """Verify signature, issuer, audience and (optionally) expiry.

    Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError. The algorithm is
    pinned, so tokens signed with "none" or another algorithm are rejected.
    """
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        options={
            "require": ["exp", "iat", "sub", "sid", "typ", "role"],
            "verify_exp": verify_exp,
        },
    )
    try:
        return AccessClaims(
            subject=int(payload["sub"]),
            kind=str(payload["typ"]),
            role=str(payload["role"]),
            area_id=payload.get("area_id"),
            session_id=int(payload["sid"]),
        )
    except (TypeError, ValueError) as exc:
        raise jwt.InvalidTokenError("malformed claims") from exc
