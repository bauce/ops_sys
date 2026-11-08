"""后台可配置字典：故障类型、常用设备。"""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..db import get_db
from ..security import current_staff, require_roles

router = APIRouter(prefix="/api/staff/dicts", tags=["dicts"])

TABLES = {"fault_types": "故障类型", "devices": "常用设备"}


def _table(kind: str) -> str:
    if kind not in TABLES:
        raise HTTPException(status_code=404, detail="未知的字典类型")
    return kind


@router.get("/{kind}")
def list_items(
    kind: str,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    table = _table(kind)
    rows = conn.execute(
        f"SELECT * FROM {table} ORDER BY active DESC, sort, id"
    ).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.post("/{kind}")
def create_item(
    kind: str,
    payload: dict,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles("admin", "dispatcher")),
):
    table = _table(kind)
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="名称不能为空")
    if conn.execute(f"SELECT 1 FROM {table} WHERE name = ?", (name,)).fetchone():
        raise HTTPException(status_code=400, detail="名称已存在")
    sort = conn.execute(f"SELECT COALESCE(MAX(sort),0)+1 FROM {table}").fetchone()[0]
    conn.execute(
        f"INSERT INTO {table}(name,sort,active) VALUES(?,?,1)", (name, sort)
    )
    conn.commit()
    return {"ok": True}


@router.put("/{kind}/{item_id}")
def update_item(
    kind: str,
    item_id: int,
    payload: dict,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles("admin", "dispatcher")),
):
    table = _table(kind)
    row = conn.execute(f"SELECT * FROM {table} WHERE id = ?", (item_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    name = (payload.get("name") or row["name"]).strip()
    if name != row["name"] and conn.execute(
        f"SELECT 1 FROM {table} WHERE name = ? AND id != ?", (name, item_id)
    ).fetchone():
        raise HTTPException(status_code=400, detail="名称已存在")
    active = payload.get("active", row["active"])
    sort = payload.get("sort", row["sort"])
    conn.execute(
        f"UPDATE {table} SET name = ?, active = ?, sort = ? WHERE id = ?",
        (name, active, sort, item_id),
    )
    conn.commit()
    return {"ok": True}


@router.delete("/{kind}/{item_id}")
def delete_item(
    kind: str,
    item_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles("admin", "dispatcher")),
):
    table = _table(kind)
    conn.execute(f"DELETE FROM {table} WHERE id = ?", (item_id,))
    conn.commit()
    return {"ok": True}
