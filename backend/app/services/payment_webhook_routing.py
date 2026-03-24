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
    """Коды ответа Check URL согласно документации MONETA.Assistant (Глава 5).

    100 — вернуть сумму заказа (когда MNT_AMOUNT не был передан в запросе)
    200 — заказ уже оплачен, уведомление доставлено
    302 — заказ в обработке
    402 — заказ создан и ГОТОВ К ОПЛАТЕ (использовать для pending-заказов)
    500 — заказ не актуален (отменён/не найден)

    Примечание из документации: «В обычных случаях для продолжения процесса
    оплаты следует использовать код ответа 402 или 100.»
    """

    AMOUNT_REQUIRED = "100"   # MNT_AMOUNT не пришёл — вернуть сумму
    ALREADY_PAID = "200"       # заказ уже оплачен
    IN_PROGRESS = "302"        # в обработке
    READY_FOR_PAYMENT = "402"  # заказ готов к оплате (pending)
    NOT_RELEVANT = "500"       # заказ не актуален / не найден

    # Обратная совместимость
    OK = ALREADY_PAID
    NOT_FOUND_OR_UNAVAILABLE = READY_FOR_PAYMENT
    INVALID_SIGNATURE_OR_AMOUNT_MISMATCH = NOT_RELEVANT


# ---------------------------------------------------------------------------
# Идемпотентность YooKassa webhook (Redis)
# ---------------------------------------------------------------------------
YOOKASSA_WEBHOOK_DEDUP_KEY_PREFIX = "webhook:dedup:"
YOOKASSA_WEBHOOK_DEDUP_TTL_SECONDS = 86400
