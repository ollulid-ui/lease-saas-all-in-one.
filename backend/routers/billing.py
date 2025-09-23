import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..models import User
from ..settings import settings
from .auth import get_current_user_from_header

router = APIRouter(prefix="/billing", tags=["billing"])

@router.on_event("startup")
def _init_stripe():
    if settings.STRIPE_API_KEY:
        stripe.api_key = settings.STRIPE_API_KEY

@router.post("/create-checkout-session")
def create_checkout_session(db: Session = Depends(get_db), user: User = Depends(get_current_user_from_header)):
    if not settings.STRIPE_PRICE_ID_PRO or not settings.STRIPE_SUCCESS_URL or not settings.STRIPE_CANCEL_URL:
        raise HTTPException(status_code=500, detail="Stripe is not configured")
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": settings.STRIPE_PRICE_ID_PRO, "quantity": 1}],
        success_url=settings.STRIPE_SUCCESS_URL,
        cancel_url=settings.STRIPE_CANCEL_URL,
        customer_email=user.email
    )
    return {"checkout_url": session.url}

@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", None)
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Stripe webhook not configured")
    try:
        event = stripe.Webhook.construct_event(payload, sig, settings.STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Basic handling: when subscription created/active, set plan=pro for the customer email
    if event["type"] in ("checkout.session.completed", "customer.subscription.created", "customer.subscription.updated"):
        data = event["data"]["object"]
        email = data.get("customer_details", {}).get("email") or data.get("customer_email")
        if email:
            user = db.query(User).filter(User.email == email).first()
            if user:
                user.plan = "pro"
                db.add(user)
                db.commit()
    if event["type"] in ("customer.subscription.deleted", "invoice.payment_failed"):
        data = event["data"]["object"]
        customer_id = data.get("customer") if isinstance(data, dict) else None
        # Fallback: downgrade all users with unknown failures (simple example)
        # In real apps, map customer_id <-> user in DB
        # Here we skip for simplicity.
    return {"status": "ok"}
