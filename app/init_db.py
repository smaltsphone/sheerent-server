# init_db.py
from app.database import Base, engine
from app.models.models import User, Item, Rental

print("🧨 모든 테이블 삭제 중...")
Base.metadata.drop_all(bind=engine)

print("📦 모든 테이블 다시 생성 중...")
Base.metadata.create_all(bind=engine)

print("✅ 초기화 완료")