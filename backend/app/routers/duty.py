"""值班排班：整周固定多人 + 临时时段调班。"""
import json
import sqlite3
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from ..db import get_db, now
from ..security import ROLE_NAMES, current_staff, parse_roles, require_permissions

router = APIRouter(prefix="/api/staff/duty", tags=["duty"])


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_range(week_start: str):
    try:
        start = datetime.strptime(week_start, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        start = date.today()
    start = monday_of(start)
    return start, start + timedelta(days=6)


def load_staff(conn, ids):
    if not ids:
        return []
    marks = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT id, name, phone, role, roles, active FROM staff WHERE id IN ({marks})",
        list(ids),
    ).fetchall()
    by_id = {r["id"]: r for r in rows}
    items = []
    for sid in ids:
        r = by_id.get(int(sid)) if str(sid).isdigit() or isinstance(sid, int) else None
        if not r or not r["active"]:
            continue
        items.append({
            "id": r["id"],
            "name": r["name"],
            "phone": r["phone"],
            "role_text": "、".join(
                ROLE_NAMES.get(x, x) for x in parse_roles(r["roles"], r["role"])
            ),
        })
    return items


def parse_ids(value) -> list:
    try:
        raw = json.loads(value or "[]")
    except (TypeError, ValueError):
        raw = []
    ids = []
    for x in raw:
        try:
            ids.append(int(x))
        except (TypeError, ValueError):
            continue
    return list(dict.fromkeys(ids))


def week_payload(conn, start: date):
    ws = start.isoformat()
    we = (start + timedelta(days=6)).isoformat()
    row = conn.execute(
        "SELECT * FROM duty_weeks WHERE week_start = ?", (ws,)
    ).fetchone()
    staff = load_staff(conn, parse_ids(row["staff_ids"])) if row else []
    adjustments = []
    for r in conn.execute(
        "SELECT * FROM duty_adjustments WHERE week_start = ? ORDER BY adjust_date, start_time",
        (ws,),
    ):
        adjustments.append({
            "id": r["id"],
            "adjust_date": r["adjust_date"],
            "start_time": r["start_time"],
            "end_time": r["end_time"],
            "note": r["note"],
            "staff": load_staff(conn, parse_ids(r["staff_ids"])),
        })
    return {
        "week_start": ws,
        "week_end": we,
        "note": row["note"] if row else "",
        "staff": staff,
        "adjustments": adjustments,
    }


def today_duty(conn):
    """今日值班：本周固定人员 + 今天的临时调班。"""
    today = date.today()
    start, _ = week_range(today.isoformat())
    data = week_payload(conn, start)
    items = [
        {"name": s["name"], "phone": s["phone"], "kind": "week", "time": ""}
        for s in data["staff"]
    ]
    for adj in data["adjustments"]:
        if adj["adjust_date"] != today.isoformat():
            continue
        for s in adj["staff"]:
            items.append({
                "name": s["name"],
                "phone": s["phone"],
                "kind": "temp",
                "time": f"{adj['start_time']}-{adj['end_time']}",
                "note": adj["note"],
            })
    return items, data


@router.get("")
def get_week(
    week_start: str = "",
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    start, _ = week_range(week_start or date.today().isoformat())
    data = week_payload(conn, start)
    today_items, _ = today_duty(conn)
    data["today"] = today_items
    return data


@router.put("/week")
def save_week(
    payload: dict,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_permissions("duty.manage")),
):
    start, _ = week_range(payload.get("week_start") or date.today().isoformat())
    ids = parse_ids(json.dumps(payload.get("staff_ids") or []))
    if len(ids) < 2:
        raise HTTPException(status_code=400, detail="整周值班至少需要选择 2 人")
    valid = load_staff(conn, ids)
    if len(valid) < 2:
        raise HTTPException(status_code=400, detail="所选人员不存在或已停用")
    note = (payload.get("note") or "").strip()
    ws = start.isoformat()
    conn.execute(
        "INSERT INTO duty_weeks(week_start, staff_ids, note, created_by, created_at)"
        " VALUES(?,?,?,?,?) ON CONFLICT(week_start) DO UPDATE SET"
        " staff_ids = excluded.staff_ids, note = excluded.note",
        (ws, json.dumps(ids), note, staff["id"], now()),
    )
    conn.commit()
    return {"ok": True}


@router.post("/adjustments")
def add_adjustment(
    payload: dict,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_permissions("duty.manage")),
):
    adjust_date = (payload.get("adjust_date") or "").strip()
    try:
        dt = datetime.strptime(adjust_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="调班日期格式应为 YYYY-MM-DD")
    start, end = week_range(payload.get("week_start") or adjust_date)
    if not (start <= dt <= end):
        raise HTTPException(status_code=400, detail="调班日期不在该周内")

    start_time = (payload.get("start_time") or "").strip()
    end_time = (payload.get("end_time") or "").strip()
    for value in (start_time, end_time):
        try:
            datetime.strptime(value, "%H:%M")
        except ValueError:
            raise HTTPException(status_code=400, detail="时间格式应为 HH:MM")
    if start_time >= end_time:
        raise HTTPException(status_code=400, detail="结束时间必须晚于开始时间")

    ids = parse_ids(json.dumps(payload.get("staff_ids") or []))
    if not ids:
        raise HTTPException(status_code=400, detail="请选择临时值班人员")
    if not load_staff(conn, ids):
        raise HTTPException(status_code=400, detail="所选人员不存在或已停用")

    conn.execute(
        "INSERT INTO duty_adjustments(week_start, adjust_date, start_time, end_time,"
        " staff_ids, note, created_by, created_at) VALUES(?,?,?,?,?,?,?,?)",
        (
            start.isoformat(), adjust_date, start_time, end_time,
            json.dumps(ids), (payload.get("note") or "").strip(),
            staff["id"], now(),
        ),
    )
    conn.commit()
    return {"ok": True}


@router.delete("/adjustments/{adjust_id}")
def delete_adjustment(
    adjust_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_permissions("duty.manage")),
):
    conn.execute("DELETE FROM duty_adjustments WHERE id = ?", (adjust_id,))
    conn.commit()
    return {"ok": True}


@router.get("/today")
def duty_today(
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    items, _ = today_duty(conn)
    return {"items": items}
