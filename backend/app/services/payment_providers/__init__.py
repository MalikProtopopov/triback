"""Payment provider factory and public re-exports."""

from app.core.config import settings
from app.core.enums import PaymentProviderEnum
from app.services.payment_providers.base import (
    CreatePaymentResult,
    PaymentItem,
    PaymentProvider,
    RefundResult,
    WebhookData,
)

__all__ = [
    "CreatePaymentResult",
    "PaymentItem",
    "PaymentProvider",
    "RefundResult",
    "WebhookData",
    "get_provider",
]


def get_provider() -> PaymentProvider:
    """Return the active payment provider based on settings."""
    provider = settings.PAYMENT_PROVIDER
    if provider == PaymentProviderEnum.YOOKASSA:
        from app.services.payment_providers.yookassa_client import YooKassaPaymentProvider

        return YooKassaPaymentProvider()
    if provider == PaymentProviderEnum.MONETA:
        from app.services.payment_providers.moneta_client import MonetaPaymentProvider

        return MonetaPaymentProvider()
    raise ValueError(f"Unknown payment provider: {provider}")
