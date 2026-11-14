"""Load the client's vehicle, permit, driver and conductor data from their workbook. Safe to run repeatedly.

    cd backend
    .venv\\Scripts\\python -m app.scripts.import_master_data "C:\\path\\to\\Permit_Conductor_Driver_Separate.xlsx"

Run the seed first (it creates the three areas). The workbook has three sheets:

- Permits (Permit No, Bus No, Office, Route, Origin, Destination): becomes a vehicle (bus number, registered
  in the office's area), its permit (DB doc 2.7) and a route for that area (DB doc 2.5). A permit is not linked
  to its route: the permits table has no column for it.
- Conductors and Drivers (Conductor/Driver Name, three address lines, City, Mobile): become people (DB doc 2.8). The mobile
  number is stored as +94...; the address has no column and is not stored.

Rows that cannot be stored are skipped and listed at the end: a permit with no bus number (a permit needs a
vehicle) and a permit number that an earlier row already uses (permit numbers are unique). The workbook holds
personal data, so it is never kept in the repository: pass its path each time.

Reading the .xlsx uses only the standard library, so no new package is needed.
"""

import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import PersonType, PlaceKind, VehicleType
from app.core.identifiers import normalise_identifier
from app.db.session import SessionLocal
from app.models import Area, Permit, Person, RouteStand, Vehicle

PERMIT_HEADER = ["Permit No", "Bus No", "Office", "Route", "Origin", "Destination"]
ADDRESS_AND_MOBILE = ["Address 1", "Address 2", "Address 3", "City", "Mobile"]
SHEETS = {
    "Permits": PERMIT_HEADER,
    "Conductors": ["Conductor Name", *ADDRESS_AND_MOBILE],
    "Drivers": ["Driver Name", *ADDRESS_AND_MOBILE],
}

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"


# ---------------------------------------------------------------- reading the workbook


def _column(cell_ref: str) -> int:
    index = 0
    for letter in re.match(r"[A-Z]+", cell_ref).group():
        index = index * 26 + ord(letter) - 64
    return index - 1


def read_workbook(path: str) -> dict[str, list[list[str]]]:
    """Every sheet as a list of rows of text, header row included."""
    book = zipfile.ZipFile(path)
    shared = []
    if "xl/sharedStrings.xml" in book.namelist():
        for item in ET.fromstring(book.read("xl/sharedStrings.xml")).findall(f"{_NS}si"):
            shared.append("".join(t.text or "" for t in item.iter(f"{_NS}t")))

    links = {r.get("Id"): r.get("Target") for r in ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))}
    sheets: dict[str, list[list[str]]] = {}
    for sheet in ET.fromstring(book.read("xl/workbook.xml")).find(f"{_NS}sheets"):
        target = links[sheet.get(f"{_REL}id")].lstrip("/")
        rows = []
        for row in ET.fromstring(book.read(target if target.startswith("xl/") else f"xl/{target}")).iter(f"{_NS}row"):
            cells: dict[int, str] = {}
            for cell in row.findall(f"{_NS}c"):
                value = cell.find(f"{_NS}v")
                if cell.get("t") == "inlineStr":
                    cells[_column(cell.get("r"))] = "".join(t.text or "" for t in cell.iter(f"{_NS}t"))
                elif value is not None:
                    text = value.text or ""
                    cells[_column(cell.get("r"))] = shared[int(text)] if cell.get("t") == "s" else text
            rows.append([cells.get(i, "") for i in range(max(cells) + 1)] if cells else [])
        sheets[sheet.get("name")] = rows
    return sheets


def _data_rows(sheets: dict[str, list[list[str]]], name: str) -> list[list[str]]:
    """The rows under the header, each padded to the width of the header and with blank rows dropped."""
    header = SHEETS[name]
    if name not in sheets or [c.strip() for c in sheets[name][0][: len(header)]] != header:
        raise SystemExit(f'The "{name}" sheet is missing or its columns are not: {", ".join(header)}')
    rows = [r + [""] * (len(header) - len(r)) for r in sheets[name][1:]]
    return [[c.strip() for c in r[: len(header)]] for r in rows if any(c.strip() for c in r)]


# ---------------------------------------------------------------- cleaning


def _words(text: str) -> str:
    return " ".join(text.split())


def _vehicle_number(raw: str) -> str:
    return _words(raw).upper()


def _route_name(number: str, origin: str, destination: str) -> str:
    return f"{number} {_words(origin).title()} - {_words(destination).title()}"


def _mobile(raw: str) -> str | None:
    parsed = normalise_identifier(raw) if raw else None
    return parsed[1] if parsed and parsed[0] == "phone" else None


# ---------------------------------------------------------------- importing


@dataclass
class Report:
    created: Counter = field(default_factory=Counter)
    existing: Counter = field(default_factory=Counter)
    skipped: list[str] = field(default_factory=list)


def _areas(db: Session) -> dict[str, int]:
    areas = {a.name.upper(): a.id for a in db.scalars(select(Area))}
    if not areas:
        raise SystemExit("There are no areas yet. Run the seed first: python -m app.scripts.seed")
    return areas


def import_permits(db: Session, rows: list[list[str]], report: Report) -> None:
    areas = _areas(db)
    vehicles = {v.vehicle_number: v for v in db.scalars(select(Vehicle))}
    permit_owner = {number: vehicle_id for number, vehicle_id in db.execute(select(Permit.permit_number, Permit.vehicle_id))}
    seen: set[str] = set()  # permit numbers met so far in this file
    places = {(p.name, p.area_id) for p in db.scalars(select(RouteStand).where(RouteStand.kind == PlaceKind.ROUTE))}

    for line, (permit_no, bus, office, route, origin, destination) in enumerate(rows, start=2):
        area_id = areas.get(office.upper())
        if area_id is None:
            raise SystemExit(f'Permits row {line}: there is no area called "{office}". Run the seed, or check the office.')

        name = _route_name(route, origin, destination)
        if (name, area_id) not in places:
            db.add(RouteStand(kind=PlaceKind.ROUTE, name=name, area_id=area_id))
            places.add((name, area_id))
            report.created["routes"] += 1

        number = _vehicle_number(bus)
        if not number:
            report.skipped.append(f"Permits row {line}: permit {permit_no} has no bus number, so it has no vehicle")
            continue
        vehicle = vehicles.get(number)
        if vehicle is None:
            vehicle = Vehicle(vehicle_number=number, vehicle_type=VehicleType.BUS, registered_area_id=area_id)
            db.add(vehicle)
            db.flush()
            vehicles[number] = vehicle
            report.created["vehicles"] += 1
        else:
            report.existing["vehicles"] += 1

        if permit_no in seen:
            report.skipped.append(
                f"Permits row {line}: permit {permit_no} for {number} not added, "
                "because that permit number is already used by another row"
            )
            continue
        seen.add(permit_no)
        if permit_no not in permit_owner:
            db.add(Permit(permit_number=permit_no, vehicle_id=vehicle.id))
            permit_owner[permit_no] = vehicle.id
            report.created["permits"] += 1
        elif permit_owner[permit_no] == vehicle.id:
            report.existing["permits"] += 1  # stored by an earlier run
        else:
            report.skipped.append(
                f"Permits row {line}: permit {permit_no} for {number} not added, "
                "because that permit number is already stored for another vehicle"
            )

def import_people(db: Session, rows: list[list[str]], person_type: PersonType, report: Report) -> None:
    """People have no unique key, so two rows with the same name and mobile are kept as two people,
    and a repeat run only adds the rows that are not stored yet."""
    label = f"{person_type.value}s"
    stored = Counter(
        (p.full_name, p.phone)
        for p in db.scalars(select(Person).where(Person.person_type == person_type))
    )
    wanted = Counter()
    for line, (name, *_address, mobile) in enumerate(rows, start=2):
        name = _words(name)
        phone = _mobile(mobile)
        if mobile and phone is None:
            report.skipped.append(f"{label.capitalize()} row {line}: mobile number {mobile!r} is not valid, saved without it")
        key = (name, phone)
        wanted[key] += 1
        if wanted[key] > stored[key]:
            db.add(Person(full_name=name, person_type=person_type, phone=phone))
            report.created[label] += 1
        else:
            report.existing[label] += 1


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('Usage: python -m app.scripts.import_master_data "path\\to\\workbook.xlsx"')
    sheets = read_workbook(sys.argv[1])
    report = Report()
    with SessionLocal() as db:
        import_permits(db, _data_rows(sheets, "Permits"), report)
        import_people(db, _data_rows(sheets, "Conductors"), PersonType.CONDUCTOR, report)
        import_people(db, _data_rows(sheets, "Drivers"), PersonType.DRIVER, report)
        db.commit()

    for what in ("vehicles", "permits", "routes", "conductors", "drivers"):
        print(f"  {what:<11} added {report.created[what]:>5}   already there {report.existing[what]:>5}")
    if report.skipped:
        print(f"\nNot stored as given ({len(report.skipped)}):")
        for line in report.skipped:
            print(f"  {line}")
    print("Done.")


if __name__ == "__main__":
    main()
