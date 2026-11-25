"""Complainant sign-up with a one-time code (UC-CP-01)."""

import re
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.enums import MessageState
from app.core.roles import UserRole
from app.models import ComplainantAccount, OtpCode, OutboundMessage
from tests.conftest import PASSWORD, make_complainant, make_user, sign_in

SIGNUP = "/api/auth/signup"
VERIFY = "/api/auth/verify-otp"
RESEND = "/api/auth/resend-otp"
EMAIL = "nimali@sprpta.test"


def sign_up(client, identifier=EMAIL, name="Nimali Perera", password=PASSWORD):
    return client.post(SIGNUP, json={"name": name, "identifier": identifier, "password": password})


def printed_code(capsys) -> str:
    """The code the backend printed in its terminal (console mode)."""
    found = re.findall(r"\[SPRPTA sign-up code\] \S+: (\d{6})", capsys.readouterr().out)
    assert found, "no code was printed"
    return found[-1]


def account(db, email=EMAIL) -> ComplainantAccount:
    db.expire_all()
    return db.scalar(select(ComplainantAccount).where(ComplainantAccount.email == email))


def test_sign_up_makes_an_unverified_account_and_prints_a_code(client, db, capsys):
    r = sign_up(client)
    assert r.status_code == 200
    assert r.json() == {"channel": "email", "resend_after": settings.otp_resend_seconds}
    assert len(printed_code(capsys)) == 6
    created = account(db)
    assert created.verified_at is None and created.display_name == "Nimali Perera"
    assert created.password_hash != PASSWORD


def test_the_message_log_never_holds_the_code(client, db, capsys):
    sign_up(client)
    code = printed_code(capsys)
    row = db.scalar(select(OutboundMessage))
    assert row.state == MessageState.SENT and code not in row.body
    assert db.scalar(select(OtpCode.code_hash)) != code


def test_an_unverified_account_cannot_log_in(client, capsys):
    sign_up(client)
    r = sign_in(client, EMAIL)
    assert r.status_code == 403 and r.json()["detail"]["code"] == "account_not_verified"


def test_the_right_code_verifies_and_signs_in(client, db, capsys):
    sign_up(client)
    r = client.post(VERIFY, json={"identifier": EMAIL, "code": printed_code(capsys)})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "cp" and r.json()["redirect_to"] == "/cp/dashboard"
    assert "sprpta_at" in client.cookies
    assert account(db).verified_at is not None
    assert client.get("/api/cp/complaints").status_code == 200  # the new session works
    assert sign_in(client, EMAIL).status_code == 200  # and so does the password


def test_a_code_works_once(client, capsys):
    sign_up(client)
    code = printed_code(capsys)
    assert client.post(VERIFY, json={"identifier": EMAIL, "code": code}).status_code == 200
    again = client.post(VERIFY, json={"identifier": EMAIL, "code": code})
    assert again.status_code == 400 and again.json()["detail"]["code"] == "invalid_code"


def test_a_wrong_code_is_refused_and_too_many_lock_the_code(client, db, capsys):
    sign_up(client)
    code = printed_code(capsys)
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(settings.otp_max_attempts):
        r = client.post(VERIFY, json={"identifier": EMAIL, "code": wrong})
        assert r.status_code == 400 and r.json()["detail"]["code"] == "invalid_code"
    locked = client.post(VERIFY, json={"identifier": EMAIL, "code": code})
    assert locked.status_code == 429 and locked.json()["detail"]["code"] == "too_many_codes"
    assert account(db).verified_at is None


def test_an_expired_code_is_refused(client, db, capsys):
    sign_up(client)
    code = printed_code(capsys)
    otp = db.scalar(select(OtpCode))
    otp.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    db.commit()
    r = client.post(VERIFY, json={"identifier": EMAIL, "code": code})
    assert r.status_code == 400 and r.json()["detail"]["code"] == "invalid_code"


def test_a_new_code_replaces_the_old_one_after_the_wait(client, db, capsys):
    sign_up(client)
    first = printed_code(capsys)
    too_soon = client.post(RESEND, json={"identifier": EMAIL})
    assert too_soon.status_code == 429 and too_soon.json()["detail"]["code"] == "resend_too_soon"

    otp = db.scalar(select(OtpCode))
    otp.created_at = datetime.now(UTC) - timedelta(seconds=settings.otp_resend_seconds + 1)
    db.commit()
    assert client.post(RESEND, json={"identifier": EMAIL}).status_code == 200
    second = printed_code(capsys)

    if first != second:
        assert client.post(VERIFY, json={"identifier": EMAIL, "code": first}).status_code == 400
    assert client.post(VERIFY, json={"identifier": EMAIL, "code": second}).status_code == 200


def test_a_phone_number_gets_a_text_message_code(client, db, capsys):
    r = sign_up(client, "071 234 5678")
    assert r.status_code == 200 and r.json()["channel"] == "sms"
    assert "+94712345678" in capsys.readouterr().out
    created = db.scalar(select(ComplainantAccount))
    assert created.phone == "+94712345678" and created.email is None


def test_a_registered_email_or_login_cannot_sign_up_again(client, db):
    make_complainant(db, "taken@sprpta.test")
    make_user(db, "staff@sprpta.test", UserRole.L1)
    for identifier in ("taken@sprpta.test", "staff@sprpta.test"):
        r = sign_up(client, identifier)
        assert r.status_code == 409 and r.json()["detail"]["code"] == "already_registered"


def test_an_unfinished_sign_up_can_be_started_again(client, db, capsys):
    sign_up(client, name="First Try")
    printed_code(capsys)
    assert sign_up(client, name="Second Try").status_code == 200
    code = printed_code(capsys)
    assert account(db).display_name == "Second Try"
    assert client.post(VERIFY, json={"identifier": EMAIL, "code": code}).status_code == 200


@pytest.mark.parametrize(
    "body",
    [
        {"name": "A", "identifier": "not-an-address", "password": PASSWORD},
        {"name": "A", "identifier": EMAIL, "password": "short"},
        {"name": "   ", "identifier": EMAIL, "password": PASSWORD},
    ],
)
def test_bad_sign_up_details_are_refused(client, body):
    assert client.post(SIGNUP, json=body).status_code == 422


def test_outside_development_no_code_is_sent_until_a_provider_exists(client, monkeypatch, capsys):
    monkeypatch.setattr(settings, "app_env", "production")
    r = sign_up(client)
    assert r.status_code == 503 and r.json()["detail"]["code"] == "code_not_sent"
    assert "sign-up code" not in capsys.readouterr().out


def test_asking_too_often_from_one_address_is_stopped(client, monkeypatch, capsys):
    monkeypatch.setattr(settings, "ip_failure_limit", 3)
    codes = [sign_up(client, f"p{i}@sprpta.test").status_code for i in range(4)]
    assert codes == [200, 200, 200, 429]
