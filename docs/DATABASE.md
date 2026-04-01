# Database Schema

> PostgreSQL 16. ORM: SQLAlchemy 2.0 (async). Миграции: Alembic.
> Модели: `backend/app/models/`

---

## ER-диаграмма (упрощенная)

```
users ─────┬──── doctor_profiles ──── doctor_documents
           │         │                doctor_profile_changes
           │         │                moderation_history
           │         │
           ├──── user_role_assignments ──── roles
           ├──── telegram_bindings
           ├──── notifications
           │
           ├──── subscriptions ──── plans
           ├──── payments ──────── receipts
           │         │
           │         └──── membership_arrears
           │
           ├──── event_registrations ──── events
           │                               ├── event_tariffs
           │                               ├── event_galleries ── event_gallery_photos
           │                               └── event_recordings
           │
           ├──── certificates
           ├──── votes ──── voting_candidates ──── voting_sessions
           │
           └──── audit_log

articles ──── article_theme_assignments ──── article_themes
content_blocks (generic, по entity_type + entity_id)
organization_documents
page_seo
cities
site_settings
certificate_settings (singleton, id=1)
telegram_integration (singleton, id=1)
protocol_history_entries
media_assets
payment_webhook_inbox
```

---

## Таблицы

### users

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID v7, PK | |
| email | String 255, unique | |
| password_hash | String 255 | bcrypt |
| email_verified_at | DateTime | null = не подтвержден |
| is_active | Boolean | Активен ли аккаунт |
| last_login_at | DateTime | |
| is_deleted / deleted_at | Boolean / DateTime | Soft delete |
| created_at / updated_at | DateTime | |

### roles

| Поле | Тип | Описание |
|------|-----|----------|
| id | SmallInt, PK | Auto |
| name | Enum: admin, manager, accountant, doctor, user | Уникальное |
| title | String 100 | Название роли |

### user_role_assignments

PK: (user_id, role_id). Связь many-to-many.

### doctor_profiles

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID v7, PK | |
| user_id | FK users, unique | 1:1 с пользователем |
| first_name / last_name / middle_name | String | ФИО |
| phone | String 20 | |
| city_id | FK cities | |
| specialization | Text | Специализация |
| clinic_name / position | String | Место работы |
| academic_degree | String | Ученая степень |
| bio | Text | Публичная биография |
| photo_url | String 500 | Фото профиля (S3) |
| public_email / public_phone | String | Публичные контакты |
| status | Enum | pending_review → approved → active / rejected / deactivated |
| slug | String 255, unique | URL-slug для публичного профиля |
| board_role | Enum: pravlenie, president, null | Роль в правлении |
| has_medical_diploma | Boolean | Наличие диплома |
| diploma_photo_url | String 500 | Фото диплома (S3) |
| entry_fee_exempt | Boolean | Освобожден от вступительного взноса |
| membership_excluded_at | DateTime | Исключен из членства |
| onboarding_submitted_at | DateTime | Дата завершения онбординга |
| is_deleted / deleted_at | | Soft delete |

**Жизненный цикл статуса:**
```
pending_review → approved → active
                         ↘ rejected
active → deactivated
```

### doctor_documents

| Поле | Тип | Описание |
|------|-----|----------|
| doctor_profile_id | FK | |
| document_type | Enum | medical_diploma, retraining_cert, oncology_cert, additional_cert |
| file_url | String 500 | S3 URL |
| original_filename | String 255 | |
| file_size / mime_type | | |

### doctor_profile_changes

Модерация изменений профиля. Уникальный partial index: одна pending-заявка на врача.

| Поле | Тип | Описание |
|------|-----|----------|
| doctor_profile_id | FK | |
| changes | JSONB | Измененные поля и значения |
| changed_fields | String[] | Список имен полей |
| status | Enum | pending → approved / rejected |
| reviewed_by | FK users | Кто проверил |
| rejection_reason | Text | |

### subscriptions

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID v7, PK | |
| user_id | FK users | |
| plan_id | FK plans | |
| status | Enum | active, expired, pending_payment, cancelled |
| is_first_year | Boolean | Первый год членства |
| starts_at / ends_at | DateTime | Период подписки |

**Constraint:** ends_at > starts_at

### plans

| Поле | Тип | Описание |
|------|-----|----------|
| code | String 50, unique | Код плана |
| name | String 255 | |
| price | Numeric(12,2) | > 0 |
| duration_months | Integer | 0 для entry_fee, 12 для annual |
| plan_type | String 20 | "subscription" или "entry_fee" |
| is_active | Boolean | |

### payments

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID v7, PK | |
| user_id | FK users | |
| amount | Numeric(12,2) | > 0 |
| product_type | Enum | entry_fee, subscription, event, membership_arrears |
| payment_provider | Enum | moneta, yookassa, psb, manual |
| status | Enum | pending → succeeded / failed / expired / refunded |
| subscription_id | FK subscriptions | Для подписок |
| event_registration_id | FK event_registrations | Для мероприятий |
| arrear_id | FK membership_arrears | Для задолженностей |
| external_payment_id | String 255 | ID в платежной системе |
| idempotency_key | String 255, unique | Идемпотентность |
| moneta_operation_id | String 255 | ID операции Moneta |
| paid_at / expires_at | DateTime | |

### receipts

Фискальные чеки (54-ФЗ). Уникальный: (payment_id, receipt_type).

| Поле | Тип | Описание |
|------|-----|----------|
| payment_id | FK payments | |
| receipt_type | Enum | payment, refund |
| amount | Numeric(12,2) | |
| status | Enum | pending, succeeded, failed |
| fiscal_number / fiscal_document / fiscal_sign | String | Фискальные данные |
| receipt_url | String 1000 | Ссылка на чек |

### membership_arrears

Задолженности по членским взносам. Уникальный partial index: один open arrear на (user_id, year).

| Поле | Тип | Описание |
|------|-----|----------|
| user_id | FK users | |
| year | Integer | 2000-2100 |
| amount | Numeric(12,2) | > 0 |
| status | Enum | open → paid / cancelled / waived |
| source | String 20 | manual, automatic |
| escalation_level | String 32 | Уровень эскалации |
| payment_id | UUID | Платеж, закрывший задолженность |
| waived_by | FK users | Кто списал |
| waive_reason | Text | |

### events

| Поле | Тип | Описание |
|------|-----|----------|
| id | UUID v7, PK | |
| title | String 500 | |
| slug | String 500, unique | |
| description | Text | |
| event_date / event_end_date | DateTime | |
| location | String 500 | |
| cover_image_url | String 500 | S3 |
| status | Enum | upcoming, ongoing, finished, cancelled |
| created_by | FK users | |
| is_deleted / deleted_at | | Soft delete |

### event_tariffs

| Поле | Тип | Описание |
|------|-----|----------|
| event_id | FK events | |
| name | String 255 | |
| price | Numeric(12,2) | Обычная цена |
| member_price | Numeric(12,2) | Цена для членов |
| seats_limit | Integer, nullable | null = без лимита |
| seats_taken | Integer | Счетчик |
| is_active | Boolean | |

### event_registrations

Уникальный: (user_id, event_id, event_tariff_id).

| Поле | Тип | Описание |
|------|-----|----------|
| user_id | FK users | |
| event_id | FK events | |
| event_tariff_id | FK event_tariffs | |
| applied_price | Numeric(12,2) | Фактическая цена |
| is_member_price | Boolean | Применена ли членская цена |
| status | Enum | pending, confirmed, cancelled |
| guest_full_name / guest_email | String | Для гостевой регистрации |
| fiscal_email | String 255 | Email для чека |

### certificates

| Поле | Тип | Описание |
|------|-----|----------|
| user_id | FK users | |
| doctor_profile_id | FK doctor_profiles | |
| certificate_type | Enum | member, event |
| year | SmallInt | 2020-2100 |
| event_id | FK events | Для event-сертификатов |
| certificate_number | String 100, unique | Формат: TRICH-YYYY-NNNNNN |
| file_url | String 500 | S3 PDF |
| is_active | Boolean | |

**Уникальные:** (doctor_profile_id, year) для member, (doctor_profile_id, event_id) для event.

### voting_sessions / voting_candidates / votes

Голосование. Один голос на (session_id, user_id).

### articles / article_themes / article_theme_assignments

Статьи с тегами. Статус: draft → published → archived.

### content_blocks

Универсальные блоки контента для любой сущности.

| Поле | Тип | Описание |
|------|-----|----------|
| entity_type | String 30 | article, event, doctor_profile, organization_document |
| entity_id | UUID | ID сущности |
| block_type | String 30 | text, image, video, gallery, link |
| sort_order | Integer | Порядок |
| content / media_url / link_url | | Данные блока |

### site_settings

Key-value хранилище (JSONB). Ключевые настройки:
- `arrears_block_membership_features` — тумблер ограничений при задолженностях
- `arrears_auto_accrual_enabled` — автоначисление задолженностей

### Синглтоны

- **certificate_settings** (id=1) — настройки шаблона сертификата (президент, печать, подпись)
- **telegram_integration** (id=1) — настройки Telegram-бота

### Вспомогательные

- **cities** — справочник городов (name, slug, is_active)
- **page_seo** — SEO-метаданные для статических страниц
- **organization_documents** — уставные документы
- **media_assets** — реестр загруженных файлов в S3
- **audit_log** — аудит всех изменений (entity_type, action, old_values, new_values)
- **moderation_history** — история действий модерации
- **notification_templates** — шаблоны уведомлений
- **notifications** — отправленные уведомления
- **protocol_history_entries** — протоколы приема/исключения
- **payment_webhook_inbox** — inbox для обработки вебхуков (retry + dedup)
