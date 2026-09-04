from io import BytesIO
from openpyxl import Workbook
from app.services.importer import preview_import


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
