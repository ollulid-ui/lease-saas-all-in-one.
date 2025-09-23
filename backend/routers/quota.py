from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from ..core.database import get_db
from ..models import UsageMonth, User
from .auth import get_current_user_from_header
from ..settings import settings

router = APIRouter(prefix="/quota", tags=["quota"])

def _yyyymm(dt: datetime) -> str:
    return dt.strftime("%Y-%m")

@router.get("")
def get_quota(db: Session = Depends(get_db), user: User = Depends(get_current_user_from_header)):
    yyyymm = _yyyymm(datetime.utcnow())
    usage = db.query(UsageMonth).filter(UsageMonth.user_id == user.id, UsageMonth.yyyymm == yyyymm).first()
    used = usage.bytes_used if usage else 0
    max_mb = settings.MAX_UPLOAD_MB_PRO if user.plan == "pro" else settings.MAX_UPLOAD_MB_FREE
    return {"plan": user.plan, "used_bytes": used, "max_bytes": max_mb * 1024 * 1024, "yyyymm": yyyymm}
