"""Deleting a complaint, evidence files, and finding a vehicle while typing (portal)."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.enums import ComplaintStatus, VehicleType
from app.core.roles import UserRole
from app.models import AuditLog, Complaint, ComplaintAttachment, Vehicle
from tests.conftest import make_complainant, make_user, sign_in
from tests.test_portal_complaints import URL, form, world  # noqa: F401  (world is a fixture)

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def lodge(client, w, **changes) -> int:
    return client.post(URL, json=form(w, **changes)).json()["id"]


def start_work_on(db, cid: int) -> None:
    """Level 1 has begun on it: the complainant can no longer change or delete it."""
    c = db.get(Complaint, cid)
    c.status = ComplaintStatus.INCOMPLETE
    c.reference_number = f"SPRPTA-2026-{cid:06d}"
    db.commit()


# ---------------------------------------------------------------- deleting a complaint


def test_deleting_keeps_the_record_and_hides_it_everywhere(client, db, world):
    cid = lodge(client, world)
    assert client.get(f"{URL}/{cid}").json()["can_delete"] is True
    assert client.delete(f"{URL}/{cid}").status_code == 204

    db.expire_all()
    row = db.get(Complaint, cid)
    assert row is not None and row.withdrawn_at is not None and row.status == ComplaintStatus.SUBMITTED
    audit = db.scalar(select(AuditLog).where(AuditLog.action == "complaint.withdraw_portal"))
    assert audit.complaint_id == cid and audit.actor_account_id == world.account.id

    assert client.get(URL).json() == []
    assert client.get(f"{URL}/{cid}").status_code == 404
    assert client.delete(f"{URL}/{cid}").status_code == 404

    make_user(db, "office@sprpta.test", UserRole.L1)
    sign_in(client, "office@sprpta.test")
    assert client.get("/api/l1/dashboard").json()["queues"]["portal"] == 0
    assert client.get("/api/l1/dashboard").json()["portal"] == []


def test_a_complaint_cannot_be_deleted_once_sprpta_has_started_on_it(client, db, world):
    cid = lodge(client, world)
    start_work_on(db, cid)
    assert client.get(f"{URL}/{cid}").json()["can_delete"] is False
    r = client.delete(f"{URL}/{cid}")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "already_checked"
    assert db.get(Complaint, cid).withdrawn_at is None


def test_someone_elses_complaint_cannot_be_deleted(client, db, world):
    other = make_complainant(db, "other@sprpta.test")
    theirs = Complaint(status=ComplaintStatus.SUBMITTED, complainant_account_id=other.id, subject="Not mine")
    db.add(theirs)
    db.commit()
    assert client.delete(f"{URL}/{theirs.id}").status_code == 404
    db.refresh(theirs)
    assert theirs.withdrawn_at is None


def test_the_database_refuses_a_withdrawn_complaint_that_is_past_the_first_check(db, world):
    db.add(
        Complaint(
            status=ComplaintStatus.INCOMPLETE,
            reference_number="SPRPTA-2026-000009",
            withdrawn_at=datetime.now(UTC),
            complainant_account_id=world.account.id,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


# ---------------------------------------------------------------- files


@pytest.fixture
def uploads(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    return tmp_path


def upload(client, cid, name="photo.png", content=PNG, mime="image/png"):
    return client.post(f"{URL}/{cid}/attachments", files={"file": (name, content, mime)})


def test_a_file_can_be_added_listed_and_opened(client, world, uploads):
    cid = lodge(client, world)
    r = upload(client, cid)
    assert r.status_code == 201 and r.json()["file_name"] == "photo.png" and r.json()["size_bytes"] == len(PNG)

    shown = client.get(f"{URL}/{cid}").json()["attachments"]
    assert [a["file_name"] for a in shown] == ["photo.png"]

    opened = client.get(f"{URL}/{cid}/attachments/{shown[0]['id']}/file")
    assert opened.status_code == 200 and opened.content == PNG
    assert opened.headers["content-type"] == "image/png"
    assert opened.headers["x-content-type-options"] == "nosniff"
    assert "inline" in opened.headers["content-disposition"]


def test_a_pdf_and_other_allowed_kinds_are_accepted(client, world, uploads):
    cid = lodge(client, world)
    assert upload(client, cid, "bill.pdf", b"%PDF-1.4 test", "application/pdf").status_code == 201
    assert upload(client, cid, "note.txt", b"plain words", "text/plain").status_code == 201


def test_a_dangerous_or_disguised_file_is_refused(client, world, uploads):
    cid = lodge(client, world)
    exe = upload(client, cid, "run.exe", b"MZ....", "application/x-msdownload")
    assert exe.status_code == 415 and exe.json()["detail"]["code"] == "file_type_not_allowed"
    assert upload(client, cid, "page.html", b"<script>alert(1)</script>", "text/html").status_code == 415
    fake = upload(client, cid, "photo.png", b"this is not a png", "image/png")
    assert fake.status_code == 415 and fake.json()["detail"]["code"] == "file_type_mismatch"
    assert upload(client, cid, "empty.png", b"", "image/png").status_code in (415, 422)
    assert client.get(f"{URL}/{cid}").json()["attachments"] == []


def test_only_the_owner_can_open_add_or_remove_a_file(client, db, world, uploads):
    cid = lodge(client, world)
    fid = upload(client, cid).json()["id"]
    make_complainant(db, "other@sprpta.test")
    client.post("/api/auth/logout")
    assert sign_in(client, "other@sprpta.test").status_code == 200
    assert client.get(f"{URL}/{cid}/attachments/{fid}/file").status_code == 404
    assert upload(client, cid).status_code == 404
    assert client.delete(f"{URL}/{cid}/attachments/{fid}").status_code == 404


def test_a_file_can_be_removed_but_the_record_of_it_stays(client, db, world, uploads):
    cid = lodge(client, world)
    fid = upload(client, cid).json()["id"]
    assert client.delete(f"{URL}/{cid}/attachments/{fid}").status_code == 204
    assert client.get(f"{URL}/{cid}").json()["attachments"] == []
    assert client.get(f"{URL}/{cid}/attachments/{fid}/file").status_code == 404
    row = db.get(ComplaintAttachment, fid)
    assert row.removed_at is not None and row.uploaded_by_account_id == world.account.id
    assert row.uploaded_by_user_id is None


def test_files_cannot_be_changed_after_sprpta_has_started_on_the_complaint(client, db, world, uploads):
    cid = lodge(client, world)
    fid = upload(client, cid).json()["id"]
    start_work_on(db, cid)
    assert upload(client, cid).status_code == 409
    assert client.delete(f"{URL}/{cid}/attachments/{fid}").status_code == 409
    assert client.get(f"{URL}/{cid}/attachments/{fid}/file").status_code == 200  # still viewable


def test_a_deleted_complaints_files_stay_stored_but_cannot_be_opened(client, db, world, uploads):
    cid = lodge(client, world)
    fid = upload(client, cid).json()["id"]
    client.delete(f"{URL}/{cid}")
    assert client.get(f"{URL}/{cid}/attachments/{fid}/file").status_code == 404
    assert db.get(ComplaintAttachment, fid).removed_at is None


# ---------------------------------------------------------------- finding a vehicle while typing


@pytest.fixture
def fleet(db, world):
    db.add_all(
        [
            Vehicle(vehicle_number="SP NB-2345", vehicle_type=VehicleType.BUS, registered_area_id=world.area.id),
            Vehicle(vehicle_number="SP NB-2399", vehicle_type=VehicleType.BUS, registered_area_id=world.area.id),
            Vehicle(vehicle_number="SP TW-1000", vehicle_type=VehicleType.TRISHAW, registered_area_id=world.matara.id),
            Vehicle(
                vehicle_number="SP NB-9999", vehicle_type=VehicleType.BUS, registered_area_id=world.area.id, is_active=False
            ),
        ]
    )
    db.commit()


def suggested(client, q):
    return [v["vehicle_number"] for v in client.get(f"{URL}/lookup/vehicles", params={"q": q}).json()]


def test_vehicle_numbers_are_offered_by_their_first_letters(client, fleet):
    assert suggested(client, "sp n") == ["SP NB-2345", "SP NB-2399"]
    assert suggested(client, "spnb-23") == ["SP NB-2345", "SP NB-2399"]
    assert suggested(client, "SP NB-2345") == ["SP NB-2345"]
    assert suggested(client, "sp t") == ["SP TW-1000"]
    assert suggested(client, "S") == ["SP NB-2345", "SP NB-2399", "SP TW-1000"]


def test_a_suggestion_carries_the_area_and_leaves_out_inactive_vehicles(client, fleet):
    found = client.get(f"{URL}/lookup/vehicles", params={"q": "sp tw"}).json()
    assert len(found) == 1 and found[0]["area_name"] == "Matara" and found[0]["vehicle_type"] == "trishaw"
    assert suggested(client, "sp nb-99") == []


@pytest.mark.parametrize("q", ["", "   ", "%", "_", "zzz"])
def test_nothing_or_no_match_gives_an_empty_list(client, fleet, q):
    assert suggested(client, q) == []


def test_suggestions_are_for_portal_users_only(client, db, fleet):
    client.post("/api/auth/logout")
    assert client.get(f"{URL}/lookup/vehicles", params={"q": "sp"}).status_code == 401
    make_user(db, "office@sprpta.test", UserRole.L1)
    sign_in(client, "office@sprpta.test")
    assert client.get(f"{URL}/lookup/vehicles", params={"q": "sp"}).status_code == 403
