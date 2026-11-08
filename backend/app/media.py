"""报障现场照片：保存 base64 图片到 data/uploads。"""
import base64
import re
import uuid
from datetime import datetime
from pathlib import Path

from .db import DATA_DIR

UPLOAD_DIR = DATA_DIR / "uploads"
MAX_BYTES = 2 * 1024 * 1024
MAX_PHOTOS = 3
DATA_URL_RE = re.compile(r"^data:image/(jpeg|jpg|png|webp);base64,(.+)$", re.S)


def save_data_url(data_url: str) -> str:
    """保存图片，返回可访问的相对路径；格式不合法时抛 ValueError。"""
    match = DATA_URL_RE.match((data_url or "").strip())
    if not match:
        raise ValueError("图片格式不支持，请上传 JPG/PNG")
    ext = "jpg" if match.group(1) in ("jpeg", "jpg") else match.group(1)
    try:
        raw = base64.b64decode(match.group(2), validate=True)
    except Exception:
        raise ValueError("图片数据损坏")
    if len(raw) > MAX_BYTES:
        raise ValueError("单张照片不能超过 2MB")
    month = datetime.now().strftime("%Y%m")
    folder = UPLOAD_DIR / month
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    (folder / name).write_bytes(raw)
    return f"/uploads/{month}/{name}"
