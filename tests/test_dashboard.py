from datetime import date

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