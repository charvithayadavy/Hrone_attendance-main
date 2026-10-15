import os
import json
import urllib.request
import urllib.error
from pymongo import MongoClient

BASE_URL = "http://localhost:8000"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "attendance_db")

results = []

def record_test(feature, test_name, passed, details="", remaining="None"):
    results.append({
        "feature": feature,
        "test": test_name,
        "status": "PASS" if passed else "FAIL",
        "details": details,
        "remaining": remaining
    })
    status_str = "[PASS]" if passed else "[FAIL]"
    print(f"{status_str} {feature} - {test_name}: {details}")

def api_request(method, path, body=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read().decode("utf-8")
            return resp.status, json.loads(resp_body) if resp_body else None
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode("utf-8")
        try:
            parsed = json.loads(resp_body)
        except Exception:
            parsed = resp_body
        return e.code, parsed

def run_all_qa_tests():
    print("--- Starting Phase 5 Comprehensive Business Flow Verification ---")
    
    # Clean test records if any exist
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    db.employees.delete_many({"emp_code": {"$regex": "^EMP999"}})
    db.attendance_logs.delete_many({"emp_code": {"$regex": "^EMP999"}})
    
    # 1. Create Employee & Retrieve List
    code, res = api_request("POST", "/employees", {
        "emp_code": "EMP9991",
        "name": "QA Tester One",
        "email": "qa1@example.com",
        "department": "QA_Dept",
        "shift_start": "09:00",
        "shift_end": "17:00",
        "joined_on": "2026-01-01"
    })
    passed = (code == 201 and res.get("emp_code") == "EMP9991" and res.get("department") == "QA_Dept")
    record_test("Employee Management", "Create Employee", passed, f"Status: {code}, emp_code: {res.get('emp_code') if passed else res}")
    
    # Duplicate Employee
    code_dup, res_dup = api_request("POST", "/employees", {
        "emp_code": "EMP9991",
        "name": "QA Duplicate",
        "email": "qa_dup@example.com",
        "department": "QA_Dept",
        "shift_start": "09:00",
        "shift_end": "17:00",
        "joined_on": "2026-01-01"
    })
    passed_dup = (code_dup == 409)
    record_test("Employee Management", "Reject Duplicate Employee Code", passed_dup, f"Status: {code_dup}, Detail: {res_dup.get('detail') if isinstance(res_dup, dict) else res_dup}")
    
    # Invalid Employee Payload (shift_start == shift_end)
    code_inv, res_inv = api_request("POST", "/employees", {
        "emp_code": "EMP9992",
        "name": "QA Tester Two",
        "email": "qa2@example.com",
        "department": "QA_Dept",
        "shift_start": "09:00",
        "shift_end": "09:00",
        "joined_on": "2026-01-01"
    })
    passed_inv = (code_inv == 422)
    record_test("Employee Management", "Reject Invalid Employee Payload", passed_inv, f"Status: {code_inv}")

    # List Employees
    code_list, res_list = api_request("GET", "/employees?department=QA_Dept")
    passed_list = (code_list == 200 and res_list.get("total") == 1 and len(res_list.get("items")) == 1)
    record_test("Employee Management", "List Employees Filtered by Department", passed_list, f"Total: {res_list.get('total') if passed_list else None}")

    # 2. Punch In
    # 2026-07-06 09:05:00 IST -> UTC 2026-07-06 03:35:00 = 1783308900000 ms
    in_ts_1 = 1783308900000
    code_pi1, res_pi1 = api_request("POST", "/attendance/punch-in", {
        "emp_code": "EMP9991",
        "punched_at": in_ts_1,
        "status": "PRESENT"
    })
    passed_pi1 = (code_pi1 == 201 and res_pi1.get("date") == "2026-07-06" and res_pi1.get("late_minutes") == 0 and res_pi1.get("status") == "PRESENT")
    record_test("Attendance Punch-In", "Punch In On-Time", passed_pi1, f"Status: {code_pi1}, Date: {res_pi1.get('date') if passed_pi1 else None}, Late: {res_pi1.get('late_minutes') if passed_pi1 else None}")

    # Duplicate Punch In
    code_pi_dup, res_pi_dup = api_request("POST", "/attendance/punch-in", {
        "emp_code": "EMP9991",
        "punched_at": in_ts_1 + 3600000,
        "status": "PRESENT"
    })
    passed_pi_dup = (code_pi_dup == 409)
    record_test("Attendance Punch-In", "Reject Duplicate Punch-In for Same Date", passed_pi_dup, f"Status: {code_pi_dup}")

    # Punch In Non-existent Employee
    code_pi_404, res_pi_404 = api_request("POST", "/attendance/punch-in", {
        "emp_code": "EMP0000",
        "punched_at": in_ts_1,
        "status": "PRESENT"
    })
    passed_pi_404 = (code_pi_404 == 404)
    record_test("Attendance Punch-In", "Reject Punch-In for Non-Existent Employee", passed_pi_404, f"Status: {code_pi_404}")

    # 3. Punch Out
    # 2026-07-06 18:05:00 IST -> UTC 2026-07-06 12:35:00 = 1783341300000 ms (9.0 hours worked, shift end 17:00 -> 65 min overtime)
    out_ts_1 = 1783341300000
    code_po1, res_po1 = api_request("POST", "/attendance/punch-out", {
        "emp_code": "EMP9991",
        "punched_at": out_ts_1
    })
    passed_po1 = (code_po1 == 200 and res_po1.get("work_hours") == 9.0 and res_po1.get("overtime_minutes") == 65 and res_po1.get("half_day") is False)
    record_test("Attendance Punch-Out", "Punch Out & Metric Calculations", passed_po1, f"Status: {code_po1}, WorkHours: {res_po1.get('work_hours') if passed_po1 else None}, OT: {res_po1.get('overtime_minutes') if passed_po1 else None}")

    # Repeated Punch Out (no open session)
    code_po_dup, res_po_dup = api_request("POST", "/attendance/punch-out", {
        "emp_code": "EMP9991",
        "punched_at": out_ts_1 + 3600000
    })
    passed_po_dup = (code_po_dup == 404)
    record_test("Attendance Punch-Out", "Reject Punch-Out Without Open Session", passed_po_dup, f"Status: {code_po_dup}")

    # 4. Calculation Rules (Late Minutes & Half Day)
    # Create EMP9992 for calculation test
    api_request("POST", "/employees", {
        "emp_code": "EMP9992",
        "name": "QA Tester Two",
        "email": "qa2@example.com",
        "department": "QA_Dept",
        "shift_start": "09:00",
        "shift_end": "17:00",
        "joined_on": "2026-01-01"
    })
    # Punch in 09:20 IST (20 mins late > 10 min grace) -> UTC 2026-07-07 03:50:00 = 1783396200000 ms
    in_ts_late = 1783396200000
    code_late, res_late = api_request("POST", "/attendance/punch-in", {
        "emp_code": "EMP9992",
        "punched_at": in_ts_late,
        "status": "PRESENT"
    })
    passed_late = (code_late == 201 and res_late.get("late_minutes") == 20)
    record_test("Business Rules", "Late Minutes Calculation (Rule R2)", passed_late, f"Late Mins: {res_late.get('late_minutes') if passed_late else None}")

    # Punch out after 3.5 hours (12:50 IST) -> UTC 2026-07-07 07:20:00 = 1783408800000 ms -> Half day True (< 4.50 hrs)
    out_ts_half = 1783408800000
    code_half, res_half = api_request("POST", "/attendance/punch-out", {
        "emp_code": "EMP9992",
        "punched_at": out_ts_half
    })
    passed_half = (code_half == 200 and res_half.get("work_hours") == 3.5 and res_half.get("half_day") is True)
    record_test("Business Rules", "Half-Day Detection (Rule R5)", passed_half, f"WorkHours: {res_half.get('work_hours') if passed_half else None}, HalfDay: {res_half.get('half_day') if passed_half else None}")

    # 5. Incomplete Attendance (Punch-in without punch-out)
    in_ts_open = 1783482600000 # 2026-07-08
    code_open, res_open = api_request("POST", "/attendance/punch-in", {
        "emp_code": "EMP9992",
        "punched_at": in_ts_open,
        "status": "PRESENT"
    })
    passed_open = (code_open == 201 and res_open.get("punch_out") is None and res_open.get("work_hours") is None)
    record_test("Attendance Handling", "Incomplete Attendance Record (Missing Punch-Out)", passed_open, f"PunchOut: {res_open.get('punch_out') if passed_open else None}")

    # 6. Regularization (Attendance Correction) & Audit History
    # Correct EMP9991 record for 2026-07-06
    code_reg, res_reg = api_request("PATCH", "/attendance/EMP9991/2026-07-06", {
        "status": "WFH",
        "reason": "WFH approved retroactively by lead",
        "regularized_by": "qa.lead"
    })
    passed_reg = (
        code_reg == 200 and 
        res_reg.get("status") == "WFH" and 
        len(res_reg.get("history", [])) == 1 and 
        res_reg["history"][0]["by"] == "qa.lead" and
        res_reg["history"][0]["changes"].get("status") == {"from": "PRESENT", "to": "WFH"}
    )
    record_test("Regularization", "Attendance Regularization & Audit Trail", passed_reg, f"History Entries: {len(res_reg.get('history', [])) if passed_reg else None}")

    # Reject Invalid Regularization (ABSENT with punch_in)
    code_reg_inv, res_reg_inv = api_request("PATCH", "/attendance/EMP9991/2026-07-06", {
        "status": "ABSENT",
        "punch_in": in_ts_1,
        "reason": "Invalid regularization attempt",
        "regularized_by": "qa.lead"
    })
    passed_reg_inv = (code_reg_inv == 422)
    record_test("Regularization", "Reject Invalid Regularization Payload", passed_reg_inv, f"Status: {code_reg_inv}")

    # 7. Analytics Endpoints
    # Monthly Analytics
    code_m, res_m = api_request("GET", "/analytics/employees/EMP9991/monthly?month=2026-07")
    passed_m = (code_m == 200 and res_m.get("emp_code") == "EMP9991" and res_m.get("working_days") == 23)
    record_test("Analytics", "Employee Monthly Analytics", passed_m, f"Working Days: {res_m.get('working_days') if passed_m else None}, Present Days: {res_m.get('present_days') if passed_m else None}")

    # Department Summary
    code_ds, res_ds = api_request("GET", "/analytics/departments/summary?month=2026-07&department=QA_Dept")
    passed_ds = (code_ds == 200 and len(res_ds.get("items", [])) == 1 and res_ds["items"][0]["headcount"] == 2)
    record_test("Analytics", "Department Summary Analytics", passed_ds, f"Headcount: {res_ds['items'][0]['headcount'] if passed_ds else None}")

    # Late Leaderboard
    code_ll, res_ll = api_request("GET", "/analytics/leaderboard/late?month=2026-07&department=QA_Dept")
    passed_ll = (code_ll == 200 and len(res_ll.get("items", [])) >= 1)
    record_test("Analytics", "Late Leaderboard Analytics", passed_ll, f"Late items: {len(res_ll.get('items', [])) if passed_ll else None}")

    # Department Trend
    code_dt, res_dt = api_request("GET", "/analytics/departments/QA_Dept/trend?from=2026-07-01&to=2026-07-05")
    passed_dt = (code_dt == 200 and len(res_dt.get("items", [])) == 5)
    record_test("Analytics", "Department Trend Analytics", passed_dt, f"Trend Days: {len(res_dt.get('items', [])) if passed_dt else None}")

    # Analytics 404 & 422 Edge Cases
    code_an_404, _ = api_request("GET", "/analytics/employees/EMP9999/monthly?month=2026-07")
    record_test("Analytics", "Missing Employee 404 in Analytics", code_an_404 == 404, f"Status: {code_an_404}")

    code_an_422, _ = api_request("GET", "/analytics/departments/QA_Dept/trend?from=2026-07-10&to=2026-07-01")
    record_test("Analytics", "Invalid Date Filter 422 in Department Trend", code_an_422 == 422, f"Status: {code_an_422}")

    # 8. Admin Diagnostics
    code_ex, res_ex = api_request("GET", "/admin/explain/attendance_list?emp_code=EMP9991")
    passed_ex = (code_ex == 200 and "explain" in res_ex)
    record_test("Admin Diagnostics", "Explain Endpoint Execution Stats", passed_ex, f"Collection: {res_ex.get('collection') if passed_ex else None}")

    # 9. MongoDB Data Persistence Check
    emp_doc = db.employees.find_one({"emp_code": "EMP9991"})
    log_doc = db.attendance_logs.find_one({"emp_code": "EMP9991", "date": "2026-07-06"})
    passed_db = (emp_doc is not None and log_doc is not None and log_doc.get("status") == "WFH")
    record_test("Database Persistence", "MongoDB Persistence & Audit Verification", passed_db, f"Emp in DB: {emp_doc['emp_code'] if passed_db else None}")

    print("\n--- Phase 5 Verification Complete ---")

if __name__ == "__main__":
    run_all_qa_tests()
