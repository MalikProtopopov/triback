# Changelog бэкенда — Интеграция Монета (18.03.2026)

**Дата:** 18 марта 2026

---

## Обзор

Полная интеграция платёжной системы Монета (BPA PayAnyWay API) с поддержкой:
- Фискализации чеков по 54-ФЗ
- Комбинированных платежей (вступительный взнос + годовая подписка) в одной ссылке
- Модульной архитектуры для быстрой замены провайдера

---

## 1. Новая архитектура платёжных провайдеров

### Абстракция `PaymentProvider`

Создан пакет `app/services/payment_providers/` с модульной архитектурой:

| Файл | Описание |
|------|----------|
| `base.py` | ABC `PaymentProvider` + dataclass'ы: `PaymentItem`, `CreatePaymentResult`, `WebhookData`, `RefundResult` |
| `yookassa_client.py` | `YooKassaPaymentProvider` — адаптер старого клиента под новый интерфейс |
| `moneta_client.py` | `MonetaPaymentProvider` — полная реализация BPA PayAnyWay API |
| `__init__.py` | Фабрика `get_provider()` — возвращает провайдер по `settings.PAYMENT_PROVIDER` |

### Конфигурация

Переменная `PAYMENT_PROVIDER` (`"moneta"` или `"yookassa"`) определяет активный провайдер.

---

## 2. Moneta BPA PayAnyWay

### `MonetaPaymentProvider`

- **`create_payment()`** — создаёт invoice через `POST /api/invoice` с `inventory[]` для фискализации
- **`verify_webhook()`** — проверка MD5 подписи входящих вебхуков
- **`build_webhook_success_response()`** — ответ `"SUCCESS"` на Pay URL
- **`build_check_response()`** — XML ответ на Check URL (200/402)
- **`confirm_operation()`** / **`cancel_operation()`** / **`cancel_invoice()`** — управление операциями
- Retry логика (3 попытки при 5xx)
- structlog логирование всех запросов

---

## 3. Webhook-эндпоинты

### Новые маршруты в `webhooks.py`

| Метод | Путь | Описание |
|-------|------|----------|
| GET+POST | `/webhooks/moneta` | Pay URL — уведомление об оплате, проверка подписи, dedup через Redis |
| GET+POST | `/webhooks/moneta/check` | Check URL — предоплатная валидация заказа, XML ответ |
| POST | `/webhooks/moneta/receipt` | BPA receipt — сохранение чеков от фискализатора |

### Deduplication

Redis ключ: `webhook:dedup:moneta:{MNT_OPERATION_ID}` с TTL 24 часа.

---

## 4. Изменения в бизнес-логике

### SubscriptionService

- Использует `get_provider()` вместо прямого `YooKassaClient`
- **Комбинированные платежи**: если пользователю нужен вступительный взнос — создаётся один `Payment` с общей суммой и двумя `PaymentItem` в invoice
- **`get_status()`** расширен:
  - `entry_fee_required: bool` — нужен ли вступительный взнос
  - `entry_fee_plan: PlanNested | None` — план вступительного взноса
  - `available_plans: list[PlanNested]` — доступные планы подписки

### EventRegistrationService

- Использует `get_provider()` вместо прямого `YooKassaClient`
- Формирует `PaymentItem` для каждого мероприятия
- `payment_provider` берётся из `settings.PAYMENT_PROVIDER`
- Бесплатные мероприятия (price=0) — без изменений

---

## 5. Миграция БД (004)

| Изменение | Описание |
|-----------|----------|
| `payment_provider` enum | Добавлен `'moneta'` |
| `plans.plan_type` | Новая колонка `VARCHAR(20)`, default `'subscription'`, индекс `idx_plans_plan_type` |
| `plans.chk_plans_duration` | Ослаблен с `> 0` на `>= 0` (для entry_fee с duration_months=0) |
| `payments.moneta_operation_id` | Новая колонка `VARCHAR(255)`, индекс `idx_payments_moneta_op` |

---

## 6. Обновлённые схемы

### Admin API

- `PlanCreateRequest` / `PlanUpdateRequest` — добавлен `plan_type`
- `PlanAdminResponse` — добавлен `plan_type`
- `duration_months` — валидация `ge=0` вместо `gt=0`

### Client API

- `PlanNested` — расширен: `id`, `plan_type`, `price`, `duration_months`
- `SubscriptionStatusResponse` — расширен: `entry_fee_required`, `entry_fee_plan`, `available_plans`

---

## 7. Конфигурация

Добавлено 20+ переменных окружения `MONETA_*`:

```
PAYMENT_PROVIDER=moneta
MONETA_BPA_API_URL, MONETA_BPA_KEY, MONETA_BPA_SECRET
MONETA_CREDIT_ACCOUNT, MONETA_DEBIT_ACCOUNT
MONETA_SELLER_ACCOUNT, MONETA_SELLER_INN, MONETA_SELLER_NAME, MONETA_SELLER_PHONE
MONETA_MNT_ID, MONETA_ASSISTANT_URL, MONETA_WIDGET_URL, MONETA_DEMO_MODE
MONETA_WEBHOOK_SECRET
MONETA_SUCCESS_URL, MONETA_FAIL_URL, MONETA_INPROGRESS_URL, MONETA_RETURN_URL
MONETA_VAT_CODE, MONETA_PAYMENT_OBJECT, MONETA_PAYMENT_METHOD, MONETA_FORM_VERSION
```

---

## 8. Обратная совместимость

- `payment_service.py` сохранён как backward-compatible re-export: `YooKassaClient` = `YooKassaPaymentProvider`
- YooKassa webhook (`POST /webhooks/yookassa`) **не изменён** и работает параллельно
- При `PAYMENT_PROVIDER=yookassa` вся логика работает как прежде

---

## 9. Тесты

| Файл | Кол-во | Описание |
|------|--------|----------|
| `test_moneta_client.py` | 10 | Unit-тесты MonetaPaymentProvider |
| `test_moneta_webhook.py` | 8 | Integration-тесты webhook endpoints |
| `test_subscription_pay_moneta.py` | 5 | Бизнес-логика комбинированных подписок |
