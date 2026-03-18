"""Legacy YooKassa client — kept for backward compatibility.

New code should use::

    from app.services.payment_providers import get_provider
"""

from app.services.payment_providers.yookassa_client import (  # noqa: F401
    YooKassaPaymentProvider as YooKassaClient,
)
