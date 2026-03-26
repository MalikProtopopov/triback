"""Russian labels for export columns (no SQL)."""

PAYMENT_STATUS_RU: dict[str, str] = {
    "pending": "Ожидает оплаты",
    "succeeded": "Оплачен",
    "failed": "Ошибка оплаты",
    "expired": "Истёк срок",
    "refunded": "Возврат",
    "partially_refunded": "Частичный возврат",
}

PRODUCT_TYPE_RU: dict[str, str] = {
    "subscription": "Членский взнос",
    "entry_fee": "Вступительный взнос",
    "event": "Мероприятие",
    "membership_arrears": "Задолженность",
}

ARREAR_STATUS_RU: dict[str, str] = {
    "open": "Открыта",
    "paid": "Оплачена",
    "cancelled": "Отменена",
    "waived": "Списана",
}

EVENT_REGISTRATION_STATUS_RU: dict[str, str] = {
    "pending": "Ожидает",
    "confirmed": "Подтверждена",
    "cancelled": "Отменена",
}

SUBSCRIPTION_STATUS_RU: dict[str, str] = {
    "active": "Активна",
    "expired": "Истекла",
    "pending_payment": "Ожидает оплаты",
    "cancelled": "Отменена",
}

RECEIPT_STATUS_RU: dict[str, str] = {
    "pending": "Ожидает",
    "succeeded": "Готов",
    "failed": "Ошибка",
}

PLAN_TYPE_RU: dict[str, str] = {
    "subscription": "Членский взнос",
    "entry_fee": "Вступительный взнос",
}

DOCTOR_STATUS_RU: dict[str, str] = {
    "pending_review": "На проверке",
    "approved": "Одобрен",
    "rejected": "Отклонён",
    "active": "Активен",
    "deactivated": "Деактивирован",
}

BOARD_ROLE_RU: dict[str, str] = {
    "pravlenie": "Правление",
    "president": "Президент",
}

PROTOCOL_ACTION_TYPE_RU: dict[str, str] = {
    "admission": "Приём в ассоциацию",
    "exclusion": "Исключение из ассоциации",
}


def ru_payment_status(en: str | None) -> str:
    if not en:
        return ""
    return PAYMENT_STATUS_RU.get(en, en)


def ru_product_type(en: str | None) -> str:
    if not en:
        return ""
    return PRODUCT_TYPE_RU.get(en, en)


def ru_arrear_status(en: str | None) -> str:
    if not en:
        return ""
    return ARREAR_STATUS_RU.get(en, en)


def ru_event_reg_status(en: str | None) -> str:
    if not en:
        return ""
    return EVENT_REGISTRATION_STATUS_RU.get(en, en)


def ru_subscription_status(en: str | None) -> str:
    if not en:
        return ""
    return SUBSCRIPTION_STATUS_RU.get(en, en)


def ru_receipt_status(en: str | None) -> str:
    if not en:
        return ""
    return RECEIPT_STATUS_RU.get(en, en)


def ru_plan_type(en: str | None) -> str:
    if not en:
        return ""
    return PLAN_TYPE_RU.get(en, en)


def ru_doctor_status(en: str | None) -> str:
    if not en:
        return ""
    return DOCTOR_STATUS_RU.get(en, en)


def ru_board_role(en: str | None) -> str:
    if not en:
        return ""
    return BOARD_ROLE_RU.get(en, en)


def ru_protocol_action(en: str | None) -> str:
    if not en:
        return ""
    return PROTOCOL_ACTION_TYPE_RU.get(en, en)
