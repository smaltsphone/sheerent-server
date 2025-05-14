from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, DateTime, Boolean
from sqlalchemy import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.types import JSON
from datetime import datetime
from app.database import Base
import enum

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50))
    email = Column(String(100), unique=True, index=True)
    phone = Column(String(20))  # ✅ 추가
    password = Column(String(100))
    items = relationship("Item", back_populates="owner")
    
# Item 상태 ENUM
class ItemStatus(str, enum.Enum):
    registered = "registered"
    rented = "rented"
    returned = "returned"

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    description = Column(String(300))
    price_per_day = Column(Integer)
    status = Column(String(20))
    owner_id = Column(Integer, ForeignKey("users.id"))  # ✅ 이 줄 추가해야 함
    images = Column(JSON)
    rentals = relationship("Rental", back_populates="item")
    unit = Column(String(20))
    owner = relationship("User", back_populates="items")

class Rental(Base):
    __tablename__ = "rentals"

    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey("items.id"))
    borrower_id = Column(Integer, ForeignKey("users.id"))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    is_returned = Column(Boolean, default=False)
    item = relationship("Item", back_populates="rentals")

    # ✅ 여기가 들여쓰기 맞는 상태
    deposit_amount = Column(Integer, default=0)
    damage_reported = Column(Boolean, default=False)
    deducted_amount = Column(Integer, default=0)
