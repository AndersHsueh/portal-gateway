import random
from datetime import datetime, timedelta
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Form, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_DAYS, COOKIE_DOMAIN, K8S_DASHBOARD_TOKEN
from database import get_db
from email_service import send_verification_code
from models import User, LoginLog, VerifyCode

router = APIRouter(prefix="/api/auth", tags=["认证"])
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 排除易混淆字符 I/O/1/0
CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class SendCodeRequest(BaseModel):
    email: str
    type: Literal["register", "reset"]


class RegisterRequest(BaseModel):
    email: str
    code: str
    password: str
    name: Optional[str] = None


class ResetPasswordBody(BaseModel):
    email: str
    code: str
    new_password: str


def generate_code(length: int = 4) -> str:
    return "".join(random.choices(CODE_CHARS, k=length))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email, User.is_deleted == False).first()
    if user is None:
        raise credentials_exception
    return user


def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current_user


@router.post("/login")
def login(request: Request, response: Response, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email, User.is_deleted == False).first()

    # 记录登录日志
    log = LoginLog(
        email=email,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        success=False
    )

    if user and verify_password(password, user.password_hash):
        log.user_id = user.id
        log.success = True
        db.add(log)
        db.commit()

        access_token = create_access_token(data={"sub": user.email, "role": user.role})

        # 设置跨子域 cookie，用于 K8s Dashboard 等子服务认证
        response.set_cookie(
            key="portal_token",
            value=access_token,
            domain=COOKIE_DOMAIN,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role
            }
        }

    db.add(log)
    db.commit()
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")


@router.post("/logout")
def logout(response: Response, current_user: User = Depends(get_current_user)):
    response.delete_cookie("portal_token", domain=COOKIE_DOMAIN)
    return {"message": "已退出登录"}


@router.get("/k8s-check")
def k8s_auth_check(request: Request, db: Session = Depends(get_db)):
    """
    供 ingress-nginx auth-url 调用的认证端点。
    从 cookie 中读取 portal_token，校验 JWT 和 admin 角色，
    成功则返回 200 并在 Authorization 头中携带 k8s ServiceAccount token。
    """
    token = request.cookies.get("portal_token")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证凭据")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="认证已过期")

    user = db.query(User).filter(User.email == email, User.is_deleted == False).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")

    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")

    if not K8S_DASHBOARD_TOKEN:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="K8s Dashboard Token 未配置")

    response = Response(status_code=200)
    response.headers["Authorization"] = f"Bearer {K8S_DASHBOARD_TOKEN}"
    return response


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role
    }


@router.post("/send-code")
async def send_code(body: SendCodeRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == body.email, User.is_deleted == False).first()

    if body.type == "register" and existing_user:
        raise HTTPException(status_code=400, detail="该邮箱已注册")
    if body.type == "reset" and not existing_user:
        raise HTTPException(status_code=400, detail="该邮箱未注册")

    # 2 分钟频率限制
    recent = db.query(VerifyCode).filter(
        VerifyCode.email == body.email,
        VerifyCode.type == body.type,
        VerifyCode.created_at > datetime.utcnow() - timedelta(minutes=2)
    ).first()
    if recent:
        raise HTTPException(status_code=429, detail="发送过于频繁，请2分钟后再试")

    code = generate_code()
    verify_code = VerifyCode(
        email=body.email,
        code=code,
        type=body.type,
        expires_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.add(verify_code)
    db.commit()

    success = await send_verification_code(body.email, code, body.type)
    if not success:
        raise HTTPException(status_code=500, detail="邮件发送失败，请稍后重试")

    return {"message": "验证码已发送", "expires_in": 600}


@router.post("/register")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email, User.is_deleted == False).first():
        raise HTTPException(status_code=400, detail="该邮箱已注册")

    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6位")

    vc = db.query(VerifyCode).filter(
        VerifyCode.email == body.email,
        VerifyCode.code == body.code.upper(),
        VerifyCode.type == "register",
        VerifyCode.used == False,
        VerifyCode.expires_at > datetime.utcnow()
    ).first()
    if not vc:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    vc.used = True

    name = body.name or body.email.split("@")[0]
    user = User(
        email=body.email,
        password_hash=get_password_hash(body.password),
        name=name,
        role="user"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "注册成功",
        "user": {"id": user.id, "email": user.email, "name": user.name}
    }


@router.post("/reset-password")
def reset_password_with_code(body: ResetPasswordBody, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=400, detail="该邮箱未注册")

    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="密码至少6位")

    vc = db.query(VerifyCode).filter(
        VerifyCode.email == body.email,
        VerifyCode.code == body.code.upper(),
        VerifyCode.type == "reset",
        VerifyCode.used == False,
        VerifyCode.expires_at > datetime.utcnow()
    ).first()
    if not vc:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")

    vc.used = True
    user.password_hash = get_password_hash(body.new_password)
    db.commit()

    return {"message": "密码重置成功"}