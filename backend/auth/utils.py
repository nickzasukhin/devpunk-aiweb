from datetime import datetime, timedelta
from typing import Optional
from jose import jwt, JWTError
from passlib.context import CryptContext
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    return jwt.encode({**data, "exp": expire, "type": "access"}, settings.SECRET_KEY, settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode({**data, "exp": expire, "type": "refresh"}, settings.SECRET_KEY, settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None
