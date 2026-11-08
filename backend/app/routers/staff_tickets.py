"""运维端工单接口：受理、派单、处理、完成、统计。"""
import sqlite3
from typing import Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from .. import mailer
from ..db import get_db, now
from .duty import today_duty
from ..schemas import AcceptIn, FinishIn, ManualTicketIn, TransferIn
from ..security import current_staff, has_role, parse_roles, require_roles
from ..tickets_common import (
    STATUS_TEXT,
    add_log,
    gen_code,
    staff_actor,
    ticket_detail,
)

router = APIRouter(prefix="/api/staff/tickets", tags=["staff-tickets"])

OPEN_STATUSES = ("pending", "accepted", "processing", "pending_confirm")


def _get_ticket(conn: sqlite3.Connection, ticket_id: int):
    row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="工单不存在")
    return row


def _check_can_handle(ticket, staff: dict) -> None:
    if has_role(staff, "admin") or has_role(staff, "dispatcher"):
        return
    if ticket["assignee_id"] != staff["id"]:
        raise HTTPException(status_code=403, detail="该工单未指派给你，无法操作")


@router.get("")
def list_tickets(
    status: str = "",
    keyword: str = "",
    assignee_id: Optional[int] = None,
    mine: int = 0,
    page: int = 1,
    page_size: int = 20,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    where, params = ["1=1"], []
    if status:
        statuses = [s for s in status.split(",") if s in STATUS_TEXT]
        if statuses:
            where.append("t.status IN (%s)" % ",".join("?" * len(statuses)))
            params += statuses
    if keyword:
        kw = f"%{keyword.strip()}%"
        where.append(
            "(t.code LIKE ? OR t.device LIKE ? OR t.location LIKE ?"
            " OR t.contact_name LIKE ? OR t.contact_phone LIKE ?)"
        )
        params += [kw] * 5
    if mine:
        where.append("t.assignee_id = ?")
        params.append(staff["id"])
    elif assignee_id:
        where.append("t.assignee_id = ?")
        params.append(assignee_id)

    total = conn.execute(
        "SELECT COUNT(*) FROM tickets t WHERE " + " AND ".join(where), params
    ).fetchone()[0]

    page = max(1, page)
    page_size = min(100, max(1, page_size))
    sql = (
        """SELECT t.id, t.code, t.status, t.location, t.device, t.fault_type,
                  t.contact_name, t.contact_phone, t.expect_time, t.created_at,
                  t.accepted_at, t.finished_at, t.rating, t.assignee_id, t.room_id,
                  a.name AS assignee_name
           FROM tickets t LEFT JOIN staff a ON a.id = t.assignee_id
           WHERE """
        + " AND ".join(where)
        + " ORDER BY CASE t.status WHEN 'pending' THEN 0 WHEN 'accepted' THEN 1"
        " WHEN 'processing' THEN 2 WHEN 'pending_confirm' THEN 3 ELSE 4 END,"
        " t.id DESC LIMIT ? OFFSET ?"
    )
    rows = conn.execute(sql, params + [page_size, (page - 1) * page_size]).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        d["status_text"] = STATUS_TEXT.get(d["status"], d["status"])
        items.append(d)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get("/stats/overview")
def stats_overview(
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    counts = {k: 0 for k in STATUS_TEXT}
    for r in conn.execute("SELECT status, COUNT(*) c FROM tickets GROUP BY status"):
        counts[r["status"]] = r["c"]

    today = datetime.now().strftime("%Y-%m-%d")
    today_new = conn.execute(
        "SELECT COUNT(*) FROM tickets WHERE substr(created_at,1,10) = ?", (today,)
    ).fetchone()[0]

    week = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    week_done = conn.execute(
        "SELECT COUNT(*) FROM tickets WHERE status='confirmed' AND substr(confirm_at,1,10) >= ?",
        (week,),
    ).fetchone()[0]

    avg_hours = conn.execute(
        "SELECT AVG((julianday(finished_at) - julianday(created_at)) * 24)"
        " FROM tickets WHERE finished_at IS NOT NULL"
    ).fetchone()[0]

    rating = conn.execute(
        "SELECT AVG(rating), COUNT(rating) FROM tickets WHERE rating IS NOT NULL"
    ).fetchone()

    low_stock = conn.execute(
        "SELECT COUNT(*) FROM materials WHERE active=1 AND stock <= warn_stock"
    ).fetchone()[0]

    top_rooms = [
        dict(r)
        for r in conn.execute(
            """SELECT t.location, COUNT(*) c FROM tickets t
               WHERE t.created_at >= ? GROUP BY t.location ORDER BY c DESC LIMIT 5""",
            ((datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),),
        )
    ]
    fault_types = [
        dict(r)
        for r in conn.execute(
            "SELECT fault_type, COUNT(*) c FROM tickets GROUP BY fault_type ORDER BY c DESC LIMIT 6"
        )
    ]
    return {
        "counts": counts,
        "today_new": today_new,
        "week_done": week_done,
        "avg_hours": round(avg_hours or 0, 1),
        "avg_rating": round(rating[0] or 0, 1),
        "rating_count": rating[1],
        "low_stock": low_stock,
        "top_rooms": top_rooms,
        "fault_types": fault_types,
    }


@router.post("/manual")
def create_manual(
    payload: ManualTicketIn,
    background: BackgroundTasks,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles("admin", "dispatcher", "duty")),
):
    """受理员代录电话报障，可同时派单。"""
    location = (payload.location_text or "").strip()
    room_id = None
    if payload.room_id:
        room = conn.execute(
            "SELECT * FROM rooms WHERE id = ? AND active = 1", (payload.room_id,)
        ).fetchone()
        if not room:
            raise HTTPException(status_code=400, detail="报障地点不存在")
        room_id = room["id"]
        location = f"{room['building']}{room['floor']}层 {room['room_no']}室"
        if room["name"]:
            location += f"（{room['name']}）"
    if not location:
        raise HTTPException(status_code=400, detail="请选择或填写报障地点")

    assignee = None
    if payload.assignee_id:
        assignee = conn.execute(
            "SELECT id, name, role FROM staff WHERE id = ? AND active = 1",
            (payload.assignee_id,),
        ).fetchone()
        if not assignee:
            raise HTTPException(status_code=400, detail="处理人不存在")

    expect_time = (payload.expect_time or "").strip()[:60] or "立即上门"
    code = gen_code(conn)
    ts = now()
    status = "accepted" if assignee else "pending"
    cur = conn.execute(
        """INSERT INTO tickets(code, room_id, location, device, fault_type, description,
               contact_name, contact_phone, expect_time, source, status, dispatcher_id,
               assignee_id, accepted_at, created_at, updated_at)
           VALUES(?,?,?,?,?,?,?,?,?,'phone',?,?,?,?,?,?)""",
        (
            code, room_id, location, payload.device.strip(), payload.fault_type,
            payload.description.strip(), payload.contact_name.strip(),
            payload.contact_phone.strip(), expect_time, status,
            staff["id"], assignee["id"] if assignee else None,
            ts if assignee else None, ts, ts,
        ),
    )
    ticket_id = cur.lastrowid
    add_log(
        conn, ticket_id, staff_actor(staff), "电话报障代录",
        f"{payload.contact_name} · {payload.contact_phone}",
    )
    if assignee:
        add_log(conn, ticket_id, staff_actor(staff), "受理并指派处理人", assignee["name"])
    conn.commit()
    if assignee:
        background.add_task(mailer.send_assigned, ticket_id)
    return {
        "ok": True,
        "id": ticket_id,
        "code": code,
        "status": status,
        "status_text": STATUS_TEXT.get(status),
        "assignee_name": assignee["name"] if assignee else None,
    }


@router.get("/transfers/pending")
def my_pending_transfers(
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    rows = conn.execute(
        """SELECT tr.id, tr.note, tr.created_at, t.id AS ticket_id, t.code,
                  t.location, t.device, t.expect_time, t.status AS ticket_status,
                  f.name AS from_name
           FROM transfers tr
           JOIN tickets t ON t.id = tr.ticket_id
           JOIN staff f ON f.id = tr.from_staff_id
           WHERE tr.to_staff_id = ? AND tr.status = 'pending'
           ORDER BY tr.id DESC""",
        (staff["id"],),
    ).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.get("/board")
def board_data(
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    """报障大屏数据：待受理、超时预警、今日统计与今日值班。"""
    settings = {
        r["key"]: r["value"]
        for r in conn.execute(
            "SELECT key, value FROM settings WHERE key LIKE 'sla_%'"
        )
    }
    try:
        sla_pending = int(settings.get("sla_pending_minutes", 15))
    except ValueError:
        sla_pending = 15
    try:
        sla_accept = int(settings.get("sla_accept_minutes", 60))
    except ValueError:
        sla_accept = 60
    try:
        sla_processing = float(settings.get("sla_processing_hours", 4))
    except ValueError:
        sla_processing = 4.0

    now_dt = datetime.now()

    def minutes_since(value):
        if not value:
            return 0
        try:
            return int((now_dt - datetime.strptime(value, "%Y-%m-%d %H:%M:%S")).total_seconds() // 60)
        except ValueError:
            return 0

    rows = conn.execute(
        """SELECT t.id, t.code, t.status, t.location, t.device, t.fault_type,
                  t.contact_name, t.contact_phone, t.expect_time, t.created_at,
                  t.accepted_at, t.started_at, a.name AS assignee_name
           FROM tickets t LEFT JOIN staff a ON a.id = t.assignee_id
           WHERE t.status IN ('pending', 'accepted', 'processing')
           ORDER BY t.id DESC"""
    ).fetchall()

    pending, overdue = [], []
    for r in rows:
        d = dict(r)
        d["status_text"] = STATUS_TEXT.get(d["status"], d["status"])
        d["wait_minutes"] = minutes_since(d["created_at"])
        reason = None
        if d["status"] == "pending" and d["wait_minutes"] > sla_pending:
            reason = "待受理超时"
        elif d["status"] == "accepted":
            waited = minutes_since(d["accepted_at"])
            if waited > sla_accept:
                reason = "上门超时"
            d["wait_minutes"] = waited
        elif d["status"] == "processing":
            spent = minutes_since(d["started_at"]) / 60
            if spent > sla_processing:
                reason = "处理超时"
            d["wait_minutes"] = int(spent * 60)
        if reason:
            d["overdue_reason"] = reason
            overdue.append(d)
        if d["status"] == "pending":
            pending.append(d)

    counts = {"pending": 0, "accepted": 0, "processing": 0, "pending_confirm": 0,
              "confirmed": 0, "cancelled": 0}
    for r in conn.execute("SELECT status, COUNT(*) c FROM tickets GROUP BY status"):
        counts[r["status"]] = r["c"]
    today = datetime.now().strftime("%Y-%m-%d")
    today_new = conn.execute(
        "SELECT COUNT(*) FROM tickets WHERE substr(created_at,1,10) = ?", (today,)
    ).fetchone()[0]
    today_done = conn.execute(
        "SELECT COUNT(*) FROM tickets WHERE status='confirmed' AND substr(confirm_at,1,10) = ?",
        (today,),
    ).fetchone()[0]
    duty_items, _ = today_duty(conn)
    return {
        "pending": pending,
        "overdue": overdue,
        "stats": {
            "pending": counts.get("pending", 0),
            "processing": counts.get("accepted", 0) + counts.get("processing", 0),
            "pending_confirm": counts.get("pending_confirm", 0),
            "today_new": today_new,
            "today_done": today_done,
        },
        "duty": duty_items,
        "sla": {
            "pending_minutes": sla_pending,
            "accept_minutes": sla_accept,
            "processing_hours": sla_processing,
        },
    }


@router.get("/{ticket_id}")
def detail(
    ticket_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    data = ticket_detail(conn, ticket_id)
    if not data:
        raise HTTPException(status_code=404, detail="工单不存在")
    return data


@router.post("/{ticket_id}/accept")
def accept(
    ticket_id: int,
    payload: AcceptIn,
    background: BackgroundTasks,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles("admin", "dispatcher", "duty")),
):
    t = _get_ticket(conn, ticket_id)
    if t["status"] != "pending":
        raise HTTPException(status_code=400, detail="该工单已被受理")
    assignee_id = payload.assignee_id or (staff["id"] if has_role(staff, "engineer") else None)
    ts = now()
    conn.execute(
        "UPDATE tickets SET status='accepted', dispatcher_id=?, assignee_id=?,"
        " accepted_at=?, updated_at=? WHERE id=?",
        (staff["id"], assignee_id, ts, ts, ticket_id),
    )
    add_log(conn, ticket_id, staff_actor(staff), "受理工单")
    if assignee_id:
        name = conn.execute("SELECT name FROM staff WHERE id=?", (assignee_id,)).fetchone()
        add_log(conn, ticket_id, staff_actor(staff), "指派处理人", name["name"] if name else "")
    conn.commit()
    if assignee_id:
        background.add_task(mailer.send_assigned, ticket_id)
    return {"ok": True, "status": "accepted", "status_text": "已受理"}


@router.post("/{ticket_id}/assign")
def assign(
    ticket_id: int,
    payload: AcceptIn,
    background: BackgroundTasks,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles("admin", "dispatcher", "duty")),
):
    if not payload.assignee_id:
        raise HTTPException(status_code=400, detail="请选择处理人")
    t = _get_ticket(conn, ticket_id)
    if t["status"] in ("confirmed", "cancelled"):
        raise HTTPException(status_code=400, detail="工单已结束，无法改派")
    row = conn.execute(
        "SELECT id, name, role FROM staff WHERE id = ? AND active = 1",
        (payload.assignee_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="处理人不存在")
    ts = now()
    new_status = "accepted" if t["status"] == "pending" else t["status"]
    conn.execute(
        "UPDATE tickets SET assignee_id = ?, status = ?, dispatcher_id = COALESCE(dispatcher_id, ?),"
        " accepted_at = COALESCE(accepted_at, ?), updated_at = ? WHERE id = ?",
        (row["id"], new_status, staff["id"], ts, ts, ticket_id),
    )
    conn.execute(
        "UPDATE transfers SET status = 'cancelled', resolved_at = ?"
        " WHERE ticket_id = ? AND status = 'pending'",
        (ts, ticket_id),
    )
    add_log(conn, ticket_id, staff_actor(staff), "改派处理人", row["name"])
    conn.commit()
    background.add_task(mailer.send_assigned, ticket_id)
    return {"ok": True, "assignee_id": row["id"], "assignee_name": row["name"]}


@router.post("/{ticket_id}/start")
def start(
    ticket_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    t = _get_ticket(conn, ticket_id)
    _check_can_handle(t, staff)
    if t["status"] not in ("accepted", "processing"):
        raise HTTPException(status_code=400, detail="当前状态不能开始处理")
    ts = now()
    conn.execute(
        "UPDATE tickets SET status='processing', started_at=COALESCE(started_at, ?),"
        " updated_at=?, assignee_id=COALESCE(assignee_id, ?) WHERE id=?",
        (ts, ts, staff["id"], ticket_id),
    )
    add_log(conn, ticket_id, staff_actor(staff), "开始上门处理")
    conn.commit()
    return {"ok": True, "status": "processing", "status_text": "处理中"}


@router.post("/{ticket_id}/finish")
def finish(
    ticket_id: int,
    payload: FinishIn,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    t = _get_ticket(conn, ticket_id)
    _check_can_handle(t, staff)
    if t["status"] not in ("accepted", "processing"):
        raise HTTPException(status_code=400, detail="当前状态不能提交处理结果")
    if not payload.solve_note.strip():
        raise HTTPException(status_code=400, detail="请填写处理说明")

    # 先校验库存，避免扣减到一半失败
    for use in payload.materials:
        if use.qty <= 0:
            raise HTTPException(status_code=400, detail="物资数量必须大于 0")
        mat = conn.execute(
            "SELECT * FROM materials WHERE id = ? AND active = 1", (use.material_id,)
        ).fetchone()
        if not mat:
            raise HTTPException(status_code=400, detail="物资不存在或已停用")
        if mat["stock"] < use.qty:
            raise HTTPException(
                status_code=400,
                detail=f"物资「{mat['name']}」库存不足（现有 {mat['stock']}{mat['unit']}）",
            )

    ts = now()
    for use in payload.materials:
        mat = conn.execute(
            "SELECT * FROM materials WHERE id = ?", (use.material_id,)
        ).fetchone()
        before = mat["stock"]
        after = before - use.qty
        conn.execute(
            "UPDATE materials SET stock = ?, updated_at = ? WHERE id = ?",
            (after, ts, mat["id"]),
        )
        conn.execute(
            "INSERT INTO stock_logs(material_id, kind, qty, before_stock, after_stock,"
            " ticket_id, operator, note, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (
                mat["id"], "out", use.qty, before, after, ticket_id,
                staff["name"], f"工单 {t['code']} 维修领用", ts,
            ),
        )
        conn.execute(
            "INSERT INTO ticket_materials(ticket_id, material_id, material_name, spec,"
            " unit, qty, created_at) VALUES(?,?,?,?,?,?,?)",
            (
                ticket_id, mat["id"], mat["name"], mat["spec"], mat["unit"], use.qty, ts,
            ),
        )

    conn.execute(
        "UPDATE tickets SET status='pending_confirm', fault_cause=?, solve_note=?,"
        " finished_at=?, updated_at=?, assignee_id=COALESCE(assignee_id, ?) WHERE id=?",
        (
            payload.fault_cause.strip(), payload.solve_note.strip(), ts, ts,
            staff["id"], ticket_id,
        ),
    )
    used = "、".join(
        f"{m['material_name']}×{m['qty']}" for m in conn.execute(
            "SELECT material_name, qty FROM ticket_materials WHERE ticket_id=?", (ticket_id,)
        )
    )
    add_log(
        conn, ticket_id, staff_actor(staff), "提交处理结果",
        (payload.solve_note.strip() + (f"；领用物资：{used}" if used else "")),
    )
    conn.commit()
    return {"ok": True, "status": "pending_confirm", "status_text": "待确认"}


@router.post("/{ticket_id}/close")
def close(
    ticket_id: int,
    payload: dict,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles("admin", "dispatcher", "duty")),
):
    t = _get_ticket(conn, ticket_id)
    if t["status"] in ("confirmed", "cancelled"):
        raise HTTPException(status_code=400, detail="工单已结束")
    reason = (payload.get("reason") or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="请填写关闭原因")
    ts = now()
    conn.execute(
        "UPDATE tickets SET status='cancelled', solve_note=?, updated_at=? WHERE id=?",
        (reason, ts, ticket_id),
    )
    add_log(conn, ticket_id, staff_actor(staff), "关闭工单", reason)
    conn.commit()
    return {"ok": True}


@router.post("/{ticket_id}/transfer")
def create_transfer(
    ticket_id: int,
    payload: TransferIn,
    background: BackgroundTasks,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    """转派申请：工程师发起后，需接收人确认；受理员/管理员也可发起。"""
    t = _get_ticket(conn, ticket_id)
    if t["status"] not in ("accepted", "processing"):
        raise HTTPException(status_code=400, detail="当前状态不能转派")
    if not (has_role(staff, "admin") or has_role(staff, "dispatcher")):
        if t["assignee_id"] != staff["id"]:
            raise HTTPException(status_code=403, detail="只有当前处理人可以发起转派")

    target = conn.execute(
        "SELECT id, name, role, roles, email FROM staff WHERE id = ? AND active = 1",
        (payload.to_staff_id,),
    ).fetchone()
    if not target:
        raise HTTPException(status_code=400, detail="接收人不存在")
    target_roles = parse_roles(target["roles"], target["role"])
    if not ({"engineer", "dispatcher"} & set(target_roles)):
        raise HTTPException(status_code=400, detail="只能转派给运维工程师或受理员")
    if t["assignee_id"] == target["id"]:
        raise HTTPException(status_code=400, detail="该工单已由此人处理")

    ts = now()
    conn.execute(
        "UPDATE transfers SET status = 'cancelled', resolved_at = ?"
        " WHERE ticket_id = ? AND status = 'pending'",
        (ts, ticket_id),
    )
    cur = conn.execute(
        "INSERT INTO transfers(ticket_id, from_staff_id, to_staff_id, status, note, created_at)"
        " VALUES(?,?,?,'pending',?,?)",
        (ticket_id, staff["id"], target["id"], payload.note.strip(), ts),
    )
    add_log(
        conn, ticket_id, staff_actor(staff), "发起转派",
        f"转给 {target['name']}" + (f"；{payload.note.strip()}" if payload.note.strip() else ""),
    )
    conn.commit()
    background.add_task(mailer.send_transfer, ticket_id, target["id"], payload.note.strip())
    return {"ok": True, "transfer_id": cur.lastrowid, "to_name": target["name"]}


@router.post("/transfers/{transfer_id}/accept")
def accept_transfer(
    transfer_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    tr = conn.execute(
        "SELECT * FROM transfers WHERE id = ?", (transfer_id,)
    ).fetchone()
    if not tr:
        raise HTTPException(status_code=404, detail="转派申请不存在")
    if tr["to_staff_id"] != staff["id"]:
        raise HTTPException(status_code=403, detail="该转派不是发给你的")
    if tr["status"] != "pending":
        raise HTTPException(status_code=400, detail="该转派已处理")
    t = _get_ticket(conn, tr["ticket_id"])
    if t["assignee_id"] != tr["from_staff_id"]:
        conn.execute(
            "UPDATE transfers SET status = 'cancelled', resolved_at = ? WHERE id = ?",
            (now(), transfer_id),
        )
        conn.commit()
        raise HTTPException(status_code=400, detail="工单已被改派，该申请失效")

    ts = now()
    conn.execute(
        "UPDATE transfers SET status = 'accepted', resolved_at = ? WHERE id = ?",
        (ts, transfer_id),
    )
    conn.execute(
        "UPDATE tickets SET assignee_id = ?, updated_at = ? WHERE id = ?",
        (staff["id"], ts, t["id"]),
    )
    add_log(conn, t["id"], staff_actor(staff), "接收转派")
    conn.commit()
    return {"ok": True}


@router.post("/transfers/{transfer_id}/reject")
def reject_transfer(
    transfer_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    tr = conn.execute(
        "SELECT * FROM transfers WHERE id = ?", (transfer_id,)
    ).fetchone()
    if not tr:
        raise HTTPException(status_code=404, detail="转派申请不存在")
    if tr["to_staff_id"] != staff["id"]:
        raise HTTPException(status_code=403, detail="该转派不是发给你的")
    if tr["status"] != "pending":
        raise HTTPException(status_code=400, detail="该转派已处理")
    ts = now()
    conn.execute(
        "UPDATE transfers SET status = 'rejected', resolved_at = ? WHERE id = ?",
        (ts, transfer_id),
    )
    add_log(conn, tr["ticket_id"], staff_actor(staff), "拒绝转派")
    conn.commit()
    return {"ok": True}
