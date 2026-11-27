"""A complainant who forgot their password resets it with a one-time code (UC-CP-02)."""

import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.roles import UserRole
from app.models import AuthSession, OtpCode
from tests.conftest import PASSWORD, make_complainant, make_user, sign_in

FORGOT = "/api/auth/forgot-password"
RESET = "/api/auth/reset-password"
EMAIL = "client@sprpta.test"
NEW_PASSWORD = "a-brand-new-pass"


def printed_code(capsys) -> str:
    found = re.findall(r"\[SPRPTA password reset code\].*\n.*?(\d{6})", capsys.readouterr().out)
    assert found, "no code was printed"
    return found[-1]


def reset(client, code, identifier=EMAIL, password=NEW_PASSWORD):
    return client.post(RESET, json={"identifier": identifier, "code": code, "password": password})


def test_the_code_resets_the_password(client, db, capsys):
    make_complainant(db, EMAIL)
    sent = client.post(FORGOT, json={"identifier": EMAIL})
    assert sent.status_code == 200 and sent.json()["channel"] == "email"

    assert reset(client, printed_code(capsys)).status_code == 204
    assert sign_in(client, EMAIL).status_code == 401  # the old password no longer works
    assert sign_in(client, EMAIL, NEW_PASSWORD).status_code == 200


def test_a_code_works_once_and_a_wrong_one_is_refused(client, db, capsys):
    make_complainant(db, EMAIL)
    client.post(FORGOT, json={"identifier": EMAIL})
    code = printed_code(capsys)
    wrong = "000000" if code != "000000" else "111111"
    assert reset(client, wrong).json()["detail"]["code"] == "invalid_code"
    assert reset(client, code).status_code == 204
    assert reset(client, code).json()["detail"]["code"] == "invalid_code"


def test_an_expired_code_is_refused(client, db, capsys):
    make_complainant(db, EMAIL)
    client.post(FORGOT, json={"identifier": EMAIL})
    code = printed_code(capsys)
    otp = db.scalar(select(OtpCode))
    otp.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    assert reset(client, code).status_code == 400


def test_an_unknown_address_gets_the_same_answer_and_no_code(client, db, capsys):
    for identifier in ("nobody@sprpta.test",):
        answer = client.post(FORGOT, json={"identifier": identifier})
        assert answer.status_code == 200 and answer.json()["channel"] == "email"
    assert "password reset code" not in capsys.readouterr().out
    assert db.scalar(select(OtpCode)) is None


def test_asking_again_too_soon_sends_nothing_new(client, db, capsys):
    make_complainant(db, EMAIL)
    client.post(FORGOT, json={"identifier": EMAIL})
    printed_code(capsys)
    again = client.post(FORGOT, json={"identifier": EMAIL})
    assert again.status_code == 200 and again.json()["resend_after"] > 0
    assert "password reset code" not in capsys.readouterr().out


def test_resetting_ends_every_session_and_lifts_a_lock(client, db, capsys):
    account = make_complainant(db, EMAIL, locked_until=datetime.now(UTC) + timedelta(minutes=15))
    db.add(
        AuthSession(
            account_id=account.id,
            refresh_token_hash="old-session",
            idle_expires_at=datetime.now(UTC) + timedelta(hours=1),
            absolute_expires_at=datetime.now(UTC) + timedelta(hours=8),
        )
    )
    db.commit()
    client.post(FORGOT, json={"identifier": EMAIL})
    reset(client, printed_code(capsys))

    db.expire_all()
    assert db.scalar(select(AuthSession.revoke_reason)) == "password_reset"
    assert sign_in(client, EMAIL, NEW_PASSWORD).status_code == 200


def test_a_short_password_is_refused(client, db, capsys):
    make_complainant(db, EMAIL)
    client.post(FORGOT, json={"identifier": EMAIL})
    assert reset(client, printed_code(capsys), password="short").status_code == 422
    assert sign_in(client, EMAIL, PASSWORD).status_code == 200


def test_staff_are_told_to_contact_the_administrator(client, db, capsys):
    make_user(db, "office@sprpta.test", UserRole.L1)
    for path, body in (
        ("/api/auth/account-check", {"identifier": "Office@sprpta.test"}),
        (FORGOT, {"identifier": "office@sprpta.test"}),
        ("/api/auth/signup", {"name": "Office", "identifier": "office@sprpta.test", "password": "long-enough-1"}),
    ):
        refused = client.post(path, json=body)
        assert refused.status_code == 409 and refused.json()["detail"]["code"] == "staff_account", path
        assert "System Administrator" in refused.json()["detail"]["message"]
    assert "code" not in capsys.readouterr().out
    assert db.scalar(select(OtpCode)) is None


def test_anyone_else_passes_the_account_check(client, db):
    make_complainant(db, EMAIL)
    for identifier in (EMAIL, "nobody@sprpta.test", "not an address"):
        assert client.post("/api/auth/account-check", json={"identifier": identifier}).status_code == 204


def test_the_account_check_is_limited_per_address(client, db, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "ip_failure_limit", 3)
    answers = [client.post("/api/auth/account-check", json={"identifier": f"n{i}@sprpta.test"}).status_code for i in range(4)]
    assert answers == [204, 204, 204, 429]
