from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.core.roles import UserRole
from app.main import app
from app.models import UsageLog
from app.services.admin_dashboard_service import mask_name
from tests.conftest import make_complainant, make_user, sign_in

URL = "/api/admin/dashboard"


def signed_in_admin(db, client) -> None:
    make_user(db, "admin@sprpta.test", UserRole.ADMIN, full_name="Sarah Admin")
    sign_in(client, "admin@sprpta.test")


def test_only_the_admin_may_open_the_dashboard(client, db):
    assert client.get(URL).status_code == 401
    make_user(db, "office@sprpta.test", UserRole.L1)
    sign_in(client, "office@sprpta.test")
    assert client.get(URL).status_code == 403


def test_counts_come_from_the_database(client, db, galle):
    signed_in_admin(db, client)
    make_user(db, "one@sprpta.test", UserRole.L1)
    make_user(db, "two@sprpta.test", UserRole.L1)
    make_user(db, "officer@sprpta.test", UserRole.L2, area_id=galle.id)
    make_user(db, "gone@sprpta.test", UserRole.L1, is_active=False)
    make_user(
        db, "locked@sprpta.test", UserRole.IMPLEMENTING_STAFF, locked_until=datetime.now(UTC) + timedelta(minutes=10)
    )
    make_complainant(db, "a@sprpta.test")
    make_complainant(db, "b@sprpta.test")
    make_complainant(db, "new@sprpta.test", verified_at=None)
    make_complainant(db, "off@sprpta.test", is_active=False)

    sign_in(TestClient(app), "one@sprpta.test")  # a second person signs in
    sign_in(TestClient(app), "two@sprpta.test", "wrong")  # and one failed attempt

    body = client.get(URL).json()
    assert body["sessions"] == {"signed_in_now": 2, "sign_ins_today": 2, "failed_today": 1, "locked_accounts": 1}
    assert [r["count"] for r in body["staff_by_role"]] == [2, 1, 0, 1, 1]  # L1, L2, L3, admin, IS
    assert body["portal_users"] == {"total": 2, "unverified": 1}
    assert body["deactivated_users"] == 2


def test_logging_out_removes_someone_from_signed_in_now(client, db):
    signed_in_admin(db, client)
    make_user(db, "one@sprpta.test", UserRole.L1)
    other = TestClient(app)
    sign_in(other, "one@sprpta.test")
    assert client.get(URL).json()["sessions"]["signed_in_now"] == 2
    other.post("/api/auth/logout")
    assert client.get(URL).json()["sessions"]["signed_in_now"] == 1


def test_sign_ins_are_counted_per_hour_for_the_last_24_hours(client, db):
    signed_in_admin(db, client)  # one sign-in, in the current hour
    now = datetime.now(UTC)
    db.add_all(
        [
            UsageLog(event_type="login", occurred_at=now - timedelta(hours=5)),
            UsageLog(event_type="login", occurred_at=now - timedelta(hours=30)),  # too old
        ]
    )
    db.commit()

    body = client.get(URL).json()
    per_hour = body["sign_ins_per_hour"]
    assert len(per_hour) == 24
    assert per_hour[-1] == 1
    assert per_hour[-1 - 5] == 1
    assert sum(per_hour) == 2
    assert 0 <= body["current_hour"] <= 23


def test_recent_usage_is_newest_first_and_names_are_masked(client, db):
    signed_in_admin(db, client)
    make_user(db, "kavindu@sprpta.test", UserRole.L1, full_name="Kavindu Perera")
    make_complainant(db, "client@sprpta.test")
    sign_in(TestClient(app), "kavindu@sprpta.test")
    sign_in(TestClient(app), "ghost@sprpta.test", "wrong")
    sign_in(TestClient(app), "client@sprpta.test")

    response = client.get(URL)
    events = response.json()["recent_usage"]
    assert [(e["who"], e["role"], e["event"]) for e in events] == [
        ("T*** C*****", "Portal", "signed in"),
        ("Unknown login", "No account", "failed sign-in"),
        ("K***** P*****", "Level 1", "signed in"),
        ("S**** A****", "Administrator", "signed in"),
    ]
    assert "@" not in response.text  # no email address ever reaches the administrator


def test_mask_name_keeps_the_first_letter_and_hides_the_length():
    assert mask_name("Kavindu Perera") == "K***** P*****"
    assert mask_name("Li Wu") == "L* W*"
    assert mask_name("Wickramasinghe") == "W*****"
