from typing import List, Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from auth import get_admin_user, get_current_user, get_password_hash
from database import get_db
from models import User, LoginLog

router = APIRouter(prefix="/api/admin", tags=["管理员"])


class CreateUserRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "user"


class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    new_password: str


@router.get("/users")
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    users = db.query(User).filter(User.is_deleted == False).all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat()
        }
        for u in users
    ]


@router.post("/users")
def create_user(body: CreateUserRequest, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    existing = db.query(User).filter(User.email == body.email, User.is_deleted == False).first()
    if existing:
        raise HTTPException(status_code=400, detail="该邮箱已存在")

    user = User(
        email=body.email,
        password_hash=get_password_hash(body.password),
        name=body.name,
        role=body.role if body.role in ["admin", "user"] else "user"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {"id": user.id, "email": user.email, "name": user.name, "role": user.role}


@router.put("/users/{user_id}")
def update_user(user_id: int, body: UpdateUserRequest,
                db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if body.email:
        user.email = body.email
    if body.name:
        user.name = body.name
    if body.role and body.role in ["admin", "user"]:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active

    db.commit()
    return {"message": "更新成功"}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能删除自己")

    user.is_deleted = True
    db.commit()
    return {"message": "删除成功"}


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: int, body: ResetPasswordRequest,
                   db: Session = Depends(get_db), current_user: User = Depends(get_admin_user)):
    user = db.query(User).filter(User.id == user_id, User.is_deleted == False).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.password_hash = get_password_hash(body.new_password)
    db.commit()
    return {"message": "密码已重置"}