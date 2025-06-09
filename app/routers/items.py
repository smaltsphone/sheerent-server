from fastapi import status, APIRouter, Depends, HTTPException, File, UploadFile, Form, Body
from fastapi.responses import FileResponse
import qrcode
import shutil
import os
from sqlalchemy.orm import Session
from typing import List
from app.database import SessionLocal
from app.models.models import Item, ItemStatus
from app.schemas.schemas import Item as ItemSchema, ItemCreate, ItemStatusUpdate
from typing import Optional

router = APIRouter(tags=["items"])

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 1. 아이템 등록 (JSON)
@router.post("/json", response_model=ItemSchema)
def create_item_json(
    item: ItemCreate = Body(...),
    db: Session = Depends(get_db)
):
    db_item = Item(
        name=item.name,
        description=item.description,
        price_per_day=item.price_per_day,
        owner_id=item.owner_id,
        unit=item.unit,
        images=[],
        status=ItemStatus.registered
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

# 2. 이미지 포함 아이템 등록 (Form + files)
@router.post("/", response_model=ItemSchema)
async def create_item_with_images(
    name: str = Form(...),
    description: str = Form(""),
    price_per_day: int = Form(...),
    owner_id: int = Form(...),
    unit: str = Form("per_day"),
    locker_number: Optional[str] = Form(default=None),  # ✅ 보관함 번호 입력 받기
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db)
):
    # ✅ 중복된 보관함 번호가 있는지 확인
    if locker_number:
        existing_item = db.query(Item).filter(Item.locker_number == locker_number).first()
        if existing_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"보관함 번호 {locker_number}는 이미 사용 중입니다."
            )

    # ✅ 아이템 생성
    db_item = Item(
        name=name,
        description=description,
        price_per_day=price_per_day,
        owner_id=owner_id,
        unit=unit,
        locker_number=locker_number,  # ✅ 저장
        images=[],
        status=ItemStatus.registered
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    # ✅ 이미지 저장
    item_dir = f"app/static/images/item_{db_item.id}"
    web_base_path = f"/static/images/item_{db_item.id}"
    os.makedirs(item_dir, exist_ok=True)
    saved_paths = []

    for idx, file in enumerate(files[:10]):
        ext = os.path.splitext(file.filename)[1]
        filename = f"before{ext}" if idx == 0 else f"{idx}{ext}"
        file_path = os.path.join(item_dir, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        saved_paths.append(f"{web_base_path}/{filename}")

    db_item.images = saved_paths
    db.commit()
    db.refresh(db_item)
    return db_item

# 3. 대여 가능한 아이템 조회
@router.get("/available", response_model=List[ItemSchema])
def get_available_items(db: Session = Depends(get_db)):
    return db.query(Item).filter(Item.status == ItemStatus.registered).all()

# 4. 아이템 상태 변경 (PATCH)
@router.patch("/{item_id}/status", response_model=ItemSchema)
def update_item_status(item_id: int, update: ItemStatusUpdate, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="아이템을 찾을 수 없습니다.")
    item.status = update.status
    db.commit()
    db.refresh(item)
    return item

# 5. 아이템 상세 조회
@router.get("/{item_id}", response_model=ItemSchema)
def get_item_detail(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="해당 아이템을 찾을 수 없습니다.")
    return item

# 6. 아이템 통계 조회
@router.get("/stats")
def get_item_statistics(db: Session = Depends(get_db)):
    total = db.query(Item).count()
    registered = db.query(Item).filter(Item.status == ItemStatus.registered).count()
    rented = db.query(Item).filter(Item.status == ItemStatus.rented).count()
    returned = db.query(Item).filter(Item.status == ItemStatus.returned).count()

    return {
        "total_items": total,
        "registered_items": registered,
        "rented_items": rented,
        "returned_items": returned
    }

# 7. 아이템 삭제
@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="해당 아이템을 찾을 수 없습니다.")
    db.delete(item)
    db.commit()
    return

# 8. 모든 아이템 삭제
@router.delete("/delete_all", status_code=204)
def delete_all_items(db: Session = Depends(get_db)):
    db.query(Item).delete()
    db.commit()
    return

# 9. 특정 사용자 아이템 조회
@router.get("/owned/{user_id}", response_model=List[ItemSchema])
def get_items_by_owner(user_id: int, db: Session = Depends(get_db)):
    return db.query(Item).filter(Item.owner_id == user_id).all()

# 10. 아이템 QR코드 생성 및 제공
@router.get("/{item_id}/qrcode")
def get_item_qrcode(item_id: int):
    save_dir = "qrcodes"
    os.makedirs(save_dir, exist_ok=True)

    qr_path = os.path.join(save_dir, f"item_{item_id}.png")

    if not os.path.exists(qr_path):
        qr = qrcode.make(str(item_id))
        qr.save(qr_path)

    return FileResponse(qr_path, media_type="image/png")

# 11. 아이템 정보 업데이트 (PUT)
@router.put("/{item_id}", response_model=ItemSchema)
async def update_item(
    item_id: int,
    name: str = Form(None),
    description: str = Form(None),
    price_per_day: int = Form(None),
    unit: str = Form(None),
    locker_number: str = Form(None),
    status: str = Form(None),
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db)
):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="아이템 없음")

    # 값 수정
    if name is not None: item.name = name
    if description is not None: item.description = description
    if price_per_day is not None: item.price_per_day = price_per_day
    if unit is not None: item.unit = unit
    if locker_number is not None: item.locker_number = locker_number
    if status is not None: item.status = status
    print(f"Received locker_number: {locker_number}")

    # 이미지 수정
    if files:
        item_dir = f"app/static/images/item_{item.id}"
        web_base_path = f"/static/images/item_{item.id}"
        os.makedirs(item_dir, exist_ok=True)
        saved_paths = []

        for idx, file in enumerate(files[:10]):
            ext = os.path.splitext(file.filename)[1]
            filename = f"before{ext}" if idx == 0 else f"{idx}{ext}"
            file_path = os.path.join(item_dir, filename)

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            saved_paths.append(f"{web_base_path}/{filename}")

        item.images = saved_paths

    try:
        db.commit()
        db.refresh(item)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="DB 업데이트 실패")

    return item