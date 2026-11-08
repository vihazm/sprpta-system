from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import APIRouter, Depends
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.deps import require_roles
from app.core.config import settings
from app.core.roles import UserRole
from app.core.security import AccessClaims, create_access_token
from app.main import app
from app.models import AuthSession, UsageLog, User
from tests.conftest import PASSWORD, make_complainant, make_user, sign_in

# A route that only L1 may call, to test role checks.
_probe = APIRouter()


@_probe.get("/api/_probe/l1")
def _l1_only(_=Depends(require_roles("l1"))):
    return {"ok": True}


app.include_router(_probe)


def cookie_header(client: TestClient, *names: str) -> str:
    return "; ".join(f"{n}={client.cookies.get(n)}" for n in names)


# ------------------------------------------------------------------ login


@pytest.mark.parametrize(
    "role,expected",
    [
        (UserRole.L1, "/l1/dashboard"),
        (UserRole.L2, "/l2/dashboard"),
        (UserRole.L3, "/l3/dashboard"),
        (UserRole.ADMIN, "/admin/dashboard"),
        (UserRole.IMPLEMENTING_STAFF, "/is/cases"),
    ],
)
def test_staff_login_redirects_by_role(client, db, galle, role, expected):
    make_user(db, "staff@sprpta.test", role, area_id=galle.id if role is UserRole.L2 else None)
    r = sign_in(client, "staff@sprpta.test")
    assert r.status_code == 200
    assert r.json()["redirect_to"] == expected
    assert r.json()["user"]["role"] == role.value


def test_complainant_login_goes_to_my_complaints(client, db):
    make_complainant(db, "client@sprpta.test")
    r = sign_in(client, "client@sprpta.test")
    assert r.status_code == 200
    assert r.json()["redirect_to"] == "/cp/complaints"
    assert r.json()["user"]["role"] == "cp"


def test_login_sets_httponly_cookies_and_returns_no_tokens(client, db):
    make_user(db, "a@sprpta.test", UserRole.L1)
    r = sign_in(client, "a@sprpta.test")
    cookies = r.headers.get_list("set-cookie")
    assert len(cookies) == 2
    assert all("HttpOnly" in c and "SameSite=lax" in c for c in cookies)
    assert any("sprpta_rt=" in c and "Path=/api/auth" in c for c in cookies)
    assert "token" not in r.text.lower()
    assert r.headers["cache-control"] == "no-store"


def test_login_matches_email_case_insensitively_and_phone_formats(client, db):
    make_user(db, "mixed@sprpta.test", UserRole.L1)
    make_user(db, "+94712345678", UserRole.L3)
    assert sign_in(client, "  MIXED@SPRPTA.TEST ").status_code == 200
    assert sign_in(client, "071 234 5678").json()["user"]["role"] == "l3"
    assert sign_in(client, "+94 71-234-5678").status_code == 200


def test_wrong_password_and_unknown_user_look_identical(client, db):
    make_user(db, "a@sprpta.test", UserRole.L1)
    bad_pw = sign_in(client, "a@sprpta.test", "nope")
    unknown = sign_in(client, "ghost@sprpta.test", "nope")
    not_an_id = sign_in(client, "plainname", "nope")
    assert bad_pw.status_code == unknown.status_code == not_an_id.status_code == 401
    assert bad_pw.json() == unknown.json() == not_an_id.json()
    assert bad_pw.json()["detail"]["code"] == "invalid_credentials"


def test_lockout_after_five_failures_then_unlocks(client, db):
    user = make_user(db, "a@sprpta.test", UserRole.L1)
    for _ in range(4):
        assert sign_in(client, "a@sprpta.test", "bad").status_code == 401
    fifth = sign_in(client, "a@sprpta.test", "bad")
    assert fifth.status_code == 423
    assert fifth.json()["detail"]["code"] == "account_locked"
    assert fifth.json()["detail"]["retry_after"] > 0
    # even the right password is refused while locked
    assert sign_in(client, "a@sprpta.test").status_code == 423

    db.expire_all()
    row = db.get(User, user.id)
    row.locked_until = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert sign_in(client, "a@sprpta.test").status_code == 200
    db.expire_all()
    assert db.get(User, user.id).failed_login_count == 0


def test_deactivated_and_unverified_accounts_cannot_log_in(client, db):
    make_user(db, "off@sprpta.test", UserRole.L1, is_active=False)
    make_complainant(db, "new@sprpta.test", verified_at=None)
    # the reason is only shared once the password is right
    assert sign_in(client, "off@sprpta.test", "wrong").json()["detail"]["code"] == "invalid_credentials"
    assert sign_in(client, "off@sprpta.test").json()["detail"]["code"] == "account_disabled"
    r = sign_in(client, "new@sprpta.test")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "account_not_verified"
    assert "sprpta_at" not in client.cookies


def test_ip_limiter_blocks_after_repeated_failures(client, db):
    make_user(db, "a@sprpta.test", UserRole.L1)
    for i in range(settings.ip_failure_limit):
        sign_in(client, f"nobody{i}@sprpta.test", "bad", **{"X-Forwarded-For": "203.0.113.9"})
    blocked = sign_in(client, "a@sprpta.test", PASSWORD, **{"X-Forwarded-For": "203.0.113.9"})
    assert blocked.status_code == 429
    assert "Retry-After" in blocked.headers
    # another address is unaffected
    other = sign_in(client, "a@sprpta.test", PASSWORD, **{"X-Forwarded-For": "198.51.100.4"})
    assert other.status_code == 200


def test_bad_origin_is_rejected(client, db):
    make_user(db, "a@sprpta.test", UserRole.L1)
    r = sign_in(client, "a@sprpta.test", **{"Origin": "https://evil.example"})
    assert r.status_code == 403 and r.json()["detail"]["code"] == "bad_origin"
    assert sign_in(client, "a@sprpta.test", **{"Origin": "http://localhost:3000"}).status_code == 200


# ------------------------------------------------------------------ /me and role checks


def test_me_requires_a_session(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401 and r.json()["detail"]["code"] == "not_authenticated"


def test_me_returns_the_signed_in_user(client, db, galle):
    make_user(db, "o@sprpta.test", UserRole.L2, area_id=galle.id)
    sign_in(client, "o@sprpta.test")
    body = client.get("/api/auth/me").json()
    assert body["user"]["role"] == "l2" and body["user"]["area_id"] == galle.id
    assert body["redirect_to"] == "/l2/dashboard"


def test_role_checks_are_enforced_by_the_backend(client, db):
    make_user(db, "l1@sprpta.test", UserRole.L1)
    make_user(db, "l3@sprpta.test", UserRole.L3)
    assert client.get("/api/_probe/l1").status_code == 401
    sign_in(client, "l3@sprpta.test")
    r = client.get("/api/_probe/l1")
    assert r.status_code == 403 and r.json()["detail"]["code"] == "forbidden"
    sign_in(client, "l1@sprpta.test")
    assert client.get("/api/_probe/l1").status_code == 200


def test_role_change_applies_immediately(client, db):
    user = make_user(db, "l1@sprpta.test", UserRole.L1)
    sign_in(client, "l1@sprpta.test")
    assert client.get("/api/_probe/l1").status_code == 200
    db.expire_all()
    db.get(User, user.id).role = UserRole.L3
    db.commit()
    assert client.get("/api/_probe/l1").status_code == 403


# ------------------------------------------------------------------ JWT checks


def _token(user_id=1, sid=1, **kw):
    return create_access_token(AccessClaims(user_id, "staff", "l1", None, sid), **kw)


def test_tampered_foreign_and_unsigned_tokens_are_rejected(client, db):
    user = make_user(db, "a@sprpta.test", UserRole.L1)
    sign_in(client, "a@sprpta.test")
    good = client.cookies.get("sprpta_at")

    header, payload, sig = good.split(".")
    forged_payload = jwt.utils.base64url_encode(
        b'{"sub":"999","typ":"staff","role":"admin","sid":1,"iat":1,"exp":9999999999,'
        b'"iss":"sprpta-api","aud":"sprpta-web"}'
    ).decode()
    unsigned = jwt.encode(
        {"sub": str(user.id), "typ": "staff", "role": "admin", "sid": 1,
         "iat": datetime.now(UTC), "exp": datetime.now(UTC) + timedelta(minutes=5),
         "iss": settings.jwt_issuer, "aud": settings.jwt_audience},
        key=None, algorithm="none",
    )
    wrong_key = jwt.encode(
        {"sub": str(user.id), "typ": "staff", "role": "admin", "sid": 1,
         "iat": datetime.now(UTC), "exp": datetime.now(UTC) + timedelta(minutes=5),
         "iss": settings.jwt_issuer, "aud": settings.jwt_audience},
        "another-secret-another-secret-another-secret", algorithm="HS256",
    )
    wrong_audience = jwt.encode(
        {"sub": str(user.id), "typ": "staff", "role": "l1", "sid": 1,
         "iat": datetime.now(UTC), "exp": datetime.now(UTC) + timedelta(minutes=5),
         "iss": settings.jwt_issuer, "aud": "someone-else"},
        settings.jwt_secret, algorithm="HS256",
    )
    for bad in (f"{header}.{forged_payload}.{sig}", unsigned, wrong_key, wrong_audience, "garbage"):
        r = TestClient(app).get("/api/auth/me", headers={"Cookie": f"sprpta_at={bad}"})
        assert r.status_code == 401 and r.json()["detail"]["code"] == "invalid_token", bad[:30]


def test_expired_access_token_is_reported_as_expired(client, db):
    user = make_user(db, "a@sprpta.test", UserRole.L1)
    sign_in(client, "a@sprpta.test")
    sid = db.scalar(select(AuthSession.id).where(AuthSession.user_id == user.id))
    old = _token(user.id, sid, expires_in=timedelta(seconds=-5))
    r = TestClient(app).get("/api/auth/me", headers={"Cookie": f"sprpta_at={old}"})
    assert r.status_code == 401 and r.json()["detail"]["code"] == "token_expired"


# ------------------------------------------------------------------ refresh


def test_refresh_rotates_the_refresh_token(client, db):
    make_user(db, "a@sprpta.test", UserRole.L1)
    sign_in(client, "a@sprpta.test")
    old_rt = client.cookies.get("sprpta_rt")
    r = client.post("/api/auth/refresh")
    assert r.status_code == 200
    assert client.cookies.get("sprpta_rt") != old_rt
    assert client.get("/api/auth/me").status_code == 200


def test_parallel_refresh_inside_grace_window_only_renews_access(client, db):
    make_user(db, "a@sprpta.test", UserRole.L1)
    sign_in(client, "a@sprpta.test")
    old_rt = client.cookies.get("sprpta_rt")
    client.post("/api/auth/refresh")  # the "winning" request rotates the token
    second = TestClient(app).post("/api/auth/refresh", headers={"Cookie": f"sprpta_rt={old_rt}"})
    assert second.status_code == 200
    names = [c.split("=")[0] for c in second.headers.get_list("set-cookie")]
    assert names == ["sprpta_at"]  # no second refresh token handed out
    assert client.post("/api/auth/refresh").status_code == 200  # real token still valid


def test_reusing_an_old_refresh_token_after_grace_kills_the_session(client, db):
    user = make_user(db, "a@sprpta.test", UserRole.L1)
    sign_in(client, "a@sprpta.test")
    old_rt = client.cookies.get("sprpta_rt")
    client.post("/api/auth/refresh")
    sess = db.scalar(select(AuthSession).where(AuthSession.user_id == user.id))
    sess.rotated_at = datetime.now(UTC) - timedelta(seconds=settings.refresh_grace_seconds + 5)
    db.commit()

    stolen = TestClient(app).post("/api/auth/refresh", headers={"Cookie": f"sprpta_rt={old_rt}"})
    assert stolen.status_code == 401
    db.expire_all()
    assert db.get(AuthSession, sess.id).revoke_reason == "reuse_detected"
    # the legitimate holder is signed out too
    assert client.post("/api/auth/refresh").status_code == 401
    assert client.get("/api/auth/me").status_code == 401


def test_refresh_fails_after_idle_or_absolute_timeout(client, db):
    user = make_user(db, "a@sprpta.test", UserRole.L1)
    for column in ("idle_expires_at", "absolute_expires_at"):
        sign_in(client, "a@sprpta.test")
        sess = db.scalar(
            select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        )
        setattr(sess, column, datetime.now(UTC) - timedelta(seconds=1))
        db.commit()
        r = client.post("/api/auth/refresh")
        assert r.status_code == 401 and r.json()["detail"]["code"] == "session_expired"


def test_refresh_without_a_cookie_is_rejected(client):
    assert client.post("/api/auth/refresh").status_code == 401


def test_session_lifetimes_follow_the_agreed_settings(client, db):
    user = make_user(db, "a@sprpta.test", UserRole.L1)
    sign_in(client, "a@sprpta.test")
    sess = db.scalar(select(AuthSession).where(AuthSession.user_id == user.id))
    assert sess.idle_expires_at - sess.created_at == pytest.approx(
        timedelta(minutes=30), abs=timedelta(seconds=5)
    )
    assert sess.absolute_expires_at - sess.created_at == pytest.approx(
        timedelta(hours=12), abs=timedelta(seconds=5)
    )
    assert settings.access_token_minutes == 15


# ------------------------------------------------------------------ logout and deactivation


def test_logout_ends_the_session_immediately(client, db):
    make_user(db, "a@sprpta.test", UserRole.L1)
    sign_in(client, "a@sprpta.test")
    access, refresh = client.cookies.get("sprpta_at"), client.cookies.get("sprpta_rt")

    r = client.post("/api/auth/logout")
    assert r.status_code == 200
    assert client.get("/api/auth/me").status_code == 401

    # copies of the old cookies are useless: the session row is revoked
    replay = TestClient(app)
    assert replay.get("/api/auth/me", headers={"Cookie": f"sprpta_at={access}"}).status_code == 401
    assert replay.post("/api/auth/refresh", headers={"Cookie": f"sprpta_rt={refresh}"}).status_code == 401
    assert client.post("/api/auth/logout").status_code == 200  # signing out twice is fine


def test_logout_only_ends_this_browsers_session(db):
    make_user(db, "a@sprpta.test", UserRole.L1)
    laptop, office_pc = TestClient(app), TestClient(app)
    sign_in(laptop, "a@sprpta.test")
    sign_in(office_pc, "a@sprpta.test")
    laptop.post("/api/auth/logout")
    assert laptop.get("/api/auth/me").status_code == 401
    assert office_pc.get("/api/auth/me").status_code == 200


def test_deactivating_a_user_ends_their_session_at_once(client, db):
    user = make_user(db, "a@sprpta.test", UserRole.L1)
    sign_in(client, "a@sprpta.test")
    db.expire_all()
    db.get(User, user.id).is_active = False
    db.commit()
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/refresh").status_code == 401


def test_usage_log_records_login_failure_and_logout_without_the_typed_identifier(client, db):
    make_user(db, "a@sprpta.test", UserRole.L1)
    sign_in(client, "a@sprpta.test", "bad")
    sign_in(client, "a@sprpta.test")
    client.post("/api/auth/logout")
    rows = db.scalars(select(UsageLog).order_by(UsageLog.id)).all()
    assert [r.event_type for r in rows] == ["login_failed", "login", "logout"]
    assert all(r.user_id is not None for r in rows)
    assert not any("a@sprpta.test" in (r.resource or "") for r in rows)
