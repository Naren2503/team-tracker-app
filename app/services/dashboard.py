from calendar import monthrange
from datetime import date, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import TrackerRecord, WorkLog


def dashboard_metrics(db: Session, start: date | None = None, end: date | None = None, tester: str | None = None, status: str | None = None, granularity: str = "month", week: int | None = None) -> dict:
    if start is None and end is None and granularity == "month":
        current_month = date.today().replace(day=1)
        start = (current_month - timedelta(days=5 * 31)).replace(day=1)
        end = date.today()
    if week and start and granularity == "week":
        week_start = start.replace(day=(week - 1) * 7 + 1)
        week_end = start.replace(day=min(week * 7, monthrange(start.year, start.month)[1]))
        start, end = week_start, week_end
    tracker = select(TrackerRecord).where(TrackerRecord.deleted_at.is_(None))
    if tester:
        tracker = tracker.where(TrackerRecord.tester_name_raw == tester)
    if status:
        tracker = tracker.where(TrackerRecord.status == status)
    if start:
        tracker = tracker.where(TrackerRecord.date_started >= start)
    if end:
        tracker = tracker.where(TrackerRecord.date_started <= end)
    records = db.execute(tracker).scalars().all()

    log_query = select(WorkLog).where(WorkLog.deleted_at.is_(None))
    if start:
        log_query = log_query.where(WorkLog.work_date >= start)
    if end:
        log_query = log_query.where(WorkLog.work_date <= end)
    if tester:
        log_query = log_query.where(WorkLog.tester_name_raw == tester)
    logs = db.execute(log_query).scalars().all()

    def status_key(value: str | None) -> str:
        normalized = (value or "").lower()
        if "block" in normalized:
            return "blocked"
        if "progress" in normalized:
            return "in_progress"
        if "complete" in normalized:
            return "completed"
        return "pending"

    status_counts: dict[str, int] = {"completed": 0, "in_progress": 0, "pending": 0, "blocked": 0}
    by_tester: dict[str, int] = {}
    for record in records:
        status_counts[status_key(record.status)] += 1
        by_tester[record.tester_name_raw or "Unassigned"] = by_tester.get(record.tester_name_raw or "Unassigned", 0) + 1

    trend: dict[str, dict[str, float]] = {}
    for log in logs:
        if not log.work_date:
            continue
        if granularity == "week":
            bucket = f"Week {(log.work_date.day - 1) // 7 + 1}"
        else:
            bucket = log.work_date.strftime("%Y-%m")
        entry = trend.setdefault(bucket, {"hours": 0, "passed_tc": 0, "failed_tc": 0, "steps": 0, "tickets": 0})
        entry["hours"] += log.work_log_hours or 0
        entry["passed_tc"] += log.passed_tc or 0
        entry["failed_tc"] += log.failed_tc or 0
        entry["steps"] += (log.passed_steps or 0) + (log.failed_steps or 0)

    for record in records:
        if record.date_started:
            bucket = record.date_started.strftime("%Y-%m") if granularity != "week" else f"Week {(record.date_started.day - 1) // 7 + 1}"
            trend.setdefault(bucket, {"hours": 0, "passed_tc": 0, "failed_tc": 0, "steps": 0, "tickets": 0})["tickets"] = trend.get(bucket, {}).get("tickets", 0) + 1

    for row in trend.values():
        row["test_cases"] = row["passed_tc"] + row["failed_tc"]
        row["test_steps"] = row["steps"]

    lifecycle_trend: dict[str, dict[str, int]] = {}
    if granularity == "month":
        lifecycle_start = start or date.today().replace(day=1)
        lifecycle_end = end or date.today()
        cursor = lifecycle_start.replace(day=1)
        while cursor <= lifecycle_end:
            lifecycle_trend[cursor.strftime("%Y-%m")] = {"created": 0, "resolved": 0, "backlog": 0}
            cursor = (cursor + timedelta(days=32)).replace(day=1)
        for record in records:
            if record.date_started:
                bucket = record.date_started.strftime("%Y-%m")
                if bucket in lifecycle_trend:
                    lifecycle_trend[bucket]["created"] += 1
            if record.date_ended:
                bucket = record.date_ended.strftime("%Y-%m")
                if bucket in lifecycle_trend:
                    lifecycle_trend[bucket]["resolved"] += 1
        running_backlog = 0
        for bucket, values in lifecycle_trend.items():
            running_backlog += values["created"] - values["resolved"]
            values["backlog"] = max(running_backlog, 0)

    history_trend: dict[str, dict[str, float]] = {}
    if granularity == "month" and end:
        month_index = end.year * 12 + end.month - 1 - 5
        history_start = date(month_index // 12, month_index % 12 + 1, 1)
        history_cursor = history_start
        while history_cursor <= end:
            history_trend[history_cursor.strftime("%Y-%m")] = {"hours": 0, "passed_tc": 0, "failed_tc": 0, "steps": 0, "tickets": 0}
            history_cursor = (history_cursor + timedelta(days=32)).replace(day=1)
        history_log_query = select(WorkLog).where(WorkLog.deleted_at.is_(None), WorkLog.work_date >= history_start, WorkLog.work_date <= end)
        history_tracker_query = select(TrackerRecord).where(TrackerRecord.deleted_at.is_(None), TrackerRecord.date_started >= history_start, TrackerRecord.date_started <= end)
        if tester:
            history_log_query = history_log_query.where(WorkLog.tester_name_raw == tester)
            history_tracker_query = history_tracker_query.where(TrackerRecord.tester_name_raw == tester)
        if status:
            history_tracker_query = history_tracker_query.where(TrackerRecord.status == status)
        history_logs = db.execute(history_log_query).scalars().all()
        history_records = db.execute(history_tracker_query).scalars().all()
        for log in history_logs:
            if log.work_date:
                bucket = log.work_date.strftime("%Y-%m")
                entry = history_trend.setdefault(bucket, {"hours": 0, "passed_tc": 0, "failed_tc": 0, "steps": 0, "tickets": 0})
                entry["hours"] += log.work_log_hours or 0
                entry["passed_tc"] += log.passed_tc or 0
                entry["failed_tc"] += log.failed_tc or 0
                entry["steps"] += (log.passed_steps or 0) + (log.failed_steps or 0)
        for record in history_records:
            if record.date_started:
                history_trend.setdefault(record.date_started.strftime("%Y-%m"), {"hours": 0, "passed_tc": 0, "failed_tc": 0, "steps": 0, "tickets": 0})["tickets"] += 1

    utilization: dict[str, float] = {}
    for log in logs:
        if log.tester_name_raw and log.work_date:
            utilization.setdefault(log.tester_name_raw, 0)
            utilization[log.tester_name_raw] += log.work_log_hours or 0
    for tester_name, hours in list(utilization.items()):
        tester_dates = {log.work_date for log in logs if log.tester_name_raw == tester_name and log.work_date}
        capacity = max(len(tester_dates), 1) * 7.5
        utilization[tester_name] = round(hours / capacity * 100, 1)
    tester_names = {name for name in [record.tester_name_raw for record in records] + [log.tester_name_raw for log in logs] if name}

    utilization_trend: dict[str, float] = {}
    for bucket, row in trend.items():
        bucket_logs = [log for log in logs if log.work_date and (log.work_date.strftime("%Y-%m") == bucket if granularity != "week" else f"Week {(log.work_date.day - 1) // 7 + 1}" == bucket)]
        active_days = {(log.tester_name_raw, log.work_date) for log in bucket_logs if log.tester_name_raw}
        capacity = len(active_days) * 7.5
        utilization_trend[bucket] = round(row["hours"] / capacity * 100, 1) if capacity else 0

    def age_days(record: TrackerRecord) -> int | None:
        if not record.date_started:
            return None
        finish_date = record.date_ended or date.today()
        return max((finish_date - record.date_started).days, 0)

    ticket_ageing = [{"ticket_id": record.ticket_id, "status": record.status, "tester": record.tester_name_raw or "Unassigned", "start_date": record.date_started.isoformat() if record.date_started else None, "end_date": record.date_ended.isoformat() if record.date_ended else None, "comments": record.comments or "", "age_days": age_days(record)} for record in records]
    ticket_ageing.sort(key=lambda item: item["age_days"] if item["age_days"] is not None else -1, reverse=True)
    age_values = [item["age_days"] for item in ticket_ageing if item["age_days"] is not None]

    return {
        "total_records": len(records),
        "status_counts": status_counts,
        "by_tester": by_tester,
        "total_hours": round(sum(log.work_log_hours or 0 for log in logs), 2),
        "passed_tc": sum(log.passed_tc or 0 for log in logs),
        "failed_tc": sum(log.failed_tc or 0 for log in logs),
        "passed_steps": sum(log.passed_steps or 0 for log in logs),
        "failed_steps": sum(log.failed_steps or 0 for log in logs),
        "trend": dict(sorted(trend.items())),
        "history_trend": dict(sorted(history_trend.items())),
        "lifecycle_trend": lifecycle_trend,
        "granularity": "week" if granularity == "week" else "month",
        "utilization": dict(sorted(utilization.items())),
        "total_testers": len(tester_names),
        "average_utilization": round(sum(utilization.values()) / len(utilization), 1) if utilization else 0,
        "utilization_trend": dict(sorted(utilization_trend.items())),
        "average_age_days": round(sum(age_values) / len(age_values), 1) if age_values else 0,
        "ticket_ageing": ticket_ageing,
    }


def filter_options(db: Session) -> dict:
    testers = db.execute(select(TrackerRecord.tester_name_raw).where(TrackerRecord.tester_name_raw.is_not(None)).distinct().order_by(TrackerRecord.tester_name_raw)).scalars().all()
    statuses = db.execute(select(TrackerRecord.status).where(TrackerRecord.status.is_not(None)).distinct().order_by(TrackerRecord.status)).scalars().all()
    return {"testers": testers, "statuses": statuses}
