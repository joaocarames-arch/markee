"""Billing router — Stripe checkout, webhooks and subscription state."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.api.common import ORMModel, StrId
from app.core.config import settings
from app.models.database import get_db
from app.models.subscription import Subscription
from app.models.user import User
from app.services.billing import PLAN_LIMITS, BillingService

router = APIRouter(prefix="/billing", tags=["billing"])

billing_service = BillingService()


class CheckoutPayload(BaseModel):
    """Payload for starting a Stripe Checkout session."""

    plan: str
    success_url: str = settings.APP_BASE_URL
    cancel_url: str = settings.APP_BASE_URL


class SubscriptionOut(ORMModel):
    """Public representation of a subscription."""

    id: StrId
    user_id: StrId
    plan_type: str
    status: str
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    max_marks: int
    max_users: int
    max_clients: int
    features: dict[str, Any] | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None


@router.get("/subscription", response_model=SubscriptionOut)
async def get_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubscriptionOut:
    """Return the current user's subscription, defaulting to the free plan."""
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    subscription = result.scalar_one_or_none()
    if subscription is None:
        return SubscriptionOut(
            id="free",
            user_id=str(current_user.id),
            plan_type="free",
            status="active",
            max_marks=1,
            max_users=1,
            max_clients=0,
            features={},
        )
    return SubscriptionOut.model_validate(subscription)


@router.post("/checkout")
async def create_checkout(
    payload: CheckoutPayload,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str | None]:
    """Create a Stripe Checkout session for a plan upgrade.

    Raises:
        HTTPException: 400 if the requested plan is unknown.
    """
    if payload.plan not in PLAN_LIMITS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid plan"
        )

    result = await db.execute(
        select(Subscription).where(Subscription.user_id == current_user.id)
    )
    subscription = result.scalar_one_or_none()
    customer_id = subscription.stripe_customer_id if subscription else None

    if not customer_id:
        customer_id = await billing_service.create_customer(
            current_user.email, current_user.full_name or current_user.email
        )
        if subscription is None:
            subscription = Subscription(
                user_id=current_user.id,
                plan_type="free",
                stripe_customer_id=customer_id,
            )
            db.add(subscription)
        else:
            subscription.stripe_customer_id = customer_id
        await db.commit()

    session = await billing_service.create_checkout_session(
        customer_id=customer_id,
        plan=payload.plan,
        success_url=payload.success_url,
        cancel_url=payload.cancel_url,
    )
    return {"checkout_url": session.get("url")}


@router.post("/webhook")
async def stripe_webhook(
    request: Request, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """Handle Stripe webhook callbacks.

    Raises:
        HTTPException: 400 if the webhook payload/signature is invalid.
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    event = await billing_service.handle_webhook(payload, sig_header)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook"
        )

    data = event.get("object", {})
    if event.get("type") == "checkout.session.completed":
        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_customer_id == data.get("customer")
            )
        )
        subscription = result.scalar_one_or_none()
        if subscription is not None:
            subscription.status = "active"
            subscription.stripe_subscription_id = data.get("subscription")
            await db.commit()

    return {"status": "ok"}


@router.get("/plans")
async def list_plans() -> dict[str, Any]:
    """Return the catalogue of available plans and their limits."""
    return PLAN_LIMITS
