"""面向报障人（免登录）的接口。"""
import json
import sqlite3
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException

from ..db import get_db, now
from ..media import MAX_PHOTOS, save_data_url
from ..schemas import ConfirmIn, TicketCreateIn
from ..security import reporter_identity
from ..tickets_common import STATUS_TEXT, add_log, gen_code

router = APIRouter(prefix="/api/public", tags=["public"])

PUBLIC_FIELDS = (
    "id, code, status, location, device, fault_type, description, contact_name,"
    " contact_phone, expect_time, photos, created_at, accepted_at, started_at,"
    " finished_at, confirm_at, rating, confirm_comment, signature, fault_cause,"
    " solve_note, room_id, assignee_id, dispatcher_id, reporter_id"
)

# 简单的内存限流：同一匿名身份 10 分钟内最多查询 10 次
_LOOKUP_LOG: dict = {}
_LOOKUP_WINDOW = 600
_LOOKUP_LIMIT = 10


def _rate_limited(key: str) -> bool:
    now_ts = time.time()
    hits = [t for t in _LOOKUP_LOG.get(key, []) if now_ts - t < _LOOKUP_WINDOW]
    if len(hits) >= _LOOKUP_LIMIT:
        _LOOKUP_LOG[key] = hits
        return True
    hits.append(now_ts)
    _LOOKUP_LOG[key] = hits
    return False


def mask_phone(phone: str) -> str:
    if len(phone) >= 7:
        return phone[:3] + "****" + phone[-4:]
    return phone


def public_ticket(conn: sqlite3.Connection, row, is_owner: bool) -> dict:
    data = dict(row)
    data["status_text"] = STATUS_TEXT.get(data["status"], data["status"])
    data["contact_phone"] = mask_phone(data["contact_phone"])
    data["is_owner"] = is_owner
    assignee = None
    if data.get("assignee_id"):
        r = conn.execute(
            "SELECT name FROM staff WHERE id = ?", (data["assignee_id"],)
        ).fetchone()
        assignee = r["name"] if r else None
    data["assignee_name"] = assignee
    try:
        data["photos"] = json.loads(data.get("photos") or "[]")
    except (TypeError, ValueError):
        data["photos"] = []
    data["materials"] = [
        dict(m)
        for m in conn.execute(
            "SELECT material_name, spec, unit, qty FROM ticket_materials WHERE ticket_id = ?",
            (data["id"],),
        )
    ]
    data["logs"] = [
        dict(m)
        for m in conn.execute(
            "SELECT actor, action, note, created_at FROM ticket_logs"
            " WHERE ticket_id = ? ORDER BY id",
            (data["id"],),
        )
    ]
    for key in ("reporter_id", "assignee_id", "dispatcher_id"):
        data.pop(key, None)
    return data


def room_location(room) -> str:
    location = f"{room['building']}{room['floor']}层 {room['room_no']}室"
    if room["name"]:
        location += f"（{room['name']}）"
    return location


@router.get("/room/{qr}")
def room_by_qr(qr: str, conn: sqlite3.Connection = Depends(get_db)):
    room = conn.execute(
        "SELECT id, building, floor, room_no, name, note FROM rooms"
        " WHERE qr_code = ? AND active = 1",
        (qr,),
    ).fetchone()
    if not room:
        raise HTTPException(status_code=404, detail="二维码无效或房间已停用")
    since = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    recent = conn.execute(
        "SELECT COUNT(*) FROM tickets WHERE room_id = ? AND created_at >= ?",
        (room["id"], since),
    ).fetchone()[0]
    return {
        "room": dict(room),
        "recent_30d": recent,
    }


@router.get("/meta")
def meta(conn: sqlite3.Connection = Depends(get_db)):
    fault_types = [
        r["name"]
        for r in conn.execute(
            "SELECT name FROM fault_types WHERE active = 1 ORDER BY sort, id"
        )
    ]
    devices = [
        r["name"]
        for r in conn.execute(
            "SELECT name FROM devices WHERE active = 1 ORDER BY sort, id"
        )
    ]
    rooms = [
        {
            "id": r["id"],
            "building": r["building"],
            "floor": r["floor"],
            "room_no": r["room_no"],
            "name": r["name"],
            "location": room_location(r),
        }
        for r in conn.execute(
            "SELECT * FROM rooms WHERE active = 1 ORDER BY building, floor, room_no"
        )
    ]
    return {"fault_types": fault_types, "devices": devices, "rooms": rooms}


@router.post("/tickets")
def create_ticket(
    payload: TicketCreateIn,
    conn: sqlite3.Connection = Depends(get_db),
    reporter: dict = Depends(reporter_identity),
):
    if payload.room_id:
        room = conn.execute(
            "SELECT * FROM rooms WHERE id = ? AND active = 1", (payload.room_id,)
        ).fetchone()
    else:
        room = conn.execute(
            "SELECT * FROM rooms WHERE qr_code = ? AND active = 1", (payload.qr,)
        ).fetchone()
    if not room:
        raise HTTPException(status_code=404, detail="报障地点无效，请重新扫码")

    since = (datetime.now() - timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
    recent = conn.execute(
        "SELECT COUNT(*) FROM tickets WHERE reporter_id = ? AND created_at >= ?",
        (reporter["id"], since),
    ).fetchone()[0]
    if recent >= 5:
        raise HTTPException(status_code=429, detail="提交过于频繁，请 10 分钟后再试")

    expect_time = (payload.expect_time or "").strip()[:60] or "立即上门"
    location = room_location(room)

    photo_paths = []
    for data_url in (payload.photos or [])[:MAX_PHOTOS]:
        try:
            photo_paths.append(save_data_url(data_url))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    code = gen_code(conn)
    ts = now()
    cur = conn.execute(
        """INSERT INTO tickets(code, room_id, location, device, fault_type, description,
               contact_name, contact_phone, expect_time, photos, reporter_id, status,
               created_at, updated_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,'pending',?,?)""",
        (
            code, room["id"], location, payload.device.strip(), payload.fault_type,
            payload.description.strip(), payload.contact_name.strip(),
            payload.contact_phone.strip(), expect_time,
            json.dumps(photo_paths, ensure_ascii=False), reporter["id"], ts, ts,
        ),
    )
    ticket_id = cur.lastrowid
    conn.execute(
        "UPDATE reporters SET name = ?, phone = ? WHERE id = ?",
        (payload.contact_name.strip(), payload.contact_phone.strip(), reporter["id"]),
    )
    note = payload.description.strip()
    if expect_time:
        note = (note + "；" if note else "") + f"期望上门：{expect_time}"
    add_log(conn, ticket_id, f"报障人 {payload.contact_name}", "提交报障", note)
    conn.commit()
    return {
        "id": ticket_id,
        "code": code,
        "status": "pending",
        "status_text": "待受理",
        "location": location,
        "expect_time": expect_time,
    }


@router.get("/my-tickets")
def my_tickets(
    conn: sqlite3.Connection = Depends(get_db),
    reporter: dict = Depends(reporter_identity),
):
    rows = conn.execute(
        f"SELECT {PUBLIC_FIELDS} FROM tickets WHERE reporter_id = ?"
        " ORDER BY id DESC LIMIT 200",
        (reporter["id"],),
    ).fetchall()
    return {"items": [public_ticket(conn, r, True) for r in rows]}


@router.get("/lookup")
def lookup_tickets(
    tail: str,
    room_id: int = 0,
    conn: sqlite3.Connection = Depends(get_db),
    reporter: dict = Depends(reporter_identity),
):
    """扫码后凭手机号后四位找回本手机号提交过的报障单。"""
    tail = (tail or "").strip()
    if not (tail.isdigit() and len(tail) == 4):
        raise HTTPException(status_code=400, detail="请输入手机号后四位")
    if _rate_limited(reporter["token_hash"]):
        raise HTTPException(status_code=429, detail="查询过于频繁，请稍后再试")

    sql = (
        f"SELECT {PUBLIC_FIELDS} FROM tickets"
        " WHERE substr(contact_phone, -4) = ?"
    )
    params: list = [tail]
    if room_id:
        sql += " AND room_id = ?"
        params.append(room_id)
    sql += " ORDER BY id DESC LIMIT 30"
    rows = conn.execute(sql, params).fetchall()
    return {
        "items": [
            public_ticket(conn, r, r["reporter_id"] == reporter["id"]) for r in rows
        ],
        "total": len(rows),
    }


@router.get("/ticket/{code}")
def get_ticket(
    code: str,
    tail: str = "",
    conn: sqlite3.Connection = Depends(get_db),
    reporter: dict = Depends(reporter_identity),
):
    row = conn.execute(
        f"SELECT {PUBLIC_FIELDS} FROM tickets WHERE code = ?", (code.strip().upper(),)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="未找到该报障单")
    is_owner = row["reporter_id"] == reporter["id"]
    if not is_owner:
        real = conn.execute(
            "SELECT contact_phone FROM tickets WHERE id = ?", (row["id"],)
        ).fetchone()["contact_phone"]
        if not tail or not tail.isdigit() or real[-4:] != tail[-4:]:
            raise HTTPException(status_code=403, detail="请填写报障手机号后四位")
    return public_ticket(conn, row, is_owner)


@router.post("/ticket/{code}/confirm")
def confirm_ticket(
    code: str,
    payload: ConfirmIn,
    tail: str = "",
    conn: sqlite3.Connection = Depends(get_db),
    reporter: dict = Depends(reporter_identity),
):
    row = conn.execute(
        "SELECT * FROM tickets WHERE code = ?", (code.strip().upper(),)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="未找到该报障单")
    is_owner = row["reporter_id"] == reporter["id"]
    if not is_owner and (not tail or row["contact_phone"][-4:] != tail[-4:]):
        raise HTTPException(status_code=403, detail="无权确认该工单")
    if row["status"] == "confirmed":
        raise HTTPException(status_code=400, detail="该工单已确认")
    if row["status"] != "pending_confirm":
        raise HTTPException(status_code=400, detail="工单尚未处理完成，暂不能确认")

    signature = (payload.signature or "").strip()
    if not signature.startswith("data:image/png;base64,"):
        raise HTTPException(status_code=400, detail="请手写签名后再确认")
    if len(signature) > 600_000:
        raise HTTPException(status_code=400, detail="签名图片过大，请重签")

    rating = max(1, min(5, payload.rating))
    ts = now()
    conn.execute(
        "UPDATE tickets SET status='confirmed', confirm_at=?, rating=?,"
        " confirm_comment=?, signature=?, updated_at=? WHERE id=?",
        (ts, rating, payload.comment.strip(), signature, ts, row["id"]),
    )
    add_log(
        conn, row["id"], f"报障人 {row['contact_name']}", "签字确认完成",
        f"满意度 {rating} 星",
    )
    conn.commit()
    return {"ok": True, "status": "confirmed", "status_text": "已完成"}


@router.post("/ticket/{code}/cancel")
def cancel_ticket(
    code: str,
    conn: sqlite3.Connection = Depends(get_db),
    reporter: dict = Depends(reporter_identity),
):
    row = conn.execute(
        "SELECT * FROM tickets WHERE code = ?", (code.strip().upper(),)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="未找到该报障单")
    if row["reporter_id"] != reporter["id"]:
        raise HTTPException(status_code=403, detail="只能撤销本人提交的报障")
    if row["status"] not in ("pending",):
        raise HTTPException(status_code=400, detail="工单已受理，无法撤销，请联系运维人员")
    conn.execute(
        "UPDATE tickets SET status='cancelled', updated_at=? WHERE id=?",
        (now(), row["id"]),
    )
    add_log(conn, row["id"], f"报障人 {row['contact_name']}", "撤销报障")
    conn.commit()
    return {"ok": True}
