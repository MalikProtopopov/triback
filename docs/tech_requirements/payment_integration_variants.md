# ТЗ на интеграцию платёжной системы: два варианта реализации
## Проект: «Ассоциация трихологов»

**Версия:** 1.0 | **Дата:** 2026-03-03  
**Статус:** Актуально  
**Текущее решение:** вероятнее всего **ЮKassa** + вывод средств на расчётный счёт в ПСБ. Прямая интеграция ПСБ через **PayKeeper** — на рассмотрении (через PayKeeper отправка чеков).

---

## Исходные данные

| Параметр | Значение |
|----------|----------|
| Тип организации | МОО (НКО), зарегистрирована 01.12.2023 |
| Банк | ПСБ (расчётный счёт уже открыт) |
| Существующая ККТ | ПСБ Касса (офлайн), зарегистрирована в ФНС, договор с ОФД есть |
| Система налогообложения | УСН 6% (требует подтверждения) |
| Ожидаемый оборот | ~4 млн ₽/год (650 тыс. взносы + 3,35 млн мероприятия) |
| Платежи в месяц | 50–200 |
| Дедлайн запуска | Май 2026 |

### Ключевое правило: что требует чека, а что нет

```
┌─────────────────────────────────────┬─────────────────┬──────────────┐
│ Тип платежа                         │ Чек (54-ФЗ)     │ Налог УСН 6% │
├─────────────────────────────────────┼─────────────────┼──────────────┤
│ Вступительный взнос                 │ ❌ НЕ нужен     │ ❌ Не облагается │
│ Ежегодный членский взнос            │ ❌ НЕ нужен     │ ❌ Не облагается │
│ Оплата мероприятия (физлицо)        │ ✅ ОБЯЗАТЕЛЕН   │ ✅ Облагается   │
│ Оплата мероприятия (юрлицо, б/н)   │ ❌ НЕ нужен     │ ✅ Облагается   │
└─────────────────────────────────────┴─────────────────┴──────────────┘

Основание: пп. 1 п. 2 ст. 251 НК РФ, письма Минфина от 08.05.2019 №03-11-11/33481,
от 28.07.2020 №03-01-15/65830. Взносы — целевые поступления НКО, не расчёты по 54-ФЗ.
```

---

## Быстрое сравнение двух вариантов

| Критерий | Вариант 1: ЮKassa | Вариант 2: ПСБ |
|----------|-------------------|----------------|
| **Комиссия (карты)** | ~3,4% эффективная | ~1,5–2,3% |
| **Комиссия (СБП)** | ~2,2% | ~0,4–0,7% |
| **Экономия на оборот 4 млн/год** | Базовый вариант | ~60–80 тыс. ₽/год |
| **Фискализация** | Встроенная (+0,8%) или своя ККТ | Только своя ККТ |
| **Python SDK** | ✅ Официальный | ❌ Нет |
| **Документация API** | ✅ Публичная | ⚠️ Только после договора |
| **Тестовая среда** | ✅ Сразу | После подписания |
| **Срок подключения** | 5–10 дней (НКО) | Непредсказуемо |
| **Сложность интеграции** | Средняя | Высокая |
| **Доп. разработка (ч)** | ~60–80 ч | ~100–130 ч |
| **Риск срыва дедлайна** | Низкий | Средний |
| **Рекомендация при дедлайне май** | ✅ Приоритет | ⚠️ Только если ПСБ подтвердит всё быстро |

---

## Вариант 1: ЮKassa

### 1.1 Обоснование выбора

**Выбирать этот вариант если:**
- Дедлайн май 2026 критичен
- Клиент хочет запустить и не рисковать документацией ПСБ
- Не удаётся быстро получить подтверждение от менеджера ПСБ

**Риски:**
- Возраст организации 1,2 года → проверка может занять до 10 рабочих дней. Документы нужно подавать **немедленно**, не позднее первой недели марта
- При использовании «Чеков от ЮKassa» (+0,8%) и объёме мероприятий 3,35 млн/год дополнительные расходы = ~26 800 ₽/год. Если использовать свою ККТ — эти расходы уходят

**Документы для подключения ЮKassa (МОО):**
1. Устав организации
2. Выписка из ЕГРЮЛ (свежая, до 30 дней)
3. Решение о назначении президента
4. Паспорт президента
5. Реквизиты расчётного счёта в ПСБ

### 1.2 Архитектура платежей

```
┌─────────────┐    POST /api/v1/subscriptions/pay     ┌──────────────┐
│  Фронтенд   │ ─────────────────────────────────────▶ │   FastAPI    │
│  (Next.js)  │   { plan_id, idempotency_key }         │   Backend    │
└─────────────┘                                         └──────┬───────┘
                                                               │
                          1. Валидация бизнес-правил           │
                          2. Создать subscription/registration  │
                          3. Создать payment (pending)          │
                                                               │
                          4. POST /v3/payments → ЮKassa API    │
                                                               ▼
                                                    ┌──────────────────┐
                                                    │   ЮKassa API     │
                                                    │   v3/payments    │
                                                    └────────┬─────────┘
                                                             │
                                        { id, confirmation_url }
                                                             │
              ┌─────────────┐ ◀── redirect URL ─────────────┘
              │  Фронтенд   │ ──── redirect ────▶  ЮKassa Payment Page
              └─────────────┘
                                                        Пользователь платит
                                                               │
              ┌─────────────────┐   POST /webhooks/yookassa   │
              │  ЮKassa Webhook │ ──────────────────────────▶ Backend
              └─────────────────┘
```

### 1.3 Создание платежа

**Конфигурация SDK:**
```python
from yookassa import Configuration, Payment, Refund
from yookassa.domain.notification import WebhookNotificationFactory

Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY
```

**Платёж за взнос (БЕЗ чека):**
```python
import uuid
from decimal import Decimal

async def create_membership_payment(
    internal_payment_id: str,
    amount: Decimal,
    plan_code: str,     # 'entry_fee' или 'annual_fee'
    user_id: str,
    user_email: str,
    subscription_id: str,
    idempotency_key: str,
) -> dict:
    """
    Взносы НКО — целевые поступления по 251 НК РФ.
    Чек по 54-ФЗ НЕ требуется. Объект receipt не передаётся.
    """
    description_map = {
        "entry_fee": "Вступительный взнос — Ассоциация трихологов",
        "annual_fee": "Ежегодный членский взнос — Ассоциация трихологов",
    }

    payment_data = {
        "amount": {
            "value": str(amount),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": f"{settings.FRONTEND_URL}/payment/result?payment_id={internal_payment_id}"
        },
        "capture": True,
        "description": description_map[plan_code],
        "metadata": {
            "internal_payment_id": internal_payment_id,
            "product_type": plan_code,
            "user_id": user_id,
            "subscription_id": subscription_id,
        },
        # receipt НЕ передаётся — взносы не фискализируются
    }

    import anyio
    payment = await anyio.to_thread.run_sync(
        lambda: Payment.create(payment_data, idempotency_key)
    )
    return {
        "external_payment_id": payment.id,
        "payment_url": payment.confirmation.confirmation_url,
        "status": payment.status,
    }
```

**Платёж за мероприятие (С чеком):**
```python
async def create_event_payment(
    internal_payment_id: str,
    amount: Decimal,
    event_title: str,
    tariff_name: str,
    user_id: str,
    fiscal_email: str,           # email для отправки чека
    event_registration_id: str,
    idempotency_key: str,
) -> dict:
    """
    Оплата участия в мероприятии — возмездная услуга.
    Чек по 54-ФЗ ОБЯЗАТЕЛЕН. Передаём объект receipt.
    vat_code = 1 (без НДС) для НКО на УСН.
    """
    payment_data = {
        "amount": {
            "value": str(amount),
            "currency": "RUB"
        },
        "confirmation": {
            "type": "redirect",
            "return_url": f"{settings.FRONTEND_URL}/payment/result?payment_id={internal_payment_id}"
        },
        "capture": True,
        "description": f"Участие в мероприятии «{event_title}» — {tariff_name}",
        "metadata": {
            "internal_payment_id": internal_payment_id,
            "product_type": "event",
            "user_id": user_id,
            "event_registration_id": event_registration_id,
        },
        "receipt": {
            "customer": {
                "email": fiscal_email
            },
            "items": [
                {
                    "description": f"Участие в мероприятии «{event_title}»",
                    "quantity": "1.00",
                    "amount": {
                        "value": str(amount),
                        "currency": "RUB"
                    },
                    "vat_code": 1,               # без НДС (УСН)
                    "payment_mode": "full_payment",
                    "payment_subject": "service",
                }
            ]
        }
    }

    import anyio
    payment = await anyio.to_thread.run_sync(
        lambda: Payment.create(payment_data, idempotency_key)
    )
    return {
        "external_payment_id": payment.id,
        "payment_url": payment.confirmation.confirmation_url,
        "status": payment.status,
    }
```

### 1.4 Обработка webhook

**Endpoint:** `POST /api/v1/webhooks/yookassa`

**Верификация:** ЮKassa не использует HMAC-подписи для уведомлений. Верификация — по IP-адресу отправителя + повторный GET-запрос к API ЮKassa для подтверждения данных.

```python
from yookassa.domain.common import SecurityHelper
from yookassa.domain.notification import WebhookNotificationFactory
from fastapi import Request, HTTPException, Response

YOOKASSA_IPS = [
    "185.71.76.0/27",
    "185.71.77.0/27",
    "77.75.153.0/25",
    "77.75.156.11",
    "77.75.156.35",
]

@router.post("/webhooks/yookassa")
async def handle_yookassa_webhook(request: Request):
    # 1. Проверка IP
    client_ip = request.client.host
    if not SecurityHelper().is_ip_trusted(client_ip):
        raise HTTPException(status_code=403, detail="Untrusted IP")

    body = await request.json()
    notification = WebhookNotificationFactory().create(body)
    payment = notification.object

    # 2. Повторная проверка через API (double-check pattern)
    confirmed = Payment.find_one(payment.id)
    if confirmed.status != body["object"]["status"]:
        raise HTTPException(status_code=400, detail="Status mismatch")

    # 3. Идемпотентность
    existing = await db.payments.find_by_external_id(payment.id)
    if not existing:
        return Response(status_code=200)
    if existing.status == "succeeded":
        return Response(status_code=200)  # уже обработано

    # 4. Диспетчеризация по событию
    if notification.event == "payment.succeeded":
        await process_payment_success(payment, existing)
    elif notification.event == "payment.canceled":
        await process_payment_cancel(payment, existing)
    elif notification.event == "refund.succeeded":
        await process_refund_success(payment, existing)

    return Response(status_code=200)  # Всегда 200 — иначе ЮKassa будет повторять


async def process_payment_success(yk_payment, db_payment):
    async with db.transaction():
        # Обновить платёж
        await db.payments.update(db_payment.id, {
            "status": "succeeded",
            "paid_at": yk_payment.captured_at,
        })

        # Активировать подписку или подтвердить регистрацию
        if db_payment.product_type in ("entry_fee", "annual_fee"):
            await subscription_service.activate(
                subscription_id=db_payment.subscription_id,
                user_id=db_payment.user_id,
            )
        elif db_payment.product_type == "event":
            await event_service.confirm_registration(
                registration_id=db_payment.event_registration_id,
            )
            # Запустить получение чека (только для мероприятий)
            await taskiq.kiq(fetch_and_save_receipt, db_payment.id, yk_payment.id)

    # Сайд-эффекты вне транзакции
    await taskiq.kiq(notify_payment_success, db_payment.user_id, db_payment.id)
    await taskiq.kiq(notify_admins_payment, db_payment.id)
    if db_payment.product_type in ("entry_fee", "annual_fee"):
        await taskiq.kiq(add_to_telegram_channel, db_payment.user_id)
```

### 1.5 Получение и сохранение чека (только для мероприятий)

```python
@broker.task(retry_on_error=True, max_retries=5)
async def fetch_and_save_receipt(internal_payment_id: str, yookassa_payment_id: str):
    """
    Получить фискальные данные от ЮKassa и сохранить в receipts.
    Вызывается только для payment.product_type = 'event'.
    """
    import time

    # ЮKassa может не сразу вернуть чек — ждём
    await asyncio.sleep(5)

    receipts_response = await yookassa_client.get_receipts(yookassa_payment_id)

    if not receipts_response.get("items"):
        raise Exception(f"Receipt not ready yet for payment {yookassa_payment_id}, will retry")

    receipt_data = receipts_response["items"][0]

    if receipt_data["status"] != "succeeded":
        raise Exception(f"Receipt status: {receipt_data['status']}, will retry")

    await db.receipts.create_or_update(internal_payment_id, {
        "provider_receipt_id": receipt_data.get("id"),
        "fiscal_number": receipt_data.get("fiscal_storage_number"),
        "fiscal_document": receipt_data.get("fiscal_document_number"),
        "fiscal_sign": receipt_data.get("fiscal_attribute"),
        "receipt_url": build_receipt_url(receipt_data),
        "receipt_data": receipt_data,
        "amount": receipt_data["amount"]["value"],
        "status": "succeeded",
        "receipt_type": "payment",
    })


def build_receipt_url(receipt_data: dict) -> str:
    fn = receipt_data.get("fiscal_storage_number", "")
    fp = receipt_data.get("fiscal_attribute", "")
    fd = receipt_data.get("fiscal_document_number", "")
    return f"https://receipt.taxcom.ru/v01/show?fn={fn}&fp={fp}&i={fd}"
```

### 1.6 Возврат оплаты за мероприятие

```python
async def refund_event_payment(
    payment_id: str,
    amount: Decimal | None = None,   # None = полный возврат
    fiscal_email: str = None,
) -> dict:
    db_payment = await db.payments.get(payment_id)

    refund_data = {
        "payment_id": db_payment.external_payment_id,
        "amount": {
            "value": str(amount or db_payment.amount),
            "currency": "RUB"
        },
    }

    # При возврате за мероприятие — чек возврата обязателен
    if db_payment.product_type == "event" and fiscal_email:
        refund_data["receipt"] = {
            "customer": {"email": fiscal_email},
            "items": [{
                "description": "Возврат: участие в мероприятии",
                "quantity": "1.00",
                "amount": {
                    "value": str(amount or db_payment.amount),
                    "currency": "RUB"
                },
                "vat_code": 1,
                "payment_mode": "full_payment",
                "payment_subject": "service",
            }]
        }

    import anyio
    refund = await anyio.to_thread.run_sync(
        lambda: Refund.create(refund_data, str(uuid.uuid4()))
    )

    refund_amount = amount or db_payment.amount
    new_status = "refunded" if refund_amount >= db_payment.amount else "partially_refunded"
    await db.payments.update(payment_id, {"status": new_status})

    if db_payment.product_type == "event":
        await db.receipts.create({
            "payment_id": payment_id,
            "receipt_type": "refund",
            "amount": refund_amount,
            "status": "pending",
        })

    return {"refund_id": refund.id, "status": refund.status}
```

### 1.7 Polling-эндпоинт для проверки статуса

```python
@router.get("/payments/{payment_id}/status")
async def get_payment_status(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Используется фронтендом для polling после возврата с платёжной страницы.
    Пользователь видит результат даже если вебхук ещё не пришёл.
    """
    payment = await db.payments.get(payment_id)
    if payment.user_id != current_user.id and "admin" not in current_user.roles:
        raise HTTPException(403)

    # Если статус всё ещё pending — сделать запрос в ЮKassa для актуального статуса
    if payment.status == "pending":
        try:
            yk_payment = Payment.find_one(payment.external_payment_id)
            if yk_payment.status == "succeeded" and payment.status != "succeeded":
                # Вебхук ещё не дошёл — обработать сейчас
                await process_payment_success(yk_payment, payment)
                payment = await db.payments.get(payment_id)
        except Exception:
            pass

    return {
        "payment_id": str(payment_id),
        "status": payment.status,
        "amount": float(payment.amount),
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
    }
```

### 1.8 Отмена просроченных pending-платежей

```python
@broker.task
async def cancel_stale_pending_payments():
    """
    Cron-задача. Раз в час отменяет платежи в статусе pending
    старше 1 часа — пользователь закрыл страницу оплаты.
    """
    stale_payments = await db.payments.find_stale_pending(older_than_minutes=60)

    for payment in stale_payments:
        try:
            Payment.cancel(payment.external_payment_id)
        except Exception:
            pass  # Уже отменён на стороне ЮKassa
        await db.payments.update(payment.id, {"status": "failed"})
```

### 1.9 ENV-переменные (Вариант 1)

```env
PAYMENT_PROVIDER=yookassa

# ЮKassa
YOOKASSA_SHOP_ID=123456
YOOKASSA_SECRET_KEY=test_Fh8h...
YOOKASSA_RETURN_URL=https://trichology.ru/payment/result
YOOKASSA_WEBHOOK_URL=https://api.trichology.ru/api/v1/webhooks/yookassa
YOOKASSA_IP_WHITELIST=185.71.76.0/27,185.71.77.0/27,77.75.153.0/25,77.75.156.11,77.75.156.35

# Фискализация
KKT_PROVIDER=yookassa_builtin
YOOKASSA_VAT_CODE=1
RECEIPT_FETCH_RETRY_COUNT=5
RECEIPT_FETCH_RETRY_DELAY_SEC=30
```

---

## Вариант 2: ПСБ-эквайринг + существующая ККТ

### 2.1 Обоснование выбора

**Выбирать этот вариант если:**
- Менеджер ПСБ подтвердил: МОО работает с интернет-эквайрингом
- Получены конкретные ставки комиссии (~1,5–2,3% по картам, ~0,4% по СБП)
- Существующая ККТ поддерживает API для облачных чеков
- Сроки позволяют +2–3 недели на интеграцию
- Приоритет — экономия ~60–80 тыс. ₽/год на комиссиях

**Три вопроса, которые нужно прояснить с менеджером ПСБ до начала:**
1. Работает ли интернет-эквайринг с МОО (межрегиональная общественная организация)?
2. Какая комиссия для НКО по картам и СБП?
3. Есть ли API документация для разработчиков (хотя бы базовая)?

**Вопрос по ККТ (уточнить у клиента):**
- Какая модель ККТ зарегистрирована в ФНС?
- Поддерживает ли она облачные чеки через API? (Большинство АТОЛ, ШТРИХ, Эвотор — поддерживают)

**Риски:**
- Документация и SDK только после подписания договора — разработка начинается вслепую
- Нет официального Python SDK — вся интеграция на прямых HTTP-запросах
- Сроки подключения непредсказуемы даже при наличии счёта в ПСБ
- Фискализация — отдельная интеграция с API ККТ, дополнительная точка отказа

### 2.2 Архитектура платежей

```
┌─────────────┐    POST /api/v1/subscriptions/pay     ┌──────────────┐
│  Фронтенд   │ ─────────────────────────────────────▶ │   FastAPI    │
│  (Next.js)  │   { plan_id, idempotency_key }         │   Backend    │
└─────────────┘                                         └──────┬───────┘
                                                               │
                    1. Валидация бизнес-правил                  │
                    2. Создать subscription/registration         │
                    3. Создать payment (pending)                 │
                                                               │
                    4. POST ПСБ API → создать заказ            │
                                                               ▼
                                                    ┌──────────────────┐
                                                    │    ПСБ API       │
                                                    │  (эквайринг)     │
                                                    └────────┬─────────┘
                                                             │
                                              { order_id, payment_url }
                                                             │
              ┌─────────────┐ ◀── redirect URL ─────────────┘
              │  Фронтенд   │ ──── redirect ────▶  ПСБ Payment Page
              └─────────────┘
                                                       Пользователь платит
                                                               │
              ┌─────────────────┐   POST /webhooks/psb        │
              │  ПСБ Webhook    │ ──────────────────────────▶ Backend
              └─────────────────┘                              │
                                                               │ (только для мероприятий)
                                                               ▼
                                                    ┌──────────────────┐
                                                    │   API ККТ        │
                                                    │  (АТОЛ/ШТРИХ)    │
                                                    └──────────────────┘
```

### 2.3 HTTP-клиент для ПСБ API

Официального Python SDK нет. Используем `httpx` с async-поддержкой.

```python
import httpx
import hashlib
import hmac
import uuid
from decimal import Decimal

class PSBPaymentClient:
    """
    HTTP-клиент для API ПСБ-эквайринга.
    Конкретные endpoint и формат подписи уточняются по документации ПСБ
    после подписания договора. Ниже — типовая структура для банковских API РФ.
    """

    def __init__(self):
        self.api_url = settings.PSB_API_URL
        self.merchant_id = settings.PSB_MERCHANT_ID
        self.secret_key = settings.PSB_SECRET_KEY

    def _sign_request(self, params: dict) -> str:
        """
        Формирование подписи запроса.
        Точный алгоритм (MD5/SHA256/HMAC) — из документации ПСБ.
        Типовой вариант для РФ-банков: MD5 от конкатенации полей.
        """
        fields_to_sign = sorted(params.items())
        sign_string = "".join(str(v) for _, v in fields_to_sign) + self.secret_key
        return hashlib.md5(sign_string.encode()).hexdigest()

    async def create_payment(
        self,
        order_id: str,
        amount: Decimal,
        description: str,
        return_url: str,
        notify_url: str,
    ) -> dict:
        """
        Создать платёжный заказ в ПСБ.
        Возвращает URL для редиректа пользователя.
        """
        params = {
            "merchant_id": self.merchant_id,
            "order_id": order_id,
            "amount": str(int(amount * 100)),  # в копейках
            "currency": "RUB",
            "description": description,
            "return_url": return_url,
            "notify_url": notify_url,
            "timestamp": str(int(time.time())),
        }
        params["sign"] = self._sign_request(params)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.api_url}/payment/create",
                json=params,
            )
            response.raise_for_status()
            return response.json()

    def verify_webhook_signature(self, body: dict, received_sign: str) -> bool:
        """
        Верификация подписи входящего webhook от ПСБ.
        """
        body_without_sign = {k: v for k, v in body.items() if k != "sign"}
        expected_sign = self._sign_request(body_without_sign)
        return hmac.compare_digest(expected_sign, received_sign)

    async def get_order_status(self, order_id: str) -> dict:
        """
        Запросить статус заказа в ПСБ.
        Используется для polling и сверки после webhook.
        """
        params = {
            "merchant_id": self.merchant_id,
            "order_id": order_id,
            "timestamp": str(int(time.time())),
        }
        params["sign"] = self._sign_request(params)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.api_url}/payment/status",
                json=params,
            )
            response.raise_for_status()
            return response.json()

    async def refund(self, order_id: str, amount: Decimal) -> dict:
        params = {
            "merchant_id": self.merchant_id,
            "order_id": order_id,
            "amount": str(int(amount * 100)),
            "timestamp": str(int(time.time())),
        }
        params["sign"] = self._sign_request(params)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self.api_url}/payment/refund", json=params)
            response.raise_for_status()
            return response.json()
```

### 2.4 Создание платежей

```python
async def create_psb_membership_payment(
    internal_payment_id: str,
    amount: Decimal,
    plan_code: str,
    user_id: str,
    idempotency_key: str,
) -> dict:
    """
    Взносы НКО — чек НЕ нужен. Просто создаём платёжный заказ.
    """
    psb_client = PSBPaymentClient()

    description_map = {
        "entry_fee": "Вступительный взнос — Ассоциация трихологов",
        "annual_fee": "Ежегодный членский взнос — Ассоциация трихологов",
    }

    result = await psb_client.create_payment(
        order_id=internal_payment_id,
        amount=amount,
        description=description_map[plan_code],
        return_url=f"{settings.FRONTEND_URL}/payment/result?payment_id={internal_payment_id}",
        notify_url=settings.PSB_WEBHOOK_URL,
    )

    return {
        "external_payment_id": result["order_id"],
        "payment_url": result["payment_url"],
    }


async def create_psb_event_payment(
    internal_payment_id: str,
    amount: Decimal,
    event_title: str,
    tariff_name: str,
    user_id: str,
    fiscal_email: str,
    event_registration_id: str,
    idempotency_key: str,
) -> dict:
    """
    Оплата мероприятия — чек ОБЯЗАТЕЛЕН.
    ПСБ принимает платёж → при успехе отдельно отправляем данные в ККТ API.
    """
    psb_client = PSBPaymentClient()

    result = await psb_client.create_payment(
        order_id=internal_payment_id,
        amount=amount,
        description=f"Участие в мероприятии «{event_title}» — {tariff_name}",
        return_url=f"{settings.FRONTEND_URL}/payment/result?payment_id={internal_payment_id}",
        notify_url=settings.PSB_WEBHOOK_URL,
    )

    return {
        "external_payment_id": result["order_id"],
        "payment_url": result["payment_url"],
    }
```

### 2.5 Обработка webhook от ПСБ

```python
@router.post("/webhooks/psb")
async def handle_psb_webhook(request: Request):
    body = await request.json()

    # 1. Верификация подписи
    received_sign = body.get("sign", "")
    psb_client = PSBPaymentClient()
    if not psb_client.verify_webhook_signature(body, received_sign):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # 2. Извлечь данные
    order_id = body.get("order_id")
    status = body.get("status")   # Точные коды статусов — из документации ПСБ

    # 3. Найти платёж по external_payment_id
    db_payment = await db.payments.find_by_external_id(order_id)
    if not db_payment:
        return Response(status_code=200)

    # 4. Идемпотентность
    if db_payment.status == "succeeded":
        return Response(status_code=200)

    # 5. Обработка по статусу
    # Коды статусов ПСБ уточняются по документации после подключения
    # Типовые: "APPROVED" / "SETTLED" = успех, "DECLINED" / "REVERSED" = отказ
    if status in ("APPROVED", "SETTLED", "succeeded"):
        await process_psb_payment_success(db_payment)
    elif status in ("DECLINED", "REVERSED", "failed", "cancelled"):
        await db.payments.update(db_payment.id, {"status": "failed"})

    return Response(status_code=200)


async def process_psb_payment_success(db_payment):
    async with db.transaction():
        await db.payments.update(db_payment.id, {
            "status": "succeeded",
            "paid_at": datetime.utcnow(),
        })

        if db_payment.product_type in ("entry_fee", "annual_fee"):
            await subscription_service.activate(
                subscription_id=db_payment.subscription_id,
                user_id=db_payment.user_id,
            )
        elif db_payment.product_type == "event":
            await event_service.confirm_registration(
                registration_id=db_payment.event_registration_id,
            )
            # Для мероприятий — запустить формирование чека через ККТ API
            await taskiq.kiq(
                create_kkt_receipt,
                db_payment.id,
                db_payment.event_registration_id,
            )

    await taskiq.kiq(notify_payment_success, db_payment.user_id, db_payment.id)
    await taskiq.kiq(notify_admins_payment, db_payment.id)
    if db_payment.product_type in ("entry_fee", "annual_fee"):
        await taskiq.kiq(add_to_telegram_channel, db_payment.user_id)
```

### 2.6 Интеграция с ККТ для формирования чеков

Чеки нужны **только для мероприятий**. При выборе варианта ПСБ используем существующую ККТ клиента через её API. Большинство современных касс (АТОЛ, ШТРИХ-М, Эвотор) поддерживают облачный режим.

#### 2.6.1 Вариант ККТ: АТОЛ Онлайн (наиболее распространён)

```python
import httpx
import base64
from datetime import datetime

class ATOLKKTClient:
    """
    Клиент для API АТОЛ Онлайн v5.
    Документация: https://online.atol.ru/files/API_atol_online_v5.pdf
    """

    BASE_URL = "https://online.atol.ru/possystem/v5"

    def __init__(self):
        self.login = settings.KKT_ATOL_LOGIN
        self.password = settings.KKT_ATOL_PASSWORD
        self.group_code = settings.KKT_ATOL_GROUP_CODE
        self.inn = settings.KKT_INN
        self._token: str | None = None
        self._token_expires: datetime | None = None

    async def _get_token(self) -> str:
        if self._token and self._token_expires and datetime.utcnow() < self._token_expires:
            return self._token

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/getToken",
                json={"login": self.login, "pass": self.password},
            )
            response.raise_for_status()
            data = response.json()
            self._token = data["token"]
            self._token_expires = datetime.utcnow().replace(hour=23, minute=59)
            return self._token

    async def send_receipt(
        self,
        receipt_type: str,    # "sell" или "sell_refund"
        fiscal_email: str,
        items: list[dict],
        total_amount: Decimal,
        external_id: str,     # наш internal_payment_id
    ) -> dict:
        token = await self._get_token()

        receipt_data = {
            "external_id": external_id,
            "receipt": {
                "client": {
                    "email": fiscal_email,
                },
                "company": {
                    "email": settings.KKT_COMPANY_EMAIL,
                    "sno": "usn_income",   # УСН доходы
                    "inn": self.inn,
                    "payment_address": settings.KKT_PAYMENT_ADDRESS,
                },
                "items": items,
                "payments": [{
                    "type": 1,             # 1 = электронный платёж
                    "sum": float(total_amount),
                }],
                "total": float(total_amount),
            },
            "service": {
                "callback_url": settings.KKT_CALLBACK_URL,
            },
            "timestamp": datetime.utcnow().strftime("%d.%m.%Y %H:%M:%S"),
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/{self.group_code}/{receipt_type}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=utf-8",
                    "Token": token,
                },
                json=receipt_data,
            )
            response.raise_for_status()
            return response.json()

    async def get_receipt_status(self, uuid: str) -> dict:
        token = await self._get_token()
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/{self.group_code}/report/{uuid}",
                headers={"Token": token},
            )
            response.raise_for_status()
            return response.json()
```

#### 2.6.2 TaskIQ-задача формирования чека

```python
@broker.task(retry_on_error=True, max_retries=5)
async def create_kkt_receipt(
    internal_payment_id: str,
    event_registration_id: str,
    receipt_type: str = "sell",    # "sell" для прихода, "sell_refund" для возврата
):
    """
    Формирование кассового чека через API ККТ.
    Вызывается ТОЛЬКО для product_type = 'event'.
    Для взносов НКО чеки не формируются (целевые поступления).
    """
    db_payment = await db.payments.get(internal_payment_id)
    registration = await db.event_registrations.get(event_registration_id)

    # Получить email для чека
    fiscal_email = registration.fiscal_email or await get_user_email(db_payment.user_id)

    # Получить данные мероприятия
    event = await db.events.get(registration.event_id)
    tariff = await db.event_tariffs.get(registration.event_tariff_id)

    items = [{
        "name": f"Участие в мероприятии «{event.title}»",
        "price": float(registration.applied_price),
        "quantity": 1.0,
        "sum": float(registration.applied_price),
        "measurement_unit": "услуга",
        "payment_method": "full_payment",
        "payment_object": "service",
        "vat": {
            "type": "none"   # без НДС, УСН
        }
    }]

    kkt = ATOLKKTClient()

    # Создать запись чека со статусом pending
    receipt_id = await db.receipts.create({
        "payment_id": internal_payment_id,
        "amount": db_payment.amount,
        "status": "pending",
        "receipt_type": receipt_type,
    })

    response = await kkt.send_receipt(
        receipt_type="sell" if receipt_type == "payment" else "sell_refund",
        fiscal_email=fiscal_email,
        items=items,
        total_amount=db_payment.amount,
        external_id=internal_payment_id,
    )

    # АТОЛ возвращает uuid задачи → нужно дополнительно опросить статус
    atol_uuid = response.get("uuid")
    await taskiq.kiq(
        fetch_kkt_receipt_result,
        receipt_id,
        atol_uuid,
        retry_count=0,
    )


@broker.task
async def fetch_kkt_receipt_result(
    receipt_id: str,
    atol_uuid: str,
    retry_count: int = 0,
):
    """Получить результат обработки чека от АТОЛ (polling)."""
    MAX_RETRIES = 10
    RETRY_DELAY = 15  # секунд

    kkt = ATOLKKTClient()
    result = await kkt.get_receipt_status(atol_uuid)

    if result.get("status") == "done":
        payload = result.get("payload", {})
        await db.receipts.update(receipt_id, {
            "fiscal_number": payload.get("fn_number"),
            "fiscal_document": payload.get("fiscal_document_number"),
            "fiscal_sign": payload.get("fiscal_document_attribute"),
            "receipt_url": build_receipt_url_from_atol(payload),
            "receipt_data": result,
            "status": "succeeded",
        })
    elif result.get("status") in ("wait", "receive"):
        if retry_count < MAX_RETRIES:
            await asyncio.sleep(RETRY_DELAY)
            await taskiq.kiq(fetch_kkt_receipt_result, receipt_id, atol_uuid, retry_count + 1)
        else:
            await db.receipts.update(receipt_id, {
                "status": "failed",
                "error_message": "Timeout: АТОЛ не вернул результат за отведённое время",
            })
            await notify_admin_receipt_failed(receipt_id)
    else:
        await db.receipts.update(receipt_id, {
            "status": "failed",
            "error_message": result.get("error", {}).get("text", "Unknown error"),
        })
        await notify_admin_receipt_failed(receipt_id)


def build_receipt_url_from_atol(payload: dict) -> str:
    fn = payload.get("fn_number", "")
    fp = payload.get("fiscal_document_attribute", "")
    fd = payload.get("fiscal_document_number", "")
    return f"https://receipt.taxcom.ru/v01/show?fn={fn}&fp={fp}&i={fd}"
```

### 2.7 Polling-эндпоинт для проверки статуса

```python
@router.get("/payments/{payment_id}/status")
async def get_payment_status_psb(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Для ПСБ: polling статуса после возврата с платёжной страницы.
    У ПСБ нет единого SDK — делаем запрос к их API для проверки.
    """
    payment = await db.payments.get(payment_id)
    if payment.user_id != current_user.id and "admin" not in current_user.roles:
        raise HTTPException(403)

    if payment.status == "pending":
        try:
            psb_client = PSBPaymentClient()
            psb_status = await psb_client.get_order_status(payment.external_payment_id)
            # Уточнить код успешного статуса по документации ПСБ
            if psb_status.get("status") in ("APPROVED", "SETTLED"):
                await process_psb_payment_success(payment)
                payment = await db.payments.get(payment_id)
        except Exception:
            pass

    return {
        "payment_id": str(payment_id),
        "status": payment.status,
        "amount": float(payment.amount),
        "paid_at": payment.paid_at.isoformat() if payment.paid_at else None,
    }
```

### 2.8 ENV-переменные (Вариант 2)

```env
PAYMENT_PROVIDER=psb

# ПСБ эквайринг
PSB_MERCHANT_ID=
PSB_SECRET_KEY=
PSB_API_URL=https://3ds.payment.ru    # уточнить по документации ПСБ
PSB_RETURN_URL=https://trichology.ru/payment/result
PSB_WEBHOOK_URL=https://api.trichology.ru/api/v1/webhooks/psb

# ККТ (АТОЛ Онлайн) — для чеков по мероприятиям
KKT_PROVIDER=atol
KKT_ATOL_LOGIN=
KKT_ATOL_PASSWORD=
KKT_ATOL_GROUP_CODE=
KKT_INN=
KKT_COMPANY_EMAIL=info@trichology.ru
KKT_PAYMENT_ADDRESS=https://trichology.ru
KKT_CALLBACK_URL=https://api.trichology.ru/api/v1/webhooks/kkt-receipt
```

---

## Общий код (независимо от варианта)

### Идемпотентность при создании платежа

```python
async def get_or_create_payment_idempotent(
    user_id: str,
    product_type: str,
    idempotency_key: str,
    create_fn,
) -> dict:
    """
    Проверяем Redis перед созданием платежа.
    Если ключ уже есть — возвращаем тот же ответ.
    """
    redis_key = f"idempotency:pay:{user_id}:{idempotency_key}"

    cached = await redis.get(redis_key)
    if cached:
        return json.loads(cached)

    result = await create_fn()

    await redis.setex(
        redis_key,
        86400,  # 24 часа
        json.dumps(result),
    )
    return result
```

### Маршрутизация вебхуков через фабрику

```python
# app/api/v1/webhooks.py

from app.services.payment_service import get_payment_handler

@router.post("/webhooks/yookassa")
async def yookassa_webhook(request: Request):
    handler = get_payment_handler("yookassa")
    return await handler.handle_webhook(request)


@router.post("/webhooks/psb")
async def psb_webhook(request: Request):
    handler = get_payment_handler("psb")
    return await handler.handle_webhook(request)


# app/services/payment_service.py
def get_payment_handler(provider: str):
    if provider == "yookassa":
        return YooKassaPaymentHandler()
    elif provider == "psb":
        return PSBPaymentHandler()
    raise ValueError(f"Unknown payment provider: {provider}")
```

---

## Сводная таблица решений по фискализации

| Сценарий | Чек нужен? | Вариант 1 (ЮKassa) | Вариант 2 (ПСБ) |
|----------|------------|---------------------|-----------------|
| Вступительный взнос | ❌ НЕТ | receipt не передаётся | ККТ не вызывается |
| Ежегодный членский взнос | ❌ НЕТ | receipt не передаётся | ККТ не вызывается |
| Оплата мероприятия | ✅ ДА | receipt в теле запроса ЮKassa | TaskIQ → АТОЛ API |
| Возврат за мероприятие | ✅ ДА | receipt в Refund.create() | TaskIQ → АТОЛ sell_refund |
| Оплата мероприятия юрлицом б/н | ❌ НЕТ | Счёт-оферта, не через сайт | Счёт-оферта, не через сайт |

---

## Итоговая рекомендация

```
При дедлайне МАЙ 2026 — Вариант 1 (ЮKassa):

  ✅ Подать документы в ЮKassa немедленно (первая неделя марта)
  ✅ Запустить тестовую среду параллельно с разработкой
  ✅ При наличии существующей ККТ с API — подключить её вместо
     "Чеков от ЮKassa" и сэкономить ~0,8% на мероприятиях
  ✅ Вывод средств настроить на расчётный счёт в ПСБ

Через 6–12 месяцев после запуска — пересмотреть в пользу Варианта 2:

  После получения документации ПСБ и стабилизации оборота
  миграция даёт ~60–80 тыс. ₽/год экономии на комиссиях.
  К тому моменту история деятельности организации будет достаточной
  для любого провайдера.

Вариант 2 (ПСБ) — немедленно, если:

  ✅ Менеджер ПСБ подтвердил работу с МОО на этой неделе
  ✅ Получены ставки ~1,5–2% по картам, ~0,4% по СБП
  ✅ Документация API получена до начала разработки
  ✅ Существующая ККТ подтверждена поддержка облачных чеков
  ✅ Сроки позволяют +2–3 недели
```
