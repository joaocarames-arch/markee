"""Stripe billing integration with subscription-tier enforcement.

Every network call degrades gracefully to a mock response when Stripe is not
configured, so the billing flow can be exercised end-to-end in development.
"""
from __future__ import annotations

import logging
from typing import Any

import stripe

from app.core.config import settings

logger = logging.getLogger(__name__)

# Plan limits aligned with the pricing tiers in CLAUDE.md.
PLAN_LIMITS: dict[str, dict[str, Any]] = {
    "free": {"max_marks": 1, "max_users": 1, "max_clients": 0, "features": {}},
    "individual": {"max_marks": 5, "max_users": 1, "max_clients": 0, "features": {}},
    "pro": {
        "max_marks": 100,
        "max_users": 5,
        "max_clients": 0,
        "features": {"import_csv": True, "pdf_reports": True, "telegram_alerts": True},
    },
    "profissional": {
        "max_marks": 500,
        "max_users": 20,
        "max_clients": 100,
        "features": {
            "import_csv": True,
            "pdf_reports": True,
            "telegram_alerts": True,
            "prospection": True,
            "white_label": True,
        },
    },
    "enterprise": {
        "max_marks": 999999,
        "max_users": 999999,
        "max_clients": 999999,
        "features": {
            "import_csv": True,
            "pdf_reports": True,
            "telegram_alerts": True,
            "prospection": True,
            "white_label": True,
            "api_keys": True,
            "sso": True,
        },
    },
}

PLAN_PRICES: dict[str, str] = {
    "individual": settings.STRIPE_PRICE_INDIVIDUAL,
    "pro": settings.STRIPE_PRICE_PRO,
    "profissional": settings.STRIPE_PRICE_PROFISSIONAL,
    "enterprise": settings.STRIPE_PRICE_ENTERPRISE,
}


class BillingService:
    """Manage Stripe customers, checkout sessions, portals and webhooks."""

    def __init__(self, stripe_secret_key: str = "", webhook_secret: str = "") -> None:
        """Initialise the service and configure the Stripe SDK.

        Args:
            stripe_secret_key: Stripe secret key (falls back to settings).
            webhook_secret: Stripe webhook signing secret (falls back to settings).
        """
        stripe.api_key = stripe_secret_key or settings.STRIPE_SECRET_KEY
        self.webhook_secret = webhook_secret or settings.STRIPE_WEBHOOK_SECRET

    @property
    def configured(self) -> bool:
        """Whether a Stripe API key is available."""
        return bool(stripe.api_key)

    async def create_customer(self, email: str, name: str) -> str:
        """Create a Stripe customer.

        Args:
            email: Customer email.
            name: Customer display name.

        Returns:
            The Stripe customer id (a mock id when Stripe is not configured).
        """
        if not self.configured:
            logger.warning("Stripe not configured; returning mock customer")
            slug = email.replace("@", "_").replace(".", "_")
            return f"cus_mock_{slug}"
        customer = stripe.Customer.create(email=email, name=name)
        return customer["id"]

    async def create_checkout_session(
        self,
        customer_id: str,
        plan: str,
        success_url: str,
        cancel_url: str,
    ) -> dict[str, Any]:
        """Create a Stripe Checkout session for a subscription plan.

        Args:
            customer_id: The Stripe customer id.
            plan: The plan key (must be present in :data:`PLAN_PRICES`).
            success_url: Redirect URL on success.
            cancel_url: Redirect URL on cancel.

        Returns:
            The Checkout session as a dict.

        Raises:
            ValueError: If the plan has no configured price.
        """
        if not self.configured:
            logger.warning("Stripe not configured; returning mock checkout session")
            return {"id": "cs_mock_123", "url": success_url, "status": "open"}

        price_id = PLAN_PRICES.get(plan)
        if not price_id:
            raise ValueError(f"Invalid plan: {plan}")

        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return dict(session)

    async def create_customer_portal(self, customer_id: str, return_url: str) -> str:
        """Create a Stripe Customer Portal session.

        Args:
            customer_id: The Stripe customer id.
            return_url: URL to return to after the portal session.

        Returns:
            The portal session URL (the return URL when Stripe is not configured).
        """
        if not self.configured:
            logger.warning("Stripe not configured; returning mock portal URL")
            return return_url
        session = stripe.billing_portal.Session.create(
            customer=customer_id, return_url=return_url
        )
        return session["url"]

    async def handle_webhook(
        self, payload: bytes, sig_header: str
    ) -> dict[str, Any] | None:
        """Verify and interpret a Stripe webhook event.

        Args:
            payload: The raw request body.
            sig_header: The ``Stripe-Signature`` header value.

        Returns:
            A dict with ``type`` and ``object`` keys, or ``None`` when the
            signature is invalid or Stripe is not configured.
        """
        if not self.configured:
            logger.warning("Stripe not configured; webhook skipped")
            return None
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
        except (stripe.error.SignatureVerificationError, ValueError):
            logger.error("Invalid Stripe webhook signature")
            return None

        event_type = event.get("type")
        data = event.get("data", {}).get("object", {})

        if event_type == "checkout.session.completed":
            logger.info("Checkout completed for customer %s", data.get("customer"))
        elif event_type == "invoice.paid":
            logger.info("Invoice paid: %s", data.get("id"))
        elif event_type == "invoice.payment_failed":
            logger.warning("Invoice payment failed: %s", data.get("id"))
        elif event_type == "customer.subscription.updated":
            logger.info("Subscription updated: %s", data.get("id"))
        elif event_type == "customer.subscription.deleted":
            logger.info("Subscription cancelled: %s", data.get("id"))

        return {"type": event_type, "object": data}

    async def cancel_subscription(self, subscription_id: str) -> bool:
        """Schedule a subscription to cancel at the end of the period.

        Args:
            subscription_id: The Stripe subscription id.

        Returns:
            ``True`` on success.
        """
        if not self.configured:
            logger.warning("Stripe not configured; mock cancel")
            return True
        stripe.Subscription.modify(subscription_id, cancel_at_period_end=True)
        return True

    @staticmethod
    def get_plan_limits(plan_type: str) -> dict[str, Any]:
        """Return the limits/features for a plan (defaults to free).

        Args:
            plan_type: The plan key.

        Returns:
            The plan's limit/feature dict.
        """
        return PLAN_LIMITS.get(plan_type, PLAN_LIMITS["free"])

    @staticmethod
    def can_add_mark(current_count: int, plan_type: str) -> bool:
        """Return whether another mark can be added under a plan's quota.

        Args:
            current_count: Number of marks currently used.
            plan_type: The plan key.

        Returns:
            ``True`` if under the quota.
        """
        limits = PLAN_LIMITS.get(plan_type, PLAN_LIMITS["free"])
        return current_count < limits["max_marks"]

    @staticmethod
    def enforce_tier(feature: str, plan_type: str) -> bool:
        """Return whether a feature flag is enabled for a plan.

        Args:
            feature: The feature key.
            plan_type: The plan key.

        Returns:
            ``True`` if the feature is available.
        """
        limits = PLAN_LIMITS.get(plan_type, PLAN_LIMITS["free"])
        return bool(limits.get("features", {}).get(feature, False))
