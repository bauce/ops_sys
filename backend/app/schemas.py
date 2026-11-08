"""请求/响应数据结构。"""
from typing import List, Optional

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str
    password: str


class TicketCreateIn(BaseModel):
    qr: str = ""
    room_id: Optional[int] = None
    device: str = Field(..., min_length=1, max_length=100)
    fault_type: str = Field(..., min_length=1, max_length=50)
    description: str = ""
    contact_name: str = Field(..., min_length=1, max_length=50)
    contact_phone: str = Field(..., min_length=5, max_length=20)
    expect_time: str = ""
    photos: List[str] = []


class ConfirmIn(BaseModel):
    rating: int = 5
    comment: str = ""
    signature: str = ""


class AcceptIn(BaseModel):
    assignee_id: Optional[int] = None


class MaterialUse(BaseModel):
    material_id: int
    qty: float = 1


class FinishIn(BaseModel):
    fault_cause: str = ""
    solve_note: str = ""
    materials: List[MaterialUse] = []


class RoomIn(BaseModel):
    building: str
    floor: str
    room_no: str
    name: str = ""
    note: str = ""
    active: int = 1


class CategoryIn(BaseModel):
    name: str
    prefix: str
    sort: int = 0


class DictIn(BaseModel):
    name: str
    sort: int = 0


class MaterialIn(BaseModel):
    code: Optional[str] = None
    name: str
    category: str = ""
    category_id: Optional[int] = None
    spec: str = ""
    unit: str = "个"
    stock: float = 0
    warn_stock: float = 0
    location: str = ""
    unit_price: float = 0
    remark: str = ""


class MaterialUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    category_id: Optional[int] = None
    spec: Optional[str] = None
    unit: Optional[str] = None
    warn_stock: Optional[float] = None
    location: Optional[str] = None
    unit_price: Optional[float] = None
    remark: Optional[str] = None
    active: Optional[int] = None


class StockIn(BaseModel):
    qty: float
    note: str = ""
    ticket_id: Optional[int] = None


class ImportIn(BaseModel):
    content: str


class StaffIn(BaseModel):
    username: str
    name: str
    role: str = "engineer"
    roles: List[str] = []
    phone: str = ""
    email: str = ""
    password: str


class EmailConfigIn(BaseModel):
    smtp_host: str = ""
    smtp_port: str = "587"
    smtp_secure: str = "starttls"
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from: str = ""
    mail_from_name: str = "信息化运维系统"
    mail_enabled: int = 0


class EmailTestIn(BaseModel):
    to: str = ""


class ManualTicketIn(BaseModel):
    room_id: Optional[int] = None
    location_text: str = ""
    device: str
    fault_type: str
    description: str = ""
    contact_name: str
    contact_phone: str
    expect_time: str = ""
    assignee_id: Optional[int] = None


class TransferIn(BaseModel):
    to_staff_id: int
    note: str = ""
