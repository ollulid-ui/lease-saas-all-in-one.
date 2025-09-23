import os, jwt
from datetime import datetime, timedelta
from passlib.hash import bcrypt
from sqlalchemy.orm import Session
from utils.db import User
from fastapi import HTTPException

JWT_SECRET = os.getenv("JWT_SECRET", "changeme")

def hash_password(pw: str) -> str:
    return bcrypt.hash(pw)

def verify_password(pw: str, hashed: str) -> bool:
    return bcrypt.verify(pw, hashed)

def create_token(user_id: int, email: str) -> str:
    payload = {"sub": str(user_id), "email": email, "exp": datetime.utcnow() + timedelta(days=7)}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
