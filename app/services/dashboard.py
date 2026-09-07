from calendar import monthrange
from datetime import date, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import TrackerRecord, WorkLog


BT_TICKET_PREFIXES = ("HYDRAS", "THESTRALS", "CIMDB", "CIMBT")


def ticket_category_matches(ticket_id: str | None, category: str | None) -> bool:
    if not category or category == "all":
        return True
    normalized = (ticket_id or "").strip().upper()
    if category == "dq":
        return normalized.startswith("DQ")
    if category == "bt":
        return normalized.startswith(BT_TICKET_PREFIXES)
    if category == "others":
        return not normalized.startswith(("DQ", *BT_TICKET_PREFIXES))
    return True


def dashboard_metrics(db: Session, start: date | None = None, end: date | None = None, tester: str | None = None, status: str | None = None, granularity: str = "month", week: int | None = None, report_view: str | None = None, ticket_category: str | None = None) -> dict:
    if start is None and end is None and granularity == "month":
        current_month = date.today().replace(day=1)
        start = (current_month - timedelta(days=5 * 31)).replace(day=1)
        end = date.today()
    if week and start and granularity == "week":
        week_start = start.replace(day=(week - 1) * 7 + 1)
        week_end = start.replace(day=min(week * 7, monthrange(start.year, start.month)[1]))
        start, end = week_start, week_end
    use_ft_activity = report_view in {"monthly", "weekly", "utilization"}
    log_query = select(WorkLog).where(WorkLog.deleted_at.is_(None))
    if use_ft_activity:
        log_query = log_query.where(WorkLog.source_sheet == "Daily Report - FT")
    if start:
        log_query = log_query.where(WorkLog.work_date >= start)
    if end:
        log_query = log_query.where(WorkLog.work_date <= end)
    if tester:
        log_query = log_query.where(WorkLog.tester_name_raw == tester)
    logs = db.execute(log_query).scalars().all()
    if ticket_category:
        logs = [log for log in logs if ticket_category_matches(log.ticket_id_raw, ticket_category)]

    def ticket_key(value: str | None) -> str:
        return (value or "").strip().casefold()

    tracker = select(TrackerRecord).where(TrackerRecord.deleted_at.is_(None))
    if use_ft_activity:
        if status:
            tracker = tracker.where(TrackerRecord.status == status)
        candidate_records = db.execute(tracker).scalars().all()
        linked_record_ids = {log.tracker_record_id for log in logs if log.tracker_record_id is not None}
        activity_ticket_ids = {ticket_key(log.ticket_id_raw) for log in logs}
        records = [record for record in candidate_records if record.id in linked_record_ids or ticket_key(record.ticket_id) in activity_ticket_ids]
    else:
        if tester:
            tracker = tracker.where(TrackerRecord.tester_name_raw == tester)
        if status:
            tracker = tracker.where(TrackerRecord.status == status)
        if start:
            tracker = tracker.where(TrackerRecord.date_started >= start)
        if end:
            tracker = tracker.where(TrackerRecord.date_started <= end)
        records = db.execute(tracker).scalars().all()
    if use_ft_activity and status:
        record_ids = {record.id for record in records}
        record_ticket_ids = {ticket_key(record.ticket_id) for record in records}
        logs = [log for log in logs if log.tracker_record_id in record_ids or ticket_key(log.ticket_id_raw) in record_ticket_ids]

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

    if use_ft_activity:
        tickets_by_bucket: dict[str, set[str]] = {}
        for log in logs:
            if not log.work_date:
                continue
            bucket = log.work_date.strftime("%Y-%m") if granularity != "week" else f"Week {(log.work_date.day - 1) // 7 + 1}"
            tickets_by_bucket.setdefault(bucket, set()).add(log.ticket_id_raw)
        for bucket, ticket_ids in tickets_by_bucket.items():
            trend.setdefault(bucket, {"hours": 0, "passed_tc": 0, "failed_tc": 0, "steps": 0, "tickets": 0})["tickets"] = len(ticket_ids)
    else:
        for record in records:
            if record.date_started:
                bucket = record.date_started.strftime("%Y-%m") if granularity != "week" else f"Week {(record.date_started.day - 1) // 7 + 1}"
                trend.setdefault(bucket, {"hours": 0, "passed_tc": 0, "failed_tc": 0, "steps": 0, "tickets": 0})["tickets"] = trend.get(bucket, {}).get("tickets", 0) + 1

    for row in trend.values():
        row["test_cases"] = row["passed_tc"] + row["failed_tc"]
        row["test_steps"] = row["steps"]

    lifecycle_trend: dict[str, dict] = {}
    if granularity == "month":
        lifecycle_start = start or date.today().replace(day=1)
        lifecycle_end = end or date.today()
        cursor = lifecycle_start.replace(day=1)
        while cursor <= lifecycle_end:
            lifecycle_trend[cursor.strftime("%Y-%m")] = {
                "created": 0,
                "resolved": 0,
                "created_tickets": [],
                "resolved_tickets": [],
            }
            cursor = (cursor + timedelta(days=32)).replace(day=1)
        for record in records:
            if record.date_started:
                bucket = record.date_started.strftime("%Y-%m")
                if bucket in lifecycle_trend:
                    lifecycle_trend[bucket]["created"] += 1
                    lifecycle_trend[bucket]["created_tickets"].append(record.ticket_id)
            if record.date_ended:
                bucket = record.date_ended.strftime("%Y-%m")
                if bucket in lifecycle_trend:
                    lifecycle_trend[bucket]["resolved"] += 1
                    lifecycle_trend[bucket]["resolved_tickets"].append(record.ticket_id)
        for values in lifecycle_trend.values():
            values["created_tickets"].sort()
            values["resolved_tickets"].sort()

    history_trend: dict[str, dict[str, float]] = {}
    if granularity == "month" and end:
        month_index = end.year * 12 + end.month - 1 - 5
        history_start = date(month_index // 12, month_index % 12 + 1, 1)
        history_cursor = history_start
        while history_cursor <= end:
            history_trend[history_cursor.strftime("%Y-%m")] = {"hours": 0, "passed_tc": 0, "failed_tc": 0, "steps": 0, "tickets": 0}
            history_cursor = (history_cursor + timedelta(days=32)).replace(day=1)
        history_log_query = select(WorkLog).where(WorkLog.deleted_at.is_(None), WorkLog.work_date >= history_start, WorkLog.work_date <= end)
        if use_ft_activity:
            history_log_query = history_log_query.where(WorkLog.source_sheet == "Daily Report - FT")
        history_tracker_query = select(TrackerRecord).where(TrackerRecord.deleted_at.is_(None), TrackerRecord.date_started >= history_start, TrackerRecord.date_started <= end)
        if tester:
            history_log_query = history_log_query.where(WorkLog.tester_name_raw == tester)
            history_tracker_query = history_tracker_query.where(TrackerRecord.tester_name_raw == tester)
        if status:
            history_tracker_query = history_tracker_query.where(TrackerRecord.status == status)
        history_logs = db.execute(history_log_query).scalars().all()
        if ticket_category:
            history_logs = [log for log in history_logs if ticket_category_matches(log.ticket_id_raw, ticket_category)]
        history_records = db.execute(history_tracker_query).scalars().all()
        for log in history_logs:
            if log.work_date:
                bucket = log.work_date.strftime("%Y-%m")
                entry = history_trend.setdefault(bucket, {"hours": 0, "passed_tc": 0, "failed_tc": 0, "steps": 0, "tickets": 0})
                entry["hours"] += log.work_log_hours or 0
                entry["passed_tc"] += log.passed_tc or 0
                entry["failed_tc"] += log.failed_tc or 0
                entry["steps"] += (log.passed_steps or 0) + (log.failed_steps or 0)
        if use_ft_activity:
            history_tickets: dict[str, set[str]] = {}
            for log in history_logs:
                if log.work_date:
                    history_tickets.setdefault(log.work_date.strftime("%Y-%m"), set()).add(log.ticket_id_raw)
            for bucket, ticket_ids in history_tickets.items():
                history_trend[bucket]["tickets"] = len(ticket_ids)
        else:
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
    if use_ft_activity:
        tester_names = {log.tester_name_raw for log in logs if log.tester_name_raw}
    else:
        tester_names = {name for name in [record.tester_name_raw for record in records] + [log.tester_name_raw for log in logs] if name}

    utilization_trend: dict[str, float] = {}
    for bucket, row in trend.items():
        bucket_logs = [log for log in logs if log.work_date and (log.work_date.strftime("%Y-%m") == bucket if granularity != "week" else f"Week {(log.work_date.day - 1) // 7 + 1}" == bucket)]
        active_days = {(log.tester_name_raw, log.work_date) for log in bucket_logs if log.tester_name_raw}
        capacity = len(active_days) * 7.5
        utilization_trend[bucket] = round(row["hours"] / capacity * 100, 1) if capacity else 0

    def report_dates(record: TrackerRecord) -> tuple[date | None, date | None, str | None]:
        start_date = report_start_dates.get(record.id) if use_ft_activity else record.date_started
        end_date = record.date_ended
        warning = None
        if start_date and end_date and end_date < start_date and end_date.day <= 12:
            swapped_end_date = date(end_date.year, end_date.day, end_date.month)
            if swapped_end_date >= start_date:
                end_date = swapped_end_date
                warning = "DQ end date month/day order was corrected for this report"
        return start_date, end_date, warning

    def age_days(record: TrackerRecord) -> int | None:
        start_date, end_date, _ = report_dates(record)
        if not start_date or not end_date:
            return None
        return (end_date - start_date).days

    def ticket_ageing_item(record: TrackerRecord) -> dict:
        start_date, end_date, warning = report_dates(record)
        logged_hours = sum(
            log.work_log_hours or 0
            for log in logs
            if log.tracker_record_id == record.id or ticket_key(log.ticket_id_raw) == ticket_key(record.ticket_id)
        )
        return {
            "ticket_id": record.ticket_id,
            "status": record.status,
            "tester": report_testers.get(record.id, record.tester_name_raw or "Unassigned"),
            "logged_hours": round(logged_hours, 2),
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "date_warning": warning,
            "comments": record.comments or "",
            "age_days": age_days(record),
        }

    report_start_dates: dict[int, date] = {}
    report_testers: dict[int, str] = {}
    unmatched_ticket_details: list[dict] = []
    if use_ft_activity:
        record_ids = {record.id for record in records}
        record_ids_by_ticket = {ticket_key(record.ticket_id): record.id for record in records}
        detail_logs = db.execute(select(WorkLog).where(WorkLog.deleted_at.is_(None), WorkLog.source_sheet == "Daily Report - FT")).scalars().all()
        for log in detail_logs:
            target_record_id = log.tracker_record_id if log.tracker_record_id in record_ids else record_ids_by_ticket.get(ticket_key(log.ticket_id_raw))
            if target_record_id is None or not log.work_date:
                continue
            current_start = report_start_dates.get(target_record_id)
            if current_start is None or log.work_date < current_start:
                report_start_dates[target_record_id] = log.work_date
                if log.tester_name_raw:
                    report_testers[target_record_id] = log.tester_name_raw

        selected_logs_by_ticket: dict[str, list[WorkLog]] = {}
        for log in logs:
            selected_logs_by_ticket.setdefault(ticket_key(log.ticket_id_raw), []).append(log)
        matched_ticket_keys = set(record_ids_by_ticket)
        matched_ticket_keys.update(ticket_key(log.ticket_id_raw) for log in logs if log.tracker_record_id in record_ids)
        for key, selected_ticket_logs in selected_logs_by_ticket.items():
            if key in matched_ticket_keys:
                continue
            dated_logs = [log for log in selected_ticket_logs if log.work_date]
            first_log = min(dated_logs, key=lambda log: log.work_date) if dated_logs else selected_ticket_logs[0]
            latest_comment_log = max((log for log in selected_ticket_logs if log.daily_comments), key=lambda log: log.work_date or date.min, default=None)
            unmatched_ticket_details.append({
                "ticket_id": (first_log.ticket_id_raw or "GENERAL").strip(),
                "status": "Not available",
                "tester": first_log.tester_name_raw or "Unassigned",
                "logged_hours": round(sum(log.work_log_hours or 0 for log in selected_ticket_logs), 2),
                "start_date": first_log.work_date.isoformat() if first_log.work_date else None,
                "end_date": None,
                "date_warning": None,
                "comments": latest_comment_log.daily_comments if latest_comment_log else "",
                "age_days": None,
            })

    ticket_ageing = [ticket_ageing_item(record) for record in records] + unmatched_ticket_details
    ticket_ageing.sort(key=lambda item: item["age_days"] if item["age_days"] is not None else -1, reverse=True)
    age_values = [item["age_days"] for item in ticket_ageing if item["age_days"] is not None]

    return {
        "total_records": len(ticket_ageing) if use_ft_activity else len(records),
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
    tracker_testers = db.execute(select(TrackerRecord.tester_name_raw).where(TrackerRecord.tester_name_raw.is_not(None)).distinct()).scalars().all()
    ft_testers = db.execute(select(WorkLog.tester_name_raw).where(WorkLog.deleted_at.is_(None), WorkLog.source_sheet == "Daily Report - FT", WorkLog.tester_name_raw.is_not(None)).distinct()).scalars().all()
    testers = sorted(set(tracker_testers) | set(ft_testers))
    statuses = db.execute(select(TrackerRecord.status).where(TrackerRecord.status.is_not(None)).distinct().order_by(TrackerRecord.status)).scalars().all()
    return {"testers": testers, "statuses": statuses}
