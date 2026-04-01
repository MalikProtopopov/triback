# Environment Variables

> Шаблон: `env.prod.example` (корень репозитория).
> Dev: `backend/.env`. Prod: `.env.prod` (корень, НЕ коммитить).
> Конфиг: `backend/app/core/config.py`

---

## Domains & URLs

| Переменная | Пример | Описание |
|------------|--------|----------|
| `API_DOMAIN` | `api.trichologia.ru` | Домен API (nginx, SSL, healthcheck) |
| `PUBLIC_API_URL` | `https://api.trichologia.ru` | Абсолютный URL для ссылок в ответах |
| `FRONTEND_URL` | `https://trichologia.ru` | URL клиентского сайта |
| `ADMIN_FRONTEND_URL` | `https://admin.trichologia.ru` | URL админки |
| `CERT_EMAIL` | `admin@trichologia.ru` | Email для Let's Encrypt |

## CORS

| Переменная | Пример | Описание |
|------------|--------|----------|
| `CORS_ALLOWED_ORIGINS` | `["https://trichologia.ru","https://admin.trichologia.ru"]` | JSON-массив или comma-separated |
| (legacy alias) `ALLOWED_HOSTS` | то же | Совместимость |

## Application

| Переменная | Default | Описание |
|------------|---------|----------|
| `DEBUG` | `false` | Режим отладки (в prod = false!) |
| `SECRET_KEY` | - | Секрет для подписей (`openssl rand -hex 32`) |
| `ENCRYPTION_KEY` | - | Fernet ключ для шифрования (bot tokens) |

## JWT (RS256)

| Переменная | Default | Описание |
|------------|---------|----------|
| `JWT_PRIVATE_KEY_PATH` | `keys/private.pem` | Приватный ключ |
| `JWT_PUBLIC_KEY_PATH` | `keys/public.pem` | Публичный ключ |
| `JWT_AUDIENCE` | `trihoback-api` | |
| `JWT_ISSUER` | `trihoback` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Время жизни access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Время жизни refresh token |

## Database

| Переменная | Пример | Описание |
|------------|--------|----------|
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@postgres:5432/db` | Async PostgreSQL |
| `POSTGRES_USER` | `triho_user` | Для docker postgres |
| `POSTGRES_PASSWORD` | - | |
| `POSTGRES_DB` | `triho_db` | |

## Redis

| Переменная | Пример | Описание |
|------------|--------|----------|
| `REDIS_URL` | `redis://redis:6379/0` | Кэш, токены, очереди |

## S3 / MinIO

| Переменная | Пример | Описание |
|------------|--------|----------|
| `S3_ENDPOINT_URL` | `http://minio:9000` | Endpoint S3 |
| `S3_ACCESS_KEY` | - | |
| `S3_SECRET_KEY` | - | |
| `S3_BUCKET` | `triho-prod` | |
| `S3_PUBLIC_URL` | `https://api.trichologia.ru/media` | Публичный URL для файлов |

## Moneta (основной провайдер)

| Переменная | Описание |
|------------|----------|
| `PAYMENT_PROVIDER` | `moneta` или `yookassa` |
| `MONETA_USERNAME` / `MONETA_PASSWORD` | Логин/пароль MerchantAPI v2 |
| `MONETA_SERVICE_URL` | `https://service.moneta.ru/services` |
| `MONETA_PAYEE_ACCOUNT` | Расширенный счет получателя |
| `MONETA_PAYMENT_PASSWORD` | Пароль оплаты |
| `MONETA_MNT_ID` | ID мерчанта для Assistant |
| `MONETA_ASSISTANT_URL` | URL формы оплаты |
| `MONETA_WIDGET_URL` | URL виджета |
| `MONETA_DEMO_MODE` | `true` = тестовый режим |
| `MONETA_WEBHOOK_SECRET` | Секрет вебхуков Pay URL |
| `MONETA_SUCCESS_URL` | Редирект при успехе |
| `MONETA_FAIL_URL` | Редирект при ошибке |
| `MONETA_INPROGRESS_URL` | Редирект "ожидание" |
| `MONETA_RETURN_URL` | Возврат в ЛК |
| `MONETA_FORM_VERSION` | `v3` (SBP, SberPay) |

### Moneta Kassa (54-ФЗ)

| Переменная | Описание |
|------------|----------|
| `MONETA_KASSA_FISCAL_ENABLED` | `true` = включить фискализацию |
| `MONETA_FISCAL_SELLER_INN` | ИНН продавца |
| `MONETA_FISCAL_SELLER_NAME` | Наименование |
| `MONETA_FISCAL_SELLER_PHONE` | Телефон |
| `MONETA_FISCAL_SELLER_ACCOUNT` | Счет |
| `MONETA_FISCAL_SNO` | Система налогообложения (1-6) |

### Moneta Receipt Webhook

| Переменная | Описание |
|------------|----------|
| `MONETA_RECEIPT_WEBHOOK_SECRET` | Секрет заголовка `X-Moneta-Receipt-Secret` |
| `MONETA_RECEIPT_IP_ALLOWLIST` | CIDR-список IP (альтернатива секрету) |

## YooKassa (legacy)

| Переменная | Описание |
|------------|----------|
| `YOOKASSA_SHOP_ID` | |
| `YOOKASSA_SECRET_KEY` | |
| `YOOKASSA_RETURN_URL` | |
| `YOOKASSA_IP_WHITELIST` | CIDR подсетей YooKassa |
| `YOOKASSA_WEBHOOK_VERIFY_WITH_API` | `true` в production |

## Payments (общее)

| Переменная | Default | Описание |
|------------|---------|----------|
| `WEBHOOK_INBOX_ENABLED` | `false` | Inbox pipeline для YooKassa v2 |
| `PAYMENT_IDEMPOTENCY_TTL` | `86400` | TTL идемпотентности (сек) |
| `PAYMENT_EXPIRATION_HOURS` | `24` | Срок жизни pending-платежа |

## SMTP

| Переменная | Описание |
|------------|----------|
| `SMTP_HOST` | Хост SMTP сервера |
| `SMTP_PORT` | Порт (465 для SSL, 587 для STARTTLS) |
| `SMTP_USER` | |
| `SMTP_PASSWORD` | |
| `SMTP_FROM` | Адрес отправителя |
| `SMTP_TLS` | `true` для SSL |

## Telegram

| Переменная | Описание |
|------------|----------|
| `TELEGRAM_BOT_TOKEN` | Токен бота |
| `TELEGRAM_CHANNEL_ID` | Канал уведомлений |
| `TELEGRAM_EXPORTS_CHAT_ID` | Чат для XLSX экспортов |
| `TELEGRAM_WEBHOOK_SECRET` | Секрет вебхука |

## Cookies

| Переменная | Default | Описание |
|------------|---------|----------|
| `COOKIE_DOMAIN` | null | `.trichologia.ru` для cross-subdomain |
| `ACCESS_TOKEN_COOKIE_SAMESITE` | `none` | `none` для cross-origin SPA, `lax` для same-site |

## Certificates

| Переменная | Default | Описание |
|------------|---------|----------|
| `CERTIFICATE_QR_BASE_URL` | (FRONTEND_URL) | Базовый URL для QR-кодов сертификатов |
