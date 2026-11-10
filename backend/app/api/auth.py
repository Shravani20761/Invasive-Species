from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.core.security import create_access_token, hash_password, verify_password
from app.database.session import get_db
from app.models.entities import User, utcnow
from app.services.audit_service import write_audit
from app.services.serializers import user_out

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None


def _token_response(user: User) -> dict:
    return {"access_token": create_access_token(user.id, user.role), "token_type": "bearer", "user": user_out(user)}


@router.post("/register", status_code=201)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    email = payload.email.lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(email=email, full_name=payload.full_name.strip(), hashed_password=hash_password(payload.password), role="citizen")
    db.add(user)
    db.flush()
    write_audit(db, user.id, "register", "user", user.id, {})
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is inactive.")
    write_audit(db, user.id, "login", "user", user.id, {})
    db.commit()
    return _token_response(user)


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return user_out(user)


users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("")
def list_users(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    users = db.query(User).order_by(User.full_name).all()
    return {"items": [user_out(user) for user in users], "total": len(users)}


@users_router.put("/{user_id}")
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), actor: User = Depends(require_roles("admin"))):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if payload.role is not None:
        if payload.role not in {"citizen", "researcher", "admin"}:
            raise HTTPException(status_code=400, detail="Role must be citizen, researcher, or admin.")
        if user.id == actor.id and payload.role != "admin":
            raise HTTPException(status_code=400, detail="You cannot remove your own administrator role.")
        user.role = payload.role
    if payload.is_active is not None:
        if user.id == actor.id and not payload.is_active:
            raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")
        user.is_active = payload.is_active
    user.updated_at = utcnow()
    write_audit(db, actor.id, "user_updated", "user", user.id, {"role": user.role, "is_active": user.is_active})
    db.commit()
    db.refresh(user)
    return user_out(user)
