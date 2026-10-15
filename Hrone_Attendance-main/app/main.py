"""
Employee Attendance & Analytics API

Run: uvicorn app.main:app --port 8000
Env: MONGO_URI, MONGO_DB
"""
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
import os
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Path, Query
from pydantic import BaseModel, Field, field_validator
from pymongo import ASCENDING, DESCENDING, MongoClient, errors

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "attendance_db")

client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

IST = timezone(timedelta(hours=5, minutes=30))

MIN_EPOCH_MS = 100_000_000_000
MAX_EPOCH_MS = 4_102_444_800_000


def init_indexes():
    """Initializes database indexes idempotently at startup."""
    try:
        # employees collection
        db.employees.create_index([("emp_code", ASCENDING)], unique=True)
        db.employees.create_index([("department", ASCENDING), ("joined_on", ASCENDING)])

        # attendance_logs collection
        db.attendance_logs.create_index([("emp_code", ASCENDING), ("date", ASCENDING)], unique=True)
        db.attendance_logs.create_index([("date", DESCENDING), ("emp_code", ASCENDING)])
        db.attendance_logs.create_index([("emp_code", ASCENDING), ("date", ASCENDING), ("status", ASCENDING)])
        db.attendance_logs.create_index([("department", ASCENDING), ("date", ASCENDING)])
    except Exception as e:
        print(f"Warning: Index creation failed or pending DB connection: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_indexes()
    yield


app = FastAPI(title="Employee Attendance & Analytics API", version="2.0.0", lifespan=lifespan)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

init_indexes()


# --------------------------------------------------------------------------- #
# Calculation & Serialization Helpers
# --------------------------------------------------------------------------- #
def round_half_up(val: float, decimals: int = 2) -> float:
    """R8 & R4: Round half-up to specified decimal places."""
    d = Decimal(str(val))
    q = Decimal("10") ** -decimals
    return float(d.quantize(q, rounding=ROUND_HALF_UP))


def epoch_ms_to_datetime(ms: int) -> datetime:
    """Converts epoch milliseconds to naive UTC datetime with microsecond=0."""
    seconds = ms // 1000
    dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return dt.replace(tzinfo=None, microsecond=0)


def datetime_to_epoch_ms(dt: Optional[datetime]) -> Optional[int]:
    """Converts datetime to epoch milliseconds."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def compute_attendance_date(ts_utc: datetime, shift_start_str: str, shift_end_str: str) -> str:
    """
    R1: Attendance Date calculation in IST.
    For overnight shifts (shift_end <= shift_start), a punch-in whose IST time is strictly
    earlier than shift_end belongs to the shift that started the previous calendar day.
    """
    if ts_utc.tzinfo is None:
        ts_utc = ts_utc.replace(tzinfo=timezone.utc)
    ts_ist = ts_utc.astimezone(IST)
    sh_h, sh_m = map(int, shift_start_str.split(":"))
    eh_h, eh_m = map(int, shift_end_str.split(":"))

    is_overnight = (eh_h < sh_h) or (eh_h == sh_h and eh_m <= sh_m)

    if is_overnight:
        ist_time_tuple = (ts_ist.hour, ts_ist.minute)
        shift_end_tuple = (eh_h, eh_m)
        if ist_time_tuple < shift_end_tuple:
            prev_day = ts_ist.date() - timedelta(days=1)
            return prev_day.isoformat()

    return ts_ist.date().isoformat()


def compute_late_minutes(ts_utc: datetime, shift_start_str: str, date_str: str) -> int:
    """
    R2: Late Minutes calculation.
    Grace period is 10 minutes. Late only if strictly > 10 minutes (600s) past shift_start.
    Returns floor of whole minutes elapsed since shift_start.
    """
    sh_h, sh_m = map(int, shift_start_str.split(":"))
    d = date.fromisoformat(date_str)
    start_dt_ist = datetime(d.year, d.month, d.day, sh_h, sh_m, 0, tzinfo=IST)

    if ts_utc.tzinfo is None:
        ts_utc = ts_utc.replace(tzinfo=timezone.utc)
    ts_ist = ts_utc.astimezone(IST)
    diff_sec = (ts_ist - start_dt_ist).total_seconds()

    if diff_sec > 600:
        return int(diff_sec // 60)
    return 0


def compute_work_hours(punch_in_utc: datetime, punch_out_utc: datetime) -> float:
    """R4: Work Hours calculation rounded half-up to 2 decimals."""
    duration_sec = (punch_out_utc - punch_in_utc).total_seconds()
    raw_hours = duration_sec / 3600.0
    return round_half_up(raw_hours, 2)


def compute_overtime_minutes(punch_out_utc: datetime, shift_start_str: str, shift_end_str: str, date_str: str) -> int:
    """
    R3: Overtime Minutes calculation.
    Floor of whole minutes between shift_end and punch_out, counted only when >= 30; otherwise 0.
    Overnight shifts have shift_end on date + 1 day.
    """
    sh_h, sh_m = map(int, shift_start_str.split(":"))
    eh_h, eh_m = map(int, shift_end_str.split(":"))

    is_overnight = (eh_h < sh_h) or (eh_h == sh_h and eh_m <= sh_m)
    d = date.fromisoformat(date_str)

    if is_overnight:
        end_date = d + timedelta(days=1)
    else:
        end_date = d

    end_dt_ist = datetime(end_date.year, end_date.month, end_date.day, eh_h, eh_m, 0, tzinfo=IST)
    if punch_out_utc.tzinfo is None:
        punch_out_utc = punch_out_utc.replace(tzinfo=timezone.utc)
    punch_out_ist = punch_out_utc.astimezone(IST)

    diff_sec = (punch_out_ist - end_dt_ist).total_seconds()
    diff_min = int(diff_sec // 60)

    if diff_min >= 30:
        return diff_min
    return 0


def compute_half_day(work_hours: float) -> bool:
    """R5: Half Day calculation (True when rounded work_hours < 4.50)."""
    return work_hours < 4.50


def serialize_employee(doc: dict) -> dict:
    return {
        "emp_code": doc["emp_code"],
        "name": doc["name"],
        "email": doc["email"],
        "department": doc["department"],
        "shift_start": doc["shift_start"],
        "shift_end": doc["shift_end"],
        "joined_on": doc["joined_on"],
        "created_at": datetime_to_epoch_ms(doc.get("created_at")),
    }


def serialize_history_entry(entry: dict) -> dict:
    changes = {}
    raw_changes = entry.get("changes", {})
    for k, v in raw_changes.items():
        if k in ("punch_in", "punch_out"):
            frm = datetime_to_epoch_ms(v.get("from")) if isinstance(v.get("from"), datetime) else v.get("from")
            to_val = datetime_to_epoch_ms(v.get("to")) if isinstance(v.get("to"), datetime) else v.get("to")
            changes[k] = {"from": frm, "to": to_val}
        else:
            changes[k] = {"from": v.get("from"), "to": v.get("to")}

    at_val = datetime_to_epoch_ms(entry.get("at")) if isinstance(entry.get("at"), datetime) else entry.get("at")
    return {
        "at": at_val,
        "by": entry.get("by"),
        "reason": entry.get("reason"),
        "changes": changes,
    }


def serialize_attendance_log(doc: dict) -> dict:
    history = [serialize_history_entry(h) for h in doc.get("history", [])]
    return {
        "emp_code": doc["emp_code"],
        "date": doc["date"],
        "status": doc["status"],
        "punch_in": datetime_to_epoch_ms(doc.get("punch_in")),
        "punch_out": datetime_to_epoch_ms(doc.get("punch_out")),
        "work_hours": doc.get("work_hours"),
        "late_minutes": doc.get("late_minutes", 0),
        "overtime_minutes": doc.get("overtime_minutes", 0),
        "half_day": doc.get("half_day", False),
        "history": history,
    }


def get_month_date_range(month_str: str) -> tuple[date, date]:
    year, month = map(int, month_str.split("-"))
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, month + 1, 1) - timedelta(days=1)
    return start_date, end_date


def calculate_working_days(month_start: date, month_end: date, joined_on_str: str) -> int:
    joined_date = date.fromisoformat(joined_on_str)
    effective_start = max(month_start, joined_date)
    if effective_start > month_end:
        return 0
    working_days = 0
    curr = effective_start
    while curr <= month_end:
        if curr.weekday() < 5:  # Mon=0..Fri=4
            working_days += 1
        curr += timedelta(days=1)
    return working_days


# --------------------------------------------------------------------------- #
# Pydantic Schemas
# --------------------------------------------------------------------------- #
class EmployeeCreate(BaseModel):
    emp_code: str = Field(..., pattern=r"^EMP\d{4,6}$")
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=120, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    department: str = Field(..., min_length=1, max_length=50)
    shift_start: str = Field("09:30", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    shift_end: str = Field("18:30", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    joined_on: str = Field(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$")

    @field_validator("joined_on")
    @classmethod
    def validate_joined_on(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("Invalid date format")
        return v


class PunchInRequest(BaseModel):
    emp_code: str
    punched_at: Optional[int] = Field(None, ge=MIN_EPOCH_MS, le=MAX_EPOCH_MS)
    status: str = Field("PRESENT", pattern=r"^(PRESENT|WFH|ON_DUTY)$")


class PunchOutRequest(BaseModel):
    emp_code: str
    punched_at: Optional[int] = Field(None, ge=MIN_EPOCH_MS, le=MAX_EPOCH_MS)


class RegularizeRequest(BaseModel):
    status: Optional[str] = Field(None, pattern=r"^(PRESENT|ABSENT|LEAVE|WFH|ON_DUTY)$")
    punch_in: Optional[int] = Field(None, ge=MIN_EPOCH_MS, le=MAX_EPOCH_MS)
    punch_out: Optional[int] = Field(None, ge=MIN_EPOCH_MS, le=MAX_EPOCH_MS)
    reason: str = Field(..., min_length=5, max_length=200)
    regularized_by: str = Field(..., min_length=1, max_length=50)


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.get("/health")
def health():
    try:
        client.admin.command("ping")
        return {"status": "ok"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")


@app.post("/employees", status_code=201)
def create_employee(body: EmployeeCreate):
    if body.shift_start == body.shift_end:
        raise HTTPException(status_code=422, detail="shift_start and shift_end must differ")

    doc = body.model_dump()
    doc["created_at"] = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)

    try:
        db.employees.insert_one(doc)
    except errors.DuplicateKeyError:
        raise HTTPException(status_code=409, detail="emp_code already exists")

    return serialize_employee(doc)


@app.get("/employees")
def list_employees(
    department: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    q = {}
    if department is not None:
        q["department"] = department

    total = db.employees.count_documents(q)
    skip = (page - 1) * page_size
    cursor = db.employees.find(q, {"_id": 0}).sort("emp_code", ASCENDING).skip(skip).limit(page_size)
    items = [serialize_employee(doc) for doc in cursor]

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@app.post("/attendance/punch-in", status_code=201)
def punch_in(body: PunchInRequest):
    emp = db.employees.find_one({"emp_code": body.emp_code})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    punched_at_ms = body.punched_at if body.punched_at is not None else int(datetime.now(timezone.utc).timestamp() * 1000)
    ts_utc = epoch_ms_to_datetime(punched_at_ms)

    att_date = compute_attendance_date(ts_utc, emp["shift_start"], emp["shift_end"])
    late_mins = compute_late_minutes(ts_utc, emp["shift_start"], att_date)

    doc = {
        "emp_code": body.emp_code,
        "date": att_date,
        "status": body.status,
        "punch_in": ts_utc,
        "punch_out": None,
        "work_hours": None,
        "late_minutes": late_mins,
        "overtime_minutes": 0,
        "half_day": False,
        "history": [],
    }

    try:
        db.attendance_logs.insert_one(doc)
    except errors.DuplicateKeyError:
        raise HTTPException(status_code=409, detail="already punched in for this date")

    return serialize_attendance_log(doc)


@app.post("/attendance/punch-out", status_code=200)
def punch_out(body: PunchOutRequest):
    emp = db.employees.find_one({"emp_code": body.emp_code})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    punched_at_ms = body.punched_at if body.punched_at is not None else int(datetime.now(timezone.utc).timestamp() * 1000)
    ts_out_utc = epoch_ms_to_datetime(punched_at_ms)

    # Find open record for employee
    open_doc = db.attendance_logs.find_one(
        {
            "emp_code": body.emp_code,
            "punch_out": None,
        },
        sort=[("punch_in", DESCENDING)],
    )

    if not open_doc:
        raise HTTPException(status_code=404, detail="No open punch-in record found for employee")

    ts_in_utc = open_doc["punch_in"]

    if ts_out_utc <= ts_in_utc:
        raise HTTPException(status_code=422, detail="punched_at must be strictly greater than punch_in")

    if (ts_out_utc - ts_in_utc).total_seconds() > 86400:
        raise HTTPException(status_code=422, detail="punch_out cannot be more than 24 hours after punch_in")

    work_hrs = compute_work_hours(ts_in_utc, ts_out_utc)
    ot_mins = compute_overtime_minutes(ts_out_utc, emp["shift_start"], emp["shift_end"], open_doc["date"])
    is_half = compute_half_day(work_hrs)

    updated_doc = db.attendance_logs.find_one_and_update(
        {"_id": open_doc["_id"], "punch_out": None},
        {
            "$set": {
                "punch_out": ts_out_utc,
                "work_hours": work_hrs,
                "overtime_minutes": ot_mins,
                "half_day": is_half,
            }
        },
        return_document=True,
    )

    if not updated_doc:
        raise HTTPException(status_code=409, detail="Record is already punched out")

    return serialize_attendance_log(updated_doc)


@app.get("/attendance")
def list_attendance(
    emp_code: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$"),
    date_to: Optional[str] = Query(None, pattern=r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$"),
    status: Optional[str] = Query(None, pattern=r"^(PRESENT|ABSENT|LEAVE|WFH|ON_DUTY)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from cannot be greater than date_to")

    q = {}
    if emp_code:
        q["emp_code"] = emp_code
    if status:
        q["status"] = status
    if date_from or date_to:
        q["date"] = {}
        if date_from:
            q["date"]["$gte"] = date_from
        if date_to:
            q["date"]["$lte"] = date_to

    total = db.attendance_logs.count_documents(q)
    skip = (page - 1) * page_size
    cursor = db.attendance_logs.find(q, {"_id": 0}).sort([("date", DESCENDING), ("emp_code", ASCENDING)]).skip(skip).limit(page_size)
    items = [serialize_attendance_log(doc) for doc in cursor]

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@app.patch("/attendance/{emp_code}/{date}")
def regularize_attendance(
    emp_code: str = Path(...),
    date_str: str = Path(..., alias="date", pattern=r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$"),
    body: RegularizeRequest = ...,
):
    emp = db.employees.find_one({"emp_code": emp_code})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    log = db.attendance_logs.find_one({"emp_code": emp_code, "date": date_str})
    if not log:
        raise HTTPException(status_code=404, detail="Attendance record not found for date")

    target_status = body.status if body.status is not None else log["status"]

    if body.status in ("ABSENT", "LEAVE"):
        if body.punch_in is not None or body.punch_out is not None:
            raise HTTPException(status_code=422, detail="Cannot supply punch_in or punch_out when setting status to ABSENT or LEAVE")

    if target_status in ("PRESENT", "WFH", "ON_DUTY"):
        in_ms = body.punch_in if body.punch_in is not None else datetime_to_epoch_ms(log.get("punch_in"))
        if in_ms is None:
            raise HTTPException(status_code=422, detail="Presence status requires a punch_in")

    if target_status in ("ABSENT", "LEAVE"):
        new_punch_in = None
        new_punch_out = None
        new_work_hours = None
        new_late_minutes = 0
        new_overtime_minutes = 0
        new_half_day = False
    else:
        in_ms = body.punch_in if body.punch_in is not None else datetime_to_epoch_ms(log.get("punch_in"))
        new_punch_in = epoch_ms_to_datetime(in_ms)

        calc_date = compute_attendance_date(new_punch_in, emp["shift_start"], emp["shift_end"])
        if calc_date != date_str:
            raise HTTPException(status_code=422, detail="punch_in must stay on the record's attendance date")

        out_ms = body.punch_out if body.punch_out is not None else datetime_to_epoch_ms(log.get("punch_out"))
        if out_ms is not None:
            new_punch_out = epoch_ms_to_datetime(out_ms)
            if new_punch_out <= new_punch_in:
                raise HTTPException(status_code=422, detail="punch_out must be strictly greater than punch_in")
            if (new_punch_out - new_punch_in).total_seconds() > 86400:
                raise HTTPException(status_code=422, detail="punch_out cannot be more than 24 hours after punch_in")
            new_work_hours = compute_work_hours(new_punch_in, new_punch_out)
            new_overtime_minutes = compute_overtime_minutes(new_punch_out, emp["shift_start"], emp["shift_end"], date_str)
            new_half_day = compute_half_day(new_work_hours)
        else:
            new_punch_out = None
            new_work_hours = None
            new_overtime_minutes = 0
            new_half_day = False

        new_late_minutes = compute_late_minutes(new_punch_in, emp["shift_start"], date_str)

    changes = {}
    old_status = log["status"]
    if target_status != old_status:
        changes["status"] = {"from": old_status, "to": target_status}

    old_in_ms = datetime_to_epoch_ms(log.get("punch_in"))
    new_in_ms = datetime_to_epoch_ms(new_punch_in)
    if old_in_ms != new_in_ms:
        changes["punch_in"] = {"from": log.get("punch_in"), "to": new_punch_in}

    old_out_ms = datetime_to_epoch_ms(log.get("punch_out"))
    new_out_ms = datetime_to_epoch_ms(new_punch_out)
    if old_out_ms != new_out_ms:
        changes["punch_out"] = {"from": log.get("punch_out"), "to": new_punch_out}

    if log.get("work_hours") != new_work_hours:
        changes["work_hours"] = {"from": log.get("work_hours"), "to": new_work_hours}

    if log.get("late_minutes", 0) != new_late_minutes:
        changes["late_minutes"] = {"from": log.get("late_minutes", 0), "to": new_late_minutes}

    if log.get("overtime_minutes", 0) != new_overtime_minutes:
        changes["overtime_minutes"] = {"from": log.get("overtime_minutes", 0), "to": new_overtime_minutes}

    if log.get("half_day", False) != new_half_day:
        changes["half_day"] = {"from": log.get("half_day", False), "to": new_half_day}

    if not changes:
        raise HTTPException(status_code=422, detail="No changes detected in regularization request")

    history_entry = {
        "at": datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0),
        "by": body.regularized_by,
        "reason": body.reason,
        "changes": changes,
    }

    old_history = log.get("history", [])
    updated = db.attendance_logs.find_one_and_update(
        {"_id": log["_id"], "history": old_history},
        {
            "$set": {
                "status": target_status,
                "punch_in": new_punch_in,
                "punch_out": new_punch_out,
                "work_hours": new_work_hours,
                "late_minutes": new_late_minutes,
                "overtime_minutes": new_overtime_minutes,
                "half_day": new_half_day,
            },
            "$push": {"history": history_entry},
        },
        return_document=True,
    )

    if not updated:
        raise HTTPException(status_code=409, detail="Concurrent modification detected on history")

    return serialize_attendance_log(updated)


@app.get("/analytics/employees/{emp_code}/monthly")
def employee_monthly_analytics(
    emp_code: str = Path(...),
    month: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
):
    emp = db.employees.find_one({"emp_code": emp_code})
    if not emp:
        raise HTTPException(status_code=404, detail="Employee not found")

    month_start, month_end = get_month_date_range(month)
    working_days = calculate_working_days(month_start, month_end, emp["joined_on"])

    pipeline = [
        {
            "$match": {
                "emp_code": emp_code,
                "date": {"$gte": month_start.isoformat(), "$lte": month_end.isoformat()},
            }
        },
        {
            "$addFields": {
                "date_obj": {"$dateFromString": {"dateString": "$date"}},
            }
        },
        {
            "$addFields": {
                "dow": {"$dayOfWeek": "$date_obj"},
                "is_present_status": {"$in": ["$status", ["PRESENT", "WFH", "ON_DUTY"]]},
            }
        },
        {
            "$group": {
                "_id": None,
                "present_days": {
                    "$sum": {
                        "$cond": [
                            {"$and": [{"$in": ["$dow", [2, 3, 4, 5, 6]]}, "$is_present_status"]},
                            {"$cond": ["$half_day", 0.5, 1.0]},
                            0.0,
                        ]
                    }
                },
                "leave_days": {
                    "$sum": {"$cond": [{"$eq": ["$status", "LEAVE"]}, 1, 0]}
                },
                "late_count": {
                    "$sum": {"$cond": [{"$gt": ["$late_minutes", 0]}, 1, 0]}
                },
                "total_late_minutes": {"$sum": "$late_minutes"},
                "total_overtime_minutes": {"$sum": "$overtime_minutes"},
            }
        },
    ]

    results = list(db.attendance_logs.aggregate(pipeline))
    if results:
        res = results[0]
        present_days = float(res.get("present_days", 0.0))
        leave_days = int(res.get("leave_days", 0))
        late_count = int(res.get("late_count", 0))
        total_late_minutes = int(res.get("total_late_minutes", 0))
        total_overtime_minutes = int(res.get("total_overtime_minutes", 0))
    else:
        present_days = 0.0
        leave_days = 0
        late_count = 0
        total_late_minutes = 0
        total_overtime_minutes = 0

    attendance_pct = round_half_up((present_days / working_days) * 100, 2) if working_days > 0 else None

    return {
        "emp_code": emp_code,
        "month": month,
        "working_days": working_days,
        "present_days": present_days,
        "leave_days": leave_days,
        "late_count": late_count,
        "total_late_minutes": total_late_minutes,
        "total_overtime_minutes": total_overtime_minutes,
        "attendance_pct": attendance_pct,
    }


@app.get("/analytics/departments/summary")
def department_summary_analytics(
    month: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    department: Optional[str] = Query(None),
):
    month_start, month_end = get_month_date_range(month)
    month_end_str = month_end.isoformat()

    emp_match = {"joined_on": {"$lte": month_end_str}}
    if department:
        emp_match["department"] = department

    pipeline = [
        {"$match": emp_match},
        {
            "$lookup": {
                "from": "attendance_logs",
                "let": {"code": "$emp_code"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$emp_code", "$$code"]},
                                    {"$gte": ["$date", month_start.isoformat()]},
                                    {"$lte": ["$date", month_end_str]},
                                ]
                            }
                        }
                    }
                ],
                "as": "logs",
            }
        },
        {
            "$project": {
                "emp_code": 1,
                "department": 1,
                "logs": 1,
            }
        },
        {"$unwind": {"path": "$logs", "preserveNullAndEmptyArrays": True}},
        {
            "$addFields": {
                "log_date_obj": {
                    "$cond": [
                        {"$ifNull": ["$logs.date", False]},
                        {"$dateFromString": {"dateString": "$logs.date"}},
                        None,
                    ]
                }
            }
        },
        {
            "$addFields": {
                "dow": {"$cond": ["$log_date_obj", {"$dayOfWeek": "$log_date_obj"}, None]},
                "is_present_status": {
                    "$cond": [
                        {"$ifNull": ["$logs.status", False]},
                        {"$in": ["$logs.status", ["PRESENT", "WFH", "ON_DUTY"]]},
                        False,
                    ]
                },
            }
        },
        {
            "$group": {
                "_id": {
                    "department": "$department",
                    "emp_code": "$emp_code",
                },
                "present_days": {
                    "$sum": {
                        "$cond": [
                            {"$and": [{"$in": ["$dow", [2, 3, 4, 5, 6]]}, "$is_present_status"]},
                            {"$cond": ["$logs.half_day", 0.5, 1.0]},
                            0.0,
                        ]
                    }
                },
                "late_count": {
                    "$sum": {"$cond": [{"$gt": [{"$ifNull": ["$logs.late_minutes", 0]}, 0]}, 1, 0]}
                },
                "total_late_minutes": {
                    "$sum": {"$ifNull": ["$logs.late_minutes", 0]}
                },
                "leave_count": {
                    "$sum": {"$cond": [{"$eq": ["$logs.status", "LEAVE"]}, 1, 0]}
                },
                "on_duty_count": {
                    "$sum": {"$cond": [{"$eq": ["$logs.status", "ON_DUTY"]}, 1, 0]}
                },
                "valid_work_hours": {
                    "$push": {
                        "$cond": [
                            {"$and": ["$is_present_status", {"$ne": ["$logs.work_hours", None]}]},
                            "$logs.work_hours",
                            "$$REMOVE",
                        ]
                    }
                },
            }
        },
        {
            "$group": {
                "_id": "$_id.department",
                "headcount": {"$sum": 1},
                "present_days": {"$sum": "$present_days"},
                "late_count": {"$sum": "$late_count"},
                "total_late_minutes": {"$sum": "$total_late_minutes"},
                "leave_count": {"$sum": "$leave_count"},
                "on_duty_count": {"$sum": "$on_duty_count"},
                "all_work_hours": {"$push": "$valid_work_hours"},
            }
        },
        {
            "$addFields": {
                "flat_work_hours": {
                    "$reduce": {
                        "input": "$all_work_hours",
                        "initialValue": [],
                        "in": {"$concatArrays": ["$$value", "$$this"]},
                    }
                }
            }
        },
        {
            "$addFields": {
                "avg_work_hours": {
                    "$cond": [
                        {"$gt": [{"$size": "$flat_work_hours"}, 0]},
                        {"$avg": "$flat_work_hours"},
                        None,
                    ]
                }
            }
        },
        {"$sort": {"_id": 1}},
    ]

    results = list(db.employees.aggregate(pipeline))
    items = []
    for r in results:
        avg_wh = float(r["avg_work_hours"]) if r["avg_work_hours"] is not None else None
        if avg_wh is not None:
            avg_wh = round_half_up(avg_wh, 2)

        items.append({
            "department": r["_id"],
            "headcount": int(r["headcount"]),
            "present_days": float(r["present_days"]),
            "avg_work_hours": avg_wh,
            "late_count": int(r["late_count"]),
            "total_late_minutes": int(r["total_late_minutes"]),
            "leave_count": int(r["leave_count"]),
            "on_duty_count": int(r["on_duty_count"]),
        })

    return {"month": month, "items": items}


@app.get("/analytics/leaderboard/late")
def late_leaderboard_analytics(
    month: str = Query(..., pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
    limit: int = Query(10, ge=1, le=50),
    department: Optional[str] = Query(None),
):
    month_start, month_end = get_month_date_range(month)

    pipeline = [
        {
            "$match": {
                "date": {"$gte": month_start.isoformat(), "$lte": month_end.isoformat()},
                "late_minutes": {"$gt": 0},
            }
        },
        {
            "$lookup": {
                "from": "employees",
                "localField": "emp_code",
                "foreignField": "emp_code",
                "as": "emp",
            }
        },
        {"$unwind": "$emp"},
    ]

    if department:
        pipeline.append({"$match": {"emp.department": department}})

    pipeline.extend([
        {
            "$group": {
                "_id": "$emp_code",
                "name": {"$first": "$emp.name"},
                "department": {"$first": "$emp.department"},
                "total_late_minutes": {"$sum": "$late_minutes"},
                "late_count": {"$sum": 1},
            }
        },
        {
            "$setWindowFields": {
                "sortBy": {"total_late_minutes": -1},
                "output": {
                    "rank": {"$rank": {}}
                },
            }
        },
        {"$match": {"rank": {"$lte": limit}}},
        {"$sort": {"rank": 1, "_id": 1}},
    ])

    results = list(db.attendance_logs.aggregate(pipeline))
    items = []
    for r in results:
        items.append({
            "rank": int(r["rank"]),
            "emp_code": r["_id"],
            "name": r["name"],
            "department": r["department"],
            "total_late_minutes": int(r["total_late_minutes"]),
            "late_count": int(r["late_count"]),
        })

    return {"month": month, "items": items}


@app.get("/analytics/departments/{department}/trend")
def department_trend_analytics(
    department: str = Path(...),
    from_date_str: str = Query(..., alias="from", pattern=r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$"),
    to_date_str: str = Query(..., alias="to", pattern=r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$"),
):
    dept_count = db.employees.count_documents({"department": department})
    if dept_count == 0:
        raise HTTPException(status_code=404, detail="Department not found")

    d_from = date.fromisoformat(from_date_str)
    d_to = date.fromisoformat(to_date_str)

    if d_to < d_from:
        raise HTTPException(status_code=422, detail="to date cannot be earlier than from date")
    if (d_to - d_from).days > 92:
        raise HTTPException(status_code=422, detail="Date range cannot exceed 92 days")

    pipeline = [
        {"$match": {"department": department}},
        {
            "$lookup": {
                "from": "attendance_logs",
                "let": {"code": "$emp_code"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$emp_code", "$$code"]},
                                    {"$gte": ["$date", from_date_str]},
                                    {"$lte": ["$date", to_date_str]},
                                ]
                            }
                        }
                    }
                ],
                "as": "logs",
            }
        },
        {"$unwind": {"path": "$logs", "preserveNullAndEmptyArrays": True}},
        {
            "$project": {
                "emp_code": 1,
                "joined_on": 1,
                "log_date": "$logs.date",
                "status": "$logs.status",
                "half_day": "$logs.half_day",
                "late_minutes": "$logs.late_minutes",
            }
        },
    ]

    raw_data = list(db.employees.aggregate(pipeline))

    daily_records = {}
    curr = d_from
    while curr <= d_to:
        daily_records[curr.isoformat()] = {
            "date": curr.isoformat(),
            "is_working_day": (curr.weekday() < 5),
            "headcount": 0,
            "present_count": 0.0,
            "late_count": 0,
        }
        curr += timedelta(days=1)

    employees = list(db.employees.find({"department": department}, {"_id": 0, "emp_code": 1, "joined_on": 1}))
    for item in daily_records.values():
        d_str = item["date"]
        item["headcount"] = sum(1 for e in employees if e["joined_on"] <= d_str)

    for doc in raw_data:
        log_date = doc.get("log_date")
        if log_date and log_date in daily_records:
            st = doc.get("status")
            half = doc.get("half_day", False)
            late = doc.get("late_minutes", 0)

            if st in ("PRESENT", "WFH", "ON_DUTY"):
                daily_records[log_date]["present_count"] += 0.5 if half else 1.0
            if late and late > 0:
                daily_records[log_date]["late_count"] += 1

    items = []
    dates_sorted = sorted(daily_records.keys())
    rates = []

    for i, d_str in enumerate(dates_sorted):
        rec = daily_records[d_str]
        is_wk = rec["is_working_day"]
        hc = rec["headcount"]
        pr = rec["present_count"]

        if is_wk and hc > 0:
            rate = round_half_up(pr / float(hc), 4)
        else:
            rate = None
        rates.append(rate)

        window = [r for r in rates[max(0, i - 6) : i + 1] if r is not None]
        if window:
            m_avg = round_half_up(sum(window) / len(window), 4)
        else:
            m_avg = None

        items.append({
            "date": d_str,
            "is_working_day": is_wk,
            "headcount": hc,
            "present_count": pr,
            "late_count": rec["late_count"],
            "attendance_rate": rate,
            "moving_avg_7d": m_avg,
        })

    return {"department": department, "items": items}


@app.get("/admin/explain/{endpoint}")
def explain_endpoint(
    endpoint: str = Path(...),
    emp_code: Optional[str] = Query(None),
    month: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    limit: Optional[int] = Query(10),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    page: Optional[int] = Query(1),
    page_size: Optional[int] = Query(20),
):
    if endpoint == "attendance_list":
        q = {}
        if emp_code:
            q["emp_code"] = emp_code
        if status:
            q["status"] = status
        if date_from or date_to:
            q["date"] = {}
            if date_from:
                q["date"]["$gte"] = date_from
            if date_to:
                q["date"]["$lte"] = date_to
        skip = (page - 1) * page_size
        explain_res = db.command(
            "explain",
            {
                "find": "attendance_logs",
                "filter": q,
                "sort": {"date": -1, "emp_code": 1},
                "skip": skip,
                "limit": page_size,
            },
            verbosity="executionStats",
        )
        return {"endpoint": endpoint, "collection": "attendance_logs", "explain": explain_res}

    elif endpoint == "employee_monthly":
        if not emp_code or not month:
            raise HTTPException(status_code=422, detail="emp_code and month required")
        month_start, month_end = get_month_date_range(month)
        pipeline = [
            {
                "$match": {
                    "emp_code": emp_code,
                    "date": {"$gte": month_start.isoformat(), "$lte": month_end.isoformat()},
                }
            },
            {"$addFields": {"date_obj": {"$dateFromString": {"dateString": "$date"}}}},
            {"$addFields": {"dow": {"$dayOfWeek": "$date_obj"}, "is_present_status": {"$in": ["$status", ["PRESENT", "WFH", "ON_DUTY"]]}}},
            {
                "$group": {
                    "_id": None,
                    "present_days": {
                        "$sum": {
                            "$cond": [
                                {"$and": [{"$in": ["$dow", [2, 3, 4, 5, 6]]}, "$is_present_status"]},
                                {"$cond": ["$half_day", 0.5, 1.0]},
                                0.0,
                            ]
                        }
                    },
                    "leave_days": {"$sum": {"$cond": [{"$eq": ["$status", "LEAVE"]}, 1, 0]}},
                    "late_count": {"$sum": {"$cond": [{"$gt": ["$late_minutes", 0]}, 1, 0]}},
                    "total_late_minutes": {"$sum": "$late_minutes"},
                    "total_overtime_minutes": {"$sum": "$overtime_minutes"},
                }
            },
        ]
        explain_res = db.command("explain", {"aggregate": "attendance_logs", "pipeline": pipeline, "cursor": {}}, verbosity="executionStats")
        return {"endpoint": endpoint, "collection": "attendance_logs", "explain": explain_res}

    elif endpoint == "department_summary":
        if not month:
            raise HTTPException(status_code=422, detail="month required")
        month_start, month_end = get_month_date_range(month)
        month_end_str = month_end.isoformat()
        emp_match = {"joined_on": {"$lte": month_end_str}}
        if department:
            emp_match["department"] = department
        pipeline = [
            {"$match": emp_match},
            {
                "$lookup": {
                    "from": "attendance_logs",
                    "let": {"code": "$emp_code"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$emp_code", "$$code"]},
                                        {"$gte": ["$date", month_start.isoformat()]},
                                        {"$lte": ["$date", month_end_str]},
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "logs",
                }
            },
            {"$unwind": {"path": "$logs", "preserveNullAndEmptyArrays": True}},
        ]
        explain_res = db.command("explain", {"aggregate": "employees", "pipeline": pipeline, "cursor": {}}, verbosity="executionStats")
        return {"endpoint": endpoint, "collection": "employees", "explain": explain_res}

    elif endpoint == "late_leaderboard":
        if not month:
            raise HTTPException(status_code=422, detail="month required")
        month_start, month_end = get_month_date_range(month)
        pipeline = [
            {
                "$match": {
                    "date": {"$gte": month_start.isoformat(), "$lte": month_end.isoformat()},
                    "late_minutes": {"$gt": 0},
                }
            },
            {
                "$lookup": {
                    "from": "employees",
                    "localField": "emp_code",
                    "foreignField": "emp_code",
                    "as": "emp",
                }
            },
            {"$unwind": "$emp"},
        ]
        if department:
            pipeline.append({"$match": {"emp.department": department}})
        pipeline.extend([
            {
                "$group": {
                    "_id": "$emp_code",
                    "name": {"$first": "$emp.name"},
                    "department": {"$first": "$emp.department"},
                    "total_late_minutes": {"$sum": "$late_minutes"},
                    "late_count": {"$sum": 1},
                }
            },
            {
                "$setWindowFields": {
                    "sortBy": {"total_late_minutes": -1},
                    "output": {"rank": {"$rank": {}}},
                }
            },
            {"$match": {"rank": {"$lte": limit if limit else 10}}},
            {"$sort": {"rank": 1, "_id": 1}},
        ])
        explain_res = db.command("explain", {"aggregate": "attendance_logs", "pipeline": pipeline, "cursor": {}}, verbosity="executionStats")
        return {"endpoint": endpoint, "collection": "attendance_logs", "explain": explain_res}

    elif endpoint == "department_trend":
        if not department or not from_date or not to_date:
            raise HTTPException(status_code=422, detail="department, from, to required")
        pipeline = [
            {"$match": {"department": department}},
            {
                "$lookup": {
                    "from": "attendance_logs",
                    "let": {"code": "$emp_code"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$and": [
                                        {"$eq": ["$emp_code", "$$code"]},
                                        {"$gte": ["$date", from_date]},
                                        {"$lte": ["$date", to_date]},
                                    ]
                                }
                            }
                        }
                    ],
                    "as": "logs",
                }
            },
            {"$unwind": {"path": "$logs", "preserveNullAndEmptyArrays": True}},
        ]
        explain_res = db.command("explain", {"aggregate": "employees", "pipeline": pipeline, "cursor": {}}, verbosity="executionStats")
        return {"endpoint": endpoint, "collection": "employees", "explain": explain_res}

    else:
        raise HTTPException(status_code=422, detail="Invalid endpoint name")
