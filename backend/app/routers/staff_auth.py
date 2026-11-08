"""运维人员登录、账号管理与系统设置（含邮件配置）。"""
import os
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from .. import mailer
from ..db import get_db, now
from ..schemas import EmailConfigIn, EmailTestIn, LoginIn, StaffIn
from ..security import (
    COOKIE_STAFF,
    apply_duty_role,
    ROLE_NAMES,
    create_session,
    current_staff,
    has_role,
    hash_password,
    parse_roles,
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
    if not row or not verify_password(payload.password, row["pwd_salt"], row["pwd_hash"]):
        raise HTTPException(status_code=400, detail="账号或密码错误")
    if not row["active"]:
        raise HTTPException(status_code=403, detail="账号已停用")
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
        "role_text": "、".join(ROLE_NAMES.get(r, r) for r in data["roles"]),
        "email": data["email"] or "",
    }


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
        "role_text": "、".join(ROLE_NAMES.get(r, r) for r in roles),
        "phone": staff["phone"],
        "email": staff["email"] or "",
    }


@router.get("/users")
def list_users(
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles(*MANAGER_ROLES, "engineer")),
):
    rows = conn.execute(
        "SELECT id, username, name, role, roles, phone, email, active, created_at FROM staff"
        " ORDER BY CASE role WHEN 'admin' THEN 0 WHEN 'dispatcher' THEN 1 ELSE 2 END, id"
    ).fetchall()
    items = []
    for r in rows:
        roles = parse_roles(r["roles"], r["role"])
        items.append({
            **dict(r),
            "roles": roles,
            "role_text": "、".join(ROLE_NAMES.get(x, x) for x in roles),
        })
    return {"items": items}


@router.post("/users")
def create_user(
    payload: StaffIn,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles(*MANAGER_ROLES)),
):
    roles = payload.roles or [payload.role]
    roles = [r for r in dict.fromkeys(roles) if r in ("admin", "dispatcher", "engineer")]
    if not roles:
        raise HTTPException(status_code=400, detail="请至少选择一个角色")
    if has_role(staff, "dispatcher") and not has_role(staff, "admin"):
        if set(roles) - {"engineer"}:
            raise HTTPException(status_code=403, detail="受理员只能添加运维工程师账号")
    if conn.execute(
        "SELECT 1 FROM staff WHERE username = ?", (payload.username.strip(),)
    ).fetchone():
        raise HTTPException(status_code=400, detail="登录名已存在")
    primary = "admin" if "admin" in roles else ("dispatcher" if "dispatcher" in roles else "engineer")
    salt = os.urandom(16).hex()
    conn.execute(
        "INSERT INTO staff(username,name,role,roles,phone,email,pwd_hash,pwd_salt,active,created_at)"
        " VALUES(?,?,?,?,?,?,?,?,1,?)",
        (
            payload.username.strip(), payload.name.strip(), primary, ",".join(roles),
            payload.phone.strip(), (payload.email or "").strip(),
            hash_password(payload.password, salt), salt, now(),
        ),
    )
    conn.commit()
    return {"ok": True}


def _check_manage_permission(staff: dict, target) -> None:
    if has_role(staff, "admin"):
        return
    if has_role(staff, "dispatcher"):
        target_roles = parse_roles(target["roles"], target["role"])
        if set(target_roles) - {"engineer"}:
            raise HTTPException(status_code=403, detail="受理员只能维护运维工程师账号")
        return
    raise HTTPException(status_code=403, detail="没有操作权限")


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    payload: dict,
    conn: sqlite3.Connection = Depends(get_db),
    staff: dict = Depends(require_roles(*MANAGER_ROLES)),
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
        if has_role(staff, "dispatcher") and not has_role(staff, "admin") and set(roles) - {"engineer"}:
            raise HTTPException(status_code=403, detail="受理员不能修改账号角色")
        primary = "admin" if "admin" in roles else ("dispatcher" if "dispatcher" in roles else "engineer")
        payload = {**payload, "role": primary, "roles": ",".join(roles)}

    fields, values = [], []
    for key in ("name", "role", "roles", "phone", "email", "active"):
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
