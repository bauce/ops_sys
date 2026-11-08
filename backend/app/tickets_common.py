"""工单公共逻辑：编号、日志、详情组装。"""
import json
import sqlite3
from datetime import datetime

from .db import now

STATUS_TEXT = {
    "pending": "待受理",
    "accepted": "已受理",
    "processing": "处理中",
    "pending_confirm": "待确认",
    "confirmed": "已完成",
    "cancelled": "已取消",
}

FAULT_TYPES = [
    "网络无法访问",
    "电脑/终端故障",
    "打印机/复印机故障",
    "电话故障",
    "服务器/系统故障",
    "投影/会议设备故障",
    "门禁/监控故障",
    "软件使用问题",
    "其他",
]


def gen_code(conn: sqlite3.Connection) -> str:
    day = datetime.now().strftime("%Y%m%d")
    prefix = f"WO{day}"
    n = conn.execute(
        "SELECT COUNT(*) FROM tickets WHERE code LIKE ?", (prefix + "%",)
    ).fetchone()[0]
    while True:
        n += 1
        code = f"{prefix}{n:03d}"
        exists = conn.execute(
            "SELECT 1 FROM tickets WHERE code = ?", (code,)
        ).fetchone()
        if not exists:
            return code


def add_log(
    conn: sqlite3.Connection, ticket_id: int, actor: str, action: str, note: str = ""
) -> None:
    conn.execute(
        "INSERT INTO ticket_logs(ticket_id, actor, action, note, created_at)"
        " VALUES(?,?,?,?,?)",
        (ticket_id, actor, action, note, now()),
    )


def staff_actor(staff: dict) -> str:
    from .security import ROLE_NAMES

    names = "、".join(
        ROLE_NAMES.get(r, r) for r in staff.get("roles", [staff.get("role", "")])
    )
    return f"{staff['name']}（{names}）"


def ticket_detail(conn: sqlite3.Connection, ticket_id: int):
    row = conn.execute(
        """SELECT t.*, r.name AS room_name, r.building, r.floor, r.room_no,
                  d.name AS dispatcher_name, a.name AS assignee_name
           FROM tickets t
           LEFT JOIN rooms r ON r.id = t.room_id
           LEFT JOIN staff d ON d.id = t.dispatcher_id
           LEFT JOIN staff a ON a.id = t.assignee_id
           WHERE t.id = ?""",
        (ticket_id,),
    ).fetchone()
    if not row:
        return None
    data = dict(row)
    data["status_text"] = STATUS_TEXT.get(data["status"], data["status"])
    data["reporter_name"] = ""
    if data.get("reporter_id"):
        rep = conn.execute(
            "SELECT name, phone FROM reporters WHERE id = ?", (data["reporter_id"],)
        ).fetchone()
        if rep:
            data["reporter_name"] = rep["name"] or ""
    tr = conn.execute(
        """SELECT tr.id, tr.note, tr.created_at, tr.from_staff_id, tr.to_staff_id,
                  fs.name AS from_name, ts.name AS to_name
           FROM transfers tr
           JOIN staff fs ON fs.id = tr.from_staff_id
           JOIN staff ts ON ts.id = tr.to_staff_id
           WHERE tr.ticket_id = ? AND tr.status = 'pending'
           ORDER BY tr.id DESC LIMIT 1""",
        (ticket_id,),
    ).fetchone()
    data["pending_transfer"] = dict(tr) if tr else None
    try:
        data["photos"] = json.loads(data.get("photos") or "[]")
    except (TypeError, ValueError):
        data["photos"] = []
    data["materials"] = [
        dict(m)
        for m in conn.execute(
            "SELECT material_id, material_name, spec, unit, qty FROM ticket_materials"
            " WHERE ticket_id = ? ORDER BY id",
            (ticket_id,),
        )
    ]
    data["logs"] = [
        dict(m)
        for m in conn.execute(
            "SELECT actor, action, note, created_at FROM ticket_logs"
            " WHERE ticket_id = ? ORDER BY id",
            (ticket_id,),
        )
    ]
    return data
