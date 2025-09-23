import os
from datetime import datetime
from sqlalchemy.orm import Session
from utils.db import RateLimit
from fastapi import HTTPException
try:
    import redis  # type: ignore
except Exception:
    redis = None

BACKEND = os.getenv("RATE_LIMIT_BACKEND","db")
REDIS_URL = os.getenv("REDIS_URL","redis://localhost:6379/0")

class DBRateLimiter:
    def __init__(self, db: Session): self.db = db
    def check(self, key: str, rpm: int):
        now = datetime.utcnow().replace(second=0, microsecond=0)
        row = self.db.query(RateLimit).filter_by(key=key, window_start=now).first()
        if not row:
            row = RateLimit(key=key, window_start=now, count=0)
            self.db.add(row); 
            try: self.db.commit()
            except: self.db.rollback(); row = self.db.query(RateLimit).filter_by(key=key, window_start=now).first()
        if row.count >= rpm:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        row.count += 1; self.db.add(row); self.db.commit()

class RedisRateLimiter:
    def __init__(self):
        if redis is None: raise RuntimeError("redis lib not installed")
        self.r = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    def check(self, key: str, rpm: int):
        now = datetime.utcnow().strftime("%Y%m%d%H%M")
        rkey = f"rl:{key}:{now}"
        c = self.r.incr(rkey)
        if c == 1: self.r.expire(rkey, 90)
        if c > rpm: raise HTTPException(status_code=429, detail="Rate limit exceeded")

def get_limiter(db: Session):
    if BACKEND == "redis": return RedisRateLimiter()
    return DBRateLimiter(db)
