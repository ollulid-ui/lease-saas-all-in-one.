import os
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models import User, FileUpload, UsageMonth
from ..settings import settings
from .auth import get_current_user_from_header

router = APIRouter(prefix="/upload", tags=["upload"])

def _yyyymm(dt: datetime) -> str:
    return dt.strftime("%Y-%m")

def _plan_quota_mb(plan: str) -> int:
    return settings.MAX_UPLOAD_MB_PRO if plan == "pro" else settings.MAX_UPLOAD_MB_FREE

@router.post("")
async def upload_file(
    f: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user_from_header)
):
    # file size enforcement - in-memory stream size might be unknown; we write to disk and check size
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    user_dir = os.path.join(settings.UPLOAD_DIR, f"user_{user.id}")
    os.makedirs(user_dir, exist_ok=True)

    temp_path = os.path.join(user_dir, f"tmp_{datetime.utcnow().timestamp()}_{f.filename}")
    with open(temp_path, "wb") as out:
        content = await f.read()
        out.write(content)
    size_bytes = os.path.getsize(temp_path)

    max_file_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if size_bytes > max_file_bytes:
        os.remove(temp_path)
        raise HTTPException(status_code=400, detail=f"File exceeds max size of {settings.MAX_FILE_SIZE_MB} MB")

    # quota accounting
    now = datetime.utcnow()
    yyyymm = _yyyymm(now)
    usage = db.query(UsageMonth).filter(UsageMonth.user_id == user.id, UsageMonth.yyyymm == yyyymm).first()
    if not usage:
        usage = UsageMonth(user_id=user.id, yyyymm=yyyymm, bytes_used=0)
        db.add(usage)
        db.commit()
        db.refresh(usage)

    quota_mb = _plan_quota_mb(user.plan)
    quota_bytes = quota_mb * 1024 * 1024
    if usage.bytes_used + size_bytes > quota_bytes:
        os.remove(temp_path)
        raise HTTPException(status_code=402, detail="Monthly quota exceeded")

    # move to final path
    final_path = os.path.join(user_dir, f.filename)
    # handle collision
    base, ext = os.path.splitext(final_path)
    idx = 1
    while os.path.exists(final_path):
        final_path = f"{base}({idx}){ext}"
        idx += 1

    os.replace(temp_path, final_path)

    rec = FileUpload(user_id=user.id, filename=os.path.basename(final_path), size_bytes=size_bytes)
    usage.bytes_used += size_bytes
    db.add(rec)
    db.add(usage)
    db.commit()
    return {"filename": rec.filename, "size_bytes": rec.size_bytes, "yyyymm": yyyymm, "quota_mb": quota_mb}
