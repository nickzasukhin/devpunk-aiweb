from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from database import get_db, User
from auth.utils import verify_password, hash_password, create_access_token, create_refresh_token, decode_token
from auth.middleware import get_current_user
from admin.audit import log_action

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    user.last_login = datetime.utcnow()
    db.commit()

    token_data = {"sub": str(user.id), "role": user.role}
    log_action(db, user_id=user.id, action="login", ip=request.client.host if request.client else None)

    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
        role=user.role
    )


@router.post("/refresh")
async def refresh(request: Request, db: Session = Depends(get_db)):
    body = await request.json()
    token = body.get("refresh_token")
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    token_data = {"sub": str(user.id), "role": user.role}
    return {"access_token": create_access_token(token_data), "token_type": "bearer"}


@router.post("/change-password")
async def change_password(
    req: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong current password")
    current_user.hashed_password = hash_password(req.new_password)
    db.commit()
    log_action(db, user_id=current_user.id, action="change_password", ip=request.client.host if request.client else None)
    return {"message": "Password changed"}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {"id": str(current_user.id), "email": current_user.email, "role": current_user.role}
