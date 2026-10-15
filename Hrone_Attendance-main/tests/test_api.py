import os
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

os.environ["MONGO_URI"] = "mongodb://localhost:27017"
os.environ["MONGO_DB"] = "test_attendance_db"

from app.main import app, db

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    db.employees.delete_many({})
    db.attendance_logs.delete_many({})
    # Seed standard test employees
    db.employees.insert_one({
        "emp_code": "EMP0001",
        "name": "Test User",
        "email": "test@example.com",
        "department": "Engineering",
        "shift_start": "09:30",
        "shift_end": "18:30",
        "joined_on": "2026-01-01",
        "created_at": datetime.now(timezone.utc),
    })
    db.employees.insert_one({
        "emp_code": "EMP0002",
        "name": "Night Shift User",
        "email": "night@example.com",
        "department": "Operations",
        "shift_start": "22:00",
        "shift_end": "06:00",
        "joined_on": "2026-01-01",
        "created_at": datetime.now(timezone.utc),
    })
    yield


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_1_valid_punch_in():
    # 2026-07-06 09:28 IST -> 03:58 UTC = 1783310280000 ms
    ts = 1783310280000
    res = client.post("/attendance/punch-in", json={"emp_code": "EMP0001", "punched_at": ts})
    assert res.status_code == 201
    data = res.json()
    assert data["emp_code"] == "EMP0001"
    assert data["date"] == "2026-07-06"
    assert data["status"] == "PRESENT"
    assert data["late_minutes"] == 0
    assert data["punch_out"] is None


def test_2_repeated_punch_in():
    ts = 1783310280000
    res1 = client.post("/attendance/punch-in", json={"emp_code": "EMP0001", "punched_at": ts})
    assert res1.status_code == 201
    res2 = client.post("/attendance/punch-in", json={"emp_code": "EMP0001", "punched_at": ts + 1000})
    assert res2.status_code == 409


def test_3_valid_punch_out():
    in_ts = 1783310280000
    out_ts = 1783343100000
    client.post("/attendance/punch-in", json={"emp_code": "EMP0001", "punched_at": in_ts})
    res = client.post("/attendance/punch-out", json={"emp_code": "EMP0001", "punched_at": out_ts})
    assert res.status_code == 200
    data = res.json()
    assert data["punch_out"] == out_ts
    assert data["work_hours"] == 9.12
    assert data["overtime_minutes"] == 0
    assert data["half_day"] is False


def test_4_punch_out_without_open_session():
    out_ts = 1783343100000
    res = client.post("/attendance/punch-out", json={"emp_code": "EMP0001", "punched_at": out_ts})
    assert res.status_code == 404


def test_5_missing_punch_out():
    in_ts = 1783310280000
    res = client.post("/attendance/punch-in", json={"emp_code": "EMP0001", "punched_at": in_ts})
    assert res.status_code == 201
    log = db.attendance_logs.find_one({"emp_code": "EMP0001", "date": "2026-07-06"})
    assert log["punch_out"] is None
    assert log["work_hours"] is None


def test_6_valid_manual_correction():
    in_ts = 1783312500000  # Late log 10:05 IST
    client.post("/attendance/punch-in", json={"emp_code": "EMP0001", "punched_at": in_ts})

    new_in = 1783310280000  # Corrected to 09:28 IST
    res = client.patch(
        "/attendance/EMP0001/2026-07-06",
        json={"punch_in": new_in, "reason": "Biometric machine error", "regularized_by": "hr.admin"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["late_minutes"] == 0
    assert len(data["history"]) == 1
    assert data["history"][0]["by"] == "hr.admin"
    assert data["history"][0]["reason"] == "Biometric machine error"
    assert "late_minutes" in data["history"][0]["changes"]


def test_7_invalid_manual_correction():
    in_ts = 1783310280000
    client.post("/attendance/punch-in", json={"emp_code": "EMP0001", "punched_at": in_ts})

    res = client.patch(
        "/attendance/EMP0001/2026-07-06",
        json={"status": "ABSENT", "punch_in": in_ts, "reason": "Invalid change", "regularized_by": "admin"},
    )
    assert res.status_code == 422


def test_8_audit_history_after_correction():
    in_ts = 1783310280000
    client.post("/attendance/punch-in", json={"emp_code": "EMP0001", "punched_at": in_ts})
    client.patch(
        "/attendance/EMP0001/2026-07-06",
        json={"status": "WFH", "reason": "Worked from home approved", "regularized_by": "manager"},
    )
    res = client.get("/attendance?emp_code=EMP0001")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    history = items[0]["history"]
    assert len(history) == 1
    assert history[0]["changes"]["status"] == {"from": "PRESENT", "to": "WFH"}


def test_9_analytics_monthly():
    in_ts = 1783310280000  # 2026-07-06 (Mon)
    out_ts = 1783343100000
    client.post("/attendance/punch-in", json={"emp_code": "EMP0001", "punched_at": in_ts})
    client.post("/attendance/punch-out", json={"emp_code": "EMP0001", "punched_at": out_ts})

    res = client.get("/analytics/employees/EMP0001/monthly?month=2026-07")
    assert res.status_code == 200
    data = res.json()
    assert data["emp_code"] == "EMP0001"
    assert data["working_days"] == 23
    assert data["present_days"] == 1.0


def test_10_analytics_incomplete_records():
    in_ts = 1783310280000  # 2026-07-06
    client.post("/attendance/punch-in", json={"emp_code": "EMP0001", "punched_at": in_ts})
    res = client.get("/analytics/employees/EMP0001/monthly?month=2026-07")
    assert res.status_code == 200
    data = res.json()
    assert data["present_days"] == 1.0


def test_11_empty_date_ranges_and_empty_results():
    res = client.get("/attendance?emp_code=NONEXISTENT")
    assert res.status_code == 200
    assert res.json()["items"] == []
    assert res.json()["total"] == 0


def test_12_invalid_request_payloads():
    res = client.post("/attendance/punch-in", json={"emp_code": "EMP0001", "punched_at": 1783310280})
    assert res.status_code == 422


def test_13_overnight_shift_boundary():
    in_ts = 1783355100000  # 2026-07-06 21:55 IST
    out_ts = 1783386600000  # 2026-07-07 06:40 IST

    res_in = client.post("/attendance/punch-in", json={"emp_code": "EMP0002", "punched_at": in_ts})
    assert res_in.status_code == 201
    assert res_in.json()["date"] == "2026-07-06"

    res_out = client.post("/attendance/punch-out", json={"emp_code": "EMP0002", "punched_at": out_ts})
    assert res_out.status_code == 200
    data = res_out.json()
    assert data["date"] == "2026-07-06"
    assert data["work_hours"] == 8.75
    assert data["overtime_minutes"] == 40


def test_14_department_summary_analytics():
    # Punch in & out for EMP0001
    in_ts = 1783310280000
    out_ts = 1783343100000
    client.post("/attendance/punch-in", json={"emp_code": "EMP0001", "punched_at": in_ts})
    client.post("/attendance/punch-out", json={"emp_code": "EMP0001", "punched_at": out_ts})

    res = client.get("/analytics/departments/summary?month=2026-07")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) >= 1
    eng = next(i for i in items if i["department"] == "Engineering")
    assert eng["headcount"] == 1
    assert eng["present_days"] == 1.0
    assert eng["avg_work_hours"] == 9.12


def test_15_late_leaderboard_analytics():
    # EMP0001 punched in late (10:05 IST -> 35 min late)
    in_ts = 1783312500000
    client.post("/attendance/punch-in", json={"emp_code": "EMP0001", "punched_at": in_ts})

    res = client.get("/analytics/leaderboard/late?month=2026-07&limit=5")
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["emp_code"] == "EMP0001"
    assert items[0]["rank"] == 1
    assert items[0]["total_late_minutes"] == 35


def test_16_department_trend_analytics():
    res = client.get("/analytics/departments/Engineering/trend?from=2026-07-01&to=2026-07-05")
    assert res.status_code == 200
    data = res.json()
    assert data["department"] == "Engineering"
    assert len(data["items"]) == 5


def test_17_explain_endpoint():
    res = client.get("/admin/explain/attendance_list?emp_code=EMP0001")
    assert res.status_code == 200
    data = res.json()
    assert data["endpoint"] == "attendance_list"
    assert data["collection"] == "attendance_logs"
    assert "explain" in data
