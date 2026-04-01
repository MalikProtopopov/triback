# Интеграция платёжной системы Moneta / PayAnyWay — полный план

> **Статус:** Требования + план поэтапной реализации  
> **Дата:** 2026-03-18 (ревизия 2)  
> **Автор:** Системный архитектор  
> **Целевая документация Moneta:** `docs/docs_moneta/`

---

## Содержание

1. [Архитектурный обзор AS-IS](#1-архитектурный-обзор-as-is)
2. [Бизнес-требования TO-BE](#2-бизнес-требования-to-be)
3. [Архитектурные решения](#3-архитектурные-решения)
4. [Детальный технический план](#4-детальный-технический-план)
5. [Промпты для поэтапной реализации](#5-промпты-для-поэтапной-реализации)
6. [Документация для фронтенда](#6-документация-для-фронтенда)
7. [Вопросы для менеджера / заказчика](#7-вопросы-для-менеджера--заказчика)
8. [Приложение A: Сравнение YooKassa vs Moneta](#приложение-a-сравнение-yookassa-vs-moneta)
9. [Приложение B: Формулы подписей Moneta](#приложение-b-формулы-подписей-moneta)
10. [Приложение C: Статусы операций Moneta](#приложение-c-статусы-операций-moneta)
11. [Приложение D: Коды ошибок Moneta](#приложение-d-коды-ошибок-moneta)

---

## 1. Архитектурный обзор AS-IS

### 1.1. Текущий стек платежей

```
                    ┌── POST /subscriptions/pay ──┐
Фронтенд ──────────┤                              ├──→ YooKassaClient.create_payment()
                    └── POST /events/{id}/register─┘           │
                                                               ▼
                                                    Редирект на YooKassa checkout
                                                               │
                                                               ▼
                                                    Webhook POST /webhooks/yookassa
                                                               │
                                                               ▼
                                                    PaymentWebhookService.handle_webhook()
                                                               │
                                                     ┌─────────┴──────────┐
                                                     │                    │
                                             entry_fee/subscription   event
                                             → активация подписки     → подтверждение
                                             → статус ACTIVE            регистрации
```

### 1.2. Ключевые модели данных

| Модель | Таблица | Ключевые поля |
|--------|---------|---------------|
| `Plan` | `plans` | `code` (unique), `name`, `price` (Numeric 12,2), `duration_months` (default 12), `is_active`, `sort_order` |
| `Subscription` | `subscriptions` | `user_id`, `plan_id`, `status`, `is_first_year`, `starts_at`, `ends_at` |
| `Payment` | `payments` | `user_id`, `amount`, `product_type`, `payment_provider`, `status`, `subscription_id`, `event_registration_id`, `external_payment_id`, `external_payment_url`, `idempotency_key`, `description`, `paid_at` |
| `Receipt` | `receipts` | `payment_id`, `receipt_type`, `provider_receipt_id`, `fiscal_number`, `fiscal_document`, `fiscal_sign`, `receipt_url`, `receipt_data` (JSONB), `amount`, `status` |
| `EventTariff` | `event_tariffs` | `event_id`, `name`, `price`, `member_price`, `seats_limit`, `seats_taken`, `is_active` |
| `EventRegistration` | `event_registrations` | `user_id`, `event_id`, `event_tariff_id`, `applied_price`, `is_member_price`, `status`, `fiscal_email` |

### 1.3. Бизнес-логика определения типа платежа

```python
# subscription_service.py → _determine_product_type()
LAPSE_THRESHOLD_DAYS = 60  # из payment_utils.py

async def _determine_product_type(user_id):
    latest_sub = <последняя активная подписка>
    if not latest_sub:
        has_entry = <есть ли succeeded платёж с product_type=entry_fee>
        return "subscription" if has_entry else "entry_fee"
    if latest_sub.ends_at < now() - 60 days:
        return "entry_fee"
    return "subscription"
```

### 1.4. Текущие PostgreSQL enum

```sql
CREATE TYPE payment_provider AS ENUM ('yookassa', 'psb', 'manual');
CREATE TYPE product_type AS ENUM ('entry_fee', 'subscription', 'event');
CREATE TYPE payment_status AS ENUM ('pending', 'succeeded', 'failed', 'partially_refunded', 'refunded');
CREATE TYPE subscription_status AS ENUM ('active', 'expired', 'pending_payment', 'cancelled');
CREATE TYPE receipt_status AS ENUM ('pending', 'succeeded', 'failed');
CREATE TYPE receipt_type AS ENUM ('payment', 'refund');
```

### 1.5. Текущие API-эндпоинты

| Метод | Путь | Назначение |
|-------|------|------------|
| `POST` | `/subscriptions/pay` | Инициация оплаты подписки |
| `GET` | `/subscriptions/status` | Статус подписки + entry_fee |
| `GET` | `/subscriptions/payments` | История платежей пользователя |
| `GET` | `/subscriptions/payments/{id}/receipt` | Чек по платежу |
| `POST` | `/webhooks/yookassa` | Webhook от YooKassa |
| `POST` | `/api/v1/events/{id}/register` | Регистрация на мероприятие (с оплатой) |
| `POST` | `/api/v1/events/{id}/confirm-guest-registration` | Подтверждение guest-email |
| `GET` | `/admin/plans` | Список планов (админ) |
| `POST` | `/admin/payments/manual` | Ручной платёж (админ) |
| `POST` | `/admin/payments/{id}/refund` | Возврат (админ) |

### 1.6. Текущий YooKassaClient (payment_service.py)

```python
class YooKassaClient:
    # auth = (YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)
    # base_url = YOOKASSA_API_URL (https://api.yookassa.ru/v3)

    async def create_payment(amount, description, metadata, idempotency_key, return_url, receipt)
    # → POST /payments → {"id", "confirmation": {"confirmation_url"}}

    async def get_payment(external_id)
    # → GET /payments/{id}

    async def create_refund(payment_id, amount, description, idempotency_key)
    # → POST /refunds
```

### 1.7. Текущий Webhook-обработчик

```python
# PaymentWebhookService.handle_webhook(body, client_ip)
# 1. Проверка IP по whitelist (YOOKASSA_IP_WHITELIST)
# 2. body = JSON: {"event": "payment.succeeded", "object": {"id": "...", "metadata": {"internal_payment_id": "uuid"}}}
# 3. Поиск Payment по external_payment_id или metadata.internal_payment_id
# 4. Вызов _handle_payment_succeeded / _handle_payment_canceled / _handle_refund_succeeded
```

---

## 2. Бизнес-требования TO-BE

### 2.1. Замена YooKassa на Moneta

- Moneta/PayAnyWay **полностью заменяет** YooKassa как активный провайдер
- Код YooKassa **остаётся в кодовой базе** как fallback (переключение через env)
- Модуль написан **модульно** — в будущем можно легко вернуть YooKassa или подключить Тинькофф
- Фискализация (54-ФЗ) **через BPA PayAnyWay** (ККТ агрегатора)

### 2.2. Выбор API: BPA PayAnyWay (рекомендовано)

У Moneta два способа создания платежа:

| Способ | Описание | Фискализация | Рекомендация |
|--------|----------|-------------|-------------|
| **MONETA.Assistant** (форма) | HTML-форма / ссылка с `MNT_*` params | Нужен отдельный модуль `kassa.payanyway.ru` | Простой, но нет нативной фискализации |
| **BPA PayAnyWay API** (invoice) | `POST /api/invoice` с `inventory[]` | **Встроенная** — чек формируется из `inventory` | **✅ Рекомендуется** |

**Решение: используем BPA API** — он даёт:
- Нативную фискализацию через `inventory[]` (54-ФЗ)
- Возможность нескольких товаров в одном платеже (entry_fee + subscription)
- Холдирование при необходимости
- Сохранение карты + рекуррентные платежи (на будущее)

**Поток оплаты через BPA:**
```
Backend → POST bpa.payanyway.ru/api/invoice → {"operation": "12345"}
    → формируем URL: moneta.ru/assistant.htm?operationId=12345
    → отдаём URL фронту → фронт делает redirect
    → покупатель оплачивает
    → Moneta шлёт Pay URL webhook → backend отвечает "SUCCESS"
    → BPA шлёт receipt webhook → backend сохраняет ссылку на чек
```

### 2.3. Два потока оплаты

#### Поток A: Членство в ассоциации (подписка)

**Сценарий A1 — Первое вступление / подписка истекла > 60 дней:**
- Бэкенд определяет: `entry_fee_required = true`
- Автоматически добавляет вступительный взнос к платежу
- Формируется один invoice с **двумя позициями в `inventory`**:
  1. `Вступительный взнос — X ₽` (Plan с plan_type="entry_fee")
  2. `Годовая подписка — Y ₽` (Plan с plan_type="subscription")
- `paymentAmount = X + Y`
- Одна платёжная ссылка, один фискальный чек с двумя строками

**Сценарий A2 — Продление (подписка активна или истекла < 60 дней):**
- `entry_fee_required = false`
- Один invoice с **одной позицией** в `inventory`:
  1. `Годовая подписка — Y ₽`
- Одна платёжная ссылка, один чек

**Важно:** Пользователь **всегда получает одну ссылку на оплату**. Бэкенд решает что включить (entry_fee + subscription или только subscription).

#### Поток B: Оплата мероприятия

**Сценарий B1 — Авторизованный врач с активной подпиской:**
- Цена = `EventTariff.member_price`
- Bearer token **обязателен** — по нему определяется наличие активной подписки
- `is_member_price = True` в записи регистрации

**Сценарий B2 — Гость / пользователь без подписки:**
- Цена = `EventTariff.price` (полная цена)
- Может быть без авторизации (существующий guest registration flow)
- `is_member_price = False`

**Сценарий B3 — Бесплатное мероприятие (price=0):**
- Авто-подтверждение без платежа (текущее поведение сохраняется)

### 2.4. Расширение модели Plan

Текущая модель `Plan` не различает тип плана. Добавляется:

```sql
ALTER TABLE plans ADD COLUMN plan_type VARCHAR(20) NOT NULL DEFAULT 'subscription';
-- Значения: 'entry_fee', 'subscription'
```

| code | name | plan_type | price | duration_months | is_active |
|------|------|-----------|-------|-----------------|-----------|
| `membership_fee` | Вступительный взнос | `entry_fee` | 3000.00 | 0 | true |
| `annual` | Годовая подписка | `subscription` | 5000.00 | 12 | true |
| `biannual` | Подписка на 2 года | `subscription` | 9000.00 | 24 | false |

**Для `entry_fee` планов:** `duration_months = 0` (разовый платёж, не влияет на срок подписки).

**ВАЖНО:** Текущий CheckConstraint на таблице `plans` требует `duration_months > 0`. Миграция должна изменить его на `duration_months >= 0`, чтобы entry_fee планы с `duration_months = 0` были допустимы.

**Это позволяет:**
- Чётко отличать «вступительный взнос» от «годовой подписки»
- Иметь несколько планов подписки (1 год, 2 года) — в будущем
- На фронте показывать правильные планы в зависимости от статуса
- Деактивировать планы (`is_active=false`) без удаления
- Не перемешивать планы: бэкенд автоматически подбирает entry_fee план

### 2.5. Фискализация (54-ФЗ)

- Чеки формирует **BPA PayAnyWay** (ККТ агрегатора ООО «ПЭЙ ЭНИ ВЭЙ»)
- При создании invoice передаётся `inventory[]` с позициями
- Каждая позиция содержит:
  - `sellerAccount` — бизнес-счёт продавца в МОНЕТА.РУ
  - `sellerInn` — ИНН продавца
  - `sellerName` — наименование организации
  - `sellerPhone` — телефон
  - `productName` — название товара/услуги (для чека)
  - `productQuantity` — количество
  - `productPrice` — цена с учётом скидок
  - `productVatCode` — код НДС (1105 = без НДС для УСН)
  - `po` — объект оплаты (`service` для услуг)
  - `pm` — метод оплаты (`full_payment` для полной оплаты)
- Чек автоматически отправляется покупателю на `customerEmail`
- При возврате — чек возврата через BPA RefundRequest с `customfield:inventory`

### 2.6. Обратная совместимость

- Все существующие платежи (через YooKassa) остаются в БД без изменений
- Webhook `/webhooks/yookassa` продолжает работать для старых платежей
- Добавляется новый webhook `/webhooks/moneta` для Moneta
- `payment_provider` в Payment определяет через какой webhook обрабатывать

---

## 3. Архитектурные решения

### 3.1. Абстракция платёжного провайдера (Provider-agnostic)

```
┌──────────────────────────────────────────────────────┐
│                 PaymentProvider (ABC)                  │
│                                                        │
│  create_payment(items, email, return_url) → Result     │
│  verify_webhook(request_data) → WebhookData            │
│  build_webhook_response(data) → str                    │
│  create_refund(payment_id, amount, items) → RefundData │
└───────────────┬─────────────────┬─────────────────────┘
                │                 │
    ┌───────────┴──┐    ┌────────┴──────┐
    │  Moneta      │    │  YooKassa     │
    │  Provider    │    │  Provider     │
    └──────────────┘    └───────────────┘
```

**Ключевые дата-классы:**

```python
@dataclass
class PaymentItem:
    name: str                           # "Годовая подписка"
    price: Decimal                      # 5000.00
    quantity: int = 1
    vat_code: int | None = None         # 1105 = без НДС
    payment_object: str = "service"     # service | commodity | job
    payment_method: str = "full_payment"

@dataclass
class CreatePaymentResult:
    external_id: str       # ID операции у провайдера (Moneta operation / YooKassa payment id)
    payment_url: str       # URL для оплаты
    raw_response: dict     # полный ответ для логирования

@dataclass
class WebhookData:
    event_type: str        # "payment.succeeded" | "payment.canceled" | "refund.succeeded"
    external_id: str       # ID операции у провайдера
    transaction_id: str    # наш internal payment.id
    amount: Decimal
    raw_data: dict

@dataclass
class RefundResult:
    external_id: str
    status: str
    raw_response: dict
```

**Выбор провайдера** через `settings.PAYMENT_PROVIDER`:
- `"moneta"` → `MonetaPaymentProvider()`
- `"yookassa"` → `YooKassaPaymentProvider()`
- Дефолт: `"moneta"`

### 3.2. Структура новых файлов

```
backend/app/
├── services/
│   ├── payment_providers/
│   │   ├── __init__.py              # get_provider() factory
│   │   ├── base.py                  # PaymentProvider ABC + dataclasses
│   │   ├── moneta_client.py         # MonetaPaymentProvider (BPA API)
│   │   └── yookassa_client.py       # YooKassaPaymentProvider (перенос)
│   ├── payment_service.py           # → re-export YooKassaClient (backward-compat)
│   ├── payment_utils.py             # build_inventory(), is_ip_allowed() и т.д.
│   ├── payment_webhook_service.py   # provider-agnostic обработка webhook
│   ├── subscription_service.py      # обновлённый pay() с get_provider()
│   └── event_registration_service.py # обновлённый с get_provider()
├── api/v1/
│   └── webhooks.py                  # + POST /webhooks/moneta + POST /webhooks/moneta/check + POST /webhooks/moneta/receipt
```

### 3.3. Конфигурация (config.py)

```python
# Общее
PAYMENT_PROVIDER: str = "moneta"                    # "moneta" | "yookassa"

# Moneta / BPA PayAnyWay — API для invoice (фискализация)
MONETA_BPA_API_URL: str = "https://bpa.payanyway.ru/api"
MONETA_BPA_KEY: str = ""                             # ключ партнера BPA
MONETA_BPA_SECRET: str = ""                          # секрет для подписи BPA invoice

# Moneta — счета
MONETA_CREDIT_ACCOUNT: str = ""                      # счёт ПА для приёма средств
MONETA_DEBIT_ACCOUNT: str = ""                       # счёт списания (обычно пустой)
MONETA_SELLER_ACCOUNT: str = ""                      # бизнес-счёт продавца в МОНЕТА.РУ
MONETA_SELLER_INN: str = ""                          # ИНН продавца
MONETA_SELLER_NAME: str = ""                         # полное наименование организации
MONETA_SELLER_PHONE: str = ""                        # телефон (для чека ОФД)

# Moneta — Assistant (платёжная форма)
MONETA_MNT_ID: str = ""                              # номер расширенного счёта
MONETA_ASSISTANT_URL: str = "https://moneta.ru/assistant.htm"
MONETA_WIDGET_URL: str = "https://moneta.ru/assistant.widget"
MONETA_DEMO_MODE: bool = False                       # True → demo.moneta.ru

# Moneta — webhook (Pay URL / Check URL)
MONETA_WEBHOOK_SECRET: str = ""                      # "Код проверки целостности данных" из ЛК
MONETA_BPA_RECEIPT_URL: str = ""                     # Наш URL, на который BPA шлёт receipt-уведомления (не используется в коде — настраивается вручную через mp@payanyway.ru, хранится как документация)

# Moneta — redirect URL для покупателя
MONETA_SUCCESS_URL: str = ""                         # куда после успеха
MONETA_FAIL_URL: str = ""                            # куда после отмены
MONETA_INPROGRESS_URL: str = ""                      # куда при незавершённой оплате
MONETA_RETURN_URL: str = ""                          # куда при добровольном отказе

# Moneta — фискализация
MONETA_VAT_CODE: int = 1105                          # НДС: 1105=не облагается (УСН), 1102=20% (ОСНО)
MONETA_PAYMENT_OBJECT: str = "service"               # Тип объекта оплаты: service, commodity
MONETA_PAYMENT_METHOD: str = "full_payment"           # Метод оплаты: full_payment, full_prepayment

# Moneta — платёжная форма v3
MONETA_FORM_VERSION: str = "v3"                      # v1/v2/v3 — v3 поддерживает СБП, SberPay, рекуррент

# Legacy YooKassa (сохранено для обратной совместимости)
YOOKASSA_SHOP_ID: str = ""
YOOKASSA_SECRET_KEY: str = ""
YOOKASSA_API_URL: str = "https://api.yookassa.ru/v3"
YOOKASSA_RETURN_URL: str = "https://trichology.ru/payment/result"
YOOKASSA_IP_WHITELIST: str = "185.71.76.0/27,185.71.77.0/27,77.75.153.0/25,77.75.156.11/32,77.75.156.35/32"
```

### 3.4. Миграция БД (Alembic)

```sql
-- 1. Расширить enum payment_provider
ALTER TYPE payment_provider ADD VALUE IF NOT EXISTS 'moneta';

-- 2. Добавить plan_type в plans
ALTER TABLE plans ADD COLUMN plan_type VARCHAR(20) NOT NULL DEFAULT 'subscription';
CREATE INDEX idx_plans_plan_type ON plans (plan_type);

-- 3. Изменить CheckConstraint duration_months > 0 → >= 0 (для entry_fee с duration_months=0)
ALTER TABLE plans DROP CONSTRAINT IF EXISTS chk_plans_duration;
ALTER TABLE plans ADD CONSTRAINT chk_plans_duration CHECK (duration_months >= 0);

-- 4. Обновить существующие планы
-- (выполняется вручную или через data migration после ревью)
-- Предполагаем что в admin/plans уже есть "Членский взнос" и "Годовая подписка"
-- UPDATE plans SET plan_type = 'entry_fee' WHERE code ILIKE '%member%' OR code ILIKE '%entry%';

-- 5. Добавить поле moneta_operation_id в payments (для BPA)
ALTER TABLE payments ADD COLUMN moneta_operation_id VARCHAR(255);
CREATE INDEX idx_payments_moneta_op ON payments (moneta_operation_id)
  WHERE moneta_operation_id IS NOT NULL;
```

### 3.5. Подписи Moneta (MD5)

#### 3.5.1. Подпись для BPA invoice

```python
import hashlib

# debitMntAccount: пустая строка если не используется
signature = hashlib.md5(
    (debit_mnt_account + mnt_transaction_id + MONETA_BPA_SECRET).encode()
).hexdigest()
```

#### 3.5.2. Подпись для confirm/cancel operation

```python
signature = hashlib.md5(
    (operation_id + MONETA_BPA_SECRET).encode()
).hexdigest()
```

#### 3.5.3. Проверка подписи входящего webhook (Pay URL от MONETA.Assistant)

```python
# Порядок полей — конкатенация:
# MNT_ID + MNT_TRANSACTION_ID + MNT_OPERATION_ID + MNT_AMOUNT + MNT_CURRENCY_CODE + MNT_SUBSCRIBER_ID + MNT_TEST_MODE + <КОД_ПРОВЕРКИ_ЦЕЛОСТНОСТИ>
# Если поле отсутствует — подставлять пустую строку

expected = hashlib.md5(
    (mnt_id + mnt_transaction_id + mnt_operation_id + mnt_amount
     + mnt_currency_code + mnt_subscriber_id + mnt_test_mode
     + MONETA_WEBHOOK_SECRET).encode()
).hexdigest()

assert request_signature == expected
```

**ВАЖНО:**
- Точный порядок полей для входящей подписи **не полностью документирован** в веб-документации Moneta — указана ссылка на [PDF-спецификацию](https://www.moneta.ru/doc/MONETA.Assistant.ru.pdf). Порядок выше (MNT_ID → TRANSACTION_ID → OPERATION_ID → AMOUNT → CURRENCY → SUBSCRIBER_ID → TEST_MODE → SECRET) — общепринятый, но **при реализации ОБЯЗАТЕЛЬНО верифицировать по PDF и тестам на demo-площадке**.
- Если подпись не сходится — попробовать без `MNT_SUBSCRIBER_ID` (может отсутствовать) и/или без `MNT_TEST_MODE`.

#### 3.5.4. Подпись ответа на webhook

```python
# MNT_RESULT_CODE + MNT_ID + MNT_TRANSACTION_ID + <КОД_ПРОВЕРКИ_ЦЕЛОСТНОСТИ>
response_signature = hashlib.md5(
    (result_code + mnt_id + mnt_transaction_id + MONETA_WEBHOOK_SECRET).encode()
).hexdigest()
```

Пример из документации (`08-payments-notification.md`): `md5("200" + "54600817" + "FF790ABCD" + "QWERTY")` = `md5("20054600817FF790ABCDQWERTY")`

**ВНИМАНИЕ:** В `01-assistant-summary.md` указана формула `md5(MNT_ID + TRANSACTION_ID + RESULT_CODE + secret)` (ID первый), но конкретный пример в `08-payments-notification.md` показывает `md5(RESULT_CODE + MNT_ID + TRANSACTION_ID + secret)` (RESULT_CODE первый). **Верить примеру** — он содержит реальные значения и верифицируется. Порядок: RESULT_CODE → MNT_ID → TRANSACTION_ID → SECRET.

### 3.6. Check URL (проверочные запросы)

Moneta может отправлять проверочные запросы **до оплаты** для проверки заказа. Если в ЛК настроен Check URL:

**Запрос:** GET/POST с теми же MNT_* параметрами  
**Ответ:** XML формат (обязательно!)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<MNT_RESPONSE>
  <MNT_ID>11223344</MNT_ID>
  <MNT_TRANSACTION_ID>payment-uuid</MNT_TRANSACTION_ID>
  <MNT_RESULT_CODE>200</MNT_RESULT_CODE>
  <MNT_AMOUNT>8000.00</MNT_AMOUNT>
  <MNT_SIGNATURE>...</MNT_SIGNATURE>
</MNT_RESPONSE>
```

**Коды результата:**
- `200` — заказ существует, ожидает оплаты
- `402` — заказ не найден или уже оплачен
- `500` — внутренняя ошибка

**Важно:** Если Check URL настроен но не отвечает корректно → Moneta **отменяет платёж**.

### 3.7. Версии платёжной формы

| Версия | Поддержка | Рекомендация |
|--------|-----------|--------------|
| **v1** | Классическая форма: МОНЕТА.РУ, WebMoney, Яндекс, карты | — |
| **v2** | Компактная: только карты | — |
| **v3** | Новая: карты (РФ + зарубежные), **СБП**, **SberPay**, рекуррентные | **✅ Рекомендуется** |

Включение v3: через ЛК Монеты или параметром `version=v3` в URL.

### 3.8. MNT_TEST_MODE (устарел для включения, но остаётся в подписи)

Тестовый режим настраивается **только через флаг в ЛК Монеты** на расширенном счёте. Параметр `MNT_TEST_MODE` в запросе **устарел** и игнорируется Moneta для переключения режима.

**Однако** поле `MNT_TEST_MODE` **по-прежнему участвует в формуле подписи** webhook. В webhook-запросе от Moneta это поле приходит со значением `"0"` или `"1"`. При вычислении `expected_signature` нужно включать его (или `""` если отсутствует).

Для тестирования используется **demo-площадка**: `https://demo.moneta.ru`

---

## 4. Детальный технический план

### Фаза 0: Подготовка (миграции + конфиг + модели)

1. Alembic миграция: `payment_provider` enum + `plans.plan_type` + `payments.moneta_operation_id`
2. Новые настройки в `config.py`, `.env.example`, `env.prod.example`
3. Обновить `enums.py`: `PaymentProvider.MONETA`, новый `PlanType`
4. Обновить `models/base.py`: SAEnum PaymentProvider + 'moneta'
5. Обновить `models/subscriptions.py`: Plan.plan_type, Payment.moneta_operation_id
6. Обновить admin API: вернуть `plan_type` в GET /admin/plans + разрешить задавать при создании/редактировании

### Фаза 1: Абстракция провайдера

1. Создать `payment_providers/base.py` — ABC + dataclasses
2. Перенести `YooKassaClient` → `payment_providers/yookassa_client.py`, адаптировать под ABC
3. Оставить реэкспорт в `payment_service.py` (backward-compat)
4. Создать `payment_providers/__init__.py` — фабрика `get_provider()`

### Фаза 2: MonetaClient (BPA API)

1. `payment_providers/moneta_client.py` — реализация PaymentProvider
2. `create_payment()` → POST `/api/invoice` → operationId → payment_url
3. `verify_webhook()` → проверка MD5 подписи
4. `build_webhook_response()` → "SUCCESS" / "FAIL"
5. Вспомогательные: `confirm_operation()`, `cancel_operation()`, `cancel_invoice()`
6. `create_refund()` → заглушка (TODO: MerchantAPI RefundRequest)

### Фаза 3: Webhook-эндпоинты

1. `POST /webhooks/moneta` — Pay URL (уведомление об оплате)
   - Принимает form-data (application/x-www-form-urlencoded) или GET
   - Ответ: plain text "SUCCESS" / "FAIL"
   - Дедупликация через Redis
2. `POST /webhooks/moneta/check` — Check URL (проверка заказа до оплаты)
   - Ответ: XML (MNT_RESPONSE)
3. `POST /webhooks/moneta/receipt` — BPA receipt webhook
   - JSON: `{"operation": ..., "receipt": "url"}`
   - Сохранение receipt_url в модель Receipt

### Фаза 4: Обновление PaymentWebhookService

1. Новый метод `handle_moneta_webhook(webhook_data: WebhookData)`:
   - Поиск Payment по `id = webhook_data.transaction_id` (UUID)
   - Та же бизнес-логика: `_activate_subscription`, `_confirm_event_registration`
   - Обновление `payment.moneta_operation_id = webhook_data.external_id`
2. Новый метод `handle_moneta_check(mnt_transaction_id: str)`:
   - Проверить что Payment существует и в статусе `pending`
   - Вернуть сумму и статус

### Фаза 5: Рефакторинг SubscriptionService

1. `get_provider()` вместо `YooKassaClient()`
2. Логика entry_fee + subscription:
   - Если `_determine_product_type()` → entry_fee → формируем `items[]` с **двумя PaymentItem** (взнос + подписка)
   - Если subscription → один PaymentItem
3. Создаём **один Payment** с `product_type="entry_fee"` и `amount = entry_plan.price + sub_plan.price`:
   - Один invoice (одна ссылка на оплату) с `paymentAmount = сумма обоих`
   - Breakdown на уровне `inventory[]` — для фискального чека
   - При получении webhook → `_activate_subscription()` как и раньше
   - Один Payment = один webhook = простая логика
4. Обновить `get_status()`:
   - Добавить `entry_fee_required: bool`
   - Добавить `entry_fee_plan: PlanNested | None` (план вступительного взноса)
   - Добавить `available_plans: list[PlanNested]` (активные subscription-планы)
   - Обновить `next_action` значения

### Фаза 6: Рефакторинг EventRegistrationService

1. `get_provider()` вместо `YooKassaClient()`
2. Один PaymentItem на мероприятие
3. `customer_email` = `fiscal_email` || `user.email` || `guest_email`

### Фаза 7: Возвраты

1. `MonetaClient.create_refund()` через BPA или MerchantAPI
2. Webhook для уведомлений о возврате
3. Receipt для чека возврата

### Фаза 8: Тесты + документация

1. Unit-тесты: MonetaClient, webhook, signature verification
2. Integration-тесты: pay flow, check URL, receipt
3. Обновить BACKEND_CHANGELOG
4. Ruff check + pytest

---

## 5. Промпты для поэтапной реализации

Каждый промпт — самостоятельная задача. Скидывай их по порядку. Каждый следующий промпт зависит от предыдущего.

---

### ПРОМПТ 1: Миграция БД + конфигурация + модели

```
Контекст: бэкенд FastAPI + SQLAlchemy 2.0 (async) + Alembic + PostgreSQL.
Проект: /Users/mak/trihoback/backend

Текущее состояние:
- Модели: app/models/subscriptions.py (Plan, Subscription, Payment, Receipt)
- Enum: app/models/base.py (SAEnum PaymentProvider: 'yookassa', 'psb', 'manual')
- Python enums: app/core/enums.py (PaymentProvider, ProductType и т.д.)
- Конфиг: app/core/config.py (YOOKASSA_*)

Задача — ТОЛЬКО инфраструктура, НЕ трогай бизнес-логику сервисов:

1. Создай Alembic миграцию (revision), которая:
   a) Добавляет значение 'moneta' в PostgreSQL enum `payment_provider`:
      ALTER TYPE payment_provider ADD VALUE IF NOT EXISTS 'moneta';
   b) Добавляет колонку `plan_type` (VARCHAR(20), NOT NULL, DEFAULT 'subscription') в таблицу `plans`
   c) Добавляет индекс idx_plans_plan_type на plans(plan_type)
   c2) Изменяет CheckConstraint: DROP chk_plans_duration, ADD chk_plans_duration CHECK (duration_months >= 0)
       (Текущий constraint требует > 0, но entry_fee планы имеют duration_months = 0)
   d) Добавляет колонку `moneta_operation_id` (VARCHAR(255), nullable) в таблицу `payments`
   e) Добавляет индекс idx_payments_moneta_op на payments(moneta_operation_id) WHERE moneta_operation_id IS NOT NULL

2. В `app/core/config.py` (class Settings) добавь ВСЕ настройки Moneta:
   PAYMENT_PROVIDER: str = "moneta"
   MONETA_BPA_API_URL: str = "https://bpa.payanyway.ru/api"
   MONETA_BPA_KEY: str = ""
   MONETA_BPA_SECRET: str = ""
   MONETA_CREDIT_ACCOUNT: str = ""
   MONETA_DEBIT_ACCOUNT: str = ""
   MONETA_SELLER_ACCOUNT: str = ""
   MONETA_SELLER_INN: str = ""
   MONETA_SELLER_NAME: str = ""
   MONETA_SELLER_PHONE: str = ""
   MONETA_MNT_ID: str = ""
   MONETA_ASSISTANT_URL: str = "https://moneta.ru/assistant.htm"
   MONETA_WIDGET_URL: str = "https://moneta.ru/assistant.widget"
   MONETA_DEMO_MODE: bool = False
   MONETA_WEBHOOK_SECRET: str = ""
   MONETA_SUCCESS_URL: str = ""
   MONETA_FAIL_URL: str = ""
   MONETA_INPROGRESS_URL: str = ""
   MONETA_RETURN_URL: str = ""
   MONETA_VAT_CODE: int = 1105
   MONETA_PAYMENT_OBJECT: str = "service"
   MONETA_PAYMENT_METHOD: str = "full_payment"
   MONETA_FORM_VERSION: str = "v3"

3. В `app/core/enums.py` добавь:
   - MONETA = "moneta" в класс PaymentProvider (StrEnum)
   - Новый enum: class PlanType(StrEnum): ENTRY_FEE = "entry_fee"; SUBSCRIPTION = "subscription"

4. В `app/models/base.py` в SAEnum PaymentProvider добавь строку 'moneta'.

5. В `app/models/subscriptions.py`:
   - К модели Plan добавь: plan_type: Mapped[str] = mapped_column(String(20), server_default="subscription", nullable=False)
   - К модели Payment добавь: moneta_operation_id: Mapped[str | None] = mapped_column(String(255))

6. Обнови `backend/.env.example` и `env.prod.example` — добавь все MONETA_* переменные с комментариями.

7. В схемах admin для планов (если есть) — добавь поле plan_type.

НЕ трогай сервисы, роутеры, webhook-обработчики.
```

---

### ПРОМПТ 2: Абстракция PaymentProvider

```
Контекст: бэкенд FastAPI + SQLAlchemy 2.0 (async). Проект: /Users/mak/trihoback/backend

Задача: создай абстракцию платёжного провайдера для модульной замены.

1. Создай директорию `app/services/payment_providers/`

2. Создай `app/services/payment_providers/base.py` с содержимым:

   from __future__ import annotations
   from abc import ABC, abstractmethod
   from dataclasses import dataclass, field
   from decimal import Decimal
   from typing import Any

   @dataclass
   class PaymentItem:
       """Одна позиция в платеже (для inventory / receipt)."""
       name: str
       price: Decimal
       quantity: int = 1
       vat_code: int | None = None
       payment_object: str = "service"
       payment_method: str = "full_payment"

   @dataclass
   class CreatePaymentResult:
       """Результат создания платежа у провайдера."""
       external_id: str
       payment_url: str
       raw_response: dict = field(default_factory=dict)

   @dataclass
   class WebhookData:
       """Распарсенные данные из входящего webhook."""
       event_type: str
       external_id: str
       transaction_id: str
       amount: Decimal
       raw_data: dict = field(default_factory=dict)

   @dataclass
   class RefundResult:
       external_id: str
       status: str
       raw_response: dict = field(default_factory=dict)

   class PaymentProvider(ABC):
       @abstractmethod
       async def create_payment(
           self,
           *,
           transaction_id: str,
           items: list[PaymentItem],
           total_amount: Decimal,
           description: str,
           customer_email: str,
           return_url: str,
           idempotency_key: str,
           metadata: dict[str, Any] | None = None,
       ) -> CreatePaymentResult:
           ...

       @abstractmethod
       async def verify_webhook(self, request_data: dict[str, Any]) -> WebhookData:
           ...

       @abstractmethod
       def build_webhook_success_response(self, request_data: dict[str, Any]) -> str:
           """Сформировать ответ на успешный webhook (SUCCESS для Moneta, '' для YooKassa)."""
           ...

       @abstractmethod
       async def create_refund(
           self,
           *,
           external_payment_id: str,
           amount: Decimal,
           items: list[PaymentItem] | None = None,
           description: str = "",
           idempotency_key: str = "",
       ) -> RefundResult:
           ...

3. Перенеси `app/services/payment_service.py` (YooKassaClient) в
   `app/services/payment_providers/yookassa_client.py`.
   - Создай класс YooKassaPaymentProvider(PaymentProvider)
   - Реализуй все абстрактные методы:
     * create_payment(): маппинг PaymentItem → receipt items, вызов YooKassa REST API
     * verify_webhook(): для YooKassa это проверка IP из YOOKASSA_IP_WHITELIST (не подпись)
       Принимает body как dict, извлекает event, object, metadata. Возвращает WebhookData.
     * build_webhook_success_response(): return "" (YooKassa не требует специального ответа)
     * create_refund(): маппинг на POST /refunds
   - Сохрани низкоуровневые методы (_request, retry) внутри класса

4. В `app/services/payment_service.py` оставь:
   from app.services.payment_providers.yookassa_client import YooKassaPaymentProvider as YooKassaClient  # noqa: F401
   (Для обратной совместимости — event_registration_service.py и subscription_service.py пока импортируют YooKassaClient оттуда)

5. Создай `app/services/payment_providers/__init__.py`:
   from app.services.payment_providers.base import (
       CreatePaymentResult, PaymentItem, PaymentProvider, RefundResult, WebhookData,
   )
   from app.core.config import settings

   def get_provider() -> PaymentProvider:
       if settings.PAYMENT_PROVIDER == "yookassa":
           from .yookassa_client import YooKassaPaymentProvider
           return YooKassaPaymentProvider()
       if settings.PAYMENT_PROVIDER == "moneta":
           raise NotImplementedError("Moneta provider will be implemented in the next step")
       raise ValueError(f"Unknown payment provider: {settings.PAYMENT_PROVIDER}")

Убедись что все файлы проходят ruff check.
НЕ трогай SubscriptionService, EventRegistrationService, webhooks.py.
```

---

### ПРОМПТ 3: MonetaClient — BPA PayAnyWay API

```
Контекст: бэкенд FastAPI + httpx. Проект: /Users/mak/trihoback/backend
Документация Moneta: docs/docs_moneta/ (файлы 09-54fz-create-invoice.md, 09-54fz-pay-invoice.md,
  09-54fz-refund.md, 07-assistant-v1-pay-notification.md, 08-payments-notification.md)
Абстракция: app/services/payment_providers/base.py уже создана (Промпт 2).

Задача: реализуй MonetaPaymentProvider.

1. Создай `app/services/payment_providers/moneta_client.py`:

   class MonetaPaymentProvider(PaymentProvider):

   a) __init__():
      - Считай настройки из settings: BPA_API_URL, BPA_KEY, BPA_SECRET, CREDIT_ACCOUNT,
        DEBIT_ACCOUNT, SELLER_ACCOUNT, SELLER_INN, SELLER_NAME, SELLER_PHONE,
        MNT_ID, ASSISTANT_URL, WIDGET_URL, DEMO_MODE, WEBHOOK_SECRET,
        SUCCESS_URL, FAIL_URL, RETURN_URL, VAT_CODE, PAYMENT_OBJECT, PAYMENT_METHOD

   b) create_payment():
      - Endpoint: POST {BPA_API_URL}/invoice?key={BPA_KEY}
      - Формирование JSON body:
        {
          "signature": md5((DEBIT_ACCOUNT or "") + transaction_id + BPA_SECRET).hexdigest(),
          "paymentAmount": float(total_amount),  # JSON number: 8000.0 (Moneta принимает JSON-числа)
          "creditMntAccount": CREDIT_ACCOUNT,
          "mntTransactionId": transaction_id,
          "customerEmail": customer_email,
          "inventory": [
            {
              "sellerAccount": SELLER_ACCOUNT,
              "sellerInn": SELLER_INN,
              "sellerName": SELLER_NAME,
              "sellerPhone": SELLER_PHONE,
              "productName": item.name,
              "productQuantity": item.quantity,
              "productPrice": float(item.price),  # JSON number: 5000.0
              "productVatCode": item.vat_code or VAT_CODE,
              "po": item.payment_object or PAYMENT_OBJECT,
              "pm": item.payment_method or PAYMENT_METHOD,
            }
            for item in items
          ]
        }
      - Если DEBIT_ACCOUNT пустой → в подписи "" (пустая строка)
      - ВАЖНО: paymentAmount ДОЛЖЕН точно равняться sum(productPrice × productQuantity) по всем inventory.
        При рассогласовании Moneta вернёт ошибку "inventoryTotal and paymentAmount are missmatch".
        Используй Decimal-арифметику для расчёта суммы, затем float() при формировании JSON.
        Строковые значения НЕ допускаются в productPrice и paymentAmount — только JSON-числа.
      - Retry: 3 попытки с задержками [1, 2, 4] при 5xx/network error
      - Обработка ответа:
        * {"operation": "12345"} → success
        * {"error": "..."} → raise AppValidationError
      - Формирование URL:
        base = "https://demo.moneta.ru/assistant.htm" if DEMO_MODE else ASSISTANT_URL
        payment_url = f"{base}?operationId={operation_id}"
        Если FORM_VERSION: payment_url += f"&version={FORM_VERSION}"  # v3 для СБП/SberPay
        Если SUCCESS_URL: payment_url += f"&MNT_SUCCESS_URL={urlencode(SUCCESS_URL)}"
        Если FAIL_URL: payment_url += f"&MNT_FAIL_URL={urlencode(FAIL_URL)}"
        Если INPROGRESS_URL: payment_url += f"&MNT_INPROGRESS_URL={urlencode(INPROGRESS_URL)}"
        Если RETURN_URL: payment_url += f"&MNT_RETURN_URL={urlencode(RETURN_URL)}"
      - Return: CreatePaymentResult(external_id=operation_id, payment_url=payment_url, raw_response=resp)

   c) verify_webhook(request_data: dict):
      - Извлечь: MNT_ID, MNT_TRANSACTION_ID, MNT_OPERATION_ID, MNT_AMOUNT,
                 MNT_CURRENCY_CODE, MNT_SUBSCRIBER_ID (может не быть), MNT_TEST_MODE, MNT_SIGNATURE
      - Вычислить expected_signature = md5(
          MNT_ID + MNT_TRANSACTION_ID + MNT_OPERATION_ID + MNT_AMOUNT
          + MNT_CURRENCY_CODE + (MNT_SUBSCRIBER_ID or "") + MNT_TEST_MODE
          + WEBHOOK_SECRET
        ).hexdigest()
      - Если MNT_SIGNATURE != expected → raise ValueError("Invalid webhook signature")
      - Return: WebhookData(
          event_type="payment.succeeded",
          external_id=MNT_OPERATION_ID,
          transaction_id=MNT_TRANSACTION_ID,  # наш Payment.id (UUID string)
          amount=Decimal(MNT_AMOUNT),
          raw_data=request_data,
        )

   d) build_webhook_success_response(request_data: dict) -> str:
      - Return "SUCCESS"  # plain text, UTF-8, без HTML
      (Для XML-ответа пока не нужно — "SUCCESS" достаточно)

   e) build_check_response(mnt_id, mnt_transaction_id, result_code, amount=None) -> str:
      - Формирует XML ответ на Check URL запрос:
        signature = md5(result_code + mnt_id + mnt_transaction_id + WEBHOOK_SECRET).hexdigest()
        return XML: <MNT_RESPONSE><MNT_ID>...</MNT_ID>...<MNT_SIGNATURE>...</MNT_SIGNATURE></MNT_RESPONSE>

   f) create_refund():
      - Пока заглушка: raise NotImplementedError("Moneta refunds via MerchantAPI — TODO")

   g) Вспомогательные методы (для будущего использования):
      - async def confirm_operation(operation_id: str) -> dict:
          POST {BPA_API_URL}/confirmoperation?key={BPA_KEY}
          body: {"signature": md5(operation_id + BPA_SECRET), "operation": operation_id}
      - async def cancel_operation(operation_id: str) -> dict: аналогично
      - async def cancel_invoice(operation_id: str, description: str) -> dict: аналогично

2. Обнови `payment_providers/__init__.py`:
   - Замени NotImplementedError для moneta на:
     from .moneta_client import MonetaPaymentProvider
     return MonetaPaymentProvider()

Используй structlog для логирования. Все HTTP-запросы через httpx.AsyncClient.
Обработка ошибок: логируй все 4xx/5xx ответы от Moneta.
```

---

### ПРОМПТ 4: Webhook-эндпоинты для Moneta

```
Контекст: бэкенд FastAPI + Redis. Проект: /Users/mak/trihoback/backend
Документация: docs/docs_moneta/07-assistant-v1-pay-notification.md, 07-assistant-v1-check-requests.md,
  08-payments-notification.md, 09-54fz-pay-invoice.md

Текущее состояние:
- app/api/v1/webhooks.py содержит POST /webhooks/yookassa
- app/services/payment_webhook_service.py обрабатывает webhook бизнес-логику
- MonetaPaymentProvider уже создан (Промпт 3)

Задача: создай три новых endpoint для Moneta.

1. В `app/api/v1/webhooks.py` добавь:

   a) POST + GET /webhooks/moneta — Pay URL (уведомление об оплате)
      - Принимает и GET (query params) и POST (form data)
      - Параметры: MNT_ID, MNT_TRANSACTION_ID, MNT_OPERATION_ID, MNT_AMOUNT,
        MNT_CURRENCY_CODE, MNT_TEST_MODE, MNT_SIGNATURE, MNT_SUBSCRIBER_ID (опц.)
      - Собери все params в dict: из request.query_params + await request.form()
      - Дедупликация: Redis key "webhook:dedup:moneta:{MNT_OPERATION_ID}" TTL 24h
      - Используй MonetaPaymentProvider.verify_webhook(params)
      - При невалидной подписи: return PlainTextResponse("FAIL", status_code=200)
      - При валидной подписи:
        * Найди Payment по id = UUID(webhook_data.transaction_id)
        * Обнови payment.moneta_operation_id = webhook_data.external_id
        * Вызови PaymentWebhookService.handle_moneta_payment_succeeded(payment)
        * return PlainTextResponse("SUCCESS", status_code=200, media_type="text/plain; charset=utf-8")
      - При ошибке: удали ключ дедупликации, return PlainTextResponse("FAIL"), log error

      ВАЖНО: Moneta повторяет уведомления до 26 часов если не получит "SUCCESS".
      При дедупликации (повторный запрос) — тоже возвращай "SUCCESS".

   b) POST + GET /webhooks/moneta/check — Check URL (проверочный запрос)
      - Принимает те же MNT_* параметры
      - Найди Payment по id = UUID(MNT_TRANSACTION_ID)
      - Если Payment найден и status=pending:
        return Response(content=xml_200, media_type="application/xml; charset=utf-8")
      - Если не найден или уже оплачен:
        return Response(content=xml_402, media_type="application/xml; charset=utf-8")
      - XML формируется через MonetaPaymentProvider.build_check_response()

   c) POST /webhooks/moneta/receipt — BPA receipt webhook
      - Принимает JSON-уведомления двух типов:
        1. Оплата: {"operation": 12345678, "receipt": "https://link_to_fiscal_receipt"}
        2. Возврат: {"operation": 12345678, "parentid": 87654321, "returnid": false, "receipt": "https://..."}
        3. Возврат без чека: {"operation": false, "parentid": 87654321, "returnid": 99999, "receipt": false}
      - Для типа 1: Найди Payment по moneta_operation_id = str(operation), создай/обнови Receipt с receipt_url
      - Для типа 2: Найди Payment по moneta_operation_id, создай Receipt с receipt_type="refund"
      - Для типа 3: Логируй и return ok (чек не сформирован, средства возвращены напрямую)
      - return {"status": "ok"}

      ВАЖНО: URL для этого endpoint настраивается через mp@payanyway.ru (не в ЛК).
      Формат json из документации BPA неоднозначен — при реализации логировать raw body и адаптировать парсинг.

2. В PaymentWebhookService добавь новый метод:
   async def handle_moneta_payment_succeeded(self, payment: Payment) -> None:
     - payment.status = PaymentStatus.SUCCEEDED
     - payment.paid_at = datetime.now(UTC)
     - Далее та же логика что в _handle_payment_succeeded:
       * entry_fee/subscription → _activate_subscription(payment)
       * event → _confirm_event_registration(payment)
     - Commit
     - Email-уведомление пользователю + Telegram админу (как сейчас)

   Не удаляй и не ломай handle_webhook() для YooKassa — он работает параллельно.
```

---

### ПРОМПТ 5: Рефакторинг SubscriptionService

```
Контекст: бэкенд FastAPI. Проект: /Users/mak/trihoback/backend

Текущее состояние:
- app/services/subscription_service.py — метод pay() использует YooKassaClient напрямую
- MonetaPaymentProvider и get_provider() уже созданы
- models/subscriptions.py: Plan теперь имеет plan_type, Payment имеет moneta_operation_id

Задача: обнови SubscriptionService для provider-agnostic работы.

1. В subscription_service.py:
   - Замени `from app.services.payment_service import YooKassaClient` на:
     `from app.services.payment_providers import get_provider, PaymentItem`
   - В __init__(): `self.provider = get_provider()` вместо `self.yookassa = YooKassaClient()`

2. Обнови метод pay(user_id, plan_id, idempotency_key):
   a) Определи product_type через _determine_product_type()
   b) Найди план по plan_id (это subscription-план, выбранный пользователем)
   c) Если product_type == "entry_fee":
      - Найди активный entry_fee план:
        entry_plan = select(Plan).where(Plan.plan_type == "entry_fee", Plan.is_active == True).first()
        Если не найден → raise AppValidationError("Вступительный взнос не настроен")
      - sub_plan = plan (тот что по plan_id)
      - total_amount = Decimal(str(entry_plan.price)) + Decimal(str(sub_plan.price))
      - items = [
          PaymentItem(name=entry_plan.name, price=Decimal(str(entry_plan.price))),
          PaymentItem(name=sub_plan.name, price=Decimal(str(sub_plan.price))),
        ]
      - description = f"{entry_plan.name} + {sub_plan.name} — Ассоциация трихологов"
      - Создай Subscription как раньше (plan_id=sub_plan.id, is_first_year=True)
      - Создай Payment с product_type="entry_fee", amount=total_amount
   d) Если product_type == "subscription":
      - items = [PaymentItem(name=plan.name, price=Decimal(str(plan.price)))]
      - total_amount = Decimal(str(plan.price))
      - description = f"{plan.name} — Ассоциация трихологов"
      - Создай Subscription + Payment как раньше

   e) Вызови provider.create_payment():
      result = await self.provider.create_payment(
          transaction_id=str(payment.id),
          items=items,
          total_amount=total_amount,
          description=description,
          customer_email=user_email,
          return_url=settings.MONETA_SUCCESS_URL or settings.YOOKASSA_RETURN_URL,
          idempotency_key=idempotency_key,
          metadata={"product_type": product_type, "user_id": str(user_id)},
      )
   f) Сохрани:
      payment.external_payment_id = result.external_id
      payment.external_payment_url = result.payment_url
      payment.payment_provider = settings.PAYMENT_PROVIDER
      Если Moneta: payment.moneta_operation_id = result.external_id

3. Обнови get_status():
   - Добавь логику для entry_fee_required:
     entry_fee_required = (await self._determine_product_type(user_id)) == ProductType.ENTRY_FEE
   - Загрузи активные планы:
     subscription_plans = select(Plan).where(Plan.plan_type == "subscription", Plan.is_active == True)
     entry_plan = select(Plan).where(Plan.plan_type == "entry_fee", Plan.is_active == True).first()
   - Верни расширенный SubscriptionStatusResponse

4. Обнови SubscriptionStatusResponse (schemas/subscriptions.py):
   - Добавь: entry_fee_required: bool = False
   - Добавь: entry_fee_plan: PlanNested | None = None
   - Добавь: available_plans: list[PlanNested] = []
   - Обнови PlanNested: добавь id: UUID, plan_type: str, price: float, duration_months: int

5. Не ломай PayResponse — формат ответа POST /subscriptions/pay тот же.
```

---

### ПРОМПТ 6: Рефакторинг EventRegistrationService

```
Контекст: бэкенд FastAPI. Проект: /Users/mak/trihoback/backend

Текущее состояние:
- app/services/event_registration_service.py использует YooKassaClient напрямую
- Метод _process_payment() формирует receipt через build_receipt() и вызывает yookassa.create_payment()
- Логика member_price уже работает корректно
- MonetaPaymentProvider и get_provider() уже созданы

Задача: обнови EventRegistrationService для provider-agnostic работы.

1. Замени `from app.services.payment_service import YooKassaClient` на:
   `from app.services.payment_providers import get_provider, PaymentItem`
   В __init__: `self.provider = get_provider()`

2. Обнови _process_payment():
   - Если applied_price <= 0: авто-подтверждение (как сейчас, без изменений)
   - Иначе:
     items = [PaymentItem(
         name=f"{event.title} — {tariff.name}",
         price=Decimal(str(applied_price)),
     )]
     customer_email = fiscal_email or receipt_email
     result = await self.provider.create_payment(
         transaction_id=str(payment.id),
         items=items,
         total_amount=Decimal(str(applied_price)),
         description=payment.description or "",
         customer_email=customer_email,
         return_url=settings.MONETA_SUCCESS_URL or settings.YOOKASSA_RETURN_URL,
         idempotency_key=payment.idempotency_key or "",
         metadata={
             "product_type": "event",
             "user_id": str(payment.user_id),
             "event_id": str(event.id),
             "registration_id": str(reg.id),
         },
     )
     payment.external_payment_id = result.external_id
     payment.external_payment_url = result.payment_url
     payment.payment_provider = settings.PAYMENT_PROVIDER
     if hasattr(result, 'external_id'):
         payment.moneta_operation_id = result.external_id
     return payment.external_payment_url

3. Обнови payment_provider в создании Payment:
   payment = Payment(
       ...
       payment_provider=settings.PAYMENT_PROVIDER,  # было: "yookassa"
       ...
   )
   То же самое для confirm_guest_registration и _register_authenticated.

4. Проверь что бесплатные мероприятия (price=0) продолжают работать без провайдера.
```

---

### ПРОМПТ 7: Тесты

```
Контекст: бэкенд FastAPI + pytest + httpx. Проект: /Users/mak/trihoback/backend

Задача: напиши тесты для интеграции с Moneta. Существующие тесты не удаляй.

1. tests/test_moneta_client.py — unit-тесты MonetaPaymentProvider:
   - test_create_invoice_success:
     Mock httpx POST → {"operation": "12345"}
     Проверь: правильный URL, payload (signature, inventory, amount), headers
     Проверь: result.external_id == "12345", result.payment_url содержит operationId=12345
   - test_create_invoice_error:
     Mock → {"error": "incorrect signature"}
     Проверь: raise AppValidationError
   - test_create_invoice_multiple_items:
     Два PaymentItem (entry_fee + subscription)
     Проверь: inventory содержит 2 позиции, paymentAmount = сумма обеих
   - test_create_invoice_demo_mode:
     settings.MONETA_DEMO_MODE = True
     Проверь: payment_url содержит "demo.moneta.ru"
   - test_create_invoice_retry_on_5xx:
     Mock: 500, 500, 200 → успех на 3-й попытке
   - test_verify_webhook_valid_signature:
     Подготовь params с правильным MNT_SIGNATURE
     Проверь: WebhookData с правильными полями
   - test_verify_webhook_invalid_signature:
     Неправильный MNT_SIGNATURE → raise ValueError
   - test_verify_webhook_missing_fields:
     Отсутствует MNT_SUBSCRIBER_ID → подставляется ""
   - test_build_check_response:
     Проверь XML-формат и подпись ответа
   - test_confirm_operation:
     Mock POST /confirmoperation → проверь signature

2. tests/test_moneta_webhook.py — integration-тесты endpoint:
   - test_pay_url_success:
     POST /webhooks/moneta с валидной подписью → Response text == "SUCCESS"
   - test_pay_url_invalid_signature:
     POST с невалидной подписью → Response text == "FAIL"
   - test_pay_url_dedup:
     Два одинаковых POST → оба "SUCCESS", Payment обновлён только раз
   - test_pay_url_activates_subscription:
     Создай Payment(product_type=subscription) → webhook → subscription.status = active
   - test_pay_url_confirms_event_registration:
     Создай Payment(product_type=event) → webhook → registration.status = confirmed
   - test_check_url_valid_order:
     POST /webhooks/moneta/check → XML с code=200 и суммой
   - test_check_url_paid_order:
     Payment.status=succeeded → XML с code=402
   - test_receipt_webhook:
     POST /webhooks/moneta/receipt с JSON → Receipt создан

3. tests/test_subscription_pay_moneta.py — бизнес-логика:
   - test_pay_entry_fee_creates_invoice_with_two_items:
     Пользователь без подписки → entry_fee → provider.create_payment с 2 items
   - test_pay_subscription_creates_one_item:
     Пользователь с подпиской → subscription → 1 item
   - test_pay_returns_moneta_url:
     Mock provider → result.payment_url содержит operationId
   - test_status_entry_fee_required:
     get_status() → entry_fee_required=true, entry_fee_plan != null
   - test_status_subscription_only:
     get_status() → entry_fee_required=false

Используй monkeypatch/mock для подмены get_provider() и HTTP-запросов.
```

---

### ПРОМПТ 8: Документация + чистка + деплой

```
Контекст: Проект: /Users/mak/trihoback

Задача: финализация.

1. В payment_service.py добавь комментарий:
   """Legacy YooKassa client. Kept for backward-compat.
   New code should use: from app.services.payment_providers import get_provider"""

2. В config.py у YOOKASSA_* настроек добавь комментарий:
   # Legacy — used when PAYMENT_PROVIDER=yookassa

3. Обнови docs/BACKEND_CHANGELOG (или создай новый):
   - Интеграция Moneta / BPA PayAnyWay
   - Абстракция PaymentProvider (модульная замена провайдера)
   - Расширение Plan.plan_type
   - Фискализация 54-ФЗ через BPA inventory
   - Три новых webhook endpoint
   - Check URL обработчик

4. Обнови env.prod.example и .env.example

5. Запусти ruff check --fix и pytest, исправь все ошибки

6. Создай git commit и push
```

---

## 6. Документация для фронтенда

### 6.1. Изменения в API (Backend → Frontend)

#### GET /api/v1/subscriptions/status — расширение ответа

```json
{
  "has_subscription": false,
  "has_paid_entry_fee": false,
  "can_renew": false,
  "entry_fee_required": true,
  "next_action": "pay_entry_fee_and_subscription",
  "current_subscription": null,
  "entry_fee_plan": {
    "id": "uuid",
    "code": "membership_fee",
    "name": "Вступительный взнос",
    "price": 3000.00,
    "plan_type": "entry_fee",
    "duration_months": 0
  },
  "available_plans": [
    {
      "id": "uuid",
      "code": "annual",
      "name": "Годовая подписка",
      "price": 5000.00,
      "plan_type": "subscription",
      "duration_months": 12
    }
  ]
}
```

**Новые поля:**
| Поле | Тип | Описание |
|------|-----|----------|
| `entry_fee_required` | `bool` | Нужен ли вступительный взнос |
| `entry_fee_plan` | `object\|null` | План вступительного взноса (если required) |
| `available_plans` | `array` | Активные планы подписки (plan_type="subscription") |

**Значения `next_action`:**
| Значение | Описание | Действие фронта |
|----------|----------|-----------------|
| `"pay_entry_fee_and_subscription"` | Нужен entry_fee + подписка | Показать обе суммы, одна кнопка «Оплатить» |
| `"pay_subscription"` | Только продление | Показать цену подписки |
| `"complete_payment"` | Есть незавершённый платёж | Показать «Завершить оплату» |
| `"renew"` | Подписка истекла (< 60 дней) | Показать «Продлить подписку» |
| `null` | Подписка активна | Показать статус |

#### POST /api/v1/subscriptions/pay — без изменений формата

Запрос:
```json
{
  "plan_id": "uuid (subscription-план, выбранный пользователем)",
  "idempotency_key": "uuid"
}
```

Ответ:
```json
{
  "payment_id": "uuid",
  "payment_url": "https://moneta.ru/assistant.htm?operationId=12345&MNT_SUCCESS_URL=...",
  "amount": 8000.00
}
```

**Важно:**
- `amount` может быть суммой entry_fee + subscription (когда entry_fee_required=true)
- `payment_url` — ссылка на платёжную форму Moneta (вместо YooKassa)
- Фронт **перенаправляет** пользователя на `payment_url`

#### POST /api/v1/events/{event_id}/register — без изменений формата

`payment_url` будет указывать на Moneta вместо YooKassa.

#### GET /api/v1/admin/plans — расширение ответа

Каждый план теперь содержит `plan_type`:
```json
{
  "id": "uuid",
  "code": "annual",
  "name": "Годовая подписка",
  "plan_type": "subscription",
  "price": 5000.00,
  "duration_months": 12,
  "is_active": true,
  "sort_order": 1
}
```

### 6.2. UX-флоу: подписка

```
┌───────────────────────────────────────────────────┐
│  Страница подписки / личный кабинет               │
│                                                     │
│  GET /subscriptions/status                          │
│         │                                           │
│         ▼                                           │
│  ┌──── entry_fee_required: true ────┐              │
│  │                                   │              │
│  │  ┌─────────────────────────────┐  │              │
│  │  │ Вступительный взнос: 3000 ₽ │  │              │
│  │  │ Годовая подписка:    5000 ₽ │  │              │
│  │  │ ─────────────────────────── │  │              │
│  │  │ Итого:              8000 ₽  │  │              │
│  │  │                             │  │              │
│  │  │ [Выбор плана: 1 год ▾]     │  │              │
│  │  │                             │  │              │
│  │  │ [ Оплатить 8000 ₽ ]        │  │              │
│  │  └─────────────────────────────┘  │              │
│  └───────────────────────────────────┘              │
│                                                     │
│  ┌──── entry_fee_required: false, can_renew ────┐  │
│  │                                               │  │
│  │  ┌─────────────────────────────┐              │  │
│  │  │ Продление подписки: 5000 ₽  │              │  │
│  │  │ [Выбор плана: 1 год ▾]     │              │  │
│  │  │ [ Оплатить 5000 ₽ ]        │              │  │
│  │  └─────────────────────────────┘              │  │
│  └───────────────────────────────────────────────┘  │
│                                                     │
│  ┌──── has_subscription: true ──────────────────┐  │
│  │  Подписка активна до 01.01.2027              │  │
│  │  Осталось: 295 дней                          │  │
│  │  (Кнопка "Продлить" если < 30 дней)          │  │
│  └──────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────┘
         │
         ▼ (нажата кнопка "Оплатить")
  POST /subscriptions/pay { plan_id, idempotency_key }
         │
         ▼
  Получить payment_url из ответа
         │
         ▼
  window.location.href = payment_url  (redirect на Moneta)
         │
         ▼
  Покупатель оплачивает на форме Moneta
         │
         ├── Успех → Success URL (MNT_TRANSACTION_ID в query)
         │   → Показать "Оплата прошла успешно!"
         │   → GET /subscriptions/status для обновления UI
         │
         ├── Неуспех → Fail URL
         │   → Показать "Оплата не прошла"
         │   → Кнопка "Попробовать снова"
         │
         └── Отказ → Return URL
             → Вернуть на страницу выбора тарифа
```

### 6.3. UX-флоу: мероприятия

```
Страница мероприятия
       │
       ▼
  Показать тарифы
       │
       ├── Авторизован (Bearer token) + активная подписка:
       │   → member_price для каждого тарифа
       │   → Бейдж "Цена для членов клуба"
       │   → Показать обе цены: "5000 ₽ (для членов)" и "зачёркнуто 8000 ₽"
       │
       ├── Авторизован без подписки:
       │   → Обычная price
       │   → Подсказка: "Станьте членом клуба и получите скидку"
       │
       └── Гость (не авторизован):
           → Обычная price
           → Guest registration flow (email verification)

       │
       ▼
  POST /api/v1/events/{id}/register { tariff_id, guest_email?, ... }
       │
       ├── price > 0:
       │   → payment_url → redirect на Moneta
       │
       └── price == 0:
           → Автоматическая регистрация без оплаты
```

### 6.4. Виджет Moneta: варианты интеграции

| Способ | URL | Описание |
|--------|-----|----------|
| **Redirect** (рекомендуется) | `assistant.htm?operationId=...` | Полная страница Moneta |
| **iframe** (виджет) | `assistant.widget?operationId=...` | Форма в iframe на вашем сайте |

**Для iframe:**
- Минимальная ширина: **320px**, рекомендуемая: **488px**
- Success/Fail/Return URL открываются **внутри iframe**
- Нужны отдельные «лёгкие» страницы для Success/Fail (без шапки сайта)
- Можно стилизовать через CSS (отправить в тех.поддержку Moneta)

**Для redirect (рекомендуется):**
- `window.location.href = payment_url`
- Success/Fail URL — обычные страницы вашего сайта

### 6.5. Callback URL-ы от Moneta

| URL | Когда | Query-параметр | Действие фронта |
|-----|-------|----------------|-----------------|
| **Success URL** | После успешной оплаты | `?MNT_TRANSACTION_ID=...` | Показать «Спасибо!», запросить статус |
| **Fail URL** | После отмены/ошибки | `?MNT_TRANSACTION_ID=...` | Показать «Ошибка», кнопка «Повторить» |
| **InProgress URL** | При незавершённой оплате (холд) | `?MNT_TRANSACTION_ID=...` | Показать «Обработка платежа...» |
| **Return URL** | При добровольном отказе | `?MNT_TRANSACTION_ID=...` | Вернуть на страницу тарифов |

**ВАЖНО:** Moneta добавляет `MNT_TRANSACTION_ID` к URL. Фронт может использовать его для:
- Проверки статуса: `GET /subscriptions/payments` с фильтром по payment_id
- Отображения детальной информации о платеже

### 6.6. Версия платёжной формы (v3)

При использовании формы v3 покупателю доступны:
- Банковские карты (российские и зарубежные)
- СБП (Система быстрых платежей)
- SberPay
- Рекуррентные платежи (в будущем)

---

## 7. Вопросы для менеджера / заказчика

### 7.1. Бизнес-логика

| # | Вопрос | Варианты | Влияние на реализацию |
|---|--------|----------|----------------------|
| 1 | Какой размер вступительного взноса? | Число | Создать Plan в БД |
| 2 | Какой размер годовой подписки? | Число | Создать Plan в БД |
| 3 | Нужен ли план на 2 года сейчас? | Да / Позже | Создать ещё Plan с duration_months=24 |
| 4 | Может ли пользователь оплатить **только** вступительный взнос, а подписку позже? | Да / Нет | Если нет — entry_fee всегда идёт вместе с подпиской. Если да — нужна дополнительная логика |
| 5 | Порог для повторного вступительного взноса: 60 дней достаточно? | Число дней | Менять LAPSE_THRESHOLD_DAYS |
| 6 | Должен ли врач видеть breakdown: «Вступительный: 3000₽ + Подписка: 5000₽ = Итого: 8000₽»? | Да / Нет | Влияет на UI + нужно вернуть entry_fee_plan в status |
| 7 | Нужна ли скидка при оплате за 2 года? | Да / Нет | Если да — просто создать Plan с price < 2×annual |
| 8 | Есть ли grace period для просроченной подписки? (сейчас 60 дней) | Число дней | Менять LAPSE_THRESHOLD_DAYS |

### 7.2. UX / Фронтенд

| # | Вопрос | Влияние |
|---|--------|---------|
| 9 | **Redirect** на Moneta или **iframe** (виджет)? | Если iframe — нужны адаптивные страницы для Success/Fail |
| 10 | Что показать после успешной оплаты? | Текст, кнопки (в профиль / на главную), auto-redirect? |
| 11 | Где страница оплаты подписки? | Отдельная страница /subscription? В профиле? В личном кабинете? |
| 12 | Нужна ли страница «История платежей»? | Уже есть API: GET /subscriptions/payments |
| 13 | Как показать мероприятие с member_price если пользователь **НЕ авторизован**? | Показать обе цены? Только полную? Подсказка «Войдите для скидки»? |
| 14 | Нужен ли «загрузочный экран» пока обрабатывается платёж? | Если да — использовать InProgress URL |
| 15 | Формат Success/Fail/Return URL (full path)? | Пример: `https://trichology.ru/payment/success` |

### 7.3. Реквизиты Moneta (нужны от заказчика / менеджера Moneta)

| # | Что нужно | Откуда | Пример |
|---|-----------|--------|--------|
| 16 | **BPA Key** (ключ партнёра) | Moneta / менеджер | `abc123...` |
| 17 | **BPA Secret** (секрет для подписи BPA invoice) | Moneta / менеджер | `secret123` |
| 18 | **creditMntAccount** (счёт приёма средств ПА) | Moneta | `60252006` |
| 19 | **sellerAccount** (бизнес-счёт продавца) | ЛК Moneta | `30990009` |
| 20 | **MNT_ID** (номер расширенного счёта) | ЛК Moneta | `11223344` |
| 21 | **Код проверки целостности** (webhook secret) | ЛК Moneta → настройки счёта | `QWERTY` |
| 22 | **ИНН организации** | Заказчик | `7712345678` |
| 23 | **Полное наименование** | Заказчик | `ООО «Ассоциация трихологов»` |
| 24 | **Телефон** (для чека ОФД) | Заказчик | `79001234567` |
| 25 | **НДС**: организация на УСН (1105) или ОСНО (1102)? | Бухгалтер | `1105` |
| 26 | **Success URL** фронтенда | Менеджер / фронтенд | `https://trichology.ru/payment/success` |
| 27 | **Fail URL** фронтенда | Менеджер / фронтенд | `https://trichology.ru/payment/fail` |
| 28 | **Return URL** фронтенда | Менеджер / фронтенд | `https://trichology.ru/subscription` |

### 7.4. Тестирование

| # | Вопрос | Рекомендация |
|---|--------|-------------|
| 29 | Нужен ли сначала тест на demo.moneta.ru? | **Да, обязательно.** Зарегистрировать ЛК магазина + ЛК покупателя на demo. Написать в business@support.payanyway.ru для активации. |
| 30 | Где настроить Pay URL / Check URL в ЛК Moneta? | ЛК → Мой счёт → Управление счетами → расширенный счёт → настройки |
| 31 | Кто настроит URL для BPA receipt-уведомлений? | Отправить URL на mp@payanyway.ru |

---

## Приложение A: Сравнение YooKassa vs Moneta

| Аспект | YooKassa (текущий) | Moneta / BPA PayAnyWay (новый) |
|--------|---------------------|--------------------------------|
| **API стиль** | REST v3, Basic Auth | POST JSON, `key` в query, MD5-подпись |
| **Создание платежа** | `POST /payments` → `confirmation_url` | `POST /invoice` → `{"operation":"…"}` → `assistant.htm?operationId=…` |
| **Подпись запроса** | Idempotence-Key header | `MD5(debitAccount + transactionId + secret)` |
| **Webhook формат** | JSON: `{event, object}` | GET/POST form: `MNT_*` params |
| **Webhook верификация** | IP whitelist | MD5-подпись |
| **Webhook ответ** | HTTP 200 (любой body) | Текст `"SUCCESS"` или XML с `MNT_RESULT_CODE=200` |
| **Фискализация** | `receipt` в create_payment | `inventory[]` в create_invoice (BPA API) |
| **Несколько товаров** | `items[]` в receipt | `inventory[]` — нативная поддержка, маршрутизация по продавцам |
| **Возврат** | `POST /refunds` | MerchantAPI `RefundRequest` + `customfield:inventory` |
| **Check URL** | Нет | XML-запрос до оплаты для проверки заказа |
| **Холдирование** | Нет (в нашей интеграции) | `hold=1`, `confirmoperation`, `canceloperation` |
| **Рекуррентные** | Нет (в нашей интеграции) | `storeCard`, `PAYMENTTOKEN` |
| **СБП** | Нет (в нашей интеграции) | Поддержка через v3 формы + `QRTTL` для QR |
| **SberPay** | Нет | Поддержка через v3 формы |
| **Retry webhook** | Не документировано | 26–27 часов повторных попыток |
| **Demo-среда** | Тестовый магазин в ЛК | `demo.moneta.ru` (отдельные счета) |

## Приложение B: Формулы подписей Moneta

```python
import hashlib

def md5_sign(*parts: str) -> str:
    """Вычислить MD5 от конкатенации строк."""
    return hashlib.md5("".join(parts).encode("utf-8")).hexdigest()

# ─── BPA API ──────────────────────────────────────────

# Создание invoice (create_invoice)
signature = md5_sign(DEBIT_ACCOUNT or "", mnt_transaction_id, BPA_SECRET)

# Подтверждение / отмена операции (confirm/cancel)
signature = md5_sign(operation_id, BPA_SECRET)

# ─── MONETA.Assistant webhook ─────────────────────────

# Проверка входящего webhook (Pay URL) — порядок из PDF-спецификации:
expected = md5_sign(
    MNT_ID,                          # номер счёта
    MNT_TRANSACTION_ID,              # ID заказа (наш payment.id)
    MNT_OPERATION_ID,                # ID операции Moneta
    MNT_AMOUNT,                      # сумма
    MNT_CURRENCY_CODE,               # RUB
    MNT_SUBSCRIBER_ID or "",         # ID покупателя (может отсутствовать)
    MNT_TEST_MODE,                   # 0 или 1
    WEBHOOK_SECRET,                  # код проверки целостности из ЛК
)

# Подпись ответа на webhook (для XML-ответа)
response_sig = md5_sign(
    MNT_RESULT_CODE,                 # "200"
    MNT_ID,                          # номер счёта
    MNT_TRANSACTION_ID,              # ID заказа
    WEBHOOK_SECRET,                  # код проверки
)
# Пример: md5("200" + "54600817" + "FF790ABCD" + "QWERTY")

# Подпись Check URL ответа — такая же как response_sig
```

## Приложение C: Статусы операций Moneta

| Статус | Описание | Маппинг на наш PaymentStatus |
|--------|----------|------------------------------|
| `CREATED` | Операция создана | `pending` |
| `INPROGRESS` | Обработка/ожидание взаимодействия | `pending` |
| `TAKENOUT` | Средства списаны | `pending` (ждём зачисления) |
| `TAKENIN_NOTSENT` | Зачислено, уведомление не отправлено | `pending` |
| `FROZEN` | Ручной разбор администраторами | `pending` |
| `SUCCEED` | Успешно завершена | `succeeded` |
| `CANCELED` | Отменена | `failed` |

## Приложение D: Коды ошибок Moneta (актуальные для нашей интеграции)

| Код | Описание | Что делать |
|-----|----------|------------|
| `400.1.5` | Оплата отменена | Не retry, пометить failed |
| `400.1.6` | Операция уже оплачена | Идемпотентность — ОК |
| `400.1.18` | Сумма не совпадает с проверочной | Баг в Check URL — проверить логику |
| `400.1.19` | Операция уже в обработке | Не retry |
| `500.1.5` | Операция не найдена | Баг — проверить operationId |
| `500.1.10` | Неверный ID заказа | Баг — проверить mntTransactionId |
| `302` | Check URL вернул HTML или redirect | Проверить endpoint Check URL |
| `-600` | Не удаётся соединиться с Check/Pay URL | Проверить доступность URL |
| `-700` | Неверный XML или подпись в ответе | Проверить формат и подпись |

## Приложение E: Inventory — пример для entry_fee + subscription

```json
{
  "signature": "a1b2c3d4e5f6...",
  "paymentAmount": 8000.00,
  "creditMntAccount": "60252006",
  "mntTransactionId": "550e8400-e29b-41d4-a716-446655440000",
  "customerEmail": "doctor@example.com",
  "inventory": [
    {
      "sellerAccount": "30990009",
      "sellerInn": "7712345678",
      "sellerName": "ООО Ассоциация трихологов",
      "sellerPhone": "79001234567",
      "productName": "Вступительный взнос",
      "productQuantity": 1,
      "productPrice": 3000.00,
      "productVatCode": 1105,
      "po": "service",
      "pm": "full_payment"
    },
    {
      "sellerAccount": "30990009",
      "sellerInn": "7712345678",
      "sellerName": "ООО Ассоциация трихологов",
      "sellerPhone": "79001234567",
      "productName": "Годовая подписка",
      "productQuantity": 1,
      "productPrice": 5000.00,
      "productVatCode": 1105,
      "po": "service",
      "pm": "full_payment"
    }
  ]
}
```

**Ответ:**
```json
{"operation": "12345678"}
```

**Редирект покупателя:**
```
https://moneta.ru/assistant.htm?operationId=12345678&MNT_SUCCESS_URL=https://trichology.ru/payment/success&MNT_FAIL_URL=https://trichology.ru/payment/fail
```
