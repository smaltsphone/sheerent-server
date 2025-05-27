from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import Item

router = APIRouter(prefix="/lockers", tags=["lockers"])

# DB 세션
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 전체 가능한 보관함 번호 예시 (고정)
ALL_LOCKERS = ["101", "102", "103", "104", "105"]

@router.get("/available")
def get_available_lockers(db: Session = Depends(get_db)):
    used = db.query(Item.locker_number).filter(Item.locker_number.isnot(None)).all()
    used_lockers = {locker[0] for locker in used if locker[0]}
    available = [num for num in ALL_LOCKERS if num not in used_lockers]
    return available
