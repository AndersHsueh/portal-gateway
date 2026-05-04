from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta

from database import engine, Base, SessionLocal, get_db
from models import User
from auth import get_password_hash, router as auth_router
from users import router as users_router
from projects import router as projects_router

# 创建表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="老薛的技术博客 API", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(projects_router)


@app.on_event("startup")
def init_db():
    """初始化数据库，创建默认管理员"""
    db = SessionLocal()
    try:
        # 检查是否已有管理员
        admin = db.query(User).filter(User.role == "admin").first()
        if not admin:
            admin = User(
                email="anderssitvosinvallage@tutamail.com",
                password_hash=get_password_hash("1223"),
                name="管理员",
                role="admin"
            )
            db.add(admin)
            db.commit()
            print("✓ 默认管理员已创建: anderssitvosinvallage@tutamail.com / 1223")
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "老薛的技术博客 API", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}