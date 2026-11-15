"""Command line for the synthetic data generator.

    python -m app.synthetic plan     --scale small    what would be created, with a route coverage report (writes nothing)
    python -m app.synthetic dry-run  --scale small    the same, plus what is already in the database
    python -m app.synthetic seed     --scale small --confirm
    python -m app.synthetic validate --scale small    data-quality checks on what is in the database
    python -m app.synthetic report   --scale small    statistics of what is in the database
    python -m app.synthetic bench    --scale small    timings and index use of the lookup, lists and dashboard
    python -m app.synthetic cleanup  --scale small --confirm   delete exactly what that batch created

Development only: it refuses to run unless APP_ENV=development and the database is on this computer.
"""

import argparse
import json
import sys
import time
from urllib.parse import urlparse

from sqlalchemy import func, select, text

from app.core.config import settings
from app.db.session import SessionLocal
from app.models import Complaint, DailyTrip, SyntheticBatch
from app.scripts.seed_dev_complaints import check_environment
from app.synthetic import bench, pipeline, validate, writer
from app.synthetic.config import SCALES, load


def _database() -> str:
    return urlparse(settings.database_url.replace("+psycopg", "")).path.lstrip("/")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.synthetic", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["plan", "dry-run", "seed", "validate", "report", "bench", "cleanup"])
    parser.add_argument("--scale", choices=SCALES, default="small")
    parser.add_argument("--config", default=None, help="a different configuration file")
    parser.add_argument("--out", default="synthetic_report.json", help="where plan and dry-run write the report")
    parser.add_argument("--confirm", action="store_true", help="really write to or delete from the database")
    args = parser.parse_args(argv)

    check_environment()
    cfg = load(args.scale, args.config)
    print(f"Database: {_database()} (development) · batch {cfg.batch_name}\n")

    with SessionLocal() as db:
        batch = db.scalar(select(SyntheticBatch).where(SyntheticBatch.name == cfg.batch_name))

        if args.command in ("plan", "dry-run", "seed"):
            started = time.time()
            plan = pipeline.build_plan(db, cfg, n_officers=int(cfg.section("general")["synthetic_officers"]) + 1)
            report = plan.report()
            print("\n".join(pipeline.summary_lines(report)))
            print(f"  (planned in {time.time() - started:.0f}s)")
            if args.command in ("plan", "dry-run"):
                pipeline.write_report(report, args.out)
                print(f"\nRoute coverage report written to {args.out}")
                if args.command == "dry-run":
                    have_trips = db.scalar(select(func.count()).select_from(DailyTrip).where(
                        DailyTrip.synthetic_batch_id == (batch.id if batch else -1)))
                    have_complaints = db.scalar(select(func.count()).select_from(Complaint).where(
                        Complaint.synthetic_batch_id == (batch.id if batch else -1)))
                    print(f"Already in the database for this batch: {have_trips} trips, {have_complaints} complaints")
                print("\nNothing was written.")
                return 0
            if not args.confirm:
                print("\nNothing was written. Add --confirm to create it.")
                return 0
            print("\nWriting…")
            writer.seed(db, plan)
            batch = db.scalar(select(SyntheticBatch).where(SyntheticBatch.name == cfg.batch_name))
            print(f"\nDone in {time.time() - started:.0f}s. Run `validate` next.")
            return 0

        if batch is None:
            print("There is no data for this batch.")
            return 1

        if args.command == "validate":
            results = validate.run_checks(db, batch.id)
            for r in results:
                print(f"  {'PASS' if r['ok'] else 'FAIL'}  {r['check']}" + ("" if r["ok"] else f"  ({r['violations']} rows)"))
            failed = [r for r in results if not r["ok"]]
            print(f"\n{len(results) - len(failed)} of {len(results)} checks passed.")
            return 1 if failed else 0

        if args.command == "report":
            print(json.dumps(validate.statistics(db, batch.id), indent=2, default=str))
            return 0

        if args.command == "bench":
            results = bench.run(db, cfg.batch_name)
            for r in results[:-1]:
                print(f"  {'PASS' if r['ok'] else 'SLOW'}  {r['name']}: median {r['median_ms']} ms, worst {r['worst_ms']} ms (target {r['target_ms']} ms)")
            print("\n  Query plans:")
            for name, plan in results[-1]["plans"].items():
                print(f"    {name}: {plan}")
            return 0 if all(r["ok"] for r in results[:-1]) else 1

        if args.command == "cleanup":
            if not args.confirm:
                trips = db.scalar(select(func.count()).select_from(DailyTrip).where(DailyTrip.synthetic_batch_id == batch.id))
                complaints = db.scalar(select(func.count()).select_from(Complaint).where(Complaint.synthetic_batch_id == batch.id))
                print(f"Would delete {trips} trips, {complaints} complaints and the rest of this batch. Add --confirm to do it.")
                return 0
            writer.cleanup(db, cfg.batch_name)
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
