from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.database import SessionLocal
from app.models.models import User, Item, Rental
from app.schemas.schemas import User as UserSchema, UserCreate, UserLogin, Item as ItemSchema, Rental as RentalSchema

router = APIRouter(prefix="/users", tags=["users"])

# DB 세션 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ 1. 사용자 등록 (이메일 중복 방지)
@router.post("/", response_model=UserSchema)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")
    
    db_user = User(name=user.name, email=user.email, phone=user.phone,  password=user.password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# ✅ 2. 사용자 로그인 (이메일 + 비밀번호 인증)
@router.post("/login", response_model=UserSchema)
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email, User.password == user.password).first()
    if not db_user:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
    return db_user

# ✅ 3. 사용자가 등록한 물품 조회
@router.get("/{user_id}/items", response_model=List[ItemSchema])
def get_user_items(user_id: int, db: Session = Depends(get_db)):
    user_items = db.query(Item).filter(Item.owner_id == user_id).all()
    if not user_items:
        raise HTTPException(status_code=404, detail="해당 사용자가 등록한 물품이 없습니다.")
    return user_items

# ✅ 4. 사용자가 대여한 내역 조회
@router.get("/{user_id}/rentals", response_model=List[RentalSchema])
def get_user_rentals(user_id: int, db: Session = Depends(get_db)):
    user_rentals = db.query(Rental)\
        .options(joinedload(Rental.item))\
        .filter(Rental.borrower_id == user_id)\
        .all()
    return user_rentals
