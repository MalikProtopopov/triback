# Business Logic & Workflows

> Ключевые бизнес-процессы, FSM и нюансы реализации.

---

## 1. Онбординг врача

```
Регистрация → email verification → заполнение профиля → pending_review
→ admin approve → active (публикуется в каталоге)
→ admin reject → rejected (с причиной)
```

### Нюансы

- **Модерация изменений:** Врач редактирует публичный профиль → создается `DoctorProfileChange` со статусом `pending` → админ одобряет/отклоняет. Только одна pending-заявка на врача.
- **Slug:** Генерируется автоматически из ФИО, используется в URL каталога.
- **Документы:** Диплом обязателен (`has_medical_diploma`), дополнительные сертификаты опциональны.

---

## 2. Подписка и платежи

### Продукты оплаты (product_type)

| Тип | Описание |
|-----|----------|
| `entry_fee` | Вступительный взнос (разовый, первый платеж) |
| `subscription` | Годовая подписка |
| `event` | Регистрация на мероприятие |
| `membership_arrears` | Погашение задолженности |

### FSM подписки

```
(нет подписки) → pay_entry_fee → pending_payment → succeeded → active
                                                  → failed/expired → (повтор)

active (ends_at > now) → близится к концу (< 30 дней) → can_renew = true
active (ends_at < now) → expired → need renew

expired > LAPSE_THRESHOLD_DAYS → entry_fee_required снова = true
```

### Логика определения следующего платежа

```python
# subscription_helpers.determine_product_type(db, user_id)
1. Если entry_fee_exempt → всегда subscription
2. Если не платил entry_fee → entry_fee
3. Если платил, но lapse > LAPSE_THRESHOLD_DAYS → entry_fee (повторный)
4. Иначе → subscription
```

### FSM платежа

```
pending → succeeded (webhook)
       → failed (webhook или timeout)
       → expired (PAYMENT_EXPIRATION_HOURS)

succeeded → partially_refunded / refunded (через админку)
```

### Идемпотентность

- `idempotency_key` (UUID) в каждом запросе на создание платежа
- Уникальный index в БД предотвращает дубли
- TTL: `PAYMENT_IDEMPOTENCY_TTL` (по умолчанию 86400 сек)

### Провайдеры оплаты

**Moneta (основной, `PAYMENT_PROVIDER=moneta`):**
- MerchantAPI v2 для создания платежа
- Pay URL webhook: `/webhooks/moneta/pay`
- Check URL: `/webhooks/moneta/check`
- Kassa (фискализация 54-ФЗ): `/webhooks/moneta/kassa`
- Форма оплаты: Assistant v3 (SBP, SberPay)

**YooKassa (legacy, `PAYMENT_PROVIDER=yookassa`):**
- Используется при `PAYMENT_PROVIDER=yookassa`
- Webhook v1: прямая обработка
- Webhook v2 (inbox): `WEBHOOK_INBOX_ENABLED=true`, через `payment_webhook_inbox` с retry

### Фискализация (54-ФЗ)

При `MONETA_KASSA_FISCAL_ENABLED=true`:
- Kassa Pay URL генерирует XML с данными продавца (ИНН, наименование)
- Данные: `MONETA_FISCAL_SELLER_*` переменные
- Система налогообложения: `MONETA_FISCAL_SNO` (1-6)

---

## 3. Задолженности (Arrears)

### Тумблер ограничений

Настройка `arrears_block_membership_features` в `site_settings`:

| Состояние | Поведение |
|-----------|-----------|
| **Выключен** | Врачи с задолженностями = обычные члены (все привилегии) |
| **Включен** | Врачи с open arrears теряют привилегии: |
| | — Скрыты из публичного каталога |
| | — Сертификат при верификации = `is_valid: false` |
| | — Цена мероприятий = обычная (не членская) |
| | — `arrears_block_active: true` в `/subscriptions/status` |

### FSM задолженности

```
open → paid (через платеж или manual)
     → waived (списание админом с причиной)
     → cancelled (отмена)
```

### Автоначисление

Настройка `arrears_auto_accrual_enabled` — планируется. Сейчас задолженности создаются вручную через админку.

---

## 4. Мероприятия

### Ценообразование

```python
is_member = is_association_member(db, user_id)
# Проверяет: active doctor + active subscription
# + если arrears_block включен → НЕ должно быть open arrears

price = tariff.member_price if is_member else tariff.price
```

### Регистрация

1. **Авторизованный пользователь:** автоматически определяется member/non-member цена
2. **Гость:** регистрация без аккаунта, подтверждение по email-коду
3. **Места:** `seats_limit` на тарифе, `seats_taken` инкрементируется атомарно
4. **Повторная регистрация:** если cancelled → reuse, если pending → reuse, если confirmed → ConflictError

### Галереи и записи

- Access levels: `public`, `members_only`, `participants_only`
- Записи: `uploaded` (S3) или `external` (YouTube и т.п.)

---

## 5. Сертификаты

### Типы

- **member** — членский сертификат (ежегодный, привязан к году)
- **event** — сертификат участника мероприятия

### Генерация PDF

- Шаблон с QR-кодом → `/public/certificates/verify/{number}`
- Данные из `certificate_settings` (президент, печать, подпись, логотип)
- Нумерация: `{PREFIX}-{YEAR}-{SEQUENCE}` (например `TRICH-2026-000001`)

### Верификация по QR

```
GET /public/certificates/verify/{number} (без авторизации)

is_valid = cert.is_active
         AND has_active_subscription
         AND (NOT arrears_block OR NOT has_open_arrears)
```

### Деактивация

- Scheduler: автоматическая деактивация при истечении подписки
- Админ: ручное переключение `is_active`

---

## 6. Голосование

1. Админ создает сессию (`draft` → `active` → `closed`)
2. Кандидаты — врачи с профилем
3. Каждый врач голосует один раз за сессию
4. Результаты доступны после закрытия

---

## 7. Контент

### Content Blocks

Универсальная система блоков для любой сущности:
- `entity_type`: article, event, doctor_profile, organization_document
- `block_type`: text, image, video, gallery, link
- Сортировка по `sort_order`
- Локализация: `locale` (по умолчанию "ru")

### SEO

`page_seo` — метаданные для статических страниц (og:*, twitter:card, canonical).
Для врачей и статей SEO генерируется автоматически.

---

## 8. Уведомления

Каналы: `email`, `telegram`.
Шаблоны в `notification_templates` (subject + body_template).
Статусы: `pending` → `sent` / `failed`, с `retry_count`.

### Telegram

- Привязка через auth_code (6-значный, TTL)
- Бот отправляет уведомления в привязанный чат
- Экспорты XLSX отправляются в `TELEGRAM_EXPORTS_CHAT_ID`

---

## 9. RBAC (Роли и доступы)

### Admin

Полный доступ ко всему.

### Manager

Всё кроме: управление ролями, финансовые настройки, удаление пользователей.

### Accountant

Только чтение + финансы:
- GET врачи, GET платежи, GET задолженности
- Экспорты (XLSX, Telegram)
- Нет доступа к модерации, контенту, настройкам

### Doctor

Личный кабинет:
- Профиль (личный + публичный)
- Подписки и платежи
- Сертификаты
- Голосование (в активных сессиях)
- Регистрация на мероприятия

---

## 10. Аудит

`audit_log` записывает все CRUD-операции:
- `entity_type` + `entity_id`
- `action`: create, update, delete
- `old_values` / `new_values` (JSONB)
- `user_id` + `ip_address`
