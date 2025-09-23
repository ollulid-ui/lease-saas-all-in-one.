from datetime import datetime, timedelta
from passlib.context import CryptContext
import jwt
from pydantic import BaseModel
from fastapi import HTTPException, status, Depends
from sqlalchemy.orm import Session
from .settings import settings
from .core.database import get_db
from .models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(pw: str) -> str:
    return pwd_context.hash(pw)

def verify_password(pw: str, hashed: str) -> bool:
    return pwd_context.verify(pw, hashed)

def create_access_token(sub: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": sub, "exp": expire}
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALG)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

class TokenUser(BaseModel):
    email: str

def get_current_user(db: Session = Depends(get_db), token: str | None = None) -> User:
    # Token should be provided via dependency in router using Header
    raise NotImplementedError("Use get_current_user_from_header in routers.auth")
