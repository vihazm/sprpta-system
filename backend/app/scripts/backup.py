"""Daily backup (F-66): a dump of the database and a zip of the evidence files.

There is no background worker, so the operating system's scheduler runs this once a day: cron on the Linux
server, Task Scheduler on Windows (see the README). Each run writes two files to BACKUP_DIR,

    sprpta-20261122-020000.dump        the database, for pg_restore
    sprpta-20261122-020000-files.zip   the evidence folder

and keeps only the newest BACKUP_KEEP runs. How the run went is saved in system_settings under
"backup.last_run", which the System health page and the administrator dashboard show. A failed run also exits
with status 1, so the scheduler reports it.

    cd backend
    .venv\\Scripts\\python -m app.scripts.backup
"""

import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.engine import URL, make_url

from app.core.config import settings
from app.core.timezone import LOCAL
from app.db.session import SessionLocal
from app.models import SystemSetting
from app.services.complaint_attachment_service import BACKEND_DIR, storage_root
from app.services.system_health_service import LAST_BACKUP_KEY

TIMEOUT_SECONDS = 2 * 60 * 60


def backup_root() -> Path:
    return BACKEND_DIR / settings.backup_dir  # an absolute backup_dir is used as it is


def _dump_database(target: Path) -> None:
    program = shutil.which(settings.pg_dump_path)
    if program is None:
        raise FileNotFoundError("pg_dump was not found. Set PG_DUMP_PATH in backend/.env to its full path.")
    url = make_url(settings.database_url)
    # The password goes in the environment, not on the command line where other users of the server could see it.
    env = {**os.environ, "PGPASSWORD": url.password or ""}
    address = URL.create("postgresql", username=url.username, host=url.host, port=url.port, database=url.database)
    subprocess.run(
        [program, "--format=custom", "--file", str(target), "--dbname", address.render_as_string()],
        env=env,
        check=True,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )


def _zip_evidence(target: Path) -> Path | None:
    folder = storage_root()
    if not folder.exists():
        return None  # nothing has been uploaded yet
    return Path(shutil.make_archive(str(target.with_suffix("")), "zip", folder))


def _prune(folder: Path) -> None:
    """Deletes all but the newest runs. The date and time in the names sort them."""
    dumps = sorted(folder.glob("sprpta-*.dump"))
    for old in dumps[: -settings.backup_keep]:
        old.unlink()
        old.with_name(f"{old.stem}-files.zip").unlink(missing_ok=True)


def _reason(exc: Exception) -> str:
    if isinstance(exc, subprocess.CalledProcessError):
        lines = (exc.stderr or "").strip().splitlines()
        return lines[-1] if lines else f"pg_dump stopped with status {exc.returncode}."
    if isinstance(exc, subprocess.TimeoutExpired):
        return "pg_dump did not finish within two hours."
    return str(exc)  # pg_dump missing, a full disk, a folder it may not write to, ...


def run() -> dict[str, Any]:
    """Makes one backup and returns how it went, in the form it is saved in."""
    folder = backup_root()
    stamp = datetime.now(LOCAL).strftime("%Y%m%d-%H%M%S")
    dump = folder / f"sprpta-{stamp}.dump"
    files = folder / f"sprpta-{stamp}-files.zip"
    try:
        folder.mkdir(parents=True, exist_ok=True)
        _dump_database(dump)
        zipped = _zip_evidence(files)
        size = dump.stat().st_size + (zipped.stat().st_size if zipped else 0)
        _prune(folder)
        result = {"succeeded": True, "file": dump.name, "size_bytes": size, "error": None}
    except (OSError, subprocess.SubprocessError) as exc:
        dump.unlink(missing_ok=True)  # never leave a half-written backup that looks complete
        files.unlink(missing_ok=True)
        result = {"succeeded": False, "file": None, "size_bytes": None, "error": _reason(exc)}
    return {**result, "finished_at": datetime.now(UTC).isoformat()}


def record(result: dict[str, Any]) -> None:
    with SessionLocal() as db:
        db.merge(SystemSetting(key=LAST_BACKUP_KEY, value=result, description="The last run of the backup script"))
        db.commit()


def main() -> None:
    result = run()
    record(result)
    if not result["succeeded"]:
        sys.exit(f"Backup failed: {result['error']}")
    print(f"Backed up to {backup_root() / result['file']} ({result['size_bytes']:,} bytes).")


if __name__ == "__main__":
    main()
