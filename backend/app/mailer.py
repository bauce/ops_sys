"""邮件通知：SMTP 配置读取与派单提醒发送。"""
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from html import escape

from .db import connect, now
from .tickets_common import STATUS_TEXT

MAIL_KEYS = (
    "smtp_host", "smtp_port", "smtp_secure", "smtp_user", "smtp_password",
    "mail_from", "mail_from_name", "mail_enabled",
)

DEFAULTS = {
    "smtp_host": "",
    "smtp_port": "587",
    "smtp_secure": "starttls",
    "smtp_user": "",
    "smtp_password": "",
    "mail_from": "",
    "mail_from_name": "信息化运维系统",
    "mail_enabled": "0",
}


def get_config(conn=None) -> dict:
    own = conn is None
    conn = conn or connect()
    try:
        rows = {
            r["key"]: r["value"]
            for r in conn.execute(
                "SELECT key, value FROM settings WHERE key LIKE 'smtp_%'"
                " OR key LIKE 'mail_%'"
            )
        }
    finally:
        if own:
            conn.close()
    cfg = dict(DEFAULTS)
    cfg.update({k: v for k, v in rows.items() if k in DEFAULTS})
    cfg["enabled"] = str(cfg.get("mail_enabled", "0")).lower() in ("1", "true", "yes")
    return cfg


def send(to: str, subject: str, html: str, text: str = "") -> tuple:
    """同步发送邮件，返回 (成功, 错误信息)。调用方应放到后台任务里。"""
    to = (to or "").strip()
    if not to or "@" not in to:
        return False, "接收人邮箱为空或格式不正确"
    cfg = get_config()
    if not cfg["enabled"]:
        return False, "邮件通知未启用"
    if not cfg["smtp_host"]:
        return False, "未配置 SMTP 服务器"
    sender = cfg["mail_from"] or cfg["smtp_user"]
    if not sender:
        return False, "未配置发件人邮箱"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((cfg["mail_from_name"] or "运维系统", sender))
    msg["To"] = to
    msg.set_content(text or "请使用支持 HTML 的邮件客户端查看本通知。")
    msg.add_alternative(html, subtype="html")

    host = cfg["smtp_host"]
    try:
        port = int(cfg["smtp_port"] or 587)
    except ValueError:
        return False, "SMTP 端口格式不正确"

    try:
        if cfg["smtp_secure"] == "ssl":
            server = smtplib.SMTP_SSL(host, port, timeout=10,
                                      context=ssl.create_default_context())
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            server.ehlo()
            if cfg["smtp_secure"] == "starttls":
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
        try:
            if cfg["smtp_user"]:
                server.login(cfg["smtp_user"], cfg["smtp_password"])
            server.send_message(msg)
        finally:
            try:
                server.quit()
            except Exception:
                pass
        return True, ""
    except Exception as exc:  # 网络、认证等错误都记录为发送失败
        return False, f"{type(exc).__name__}: {exc}"


def app_link(path: str) -> str:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'public_base_url'"
        ).fetchone()
        base = (
            (row["value"] if row else "")
            or os.environ.get("OPS_PUBLIC_BASE_URL", "").strip()
            or "http://127.0.0.1:8008"
        )
    finally:
        conn.close()
    return base.rstrip("/") + path


def _ticket_rows(ticket_id: int):
    conn = connect()
    try:
        ticket = conn.execute(
            "SELECT * FROM tickets WHERE id = ?", (ticket_id,)
        ).fetchone()
        staff = None
        if ticket and ticket["assignee_id"]:
            staff = conn.execute(
                "SELECT * FROM staff WHERE id = ?", (ticket["assignee_id"],)
            ).fetchone()
        return dict(ticket) if ticket else None, dict(staff) if staff else None
    finally:
        conn.close()


def _layout(title: str, intro: str, rows: list, link: str, second=None) -> str:
    cells = "".join(
        f'<tr><td style="padding:6px 12px;color:#8a94a6;font-size:13px;white-space:nowrap">{escape(k)}</td>'
        f'<td style="padding:6px 12px;color:#1f2937;font-size:14px">{escape(str(v))}</td></tr>'
        for k, v in rows
    )
    return f"""<!DOCTYPE html><html><body style="margin:0;background:#f4f6fb;padding:24px;font-family:-apple-system,'PingFang SC',sans-serif">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:14px;overflow:hidden;border:1px solid #e6eaf2">
    <div style="background:linear-gradient(135deg,#2f6feb,#5a90ff);color:#fff;padding:20px 24px">
      <div style="font-size:18px;font-weight:700">{escape(title)}</div>
      <div style="font-size:13px;opacity:.85;margin-top:4px">{escape(intro)}</div>
    </div>
    <table style="width:100%;border-collapse:collapse">{cells}</table>
    <div style="padding:18px 24px">
      <a href="{escape(link)}" style="display:inline-block;background:#2f6feb;color:#fff;text-decoration:none;
         padding:10px 22px;border-radius:8px;font-size:14px">打开工单处理</a>
      {f'<a href="{escape(second[1])}" style="display:inline-block;margin-left:10px;color:#2f6feb;'
         'text-decoration:none;padding:10px 18px;border-radius:8px;border:1px solid #c9dbfb;'
         f'font-size:14px">{escape(second[0])}</a>' if second else ''}
    </div>
    <div style="padding:14px 24px;border-top:1px solid #eef2f8;color:#9aa4b5;font-size:12px">
      本邮件由信息化运维管理系统自动发送，请勿直接回复。
    </div>
  </div>
</body></html>"""


def send_assigned(ticket_id: int) -> tuple:
    """向工单处理人发送派单提醒。"""
    ticket, staff = _ticket_rows(ticket_id)
    if not ticket or not staff:
        return False, "工单或处理人不存在"
    if not staff.get("email"):
        return False, "处理人未填写邮箱"
    rows = [
        ("工单号", ticket["code"]),
        ("报障地点", ticket["location"]),
        ("故障设备", ticket["device"]),
        ("故障类型", ticket["fault_type"]),
        ("期望上门", ticket["expect_time"] or "立即上门"),
        ("联系人", f'{ticket["contact_name"]} {ticket["contact_phone"]}'),
        ("当前状态", STATUS_TEXT.get(ticket["status"], ticket["status"])),
    ]
    if ticket.get("description"):
        rows.append(("故障描述", ticket["description"]))
    html = _layout(
        "您有一张新的运维工单",
        f'{staff["name"]}，请尽快受理并上门处理',
        rows,
        app_link(f"/admin/tickets?open={ticket_id}"),
        ("查看我的工单", app_link("/admin/tickets?mine=1")),
    )
    subject = f"【运维派单】{ticket['code']} {ticket['location']} {ticket['device']}"
    text = "\n".join(f"{k}：{v}" for k, v in rows)
    return send(staff["email"], subject, html, text)


def send_transfer(ticket_id: int, to_staff_id: int, note: str = "") -> tuple:
    """转派申请：通知接收人。"""
    ticket, _ = _ticket_rows(ticket_id)
    conn = connect()
    try:
        target = conn.execute(
            "SELECT * FROM staff WHERE id = ?", (to_staff_id,)
        ).fetchone()
        requester = conn.execute(
            "SELECT name FROM staff WHERE id = ?", (ticket["assignee_id"],)
        ).fetchone() if ticket and ticket.get("assignee_id") else None
    finally:
        conn.close()
    if not ticket or not target:
        return False, "工单或接收人不存在"
    if not target["email"]:
        return False, "接收人未填写邮箱"
    rows = [
        ("工单号", ticket["code"]),
        ("报障地点", ticket["location"]),
        ("故障设备", ticket["device"]),
        ("期望上门", ticket["expect_time"] or "立即上门"),
        ("转派发起人", requester["name"] if requester else "—"),
        ("转派说明", note or "无"),
    ]
    html = _layout(
        "有一张工单转派给您",
        f'{target["name"]}，请在系统中确认接收或拒绝',
        rows,
        app_link(f"/admin/tickets?open={ticket_id}"),
        ("前往待接收转派", app_link("/admin")),
    )
    subject = f"【工单转派待接收】{ticket['code']} {ticket['location']}"
    text = "\n".join(f"{k}：{v}" for k, v in rows)
    return send(target["email"], subject, html, text)
