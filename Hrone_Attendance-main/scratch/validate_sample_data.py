import json
import os
from datetime import datetime, timezone
from fastapi.testclient import TestClient

os.environ["MONGO_URI"] = "mongodb://localhost:27017"
os.environ["MONGO_DB"] = "test_sample_data_db"

from app.main import app, db

client = TestClient(app)

db.employees.delete_many({})
db.attendance_logs.delete_many({})

def parse_ext_json_date(dt_obj):
    if isinstance(dt_obj, dict) and "$date" in dt_obj:
        val = dt_obj["$date"]
        if isinstance(val, str):
            return datetime.fromisoformat(val.replace("Z", "+00:00")).replace(tzinfo=None)
    return dt_obj

with open("sample_data/employees.json") as f:
    emps = json.load(f)
    for e in emps:
        if "created_at" in e:
            e["created_at"] = parse_ext_json_date(e["created_at"])
        db.employees.insert_one(e)

with open("sample_data/attendance_logs.json") as f:
    logs = json.load(f)
    for l in logs:
        l["punch_in"] = parse_ext_json_date(l.get("punch_in"))
        l["punch_out"] = parse_ext_json_date(l.get("punch_out"))
        if "history" in l:
            for h in l["history"]:
                h["at"] = parse_ext_json_date(h.get("at"))
                if "changes" in h:
                    for ck, cv in h["changes"].items():
                        if isinstance(cv, dict):
                            cv["from"] = parse_ext_json_date(cv.get("from"))
                            cv["to"] = parse_ext_json_date(cv.get("to"))
        db.attendance_logs.insert_one(l)

print(f"Seeded {db.employees.count_documents({})} employees and {db.attendance_logs.count_documents({})} logs.")

# Run endpoint checks
r_emp = client.get("/employees")
assert r_emp.status_code == 200
print("GET /employees count:", len(r_emp.json()["items"]))

r_att = client.get("/attendance")
assert r_att.status_code == 200
print("GET /attendance count:", len(r_att.json()["items"]))

r_summary = client.get("/analytics/departments/summary?month=2026-07")
assert r_summary.status_code == 200
print("GET /analytics/departments/summary items:", r_summary.json()["items"])

r_leader = client.get("/analytics/leaderboard/late?month=2026-07")
assert r_leader.status_code == 200
print("GET /analytics/leaderboard/late items:", r_leader.json()["items"])

r_trend = client.get("/analytics/departments/Engineering/trend?from=2026-07-06&to=2026-07-10")
assert r_trend.status_code == 200
print("GET /analytics/departments/Engineering/trend count:", len(r_trend.json()["items"]))

r_explain = client.get("/admin/explain/attendance_list")
assert r_explain.status_code == 200
print("GET /admin/explain/attendance_list:", r_explain.json()["endpoint"])
