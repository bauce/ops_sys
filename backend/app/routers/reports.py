"""运维周报 / 月报统计。"""
import sqlite3
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends

from ..db import get_db
from ..security import require_roles

router = APIRouter(prefix="/api/staff/reports", tags=["reports"])


def _range(period: str, anchor: str):
    try:
        d = datetime.strptime(anchor, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        d = date.today()
    if period == "month":
        start = d.replace(day=1)
        if start.month == 12:
            nxt = start.replace(year=start.year + 1, month=1, day=1)
        else:
            nxt = start.replace(month=start.month + 1, day=1)
        end = nxt - timedelta(days=1)
    else:
        start = d - timedelta(days=d.weekday())
        end = start + timedelta(days=6)
    return start, end


@router.get("/summary")
def summary(
    period: str = "week",
    anchor: str = "",
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles("admin", "dispatcher")),
):
    period = "month" if period == "month" else "week"
    start, end = _range(period, anchor)
    s, e = start.isoformat(), end.isoformat()
    base = "substr(t.created_at,1,10) BETWEEN ? AND ?"

    def scalar(sql, params=()):
        row = conn.execute(sql, params).fetchone()
        return row[0] if row else 0

    created_total = scalar(f"SELECT COUNT(*) FROM tickets t WHERE {base}", (s, e))
    confirmed_total = scalar(
        "SELECT COUNT(*) FROM tickets t WHERE t.status='confirmed'"
        " AND substr(t.confirm_at,1,10) BETWEEN ? AND ?",
        (s, e),
    )
    cancelled_total = scalar(f"SELECT COUNT(*) FROM tickets t WHERE {base} AND t.status='cancelled'", (s, e))
    avg_response = scalar(
        f"SELECT AVG((julianday(t.accepted_at)-julianday(t.created_at))*24) FROM tickets t"
        f" WHERE {base} AND t.accepted_at IS NOT NULL",
        (s, e),
    ) or 0
    avg_repair = scalar(
        f"SELECT AVG((julianday(t.finished_at)-julianday(t.created_at))*24) FROM tickets t"
        f" WHERE {base} AND t.finished_at IS NOT NULL",
        (s, e),
    ) or 0
    rating = conn.execute(
        "SELECT AVG(rating), COUNT(rating) FROM tickets t WHERE t.status='confirmed'"
        " AND substr(t.confirm_at,1,10) BETWEEN ? AND ?",
        (s, e),
    ).fetchone()

    status_counts = [
        {"status": r["status"], "count": r["c"]}
        for r in conn.execute(
            f"SELECT t.status, COUNT(*) c FROM tickets t WHERE {base} GROUP BY t.status"
            " ORDER BY c DESC",
            (s, e),
        )
    ]
    faults = [
        {"name": r["fault_type"], "count": r["c"]}
        for r in conn.execute(
            f"SELECT t.fault_type, COUNT(*) c FROM tickets t WHERE {base}"
            " GROUP BY t.fault_type ORDER BY c DESC LIMIT 8",
            (s, e),
        )
    ]

    engineers = []
    for r in conn.execute(
        f"""SELECT st.name, COUNT(t.id) assigned,
                   SUM(CASE WHEN t.status='confirmed' THEN 1 ELSE 0 END) done,
                   AVG(CASE WHEN t.finished_at IS NOT NULL
                       THEN (julianday(t.finished_at)-julianday(t.created_at))*24 END) avg_hours
            FROM tickets t JOIN staff st ON st.id = t.assignee_id
            WHERE {base} GROUP BY t.assignee_id ORDER BY assigned DESC""",
        (s, e),
    ):
        engineers.append({
            "name": r["name"],
            "assigned": r["assigned"],
            "done": r["done"] or 0,
            "avg_hours": round(r["avg_hours"] or 0, 1),
        })

    rooms = [
        {
            "location": r["location"],
            "importance": r["importance"] or "普通",
            "count": r["c"],
        }
        for r in conn.execute(
            f"""SELECT t.location, r.importance, COUNT(*) c
                FROM tickets t LEFT JOIN rooms r ON r.id = t.room_id
                WHERE {base} GROUP BY t.location ORDER BY c DESC LIMIT 8""",
            (s, e),
        )
    ]

    materials = [
        {"name": r["material_name"], "qty": r["qty"], "tickets": r["tickets"]}
        for r in conn.execute(
            """SELECT tm.material_name, SUM(tm.qty) qty, COUNT(DISTINCT tm.ticket_id) tickets
               FROM ticket_materials tm JOIN tickets t ON t.id = tm.ticket_id
               WHERE t.status='confirmed' AND substr(t.confirm_at,1,10) BETWEEN ? AND ?
               GROUP BY tm.material_name ORDER BY qty DESC LIMIT 8""",
            (s, e),
        )
    ]

    # 每日趋势
    trend = []
    day = start
    while day <= end:
        ds = day.isoformat()
        created = scalar(
            "SELECT COUNT(*) FROM tickets t WHERE substr(t.created_at,1,10) = ?", (ds,)
        )
        done = scalar(
            "SELECT COUNT(*) FROM tickets t WHERE t.status='confirmed'"
            " AND substr(t.confirm_at,1,10) = ?", (ds,)
        )
        trend.append({"date": ds, "created": created, "done": done})
        day += timedelta(days=1)

    overdue_pending = scalar(
        "SELECT COUNT(*) FROM tickets t WHERE t.status='pending'"
        " AND t.created_at < datetime('now','localtime','-15 minutes')"
    )
    open_total = scalar(
        "SELECT COUNT(*) FROM tickets t WHERE t.status IN"
        " ('pending','accepted','processing','pending_confirm')"
    )

    return {
        "period": period,
        "start": s,
        "end": e,
        "label": f"{s} ~ {e}",
        "summary": {
            "created": created_total,
            "confirmed": confirmed_total,
            "cancelled": cancelled_total,
            "avg_response_hours": round(avg_response, 1),
            "avg_repair_hours": round(avg_repair, 1),
            "avg_rating": round(rating[0] or 0, 1),
            "rating_count": rating[1] or 0,
            "overdue_pending": overdue_pending,
            "open_total": open_total,
        },
        "status": status_counts,
        "faults": faults,
        "engineers": engineers,
        "rooms": rooms,
        "materials": materials,
        "trend": trend,
    }
