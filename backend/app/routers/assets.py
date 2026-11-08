"""设备台账：资产位置、上架时间、网络、管理账号密码与批量导入。"""
import base64
import csv
import io
import json
import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response

from ..crypto import decrypt, encrypt
from ..db import get_db, now
from ..security import current_staff, require_roles

router = APIRouter(prefix="/api/staff/assets", tags=["assets"])

CATEGORIES = ["服务器", "网络设备", "安全设备", "存储设备", "终端设备", "打印设备", "其他"]
STATUSES = ["在用", "备用", "维修", "报废"]

HEADERS = [
    "资产编号", "设备名称", "设备类型", "品牌型号", "序列号", "所在房间(房间号)",
    "位置/机柜", "上架时间", "状态", "网络信息", "管理地址", "管理账号",
    "管理密码", "管理端口", "责任人", "供应商", "保修到期", "备注",
]

FIELD_MAP = {
    "资产编号": "code",
    "设备名称": "name",
    "设备类型": "category",
    "品牌型号": "brand_model",
    "序列号": "serial_no",
    "所在房间(房间号)": "room_hint",
    "位置/机柜": "rack_position",
    "上架时间": "install_date",
    "状态": "status",
    "网络信息": "network",
    "管理地址": "mgmt_address",
    "管理账号": "mgmt_user",
    "管理密码": "mgmt_password",
    "管理端口": "mgmt_port",
    "责任人": "owner",
    "供应商": "vendor",
    "保修到期": "warranty_until",
    "备注": "note",
}

EDITABLE = (
    "name", "category", "brand_model", "serial_no", "room_id", "location",
    "rack_position", "install_date", "status", "network", "mgmt_address",
    "mgmt_user", "mgmt_password", "mgmt_port", "owner", "vendor",
    "warranty_until", "note",
)


def next_code(conn: sqlite3.Connection) -> str:
    rows = conn.execute("SELECT code FROM assets WHERE code LIKE 'ZC-%'").fetchall()
    max_no = 0
    for r in rows:
        tail = r["code"].split("-", 1)[-1]
        if tail.isdigit():
            max_no = max(max_no, int(tail))
    return f"ZC-{max_no + 1:04d}"


def room_location(conn, room_id):
    if not room_id:
        return ""
    room = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if not room:
        return ""
    loc = f"{room['building']}{room['floor']}层 {room['room_no']}室"
    if room["name"]:
        loc += f"（{room['name']}）"
    return loc


def public_row(row) -> dict:
    data = dict(row)
    data["password_set"] = bool(data.pop("mgmt_password", ""))
    return data


@router.get("")
def list_assets(
    keyword: str = "",
    category: str = "",
    status: str = "",
    room_id: int = 0,
    page: int = 1,
    page_size: int = 30,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    where, params = ["active = 1"], []
    if keyword:
        kw = f"%{keyword.strip()}%"
        where.append(
            "(code LIKE ? OR name LIKE ? OR brand_model LIKE ? OR serial_no LIKE ?"
            " OR mgmt_address LIKE ? OR network LIKE ? OR owner LIKE ?)"
        )
        params += [kw] * 7
    if category:
        where.append("category = ?")
        params.append(category)
    if status:
        where.append("status = ?")
        params.append(status)
    if room_id:
        where.append("room_id = ?")
        params.append(room_id)
    total = conn.execute(
        "SELECT COUNT(*) FROM assets WHERE " + " AND ".join(where), params
    ).fetchone()[0]
    page = max(1, page)
    page_size = min(200, max(1, page_size))
    rows = conn.execute(
        "SELECT * FROM assets WHERE " + " AND ".join(where)
        + " ORDER BY category, code LIMIT ? OFFSET ?",
        params + [page_size, (page - 1) * page_size],
    ).fetchall()
    return {"items": [public_row(r) for r in rows], "total": total, "page": page}


@router.get("/meta")
def meta(
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    rooms = [
        {
            "id": r["id"],
            "location": room_location(conn, r["id"]),
        }
        for r in conn.execute(
            "SELECT id FROM rooms WHERE active = 1 ORDER BY building, floor, room_no"
        )
    ]
    return {"categories": CATEGORIES, "statuses": STATUSES, "rooms": rooms}


@router.get("/template.xlsx")
def download_template(
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    ws = wb.active
    ws.title = "设备台账"
    ws.append(HEADERS)
    header_fill = PatternFill("solid", fgColor="2F6FEB")
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.alignment = Alignment(horizontal="center", vertical="center")

    example = [
        "ZC-0099", "示例交换机", "网络设备", "华为 S5735", "SN202400001",
        "102", "A03 机柜 U10", "2026-01-01", "在用", "VLAN 30 / 10.10.30.1",
        "https://10.10.30.1", "admin", "Admin@123", "443", "张工", "华为",
        "2029-01-01", "示例行，导入前请删除",
    ]
    ws.append(example)
    widths = [12, 16, 12, 20, 16, 20, 16, 12, 10, 24, 22, 12, 14, 10, 10, 12, 12, 28]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + i)].width = w
    ws.freeze_panes = "A2"

    info = wb.create_sheet("填写说明")
    tips = [
        ["字段", "说明"],
        ["设备名称", "必填"],
        ["设备类型", "可选：" + "、".join(CATEGORIES)],
        ["所在房间(房间号)", "填写房间号（如 102）或完整位置（如 2号楼1层 102室），可留空"],
        ["上架时间 / 保修到期", "格式 YYYY-MM-DD，可留空"],
        ["状态", "可选：" + "、".join(STATUSES) + "，默认在用"],
        ["资产编号", "留空则自动生成 ZC-0001 形式的编号"],
        ["管理密码", "导入后加密保存，仅管理员可查看明文"],
        ["示例行", "请删除后再导入，避免产生假数据"],
    ]
    for row in tips:
        info.append(row)
    for cell in info[1]:
        cell.font = Font(bold=True)
    info.column_dimensions["A"].width = 22
    info.column_dimensions["B"].width = 70

    buf = io.BytesIO()
    wb.save(buf)
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="assets_template.xlsx"'},
    )


@router.post("/import")
def import_assets(
    payload: dict,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles("admin", "dispatcher")),
):
    filename = (payload.get("filename") or "").lower()
    content = payload.get("content_base64") or ""
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    try:
        raw = base64.b64decode(content.split(",")[-1])
    except Exception:
        raise HTTPException(status_code=400, detail="文件解析失败")

    rows = []
    if filename.endswith(".csv"):
        text = raw.decode("utf-8-sig", errors="ignore")
        reader = csv.reader(io.StringIO(text))
        rows = [list(r) for r in reader]
    elif filename.endswith(".xlsx") or filename.endswith(".xlsm"):
        from openpyxl import load_workbook

        wb = load_workbook(io.BytesIO(raw), data_only=True)
        ws = wb.active
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
    else:
        raise HTTPException(status_code=400, detail="仅支持 .xlsx 或 .csv 文件")
    if len(rows) < 2:
        raise HTTPException(status_code=400, detail="文件中没有数据行")
    if len(rows) > 501:
        raise HTTPException(status_code=400, detail="单次最多导入 500 行")

    header = [str(h).strip() if h is not None else "" for h in rows[0]]
    index = {h: i for i, h in enumerate(header) if h in FIELD_MAP}
    if "设备名称" not in index:
        raise HTTPException(status_code=400, detail="缺少「设备名称」列，请下载最新模板")

    created, errors = 0, []
    ts = now()
    for line_no, row in enumerate(rows[1:], start=2):
        if not row or not any(str(x).strip() for x in row if x is not None):
            continue

        def cell(name):
            i = index.get(name)
            if i is None or i >= len(row) or row[i] is None:
                return ""
            return str(row[i]).strip()

        name = cell("设备名称")
        if not name:
            continue
        if name.startswith("示例"):
            continue
        code = cell("资产编号") or next_code(conn)
        if conn.execute("SELECT 1 FROM assets WHERE code = ?", (code,)).fetchone():
            errors.append({"line": line_no, "message": f"资产编号 {code} 已存在"})
            continue

        category = cell("设备类型") or "其他"
        status = cell("状态") or "在用"
        room_hint = cell("所在房间(房间号)")
        room_id = None
        location = room_hint
        if room_hint:
            room = conn.execute(
                "SELECT * FROM rooms WHERE room_no = ?", (room_hint,)
            ).fetchone()
            if not room:
                room = conn.execute(
                    "SELECT * FROM rooms WHERE ? LIKE '%' || room_no || '%'"
                    " AND active = 1 LIMIT 1",
                    (room_hint,),
                ).fetchone()
            if room:
                room_id = room["id"]
                location = room_location(conn, room_id)

        conn.execute(
            """INSERT INTO assets(code,name,category,brand_model,serial_no,room_id,location,
                   rack_position,install_date,status,network,mgmt_address,mgmt_user,
                   mgmt_password,mgmt_port,owner,vendor,warranty_until,note,active,
                   created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)""",
            (
                code, name, category, cell("品牌型号"), cell("序列号"), room_id,
                location, cell("位置/机柜"), cell("上架时间"), status, cell("网络信息"),
                cell("管理地址"), cell("管理账号"), encrypt(conn, cell("管理密码")),
                cell("管理端口"), cell("责任人"), cell("供应商"), cell("保修到期"),
                cell("备注"), ts, ts,
            ),
        )
        created += 1
    conn.commit()
    return {"ok": True, "created": created, "errors": errors}


@router.post("")
def create_asset(
    payload: dict,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles("admin", "dispatcher")),
):
    if not (payload.get("name") or "").strip():
        raise HTTPException(status_code=400, detail="设备名称不能为空")
    code = (payload.get("code") or "").strip() or next_code(conn)
    if conn.execute("SELECT 1 FROM assets WHERE code = ?", (code,)).fetchone():
        raise HTTPException(status_code=400, detail="资产编号已存在")
    data = {k: payload.get(k) for k in EDITABLE if k in payload}
    room_id = payload.get("room_id") or None
    data["room_id"] = room_id
    data["location"] = room_location(conn, room_id) or (payload.get("location") or "").strip()
    data["mgmt_password"] = encrypt(conn, (payload.get("mgmt_password") or "").strip())
    ts = now()
    columns = ["code"] + list(data.keys()) + ["active", "created_at", "updated_at"]
    values = [code] + list(data.values()) + [1, ts, ts]
    conn.execute(
        f"INSERT INTO assets({', '.join(columns)}) VALUES({', '.join('?' * len(columns))})",
        values,
    )
    conn.commit()
    return {"ok": True, "code": code, "id": conn.execute("SELECT last_insert_rowid()").fetchone()[0]}


@router.put("/{asset_id}")
def update_asset(
    asset_id: int,
    payload: dict,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles("admin", "dispatcher")),
):
    row = conn.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="设备不存在")
    data = {k: payload.get(k) for k in EDITABLE if k in payload}
    if "room_id" in data:
        data["location"] = room_location(conn, data["room_id"]) or (payload.get("location") or "").strip()
    if "mgmt_password" in data:
        pwd = (data.pop("mgmt_password") or "").strip()
        if pwd:
            data["mgmt_password"] = encrypt(conn, pwd)
    if not data:
        return {"ok": True}
    data["updated_at"] = now()
    sets = ", ".join(f"{k} = ?" for k in data)
    conn.execute(f"UPDATE assets SET {sets} WHERE id = ?", list(data.values()) + [asset_id])
    conn.commit()
    return {"ok": True}


@router.delete("/{asset_id}")
def delete_asset(
    asset_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles("admin", "dispatcher")),
):
    conn.execute("UPDATE assets SET active = 0 WHERE id = ?", (asset_id,))
    conn.commit()
    return {"ok": True}


@router.post("/{asset_id}/reveal-password")
def reveal_password(
    asset_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_roles("admin")),
):
    row = conn.execute(
        "SELECT mgmt_password FROM assets WHERE id = ? AND active = 1", (asset_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="设备不存在")
    return {"password": decrypt(conn, row["mgmt_password"])}
