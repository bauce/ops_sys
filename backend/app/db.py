"""数据库连接与初始化（SQLite）。"""
import hashlib
import os
import sqlite3
from datetime import datetime
from pathlib import Path


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000
    ).hex()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = os.environ.get("OPS_DB", str(DATA_DIR / "ops.db"))

DEFAULT_FAULT_TYPES = [
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

DEFAULT_DEVICES = [
    "台式电脑",
    "笔记本电脑",
    "打印机",
    "复印机",
    "投影仪",
    "显示器",
    "网络交换机",
    "无线 AP",
    "路由器",
    "电话机",
    "门禁设备",
    "监控摄像头",
    "服务器",
    "UPS 电源",
]

DEFAULT_CATEGORIES = [
    # (名称, 编号前缀, 排序)
    ("线材", "XC", 1),
    ("设备", "SB", 2),
    ("其它", "QT", 3),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS staff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'dispatcher', 'engineer')),
    roles TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    email TEXT DEFAULT '',
    pwd_hash TEXT NOT NULL,
    pwd_salt TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    staff_id INTEGER NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reporters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash TEXT NOT NULL UNIQUE,
    name TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    last_seen TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rooms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building TEXT NOT NULL,
    floor TEXT NOT NULL,
    room_no TEXT NOT NULL,
    name TEXT DEFAULT '',
    qr_code TEXT NOT NULL UNIQUE,
    note TEXT DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    room_id INTEGER REFERENCES rooms(id),
    location TEXT NOT NULL,
    device TEXT NOT NULL,
    fault_type TEXT NOT NULL,
    description TEXT DEFAULT '',
    contact_name TEXT NOT NULL,
    contact_phone TEXT NOT NULL,
    expect_time TEXT DEFAULT '',
    source TEXT DEFAULT 'qr',
    photos TEXT DEFAULT '[]',
    reporter_id INTEGER REFERENCES reporters(id),
    status TEXT NOT NULL DEFAULT 'pending',
    dispatcher_id INTEGER REFERENCES staff(id),
    assignee_id INTEGER REFERENCES staff(id),
    accepted_at TEXT,
    started_at TEXT,
    finished_at TEXT,
    confirm_at TEXT,
    rating INTEGER,
    confirm_comment TEXT DEFAULT '',
    signature TEXT DEFAULT '',
    fault_cause TEXT DEFAULT '',
    solve_note TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_reporter ON tickets(reporter_id);
CREATE INDEX IF NOT EXISTS idx_tickets_room ON tickets(room_id);
CREATE INDEX IF NOT EXISTS idx_tickets_assignee ON tickets(assignee_id);
CREATE INDEX IF NOT EXISTS idx_tickets_phone ON tickets(contact_phone);

CREATE TABLE IF NOT EXISTS ticket_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_logs_ticket ON ticket_logs(ticket_id);

CREATE TABLE IF NOT EXISTS material_categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    prefix TEXT NOT NULL UNIQUE,
    sort INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT DEFAULT '',
    category_id INTEGER REFERENCES material_categories(id),
    spec TEXT DEFAULT '',
    unit TEXT DEFAULT '个',
    stock REAL NOT NULL DEFAULT 0,
    warn_stock REAL NOT NULL DEFAULT 0,
    location TEXT DEFAULT '',
    unit_price REAL DEFAULT 0,
    remark TEXT DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS stock_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL REFERENCES materials(id),
    kind TEXT NOT NULL CHECK (kind IN ('in', 'out', 'adjust')),
    qty REAL NOT NULL,
    before_stock REAL NOT NULL,
    after_stock REAL NOT NULL,
    ticket_id INTEGER REFERENCES tickets(id),
    operator TEXT NOT NULL,
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_stock_material ON stock_logs(material_id);

CREATE TABLE IF NOT EXISTS ticket_materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    material_id INTEGER NOT NULL REFERENCES materials(id),
    material_name TEXT NOT NULL,
    spec TEXT DEFAULT '',
    unit TEXT DEFAULT '',
    qty REAL NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_tm_ticket ON ticket_materials(ticket_id);

CREATE TABLE IF NOT EXISTS fault_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    sort INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS devices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    sort INTEGER NOT NULL DEFAULT 0,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS transfers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    from_staff_id INTEGER NOT NULL REFERENCES staff(id),
    to_staff_id INTEGER NOT NULL REFERENCES staff(id),
    status TEXT NOT NULL DEFAULT 'pending',
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_transfers_ticket ON transfers(ticket_id);
CREATE INDEX IF NOT EXISTS idx_transfers_to ON transfers(to_staff_id, status);

CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT DEFAULT '',
    brand_model TEXT DEFAULT '',
    serial_no TEXT DEFAULT '',
    room_id INTEGER REFERENCES rooms(id),
    location TEXT DEFAULT '',
    rack_position TEXT DEFAULT '',
    install_date TEXT DEFAULT '',
    status TEXT DEFAULT '在用',
    network TEXT DEFAULT '',
    mgmt_address TEXT DEFAULT '',
    mgmt_user TEXT DEFAULT '',
    mgmt_password TEXT DEFAULT '',
    mgmt_port TEXT DEFAULT '',
    owner TEXT DEFAULT '',
    vendor TEXT DEFAULT '',
    warranty_until TEXT DEFAULT '',
    note TEXT DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assets_category ON assets(category);
CREATE INDEX IF NOT EXISTS idx_assets_room ON assets(room_id);

CREATE TABLE IF NOT EXISTS duty_weeks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start TEXT NOT NULL UNIQUE,
    staff_ids TEXT NOT NULL DEFAULT '[]',
    note TEXT DEFAULT '',
    created_by INTEGER REFERENCES staff(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS duty_adjustments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start TEXT NOT NULL,
    adjust_date TEXT NOT NULL,
    start_time TEXT NOT NULL,
    end_time TEXT NOT NULL,
    staff_ids TEXT NOT NULL DEFAULT '[]',
    note TEXT DEFAULT '',
    created_by INTEGER REFERENCES staff(id),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_adjust_week ON duty_adjustments(week_start);
CREATE INDEX IF NOT EXISTS idx_adjust_date ON duty_adjustments(adjust_date);

CREATE TABLE IF NOT EXISTS custom_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    permissions TEXT DEFAULT '',
    active INTEGER DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def get_db():
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def next_material_code(conn: sqlite3.Connection, prefix: str) -> str:
    """按分类前缀生成下一个物资编号，如 XC-007。"""
    rows = conn.execute(
        "SELECT code FROM materials WHERE code LIKE ?", (prefix + "-%",)
    ).fetchall()
    max_no = 0
    for row in rows:
        tail = row["code"].split("-", 1)[-1]
        if tail.isdigit():
            max_no = max(max_no, int(tail))
    return f"{prefix}-{max_no + 1:03d}"


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, decl: str) -> None:
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})")]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


def _seed_dict(conn: sqlite3.Connection, table: str, names) -> None:
    if conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] > 0:
        return
    for i, name in enumerate(names, start=1):
        conn.execute(
            f"INSERT INTO {table}(name, sort, active) VALUES(?,?,1)", (name, i)
        )


def _seed_categories(conn: sqlite3.Connection) -> None:
    if conn.execute("SELECT COUNT(*) FROM material_categories").fetchone()[0] > 0:
        return
    for name, prefix, sort in DEFAULT_CATEGORIES:
        conn.execute(
            "INSERT INTO material_categories(name,prefix,sort,active) VALUES(?,?,?,1)",
            (name, prefix, sort),
        )


def _ensure_usage_material(conn: sqlite3.Connection) -> None:
    """确保「散热硅脂」这类按次数计量的物资存在。"""
    if conn.execute("SELECT 1 FROM materials WHERE name = '散热硅脂'").fetchone():
        return
    cat = conn.execute(
        "SELECT * FROM material_categories WHERE name = '其它' ORDER BY id LIMIT 1"
    ).fetchone()
    if not cat:
        return
    code = next_material_code(conn, cat["prefix"])
    ts = now()
    conn.execute(
        """INSERT INTO materials(code,name,category,category_id,spec,unit,measure_mode,
               stock,warn_stock,location,unit_price,remark,active,created_at,updated_at)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)""",
        (code, "散热硅脂", cat["name"], cat["id"], "导热硅脂 1g/次", "次", "usage",
         20, 5, "机房A柜", 0, "按使用次数计量，不按支/盒", ts, ts),
    )
    conn.commit()


def migrate(conn: sqlite3.Connection) -> None:
    """兼容旧数据库：补充字段、字典与分类，并迁移物资编号。"""
    _ensure_column(conn, "tickets", "expect_time", "TEXT DEFAULT ''")
    _ensure_column(conn, "tickets", "signature", "TEXT DEFAULT ''")
    _ensure_column(conn, "materials", "category_id", "INTEGER")
    _ensure_column(conn, "staff", "email", "TEXT DEFAULT ''")
    _ensure_column(conn, "staff", "roles", "TEXT DEFAULT ''")
    _ensure_column(conn, "staff", "custom_role_ids", "TEXT DEFAULT ''")
    _ensure_column(conn, "tickets", "source", "TEXT DEFAULT 'qr'")
    _ensure_column(conn, "tickets", "photos", "TEXT DEFAULT '[]'")
    _ensure_column(conn, "rooms", "importance", "TEXT DEFAULT '普通'")
    _ensure_column(conn, "materials", "measure_mode", "TEXT DEFAULT 'quantity'")
    _ensure_usage_material(conn)
    if conn.execute("SELECT COUNT(*) FROM custom_roles").fetchone()[0] == 0:
        conn.execute(
            "INSERT INTO custom_roles(name,permissions,active,created_at) VALUES(?,?,1,?)",
            (
                "运维组长",
                "ticket.view,ticket.dispatch,material.view,material.manage,material.approve,"
                "asset.view,asset.manage,asset.password,room.manage,duty.manage,report.view",
                now(),
            ),
        )
    conn.execute("UPDATE staff SET roles = role WHERE roles IS NULL OR roles = ''")
    for key, value in (("sla_pending_minutes", "15"), ("sla_accept_minutes", "60"),
                       ("sla_processing_hours", "4")):
        conn.execute(
            "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (key, value)
        )
    for key in ("smtp_host", "smtp_port", "smtp_secure", "smtp_user",
                "smtp_password", "mail_from", "mail_from_name"):
        conn.execute(
            "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (key, "")
        )
    conn.execute(
        "INSERT OR IGNORE INTO settings(key,value) VALUES('mail_enabled','0')"
    )
    conn.execute(
        "UPDATE settings SET value = '587' WHERE key = 'smtp_port' AND value = ''"
    )
    conn.execute(
        "UPDATE settings SET value = 'starttls' WHERE key = 'smtp_secure' AND value = ''"
    )

    conn.execute("DROP TABLE IF EXISTS duty_shifts")
    _seed_categories(conn)
    _seed_dict(conn, "fault_types", DEFAULT_FAULT_TYPES)
    _seed_dict(conn, "devices", DEFAULT_DEVICES)

    flag = conn.execute(
        "SELECT value FROM settings WHERE key = 'material_codes_v2'"
    ).fetchone()
    if flag:
        conn.commit()
        return

    # 旧分类归并到新的三类
    legacy_map = {
        "线材": "线材",
        "设备": "设备",
        "存储": "设备",
        "网络设备": "设备",
        "外设": "设备",
        "配件": "其它",
        "其它": "其它",
        "其他": "其它",
    }
    cats = {
        r["name"]: r for r in conn.execute("SELECT * FROM material_categories")
    }
    rows = conn.execute("SELECT id, code, category FROM materials ORDER BY id").fetchall()
    # 先把编号换成临时值，避免唯一索引冲突
    conn.execute("UPDATE materials SET code = 'TMP-' || id")
    seq = {name: 0 for name in cats}
    for row in rows:
        target = legacy_map.get((row["category"] or "").strip(), "其它")
        cat = cats.get(target) or cats.get("其它")
        if not cat:
            continue
        seq[cat["name"]] = seq.get(cat["name"], 0) + 1
        code = f"{cat['prefix']}-{seq[cat['name']]:03d}"
        conn.execute(
            "UPDATE materials SET category = ?, category_id = ?, code = ? WHERE id = ?",
            (cat["name"], cat["id"], code, row["id"]),
        )

    # 没有对应分类的历史物资统一放入“其它”
    other = conn.execute(
        "SELECT id FROM material_categories WHERE name = '其它'"
    ).fetchone()
    if other:
        conn.execute(
            "UPDATE materials SET category = '其它', category_id = ? WHERE category_id IS NULL",
            (other["id"],),
        )
    conn.execute(
        "INSERT OR REPLACE INTO settings(key,value) VALUES('material_codes_v2','1')"
    )
    conn.commit()


def seed(conn: sqlite3.Connection) -> None:
    """首次启动写入演示数据。"""
    if conn.execute("SELECT COUNT(*) FROM staff").fetchone()[0] == 0:
        users = [
            ("admin", "系统管理员", "admin", "13800000000", "admin123"),
            ("dispatcher", "王调度", "dispatcher", "13800000001", "dispatch123"),
            ("zhangsan", "张工", "engineer", "13800000002", "eng123"),
            ("lisi", "李工", "engineer", "13800000003", "eng123"),
        ]
        for username, name, role, phone, pwd in users:
            salt = os.urandom(16).hex()
            conn.execute(
                "INSERT INTO staff(username,name,role,roles,phone,email,pwd_hash,pwd_salt,"
                "active,created_at) VALUES(?,?,?,?,?,?,?,?,1,?)",
                (username, name, role, role, phone, "", hash_password(pwd, salt), salt, now()),
            )

    if conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0] == 0:
        rooms = [
            ("1号楼", "1", "101", "一楼大厅", "前台网络接口"),
            ("1号楼", "1", "105", "接待室", ""),
            ("1号楼", "2", "201", "综合办公室", ""),
            ("1号楼", "2", "203", "财务室", ""),
            ("1号楼", "3", "301", "会议室A", "投影、视频会议设备"),
            ("1号楼", "3", "305", "会议室B", ""),
            ("2号楼", "1", "102", "机房", "核心设备区"),
            ("2号楼", "2", "208", "档案室", ""),
        ]
        for building, floor, room_no, name, note in rooms:
            conn.execute(
                "INSERT INTO rooms(building,floor,room_no,name,qr_code,note,active,created_at)"
                " VALUES(?,?,?,?,?,?,1,?)",
                (building, floor, room_no, name, os.urandom(5).hex(), note, now()),
            )

    _seed_categories(conn)
    _seed_dict(conn, "fault_types", DEFAULT_FAULT_TYPES)
    _seed_dict(conn, "devices", DEFAULT_DEVICES)

    if conn.execute("SELECT COUNT(*) FROM materials").fetchone()[0] == 0:
        cats = {
            r["name"]: r
            for r in conn.execute("SELECT * FROM material_categories")
        }
        mats = [
            ("六类网线", "线材", "超六类 非屏蔽 305米/箱", "箱", 12, 3, "机房A柜", 680),
            ("水晶头 RJ45", "线材", "六类 100个/盒", "盒", 8, 2, "机房A柜", 65),
            ("光纤跳线", "线材", "LC-LC 3米 单模", "根", 20, 5, "机房A柜", 25),
            ("HDMI 线", "线材", "2米 2.0版", "根", 15, 5, "仓库货架3", 30),
            ("机械硬盘", "设备", "希捷 4TB SATA", "块", 6, 2, "机房B柜", 520),
            ("固态硬盘", "设备", "三星 500G NVMe", "块", 10, 3, "机房B柜", 320),
            ("内存条", "设备", "DDR4 16G 3200", "条", 15, 5, "机房B柜", 260),
            ("无线键鼠套装", "设备", "USB 接收器", "套", 9, 3, "仓库货架3", 95),
            ("无线路由器", "设备", "千兆双频", "台", 4, 2, "仓库货架2", 240),
            ("无线AP", "设备", "吸顶式 千兆", "台", 6, 2, "仓库货架2", 380),
            ("千兆交换机", "设备", "8口 非网管", "台", 3, 1, "仓库货架2", 190),
            ("电源适配器", "其它", "19V 3.42A 笔记本", "个", 10, 3, "仓库货架1", 85),
            ("插排", "其它", "六位 3米", "个", 12, 4, "仓库货架1", 45),
        ]
        for name, cat_name, spec, unit, stock, warn, loc, price in mats:
            cat = cats.get(cat_name) or cats.get("其它")
            code = next_material_code(conn, cat["prefix"])
            conn.execute(
                "INSERT INTO materials(code,name,category,category_id,spec,unit,stock,"
                "warn_stock,location,unit_price,remark,active,created_at,updated_at)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,'',1,?,?)",
                (
                    code, name, cat["name"], cat["id"], spec, unit, stock, warn, loc,
                    price, now(), now(),
                ),
            )

    if conn.execute("SELECT COUNT(*) FROM assets").fetchone()[0] == 0:
        from .crypto import encrypt

        rooms_by_no = {
            r["room_no"]: r["id"]
            for r in conn.execute("SELECT id, room_no FROM rooms")
        }
        demo_assets = [
            ("ZC-0001", "核心交换机", "网络设备", "华为 S5735-L24T4X", "SN20240301001",
             "102", "A01 机柜 U12", "2024-03-15", "在用",
             "管理 VLAN 10 / 192.168.10.1", "https://192.168.10.1", "admin", "Huawei@2024",
             "443", "张工", "华为", "2027-03-14", "核心网络设备，双电源"),
            ("ZC-0002", "接入交换机", "网络设备", "华为 S5720-28X", "SN20230908002",
             "102", "A02 机柜 U8", "2023-09-08", "在用",
             "VLAN 20 / 192.168.20.2", "https://192.168.20.2", "admin", "Switch@2023",
             "443", "李工", "华为", "2026-09-07", "二楼办公区接入"),
            ("ZC-0003", "下一代防火墙", "安全设备", "深信服 AF-1000", "SN20240115003",
             "102", "A01 机柜 U20", "2024-01-15", "在用",
             "外网出口 / 192.168.1.254", "https://192.168.1.254", "admin", "AF@2024#01",
             "443", "张工", "深信服", "2027-01-14", "互联网出口安全防护"),
            ("ZC-0004", "业务服务器", "服务器", "戴尔 R750", "SN20220620004",
             "102", "B01 机柜 U06", "2022-06-20", "在用",
             "业务网段 10.10.1.10", "https://10.10.1.10", "root", "Dell@2022",
             "8443", "王五", "戴尔", "2025-06-19", "承载 OA 与工单系统"),
            ("ZC-0005", "文件服务器", "服务器", "联想 SR650", "SN20211105005",
             "102", "B01 机柜 U10", "2021-11-05", "在用",
             "业务网段 10.10.1.20", "https://10.10.1.20", "administrator", "Lenovo@2021",
             "8443", "王五", "联想", "2024-11-04", "部门共享文件"),
            ("ZC-0006", "网络存储", "存储设备", "群晖 RS1221+", "SN20230217006",
             "102", "B02 机柜 U14", "2023-02-17", "在用",
             "存储网段 10.10.2.30", "https://10.10.2.30:5001", "admin", "Syno@2023",
             "5001", "李工", "群晖", "2026-02-16", "备份与归档"),
            ("ZC-0007", "会议室一体机", "终端设备", "MAXHUB V6", "SN20240506007",
             "301", "壁挂", "2024-05-06", "在用",
             "无线投屏 / 10.10.5.31", "https://10.10.5.31", "admin", "Maxhub@2024",
             "443", "赵六", "MAXHUB", "2027-05-05", "301 会议室"),
            ("ZC-0008", "激光打印机", "打印设备", "惠普 M405dn", "SN20220812008",
             "203", "财务室打印区", "2022-08-12", "维修",
             "打印网段 10.10.6.23", "http://10.10.6.23", "admin", "HP@2022",
             "80", "赵六", "惠普", "2025-08-11", "财务专用"),
        ]
        for (code, name, cat, model, sn, room_no, rack, install, status,
             network, addr, user, pwd, port, owner, vendor, warranty, note) in demo_assets:
            room_id = rooms_by_no.get(room_no)
            location = ""
            if room_id:
                room = conn.execute(
                    "SELECT * FROM rooms WHERE id = ?", (room_id,)
                ).fetchone()
                location = f"{room['building']}{room['floor']}层 {room['room_no']}室"
                if room["name"]:
                    location += f"（{room['name']}）"
            conn.execute(
                """INSERT INTO assets(code,name,category,brand_model,serial_no,room_id,
                       location,rack_position,install_date,status,network,mgmt_address,
                       mgmt_user,mgmt_password,mgmt_port,owner,vendor,warranty_until,
                       note,active,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1,?,?)""",
                (
                    code, name, cat, model, sn, room_id, location, rack, install,
                    status, network, addr, user, encrypt(conn, pwd), port, owner,
                    vendor, warranty, note, now(), now(),
                ),
            )

    conn.execute(
        "INSERT OR IGNORE INTO settings(key,value) VALUES('public_base_url','')"
    )
    conn.commit()


def init_db() -> None:
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        seed(conn)
        migrate(conn)
        conn.commit()
    finally:
        conn.close()
