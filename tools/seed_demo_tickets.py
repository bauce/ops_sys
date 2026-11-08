"""生成演示工单：覆盖全部故障类型与全部状态。

用法：.venv/bin/python tools/seed_demo_tickets.py
"""
import base64
import io
import json
import random
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DB = BASE / "backend" / "data" / "ops.db"
UPLOAD = BASE / "backend" / "data" / "uploads" / "202611"
UPLOAD.mkdir(parents=True, exist_ok=True)

random.seed(20261106)

DEVICES = {
    "网络无法访问": ["房间网口", "无线路由器", "网络交换机", "笔记本网卡"],
    "电脑/终端故障": ["台式电脑", "笔记本电脑", "一体机", "瘦客户机"],
    "打印机/复印机故障": ["激光打印机", "喷墨打印机", "复印机", "扫描仪"],
    "电话故障": ["办公电话", "电话交换机", "IP 话机"],
    "服务器/系统故障": ["业务服务器", "文件服务器", "数据库服务器"],
    "投影/会议设备故障": ["投影仪", "会议平板", "无线投屏器", "音响系统"],
    "门禁/监控故障": ["门禁读卡器", "监控摄像头", "录像机"],
    "软件使用问题": ["办公软件", "业务系统", "浏览器", "杀毒软件"],
    "其他": ["机房空调", "UPS 电源", "机柜", "其他设备"],
}

DESCRIPTIONS = {
    "网络无法访问": "电脑连不上内网，网页打不开，网口灯不亮",
    "电脑/终端故障": "开机后黑屏，风扇转动但无显示",
    "打印机/复印机故障": "打印卡纸，提示缺纸但纸盒有纸",
    "电话故障": "电话无拨号音，外线打不进来",
    "服务器/系统故障": "业务系统访问缓慢，偶发 502 错误",
    "投影/会议设备故障": "投影仪无信号，切换 HDMI 后仍黑屏",
    "门禁/监控故障": "门禁刷卡无反应，监控画面黑屏",
    "软件使用问题": "办公软件打开报错，无法保存文件",
    "其他": "机房空调告警，UPS 电池指示灯异常",
}

CAUSES = {
    "网络无法访问": "网线水晶头松动，重新压接后恢复",
    "电脑/终端故障": "内存条接触不良，重新插拔并清灰",
    "打印机/复印机故障": "进纸轮老化，清理卡纸并更换配件",
    "电话故障": "话机接线松动，重新插拔后恢复",
    "服务器/系统故障": "服务进程异常退出，重启服务并调整内存参数",
    "投影/会议设备故障": "HDMI 线接触不良，更换线缆后正常",
    "门禁/监控故障": "读卡器供电不足，更换电源适配器",
    "软件使用问题": "配置文件损坏，重置配置后恢复",
    "其他": "滤网积灰导致高温告警，清洗滤网后恢复",
}

CONTACTS = [
    ("王小明", "13911001001"), ("李静", "13911001002"), ("赵强", "13911001003"),
    ("陈晨", "13911001004"), ("周涛", "13911001005"), ("吴敏", "13911001006"),
    ("郑伟", "13911001007"), ("孙丽", "13911001008"), ("胡军", "13911001009"),
    ("高远", "13911001010"), ("刘洋", "13911001011"), ("何芳", "13911001012"),
]

STATUSES = ["pending", "accepted", "processing", "pending_confirm", "confirmed", "cancelled"]
EXPECTS = ["立即上门", "今天 09:00-12:00", "今天 14:00-18:00", "立即上门"]
MANAGERS = [1, 2]


def fmt(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def make_signature() -> str:
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


def make_photo() -> str:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (800, 560), (235, 241, 250))
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 760, 520], outline=(120, 145, 185), width=4)
    d.rectangle([90, 90, 380, 300], fill=(210, 222, 240))
    d.text((110, 120), "DEMO PHOTO", fill=(60, 80, 110))
    d.ellipse([520, 160, 680, 320], fill=(240, 150, 110))
    path = UPLOAD / "demo-photo.jpg"
    img.save(path, quality=85)
    return "/uploads/202611/demo-photo.jpg"


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    fault_types = [r["name"] for r in conn.execute("SELECT name FROM fault_types WHERE active=1 ORDER BY sort, id")]
    rooms = [dict(r) for r in conn.execute("SELECT * FROM rooms WHERE active=1 ORDER BY id")]
    staff = [dict(r) for r in conn.execute("SELECT * FROM staff WHERE active=1 ORDER BY id")]
    engineers = [s for s in staff if "engineer" in (s["roles"] or s["role"]).split(",") and s["role"] != "admin"]
    materials = [dict(r) for r in conn.execute("SELECT * FROM materials WHERE active=1 AND stock > 2 ORDER BY id")]

    signatures = make_signature()
    photo = make_photo()

    # 每天编号序列
    seq = {}
    for r in conn.execute("SELECT code FROM tickets"):
        code = r["code"]
        if code.startswith("WO") and len(code) == 13:
            day, n = code[2:10], code[10:]
            if n.isdigit():
                seq[day] = max(seq.get(day, 0), int(n))

    now = datetime.now()
    total = 0
    mat_idx = 0
    for type_idx, fault_type in enumerate(fault_types):
        for i in range(3):
            status = STATUSES[(type_idx * 3 + i) % len(STATUSES)]
            room = rooms[(type_idx * 3 + i) % len(rooms)]
            contact_name, contact_phone = CONTACTS[(type_idx * 3 + i) % len(CONTACTS)]

            if status == "pending":
                created = now - timedelta(minutes=random.choice([4, 8, 12, 18, 25, 38]))
            elif status == "accepted":
                created = now - timedelta(minutes=random.randint(35, 50))
            elif status == "processing":
                created = now - timedelta(hours=random.randint(1, 2), minutes=random.randint(0, 40))
            else:
                created = now - timedelta(days=random.randint(0, 6), hours=random.randint(1, 6),
                                          minutes=random.randint(0, 59))
            day = created.strftime("%Y%m%d")
            seq[day] = seq.get(day, 0) + 1
            code = f"WO{day}{seq[day]:03d}"
            location = f"{room['building']}{room['floor']}层 {room['room_no']}室"
            if room["name"]:
                location += f"（{room['name']}）"
            device = DEVICES.get(fault_type, ["设备"])[(type_idx + i) % len(DEVICES.get(fault_type, ["设备"]))]
            expect_time = EXPECTS[(type_idx + i) % len(EXPECTS)]
            source = "phone" if (type_idx + i) % 7 == 0 else "qr"

            assignee = engineers[(type_idx + i) % len(engineers)] if status != "pending" and status != "cancelled" else None
            dispatcher = MANAGERS[(type_idx + i) % len(MANAGERS)] if assignee else None
            accepted = created + timedelta(minutes=random.randint(8, 35)) if assignee else None
            started = accepted + timedelta(minutes=random.randint(5, 25)) if status in ("processing", "pending_confirm", "confirmed") else None
            finished = started + timedelta(minutes=random.randint(40, 160)) if status in ("pending_confirm", "confirmed") else None
            confirmed = finished + timedelta(minutes=random.randint(20, 90)) if status == "confirmed" else None
            signature = signatures if status == "confirmed" else ""
            rating = random.choice([4, 5, 5]) if status == "confirmed" else None
            comment = random.choice(["处理及时，谢谢", "师傅很专业", "问题已解决", "响应很快"]) if status == "confirmed" else ""
            cause = CAUSES.get(fault_type, "已排查定位") if finished else ""
            note = f"{cause}，测试正常" if finished else ""
            photos = json.dumps([photo]) if (type_idx + i) % 9 == 0 else "[]"
            if status == "cancelled":
                note = "报障人电话撤销：问题自行恢复"

            last_ts = confirmed or finished or started or accepted or created
            cur = conn.execute(
                """INSERT INTO tickets(code, room_id, location, device, fault_type, description,
                       contact_name, contact_phone, expect_time, source, photos, status,
                       dispatcher_id, assignee_id, accepted_at, started_at, finished_at,
                       confirm_at, rating, confirm_comment, signature, fault_cause, solve_note,
                       created_at, updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    code, room["id"], location, device, fault_type, DESCRIPTIONS.get(fault_type, ""),
                    contact_name, contact_phone, expect_time, source, photos, status,
                    dispatcher, assignee["id"] if assignee else None,
                    fmt(accepted) if accepted else None,
                    fmt(started) if started else None,
                    fmt(finished) if finished else None,
                    fmt(confirmed) if confirmed else None,
                    rating, comment, signature, cause, note,
                    fmt(created), fmt(last_ts),
                ),
            )
            tid = cur.lastrowid
            logs = [("报障人 " + contact_name, "提交报障", DESCRIPTIONS.get(fault_type, ""), created)]
            if assignee:
                logs.append(("系统管理员" if dispatcher == 1 else "王调度", "受理工单", "", accepted))
                logs.append(("系统管理员" if dispatcher == 1 else "王调度", "指派处理人", assignee["name"], accepted))
            if started:
                logs.append((f'{assignee["name"]}（运维工程师）', "开始上门处理", "", started))
            if finished:
                logs.append((f'{assignee["name"]}（运维工程师）', "提交处理结果", note, finished))
            if confirmed:
                logs.append(("报障人 " + contact_name, "签字确认完成", f"满意度 {rating} 星", confirmed))
            if status == "cancelled":
                logs.append(("报障人 " + contact_name, "撤销报障", note, created + timedelta(minutes=12)))

            for actor, action, log_note, ts in logs:
                conn.execute(
                    "INSERT INTO ticket_logs(ticket_id, actor, action, note, created_at)"
                    " VALUES(?,?,?,?,?)",
                    (tid, actor, action, log_note, fmt(ts)),
                )

            # 部分工单登记领用物资（含库存流水）
            if finished and materials and (type_idx + i) % 4 == 0:
                mat = materials[mat_idx % len(materials)]
                mat_idx += 1
                qty = 1
                if mat["stock"] >= qty:
                    before = mat["stock"]
                    after = before - qty
                    conn.execute("UPDATE materials SET stock=? WHERE id=?", (after, mat["id"]))
                    conn.execute(
                        "INSERT INTO stock_logs(material_id, kind, qty, before_stock, after_stock,"
                        " ticket_id, operator, note, created_at) VALUES(?,'out',?,?,?,?,?,?,?)",
                        (mat["id"], qty, before, after, tid, assignee["name"],
                         f"工单 {code} 维修领用", fmt(finished)),
                    )
                    conn.execute(
                        "INSERT INTO ticket_materials(ticket_id, material_id, material_name, spec,"
                        " unit, qty, created_at) VALUES(?,?,?,?,?,?,?)",
                        (tid, mat["id"], mat["name"], mat["spec"], mat["unit"], qty, fmt(finished)),
                    )
            total += 1

    conn.commit()
    print(f"已生成 {total} 条工单")
    print("按状态：", dict(Counter(r[0] for r in conn.execute("SELECT status FROM tickets"))))
    print("按类型：", dict(Counter(r[0] for r in conn.execute("SELECT fault_type FROM tickets"))))
    conn.close()


if __name__ == "__main__":
    sys.exit(main())
