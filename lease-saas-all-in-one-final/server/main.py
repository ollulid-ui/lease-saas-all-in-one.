import os, io
from typing import Optional
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import stripe

from utils.db import Base, engine, get_db, User, APIKey, Lease
from utils.auth import hash_password, verify_password, create_token, decode_token
from utils.ratelimit import get_limiter
from utils.pdf import extract_text_from_pdf

load_dotenv()
if os.getenv("GEMINI_API_KEY"): os.environ["GOOGLE_API_KEY"] = os.getenv("GEMINI_API_KEY")

PLAN_LIMITS = {"starter": 10, "pro": 30, "enterprise": 200}
PLAN_RPM = {"starter": 10, "pro": 60, "enterprise": 180}

stripe.api_key = os.getenv("STRIPE_SECRET_KEY") or None
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
BILLING_SUCCESS_URL = os.getenv("BILLING_SUCCESS_URL","http://localhost:8000")
BILLING_CANCEL_URL = os.getenv("BILLING_CANCEL_URL","http://localhost:8000")

app = FastAPI(title="Lease SaaS API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True)

class AuthPayload(BaseModel):
    email: str
    password: str

def auth_user(db: Session, authorization: Optional[str]) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ",1)[1]
    data = decode_token(token)
    uid = int(data["sub"])
    u = db.query(User).filter(User.id == uid).first()
    if not u: raise HTTPException(status_code=401, detail="User not found")
    return u

def ensure_month_window(rec: APIKey):
    now = datetime.utcnow()
    if not rec.last_reset or (rec.last_reset.year != now.year or rec.last_reset.month != now.month):
        rec.usage_count = 0; rec.last_reset = now

def allowed_monthly_limit(rec: APIKey) -> int:
    return rec.monthly_limit if rec.monthly_limit is not None else PLAN_LIMITS.get(rec.plan, PLAN_LIMITS["starter"])

def plan_rpm(rec: APIKey) -> int:
    return PLAN_RPM.get(rec.plan, PLAN_RPM["starter"])

@app.on_event("startup")
def _startup():
    Base.metadata.create_all(bind=engine)
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator().instrument(app).expose(app, include_in_schema=False, endpoint="/metrics")
    except Exception:
        pass

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/auth/signup")
def signup(payload: AuthPayload, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    u = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(u); db.commit(); db.refresh(u)
    key = "sk_" + os.urandom(16).hex()
    k = APIKey(user_id=u.id, key=key, plan="starter", active=True)
    db.add(k); db.commit()
    return {"token": create_token(u.id, u.email)}

@app.post("/auth/login")
def login(payload: AuthPayload, db: Session = Depends(get_db)):
    u = db.query(User).filter(User.email == payload.email).first()
    if not u or not verify_password(payload.password, u.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": create_token(u.id, u.email)}

@app.get("/api/quota")
def quota(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    u = auth_user(db, authorization)
    k = db.query(APIKey).filter(APIKey.user_id == u.id, APIKey.active == True).first()
    if not k: raise HTTPException(status_code=404, detail="No active API key")
    ensure_month_window(k); db.add(k); db.commit()
    return {"used": k.usage_count, "limit": allowed_monthly_limit(k), "plan": k.plan}

@app.post("/api/upload")
def upload(file: UploadFile = File(...), authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    u = auth_user(db, authorization)
    k = db.query(APIKey).filter(APIKey.user_id == u.id, APIKey.active == True).first()
    if not k: raise HTTPException(status_code=404, detail="No active API key")
    ensure_month_window(k)
    if k.usage_count >= allowed_monthly_limit(k):
        raise HTTPException(status_code=402, detail="Monthly quota exceeded")
    limiter = get_limiter(db); limiter.check(k.key, plan_rpm(k))

    content = file.file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (20MB limit)")
    text = ""; excerpt = ""
    try:
        if file.filename.lower().endswith(".pdf"):
            text, excerpt = extract_text_from_pdf(io.BytesIO(content))
        else:
            text = content.decode(errors="ignore"); excerpt = text[:2000]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unable to parse file: {e}")

    try:
        import langextract as lx
        prompt = ("Extract the following lease fields and return valid JSON with keys: "
                  "tenant_name, landlord_name, property_address, rent_amount, lease_term_years, "
                  "renewal_options, escalation_clauses, termination_clauses. "
                  "Set missing fields to null. Use numeric types for numbers. No extra keys.")
        result = lx.extract(text_or_documents=text, prompt_description=prompt, model_id="gemini-2.5-pro")
    except Exception as e:
        result = {"tenant_name": None, "landlord_name": None, "property_address": None, "rent_amount": None,
                  "lease_term_years": None, "renewal_options": None, "escalation_clauses": None, "termination_clauses": None,
                  "_note": f"LangExtract failed: {e}"}

    lease = Lease(user_id=u.id, filename=file.filename, text_excerpt=excerpt, json_result=result)
    db.add(lease); k.usage_count += 1; db.add(k); db.commit(); db.refresh(lease)
    return {"id": lease.id, "result": result}

@app.get("/api/history")
def history(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    u = auth_user(db, authorization)
    rows = db.query(Lease).filter(Lease.user_id == u.id).order_by(Lease.created_at.desc()).limit(50).all()
    return {"items": [{
        "id": r.id, "filename": r.filename, "created_at": r.created_at.isoformat(),
        "tenant_name": (r.json_result or {}).get("tenant_name"),
        "rent_amount": (r.json_result or {}).get("rent_amount"),
        "lease_term_years": (r.json_result or {}).get("lease_term_years")
    } for r in rows]}

@app.get("/api/lease/{lease_id}")
def get_lease(lease_id: int, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    u = auth_user(db, authorization)
    r = db.query(Lease).filter(Lease.id == lease_id, Lease.user_id == u.id).first()
    if not r: raise HTTPException(status_code=404, detail="Not found")
    return {"id": r.id, "filename": r.filename, "created_at": r.created_at.isoformat(), "result": r.json_result}

# Stripe
@app.post("/billing/create-checkout-session")
def create_checkout(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    u = auth_user(db, authorization)
    if not (stripe.api_key and STRIPE_PRICE_ID): return {"checkout_url": None, "message": "Stripe not configured"}
    session = stripe.checkout.Session.create(mode="subscription",
        success_url=BILLING_SUCCESS_URL, cancel_url=BILLING_CANCEL_URL,
        customer_email=u.email, line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}], allow_promotion_codes=True)
    return {"checkout_url": session.url}

@app.post("/billing/portal-session")
def portal(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    u = auth_user(db, authorization)
    if not stripe.api_key: return {"portal_url": None, "message": "Stripe not configured"}
    customers = stripe.Customer.list(email=u.email, limit=1)
    if not customers.data: raise HTTPException(status_code=404, detail="No Stripe customer for this email")
    sess = stripe.billing_portal.Session.create(customer=customers.data[0].id, return_url=BILLING_SUCCESS_URL)
    return {"portal_url": sess.url}

@app.post("/stripe/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    if not STRIPE_WEBHOOK_SECRET: return {"status":"ignored"}
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(payload=payload, sig_header=sig, secret=STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook signature verification failed: {e}")
    # Minimal handling as earlier
    return {"status":"ok"}
