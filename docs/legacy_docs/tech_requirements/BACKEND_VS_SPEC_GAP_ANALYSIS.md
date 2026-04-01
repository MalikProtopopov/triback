# Gap Analysis: ТЗ vs Реализованный бекенд

**Дата:** 2026-03-12

Этот документ сравнивает оригинальные ТЗ (`04_Backend_API.md`, `07_Фронтенд_клиент.md`, `06_Фронтенд_админка.md`) с фактически реализованным бекендом.

---

## 1. Изменения в бизнес-логике (отличия от ТЗ)

### 1.1 Регистрация на мероприятие — ПОЛНОСТЬЮ ПЕРЕДЕЛАНО

**Было в ТЗ:**
- Один `POST /events/{id}/register` → если гость, автоматом создаётся аккаунт → сразу платёж
- Никакой верификации email

**Стало:**
- 3 сценария с верификацией email:
  1. JWT есть → прямая оплата
  2. JWT нет, email в базе → `action: "verify_existing"` → фронт показывает форму логина
  3. JWT нет, email не в базе → `action: "verify_new_email"` → код на email → `POST /confirm-guest-registration`
- Redis для кодов верификации (TTL 10 мин, max 5 попыток, max 3 отправки)
- Новый endpoint: `POST /events/{id}/confirm-guest-registration`
- Расширенная модель ответа: `RegisterForEventResponse` с полями `action`, `masked_email`

**Влияние на фронт:**
- Модалка регистрации на мероприятие должна поддерживать 3 состояния
- Нужна форма ввода 6-значного кода
- Нужна логика повторной отправки кода и retry

---

## 2. Endpoint-ы: что есть в ТЗ, но НЕ реализовано на бекенде

| Endpoint из ТЗ | Тип | Статус | Влияние |
|----------------|-----|--------|---------|
| `GET /api/v1/pages/home` | Public | **Не реализован** | Контент hero-блока и блока миссии на главной. Можно захардкодить или хранить в `site_settings` |
| `GET /api/v1/settings/public` | Public | **Не реализован** | Контакты, ссылка бота для footer/шапки. Нужен публичный endpoint без auth |
| `GET /api/v1/events/{id}/check-price` | Public | **Не реализован** | Проверка цены (member vs обычная). На практике не нужен: фронт показывает обе цены, бекенд определяет при оплате |
| Content Blocks CRUD | Admin | **Не реализован** | Модель `ContentBlock` в БД есть. Нужны API-endpoints для управления блоками из админки и получения в публичном API |
| `GET /api/v1/specializations` | Public | **Не реализован** | Справочник специализаций для фильтра. Можно использовать строковый фильтр `specialization` в `GET /doctors` |
| Admin Users CRUD | Admin | **Не реализован** | Управление ролями admin/manager/accountant. Сейчас только через БД |
| `GET /api/v1/admin/content-blocks` | Admin | **Не реализован** | CRUD контентных блоков для врачей, мероприятий, статей, документов |
| `POST /api/v1/admin/content-blocks/reorder` | Admin | **Не реализован** | Drag-and-drop порядок блоков |
| Manual payment refund | Admin | **Не реализован** | ТЗ указывает скрыть кнопку возврата. Refund не реализован |

---

## 3. Endpoint-ы: реализованы, но НЕ упомянуты в оригинальном ТЗ

| Endpoint | Описание |
|----------|----------|
| `POST /events/{id}/confirm-guest-registration` | Новый endpoint для верификации гостей (см. раздел 1.1) |
| `GET /api/v1/seo/{slug}` | Публичный доступ к SEO-данным страниц (в ТЗ было через admin) |
| `GET /robots.txt` | Автогенерация robots.txt |
| `GET /sitemap.xml` | Автогенерация sitemap |
| `POST /admin/payments/manual` | Ручное создание платежа из админки |
| `POST /admin/notifications/send` | Отправка уведомлений через админку |

---

## 4. Различия в моделях данных

### 4.1 RegisterForEventResponse (расширена)

**В ТЗ:**
```json
{ "registration_id": "UUID", "payment_url": "string", "applied_price": 10000.0, "is_member_price": false }
```

**Реализовано:**
```json
{
  "registration_id": "UUID | null",
  "payment_url": "string | null",
  "applied_price": "float | null",
  "is_member_price": "bool | null",
  "action": "string | null",       // NEW: "verify_existing" | "verify_new_email" | null
  "masked_email": "string | null"  // NEW: "t***@gmail.com"
}
```

### 4.2 ConfirmGuestRegistrationRequest (новая схема)

```json
{
  "email": "EmailStr",
  "code": "string (6 символов)",
  "tariff_id": "UUID",
  "idempotency_key": "string",
  "guest_full_name": "string | null",
  "guest_workplace": "string | null",
  "guest_specialization": "string | null",
  "fiscal_email": "EmailStr | null"
}
```

### 4.3 EventTariff (расширены поля)

Тариф мероприятия содержит дополнительные поля, которые фронт должен отображать:

| Поле | Тип | Описание |
|------|-----|----------|
| `name` | string | Название тарифа |
| `description` | string/null | Описание (что входит, для кого) |
| `conditions` | string/null | Условия применения |
| `details` | string/null | Дополнительные детали |
| `price` | float | Обычная цена |
| `member_price` | float | Цена для членов |
| `benefits` | string[]/null | Список преимуществ (иконки ✓) |
| `seats_limit` | int/null | null = без ограничений |
| `seats_taken` | int | Занято мест |
| `is_active` | bool | |
| `sort_order` | int | Порядок отображения |

---

## 5. Расхождения в ТЗ фронтенда клиента

| Раздел ТЗ | Что написано | Что реально | Что делать |
|-----------|-------------|-------------|------------|
| § 5.5 Блок 2a: Модалка | Одна модалка с полями (ФИО, email, ...) → сразу оплата | Модалка должна поддерживать 3 сценария: прямая оплата / логин / код верификации | Обновить UI модалки |
| § 5.5 Ошибка AUTH_REQUIRED | При совпадении email — toast «Войдите в аккаунт» | Бекенд возвращает `action: "verify_existing"` вместо ошибки. Фронт показывает форму логина inline | Обновить обработку |
| § 2.2 Footer контакты | `GET /admin/settings` для контактов | Этот endpoint требует auth. Нужен публичный | Задача #1 для бекенда или захардкодить |
| § 5.7.1 Content Blocks | Рендер `content_blocks` из ответов API | Content blocks не включены в публичные ответы (API не реализован) | Задача #3 для бекенда |
| § 5.5 Check-price | `GET /events/{id}/check-price?tariff_id=` при выборе тарифа | Endpoint не реализован | Фронт показывает обе цены (price + member_price), бекенд определяет при оплате |

---

## 6. Расхождения в ТЗ фронтенда админки

| Раздел ТЗ | Что написано | Что реально | Что делать |
|-----------|-------------|-------------|------------|
| § 3.6.1 Content Blocks CRUD | Полный UI для управления контентными блоками | API не реализован | Задача #3 или отложить |
| § 3.10 Администраторы | Управление ролями админов | API не реализован | Задача #5 или управление через БД |
| § 3.4 Записи конференций | Загрузка видео до 2 ГБ | Реализовано. Бекенд принимает multipart upload | OK |

---

## 7. Email-уведомления (заглушки)

Все email-таски реализованы как **заглушки** (только логирование). Для полноценной работы нужно интегрировать SMTP.

| Таска | Реализация | Что нужно |
|-------|-----------|-----------|
| `send_verification_email` | Лог | SMTP шаблон |
| `send_password_reset_email` | Лог | SMTP шаблон |
| `send_email_change_confirmation` | Лог | SMTP шаблон |
| `send_moderation_result_notification` | Лог | SMTP шаблон |
| `send_payment_succeeded_notification` | Лог | SMTP шаблон |
| `send_event_verification_code` | Лог | SMTP шаблон (код 6 цифр) |
| `send_guest_account_created` | Лог | SMTP шаблон (пароль + инструкции) |

На тесте это OK — фронт-разработчик может видеть результат в логах Docker (`docker logs triback-worker-1`).

---

## 8. Приоритеты для завершения проекта

### P0 — Критические (блокируют фронт)

1. **Публичный endpoint настроек** — `GET /api/v1/settings/public` (контакты для footer/header)
2. **Фронтенд: модалка регистрации на мероприятие** — обновить под 3 сценария
3. **Тестирование** — проверить весь flow оплаты через YooKassa sandbox

### P1 — Важные (нужны для полного функционала)

4. **Content Blocks API** — CRUD + отдача в публичных endpoints
5. **Контент главной** — решить: CMS через `site_settings` или хардкод
6. **SMTP-интеграция** — подключить реальную отправку писем

### P2 — Можно отложить

7. **Admin Users CRUD** — управление ролями админов
8. **Справочник специализаций** — отдельный endpoint
9. **Refund** — возврат платежей
