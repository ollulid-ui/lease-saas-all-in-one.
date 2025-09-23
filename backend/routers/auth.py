from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models import User
from ..auth import hash_password, verify_password, create_access_token, decode_token

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterIn(BaseModel):
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/register")
def register(body: RegisterIn, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    u = User(email=body.email, password_hash=hash_password(body.password))
    db.add(u)
    db.commit()
    db.refresh(u)
    return {"id": u.id, "email": u.email, "plan": u.plan}

@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == body.email).first()
    if not u or not verify_password(body.password, u.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token(u.email)
    return TokenOut(access_token=token)

def get_current_user_from_header(Authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> User:
    if not Authorization or not Authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = Authorization.split(" ", 1)[1]
    payload = decode_token(token)
    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
