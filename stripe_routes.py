"""
stripe_routes.py  —  Stripe subscription flow for BugOracle.

Mount in main.py:
    from stripe_routes import router as stripe_router
    app.include_router(stripe_router, prefix="/billing", tags=["billing"])

Required environment variables (set in Render dashboard):
    STRIPE_SECRET_KEY       — sk_live_... or sk_test_...
    STRIPE_WEBHOOK_SECRET   — whsec_... (from Stripe Dashboard → Webhooks)
    STRIPE_PRO_PRICE_ID     — price_... (your Pro monthly price ID)
    FRONTEND_URL            — e.g. https://bugradar-ndzbc3bxka4pncmxarf2rn.streamlit.app
"""

import os
import stripe
from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import JSONResponse

from auth import get_current_user
from database import get_db_connection

router = APIRouter()

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

WEBHOOK_SECRET  = os.environ.get("STRIPE_WEBHOOK_SECRET")
PRO_PRICE_ID    = os.environ.get("STRIPE_PRO_PRICE_ID")
FRONTEND_URL    = os.environ.get("FRONTEND_URL", "http://localhost:8501")


# ─────────────────────────────────────────────
# POST /billing/subscribe
# Creates a Stripe Checkout session for the Pro tier.
# Returns { checkout_url } — redirect the user to this URL.
# ─────────────────────────────────────────────

@router.post("/subscribe")
def create_checkout_session(current_user: dict = Depends(get_current_user)):
    """
    Creates (or reuses) a Stripe customer for the authenticated user,
    then opens a hosted Checkout session for the Pro plan.
    """
    user_id  = current_user["id"]
    email    = current_user.get("email") or ""
    username = current_user.get("username", "user")

    conn = get_db_connection()
    try:
        # ── 1. Look up or create Stripe customer ──────────────────────────
        with conn.cursor() as cur:
            cur.execute(
                "SELECT stripe_customer_id FROM users WHERE id = %s",
                (user_id,),
            )
            row = cur.fetchone()

        stripe_customer_id = row[0] if row and row[0] else None

        if not stripe_customer_id:
            customer = stripe.Customer.create(
                email=email,
                name=username,
                metadata={"bugoracle_user_id": str(user_id)},
            )
            stripe_customer_id = customer.id

            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET stripe_customer_id = %s WHERE id = %s",
                    (stripe_customer_id, user_id),
                )
            conn.commit()

        # ── 2. Create Checkout session ─────────────────────────────────────
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
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stripe error: {str(e)}",
        )
    finally:
        conn.close()


# ─────────────────────────────────────────────
# POST /billing/webhook
# Stripe calls this endpoint after payment events.
# Must be registered in Stripe Dashboard → Webhooks.
# ─────────────────────────────────────────────

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """
    Handles Stripe webhook events:
      - checkout.session.completed  → upgrade user to Pro
      - customer.subscription.deleted → downgrade user to Free
    """
    payload   = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    # ── Verify the webhook signature ──────────────────────────────────────
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook parse error: {str(e)}")

    event_type = event["type"]
    data       = event["data"]["object"]

    conn = get_db_connection()
    try:
        # ── Payment succeeded: upgrade to Pro ─────────────────────────────
        if event_type == "checkout.session.completed":
            user_id         = data.get("metadata", {}).get("bugoracle_user_id")
            subscription_id = data.get("subscription")

            if user_id:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE users
                        SET tier = 'pro',
                            stripe_subscription_id = %s
                        WHERE id = %s
                        """,
                        (subscription_id, int(user_id)),
                    )
                conn.commit()

        # ── Subscription cancelled: downgrade to Free ─────────────────────
        elif event_type == "customer.subscription.deleted":
            subscription_id = data.get("id")

            if subscription_id:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE users
                        SET tier = 'free',
                            stripe_subscription_id = NULL
                        WHERE stripe_subscription_id = %s
                        """,
                        (subscription_id,),
                    )
                conn.commit()

    finally:
        conn.close()

    return JSONResponse(content={"received": True})


# ─────────────────────────────────────────────
# GET /billing/status
# Returns the current user's tier and subscription info.
# ─────────────────────────────────────────────

@router.get("/status")
def billing_status(current_user: dict = Depends(get_current_user)):
    """
    Returns tier info so the Streamlit dashboard can show
    the upgrade button or Pro badge.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT tier, stripe_customer_id, stripe_subscription_id FROM users WHERE id = %s",
                (current_user["id"],),
            )
            row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        tier, customer_id, subscription_id = row
        return {
            "tier": tier,
            "is_pro": tier == "pro",
            "has_stripe_customer": bool(customer_id),
            "subscription_active": bool(subscription_id),
        }
    finally:
        conn.close()