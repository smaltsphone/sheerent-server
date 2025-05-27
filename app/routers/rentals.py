from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import os
import math

from app.database import SessionLocal
from app.models.models import Rental, Item, User
from app.schemas.schemas import Rental as RentalSchema, RentalCreate
from app.routers.ai import is_item_damaged

router = APIRouter(tags=["rentals"])

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# KST 타임존 정의
KST = timezone(timedelta(hours=9))

# ✅ 요금 미리보기
from pydantic import BaseModel

class RentalPreviewRequest(BaseModel):
    item_id: int
    end_time: datetime

@router.post("/preview")
def rental_preview(request: RentalPreviewRequest, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == request.item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    start_time = datetime.now(KST)
    hours = int((request.end_time - start_time).total_seconds() // 3600)

    # 단위에 따른 시간당 가격 계산
    if item.unit == 'per_day':
        price_per_hour = item.price_per_day / 24
    else:
        price_per_hour = item.price_per_day

    total_fee = hours * price_per_hour
    insurance_fee = round(total_fee * 0.05)
    service_fee = round(total_fee * 0.05)
    total = total_fee + insurance_fee + service_fee

    return {
        "item_name": item.name,
        "hours": hours,
        "price_per_hour": price_per_hour,
        "usage_fee": total_fee,
        "insurance_fee": insurance_fee,
        "service_fee": service_fee,
        "total": total
    }

# ✅ 1. 대여 등록
@router.post("/", response_model=RentalSchema)
def create_rental(rental: RentalCreate, db: Session = Depends(get_db)):
    db_item = db.query(Item).filter(Item.id == rental.item_id).first()
    if not db_item or db_item.status != "registered":
        raise HTTPException(status_code=400, detail="대여할 수 없는 아이템입니다.")

    if db_item.owner_id == rental.borrower_id:
        raise HTTPException(status_code=400, detail="자신이 등록한 물품은 대여할 수 없습니다.")

    active_rental = db.query(Rental).filter(
        Rental.item_id == rental.item_id,
        Rental.is_returned == False
    ).first()
    if active_rental:
        raise HTTPException(status_code=400, detail="해당 아이템은 아직 반납되지 않았습니다.")

    start_time = datetime.now(KST)  # tz-aware datetime (KST)

    end_time = rental.end_time
    if end_time.tzinfo is None or end_time.tzinfo.utcoffset(end_time) is None:
        end_time = end_time.replace(tzinfo=KST)

    if end_time <= start_time:
        raise HTTPException(status_code=400, detail="종료시간은 시작시간보다 나중이어야 합니다.")

    hours = max(1, math.ceil((end_time - start_time).total_seconds() / 3600))

    # 단위에 따른 시간당 가격 계산
    if db_item.unit == "per_day":
        price_per_hour = db_item.price_per_day / 24
    else:
        price_per_hour = db_item.price_per_day

    rental_price = price_per_hour * hours

    insurance_fee = round(rental_price * 0.05)  # 보험료 5%
    service_fee = round(rental_price * 0.05)    # 수수료 5%
    total_pay = rental_price + insurance_fee + service_fee

    db_user = db.query(User).filter(User.id == rental.borrower_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    if db_user.point < total_pay:
        raise HTTPException(status_code=400, detail="포인트가 부족합니다.")

    db_user.point -= int(total_pay)

    db_item.status = "rented"
    new_rental = Rental(
        item_id=rental.item_id,
        borrower_id=rental.borrower_id,
        start_time=start_time,
        end_time=end_time,
        is_returned=False,
        deposit_amount=insurance_fee,
        damage_reported=False,
        deducted_amount=0
    )

    db.add(new_rental)
    db.commit()
    db.refresh(new_rental)

    # 디버그 출력
    print(f"[Create Rental] 요청 item_id: {rental.item_id}, borrower_id: {rental.borrower_id}")
    print(f"[Create Rental] 아이템 상태: {db_item.status if db_item else 'None'}")
    print(f"[Create Rental] 대여자와 소유자 비교: borrower_id={rental.borrower_id}, owner_id={db_item.owner_id if db_item else 'None'}")
    print(f"[Create Rental] 대여중인 렌탈 존재 여부: {active_rental is not None}")
    print(f"[Create Rental] 시작시간(start_time): {start_time}")
    print(f"[Create Rental] 종료시간(end_time): {end_time}")
    print(f"[Create Rental] 대여 시간(시): {hours}")
    print(f"[Create Rental] 시간당 가격: {price_per_hour}")
    print(f"[Create Rental] 일당 가격: {db_item.price_per_day}")
    print(f"[Create Rental] 대여료: {rental_price}")
    print(f"[Create Rental] 보험료: {insurance_fee}, 수수료: {service_fee}")
    print(f"[Create Rental] 총 결제 금액: {total_pay}")
    print(f"[Create Rental] 사용자 포인트: {db_user.point if db_user else 'None'}")

    return new_rental



# ✅ 2. 전체 대여 조회 + 필터링
@router.get("/", response_model=List[RentalSchema])
def get_rentals(is_returned: Optional[bool] = Query(None), db: Session = Depends(get_db)):
    query = db.query(Rental).options(joinedload(Rental.item))
    if is_returned is not None:
        query = query.filter(Rental.is_returned == is_returned)
    return query.all()

# ✅ 3. 반납 처리 + AI 분석 + 보증금 정산
@router.put("/{rental_id}/return", response_model=RentalSchema)
async def return_rental(
    rental_id: int,
    user_id: int = Form(...),
    item_id: int = Form(...),
    after_file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    rental = db.query(Rental).filter(Rental.id == rental_id).first()
    if not rental:
        raise HTTPException(status_code=404, detail="대여 기록을 찾을 수 없습니다.")
    if rental.borrower_id != user_id:
        raise HTTPException(status_code=403, detail="본인만 반납할 수 있습니다.")
    if rental.is_returned:
        raise HTTPException(status_code=400, detail="이미 반납된 대여입니다.")
    
    before_img = get_before_image(item_id, db)

    rental_dir = f"images/after/rental_{rental_id}"
    os.makedirs(rental_dir, exist_ok=True)
    after_path = os.path.join(rental_dir, "after.jpg")
    with open(after_path, "wb") as f:
        f.write(await after_file.read())

    rental_key, damage_detected, damage_info = is_item_damaged(item_id, rental_id, before_img, after_path)

    rental.is_returned = True
    rental.damage_reported = damage_detected
    rental.deducted_amount = rental.deposit_amount if damage_detected else 0

    db_item = db.query(Item).filter(Item.id == rental.item_id).first()
    db_item.status = "registered"

    db.commit()
    db.refresh(rental)

    return JSONResponse(content={
        "id": rental.id,
        "item_id": rental.item_id,
        "borrower_id": rental.borrower_id,
        "start_time": rental.start_time.isoformat(),
        "end_time": rental.end_time.isoformat(),
        "is_returned": rental.is_returned,
        "damage_reported": rental.damage_reported,
        "deposit_amount": rental.deposit_amount,
        "deducted_amount": rental.deducted_amount,
        "item": {
            "id": rental.item.id,
            "name": rental.item.name,
            "price_per_day": rental.item.price_per_day,
            "status": rental.item.status,
            "images": rental.item.images
        } if rental.item else None,
        "damage_info": damage_info
    })

# 보관 이미지 가져오기 함수
def get_before_image(item_id: int, db: Session):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item or not item.images:
        raise HTTPException(status_code=404, detail="아이템 이미지가 없습니다.")
    relative_path = item.images[0].lstrip("/")
    absolute_path = os.path.join("app", relative_path)
    if not os.path.isfile(absolute_path):
        raise HTTPException(status_code=404, detail="비포 이미지 파일이 존재하지 않습니다.")
    return absolute_path

# ✅ 4. 대여 상세 조회
@router.get("/{rental_id}", response_model=RentalSchema)
def get_rental_detail(rental_id: int, db: Session = Depends(get_db)):
    rental = db.query(Rental).filter(Rental.id == rental_id).first()
    if not rental:
        raise HTTPException(status_code=404, detail="해당 대여 기록을 찾을 수 없습니다.")
    return rental

# ✅ 5. 사용자별 대여 통계
@router.get("/stats/{user_id}")
def get_user_rental_stats(user_id: int, db: Session = Depends(get_db)):
    total = db.query(Rental).filter(Rental.borrower_id == user_id).count()
    returned = db.query(Rental).filter(Rental.borrower_id == user_id, Rental.is_returned == True).count()
    not_returned = db.query(Rental).filter(Rental.borrower_id == user_id, Rental.is_returned == False).count()
    return {
        "user_id": user_id,
        "total_rentals": total,
        "returned": returned,
        "not_returned": not_returned
    }

# ✅ 6. 대여 연장
@router.put("/{rental_id}/extend")
def extend_rental(rental_id: int, db: Session = Depends(get_db)):
    rental = db.query(Rental).filter(Rental.id == rental_id).first()
    if not rental:
        raise HTTPException(status_code=404, detail="대여 기록을 찾을 수 없습니다.")
    if rental.is_returned:
        raise HTTPException(status_code=400, detail="이미 반납된 대여입니다.")

    rental.end_time += timedelta(days=1)
    db.commit()
    db.refresh(rental)
    return rental
