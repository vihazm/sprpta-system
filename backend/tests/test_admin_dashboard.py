from collections import namedtuple
from datetime import UTC, datetime, timedelta
from itertools import count

import pytest
from fastapi.testclient import TestClient

from app.core.enums import ComplaintStatus, MessageChannel, MessageState, MessageType, VehicleType
from app.core.roles import UserRole
from app.core.timezone import LOCAL
from app.main import app
from app.models import (
    Area,
    Complaint,
    ComplaintCategory,
    ComplaintMedium,
    OutboundMessage,
    Permit,
    Severity,
    SystemSetting,
    UsageLog,
    Vehicle,
)
from app.services import system_health_service
from app.services.admin_dashboard_service import mask_name
from app.services.system_health_service import LAST_BACKUP_KEY
from tests.conftest import make_complainant, make_user, sign_in

URL = "/api/admin/dashboard"
NUMBERS = count(1)
DiskUsage = namedtuple("DiskUsage", "total used free")


@pytest.fixture(autouse=True)
def roomy_disk(monkeypatch):
    """The dashboard reads the real disk. Pin it to a roomy one, so that a nearly full disk on the machine running
    the tests does not add a "File storage is almost full" item. The low-space test sets its own."""
    monkeypatch.setattr(system_health_service.shutil, "disk_usage", lambda _: DiskUsage(total=1000, used=100, free=900))


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


# ---------------------------------------------------------------- areas, master data and complaints


def lists(db, galle) -> dict:
    """A second area, the lists a routed complaint needs, a bus, and a Level 1 and a Galle officer."""
    matara = Area(name="Matara")
    critical = Severity(name="Critical", rank=1, forward_days=0, decide_days=1, close_days=3, rating_weight=8)
    low = Severity(name="Low", rank=4, forward_days=3, decide_days=14, close_days=30, rating_weight=1)
    medium = ComplaintMedium(name="WhatsApp")
    category = ComplaintCategory(name="Overcharging")
    db.add_all([matara, critical, low, medium, category])
    db.flush()
    bus = Vehicle(vehicle_number="NB-2345", vehicle_type=VehicleType.BUS, registered_area_id=galle.id)
    db.add(bus)
    db.commit()
    return {
        "galle": galle,
        "critical": critical,
        "low": low,
        "medium": medium,
        "category": category,
        "bus": bus,
        "l1": make_user(db, "office@sprpta.test", UserRole.L1),
        "officer": make_user(db, "officer@sprpta.test", UserRole.L2, area_id=galle.id),
    }


def complaint(db, x: dict, *, days_ago: float, severity=None, **changes) -> None:
    """A forwarded complaint registered `days_ago` days ago."""
    registered = datetime.now(LOCAL) - timedelta(days=days_ago)
    fields = dict(
        reference_number=f"SPRPTA-2026-{next(NUMBERS):06d}",
        status=ComplaintStatus.FORWARDED,
        entered_by_user_id=x["l1"].id,
        medium_id=x["medium"].id,
        category_id=x["category"].id,
        severity_id=(severity or x["low"]).id,
        vehicle_id=x["bus"].id,
        area_id=x["galle"].id,
        assigned_l2_user_id=x["officer"].id,
        registered_at=registered,
        forwarded_at=registered,
    )
    db.add(Complaint(**{**fields, **changes}))
    db.commit()


def test_areas_show_their_vehicles_and_whether_an_officer_covers_them(client, db, galle):
    signed_in_admin(db, client)
    lists(db, galle)
    db.add(Vehicle(vehicle_number="NC-1111", vehicle_type=VehicleType.BUS, registered_area_id=galle.id, is_active=False))
    db.commit()

    body = client.get(URL).json()
    assert body["areas"] == [
        {"name": "Galle", "vehicles": 1, "has_officer": True},  # the inactive bus is not counted
        {"name": "Matara", "vehicles": 0, "has_officer": False},
    ]
    first = body["attention"][0]
    assert (first["title"], first["tone"], first["action"], first["href"]) == (
        "Matara has no active Level 2 officer", "crit", "Assign officer", "/admin/users",
    )


def test_master_data_counts_active_records_and_vehicles_without_a_permit(client, db, galle):
    signed_in_admin(db, client)
    x = lists(db, galle)
    db.add(Vehicle(vehicle_number="NC-1111", vehicle_type=VehicleType.BUS, registered_area_id=galle.id))
    db.add(Permit(permit_number="000123", vehicle_id=x["bus"].id))
    db.commit()

    assert client.get(URL).json()["master_data"] == {
        "people": 0,
        "vehicles": 2,
        "permits": 1,
        "routes_and_stands": 0,
        "categories": 1,
        "vehicles_without_permit": 1,
    }


def test_complaint_volume_covers_30_days_and_overdue_cases_of_any_age(client, db, galle):
    signed_in_admin(db, client)
    x = lists(db, galle)
    complaint(db, x, days_ago=0)
    complaint(db, x, days_ago=0, status=ComplaintStatus.UNDER_REVIEW)
    complaint(db, x, days_ago=3, severity=x["critical"])  # past its decide-by target of 1 day
    complaint(db, x, days_ago=40, severity=x["critical"])  # too old to count, but still overdue

    volume = client.get(URL).json()["complaints"]
    assert len(volume["per_day"]) == 30
    assert (volume["per_day"][-1], volume["per_day"][-4], sum(volume["per_day"])) == (2, 1, 3)
    assert volume["by_area"] == [{"label": "Galle", "count": 3}]
    assert volume["by_status"] == [{"label": "forwarded", "count": 2}, {"label": "under_review", "count": 1}]
    assert volume["overdue"] == 2


def test_time_targets_go_from_most_to_least_severe(client, db, galle):
    signed_in_admin(db, client)
    lists(db, galle)
    assert client.get(URL).json()["time_targets"] == [
        {"severity": "Critical", "forward_days": 0, "decide_days": 1, "close_days": 3},
        {"severity": "Low", "forward_days": 3, "decide_days": 14, "close_days": 30},
    ]


# ---------------------------------------------------------------- needs you


def titles(client) -> list[str]:
    return [item["title"] for item in client.get(URL).json()["attention"]]


def record_backup(db, *, succeeded: bool, hours_ago: float, error: str | None = None) -> None:
    finished = datetime.now(UTC) - timedelta(hours=hours_ago)
    run = {"succeeded": succeeded, "file": None, "size_bytes": 10, "error": error, "finished_at": finished.isoformat()}
    db.merge(SystemSetting(key=LAST_BACKUP_KEY, value=run))
    db.commit()


def test_a_backup_that_never_ran_failed_or_was_missed_needs_attention(client, db):
    signed_in_admin(db, client)
    assert titles(client) == ["No backup has been made yet"]

    record_backup(db, succeeded=False, hours_ago=1, error="pg_dump: error: disk full")
    item = client.get(URL).json()["attention"][0]
    assert (item["title"], item["detail"], item["tone"]) == ("The last backup failed", "pg_dump: error: disk full", "crit")

    record_backup(db, succeeded=True, hours_ago=30)
    assert titles(client) == ["The daily backup did not run"]

    record_backup(db, succeeded=True, hours_ago=2)
    assert titles(client) == []
    assert client.get(URL).json()["last_backup"]["succeeded"] is True


def test_urgent_items_come_before_low_space_and_locked_staff(client, db, monkeypatch):
    signed_in_admin(db, client)
    make_user(db, "locked@sprpta.test", UserRole.L1, locked_until=datetime.now(UTC) + timedelta(minutes=10))
    record_backup(db, succeeded=False, hours_ago=1, error="Failed")
    monkeypatch.setattr(system_health_service.shutil, "disk_usage", lambda _: DiskUsage(total=1000, used=950, free=50))

    assert titles(client) == ["The last backup failed", "File storage is almost full", "1 staff account is locked"]
    storage = client.get(URL).json()["file_storage"]
    assert (storage["low"], storage["free_bytes"], storage["total_bytes"]) == (True, 50, 1000)


def test_messages_are_counted_from_the_log_for_the_last_24_hours(client, db):
    signed_in_admin(db, client)
    assert client.get(URL).json()["messages"] == {
        "sent": 0,
        "failed": 0,
        "by_type": [
            {"label": label, "count": 0}
            for label in ("MSG-1 Registered", "MSG-2 Decided", "MSG-3 Closed", "Verification code")
        ],
    }

    account = make_complainant(db, "client@sprpta.test")
    now = datetime.now(UTC)
    for state, when in (("sent", now), ("sent", now), ("failed", now), ("sent", now - timedelta(hours=30))):
        db.add(
            OutboundMessage(
                complainant_account_id=account.id, message_type=MessageType.OTP, channel=MessageChannel.EMAIL,
                recipient=account.email, body="code ******", state=MessageState(state), attempted_at=when,
            )
        )
    db.commit()
    messages = client.get(URL).json()["messages"]
    assert messages["sent"] == 2 and messages["failed"] == 1  # the one from yesterday is left out
    assert messages["by_type"][-1] == {"label": "Verification code", "count": 3}
