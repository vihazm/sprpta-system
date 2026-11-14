import zipfile
from xml.sax.saxutils import escape

import pytest
from sqlalchemy import func, select

from app.core.enums import PersonType, PlaceKind, VehicleType
from app.models import Area, Permit, Person, RouteStand, Vehicle
from app.scripts import import_master_data as importer

PERMITS = [
    ["Permit No", "Bus No", "Office", "Route", "Origin", "Destination"],
    ["002108", "ND-7782", "GALLE", "24/1", "AVITHTAWA", "ELPITIYA"],
    ["002822", "nd-7980", "GALLE", "24/1", "AVITHTAWA", "ELPITIYA"],
    ["004251", "ND-7782", "GALLE", "297", "ELPITIYA", "GALLE"],  # the same bus on a second permit
    ["HM-353-6", "NB-3798", "MATARA", "353", "MATARA", "KOTAPOLA"],
    ["HM-353-6", "NB-8897", "MATARA", "353", "MATARA", "KOTAPOLA"],  # permit number already used
    ["003922", "", "GALLE", "350", "GALLE", "MATARA"],  # no bus number
    [],  # a blank row
]
PEOPLE_HEADER = ["Conductor Name", "Address 1", "Address 2", "Address 3", "City", "Mobile"]
CONDUCTORS = [
    PEOPLE_HEADER,
    ["S.M.L.KARUNARATNA", "NO.138", "", "", "ELPITIYA", "0771030757"],
    ["O.K.D.D.THARANGA", "GANEGODA", "", "", "GANEGODA", ""],
    ["O.K.D.D.THARANGA", "ELSEWHERE", "", "", "GALLE", ""],  # same name, no mobile: kept as a second person
    ["A.B.C.PERERA", "", "", "", "", "12345"],  # not a valid mobile number
]
DRIVERS = [["Driver Name", *PEOPLE_HEADER[1:]], ["K.I.ISHAN NILAKSHA", "", "", "", "", "771030999"]]


def build_workbook(path, sheets: dict[str, list[list[str]]]) -> str:
    """A minimal .xlsx with text cells only, like the one the client sent."""

    def cell(row: int, col: int, text: str) -> str:
        return f'<c r="{chr(65 + col)}{row}" t="inlineStr"><is><t>{escape(text)}</t></is></c>'

    with zipfile.ZipFile(path, "w") as book:
        names = list(sheets)
        book.writestr(
            "xl/workbook.xml",
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
            + "".join(f'<sheet name="{n}" sheetId="{i}" r:id="rId{i}"/>' for i, n in enumerate(names, 1))
            + "</sheets></workbook>",
        )
        book.writestr(
            "xl/_rels/workbook.xml.rels",
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            + "".join(
                f'<Relationship Id="rId{i}" Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(names) + 1)
            )
            + "</Relationships>",
        )
        for i, name in enumerate(names, 1):
            rows = "".join(
                f'<row r="{r}">' + "".join(cell(r, c, v) for c, v in enumerate(values) if v != "") + "</row>"
                for r, values in enumerate(sheets[name], 1)
                if values
            )
            book.writestr(
                f"xl/worksheets/sheet{i}.xml",
                f'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{rows}</sheetData></worksheet>',
            )
    return str(path)


@pytest.fixture
def areas(db):
    db.add_all([Area(name="Galle"), Area(name="Matara"), Area(name="Hambantota")])
    db.commit()


def run_import(db, path) -> importer.Report:
    sheets = importer.read_workbook(path)
    report = importer.Report()
    importer.import_permits(db, importer._data_rows(sheets, "Permits"), report)
    importer.import_people(db, importer._data_rows(sheets, "Conductors"), PersonType.CONDUCTOR, report)
    importer.import_people(db, importer._data_rows(sheets, "Drivers"), PersonType.DRIVER, report)
    db.commit()
    return report


@pytest.fixture
def workbook(tmp_path):
    return build_workbook(
        tmp_path / "data.xlsx", {"Permits": PERMITS, "Conductors": CONDUCTORS, "Drivers": DRIVERS}
    )


def count(db, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_the_workbook_is_stored_as_vehicles_permits_routes_and_people(db, areas, workbook):
    report = run_import(db, workbook)

    galle = db.scalar(select(Area).where(Area.name == "Galle"))
    bus = db.scalar(select(Vehicle).where(Vehicle.vehicle_number == "ND-7980"))  # typed in lower case
    assert (bus.vehicle_type, bus.registered_area_id, bus.owner_person_id) == (VehicleType.BUS, galle.id, None)
    assert count(db, Vehicle) == 4  # the bus on two permits is one vehicle; the row with no bus has none

    permits = {p.permit_number: p.vehicle_id for p in db.scalars(select(Permit))}
    assert permits["002108"] == permits["004251"]  # two permits, one vehicle
    assert set(permits) == {"002108", "002822", "004251", "HM-353-6"}

    route = db.scalar(select(RouteStand).where(RouteStand.name == "24/1 Avithtawa - Elpitiya"))
    assert (route.kind, route.area_id) == (PlaceKind.ROUTE, galle.id)
    assert count(db, RouteStand) == 4  # 24/1, 297, 353 and 350 (its permit has no bus, but the route is real)

    conductors = db.scalars(select(Person).where(Person.person_type == PersonType.CONDUCTOR)).all()
    phones = {p.full_name: p.phone for p in conductors if p.full_name == "S.M.L.KARUNARATNA"}
    assert phones == {"S.M.L.KARUNARATNA": "+94771030757"}
    assert len(conductors) == 4  # the two with the same name and no mobile are two people
    driver = db.scalar(select(Person).where(Person.person_type == PersonType.DRIVER))
    assert (driver.full_name, driver.phone) == ("K.I.ISHAN NILAKSHA", "+94771030999")  # a missing leading 0 is fine
    assert db.scalar(select(Person.phone).where(Person.full_name == "A.B.C.PERERA")) is None

    assert report.created["vehicles"] == 4 and report.created["permits"] == 4
    assert len(report.skipped) == 3
    text = "\n".join(report.skipped)
    assert "permit 003922 has no bus number" in text
    assert "permit HM-353-6 for NB-8897 not added" in text
    assert "'12345' is not valid" in text


def test_running_the_import_again_adds_nothing(db, areas, workbook):
    run_import(db, workbook)
    before = {m: count(db, m) for m in (Vehicle, Permit, RouteStand, Person)}

    again = run_import(db, workbook)

    assert {m: count(db, m) for m in (Vehicle, Permit, RouteStand, Person)} == before
    assert sum(again.created.values()) == 0
    assert again.existing["permits"] == 4 and again.existing["conductors"] == 4


def test_vehicles_already_in_the_database_are_kept_not_duplicated(db, areas, workbook):
    matara = db.scalar(select(Area).where(Area.name == "Matara"))
    db.add(Vehicle(vehicle_number="ND-7782", vehicle_type=VehicleType.BUS, registered_area_id=matara.id))
    db.commit()

    run_import(db, workbook)

    assert count(db, Vehicle) == 4
    kept = db.scalar(select(Vehicle).where(Vehicle.vehicle_number == "ND-7782"))
    assert kept.registered_area_id == matara.id  # what is already stored is left alone


def test_a_workbook_with_the_wrong_columns_is_refused(db, areas, tmp_path):
    bad = build_workbook(
        tmp_path / "bad.xlsx",
        {"Permits": [["Permit", "Bus"]], "Conductors": CONDUCTORS, "Drivers": DRIVERS},
    )
    with pytest.raises(SystemExit, match="Permits"):
        run_import(db, bad)
    assert count(db, Vehicle) == 0


def test_an_office_without_an_area_stops_the_import(db, areas, tmp_path):
    odd = [PERMITS[0], ["002108", "ND-7782", "COLOMBO", "24/1", "A", "B"]]
    path = build_workbook(tmp_path / "odd.xlsx", {"Permits": odd, "Conductors": CONDUCTORS, "Drivers": DRIVERS})
    with pytest.raises(SystemExit, match="COLOMBO"):
        run_import(db, path)


def test_without_areas_the_import_asks_for_the_seed(db, workbook):
    with pytest.raises(SystemExit, match="seed"):
        run_import(db, workbook)
