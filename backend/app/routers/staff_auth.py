"""运维人员登录、账号管理与系统设置（含邮件配置）。"""
import os
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from .. import mailer
from ..db import get_db, now
from ..schemas import EmailConfigIn, EmailTestIn, LoginIn, StaffIn
from ..test_mode import is_test_mode
from ..permissions import (
    ALL_PERMISSIONS,
    PERMISSION_CATALOG,
    PERMISSION_NAMES,
    custom_roles_for,
    parse_ids,
    split_perms,
)
from ..security import (
    COOKIE_STAFF,
    apply_duty_role,
    ROLE_NAMES,
    create_session,
    current_staff,
    has_perm,
    has_role,
    hash_password,
    parse_roles,
    require_permissions,
    require_roles,
    sha256,
    verify_password,
)

router = APIRouter(prefix="/api/staff", tags=["staff"])

MANAGER_ROLES = ("admin", "dispatcher")


@router.post("/login")
def login(
    payload: LoginIn,
    response: Response,
    conn: sqlite3.Connection = Depends(get_db),
):
    row = conn.execute(
        "SELECT * FROM staff WHERE username = ?", (payload.username.strip(),)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=400, detail="账号或密码错误")
    if not row["active"]:
        raise HTTPException(status_code=403, detail="账号已停用")
    # 测试环境：跳过密码校验，便于快速切换角色
    if not is_test_mode() and not verify_password(payload.password, row["pwd_salt"], row["pwd_hash"]):
        raise HTTPException(status_code=400, detail="账号或密码错误")
    create_session(conn, row["id"], response)
    data = dict(row)
    data["roles"] = parse_roles(data["roles"], data["role"])
    apply_duty_role(conn, data)
    return {
        "id": data["id"],
        "username": data["username"],
        "name": data["name"],
        "role": data["role"],
        "roles": data["roles"],
        "on_duty": data["on_duty"],
        "role_text": "、".join(
            [ROLE_NAMES.get(r, r) for r in data["roles"]]
            + [c["name"] for c in data.get("custom_roles", [])]
        ),
        "email": data["email"] or "",
        "permissions": data["permissions"],
        "custom_roles": data["custom_roles"],
    }


@router.get("/login-options")
def login_options(conn: sqlite3.Connection = Depends(get_db)):
    """测试环境返回可免密登录的账号列表；正式环境始终为空。"""
    if not is_test_mode():
        return {"test_mode": False, "accounts": []}
    rows = conn.execute(
        "SELECT id, username, name, role, roles, custom_role_ids FROM staff WHERE active = 1"
        " ORDER BY CASE role WHEN 'admin' THEN 0 WHEN 'dispatcher' THEN 1 ELSE 2 END, id"
    ).fetchall()
    accounts = []
    for row in rows:
        roles = parse_roles(row["roles"], row["role"])
        custom = custom_roles_for(conn, parse_ids(row["custom_role_ids"]))
        accounts.append({
            "username": row["username"],
            "name": row["name"],
            "roles": roles,
            "role_text": "、".join(
                [ROLE_NAMES.get(r, r) for r in roles] + [c["name"] for c in custom]
            ),
        })
    return {"test_mode": True, "accounts": accounts}


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    token = request.cookies.get(COOKIE_STAFF)
    if token:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (sha256(token),))
        conn.commit()
    response.delete_cookie(COOKIE_STAFF, path="/")
    return {"ok": True}


@router.get("/me")
def me(staff: dict = Depends(current_staff)):
    roles = staff.get("roles") or parse_roles("", staff["role"])
    return {
        "id": staff["id"],
        "username": staff["username"],
        "name": staff["name"],
        "role": staff["role"],
        "roles": roles,
        "on_duty": staff.get("on_duty", False),
        "role_text": "、".join(
            [ROLE_NAMES.get(r, r) for r in roles]
            + [c["name"] for c in staff.get("custom_roles", [])]
        ),
        "phone": staff["phone"],
        "email": staff["email"] or "",
        "permissions": staff.get("permissions", []),
        "custom_roles": staff.get("custom_roles", []),
    }


@router.get("/users")
def list_users(
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_permissions("user.manage", "ticket.dispatch", "ticket.handle", "ticket.view")),
):
    rows = conn.execute(
        "SELECT id, username, name, role, roles, custom_role_ids, phone, email, active, created_at FROM staff"
        " ORDER BY CASE role WHEN 'admin' THEN 0 WHEN 'dispatcher' THEN 1 ELSE 2 END, id"
    ).fetchall()
    items = []
    for r in rows:
        roles = parse_roles(r["roles"], r["role"])
        custom = custom_roles_for(conn, parse_ids(r["custom_role_ids"]))
        items.append({
            **dict(r),
            "roles": roles,
            "role_ids": [c["id"] for c in custom],
            "custom_roles": custom,
            "role_text": "、".join(
                [ROLE_NAMES.get(x, x) for x in roles] + [c["name"] for c in custom]
            ),
        })
    return {"items": items}


@router.post("/users")
def create_user(
    payload: StaffIn,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_permissions("user.manage")),
):
    roles = payload.roles or [payload.role]
    roles = [r for r in dict.fromkeys(roles) if r in ("admin", "dispatcher", "engineer")]
    if not roles:
        raise HTTPException(status_code=400, detail="请至少选择一个角色")
    if not has_role(staff, "admin") and set(roles) - {"engineer"}:
        raise HTTPException(status_code=403, detail="非管理员只能添加运维工程师账号")
    if conn.execute(
        "SELECT 1 FROM staff WHERE username = ?", (payload.username.strip(),)
    ).fetchone():
        raise HTTPException(status_code=400, detail="登录名已存在")
    primary = "admin" if "admin" in roles else ("dispatcher" if "dispatcher" in roles else "engineer")
    salt = os.urandom(16).hex()
    role_ids = []
    if payload.role_ids:
        if not has_role(staff, "admin"):
            raise HTTPException(status_code=403, detail="只有管理员可以分配自定义角色")
        role_ids = [r["id"] for r in custom_roles_for(conn, payload.role_ids)]
    conn.execute(
        "INSERT INTO staff(username,name,role,roles,custom_role_ids,phone,email,pwd_hash,pwd_salt,active,created_at)"
        " VALUES(?,?,?,?,?,?,?,?,?,1,?)",
        (
            payload.username.strip(), payload.name.strip(), primary, ",".join(roles),
            ",".join(str(x) for x in role_ids),
            payload.phone.strip(), (payload.email or "").strip(),
            hash_password(payload.password, salt), salt, now(),
        ),
    )
    conn.commit()
    return {"ok": True}


def _check_manage_permission(staff: dict, target) -> None:
    if has_role(staff, "admin"):
        return
    if has_perm(staff, "user.manage"):
        target_roles = parse_roles(target["roles"], target["role"])
        if set(target_roles) - {"engineer"}:
            raise HTTPException(status_code=403, detail="只能维护运维工程师账号")
        return
    raise HTTPException(status_code=403, detail="没有操作权限")


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    payload: dict,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_permissions("user.manage")),
):
    row = conn.execute("SELECT * FROM staff WHERE id = ?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="用户不存在")
    _check_manage_permission(staff, row)

    if user_id == staff["id"]:
        if payload.get("active") in (0, False):
            raise HTTPException(status_code=400, detail="不能停用当前登录账号")
        if "roles" in payload or "role" in payload:
            raw = payload.get("roles") or [payload.get("role")]
            if "admin" not in raw:
                raise HTTPException(status_code=400, detail="不能移除自己的管理员角色")

    if "roles" in payload or "role" in payload:
        raw = payload.get("roles") or [payload.get("role")]
        roles = [r for r in dict.fromkeys(raw) if r in ("admin", "dispatcher", "engineer")]
        if not roles:
            raise HTTPException(status_code=400, detail="请至少选择一个角色")
        if not has_role(staff, "admin") and set(roles) - {"engineer"}:
            raise HTTPException(status_code=403, detail="非管理员不能修改账号角色")
        primary = "admin" if "admin" in roles else ("dispatcher" if "dispatcher" in roles else "engineer")
        payload = {**payload, "role": primary, "roles": ",".join(roles)}

    fields, values = [], []
    if "role_ids" in payload:
        if not has_role(staff, "admin"):
            raise HTTPException(status_code=403, detail="只有管理员可以分配自定义角色")
        role_ids = [r["id"] for r in custom_roles_for(conn, payload.get("role_ids") or [])]
        payload["custom_role_ids"] = ",".join(str(x) for x in role_ids)
    for key in ("name", "role", "roles", "custom_role_ids", "phone", "email", "active"):
        if key in payload:
            fields.append(f"{key} = ?")
            values.append(payload[key])
    if payload.get("password"):
        salt = os.urandom(16).hex()
        fields += ["pwd_hash = ?", "pwd_salt = ?"]
        values += [hash_password(payload["password"], salt), salt]
        conn.execute("DELETE FROM sessions WHERE staff_id = ?", (user_id,))
    if not fields:
        return {"ok": True}
    values.append(user_id)
    conn.execute(f"UPDATE staff SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    return {"ok": True}


@router.get("/settings")
def get_settings(
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(current_staff),
):
    row = conn.execute(
        "SELECT value FROM settings WHERE key = 'public_base_url'"
    ).fetchone()
    return {"public_base_url": row["value"] if row else ""}


@router.put("/settings")
def update_settings(
    payload: dict,
    conn: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_roles("admin")),
):
    url = (payload.get("public_base_url") or "").strip().rstrip("/")
    conn.execute(
        "INSERT INTO settings(key,value) VALUES('public_base_url',?)"
        " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (url,),
    )
    conn.commit()
    return {"ok": True, "public_base_url": url}


# ---------------- 邮件配置 ----------------

@router.get("/settings/email")
def get_email_settings(
    conn: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_roles("admin")),
):
    cfg = mailer.get_config(conn)
    return {
        "smtp_host": cfg["smtp_host"],
        "smtp_port": cfg["smtp_port"],
        "smtp_secure": cfg["smtp_secure"],
        "smtp_user": cfg["smtp_user"],
        "mail_from": cfg["mail_from"],
        "mail_from_name": cfg["mail_from_name"],
        "mail_enabled": 1 if cfg["enabled"] else 0,
        "password_set": bool(cfg["smtp_password"]),
    }


@router.put("/settings/email")
def update_email_settings(
    payload: EmailConfigIn,
    conn: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_roles("admin")),
):
    if payload.smtp_secure not in ("ssl", "starttls", "none"):
        raise HTTPException(status_code=400, detail="加密方式不合法")
    if payload.mail_enabled and not payload.smtp_host:
        raise HTTPException(status_code=400, detail="启用邮件通知前请填写 SMTP 服务器")
    data = {
        "smtp_host": payload.smtp_host.strip(),
        "smtp_port": str(payload.smtp_port or "587").strip(),
        "smtp_secure": payload.smtp_secure,
        "smtp_user": payload.smtp_user.strip(),
        "mail_from": payload.mail_from.strip(),
        "mail_from_name": payload.mail_from_name.strip(),
        "mail_enabled": "1" if payload.mail_enabled else "0",
    }
    if payload.smtp_password:
        data["smtp_password"] = payload.smtp_password
    for key, value in data.items():
        conn.execute(
            "INSERT INTO settings(key,value) VALUES(?,?)"
            " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
    conn.commit()
    return {"ok": True}


@router.post("/settings/email/test")
def test_email(
    payload: EmailTestIn,
    conn: sqlite3.Connection = Depends(get_db),
    admin: dict = Depends(require_roles("admin")),
):
    to = (payload.to or "").strip()
    if not to:
        raise HTTPException(status_code=400, detail="请填写接收测试邮件的邮箱")
    cfg = mailer.get_config(conn)
    if not cfg["enabled"]:
        raise HTTPException(status_code=400, detail="请先启用邮件通知并保存配置")
    ok, err = mailer.send(
        to,
        "【测试】信息化运维系统邮件配置正常",
        "<p>这是一封测试邮件，说明 SMTP 配置可用。</p>",
        "这是一封测试邮件，说明 SMTP 配置可用。",
    )
    if not ok:
        raise HTTPException(status_code=400, detail=f"发送失败：{err}")
    return {"ok": True}


@router.get("/permissions")
def permission_catalog(
    staff: dict = Depends(require_permissions("user.manage")),
):
    groups = [
        {"group": group, "items": [{"key": k, "name": n} for k, n in items]}
        for group, items in PERMISSION_CATALOG
    ]
    return {"groups": groups}


@router.get("/custom-roles")
def list_custom_roles(
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_permissions("user.manage")),
):
    rows = conn.execute(
        "SELECT * FROM custom_roles ORDER BY id"
    ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["permissions"] = split_perms(item["permissions"])
        item["permission_names"] = [PERMISSION_NAMES.get(p, p) for p in item["permissions"]]
        item["user_count"] = conn.execute(
            "SELECT COUNT(*) FROM staff WHERE active = 1 AND (',' || custom_role_ids || ',') LIKE ?",
            (f"%,{row['id']},%",),
        ).fetchone()[0]
        items.append(item)
    return {"items": items, "permissions": {
        "groups": [
            {"group": group, "items": [{"key": k, "name": n} for k, n in items]}
            for group, items in PERMISSION_CATALOG
        ]
    }}


@router.post("/custom-roles")
def create_custom_role(
    payload: dict,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles("admin")),
):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="请填写角色名称")
    if conn.execute("SELECT 1 FROM custom_roles WHERE name = ?", (name,)).fetchone():
        raise HTTPException(status_code=400, detail="角色名称已存在")
    perms = [p for p in dict.fromkeys(payload.get("permissions") or []) if p in ALL_PERMISSIONS]
    cur = conn.execute(
        "INSERT INTO custom_roles(name,permissions,active,created_at) VALUES(?,?,1,?)",
        (name, ",".join(perms), now()),
    )
    conn.commit()
    return {"ok": True, "id": cur.lastrowid}


@router.put("/custom-roles/{role_id}")
def update_custom_role(
    role_id: int,
    payload: dict,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles("admin")),
):
    row = conn.execute("SELECT * FROM custom_roles WHERE id = ?", (role_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="角色不存在")
    name = (payload.get("name") or row["name"]).strip()
    if conn.execute(
        "SELECT 1 FROM custom_roles WHERE name = ? AND id != ?", (name, role_id)
    ).fetchone():
        raise HTTPException(status_code=400, detail="角色名称已存在")
    perms = [p for p in dict.fromkeys(payload.get("permissions") or []) if p in ALL_PERMISSIONS]
    conn.execute(
        "UPDATE custom_roles SET name = ?, permissions = ? WHERE id = ?",
        (name, ",".join(perms), role_id),
    )
    conn.commit()
    return {"ok": True}


@router.delete("/custom-roles/{role_id}")
def delete_custom_role(
    role_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles("admin")),
):
    used = conn.execute(
        "SELECT COUNT(*) FROM staff WHERE active = 1 AND (',' || custom_role_ids || ',') LIKE ?",
        (f"%,{role_id},%",),
    ).fetchone()[0]
    if used:
        raise HTTPException(status_code=400, detail="该角色仍分配给账号，无法删除")
    conn.execute("DELETE FROM custom_roles WHERE id = ?", (role_id,))
    conn.commit()
    return {"ok": True}
