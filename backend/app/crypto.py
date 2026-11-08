"""敏感信息加解密（设备管理密码）。"""
from cryptography.fernet import Fernet, InvalidToken

PREFIX = "enc:v1:"


def _key(conn) -> bytes:
    row = conn.execute(
        "SELECT value FROM settings WHERE key = 'asset_secret'"
    ).fetchone()
    if row and row["value"]:
        return row["value"].encode()
    key = Fernet.generate_key().decode()
    conn.execute(
        "INSERT INTO settings(key,value) VALUES('asset_secret',?)"
        " ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key,),
    )
    conn.commit()
    return key.encode()


def encrypt(conn, text: str) -> str:
    if not text:
        return ""
    token = Fernet(_key(conn)).encrypt(text.encode("utf-8")).decode()
    return PREFIX + token


def decrypt(conn, value: str) -> str:
    if not value:
        return ""
    if not value.startswith(PREFIX):
        return value
    try:
        return Fernet(_key(conn)).decrypt(value[len(PREFIX):].encode()).decode()
    except (InvalidToken, ValueError):
        return ""
