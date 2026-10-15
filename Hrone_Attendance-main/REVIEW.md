# REVIEW.md - Starter Code Review

Below is the comprehensive review of the starter code in `app/main.py`.

## 1. Identified Defects & Fixes

| # | Where (function / line) | What is wrong | How you'd notice it (test, input, or symptom) | How you fixed it |
|---|---|---|---|---|
| 1 | `create_employee` (Line 79-83) | Check-then-insert pattern (TOCTOU race condition) for `emp_code`. | Concurrent POST requests with the same `emp_code` both pass `find_one()` and create duplicate documents. | Added database unique index on `emp_code` at startup and caught `pymongo.errors.DuplicateKeyError` to return HTTP 409. |
| 2 | `punch_in` (Line 104-105) | Check-then-insert pattern for `(emp_code, date)`. | Concurrent punch-in requests at the same instant produce two attendance documents for the same day. | Created compound unique index on `(emp_code, date)` and handled `DuplicateKeyError` to return 409. |
| 3 | `punch_in` (Line 103) | `ts.date().isoformat()` uses local server time instead of IST and ignores overnight shifts (R1). | A punch-in for an overnight shift (e.g. 04:00 IST for a 22:00-06:00 shift) gets assigned to the wrong date. | Implemented `compute_attendance_date` with IST conversion (`UTC+05:30`) and overnight date rollback logic. |
| 4 | `compute_late_minutes` (Line 33-37) | Evaluates `minutes > 10` on floored integer. Returns 0 for 10 min 5 sec late (R2 violation). Also mixes naive UTC timestamp with IST shift hours. | Punching in at 09:40:05 IST returns `0` late minutes instead of `10`. | Converted timestamp to IST first, computed exact elapsed seconds, and checked `diff_sec > 600` before flooring minutes. |
| 5 | `compute_overtime` (Line 44-47) | Fails to handle overnight shift end dates (which fall on date + 1 day) and omits 30-min minimum threshold (R3). | Overnight shift punch-outs compute negative overtime or report small overtime < 30 minutes. | Checked if `shift_end <= shift_start` to add 1 day to `end_date`, and returned `diff_min` only when `diff_min >= 30`. |
| 6 | `compute_work_hours` (Line 40-41) | Python's built-in `round()` performs banker's rounding (round half to even) instead of half-up (R4/R8). | `round(2.675, 2)` evaluates to `2.67` instead of expected `2.68`. | Used Python `decimal.Decimal` with `ROUND_HALF_UP` quantization. |
| 7 | `list_employees` (Line 93) | `skip = page * page_size` skips page 1 when `page = 1`. | Requesting `/employees?page=1&page_size=20` returns items 21-40 instead of 1-20. | Fixed skip calculation to `(page - 1) * page_size`. |
| 8 | `list_employees` (Line 94) | `db.employees.count_documents({})` counts all documents ignoring active `department` filter. | `total` in response does not match the filtered result set size. | Changed count query to `db.employees.count_documents(q)`. |
| 9 | `list_attendance` (Line 144-147) | In-memory sorting and pagination (`list(db.attendance_logs.find(q))`). | Endpoint causes high memory usage and slow performance on datasets of ~100,000 documents. | Applied database-level sorting `.sort([("date", -1), ("emp_code", 1)]).skip().limit()` directly in MongoDB. |
| 10 | `punch_in` (Line 101) | Does not check if employee exists before reading `emp["shift_start"]`. | Punching in for a non-existent `emp_code` causes an unhandled 500 `TypeError`. | Added `db.employees.find_one({"emp_code": body.emp_code})` check and raised HTTP 404 if missing. |
| 11 | `punch_in` (Line 119) | Attaches `doc["id"] = str(res.inserted_id)` to response body. | Violates OpenAPI contract (`AttendanceRecord` schema has no `id` field). | Removed `id` field insertion and serialized output strictly to schema fields. |
| 12 | `health` (Line 73) | Returns static `{"status": "ok"}` without checking database connectivity. | Endpoint returns 200 even when MongoDB is down or unreachable. | Added `client.admin.command("ping")` and raised HTTP 503 if database ping fails. |

---

## 2. Non-Defects Examined & Preserved

- **FastAPI Exception Handling**: The use of `HTTPException` with `detail` string matches FastAPI default conventions and OpenAPI specifications.
- **Pydantic Model Structure**: Base Pydantic models for incoming JSON bodies were sound in design and retained with enhanced field validation rules (`ge`, `le`, regex patterns).
