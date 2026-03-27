# Переменные окружения — production (trichologia.ru)

> **Шаблон в репозитории.** Скопируйте в `docs/env-production-trichologia.ru.md` и подставьте секреты — этот путь в [`.gitignore`](../.gitignore), в git не попадёт. Либо храните значения в Vault / CI / переменных хостинга.  
> Сайт: [https://trichologia.ru/](https://trichologia.ru/)  
> Бэкенд (пример): **https://api.trichologia.ru** — подставьте фактический поддомен API.

Ниже перечислены **все** ключи из [`backend/app/core/config.py`](../backend/app/core/config.py), с рекомендуемыми значениями для продакшена. Пустые поля — вынести из ЛК Moneta / PayAnyWay / SMTP / облака.

---

## Обязательно для безопасного production

| Переменная | Пример / назначение |
|------------|----------------------|
| `DEBUG` | `false` |
| `SECRET_KEY` | Случайная длинная строка (не дефолт из репозитория). |
| `ENCRYPTION_KEY` | Fernet base64: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `JWT_PRIVATE_KEY_PATH` | Путь к `private.pem` (не хранить ключ в git). |
| `JWT_PUBLIC_KEY_PATH` | Путь к `public.pem` |
| `JWT_AUDIENCE` | `trihoback-api` (или как в клиентах) |
| `JWT_ISSUER` | `trihoback` |
| `DATABASE_URL` | `postgresql+asyncpg://USER:PASSWORD@HOST:5432/DBNAME` — **не** `triho_pass` в проде. |
| `REDIS_URL` | `redis://:PASSWORD@HOST:6379/0` при необходимости с паролем. |

---

## CORS и URL фронта / API

| Переменная | Значение для trichologia.ru + API на поддомене |
|------------|--------------------------------------------------|
| `PUBLIC_API_URL` | `https://api.trichologia.ru` — база для абсолютных ссылок (сертификаты, вебхуки в документации). **Без завершающего слэша.** |
| `FRONTEND_URL` | `https://trichologia.ru` |
| `ADMIN_FRONTEND_URL` | Например `https://admin.trichologia.ru` — если админка на отдельном хосте; иначе можно пусто (см. комментарий в config). |
| `CERTIFICATE_QR_BASE_URL` | Обычно `https://trichologia.ru` или пусто (fallback на `FRONTEND_URL`). |
| `CORS_ALLOWED_ORIGINS` | JSON-массив, например: `["https://trichologia.ru","https://www.trichologia.ru","https://admin.trichologia.ru"]` — все origin’ы браузерных клиентов. |
| `COOKIE_DOMAIN` | `.trichologia.ru` — если access_token cookie должны работать на клиенте и API с разных поддоменов (см. комментарии в config). |
| `ACCESS_TOKEN_COOKIE_SAMESITE` | `none` — для cross-origin SPA + credentials; `lax` — если фронт и API same-site. |

---

## S3 / объектное хранилище

| Переменная | Пример |
|------------|--------|
| `S3_ENDPOINT_URL` | URL провайдера (AWS / Selectel / MinIO). |
| `S3_ACCESS_KEY` | Не дефолт `minioadmin`. |
| `S3_SECRET_KEY` | |
| `S3_BUCKET` | Имя бакета продакшена. |
| `S3_PUBLIC_URL` | Публичный базовый URL для отдачи файлов (CDN или публичный endpoint бакета). |

---

## Платежи: Moneta (основной сценарий)

| Переменная | Назначение |
|------------|------------|
| `PAYMENT_PROVIDER` | `moneta` |
| `MONETA_USERNAME` | Логин MerchantAPI v2 (ЛК). |
| `MONETA_PASSWORD` | |
| `MONETA_SERVICE_URL` | `https://service.moneta.ru/services` (прод). |
| `MONETA_PAYEE_ACCOUNT` | Расширенный счёт получателя (InvoiceRequest). |
| `MONETA_PAYMENT_PASSWORD` | Если используется в возвратах и т.д. |
| `MONETA_MNT_ID` | MNT_ID платёжной формы Assistant. |
| `MONETA_ASSISTANT_URL` | Обычно `https://www.payanyway.ru/assistant.htm` (как в ЛК). |
| `MONETA_WIDGET_URL` | Как в ЛК. |
| `MONETA_DEMO_MODE` | `false` |
| `MONETA_WEBHOOK_SECRET` | Код проверки целостности (Pay URL / подпись вебхуков) из ЛК. |
| `MONETA_FORM_VERSION` | Например `v3` (SBP, SberPay). |

### Редиректы покупателя (страницы на **trichologia.ru**)

| Переменная | Пример |
|------------|--------|
| `MONETA_SUCCESS_URL` | `https://trichologia.ru/payment/success` |
| `MONETA_FAIL_URL` | `https://trichologia.ru/payment/fail` |
| `MONETA_INPROGRESS_URL` | При необходимости страница «ожидание оплаты». |
| `MONETA_RETURN_URL` | Например `https://trichologia.ru/subscription` или страница ЛК после оплаты. |

### Чек Moneta (54‑ФЗ JSON callback)

| Переменная | Назначение |
|------------|------------|
| `MONETA_RECEIPT_WEBHOOK_SECRET` | Значение заголовка `X-Moneta-Receipt-Secret` для `/api/v1/webhooks/moneta/receipt`. |
| `MONETA_RECEIPT_IP_ALLOWLIST` | CIDR Moneta, если секрет не используется; иначе можно пусто при работе через секрет. |

### kassa.payanyway.ru (фискализация XML, путь A)

В ЛК kassa в «Pay URL интернет-магазина» укажите:

`https://api.trichologia.ru/api/v1/webhooks/moneta/kassa`

| Переменная | Значение |
|------------|----------|
| `MONETA_KASSA_FISCAL_ENABLED` | `true` — если используете эту цепочку. |
| `MONETA_FISCAL_SELLER_INN` | ИНН продавца (например с реквизитов организации на сайте). |
| `MONETA_FISCAL_SELLER_NAME` | Юридическое наименование. |
| `MONETA_FISCAL_SELLER_PHONE` | Телефон для чека. |
| `MONETA_FISCAL_SELLER_ACCOUNT` | Счёт Moneta / расчётный, как в инструкции kassa. |
| `MONETA_FISCAL_SNO` | Опционально: 1–6 (СНО). |

Уведомление об оплате без XML (прямой Pay URL Moneta):  
`https://api.trichologia.ru/api/v1/webhooks/moneta`  
Check URL:  
`https://api.trichologia.ru/api/v1/webhooks/moneta/check`

---

## Платежи: YooKassa (только если `PAYMENT_PROVIDER=yookassa`)

| Переменная | Назначение |
|------------|------------|
| `YOOKASSA_SHOP_ID` | |
| `YOOKASSA_SECRET_KEY` | |
| `YOOKASSA_API_URL` | `https://api.yookassa.ru/v3` |
| `YOOKASSA_RETURN_URL` | Например `https://trichologia.ru/payment/result` |
| `YOOKASSA_IP_WHITELIST` | Актуальные подсети YooKassa (см. их документацию). |
| `YOOKASSA_WEBHOOK_VERIFY_WITH_API` | В production при YooKassa: `true` (требование валидации в приложении). |

---

## Прочее (платежи)

| Переменная | По умолчанию |
|------------|----------------|
| `WEBHOOK_INBOX_ENABLED` | `false` — включать только если используете inbox + TaskIQ для YooKassa v2. |
| `PAYMENT_IDEMPOTENCY_TTL` | `86400` |
| `PAYMENT_EXPIRATION_HOURS` | `24` |

---

## SMTP

| Переменная | Пример |
|------------|--------|
| `SMTP_HOST` | |
| `SMTP_PORT` | `587` |
| `SMTP_USER` | |
| `SMTP_PASSWORD` | |
| `SMTP_FROM` | Например `noreply@trichologia.ru` или рабочий ящик. |
| `SMTP_TLS` | `true` или по требованию провайдера. |

---

## Telegram

| Переменная | Назначение |
|------------|------------|
| `TELEGRAM_BOT_TOKEN` | Если бот включён. |
| `TELEGRAM_CHANNEL_ID` | Канал уведомлений. |
| `TELEGRAM_EXPORTS_CHAT_ID` | Чат для выгрузок XLSX; если пусто — `TELEGRAM_CHANNEL_ID`. |
| `TELEGRAM_WEBHOOK_SECRET` | **Обязателен в production**, если задан `TELEGRAM_BOT_TOKEN` (legacy webhook). |

---

## Минимальный чеклист перед деплоем

- [ ] `DEBUG=false`, `SECRET_KEY` и БД не дефолтные.  
- [ ] `PUBLIC_API_URL=https://api.trichologia.ru` (или ваш точный API host).  
- [ ] `CORS_ALLOWED_ORIGINS` содержит все продакшен-origin’ы фронта.  
- [ ] Moneta: все обязательные поля из валидации в `main.py` + редиректы на **https://trichologia.ru/...**.  
- [ ] При kassa: `MONETA_KASSA_FISCAL_ENABLED=true` и все `MONETA_FISCAL_SELLER_*`.  
- [ ] JWT ключи на диске сервера, не в репозитории.  
- [ ] SMTP и Telegram — по факту использования.

---

## Копия в формате `.env` (подставьте секреты локально)

```dotenv
# --- core ---
DEBUG=false
SECRET_KEY=
ENCRYPTION_KEY=

JWT_PRIVATE_KEY_PATH=keys/private.pem
JWT_PUBLIC_KEY_PATH=keys/public.pem
JWT_AUDIENCE=trihoback-api
JWT_ISSUER=trihoback
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DBNAME
REDIS_URL=redis://HOST:6379/0

S3_ENDPOINT_URL=
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_BUCKET=
S3_PUBLIC_URL=

PUBLIC_API_URL=https://api.trichologia.ru
FRONTEND_URL=https://trichologia.ru
ADMIN_FRONTEND_URL=https://admin.trichologia.ru
CERTIFICATE_QR_BASE_URL=
CORS_ALLOWED_ORIGINS=["https://trichologia.ru","https://www.trichologia.ru","https://admin.trichologia.ru"]
COOKIE_DOMAIN=.trichologia.ru
ACCESS_TOKEN_COOKIE_SAMESITE=none

PAYMENT_PROVIDER=moneta
MONETA_USERNAME=
MONETA_PASSWORD=
MONETA_SERVICE_URL=https://service.moneta.ru/services
MONETA_PAYEE_ACCOUNT=
MONETA_PAYMENT_PASSWORD=
MONETA_MNT_ID=
MONETA_ASSISTANT_URL=https://www.payanyway.ru/assistant.htm
MONETA_WIDGET_URL=https://www.payanyway.ru/assistant.widget
MONETA_DEMO_MODE=false
MONETA_WEBHOOK_SECRET=
MONETA_RECEIPT_WEBHOOK_SECRET=
MONETA_RECEIPT_IP_ALLOWLIST=

MONETA_SUCCESS_URL=https://trichologia.ru/payment/success
MONETA_FAIL_URL=https://trichologia.ru/payment/fail
MONETA_INPROGRESS_URL=
MONETA_RETURN_URL=https://trichologia.ru/subscription
MONETA_FORM_VERSION=v3

MONETA_KASSA_FISCAL_ENABLED=false
MONETA_FISCAL_SELLER_INN=
MONETA_FISCAL_SELLER_NAME=
MONETA_FISCAL_SELLER_PHONE=
MONETA_FISCAL_SELLER_ACCOUNT=
# MONETA_FISCAL_SNO=1

WEBHOOK_INBOX_ENABLED=false

YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
YOOKASSA_API_URL=https://api.yookassa.ru/v3
YOOKASSA_RETURN_URL=https://trichologia.ru/payment/result
YOOKASSA_IP_WHITELIST=
YOOKASSA_WEBHOOK_VERIFY_WITH_API=false

PAYMENT_IDEMPOTENCY_TTL=86400
PAYMENT_EXPIRATION_HOURS=24

SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@trichologia.ru
SMTP_TLS=true

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHANNEL_ID=
TELEGRAM_EXPORTS_CHAT_ID=
TELEGRAM_WEBHOOK_SECRET=
```
