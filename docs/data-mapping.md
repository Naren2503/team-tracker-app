# Excel Data Mapping

## Source Workbook

`C:\Users\nsr467\Downloads\DQ - Testing Tracker - 2026.xlsm`

The workbook contains 31 sheets. The application treats three sheets as authoritative source data and treats dashboards/monthly reports as derived views.

## Source Sheets

| Excel Sheet | Target Table | Notes |
|---|---|---|
| `DQ Task Tracker` | `tracker_records` | Master ticket lifecycle records |
| `Daily Report - FT` | `work_logs` | Functional testing daily work logs |
| `Daily Report - BT` | `work_logs` | BT work logs with `workstream = BT` |
| `Setup` | `lookups` / seed candidates | Statuses, testers, priorities, task categories |
| Dashboard/report sheets | API-calculated dashboard data | Not imported as permanent source records by default |

## Column Mapping

| Sheet | Excel Column | Database Field | Transform |
|---|---|---|---|
| `DQ Task Tracker` | `Ticket ID` | `tracker_records.ticket_id` | required text |
| `DQ Task Tracker` | `Date Started` | `tracker_records.date_started` | date parse |
| `DQ Task Tracker` | `Date Ended` | `tracker_records.date_ended` | nullable date |
| `DQ Task Tracker` | `Tester` | `tracker_records.tester_name_raw` | preserve raw name; optionally map to user |
| `DQ Task Tracker` | `DQ Status` | `tracker_records.status` | normalize Completed/In progress/Blocked/Withdrawn |
| `DQ Task Tracker` | `Zephyr Upload` | `tracker_records.zephyr_upload` | nullable status text |
| `DQ Task Tracker` | `Comments` | `tracker_records.comments` | text, multiline-safe UI |
| `Daily Report - FT` | `TICKET ID` | `work_logs.ticket_id_raw` | match to tracker record where possible |
| `Daily Report - FT` | `TESTER` | `work_logs.tester_name_raw` | preserve raw name |
| `Daily Report - FT` | `TASK` | `work_logs.task` | lookup-like category |
| `Daily Report - FT` | `PRIORITY` | `work_logs.priority` | title-case, blank allowed |
| `Daily Report - FT` | `DATE` | `work_logs.work_date` | required date |
| `Daily Report - FT` | `work log (hrs)` | `work_logs.work_log_hours` | numeric; blanks and '-' become null |
| `Daily Report - FT` | `Passed - TC` | `work_logs.passed_tc` | integer; blanks and '-' become null |
| `Daily Report - FT` | `Passed - Steps` | `work_logs.passed_steps` | integer; blanks and '-' become null |
| `Daily Report - FT` | `Failed - TC` | `work_logs.failed_tc` | integer; blanks and '-' become null |
| `Daily Report - FT` | `Failed - Steps` | `work_logs.failed_steps` | integer; blanks and '-' become null |
| `Daily Report - FT` | `DAILY COMMENTS` | `work_logs.daily_comments` | text |
| `Daily Report - BT` | same daily columns | `work_logs` | same mapping, `workstream = BT` |

## Known Data Quality Rules

- `Ticket ID`, `Date Started`, `Tester`, and `DQ Status` are mandatory for tracker rows.
- `TICKET ID`, `TESTER`, and `DATE` are mandatory for daily work logs.
- Duplicate tracker ticket IDs are rejected in `add` mode and merged in `merge` mode.
- Blank-like values and nonbreaking spaces are normalized.
- Status variants such as `✅ Complete` and `✅ Completed` map to `Completed`.
- Dashboard formulas are replaced by API aggregate queries.

## Unconfirmed Business Decisions

- Whether duplicate `DQ5172` in the tracker is valid or should be merged.
- Whether non-DQ activities like `Support/Meetings` should become first-class tracker records.
- Whether overdue requires a new due-date field or an SLA rule.
- Whether project should be manually added or inferred from ticket prefix.
