from datetime import datetime, time, timedelta
from itertools import count

import pytest
from fastapi.testclient import TestClient
from app.core.enums import ComplaintStatus, PlaceKind, RejectionType, VehicleType
from app.core.roles import UserRole
from app.core.timezone import LOCAL
from app.main import app
from app.models import (
    AuditLog,
    Complaint,
    ComplaintCategory,
    ComplaintMedium,
    DuplicateCheck,
    RouteStand,
    Severity,
    Vehicle,
)
from tests.conftest import make_user, sign_in, target_id

_numbers = count(1)  # a distinct reference number for each complaint added below

DASHBOARD = "/api/l1/dashboard"
COMPLAINTS = "/api/l1/complaints"
ALL = {"scope": "all"}  # the whole Level 1 queue; the list shows only the officer's own complaints by default
NOW = datetime.now(LOCAL)


class World:
    """Two Level 1 officers (`me` is signed in), an area officer, and the lists a complaint needs."""


@pytest.fixture
def world(db, client, galle) -> World:
    w = World()
    w.area = galle
    w.officer = make_user(db, "ruwan@sprpta.test", UserRole.L2, area_id=galle.id, full_name="Ruwan Silva")
    w.me = make_user(db, "office@sprpta.test", UserRole.L1, full_name="Office Staff")
    w.other = make_user(db, "other@sprpta.test", UserRole.L1, full_name="Other Staff")
    w.medium = ComplaintMedium(name="WhatsApp")
    w.category = ComplaintCategory(name="Overcharging")
    w.severity = Severity(name="High", rank=2, forward_days=1, decide_days=3, close_days=7, rating_weight=4)
    db.add_all([w.medium, w.category, w.severity])
    db.flush()
    w.bus = Vehicle(vehicle_number="ND-7782", vehicle_type=VehicleType.BUS, registered_area_id=galle.id)
    w.bus2 = Vehicle(vehicle_number="ND-7980", vehicle_type=VehicleType.BUS, registered_area_id=galle.id)
    db.add_all([w.bus, w.bus2])
    db.commit()
    sign_in(client, "office@sprpta.test")
    return w


def add(db, *, by, status=ComplaintStatus.DRAFT, created=None, ref=None, **fields) -> Complaint:
    """A complaint put straight into the database, so that its dates and status can be chosen."""
    created = created or NOW
    complaint = Complaint(
        status=status, entered_by_user_id=by.id if by else None, created_at=created, updated_at=created, **fields
    )
    if status not in (ComplaintStatus.DRAFT, ComplaintStatus.SUBMITTED):
        complaint.reference_number = ref or f"TEST-{next(_numbers):06d}"
    elif ref:
        complaint.reference_number = ref
    db.add(complaint)
    db.commit()
    return complaint


def summary(client) -> dict:
    response = client.get(DASHBOARD)
    assert response.status_code == 200, response.text
    return response.json()


# ---------------------------------------------------------------- authorization


def test_only_level_one_staff_may_see_the_dashboard_and_the_lists(client, db, world):
    for url in (DASHBOARD, COMPLAINTS, f"{COMPLAINTS}/by-reference?reference=X"):
        assert TestClient(app).get(url).status_code == 401
    for login, role in (("admin@sprpta.test", UserRole.ADMIN), ("chair@sprpta.test", UserRole.L3)):
        make_user(db, login, role)
        other = TestClient(app)
        sign_in(other, login)
        for url in (DASHBOARD, COMPLAINTS, f"{COMPLAINTS}/by-reference?reference=X"):
            assert other.get(url).status_code == 403, (login, url)
    area = TestClient(app)
    sign_in(area, "ruwan@sprpta.test")  # the Level 2 officer of Galle
    for url in (DASHBOARD, COMPLAINTS):
        assert area.get(url).status_code == 403


def test_the_dashboard_is_not_cached(client, world):
    assert client.get(DASHBOARD).headers["cache-control"] == "no-store"


# ---------------------------------------------------------------- empty and counts


def test_with_no_complaints_everything_is_zero_and_the_lists_are_empty(client, world):
    body = summary(client)
    assert body == {
        "day": {"entered": 0, "forwarded": 0, "still_open": 0},
        "week_entered": 0,
        "month_entered": 0,
        "queues": {"portal": 0, "drafts": 0, "incomplete": 0, "duplicates": 0},
        "by_target": {"driver": 0, "conductor": 0, "owner": 0, "bus_service": 0, "other": 0, "unclassified": 0},
        "waiting": [],
        "portal": [],
    }
    page = client.get(COMPLAINTS).json()
    assert page["items"] == [] and page["total"] == 0 and page["page"] == 1
    assert page["counts"] == {"all": 0, "draft": 0, "incomplete": 0, "submitted": 0, "forwarded": 0, "rejected": 0, "duplicates": 0}
    assert page["target_counts"] == {"all": 0, "driver": 0, "conductor": 0, "owner": 0, "bus_service": 0, "other": 0, "unclassified": 0}


def test_entered_counts_the_officers_own_work_by_day_week_and_month(client, db, world):
    midnight = datetime.combine(NOW.date(), time.min, LOCAL)
    monday = midnight - timedelta(days=midnight.weekday())
    first = midnight.replace(day=1)
    offsets = [timedelta(0), timedelta(hours=-5), timedelta(days=-3), timedelta(days=-9), timedelta(days=-40)]
    mine = [NOW + o for o in offsets]  # now, five hours ago, three, nine and forty days ago
    for moment in mine:
        add(db, by=world.me, created=moment)
    add(db, by=world.other, created=NOW)  # somebody else's work is not mine
    add(db, by=None, status=ComplaintStatus.SUBMITTED, created=NOW)  # a portal complaint has no officer

    body = summary(client)
    assert body["day"]["entered"] == sum(1 for m in mine if m >= midnight)
    assert body["week_entered"] == sum(1 for m in mine if m >= monday)
    assert body["month_entered"] == sum(1 for m in mine if m >= first)
    assert 1 <= body["day"]["entered"] <= 2 and body["month_entered"] >= body["week_entered"] >= body["day"]["entered"]


def test_still_open_counts_only_todays_entries_that_have_not_left_level_one(client, db, world):
    add(db, by=world.me, status=ComplaintStatus.DRAFT)
    add(db, by=world.me, status=ComplaintStatus.INCOMPLETE)
    add(db, by=world.me, status=ComplaintStatus.REJECTED, rejection_type=RejectionType.SPAM, rejection_reason="Spam")
    add(db, by=world.me, status=ComplaintStatus.DRAFT, created=NOW - timedelta(days=4))  # an older draft
    add(db, by=world.other, status=ComplaintStatus.DRAFT)
    body = summary(client)
    assert body["day"]["entered"] == 3 and body["day"]["still_open"] == 2


def test_forwarded_counts_what_this_officer_forwarded_today_from_the_audit_trail(client, db, world):
    complete = {
        "medium_id": world.medium.id,
        "complaint_date": NOW.date().isoformat(),
        "vehicle_number": "ND-7782",
        "category_id": world.category.id,
        "severity_id": world.severity.id,
        "complainant_name": "Kamala",
        "target_type_id": target_id(db, "bus_service"),
        "subject": "Fare",
        "description": "Asked for double",
    }
    route = RouteStand(kind=PlaceKind.ROUTE, name="Galle - Matara", area_id=world.area.id)
    db.add(route)
    db.commit()
    complete["route_stand_id"] = route.id
    created = client.post(COMPLAINTS, json=complete).json()
    assert client.post(f"{COMPLAINTS}/{created['id']}/forward").status_code == 200
    # Another officer's forward, and one of mine from yesterday, do not count.
    db.add_all(
        [
            AuditLog(actor_user_id=world.other.id, actor_role="l1", action="complaint.forward", entity_type="complaints"),
            AuditLog(
                actor_user_id=world.me.id, actor_role="l1", action="complaint.forward", entity_type="complaints",
                occurred_at=NOW - timedelta(days=1, hours=1),
            ),
        ]
    )
    db.commit()
    body = summary(client)
    assert body["day"]["forwarded"] == 1 and body["day"]["entered"] == 1
    assert body["day"]["still_open"] == 0  # it was forwarded
    assert body["queues"]["drafts"] == 0


# ---------------------------------------------------------------- the shared queues


def test_the_queues_count_the_whole_level_one_team(client, db, world):
    add(db, by=world.me, status=ComplaintStatus.DRAFT)
    add(db, by=world.other, status=ComplaintStatus.DRAFT)
    add(db, by=world.other, status=ComplaintStatus.INCOMPLETE)
    add(db, by=None, status=ComplaintStatus.SUBMITTED)
    add(db, by=world.me, status=ComplaintStatus.REJECTED, rejection_type=RejectionType.SPAM, rejection_reason="Spam")
    assert summary(client)["queues"] == {"portal": 1, "drafts": 2, "incomplete": 1, "duplicates": 0}


def test_possible_duplicates_are_open_cases_with_an_earlier_case_on_the_same_bus_still_to_decide(client, db, world):
    earlier = add(
        db, by=world.other, status=ComplaintStatus.INCOMPLETE, vehicle_id=world.bus.id, ref="SPRPTA-2026-000001"
    )
    open_one = add(db, by=world.me, status=ComplaintStatus.DRAFT, vehicle_id=world.bus.id)
    add(db, by=world.me, status=ComplaintStatus.DRAFT, vehicle_id=world.bus2.id)  # another bus
    add(db, by=world.me, status=ComplaintStatus.DRAFT)  # no bus yet
    body = summary(client)
    # Only the draft counts: the incomplete case is registered, but it has no earlier case of its own.
    assert body["queues"]["duplicates"] == 1
    assert {w["id"]: w["possible_duplicate"] for w in body["waiting"]}[open_one.id] is True

    db.add(DuplicateCheck(complaint_id=open_one.id, candidate_complaint_id=earlier.id, link_type="not_duplicate",
                          decided_by_user_id=world.me.id))
    db.commit()
    body = summary(client)
    assert body["queues"]["duplicates"] == 0  # decided
    assert {w["id"]: w["possible_duplicate"] for w in body["waiting"]}[open_one.id] is False


def test_waiting_longest_lists_the_oldest_open_cases_first_and_only_six(client, db, world):
    oldest = add(db, by=world.other, status=ComplaintStatus.INCOMPLETE, created=NOW - timedelta(days=5), subject="Oldest")
    for hours in range(1, 8):
        add(db, by=world.me, status=ComplaintStatus.DRAFT, created=NOW - timedelta(hours=hours), subject=f"Draft {hours}")
    add(db, by=world.me, status=ComplaintStatus.REJECTED, created=NOW - timedelta(days=9), rejection_type=RejectionType.SPAM,
        rejection_reason="Spam")  # final cases do not wait for anyone
    waiting = summary(client)["waiting"]
    assert len(waiting) == 6
    assert waiting[0]["id"] == oldest.id and waiting[0]["subject"] == "Oldest" and waiting[0]["status"] == "incomplete"
    assert waiting[0]["reference_number"] is not None and waiting[1]["reference_number"] is None  # a draft has none
    ages = [w["age_minutes"] for w in waiting]
    assert ages == sorted(ages, reverse=True) and ages[0] >= 5 * 24 * 60
    assert [w["subject"] for w in waiting[1:]] == ["Draft 7", "Draft 6", "Draft 5", "Draft 4", "Draft 3"]


def test_portal_submissions_are_listed_oldest_first_and_only_five(client, db, world):
    for hours in range(1, 7):
        add(db, by=None, status=ComplaintStatus.SUBMITTED, created=NOW - timedelta(hours=hours), subject=f"Portal {hours}",
            complainant_name="Kamala")
    body = summary(client)
    assert body["queues"]["portal"] == 6 and len(body["portal"]) == 5
    assert [p["subject"] for p in body["portal"]][:2] == ["Portal 6", "Portal 5"]
    assert body["portal"][0]["complainant"] == "Kamala"


# ---------------------------------------------------------------- the Complaints list


def test_the_list_filters_by_status_with_counts_for_every_filter(client, db, world):
    add(db, by=world.me, status=ComplaintStatus.DRAFT, subject="A draft")
    add(db, by=world.me, status=ComplaintStatus.INCOMPLETE, subject="Incomplete one")
    add(db, by=None, status=ComplaintStatus.SUBMITTED, subject="Portal one")
    add(db, by=world.me, status=ComplaintStatus.REJECTED, subject="Rejected one", rejection_type=RejectionType.SPAM,
        rejection_reason="Spam")
    for status in (ComplaintStatus.FORWARDED, ComplaintStatus.UNDER_REVIEW, ComplaintStatus.CLOSED):
        add(db, by=world.me, status=status, subject=f"Left {status.value}", medium_id=world.medium.id,
            category_id=world.category.id, severity_id=world.severity.id, vehicle_id=world.bus.id, area_id=world.area.id,
            assigned_l2_user_id=world.officer.id)

    everything = client.get(COMPLAINTS, params=ALL).json()
    assert everything["counts"] == {
        "all": 7, "draft": 1, "incomplete": 1, "submitted": 1, "forwarded": 3, "rejected": 1, "duplicates": 0,
    }
    assert everything["total"] == 7
    only = lambda name: {r["subject"] for r in client.get(COMPLAINTS, params={**ALL, "status": name}).json()["items"]}  # noqa: E731
    assert only("draft") == {"A draft"} and only("incomplete") == {"Incomplete one"}
    assert only("submitted") == {"Portal one"} and only("rejected") == {"Rejected one"}
    assert only("forwarded") == {"Left forwarded", "Left under_review", "Left closed"}  # every case that left Level 1
    assert client.get(COMPLAINTS, params={**ALL, "status": "nonsense"}).status_code == 422


def test_the_list_shows_only_what_level_one_may_see(client, db, world):
    add(db, by=world.me, status=ComplaintStatus.FORWARDED, subject="Sent on", medium_id=world.medium.id,
        category_id=world.category.id, severity_id=world.severity.id, vehicle_id=world.bus.id, area_id=world.area.id,
        assigned_l2_user_id=world.officer.id, vehicle_number_entered="ND-7782", complainant_name="Kamala")
    add(db, by=world.me, status=ComplaintStatus.DRAFT, is_anonymous=True)
    items = client.get(COMPLAINTS, params=ALL).json()["items"]
    sent = next(i for i in items if i["subject"] == "Sent on")
    assert set(sent) == {
        "id", "reference_number", "status", "subject", "vehicle_number", "complainant", "area_name", "severity_name",
        "complaint_date", "updated_at", "editable", "possible_duplicate", "target_code", "target_name", "accused_name",
        "accused_status", "category_name", "bus_verification", "synthetic",
    }  # nothing of Level 2's review is here
    assert (sent["area_name"], sent["severity_name"], sent["editable"]) == ("Galle", "High", False)
    assert next(i for i in items if i["status"] == "draft")["editable"] is True
    assert next(i for i in items if i["status"] == "draft")["complainant"] is None


def test_the_list_searches_reference_subject_complainant_and_bus(client, db, world):
    add(db, by=world.me, status=ComplaintStatus.INCOMPLETE, ref="SPRPTA-2026-000042", subject="Rude conductor",
        complainant_name="Nimali", vehicle_number_entered="ND-7782")
    add(db, by=world.me, status=ComplaintStatus.DRAFT, subject="Late bus", complainant_name="Kamal",
        vehicle_number_entered="NB-1111")
    find = lambda term: {r["subject"] for r in client.get(COMPLAINTS, params={**ALL, "search": term}).json()["items"]}  # noqa: E731
    assert find("000042") == {"Rude conductor"} and find("conductor") == {"Rude conductor"}
    assert find("nimali") == {"Rude conductor"} and find("nb-1111") == {"Late bus"}
    assert find("nothing like it") == set()
    assert find("%") == set()  # wildcard characters are taken literally
    counts = client.get(COMPLAINTS, params={**ALL, "search": "conductor"}).json()["counts"]
    assert counts["all"] == 1 and counts["incomplete"] == 1 and counts["draft"] == 0


def test_the_list_is_paged_newest_first(client, db, world):
    for n in range(12):
        add(db, by=world.me, subject=f"Draft {n:02d}", created=NOW - timedelta(minutes=12 - n))
    first = client.get(COMPLAINTS, params=ALL).json()
    assert first["total"] == 12 and first["page_size"] == 10 and len(first["items"]) == 10
    assert first["items"][0]["subject"] == "Draft 11"  # the last one touched comes first
    second = client.get(COMPLAINTS, params={**ALL, "page": 2}).json()
    assert second["page"] == 2 and [i["subject"] for i in second["items"]] == ["Draft 01", "Draft 00"]
    assert client.get(COMPLAINTS, params={**ALL, "page": 99}).json()["page"] == 2  # past the end shows the last page
    assert client.get(COMPLAINTS, params={**ALL, "page": 0}).status_code == 422


def test_the_duplicates_filter_lists_the_open_cases_to_compare(client, db, world):
    add(db, by=world.other, status=ComplaintStatus.INCOMPLETE, vehicle_id=world.bus.id, ref="SPRPTA-2026-000001")
    add(db, by=world.me, status=ComplaintStatus.DRAFT, vehicle_id=world.bus.id, subject="Same bus")
    add(db, by=world.me, status=ComplaintStatus.DRAFT, vehicle_id=world.bus2.id, subject="Other bus")
    page = client.get(COMPLAINTS, params={**ALL, "status": "duplicates"}).json()
    assert [i["subject"] for i in page["items"]] == ["Same bus"] and page["total"] == 1
    assert page["items"][0]["possible_duplicate"] is True and page["counts"]["duplicates"] == 1


# ---------------------------------------------------------------- Find reference number


def test_a_reference_number_is_found_whatever_its_case_or_spacing(client, db, world):
    draft = add(
        db, by=world.other, status=ComplaintStatus.INCOMPLETE, ref="SPRPTA-2026-000042", subject="Another officer's case"
    )
    hit = client.get(f"{COMPLAINTS}/by-reference", params={"reference": "  sprpta-2026-000042 "})
    assert hit.status_code == 200
    assert hit.json() == {
        "id": draft.id, "reference_number": "SPRPTA-2026-000042", "status": "incomplete", "editable": True,
        "subject": "Another officer's case", "area_name": None, "forwarded_to": None, "forwarded_at": None,
    }


def test_a_forwarded_reference_says_where_it_went_and_cannot_be_edited(client, db, world):
    add(db, by=world.me, status=ComplaintStatus.FORWARDED, ref="SPRPTA-2026-000007", medium_id=world.medium.id,
        category_id=world.category.id, severity_id=world.severity.id, vehicle_id=world.bus.id, area_id=world.area.id,
        assigned_l2_user_id=world.officer.id, forwarded_at=NOW)
    body = client.get(f"{COMPLAINTS}/by-reference", params={"reference": "SPRPTA-2026-000007"}).json()
    assert (body["status"], body["editable"], body["forwarded_to"], body["area_name"]) == (
        "forwarded", False, "Ruwan Silva", "Galle",
    )


def test_an_unknown_or_empty_reference_is_refused(client, world):
    missing = client.get(f"{COMPLAINTS}/by-reference", params={"reference": "SPRPTA-2026-999999"})
    assert missing.status_code == 404 and missing.json()["detail"]["code"] == "reference_not_found"
    assert client.get(f"{COMPLAINTS}/by-reference", params={"reference": ""}).status_code == 422
    assert client.get(f"{COMPLAINTS}/by-reference").status_code == 422
