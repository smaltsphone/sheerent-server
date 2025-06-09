from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.models import Item
import requests

router = APIRouter(prefix="/lockers", tags=["lockers"])
RASPBERRY_PI_URL = "http://192.168.137.187:8000"

# DB 세션
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 전체 가능한 보관함 번호 예시 (고정)
ALL_LOCKERS = ["101", "102", "103", "104", "105"]

@router.get("/all")
def get_all_lockers():
    return ALL_LOCKERS

@router.get("/available")
def get_available_lockers(db: Session = Depends(get_db)):
    used = db.query(Item.locker_number).filter(Item.locker_number.isnot(None)).all()
    used_lockers = {locker[0] for locker in used if locker[0]}
    available = [num for num in ALL_LOCKERS if num not in used_lockers]
    return available

@router.post("/open")
def open_door():
    try:
        response = requests.post(f"{RASPBERRY_PI_URL}/open")
        if response.status_code == 200:
            return {"message": "문이 열렸습니다."}
        else:
            return {"error": f"문 열기 실패: {response.status_code}"}
    except Exception as e:
        return {"error": f"연결 실패: {str(e)}"}

@router.post("/close")
def close_door():
    try:
        response = requests.post(f"{RASPBERRY_PI_URL}/close")
        if response.status_code == 200:
            return {"message": "문이 닫혔습니다."}
        else:
            return {"error": f"문 닫기 실패: {response.status_code}"}
    except Exception as e:
        return {"error": f"연결 실패: {str(e)}"}
