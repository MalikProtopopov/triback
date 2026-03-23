"""Backward-compatible imports for subscription + payment facade."""

from app.services.payment_providers import get_provider
from app.services.subscriptions.subscription_service import SubscriptionService

__all__ = ["SubscriptionService", "get_provider"]
