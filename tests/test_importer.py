from io import BytesIO
from openpyxl import Workbook
from datetime import date
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.database import Base
from app.models import Role, TrackerRecord, User, WorkLog
from app.services.importer import import_grid_data, normalize_status, parse_date, preview_import


def make_workbook():
    wb = Workbook()
    ws = wb.active
    ws.title = "DQ Task Tracker"
    ws.append([None, "Ticket ID", "Date Started", "Date Ended", "Tester", "DQ Status", "Zephyr Upload", "Comments"])
    ws.append([None, "DQ9001", "2026-01-01", None, "Narendar", "✅ Complete", None, "Done"])
    ft = wb.create_sheet("Daily Report - FT")
    ft.append(["TICKET ID", "TESTER", "TASK", "PRIORITY", "DATE", "work log (hrs)", "Passed - TC", "Passed - Steps", "Failed - TC", "Failed - Steps", "DAILY COMMENTS"])
    ft.append(["DQ9001", "Narendar", "Execution", "High", "2026-01-02", "2", "1", "12", "-", "-", "Executed"])
    output = BytesIO()
    wb.save(output)
    return output.getvalue()


def test_import_preview_accepts_valid_tracker_and_work_log_rows():
    result = preview_import(make_workbook())
    assert result["valid_rows"] == 2
    assert result["invalid_rows"] == 0
    assert set(result["sheets"]) == {"DQ Task Tracker", "Daily Report - FT"}


def test_ambiguous_slash_date_uses_workbook_month_day_order():
    assert parse_date("09/01/2026") == date(2026, 9, 1)


@pytest.mark.parametrize(("source", "expected"), [
    ("🏃 Estimation In progress", "Estimation In progress"),
    ("🏃 Design In progress", "Design In progress"),
    ("🏃 Execution In progress", "Execution In progress"),
    ("⚠️ Not started", "Not started"),
])
def test_normalize_status_preserves_active_workflow_stage(source, expected):
    assert normalize_status(source) == expected


@pytest.mark.parametrize("mode", ["merge", "replace"])
def test_import_links_worklog_to_tracker_case_insensitively(mode):
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        role = Role(name="Admin", description="Admin")
        db.add(role)
        db.flush()
        actor = User(email="admin@test.local", display_name="Admin", password_hash="hash", role_id=role.id, active=True)
        db.add(actor)
        db.commit()
        sheets = {
            "DQ Task Tracker": [
                ["Ticket ID", "Date Started", "Date Ended", "Tester", "DQ Status"],
                ["DQ9001", "2026-01-01", None, "Tester", "In progress"],
            ],
            "Daily Report - FT": [
                ["TICKET ID", "TESTER", "TASK", "PRIORITY", "DATE", "work log (hrs)"],
                ["dq9001", "Tester", "Execution", "High", "2026-01-02", 2],
            ],
        }

        import_grid_data(db, actor, "test", sheets, mode)

        tracker = db.query(TrackerRecord).filter(TrackerRecord.deleted_at.is_(None)).one()
        work_log = db.query(WorkLog).filter(WorkLog.deleted_at.is_(None)).one()
        assert work_log.tracker_record_id == tracker.id
