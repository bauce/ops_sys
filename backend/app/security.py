"""密码、会话 Cookie 与身份依赖。"""
import hashlib
import hmac
import os
import secrets
from datetime import date, datetime, timedelta

from fastapi import Depends, HTTPException, Request, Response
import json
import sqlite3

from .db import get_db, now

COOKIE_STAFF = "ops_staff"
COOKIE_REPORTER = "ops_reporter"
SESSION_DAYS = 7
REPORTER_DAYS = 180


def hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000
    ).hex()


def verify_password(password: str, salt: str, expected: str) -> bool:
    return hmac.compare_digest(hash_password(password, salt), expected)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(32)


def parse_roles(value, fallback: str = "") -> list:
    roles = [r.strip() for r in (value or "").split(",") if r.strip()]
    if not roles and fallback:
        roles = [fallback]
    return roles


def has_role(staff: dict, role: str) -> bool:
    return role in staff.get("roles", [])


ROLE_NAMES = {
    "admin": "系统管理员",
    "dispatcher": "报障受理员",
    "engineer": "运维工程师",
    "duty": "值班受理",
}


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def is_on_duty(conn, staff_id: int) -> bool:
    """当前是否在值班（整周值班或今日临时调班时间段内）。"""
    now_dt = datetime.now()
    today = now_dt.date()
    week_start = _monday(today).isoformat()
    row = conn.execute(
        "SELECT staff_ids FROM duty_weeks WHERE week_start = ?", (week_start,)
    ).fetchone()
    if row:
        try:
            ids = json.loads(row["staff_ids"] or "[]")
        except (TypeError, ValueError):
            ids = []
        if any(str(x) == str(staff_id) for x in ids):
            return True

    current_time = now_dt.strftime("%H:%M")
    for adj in conn.execute(
        "SELECT staff_ids, start_time, end_time FROM duty_adjustments"
        " WHERE adjust_date = ?",
        (today.isoformat(),),
    ):
        if not (adj["start_time"] <= current_time <= adj["end_time"]):
            continue
        try:
            ids = json.loads(adj["staff_ids"] or "[]")
        except (TypeError, ValueError):
            ids = []
        if any(str(x) == str(staff_id) for x in ids):
            return True
    return False


def apply_duty_role(conn, data: dict) -> dict:
    """值班中的工程师临时获得受理派单权限（不写入数据库）。"""
    roles = data.get("roles") or parse_roles("", data.get("role", ""))
    data["roles"] = roles
    on_duty = is_on_duty(conn, data["id"])
    data["on_duty"] = on_duty
    if (
        on_duty
        and "engineer" in roles
        and "dispatcher" not in roles
        and "admin" not in roles
    ):
        data["roles"] = roles + ["duty"]
    return data


def current_staff(
    request: Request, conn: sqlite3.Connection = Depends(get_db)
) -> dict:
    token = request.cookies.get(COOKIE_STAFF)
    if not token:
        raise HTTPException(status_code=401, detail="请先登录")
    row = conn.execute(
        "SELECT st.id, st.username, st.name, st.role, st.roles, st.phone, st.email, s.expires_at"
        " FROM sessions s JOIN staff st ON st.id = s.staff_id"
        " WHERE s.token_hash = ? AND st.active = 1",
        (sha256(token),),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录")
    if row["expires_at"] < now():
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (sha256(token),))
        conn.commit()
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    data = dict(row)
    data["roles"] = parse_roles(data.get("roles"), data["role"])
    return apply_duty_role(conn, data)


def require_roles(*roles: str):
    def dependency(staff: dict = Depends(current_staff)) -> dict:
        if not any(has_role(staff, r) for r in roles):
            raise HTTPException(status_code=403, detail="没有操作权限")
        return staff

    return dependency


def create_session(conn: sqlite3.Connection, staff_id: int, response: Response) -> None:
    token = new_token()
    expires = (datetime.now() + timedelta(days=SESSION_DAYS)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    conn.execute(
        "INSERT INTO sessions(token_hash, staff_id, created_at, expires_at)"
        " VALUES(?,?,?,?)",
        (sha256(token), staff_id, now(), expires),
    )
    conn.commit()
    response.set_cookie(
        COOKIE_STAFF, token, max_age=SESSION_DAYS * 86400, httponly=True,
        samesite="lax", path="/",
    )


def reporter_identity(
    request: Request,
    response: Response,
    conn: sqlite3.Connection = Depends(get_db),
):
    """匿名报障人身份：没有 Cookie 时自动签发一个。"""
    token = request.cookies.get(COOKIE_REPORTER)
    row = None
    if token:
        row = conn.execute(
            "SELECT * FROM reporters WHERE token_hash = ?", (sha256(token),)
        ).fetchone()
    if row is None:
        token = new_token()
        conn.execute(
            "INSERT INTO reporters(token_hash, created_at, last_seen) VALUES(?,?,?)",
            (sha256(token), now(), now()),
        )
        conn.commit()
        response.set_cookie(
            COOKIE_REPORTER, token, max_age=REPORTER_DAYS * 86400,
            httponly=True, samesite="lax", path="/",
        )
        row = conn.execute(
            "SELECT * FROM reporters WHERE token_hash = ?", (sha256(token),)
        ).fetchone()
    else:
        conn.execute(
            "UPDATE reporters SET last_seen = ? WHERE id = ?", (now(), row["id"])
        )
        conn.commit()
    return dict(row)
