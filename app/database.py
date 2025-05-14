from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 너가 설정한 비밀번호로 수정해줘!
DATABASE_URL = "mysql+pymysql://root:sheerent@localhost:3306/sheerent"

engine = create_engine(
    DATABASE_URL,
    echo=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
