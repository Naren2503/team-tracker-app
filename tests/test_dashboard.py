from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import TrackerRecord, WorkLog
from app.services.dashboard import dashboard_metrics


def test_monthly_report_uses_ft_activity_dates_and_dq_end_date():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        record = TrackerRecord(
            ticket_id="DQ9001",
            date_started=date(2025, 12, 1),
            date_ended=date(2026, 2, 20),
            tester_name_raw="DQ Tester",
            status="Completed",
        )
        db.add(record)
        db.flush()
        db.add_all([
            WorkLog(
                tracker_record_id=None,
                ticket_id_raw=" dq9001 ",
                workstream="FT",
                tester_name_raw="FT Tester",
                work_date=date(2026, 1, 25),
                work_log_hours=2,
                source_sheet="Daily Report - FT",
            ),
            WorkLog(
                tracker_record_id=None,
                ticket_id_raw=record.ticket_id,
                workstream="FT",
                tester_name_raw="FT Tester",
                work_date=date(2026, 2, 10),
                work_log_hours=3,
                source_sheet="Daily Report - FT",
            ),
            WorkLog(
                tracker_record_id=record.id,
                ticket_id_raw=record.ticket_id,
                workstream="BT",
                tester_name_raw="BT Tester",
                work_date=date(2026, 2, 11),
                work_log_hours=8,
                source_sheet="Daily Report - BT",
            ),
        ])
        db.commit()

        metrics = dashboard_metrics(
            db,
            start=date(2026, 2, 1),
            end=date(2026, 2, 28),
            report_view="monthly",
        )

    assert metrics["total_records"] == 1
    assert metrics["total_hours"] == 3
    assert metrics["total_testers"] == 1
    assert metrics["ticket_ageing"][0]["tester"] == "FT Tester"
    assert metrics["ticket_ageing"][0]["logged_hours"] == 3
    assert metrics["ticket_ageing"][0]["start_date"] == "2026-01-25"
    assert metrics["ticket_ageing"][0]["end_date"] == "2026-02-20"
    assert metrics["ticket_ageing"][0]["age_days"] == 26


def test_week_filter_defaults_to_all_ft_logs_in_selected_month():
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        record = TrackerRecord(ticket_id="DQ9002", status="In progress")
        db.add(record)
        db.flush()
        db.add_all([
            WorkLog(
                tracker_record_id=record.id,
                ticket_id_raw=record.ticket_id,
                workstream="FT",
                work_date=date(2026, 2, 2),
                work_log_hours=1,
                source_sheet="Daily Report - FT",
            ),
            WorkLog(
                tracker_record_id=record.id,
                ticket_id_raw=record.ticket_id,
                workstream="FT",
                work_date=date(2026, 2, 23),
                work_log_hours=4,
                source_sheet="Daily Report - FT",
            ),
        ])
        db.commit()

        metrics = dashboard_metrics(
            db,
            start=date(2026, 2, 1),
            end=date(2026, 2, 28),
            granularity="week",
            report_view="weekly",
        )

    assert metrics["total_hours"] == 5
    assert set(metrics["trend"]) == {"Week 1", "Week 4"}


@pytest.mark.parametrize(("category", "expected_tickets"), [
    ("dq", {"DQ-100"}),
    ("bt", {"HYDRAS-100", "THESTRALS-100", "CIMDB-100", "CIMBT-100"}),
    ("others", {"MISC-100"}),
    ("all", {"DQ-100", "HYDRAS-100", "THESTRALS-100", "CIMDB-100", "CIMBT-100", "MISC-100"}),
])
def test_monthly_ticket_category_filters_cards_details_and_history(category, expected_tickets):
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        ticket_ids = ["DQ-100", "HYDRAS-100", "THESTRALS-100", "CIMDB-100", "CIMBT-100", "MISC-100"]
        records = [TrackerRecord(ticket_id=ticket_id, status="Completed") for ticket_id in ticket_ids]
        db.add_all(records)
        db.flush()
        db.add_all([
            WorkLog(
                tracker_record_id=record.id,
                ticket_id_raw=record.ticket_id.lower(),
                workstream="FT",
                work_date=date(2026, 1, 10),
                work_log_hours=1,
                passed_tc=1,
                source_sheet="Daily Report - FT",
            )
            for record in records
        ])
        db.commit()

        metrics = dashboard_metrics(
            db,
            start=date(2026, 1, 1),
            end=date(2026, 1, 31),
            report_view="monthly",
            ticket_category=category,
        )

    assert metrics["total_records"] == len(expected_tickets)
    assert metrics["total_hours"] == len(expected_tickets)
    assert metrics["passed_tc"] == len(expected_tickets)
    assert {ticket["ticket_id"] for ticket in metrics["ticket_ageing"]} == expected_tickets
    assert metrics["history_trend"]["2026-01"]["tickets"] == len(expected_tickets)


def test_monthly_others_details_include_ft_ticket_without_dq_record():
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        db.add_all([
            WorkLog(
                ticket_id_raw="SUPPORT-42",
                workstream="FT",
                tester_name_raw="FT Tester",
                work_date=date(2025, 12, 20),
                daily_comments="Started investigation",
                source_sheet="Daily Report - FT",
            ),
            WorkLog(
                ticket_id_raw="SUPPORT-42",
                workstream="FT",
                tester_name_raw="FT Tester",
                work_date=date(2026, 1, 12),
                work_log_hours=3,
                daily_comments="Completed analysis",
                source_sheet="Daily Report - FT",
            ),
        ])
        db.commit()

        metrics = dashboard_metrics(
            db,
            start=date(2026, 1, 1),
            end=date(2026, 1, 31),
            report_view="monthly",
            ticket_category="others",
        )

    assert metrics["total_records"] == 1
    assert metrics["ticket_ageing"] == [{
        "ticket_id": "SUPPORT-42",
        "status": "Not available",
        "tester": "FT Tester",
        "logged_hours": 3,
        "start_date": "2026-01-12",
        "end_date": None,
        "date_warning": None,
        "comments": "Completed analysis",
        "age_days": None,
    }]


def test_lifecycle_trend_includes_created_and_resolved_ticket_names_for_hover_tooltips():
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        db.add_all([
            TrackerRecord(ticket_id="DQ-ACTIVE", date_started=date(2026, 1, 5), status="In progress"),
            TrackerRecord(ticket_id="DQ-DONE", date_started=date(2026, 1, 8), date_ended=date(2026, 2, 2), status="Completed"),
        ])
        db.commit()

        metrics = dashboard_metrics(db, start=date(2026, 1, 1), end=date(2026, 2, 28))

    january = metrics["lifecycle_trend"]["2026-01"]
    february = metrics["lifecycle_trend"]["2026-02"]
    assert january["created_tickets"] == ["DQ-ACTIVE", "DQ-DONE"]
    assert february["resolved_tickets"] == ["DQ-DONE"]
    assert "backlog" not in january


@pytest.mark.parametrize(("start_date", "expected_age"), [
    (date(2026, 8, 14), 18),
    (date(2026, 8, 27), 5),
])
def test_report_corrects_legacy_month_day_swap_before_calculating_age(start_date, expected_age):
    engine = create_engine("sqlite:///:memory:", poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as db:
        record = TrackerRecord(
            ticket_id="HYDRAS_345",
            date_ended=date(2026, 1, 9),
            status="Completed",
        )
        db.add(record)
        db.flush()
        db.add(WorkLog(
            tracker_record_id=record.id,
            ticket_id_raw=record.ticket_id,
            workstream="FT",
            work_date=start_date,
            source_sheet="Daily Report - FT",
        ))
        db.commit()

        metrics = dashboard_metrics(
            db,
            start=date(2026, 8, 1),
            end=date(2026, 8, 31),
            report_view="monthly",
        )

    ticket = metrics["ticket_ageing"][0]
    assert ticket["end_date"] == "2026-09-01"
    assert ticket["age_days"] == expected_age
    assert ticket["date_warning"] is not None