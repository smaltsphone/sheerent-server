from pydantic import BaseModel, EmailStr
from enum import Enum as PyEnum
from datetime import datetime
from typing import List, Optional

# ✅ Item 상태 ENUM
class ItemStatus(str, PyEnum):
    registered = "registered"
    rented = "rented"
    returned = "returned"
    available = "available"

# ✅ 사용자 등록용 (요청용)
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    phone: str
    password: str

# ✅ 사용자 출력용 (응답용)
class User(BaseModel):
    id: int
    name: str
    email: EmailStr
    phone: str
    point: int
    is_admin: bool

    class Config:
        from_attributes = True  # orm_mode 대신 pydantic v2 방식

# ✅ 아이템 등록용 (요청용)
class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price_per_day: int
    owner_id: int
    price_type: str  # <- 'hour' or 'day' 등
    unit: str

# ✅ 아이템 출력용 (응답용)
class Item(BaseModel):
    id: int
    name: str
    description: str
    price_per_day: int
    status: ItemStatus
    unit: str
    owner_id: int
    images: Optional[List[str]] = []  # ✅ 쉼표로 이어진 문자열
    locker_number: Optional[str] = None
    description: Optional[str] = None

    class Config:
        orm_mode = True

class ItemForRental(BaseModel):
    id: int
    name: str
    description: str
    price_per_day: int
    status: str
    images: Optional[List[str]] = []

    class Config:
        from_attributes = True

# ✅ 아이템 상태 수동 변경용
class ItemStatusUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    price_per_day: Optional[int]
    unit: Optional[str]
    locker_number: Optional[int] = None
    status: Optional[str]
    images: Optional[List[str]]

# ✅ 대여 등록용 (요청용)
class RentalCreate(BaseModel):
    item_id: Optional[int] = None
    borrower_id: int
    end_time: datetime

# ✅ 대여 출력용 (응답용)
class Rental(BaseModel):
    id: int
    item_id: Optional[int] = None
    description: Optional[str] = None
    borrower_id: int
    start_time: datetime
    end_time: datetime
    is_returned: bool
    damage_reported: bool
    deposit_amount: int
    deducted_amount: int
    item: Optional[ItemForRental]

    class Config:
        from_attributes = True
# ✅ 사용자 로그인
class UserLogin(BaseModel):
    email: str
    password: str

class ReturnRequest(BaseModel):
    damage_reported: bool
    user_id: int  # 🔐 실제 로그인한 사용자

