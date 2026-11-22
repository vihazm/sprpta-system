import subprocess

import pytest

from app.core.config import settings
from app.core.roles import UserRole
from app.models import SystemSetting
from app.scripts import backup
from app.services.system_health_service import LAST_BACKUP_KEY
from tests.conftest import make_user, sign_in


@pytest.fixture
def folders(tmp_path, monkeypatch):
    """Backups and uploads in a temporary folder, and pg_dump replaced by a stand-in that writes a small file."""
    monkeypatch.setattr(settings, "backup_dir", str(tmp_path / "backups"))
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    monkeypatch.setattr(backup.shutil, "which", lambda program: program)
    calls = []

    def fake_pg_dump(command, **options):
        calls.append((command, options))
        target = command[command.index("--file") + 1]
        with open(target, "wb") as dump:
            dump.write(b"PGDMP" + b"0" * 95)

    monkeypatch.setattr(backup.subprocess, "run", fake_pg_dump)
    return tmp_path, calls


def test_a_backup_dumps_the_database_and_zips_the_evidence_files(folders, db):
    tmp, calls = folders
    (tmp / "uploads" / "17").mkdir(parents=True)
    (tmp / "uploads" / "17" / "photo.jpg").write_bytes(b"x" * 400)

    result = backup.run()
    assert result["succeeded"] and result["error"] is None
    files = {p.name for p in (tmp / "backups").iterdir()}
    assert files == {result["file"], result["file"].replace(".dump", "-files.zip")}
    assert result["size_bytes"] > 100

    [(command, options)] = calls
    assert command[1] == "--format=custom"
    # The password reaches pg_dump through the environment, never on its command line.
    password = db.get_bind().url.password
    assert password and all(password not in part for part in command)
    assert options["env"]["PGPASSWORD"] == password


def test_only_the_newest_backups_are_kept(folders, monkeypatch):
    tmp, _ = folders
    monkeypatch.setattr(settings, "backup_keep", 2)
    old = tmp / "backups"
    old.mkdir()
    for stamp in ("20260101-020000", "20260102-020000"):
        (old / f"sprpta-{stamp}.dump").write_bytes(b"old")
        (old / f"sprpta-{stamp}-files.zip").write_bytes(b"old")

    result = backup.run()
    kept = sorted(p.name for p in old.iterdir())
    assert kept == ["sprpta-20260102-020000-files.zip", "sprpta-20260102-020000.dump", result["file"]]


def test_a_failed_dump_leaves_no_file_and_gives_pg_dumps_reason(folders, monkeypatch):
    tmp, _ = folders

    def refused(command, **options):
        open(command[command.index("--file") + 1], "wb").close()  # pg_dump may leave a partial file behind
        raise subprocess.CalledProcessError(1, command, stderr="pg_dump: error: connection failed\nFATAL: too many\n")

    monkeypatch.setattr(backup.subprocess, "run", refused)
    result = backup.run()
    assert (result["succeeded"], result["error"], result["file"]) == (False, "FATAL: too many", None)
    assert list((tmp / "backups").iterdir()) == []


def test_a_missing_pg_dump_is_explained(folders, monkeypatch):
    monkeypatch.setattr(backup.shutil, "which", lambda program: None)
    result = backup.run()
    assert not result["succeeded"]
    assert "Set PG_DUMP_PATH" in result["error"]


def test_the_result_is_recorded_and_shown_on_system_health(folders, client, db):
    backup.record(backup.run())
    setting = db.get(SystemSetting, LAST_BACKUP_KEY)
    assert setting.value["succeeded"] is True

    make_user(db, "admin@sprpta.test", UserRole.ADMIN)
    sign_in(client, "admin@sprpta.test")
    shown = client.get("/api/admin/system-health").json()["last_backup"]
    assert shown["succeeded"] is True and shown["stale"] is False and shown["size_bytes"] > 0


def test_the_script_exits_with_an_error_when_the_backup_fails(folders, monkeypatch):
    monkeypatch.setattr(backup.shutil, "which", lambda program: None)
    with pytest.raises(SystemExit) as exit_:
        backup.main()
    assert "Backup failed" in str(exit_.value.code)
