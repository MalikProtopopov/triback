# API Reference

> FastAPI. Base path: `/api/v1`. Swagger: `/docs`. ReDoc: `/redoc`.
> Авторизация: JWT RS256 (access_token в cookie или header `Authorization: Bearer`).

---

## Роли

| Роль | Описание |
|------|----------|
| **admin** | Полный доступ |
| **manager** | Управление контентом, врачами, мероприятиями |
| **accountant** | Финансы, экспорты, чтение врачей |
| **doctor** | Личный кабинет, подписки, голосование |
| **user** | Базовый аккаунт |

---

## Auth (`/auth`)

| Метод | Путь | Auth | Описание |
|-------|------|------|----------|
| POST | `/register` | - | Регистрация (rate limit 5/мин) |
| POST | `/verify-email` | - | Подтверждение email |
| POST | `/resend-verification-email` | - | Повтор письма подтверждения |
| POST | `/login` | - | Логин → access_token + refresh cookie |
| POST | `/refresh` | Cookie | Обновление токенов |
| GET | `/me` | Required | Текущий пользователь (роли, sidebar, is_staff) |
| POST | `/logout` | - | Выход (отзыв refresh) |
| POST | `/logout-all` | Required | Выход со всех устройств |
| POST | `/forgot-password` | - | Запрос сброса пароля |
| POST | `/reset-password` | - | Сброс пароля по токену |
| POST | `/change-password` | Required | Смена пароля |
| POST | `/change-email` | Required | Инициация смены email |
| POST | `/confirm-email-change` | - | Подтверждение смены email |

---

## Profile (`/profile`)

| Метод | Путь | Auth | Описание |
|-------|------|------|----------|
| GET | `/personal` | Required | Персональные данные |
| PATCH | `/personal` | Required | Обновить персональные данные |
| POST | `/diploma-photo` | Required | Загрузить фото диплома |
| GET | `/public` | Required | Публичный профиль |
| PATCH | `/public` | Required | Обновить публичный профиль (модерация) |
| POST | `/public/submit` | Required | Мультипарт: фото + поля |
| POST | `/photo` | Required | Загрузить фото профиля |
| GET | `/notifications` | Required | История уведомлений |
| GET | `/event-registrations` | Required | Регистрации на мероприятия |
| GET | `/events` | Required | Подтвержденные мероприятия |

---

## Subscriptions & Payments (`/subscriptions`)

| Метод | Путь | Auth | Роль | Описание |
|-------|------|------|------|----------|
| POST | `/pay` | Required | doctor | Оплатить подписку |
| POST | `/pay-arrears` | Required | doctor | Оплатить задолженность |
| GET | `/status` | Required | doctor | Статус подписки + задолженности |
| GET | `/payments` | Required | doctor | История платежей |
| GET | `/payments/{id}/status` | - | - | Публичный статус платежа (polling) |
| POST | `/payments/{id}/check-status` | Required | doctor | Проверка через Moneta API |
| GET | `/payments/{id}/receipt` | Required | doctor | Фискальный чек |

---

## Certificates (`/certificates`)

| Метод | Путь | Auth | Роль | Описание |
|-------|------|------|------|----------|
| GET | `/` | Required | doctor | Список сертификатов |
| GET | `/{id}/download` | Required | doctor | Скачать PDF |

---

## Voting (`/voting`)

| Метод | Путь | Auth | Роль | Описание |
|-------|------|------|------|----------|
| GET | `/active` | Required | doctor | Активная сессия голосования |
| POST | `/{session_id}/vote` | Required | doctor | Проголосовать |

---

## Public API (без авторизации)

### Doctors (`/doctors`)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/` | Каталог врачей (city, specialization, board_role, search) |
| GET | `/{identifier}` | Профиль врача (UUID или slug) |

### Events (`/events`)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/` | Список мероприятий (period: upcoming/past/all) |
| GET | `/{slug}` | Детали мероприятия (тарифы, галереи, записи) |
| POST | `/{event_id}/register` | Регистрация (гость или член) |
| POST | `/{event_id}/confirm-guest` | Подтверждение гостевой регистрации |

### Articles (`/articles`)

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/` | Список опубликованных статей |
| GET | `/{slug}` | Статья с content blocks |

### Other

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/cities` | Список городов |
| GET | `/org-docs` | Уставные документы |
| GET | `/settings` | Публичные настройки сайта |
| GET | `/seo/{page_slug}` | SEO-метаданные страницы |
| GET | `/public/certificates/verify/{number}` | Проверка сертификата по QR |

---

## Admin API (`/admin`)

### Doctors (`/admin/doctors`)

| Метод | Путь | Роль | Описание |
|-------|------|------|----------|
| GET | `/` | admin/manager/accountant | Список врачей с фильтрами |
| POST | `/` | admin | Создать врача вручную |
| GET | `/{id}` | admin/manager/accountant | Детали врача |
| PATCH | `/{id}` | admin/manager/accountant | Обновить board_role |
| PATCH | `/{id}/status` | admin | Одобрить / отклонить |
| PATCH | `/{id}/payment-overrides` | admin/accountant | entry_fee_exempt |
| PATCH | `/{id}/moderation/{change_id}` | admin/manager | Модерация изменений |
| POST | `/{id}/send-email` | admin | Отправить email врачу |
| POST | `/{id}/documents/{doc_id}/download` | admin/manager/accountant | Скачать документ |
| GET | `/{id}/certificates` | admin | Сертификаты врача |
| POST | `/import/start` | admin | Импорт из CSV |
| GET | `/import/{id}/status` | admin | Статус импорта |

### Events (`/admin/events`)

| Метод | Путь | Роль | Описание |
|-------|------|------|----------|
| GET/POST | `/` | admin/manager | CRUD мероприятий |
| GET/PATCH/DELETE | `/{id}` | admin/manager | Детали / обновить / удалить |
| POST/PATCH/DELETE | `/{id}/tariffs[/{tariff_id}]` | admin/manager | CRUD тарифов |
| POST/DELETE | `/{id}/galleries[/{g_id}]` | admin/manager | CRUD галерей |
| POST/DELETE | `/{id}/galleries/{g_id}/photos[/{p_id}]` | admin/manager | CRUD фото |
| POST/PATCH/DELETE | `/{id}/recordings[/{r_id}]` | admin/manager | CRUD записей |
| GET | `/{id}/registrations` | admin/manager | Регистрации |

### Voting (`/admin/voting`)

| Метод | Путь | Роль | Описание |
|-------|------|------|----------|
| GET | `/` | admin/manager | Список голосований |
| POST | `/` | admin/manager | Создать с кандидатами |
| GET | `/{id}` | admin/manager | Детали + результаты |
| PATCH | `/{id}` | admin/manager | Обновить |

### Arrears (`/admin/membership-arrears`)

| Метод | Путь | Роль | Описание |
|-------|------|------|----------|
| GET | `/` | admin/manager/accountant | Список задолженностей |
| POST | `/` | admin | Создать |
| PATCH | `/{id}` | admin | Обновить |
| POST | `/{id}/waive` | admin | Списать |

### Payments (`/admin/payments`)

| Метод | Путь | Роль | Описание |
|-------|------|------|----------|
| GET | `/` | admin/accountant | Все платежи |
| PATCH | `/{id}/status` | admin | Изменить статус |
| POST | `/manual` | admin | Ручной платеж |

### Content

- `GET/POST/PATCH/DELETE /admin/articles` — Статьи
- `GET/POST/PATCH/DELETE /admin/org-docs` — Документы организации
- `GET/POST/PATCH/DELETE /admin/content-blocks` — Блоки контента

### Settings

- `GET/PATCH /admin/settings` — Глобальные настройки
- `GET/PATCH /admin/certificate-settings` — Настройки сертификатов
- `POST /admin/certificate-settings/{type}` — Загрузка logo/stamp/signature

### Users (`/admin/users`)

- `GET /` — Список пользователей
- `PATCH /{id}/status` — Активировать / деактивировать
- `PATCH /{id}/roles` — Изменить роли

### Protocol History (`/admin/protocol-history`)

- CRUD протоколов приема/исключения

### Telegram (`/admin/telegram`)

- `GET/PATCH /settings` — Настройки бота
- `POST /send-message` — Отправить сообщение

### Media (`/admin/media`)

- `GET /` — Медиа-библиотека
- `POST /upload` — Загрузить файл

### Exports

- `POST /exports/users/telegram` — Экспорт пользователей в Telegram
- `POST /exports/doctors/telegram` — Экспорт врачей
- `POST /exports/payments/xlsx` — Экспорт платежей XLSX

---

## Webhooks

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/webhooks/moneta/pay` | Moneta Pay URL (основной) |
| POST | `/webhooks/moneta/check` | Moneta Check URL |
| POST | `/webhooks/moneta/kassa` | Moneta Kassa (фискализация 54-ФЗ) |
| POST | `/webhooks/moneta/receipt` | Чек Moneta |
| POST | `/webhooks/yookassa/v1` | YooKassa (legacy) |
| POST | `/webhooks/yookassa/v2` | YooKassa inbox (если WEBHOOK_INBOX_ENABLED) |

---

## Health

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/health` | `{"status":"ok","db":true,"redis":true}` |
