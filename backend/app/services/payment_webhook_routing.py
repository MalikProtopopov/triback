"""Справочник маршрутизации платёжных webhooks (YooKassa + Moneta).

Единая точка для имён событий и кодов ответов; сами обработчики остаются в
``PaymentWebhookService`` и в ``app.api.v1.webhooks``.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# YooKassa — поле JSON `event` (тело webhook от ЮKassa)
# ---------------------------------------------------------------------------
YOOKASSA_WEBHOOK_EVENTS_HANDLED = frozenset({
    "payment.succeeded",
    "payment.canceled",
    "refund.succeeded",
})

# ---------------------------------------------------------------------------
# Moneta — Pay URL: MNT_COMMAND (если есть)
# ---------------------------------------------------------------------------
MONETA_PAY_COMMANDS_WITH_SIGNATURE = frozenset({
    "DEBIT",
    "CREDIT",
    "AUTHORISE",
    "CANCELLED_DEBIT",
    "CANCELLED_CREDIT",
})

# ---------------------------------------------------------------------------
# Moneta — Check URL: MNT_RESULT_CODE в XML
# ---------------------------------------------------------------------------
class MonetaCheckResultCode:
    """Коды ответа Check URL (см. docs/MONETA_WEBHOOK_TROUBLESHOOTING.md)."""

    OK = "200"
    NOT_FOUND_OR_UNAVAILABLE = "402"
    INVALID_SIGNATURE_OR_AMOUNT_MISMATCH = "500"


# ---------------------------------------------------------------------------
# Идемпотентность YooKassa webhook (Redis)
# ---------------------------------------------------------------------------
YOOKASSA_WEBHOOK_DEDUP_KEY_PREFIX = "webhook:dedup:"
YOOKASSA_WEBHOOK_DEDUP_TTL_SECONDS = 86400
