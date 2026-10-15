# DECISIONS.md - Implementation Decisions & Architecture

### 1. Indexes
I created two unique compound indexes: `{ emp_code: 1 }` on `employees` (enforces employee uniqueness) and `{ emp_code: 1, date: 1 }` on `attendance_logs` (prevents double punch-in for the same date). For list and analytics queries, I added `{ date: -1, emp_code: 1 }` and `{ department: 1, joined_on: 1 }` to eliminate `COLLSCAN` during filtering and pagination. I considered adding a standalone index on `status` alone but rejected it because `status` has low cardinality and is always queried alongside `date` or `emp_code`.

### 2. Punch-in Race Condition
When two identical punch-in requests arrive simultaneously for the same employee and date, both bypass application-level checks. However, MongoDB's unique index on `(emp_code, date)` acts as an atomic lock. The first request successfully inserts the document and returns `201 Created`. The second request triggers a `pymongo.errors.DuplicateKeyError`, which our exception handler catches and returns `409 Conflict`.

### 3. Ties in Late Leaderboard
Following standard competition ranking rules (R8), employees with equal `total_late_minutes` receive identical rank numbers (e.g. 1, 2, 2, 4). The `limit` filter is applied *after* ranking (`rank <= limit`), and tied employees are sub-sorted by `emp_code` ascending. As specified in the contract, if multiple employees tie at the cutoff rank, all of them are returned, resulting in more than `limit` rows.

### 4. Headcount with Zero Logs
The department summary starts its aggregation pipeline on the `employees` collection (filtering by `joined_on <= month_end`), then `$lookup`s matching attendance logs from `attendance_logs` with `preserveNullAndEmptyArrays: True`. This guarantees that employees who joined on or before the month end are included in the headcount calculation even if they have zero attendance logs for that month.

### 5. Scaling to 100x Data
To serve 100x the data volume (tens of millions of records), I would implement database sharding on `attendance_logs` using a compound shard key `{ department: 1, emp_code: 1, date: -1 }` to distribute write/read throughput across MongoDB nodes. Additionally, I would introduce nightly pre-aggregated monthly summary collections to serve historical analytics instantly without computing aggregations on raw logs.
