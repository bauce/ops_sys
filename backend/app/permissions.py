"""角色权限：内置角色 + 可自由配置的自定义角色。"""

PERMISSION_CATALOG = [
    ("工单", [
        ("ticket.view", "查看工单"),
        ("ticket.dispatch", "受理 / 派单 / 改派"),
        ("ticket.handle", "上门处理"),
    ]),
    ("物资", [
        ("material.view", "查看物资"),
        ("material.manage", "出入库 / 台账维护"),
        ("material.approve", "物资核审"),
    ]),
    ("设备", [
        ("asset.view", "查看设备"),
        ("asset.manage", "维护设备台账"),
        ("asset.password", "查看设备密码"),
    ]),
    ("管理", [
        ("room.manage", "房间与二维码"),
        ("duty.manage", "值班排班"),
        ("report.view", "运维报表"),
        ("user.manage", "账号与角色管理"),
    ]),
]

ALL_PERMISSIONS = {key for _, items in PERMISSION_CATALOG for key, _ in items}

BUILTIN_PERMISSIONS = {
    "admin": set(ALL_PERMISSIONS),
    "dispatcher": {
        "ticket.view", "ticket.dispatch",
        "material.view", "material.manage", "material.approve",
        "asset.view", "asset.manage",
        "room.manage", "duty.manage", "report.view", "user.manage",
    },
    "engineer": {"ticket.view", "ticket.handle", "material.view", "asset.view"},
    "duty": {"ticket.view", "ticket.dispatch"},
}

PERMISSION_NAMES = {key: name for _, items in PERMISSION_CATALOG for key, name in items}


def parse_ids(value) -> list:
    out = []
    for part in str(value or "").replace("，", ",").split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return list(dict.fromkeys(out))


def split_perms(value) -> list:
    return [p.strip() for p in str(value or "").split(",") if p.strip() in ALL_PERMISSIONS]


def custom_roles_for(conn, ids):
    ids = [int(i) for i in ids if str(i).isdigit()]
    if not ids:
        return []
    marks = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT id, name, permissions FROM custom_roles WHERE id IN ({marks}) AND active = 1",
        ids,
    ).fetchall()
    by_id = {r["id"]: dict(r) for r in rows}
    result = []
    for rid in ids:
        row = by_id.get(rid)
        if row:
            row["permissions"] = split_perms(row["permissions"])
            result.append(row)
    return result


def resolve_permissions(conn, builtin_roles, custom_role_ids, on_duty=False):
    perms = set()
    for role in builtin_roles or []:
        perms |= BUILTIN_PERMISSIONS.get(role, set())
    custom = custom_roles_for(conn, parse_ids(custom_role_ids))
    for role in custom:
        perms |= set(role["permissions"])
    if on_duty:
        perms |= {"ticket.view", "ticket.dispatch"}
    return sorted(perms), custom
