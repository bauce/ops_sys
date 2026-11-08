"""物资（特资）管理：台账、分类编号、入库、出库、流水、模板导入。"""
import csv
import io
import sqlite3
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response

from ..db import get_db, next_material_code, now
from ..schemas import ImportIn, MaterialIn, MaterialUpdate, StockIn
from ..security import current_staff, require_roles

router = APIRouter(prefix="/api/staff", tags=["materials"])

MANAGER_ROLES = ("admin", "dispatcher")

CSV_HEADERS = ["名称", "分类", "规格", "单位", "初始库存", "预警库存", "存放位置", "单价", "备注"]


@router.get("/categories")
def list_categories(
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    rows = conn.execute(
        "SELECT c.*, (SELECT COUNT(*) FROM materials m WHERE m.category_id = c.id AND m.active = 1)"
        " AS material_count FROM material_categories c ORDER BY c.sort, c.id"
    ).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.post("/categories")
def create_category(
    payload: dict,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles(*MANAGER_ROLES)),
):
    name = (payload.get("name") or "").strip()
    prefix = (payload.get("prefix") or "").strip().upper()
    if not name or not prefix:
        raise HTTPException(status_code=400, detail="分类名称和编号前缀不能为空")
    if not prefix.isalnum() or len(prefix) > 4:
        raise HTTPException(status_code=400, detail="编号前缀请用 1-4 位字母或数字")
    if conn.execute(
        "SELECT 1 FROM material_categories WHERE name = ? OR prefix = ?", (name, prefix)
    ).fetchone():
        raise HTTPException(status_code=400, detail="分类名称或前缀已存在")
    sort = conn.execute("SELECT COALESCE(MAX(sort),0)+1 FROM material_categories").fetchone()[0]
    cur = conn.execute(
        "INSERT INTO material_categories(name,prefix,sort,active) VALUES(?,?,?,1)",
        (name, prefix, sort),
    )
    conn.commit()
    return {"ok": True, "id": cur.lastrowid}


@router.put("/categories/{category_id}")
def update_category(
    category_id: int,
    payload: dict,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles(*MANAGER_ROLES)),
):
    row = conn.execute(
        "SELECT * FROM material_categories WHERE id = ?", (category_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="分类不存在")
    name = (payload.get("name") or row["name"]).strip()
    prefix = (payload.get("prefix") or row["prefix"]).strip().upper()
    if not prefix.isalnum() or len(prefix) > 4:
        raise HTTPException(status_code=400, detail="编号前缀请用 1-4 位字母或数字")
    if conn.execute(
        "SELECT 1 FROM material_categories WHERE (name = ? OR prefix = ?) AND id != ?",
        (name, prefix, category_id),
    ).fetchone():
        raise HTTPException(status_code=400, detail="分类名称或前缀已存在")
    conn.execute(
        "UPDATE material_categories SET name = ?, prefix = ? WHERE id = ?",
        (name, prefix, category_id),
    )
    # 分类改名后同步物资上的分类名称（编号保持不变）
    if name != row["name"]:
        conn.execute(
            "UPDATE materials SET category = ? WHERE category_id = ?", (name, category_id)
        )
    conn.commit()
    return {"ok": True}


@router.delete("/categories/{category_id}")
def delete_category(
    category_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles(*MANAGER_ROLES)),
):
    used = conn.execute(
        "SELECT COUNT(*) FROM materials WHERE category_id = ?", (category_id,)
    ).fetchone()[0]
    if used:
        raise HTTPException(status_code=400, detail="该分类下还有物资，无法删除")
    conn.execute("DELETE FROM material_categories WHERE id = ?", (category_id,))
    conn.commit()
    return {"ok": True}


@router.get("/materials")
def list_materials(
    keyword: str = "",
    category: str = "",
    category_id: int = 0,
    low_only: int = 0,
    page: int = 1,
    page_size: int = 50,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    where, params = ["active = 1"], []
    if keyword:
        kw = f"%{keyword.strip()}%"
        where.append("(name LIKE ? OR code LIKE ? OR spec LIKE ?)")
        params += [kw] * 3
    if category:
        where.append("category = ?")
        params.append(category)
    if category_id:
        where.append("category_id = ?")
        params.append(category_id)
    if low_only:
        where.append("stock <= warn_stock")
    total = conn.execute(
        "SELECT COUNT(*) FROM materials WHERE " + " AND ".join(where), params
    ).fetchone()[0]
    page = max(1, page)
    page_size = min(200, max(1, page_size))
    rows = conn.execute(
        "SELECT * FROM materials WHERE " + " AND ".join(where)
        + " ORDER BY category_id, code LIMIT ? OFFSET ?",
        params + [page_size, (page - 1) * page_size],
    ).fetchall()
    return {
        "items": [dict(r) for r in rows],
        "total": total,
        "categories": [
            r["name"]
            for r in conn.execute(
                "SELECT name FROM material_categories ORDER BY sort, id"
            )
        ],
    }


@router.get("/materials/options")
def material_options(
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    rows = conn.execute(
        "SELECT id, code, name, spec, unit, stock FROM materials WHERE active = 1"
        " ORDER BY category_id, code"
    ).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.get("/materials/template.csv")
def download_template(
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(CSV_HEADERS)
    writer.writerow(["示例-六类网线", "线材", "超六类 305米/箱", "箱", "10", "3", "机房A柜", "680", "示例行，导入前请删除"])
    content = "\ufeff" + buf.getvalue()
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="materials_template.csv"',
        },
    )


@router.post("/materials/import")
def import_materials(
    payload: ImportIn,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles(*MANAGER_ROLES)),
):
    text = (payload.content or "").lstrip("\ufeff")
    if not text.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="文件内容为空")

    header = [h.strip() for h in rows[0]]
    index = {}
    for i, h in enumerate(header):
        if h in CSV_HEADERS:
            index[h] = i
    for required in ("名称", "分类"):
        if required not in index:
            raise HTTPException(
                status_code=400,
                detail=f"模板缺少「{required}」列，请下载最新模板",
            )

    cats = {
        r["name"]: r
        for r in conn.execute("SELECT * FROM material_categories")
    }
    created, errors = 0, []
    ts = now()
    for line_no, row in enumerate(rows[1:], start=2):
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(rows) > 502:
            errors.append({"line": line_no, "message": "单次最多导入 500 行"})
            break

        def cell(name):
            i = index.get(name)
            return (row[i].strip() if i is not None and i < len(row) else "")

        name = cell("名称")
        category_name = cell("分类")
        if not name or name.startswith("示例-"):
            continue
        cat = cats.get(category_name)
        if not cat:
            errors.append(
                {"line": line_no, "message": f"分类「{category_name}」不存在，请先在分类管理中新增"}
            )
            continue
        try:
            stock = float(cell("初始库存") or 0)
            warn = float(cell("预警库存") or 0)
            price = float(cell("单价") or 0)
        except ValueError:
            errors.append({"line": line_no, "message": "库存 / 预警 / 单价必须是数字"})
            continue

        code = next_material_code(conn, cat["prefix"])
        cur = conn.execute(
            """INSERT INTO materials(code,name,category,category_id,spec,unit,stock,
                   warn_stock,location,unit_price,remark,active,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,1,?,?)""",
            (
                code, name, cat["name"], cat["id"], cell("规格"), cell("单位") or "个",
                stock, warn, cell("存放位置"), price, cell("备注"), ts, ts,
            ),
        )
        if stock > 0:
            conn.execute(
                "INSERT INTO stock_logs(material_id,kind,qty,before_stock,after_stock,"
                "operator,note,created_at) VALUES(?,'in',?,0,?,?,?,?)",
                (cur.lastrowid, stock, stock, staff["name"], "模板导入初始库存", ts),
            )
        created += 1
    conn.commit()
    return {"ok": True, "created": created, "errors": errors}


@router.post("/materials")
def create_material(
    payload: MaterialIn,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles(*MANAGER_ROLES)),
):
    cat = None
    if payload.category_id:
        cat = conn.execute(
            "SELECT * FROM material_categories WHERE id = ?", (payload.category_id,)
        ).fetchone()
    elif payload.category:
        cat = conn.execute(
            "SELECT * FROM material_categories WHERE name = ?", (payload.category.strip(),)
        ).fetchone()
    if not cat:
        raise HTTPException(status_code=400, detail="请选择物资分类")

    code = (payload.code or "").strip() or next_material_code(conn, cat["prefix"])
    if conn.execute("SELECT 1 FROM materials WHERE code = ?", (code,)).fetchone():
        raise HTTPException(status_code=400, detail="物资编号已存在")

    ts = now()
    cur = conn.execute(
        """INSERT INTO materials(code,name,category,category_id,spec,unit,stock,warn_stock,
               location,unit_price,remark,active,created_at,updated_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,1,?,?)""",
        (
            code, payload.name.strip(), cat["name"], cat["id"], payload.spec.strip(),
            payload.unit.strip() or "个", payload.stock, payload.warn_stock,
            payload.location.strip(), payload.unit_price, payload.remark.strip(), ts, ts,
        ),
    )
    if payload.stock > 0:
        conn.execute(
            "INSERT INTO stock_logs(material_id,kind,qty,before_stock,after_stock,"
            "operator,note,created_at) VALUES(?,'in',?,0,?,?,?,?)",
            (cur.lastrowid, payload.stock, payload.stock, staff["name"], "新建物资初始入库", ts),
        )
    conn.commit()
    return {"ok": True, "id": cur.lastrowid, "code": code}


@router.put("/materials/{material_id}")
def update_material(
    material_id: int,
    payload: MaterialUpdate,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles(*MANAGER_ROLES)),
):
    row = conn.execute(
        "SELECT * FROM materials WHERE id = ?", (material_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="物资不存在")
    data = payload.model_dump(exclude_none=True)

    if "category_id" in data or "category" in data:
        cat = None
        if data.get("category_id"):
            cat = conn.execute(
                "SELECT * FROM material_categories WHERE id = ?", (data["category_id"],)
            ).fetchone()
        elif data.get("category"):
            cat = conn.execute(
                "SELECT * FROM material_categories WHERE name = ?", (data["category"],)
            ).fetchone()
        if cat:
            data["category"] = cat["name"]
            data["category_id"] = cat["id"]
    data.pop("category", None)
    if "category_id" not in data:
        data.pop("category_id", None)

    if not data:
        return {"ok": True}
    data["updated_at"] = now()
    sets = ", ".join(f"{k} = ?" for k in data)
    conn.execute(
        f"UPDATE materials SET {sets} WHERE id = ?", list(data.values()) + [material_id]
    )
    conn.commit()
    return {"ok": True}


@router.post("/materials/{material_id}/inbound")
def inbound(
    material_id: int,
    payload: StockIn,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles(*MANAGER_ROLES)),
):
    if payload.qty <= 0:
        raise HTTPException(status_code=400, detail="入库数量必须大于 0")
    mat = conn.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
    if not mat:
        raise HTTPException(status_code=404, detail="物资不存在")
    ts = now()
    after = mat["stock"] + payload.qty
    conn.execute(
        "UPDATE materials SET stock = ?, updated_at = ? WHERE id = ?",
        (after, ts, material_id),
    )
    conn.execute(
        "INSERT INTO stock_logs(material_id,kind,qty,before_stock,after_stock,ticket_id,"
        "operator,note,created_at) VALUES(?,'in',?,?,?,?,?,?,?)",
        (
            material_id, payload.qty, mat["stock"], after, payload.ticket_id,
            staff["name"], payload.note.strip(), ts,
        ),
    )
    conn.commit()
    return {"ok": True, "stock": after}


@router.post("/materials/{material_id}/outbound")
def outbound(
    material_id: int,
    payload: StockIn,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles(*MANAGER_ROLES)),
):
    if payload.qty <= 0:
        raise HTTPException(status_code=400, detail="出库数量必须大于 0")
    mat = conn.execute("SELECT * FROM materials WHERE id = ?", (material_id,)).fetchone()
    if not mat:
        raise HTTPException(status_code=404, detail="物资不存在")
    if mat["stock"] < payload.qty:
        raise HTTPException(status_code=400, detail="库存不足")
    ts = now()
    after = mat["stock"] - payload.qty
    conn.execute(
        "UPDATE materials SET stock = ?, updated_at = ? WHERE id = ?",
        (after, ts, material_id),
    )
    conn.execute(
        "INSERT INTO stock_logs(material_id,kind,qty,before_stock,after_stock,ticket_id,"
        "operator,note,created_at) VALUES(?,'out',?,?,?,?,?,?,?)",
        (
            material_id, payload.qty, mat["stock"], after, payload.ticket_id,
            staff["name"], payload.note.strip(), ts,
        ),
    )
    conn.commit()
    return {"ok": True, "stock": after}


@router.get("/stock-logs")
def stock_logs(
    material_id: Optional[int] = None,
    kind: str = "",
    page: int = 1,
    page_size: int = 30,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    where, params = ["1=1"], []
    if material_id:
        where.append("l.material_id = ?")
        params.append(material_id)
    if kind in ("in", "out", "adjust"):
        where.append("l.kind = ?")
        params.append(kind)
    total = conn.execute(
        "SELECT COUNT(*) FROM stock_logs l WHERE " + " AND ".join(where), params
    ).fetchone()[0]
    page = max(1, page)
    page_size = min(200, max(1, page_size))
    rows = conn.execute(
        "SELECT l.*, m.name AS material_name, m.code AS material_code, m.unit,"
        " t.code AS ticket_code FROM stock_logs l"
        " JOIN materials m ON m.id = l.material_id"
        " LEFT JOIN tickets t ON t.id = l.ticket_id"
        " WHERE " + " AND ".join(where)
        + " ORDER BY l.id DESC LIMIT ? OFFSET ?",
        params + [page_size, (page - 1) * page_size],
    ).fetchall()
    return {"items": [dict(r) for r in rows], "total": total}
