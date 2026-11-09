"""测试环境模拟数据：工单、设备台账、物资领用。

仅在 OPS_SEED_TEST_DATA=1 时执行；首次执行后写入 WOT 前缀工单，重复启动不会重复插入。
"""
import base64
import io
import os
import random
from datetime import datetime, timedelta

from .crypto import encrypt
from .db import connect, now
from .security import hash_password

PREFIX = "WOT"


def _enabled() -> bool:
    return os.environ.get("OPS_SEED_TEST_DATA", "").strip().lower() in ("1", "true", "yes", "on")


def _fmt(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _signature() -> str:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (300, 100), (255, 255, 255))
    d = ImageDraw.Draw(img)
    pts = []
    for i in range(0, 280, 4):
        y = 55 + 22 * ((i // 40) % 2 * 2 - 1) * (1 if (i // 20) % 2 == 0 else -1)
        pts.append((10 + i, y))
    d.line(pts, fill=(30, 45, 70), width=3)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _ticket_code(day: datetime, n: int) -> str:
    return f"{PREFIX}{day.strftime('%Y%m%d')}{n:03d}"


def seed(conn) -> dict:
    rooms = [dict(r) for r in conn.execute("SELECT * FROM rooms WHERE active = 1 ORDER BY id")]
    faults = [r["name"] for r in conn.execute("SELECT name FROM fault_types WHERE active = 1 ORDER BY sort, id")]
    staff = [dict(r) for r in conn.execute("SELECT * FROM staff WHERE active = 1 ORDER BY id")]
    engineers = [s for s in staff if "engineer" in (s["roles"] or s["role"]).split(",")]
    dispatchers = [s for s in staff if "dispatcher" in (s["roles"] or s["role"]).split(",")]
    materials = [dict(r) for r in conn.execute("SELECT * FROM materials WHERE active = 1 AND stock > 2 ORDER BY id")]
    if not rooms or not faults or not engineers:
        return {"tickets": 0, "assets": 0}

    # 补充测试账号：覆盖纯工程师与“受理员 + 工程师”多角色
    extra_users = [
        ("wangwu", "王五", "engineer", "engineer", "13900001111"),
        ("zhaoliu", "赵六", "dispatcher", "dispatcher,engineer", "13900002222"),
    ]
    for username, name, role, roles, phone in extra_users:
        if conn.execute("SELECT 1 FROM staff WHERE username = ?", (username,)).fetchone():
            continue
        salt = os.urandom(16).hex()
        conn.execute(
            "INSERT INTO staff(username,name,role,roles,phone,email,pwd_hash,pwd_salt,active,created_at)"
            " VALUES(?,?,?,?,?,?,?,?,1,?)",
            (username, name, role, roles, phone, "", hash_password("eng123", salt), salt, now()),
        )
    conn.commit()
    staff = [dict(r) for r in conn.execute("SELECT * FROM staff WHERE active = 1 ORDER BY id")]
    engineers = [s for s in staff if "engineer" in (s["roles"] or s["role"]).split(",")]
    dispatchers = [s for s in staff if "dispatcher" in (s["roles"] or s["role"]).split(",")]

    random.seed(20261109)
    dispatcher = dispatchers[0] if dispatchers else engineers[0]
    contacts = [
        ("王小明", "13911001001"), ("李静", "13911001002"), ("赵强", "13911001003"),
        ("陈晨", "13911001004"), ("周涛", "13911001005"), ("吴敏", "13911001006"),
        ("郑伟", "13911001007"), ("孙丽", "13911001008"), ("胡军", "13911001009"),
        ("高远", "13911001010"), ("刘洋", "13911001011"), ("何芳", "13911001012"),
    ]
    devices = ["台式电脑", "笔记本电脑", "打印机", "复印机", "投影仪", "门禁读卡器",
               "网络交换机", "无线路由器", "服务器", "机房空调", "UPS 电源", "IP 电话"]
    descs = [
        "设备无法正常使用，请安排上门处理",
        "开机后无响应，重启多次仍未恢复",
        "网络时断时续，影响日常办公",
        "打印/复印异常，出现卡纸或报错",
        "会议设备无法投屏，下午有会议",
        "门禁刷卡无反应，需要现场检查",
    ]
    causes = ["电源接触不良，重新插拔后恢复", "网线水晶头松动，重新压接",
              "驱动异常，重新安装后正常", "设备老化，更换配件后恢复",
              "配置错误，恢复默认配置", "灰尘堆积，清理后恢复"]
    plans = ["pending"] * 6 + ["accepted"] * 4 + ["processing"] * 4 + ["pending_confirm"] * 4 + ["confirmed"] * 4 + ["cancelled"] * 2
    sig = _signature()
    base = datetime.now() - timedelta(days=7)
    count = 0
    material_used = 0

    for i, status in enumerate(plans, start=1):
        created = base + timedelta(days=(i - 1) % 7, hours=8 + (i * 3) % 9, minutes=(i * 7) % 60)
        accepted = created + timedelta(minutes=12)
        started = accepted + timedelta(minutes=25)
        finished = started + timedelta(minutes=45)
        confirmed = finished + timedelta(minutes=30)
        room = rooms[i % len(rooms)]
        contact, phone = contacts[i % len(contacts)]
        engineer = engineers[i % len(engineers)]
        expect = ["立即上门", "今天 09:00-12:00", "今天 14:00-18:00"][i % 3]
        location = f"{room['building']}{room['floor']} {room['room_no']}室（{room['name']}）"
        assignee_id = None if status == "pending" else engineer["id"]
        dispatcher_id = None if status == "pending" else dispatcher["id"]
        accepted_at = "" if status == "pending" else _fmt(accepted)
        started_at = _fmt(started) if status in ("processing", "pending_confirm", "confirmed") else ""
        finished_at = _fmt(finished) if status in ("pending_confirm", "confirmed") else ""
        confirm_at = _fmt(confirmed) if status == "confirmed" else ""
        cause = causes[i % len(causes)] if status in ("pending_confirm", "confirmed") else ""
        solve = "已更换配件并测试正常" if status in ("pending_confirm", "confirmed") else ""
        if status == "cancelled":
            solve = "重复报障，已合并处理"
        updated = _fmt(confirmed if status == "confirmed" else (finished if finished_at else (started if started_at else (accepted if accepted_at else created))))

        cur = conn.execute(
            """INSERT INTO tickets(code, room_id, location, device, fault_type, description,
               contact_name, contact_phone, status, dispatcher_id, assignee_id,
               accepted_at, started_at, finished_at, confirm_at, rating, confirm_comment,
               fault_cause, solve_note, created_at, updated_at, expect_time, signature, source, photos)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                _ticket_code(created, i), room["id"], location, devices[i % len(devices)],
                faults[i % len(faults)], descs[i % len(descs)], contact, phone, status,
                dispatcher_id, assignee_id, accepted_at, started_at, finished_at, confirm_at,
                5 if status == "confirmed" else 0,
                "处理及时，问题已解决" if status == "confirmed" else "",
                cause, solve, _fmt(created), updated, expect,
                sig if status == "confirmed" else "", "phone" if i % 5 == 0 else "qr", "[]",
            ),
        )
        tid = cur.lastrowid
        count += 1

        logs = [(contact, "提交报障", f"{location} · {devices[i % len(devices)]}", _fmt(created))]
        if status != "pending":
            logs.append((f"{dispatcher['name']}（报障受理员）", "受理并指派处理人", engineer["name"], _fmt(accepted)))
        if started_at:
            logs.append((f"{engineer['name']}（运维工程师）", "开始上门处理", "", started_at))
        if finished_at:
            logs.append((f"{engineer['name']}（运维工程师）", "提交处理结果", cause, finished_at))
        if status == "confirmed":
            logs.append((contact, "确认完成", "评分 5 星", confirm_at))
        if status == "cancelled":
            logs.append((f"{dispatcher['name']}（报障受理员）", "关闭工单", solve, _fmt(accepted)))
        for actor, action, note, at in logs:
            conn.execute(
                "INSERT INTO ticket_logs(ticket_id, actor, action, note, created_at) VALUES(?,?,?,?,?)",
                (tid, actor, action, note, at),
            )

        if status in ("pending_confirm", "confirmed") and materials and i % 3 == 0:
            mat = materials[material_used % len(materials)]
            material_used += 1
            before = float(mat["stock"])
            if before >= 1:
                after = before - 1
                conn.execute("UPDATE materials SET stock = ? WHERE id = ?", (after, mat["id"]))
                conn.execute(
                    "INSERT INTO stock_logs(material_id, kind, qty, before_stock, after_stock,"
                    " ticket_id, operator, note, created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                    (mat["id"], "out", -1, before, after, tid, engineer["name"], "工单领用", finished_at),
                )
                conn.execute(
                    "INSERT INTO ticket_materials(ticket_id, material_id, material_name, spec, unit, qty, created_at)"
                    " VALUES(?,?,?,?,?,?,?)",
                    (tid, mat["id"], mat["name"], mat["spec"], mat["unit"], 1, finished_at),
                )

    # 设备台账
    assets = [
        ("TEST-0001", "测试核心交换机", "网络设备", "华为 S5735", "TST-SW-001", "A01 机柜 U12", "https://10.10.99.1", "192.168.99.1", "admin"),
        ("TEST-0002", "测试文件服务器", "服务器", "联想 SR650", "TST-SRV-002", "B01 机柜 U06", "业务网 10.10.99.2", "https://10.10.99.2:8443", "root"),
        ("TEST-0003", "测试防火墙", "安全设备", "深信服 AF-1000", "TST-FW-003", "A02 机柜 U20", "外网出口 192.168.99.3", "https://192.168.99.3", "admin"),
        ("TEST-0004", "测试打印机", "打印设备", "惠普 M405dn", "TST-PRN-004", "3 楼打印区", "打印网 10.10.99.4", "http://10.10.99.4", "admin"),
        ("TEST-0005", "测试会议平板", "终端设备", "MAXHUB V6", "TST-MTG-005", "会议室 A", "无线投屏 10.10.99.5", "https://10.10.99.5", "admin"),
        ("TEST-0006", "测试存储", "存储设备", "群晖 RS1221+", "TST-NAS-006", "B02 机柜 U14", "存储网段 10.10.99.6", "https://10.10.99.6:5001", "admin"),
    ]
    asset_count = 0
    for idx, (code, name, cat, model, sn, rack, net, addr, user) in enumerate(assets):
        if conn.execute("SELECT 1 FROM assets WHERE code = ?", (code,)).fetchone():
            continue
        room = rooms[idx % len(rooms)]
        conn.execute(
            """INSERT INTO assets(code, name, category, brand_model, serial_no, room_id, location,
               rack_position, install_date, status, network, mgmt_address, mgmt_user, mgmt_password,
               mgmt_port, owner, vendor, warranty_until, note, active, created_at, updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)""",
            (
                code, name, cat, model, sn, room["id"],
                f"{room['building']}{room['floor']} {room['room_no']}室（{room['name']}）",
                rack, "2025-06-01", "在用" if idx % 4 else "维修", net, addr, user,
                encrypt(conn, "Test@123"), "443", engineer["name"], "测试供应商",
                "2028-06-01", "测试数据", _fmt(base), _fmt(base),
            ),
        )
        asset_count += 1

    conn.commit()
    return {"tickets": count, "assets": asset_count, "materials_used": material_used}


def maybe_seed_test_data() -> None:
    if not _enabled():
        return
    conn = connect()
    try:
        if conn.execute("SELECT 1 FROM tickets WHERE code LIKE ? LIMIT 1", (PREFIX + "%",)).fetchone():
            return
        result = seed(conn)
        if result["tickets"]:
            print(f"[test-seed] tickets={result['tickets']} assets={result['assets']} materials={result['materials_used']}")
    finally:
        conn.close()
