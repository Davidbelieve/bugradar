"""
stripe_routes.py  —  Stripe subscription flow for BugOracle.

Mount in main.py:
    from stripe_routes import router as stripe_router
    app.include_router(stripe_router, prefix="/billing", tags=["billing"])

Required environment variables:
    STRIPE_SECRET_KEY       sk_live_...
    STRIPE_WEBHOOK_SECRET   whsec_...
    STRIPE_PRO_PRICE_ID     price_...
    FRONTEND_URL            https://bugradar-ndzbc3bxka4pncmxarf2rn.streamlit.app
"""

import os
import stripe
from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text as _text

from database import _engine
from auth import get_current_user

router = APIRouter()

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
PRO_PRICE_ID   = os.environ.get("STRIPE_PRO_PRICE_ID")
FRONTEND_URL   = os.environ.get("FRONTEND_URL", "http://localhost:8501")


# ─────────────────────────────────────────────
# POST /billing/subscribe
# ─────────────────────────────────────────────

@router.post("/subscribe")
def create_checkout_session(current_user: dict = Depends(get_current_user)):
    user_id  = int(current_user["sub"])
    email    = current_user.get("email") or ""
    username = current_user.get("username", "user")

    with _engine.connect() as conn:
        row = conn.execute(
            _text("SELECT stripe_customer_id FROM users WHERE id = :uid"),
            {"uid": user_id}
        ).fetchone()

    stripe_customer_id = row[0] if row and row[0] else None

    if not stripe_customer_id:
        customer = stripe.Customer.create(
            email=email,
            name=username,
            metadata={"bugoracle_user_id": str(user_id)},
        )
        stripe_customer_id = customer.id
        with _engine.connect() as conn:
            conn.execute(
                _text("UPDATE users SET stripe_customer_id = :cid WHERE id = :uid"),
                {"cid": stripe_customer_id, "uid": user_id}
            )
            conn.commit()

    try:
        session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{"price": PRO_PRICE_ID, "quantity": 1}],
            mode="subscription",
            success_url=f"{FRONTEND_URL}?upgrade=success",
            cancel_url=f"{FRONTEND_URL}?upgrade=cancelled",
            metadata={"bugoracle_user_id": str(user_id)},
        )
        return {"checkout_url": session.url}
    except stripe.error.StripeError as e:
        raise HTTPException(status_code=502, detail=f"Stripe error: {str(e)}")


# ─────────────────────────────────────────────
# POST /billing/webhook
# ─────────────────────────────────────────────

@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload    = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {str(e)}")

    event_type = event["type"]
    data       = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user_id         = data.get("metadata", {}).get("bugoracle_user_id")
        subscription_id = data.get("subscription")
        if user_id:
            with _engine.connect() as conn:
                conn.execute(
                    _text("UPDATE users SET tier = 'pro', stripe_subscription_id = :sid WHERE id = :uid"),
                    {"sid": subscription_id, "uid": int(user_id)}
                )
                conn.commit()

    elif event_type == "customer.subscription.deleted":
        subscription_id = data.get("id")
        if subscription_id:
            with _engine.connect() as conn:
                conn.execute(
                    _text("UPDATE users SET tier = 'free', stripe_subscription_id = NULL WHERE stripe_subscription_id = :sid"),
                    {"sid": subscription_id}
                )
                conn.commit()

    return JSONResponse(content={"received": True})


# ─────────────────────────────────────────────
# GET /billing/status
# ─────────────────────────────────────────────

@router.get("/status")
def billing_status(current_user: dict = Depends(get_current_user)):
    with _engine.connect() as conn:
        row = conn.execute(
            _text("SELECT tier, stripe_customer_id, stripe_subscription_id FROM users WHERE id = :uid"),
            {"uid": int(current_user["sub"])}
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    tier, customer_id, subscription_id = row
    return {
        "tier": tier,
        "is_pro": tier == "pro",
        "has_stripe_customer": bool(customer_id),
        "subscription_active": bool(subscription_id),
    }
