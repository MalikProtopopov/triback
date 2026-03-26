# Матрица эндпоинтов API (trihoback)

Документ сгенерирован скриптом [`scripts/generate_api_endpoint_matrix.py`](../scripts/generate_api_endpoint_matrix.py).

**OpenAPI / Swagger:** на поднятом backend — `/openapi.json`, `/docs`. Публичный стенд: [Swagger UI](https://trihoback.mediann.dev/docs#/), [openapi.json](https://trihoback.mediann.dev/openapi.json). Число операций на стенде может быть меньше, чем строк в §1, пока не выкатена текущая версия API из репозитория.

## 1. Полная таблица эндпоинтов

| Метод | Путь | Роли / доверие | Auth (JWT/роль) | Краткое описание | Side-effect (эвристика) |
|-------|------|----------------|-----------------|------------------|---------------------------|
| GET | `/api/v1/admin/article-themes` | admin, manager | Да | Список тем | Нет (чтение) |
| POST | `/api/v1/admin/article-themes` | admin, manager | Да | Создать тему | Да (обычно БД; см. §3) |
| DELETE | `/api/v1/admin/article-themes/{theme_id}` | admin | Да | Удалить тему | Да (обычно БД; см. §3) |
| PATCH | `/api/v1/admin/article-themes/{theme_id}` | admin, manager | Да | Обновить тему | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/articles` | admin, manager | Да | Список статей | Нет (чтение) |
| POST | `/api/v1/admin/articles` | admin, manager | Да | Создать статью | Да (обычно БД; см. §3) |
| DELETE | `/api/v1/admin/articles/{article_id}` | admin | Да | Удалить статью | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/articles/{article_id}` | admin, manager | Да | Детали статьи | Нет (чтение) |
| PATCH | `/api/v1/admin/articles/{article_id}` | admin, manager | Да | Обновить статью | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/certificate-settings` | admin | Да | Получить настройки сертификатов | Нет (чтение) |
| PATCH | `/api/v1/admin/certificate-settings` | admin | Да | Обновить настройки сертификатов | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/certificate-settings/background` | admin | Да | Загрузить фон/watermark для сертификата | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/certificate-settings/logo` | admin | Да | Загрузить логотип для сертификата | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/certificate-settings/regenerate-all` | admin | Да | Перегенерировать все активные сертификаты текущего года | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/certificate-settings/signature` | admin | Да | Загрузить подпись для сертификата | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/certificate-settings/stamp` | admin | Да | Загрузить печать для сертификата | Да (обычно БД; см. §3) |
| PATCH | `/api/v1/admin/certificates/{certificate_id}` | admin | Да | Обновить статус сертификата | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/certificates/{certificate_id}/download` | admin, manager | Да | Скачать/предпросмотр сертификата | Нет (чтение) |
| GET | `/api/v1/admin/cities` | admin, manager | Да | Список городов | Нет (чтение) |
| POST | `/api/v1/admin/cities` | admin, manager | Да | Создать город | Да (обычно БД; см. §3) |
| DELETE | `/api/v1/admin/cities/{city_id}` | admin | Да | Удалить город | Да (обычно БД; см. §3) |
| PATCH | `/api/v1/admin/cities/{city_id}` | admin, manager | Да | Обновить город | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/content-blocks` | admin, manager | Да | Список контентных блоков | Нет (чтение) |
| POST | `/api/v1/admin/content-blocks` | admin, manager | Да | Создать контентный блок | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/content-blocks/reorder` | admin, manager | Да | Перестановка блоков | Да (обычно БД; см. §3) |
| DELETE | `/api/v1/admin/content-blocks/{block_id}` | admin, manager | Да | Удалить контентный блок | Да (обычно БД; см. §3) |
| PATCH | `/api/v1/admin/content-blocks/{block_id}` | admin, manager | Да | Обновить контентный блок | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/dashboard` | admin, manager | Да | Сводная статистика | Нет (чтение) |
| GET | `/api/v1/admin/doctors` | admin, manager | Да | Список врачей | Нет (чтение) |
| POST | `/api/v1/admin/doctors` | admin | Да | Создать врача вручную | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/doctors/import` | admin | Да | Импорт врачей из Excel | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/doctors/import/{task_id}` | admin | Да | Статус импорта | Нет (чтение) |
| GET | `/api/v1/admin/doctors/{doctor_id}/certificates` | admin, manager | Да | Список сертификатов врача | Нет (чтение) |
| POST | `/api/v1/admin/doctors/{doctor_id}/certificates/regenerate` | admin, manager | Да | Перегенерировать сертификат врача | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/doctors/{profile_id}` | admin, manager | Да | Детали врача | Нет (чтение) |
| PATCH | `/api/v1/admin/doctors/{profile_id}` | admin, manager | Да | Обновить роль в правлении | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/doctors/{profile_id}/approve-draft` | admin, manager | Да | Одобрить черновик изменений | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/doctors/{profile_id}/moderate` | admin, manager | Да | Модерация врача | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/doctors/{profile_id}/send-email` | admin, manager | Да | Отправить email | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/doctors/{profile_id}/send-reminder` | admin, manager | Да | Отправить напоминание | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/doctors/{profile_id}/toggle-active` | admin, manager | Да | Активировать/деактивировать профиль | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/events` | admin, manager | Да | Список мероприятий | Нет (чтение) |
| POST | `/api/v1/admin/events` | admin, manager | Да | Создать мероприятие | Да (обычно БД; см. §3) |
| DELETE | `/api/v1/admin/events/{event_id}` | admin | Да | Удалить мероприятие | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/events/{event_id}` | admin, manager | Да | Детали мероприятия | Нет (чтение) |
| PATCH | `/api/v1/admin/events/{event_id}` | admin, manager | Да | Обновить мероприятие | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/events/{event_id}/galleries` | admin, manager | Да | Создать галерею | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/events/{event_id}/galleries/{gallery_id}/photos` | admin, manager | Да | Загрузить фото в галерею | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/events/{event_id}/recordings` | admin, manager | Да | Добавить запись | Да (обычно БД; см. §3) |
| PATCH | `/api/v1/admin/events/{event_id}/recordings/{recording_id}` | admin, manager | Да | Обновить запись | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/events/{event_id}/registrations` | admin, manager | Да | Список регистраций | Нет (чтение) |
| POST | `/api/v1/admin/events/{event_id}/tariffs` | admin, manager | Да | Добавить тариф | Да (обычно БД; см. §3) |
| DELETE | `/api/v1/admin/events/{event_id}/tariffs/{tariff_id}` | admin | Да | Удалить тариф | Да (обычно БД; см. §3) |
| PATCH | `/api/v1/admin/events/{event_id}/tariffs/{tariff_id}` | admin, manager | Да | Обновить тариф | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/notifications` | admin, manager | Да | Журнал уведомлений | Нет (чтение) |
| POST | `/api/v1/admin/notifications/send` | admin, manager | Да | Отправить уведомление | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/organization-documents` | admin, manager | Да | Список документов организации | Нет (чтение) |
| POST | `/api/v1/admin/organization-documents` | admin, manager | Да | Создать документ | Да (обычно БД; см. §3) |
| PATCH | `/api/v1/admin/organization-documents/reorder` | admin, manager | Да | Перестановка документов | Да (обычно БД; см. §3) |
| DELETE | `/api/v1/admin/organization-documents/{doc_id}` | admin | Да | Удалить документ | Да (обычно БД; см. §3) |
| PATCH | `/api/v1/admin/organization-documents/{doc_id}` | admin, manager | Да | Обновить документ | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/payments` | admin, manager, accountant | Да | Список платежей | Нет (чтение) |
| POST | `/api/v1/admin/payments/manual` | admin, accountant | Да | Ручной платёж | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/payments/{payment_id}/cancel` | admin, accountant | Да | Отмена платежа | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/payments/{payment_id}/confirm` | admin, accountant | Да | Ручное подтверждение платежа (dev/test) | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/payments/{payment_id}/refund` | admin, accountant | Да | Возврат платежа | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/plans` | admin | Да | Список тарифных планов | Нет (чтение) |
| POST | `/api/v1/admin/plans` | admin | Да | Создать план | Да (обычно БД; см. §3) |
| DELETE | `/api/v1/admin/plans/{plan_id}` | admin | Да | Удалить план | Да (обычно БД; см. §3) |
| PATCH | `/api/v1/admin/plans/{plan_id}` | admin | Да | Обновить план | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/portal-users` | admin, manager | Да | Список пользователей портала | Нет (чтение) |
| GET | `/api/v1/admin/portal-users/{user_id}` | admin, manager | Да | Детали пользователя портала | Нет (чтение) |
| GET | `/api/v1/admin/seo-pages` | admin, manager | Да | Список SEO-страниц | Нет (чтение) |
| POST | `/api/v1/admin/seo-pages` | admin, manager | Да | Создать SEO-страницу | Да (обычно БД; см. §3) |
| DELETE | `/api/v1/admin/seo-pages/{slug}` | admin, manager | Да | Удалить SEO-страницу | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/seo-pages/{slug}` | admin, manager | Да | SEO-страница по slug | Нет (чтение) |
| PATCH | `/api/v1/admin/seo-pages/{slug}` | admin, manager | Да | Обновить SEO-страницу | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/settings` | admin | Да | Получить настройки | Нет (чтение) |
| PATCH | `/api/v1/admin/settings` | admin | Да | Обновить настройки | Да (обычно БД; см. §3) |
| DELETE | `/api/v1/admin/telegram/integration` | admin, manager | Да | Удалить Telegram-интеграцию | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/telegram/integration` | admin, manager | Да | Получить настройки Telegram | Нет (чтение) |
| PATCH | `/api/v1/admin/telegram/integration` | admin, manager | Да | Обновить Telegram-интеграцию (частично) | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/telegram/integration` | admin, manager | Да | Создать/обновить Telegram-интеграцию | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/telegram/integration/test` | admin, manager | Да | Отправить тестовое сообщение | Да (обычно БД; см. §3) |
| DELETE | `/api/v1/admin/telegram/integration/webhook` | admin, manager | Да | Удалить webhook | Да (обычно БД; см. §3) |
| POST | `/api/v1/admin/telegram/integration/webhook` | admin, manager | Да | Установить webhook | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/telegram/integration/webhook-url` | admin, manager | Да | URL для webhook | Нет (чтение) |
| GET | `/api/v1/admin/users` | admin | Да | Список сотрудников | Нет (чтение) |
| POST | `/api/v1/admin/users` | admin | Да | Создать сотрудника | Да (обычно БД; см. §3) |
| DELETE | `/api/v1/admin/users/{user_id}` | admin | Да | Удалить сотрудника | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/users/{user_id}` | admin | Да | Детали сотрудника | Нет (чтение) |
| PATCH | `/api/v1/admin/users/{user_id}` | admin | Да | Обновить сотрудника | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/voting` | admin, manager | Да | Список голосований | Нет (чтение) |
| POST | `/api/v1/admin/voting` | admin, manager | Да | Создать голосование | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/voting/{session_id}` | admin, manager | Да | Детали голосования | Нет (чтение) |
| PATCH | `/api/v1/admin/voting/{session_id}` | admin, manager | Да | Обновить голосование | Да (обычно БД; см. §3) |
| GET | `/api/v1/admin/voting/{session_id}/results` | admin, manager | Да | Результаты голосования | Нет (чтение) |
| GET | `/api/v1/article-themes` | — | Нет | Список тем статей | Нет (чтение) |
| GET | `/api/v1/articles` | — | Нет | Список статей | Нет (чтение) |
| GET | `/api/v1/articles/{slug}` | — | Нет | Статья по slug | Нет (чтение) |
| POST | `/api/v1/auth/change-email` | любая роль из JWT (doctor / user / admin / manager / accountant) | Да | Запрос смены email | Да (обычно БД; см. §3) |
| POST | `/api/v1/auth/change-password` | любая роль из JWT (doctor / user / admin / manager / accountant) | Да | Смена пароля | Да (обычно БД; см. §3) |
| POST | `/api/v1/auth/confirm-email-change` | — | Нет | Подтверждение смены email | Да (обычно БД; см. §3) |
| POST | `/api/v1/auth/forgot-password` | — | Нет | Запрос сброса пароля | Да (обычно БД; см. §3) |
| POST | `/api/v1/auth/login` | — | Нет | Авторизация | Да (обычно БД; см. §3) |
| POST | `/api/v1/auth/logout` | — | Нет | Выход из системы | Да (обычно БД; см. §3) |
| POST | `/api/v1/auth/logout-all` | любая роль из JWT (doctor / user / admin / manager / accountant) | Да | Выйти на всех устройствах | Да (обычно БД; см. §3) |
| GET | `/api/v1/auth/me` | любая роль из JWT (doctor / user / admin / manager / accountant) | Да | Текущий пользователь | Нет (чтение) |
| POST | `/api/v1/auth/refresh` | — | Нет | Обновление токена | Да (обычно БД; см. §3) |
| POST | `/api/v1/auth/register` | — | Нет | Регистрация нового пользователя | Да (обычно БД; см. §3) |
| POST | `/api/v1/auth/resend-verification-email` | — | Нет | Повторная отправка письма подтверждения | Да (обычно БД; см. §3) |
| POST | `/api/v1/auth/reset-password` | — | Нет | Сброс пароля по токену | Да (обычно БД; см. §3) |
| POST | `/api/v1/auth/verify-email` | — | Нет | Подтверждение email | Да (обычно БД; см. §3) |
| GET | `/api/v1/certificates` | doctor | Да | Список сертификатов | Нет (чтение) |
| GET | `/api/v1/certificates/{certificate_id}/download` | doctor | Да | Скачать сертификат | Нет (чтение) |
| GET | `/api/v1/cities` | — | Нет | Список городов | Нет (чтение) |
| GET | `/api/v1/cities/{slug}` | — | Нет | Город по slug | Нет (чтение) |
| GET | `/api/v1/colleagues` | doctor | Да | Список коллег | Нет (чтение) |
| GET | `/api/v1/doctors` | — | Нет | Каталог врачей | Нет (чтение) |
| GET | `/api/v1/doctors/{identifier}` | — | Нет | Профиль врача | Нет (чтение) |
| GET | `/api/v1/events` | — | Нет | Список мероприятий | Нет (чтение) |
| POST | `/api/v1/events/{event_id}/confirm-guest-registration` | — | Нет | Подтверждение гостевой регистрации | Да (обычно БД; см. §3) |
| GET | `/api/v1/events/{event_id}/galleries` | публично; опционально JWT — см. §2 | Нет (опц. JWT) | Галереи мероприятия | Нет (чтение) |
| GET | `/api/v1/events/{event_id}/recordings` | публично; опционально JWT — см. §2 | Нет (опц. JWT) | Записи мероприятия | Нет (чтение) |
| POST | `/api/v1/events/{event_id}/register` | публично; опционально JWT — см. §2 | Нет (опц. JWT) | Регистрация на мероприятие | Да (обычно БД; см. §3) |
| GET | `/api/v1/events/{slug}` | — | Нет | Детали мероприятия | Нет (чтение) |
| GET | `/api/v1/health` | — | Нет |  | Нет (чтение) |
| POST | `/api/v1/onboarding/choose-role` | любая роль из JWT (doctor / user / admin / manager / accountant) | Да | Выбор роли | Да (обычно БД; см. §3) |
| PATCH | `/api/v1/onboarding/doctor-profile` | любая роль из JWT (doctor / user / admin / manager / accountant) | Да | Заполнение анкеты врача | Да (обычно БД; см. §3) |
| POST | `/api/v1/onboarding/documents` | любая роль из JWT (doctor / user / admin / manager / accountant) | Да | Загрузка документа | Да (обычно БД; см. §3) |
| GET | `/api/v1/onboarding/status` | любая роль из JWT (doctor / user / admin / manager / accountant) | Да | Статус онбординга | Нет (чтение) |
| POST | `/api/v1/onboarding/submit` | любая роль из JWT (doctor / user / admin / manager / accountant) | Да | Отправка на модерацию | Да (обычно БД; см. §3) |
| GET | `/api/v1/organization-documents` | — | Нет | Документы организации | Нет (чтение) |
| GET | `/api/v1/organization-documents/{slug}` | — | Нет | Документ организации по slug | Нет (чтение) |
| POST | `/api/v1/profile/diploma-photo` | любая роль из JWT (doctor / user / admin / manager / accountant) | Да | Загрузка фото диплома | Да (обычно БД; см. §3) |
| GET | `/api/v1/profile/events` | любая роль из JWT (doctor / user / admin / manager / accountant) | Да | Мои мероприятия | Нет (чтение) |
| GET | `/api/v1/profile/personal` | любая роль из JWT (doctor / user / admin / manager / accountant) | Да | Личные данные | Нет (чтение) |
| PATCH | `/api/v1/profile/personal` | любая роль из JWT (doctor / user / admin / manager / accountant) | Да | Обновить личные данные | Да (обычно БД; см. §3) |
| POST | `/api/v1/profile/photo` | любая роль из JWT (doctor / user / admin / manager / accountant) | Да | Загрузка фото профиля | Да (обычно БД; см. §3) |
| GET | `/api/v1/profile/public` | любая роль из JWT (doctor / user / admin / manager / accountant) | Да | Публичный профиль | Нет (чтение) |
| PATCH | `/api/v1/profile/public` | любая роль из JWT (doctor / user / admin / manager / accountant) | Да | Обновить публичный профиль | Да (обычно БД; см. §3) |
| GET | `/api/v1/public/certificates/verify/{certificate_number}` | — | Нет | Проверка сертификата по номеру | Нет (чтение) |
| GET | `/api/v1/seo/{slug}` | — | Нет | SEO-метаданные страницы | Нет (чтение) |
| GET | `/api/v1/settings/public` | — | Нет | Публичные настройки | Нет (чтение) |
| POST | `/api/v1/subscriptions/pay` | doctor | Да | Оплата членского взноса | Да (обычно БД; см. §3) |
| GET | `/api/v1/subscriptions/payments` | doctor | Да | История платежей | Нет (чтение) |
| POST | `/api/v1/subscriptions/payments/{payment_id}/check-status` | doctor | Да | Проверка статуса платежа через Moneta API | Да (обычно БД; см. §3) |
| GET | `/api/v1/subscriptions/payments/{payment_id}/receipt` | doctor | Да | Чек по платежу | Нет (чтение) |
| GET | `/api/v1/subscriptions/payments/{payment_id}/status` | — | Нет | Статус платежа (публичный) | Нет (чтение) |
| GET | `/api/v1/subscriptions/status` | doctor | Да | Статус подписки | Нет (чтение) |
| GET | `/api/v1/telegram/binding` | doctor, user | Да | Статус привязки Telegram | Нет (чтение) |
| POST | `/api/v1/telegram/generate-code` | doctor, user | Да | Сгенерировать код привязки | Да (обычно БД; см. §3) |
| POST | `/api/v1/telegram/webhook` | Telegram (legacy; без JWT) | Спец. | Telegram bot webhook (legacy env-based) | Да (обычно БД; см. §3) |
| POST | `/api/v1/telegram/webhook/{webhook_secret}` | Секрет в пути (`TELEGRAM_WEBHOOK_SECRET`) | Спец. | Telegram bot webhook (secret in URL) | Да (обычно БД; см. §3) |
| GET | `/api/v1/voting/active` | doctor | Да | Активное голосование | Нет (чтение) |
| POST | `/api/v1/voting/{session_id}/vote` | doctor | Да | Отдать голос | Да (обычно БД; см. §3) |
| GET | `/api/v1/webhooks/moneta` | Подпись Moneta Pay URL (MD5) + dedup Redis | Спец. | Moneta Pay URL webhook | Да (обработка уведомления; см. §3) |
| POST | `/api/v1/webhooks/moneta` | Подпись Moneta Pay URL (MD5) + dedup Redis | Спец. | Moneta Pay URL webhook | Да (обработка уведомления; см. §3) |
| GET | `/api/v1/webhooks/moneta/check` | Подпись Moneta Check URL (MD5) | Спец. | Moneta Check URL | Да (обработка уведомления; см. §3) |
| POST | `/api/v1/webhooks/moneta/check` | Подпись Moneta Check URL (MD5) | Спец. | Moneta Check URL | Да (обработка уведомления; см. §3) |
| POST | `/api/v1/webhooks/moneta/receipt` | Заголовок `X-Moneta-Receipt-Secret` и/или `MONETA_RECEIPT_IP_ALLOWLIST` | Спец. | Moneta receipt webhook | Да (обработка уведомления; см. §3) |
| POST | `/api/v1/webhooks/yookassa` | IP allowlist `YOOKASSA_IP_WHITELIST` (+ dedup Redis) | Спец. | YooKassa webhook | Да (обработка уведомления; см. §3) |
| POST | `/api/v1/webhooks/yookassa/v2` | Feature flag; IP allowlist; inbox + TaskIQ | Спец. | YooKassa webhook v2 (inbox + TaskIQ) | Да (обработка уведомления; см. §3) |
| GET | `/robots.txt` | — | Нет |  | Нет (чтение) |
| GET | `/sitemap.xml` | — | Нет |  | Да (кеш Redis при промахе) |

## 2. Нетривиальная матрица доступа

Здесь — случаи, когда **одной роли из таблицы недостаточно**: ответ или допуск зависят от состояния объекта, опционального токена или внешней подписи.

| Эндпоинт | Условие | Поведение |
|----------|---------|-----------|
| `GET/POST` `/api/v1/events/{id}/register` | Есть валидный JWT | Регистрация авторизованного пользователя; без токена — сценарий гостя / `login_required` |
| `GET/POST` `/api/v1/events/{id}/register` | Нет JWT, не передан guest-поток | Возможен **422** (нужен email и т.д.) |
| `GET` `/api/v1/events/{event_id}/galleries`, `/recordings` | `access_level` members_only / participants_only | Контент скрыт без активной подписки или подтверждённой регистрации на это событие |
| `POST` `/api/v1/voting/{session_id}/vote` | JWT роль `doctor` | Дополнительно: **403**, если нет активного членства (подписка) — см. `voting_service` |
| `GET` … `/subscriptions/payments/...`, `check-status` | JWT `doctor` | Платёж должен принадлежать текущему пользователю; иначе **403** (`payment_status_service`) |
| `GET` … `/certificates` (ЛК) | JWT `doctor` | Сертификаты только для активных врачей; иначе **403** |
| `POST` `/api/v1/webhooks/yookassa` | IP не в whitelist | **403** |
| `POST` `/api/v1/webhooks/moneta/receipt` | Prod без секрета и allowlist | **403** |
| `POST` `/api/v1/webhooks/yookassa/v2` | `WEBHOOK_INBOX_ENABLED=false` | **404** |
| Админ `DELETE` части контента (статьи, темы, …) | См. код | Часть операций только **`admin`**, хотя PATCH/GET — admin+manager |

_Уточняйте по сервисам: `event_public_service`, `event_registration_service`, `voting_service`, `payment_status_service`, `certificate_service`._

## 3. Side-эффекты (важные для тестирования)

### 3.1 Всегда с побочными эффектами

- **Все** `POST` / `PUT` / `PATCH` / `DELETE` в админке и ЛК (запись в БД, часто S3 для файлов).
- **Auth:** регистрация, сброс пароля, смена email — отправка писем (SMTP / очередь).
- **Webhooks Moneta:** Pay URL — обновление платежа, подписки, регистрации; Check URL — XML, возможны commit полей Moneta operation id; Receipt — запись чека, задачи email/Telegram.
- **Webhooks YooKassa:** обработка события, Redis dedup.
- **Admin:** `POST .../notifications/send`, ручные платежи / refund / cancel, импорт врачей, модерация, генерация сертификатов.

### 3.2 GET с эффектами

- `GET /sitemap.xml` — при промахе кеша пересборка и запись в Redis.
- Остальные `GET` по умолчанию только чтение (кеш Redis на публичных списках возможен — см. сервисы).

### 3.3 Rate limit (отдельно от RBAC)

- Часть маршрутов помечена `slowapi` (например auth, публичные события, YooKassa legacy webhook).
- Эндпоинты **Moneta** Pay / Check / receipt **без** лимита (серверные вызовы Moneta).

