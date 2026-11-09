"""房间管理与二维码生成、批量打印标签。"""
import base64
import io
import ipaddress
import os
import socket
import sqlite3
from html import escape

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from ..db import get_db, now
from ..schemas import RoomIn
from ..security import COOKIE_STAFF, current_staff, require_roles, sha256

router = APIRouter(prefix="/api/staff/rooms", tags=["rooms"])
print_router = APIRouter(tags=["print"])


def qr_png(data: str, box: int = 8) -> bytes:
    img = qrcode.make(data, box_size=box, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _is_lan_ip(ip: str) -> bool:
    """排除回环、链路本地、VPN 虚拟网段（198.18/15）等地址。"""
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    if addr.is_loopback or addr.is_link_local or addr.is_multicast:
        return False
    if ip.startswith("198.18.") or ip.startswith("198.19."):
        return False
    return addr.is_private


def detect_lan_ip() -> str:
    """获取本机在局域网中的地址，便于手机扫码访问。"""
    candidates = []
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        candidates.append(sock.getsockname()[0])
    except Exception:
        pass
    finally:
        sock.close()
    try:
        candidates += socket.gethostbyname_ex(socket.gethostname())[2]
    except Exception:
        pass

    usable = [ip for ip in dict.fromkeys(candidates) if _is_lan_ip(ip)]

    def score(ip: str) -> int:
        if ip.startswith("192.168."):
            return 0
        if ip.startswith("10."):
            return 1
        if ip.startswith("172."):
            return 2
        return 3

    usable.sort(key=score)
    return usable[0] if usable else ""


def base_url(conn: sqlite3.Connection, request: Request) -> str:
    row = conn.execute(
        "SELECT value FROM settings WHERE key = 'public_base_url'"
    ).fetchone()
    if row and row["value"]:
        return row["value"].rstrip("/")
    env_base = os.environ.get("OPS_PUBLIC_BASE_URL", "").strip()
    if env_base:
        return env_base.rstrip("/")
    url = str(request.base_url).rstrip("/")
    host = request.url.hostname or ""
    if host in ("127.0.0.1", "localhost", "0.0.0.0"):
        lan = detect_lan_ip()
        if lan:
            port = request.url.port
            url = f"{request.url.scheme}://{lan}" + (f":{port}" if port else "")
    return url


@router.get("")
def list_rooms(
    keyword: str = "",
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    where, params = ["r.active = 1"], []
    if keyword:
        kw = f"%{keyword.strip()}%"
        where.append("(r.building LIKE ? OR r.room_no LIKE ? OR r.name LIKE ?)")
        params += [kw] * 3
    rows = conn.execute(
        """SELECT r.*,
             (SELECT COUNT(*) FROM tickets t WHERE t.room_id = r.id) AS ticket_count,
             (SELECT COUNT(*) FROM tickets t WHERE t.room_id = r.id
                AND t.status IN ('pending','accepted','processing','pending_confirm')) AS open_count
           FROM rooms r WHERE """
        + " AND ".join(where)
        + " ORDER BY CASE r.importance WHEN '核心' THEN 0 WHEN '重要' THEN 1 ELSE 2 END,"
        + " r.building, r.floor, r.room_no",
        params,
    ).fetchall()
    return {"items": [dict(r) for r in rows]}


@router.post("")
def create_room(
    payload: RoomIn,
    request: Request,
    conn: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_roles("admin")),
):
    qr_code = os.urandom(5).hex()
    importance = payload.importance if payload.importance in ("普通", "重要", "核心") else "普通"
    cur = conn.execute(
        "INSERT INTO rooms(building,floor,room_no,name,qr_code,note,importance,active,created_at)"
        " VALUES(?,?,?,?,?,?,?,?,?)",
        (
            payload.building.strip(), payload.floor.strip(), payload.room_no.strip(),
            payload.name.strip(), qr_code, payload.note.strip(), importance, payload.active, now(),
        ),
    )
    conn.commit()
    return {
        "ok": True,
        "id": cur.lastrowid,
        "qr_code": qr_code,
        "url": f"{base_url(conn, request)}/r/{qr_code}",
    }


@router.put("/{room_id}")
def update_room(
    room_id: int,
    payload: RoomIn,
    conn: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_roles("admin")),
):
    row = conn.execute("SELECT id FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="房间不存在")
    importance = payload.importance if payload.importance in ("普通", "重要", "核心") else "普通"
    conn.execute(
        "UPDATE rooms SET building=?, floor=?, room_no=?, name=?, note=?, importance=?, active=? WHERE id=?",
        (
            payload.building.strip(), payload.floor.strip(), payload.room_no.strip(),
            payload.name.strip(), payload.note.strip(), importance, payload.active, room_id,
        ),
    )
    conn.commit()
    return {"ok": True}


@router.delete("/{room_id}")
def delete_room(
    room_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_roles("admin")),
):
    conn.execute("UPDATE rooms SET active = 0 WHERE id = ?", (room_id,))
    conn.commit()
    return {"ok": True}


@router.post("/{room_id}/regen-qr")
def regen_qr(
    room_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_roles("admin")),
):
    row = conn.execute("SELECT id FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="房间不存在")
    code = os.urandom(5).hex()
    conn.execute("UPDATE rooms SET qr_code = ? WHERE id = ?", (code, room_id))
    conn.commit()
    return {"ok": True, "qr_code": code}


@router.get("/{room_id}/qr.png")
def room_qr(
    room_id: int,
    request: Request,
    size: int = 240,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    room = conn.execute("SELECT * FROM rooms WHERE id = ?", (room_id,)).fetchone()
    if not room:
        raise HTTPException(status_code=404, detail="房间不存在")
    url = f"{base_url(conn, request)}/r/{room['qr_code']}"
    box = 8
    png = qr_png(url, box=box)
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "no-store"})


def label_html(room: dict, url: str) -> str:
    png = qr_png(url, box=6)
    b64 = base64.b64encode(png).decode()
    return f"""
    <div class="label">
      <div class="qr"><img src="data:image/png;base64,{b64}" alt="qr"/></div>
      <div class="info">
        <div class="loc">{escape(room['building'])}{escape(room['floor'])}层</div>
        <div class="room">{escape(room['room_no'])}室</div>
        <div class="name">{escape(room['name'] or '')}</div>
        <div class="hint">设备故障？扫码报障</div>
        <div class="code">{escape(room['qr_code'])}</div>
      </div>
    </div>"""


@print_router.get("/print/rooms", response_class=HTMLResponse)
def print_rooms(
    request: Request,
    ids: str = "",
    conn: sqlite3.Connection = Depends(get_db),
):
    token = request.cookies.get(COOKIE_STAFF)
    if not token or not conn.execute(
        "SELECT 1 FROM sessions WHERE token_hash = ?", (sha256(token),)
    ).fetchone():
        return HTMLResponse(
            "<meta charset='utf-8'><div style='font-family:sans-serif;padding:40px'>"
            "请先登录运维后台后再打开打印页面。<a href='/'>返回首页</a></div>",
            status_code=401,
        )
    id_list = [int(x) for x in ids.split(",") if x.strip().isdigit()]
    if id_list:
        marks = ",".join("?" * len(id_list))
        rows = conn.execute(
            f"SELECT * FROM rooms WHERE id IN ({marks}) AND active = 1"
            " ORDER BY building, floor, room_no",
            id_list,
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM rooms WHERE active = 1 ORDER BY building, floor, room_no"
        ).fetchall()
    base = base_url(conn, request)
    labels = "".join(
        label_html(dict(r), f"{base}/r/{r['qr_code']}") for r in rows
    )
    return HTMLResponse(
        f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8"/>
<title>报障二维码标签</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: -apple-system, "PingFang SC", sans-serif; background: #f2f4f7; }}
  .toolbar {{ padding: 12px 20px; background: #fff; border-bottom: 1px solid #e4e7ed;
             display: flex; gap: 12px; align-items: center; }}
  .toolbar button {{ padding: 8px 18px; border: 1px solid #409eff; background: #409eff;
                     color: #fff; border-radius: 6px; cursor: pointer; font-size: 14px; }}
  .sheet {{ background: #fff; width: 210mm; margin: 16px auto; padding: 8mm;
            display: grid; grid-template-columns: repeat(3, 1fr); gap: 4mm; }}
  .label {{ border: 1px dashed #c0c4cc; border-radius: 4mm; padding: 3.5mm;
            display: flex; gap: 3mm; align-items: center; height: 52mm; overflow: hidden; }}
  .qr {{ flex: 0 0 auto; }}
  .qr img {{ width: 26mm; height: 26mm; display: block; }}
  .info {{ min-width: 0; flex: 1; }}
  .loc {{ font-size: 9pt; color: #909399; }}
  .room {{ font-size: 15pt; font-weight: 700; color: #1f2d3d; line-height: 1.3; }}
  .name {{ font-size: 9pt; color: #606266; white-space: nowrap; overflow: hidden;
          text-overflow: ellipsis; }}
  .hint {{ font-size: 8pt; color: #409eff; margin-top: 1.2mm; line-height: 1.3; }}
  .code {{ font-size: 6pt; color: #c0c4cc; letter-spacing: 0.3px; margin-top: 0.8mm; }}
  @media print {{
    body {{ background: #fff; }}
    .toolbar {{ display: none; }}
    .sheet {{ margin: 0; padding: 6mm; }}
    .label {{ break-inside: avoid; }}
  }}
</style></head>
<body>
  <div class="toolbar">
    <button onclick="window.print()">打印 / 另存为 PDF</button>
    <span style="color:#909399;font-size:13px">共 {len(rows)} 张标签 · A4 纸 3 列排版 · 建议贴于房间门旁</span>
  </div>
  <div class="sheet">{labels}</div>
</body></html>"""
    )
