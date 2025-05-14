from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Body
import shutil
import os
import uuid
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import SessionLocal
from app.models.models import Item, ItemStatus
from app.schemas.schemas import Item as ItemSchema, ItemCreate, ItemStatusUpdate

router = APIRouter(tags=["items"])

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ 1. 아이템 등록 (JSON 방식)
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

# ✅ 2. 이미지 업로드 포함 등록
@router.post("/", response_model=ItemSchema)
async def create_item_with_images(
    name: str = Form(...),
    description: str = Form(""),
    price_per_day: int = Form(...),
    owner_id: int = Form(...),
    unit: str = Form("per_day"),
    files: list[UploadFile] = File(default=[]),
    db: Session = Depends(get_db)
):
    db_item = Item(
        name=name,
        description=description,
        price_per_day=price_per_day,
        owner_id=owner_id,
        unit=unit,
        images=[],
        status=ItemStatus.registered
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    item_dir = f"app/static/images/item_{db_item.id}"
    web_base_path = f"/static/images/item_{db_item.id}"
    os.makedirs(item_dir, exist_ok=True)
    saved_paths = []
    
    print(f"🔥 업로드된 파일 수: {len(files)}")
    for idx, file in enumerate(files[:10]):
        ext = os.path.splitext(file.filename)[1]
        filename = f"{idx}{ext}"
        file_path = os.path.join(item_dir, filename)

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        saved_paths.append(f"{web_base_path}/{filename}")

    db_item.images = saved_paths
    db.commit()
    db.refresh(db_item)
    return db_item

# ✅ 3. 대여 가능한 아이템 조회
@router.get("/available", response_model=List[ItemSchema])
def get_available_items(db: Session = Depends(get_db)):
    return db.query(Item).filter(Item.status == ItemStatus.registered).all()

# ✅ 4. 아이템 상태 변경
@router.patch("/{item_id}/status", response_model=ItemSchema)
def update_item_status(item_id: int, update: ItemStatusUpdate, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="아이템을 찾을 수 없습니다.")
    item.status = update.status
    db.commit()
    db.refresh(item)
    return item

# ✅ 5. 아이템 상세 조회
@router.get("/{item_id}", response_model=ItemSchema)
def get_item_detail(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="해당 아이템을 찾을 수 없습니다.")
    return item

# ✅ 6. 아이템 통계 조회
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

# ✅ 7. 아이템 삭제
@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="해당 아이템을 찾을 수 없습니다.")
    db.delete(item)
    db.commit()
    return

# ✅ 8. 모든 아이템 삭제
@router.delete("/delete_all", status_code=204)
def delete_all_items(db: Session = Depends(get_db)):
    db.query(Item).delete()
    db.commit()
    return

# ✅ 9. 특정 사용자 아이템 조회
@router.get("/owned/{user_id}", response_model=List[ItemSchema])
def get_items_by_owner(user_id: int, db: Session = Depends(get_db)):
    return db.query(Item).filter(Item.owner_id == user_id).all()
