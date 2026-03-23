# Moneta Pay URL Webhook — Диагностика

Если Pay URL не получает уведомления от Moneta (статус платежа не обновляется, нет email об оплате), проверьте по чек-листу от поддержки Moneta.

**Пошаговый runbook с командами:** [MONETA_WEBHOOK_DIAGNOSTIC_RUNBOOK.md](MONETA_WEBHOOK_DIAGNOSTIC_RUNBOOK.md) — выполнять шаги по порядку.

---

## Check URL (предвалидация заказа)

Эндпоинт: `GET|POST /api/v1/webhooks/moneta/check`

Moneta вызывает его **до** оплаты. Ответ — XML; бизнес-код в поле `MNT_RESULT_CODE` (HTTP у ответа всегда 200 OK).

| `MNT_RESULT_CODE` | Когда |
|-------------------|--------|
| **200** | Платёж в БД найден и доступен для оплаты (`pending` — в теле при необходимости передаётся `MNT_AMOUNT`) или уже оплачен (`succeeded`). |
| **402** | Заказ не найден (неверный UUID в `MNT_TRANSACTION_ID`) или недоступен для оплаты (например `failed`, `expired`, возврат). |
| **500** | Неверная `MNT_SIGNATURE`; либо в запросе указана `MNT_AMOUNT`, не совпадающая с суммой платежа в БД. |

Реализация: [`webhooks.py`](../backend/app/api/v1/webhooks.py) (`moneta_check_webhook`).

---

## Receipt webhook (фискальный чек, 54-ФЗ)

Эндпоинт: `POST /api/v1/webhooks/moneta/receipt` (JSON: `operation`, `receipt`).

В **production** без настроек аутентификации бэкенд отвечает **403** — запрос не обрабатывается.

| Переменная | Назначение |
|------------|------------|
| `MONETA_RECEIPT_WEBHOOK_SECRET` | Общий секрет; в каждом запросе заголовок **`X-Moneta-Receipt-Secret`** с тем же значением (рекомендуемый способ). |
| `MONETA_RECEIPT_IP_ALLOWLIST` | Список CIDR через запятую (как `YOOKASSA_IP_WHITELIST`): если IP клиента попадает в сеть — запрос допускается без заголовка. |

В режиме **`DEBUG=true`** при пустом секрете и пустом allowlist запросы **допускаются** с предупреждением в логах (`moneta_receipt_webhook_unauthenticated_debug`) — только для локальной разработки.

Реализация: [`payment_utils.py`](../backend/app/services/payment_utils.py) (`is_moneta_receipt_webhook_authorized`), [`webhooks.py`](../backend/app/api/v1/webhooks.py) (`moneta_receipt_webhook`).

---

## Чек-лист от менеджера Moneta

### 1. Pay URL без переадресаций

**Pay URL не должен делать redirect.** Адрес должен отдавать ответ напрямую.

- Ожидаемый URL: `https://trihoback.mediann.dev/api/v1/webhooks/moneta`
- **Важно:** в ЛК Moneta указывать только `https://`, **не** `http://`
- При `http://` nginx вернёт 301 redirect на https — Moneta требует ответ без redirect
- Бэкенд возвращает `200 OK` и текст `SUCCESS` — без редиректов

---

### 2. Код проверки целостности данных

**Секрет в ЛК Moneta и `MONETA_WEBHOOK_SECRET` в `.env.prod` должны совпадать.**

- В ЛК: **Счёт → Приём платежей → Код проверки целостности данных**
- На сервере: переменная `MONETA_WEBHOOK_SECRET` в `/opt/triback/.env.prod`
- Значения должны быть **идентичными** (с учётом регистра и пробелов)

---

### 3. SSL-сертификат

Нужна полная цепочка сертификатов. Проверка:

```bash
openssl s_client -connect trihoback.mediann.dev:443 -showcerts
```

В выводе должны быть: сертификат сайта, промежуточный и корневой. Если цепочка неполная — Moneta может не доверять соединению.

---

### 4. Блокировка хостингом

**Хостинг должен пропускать запросы без User-Agent** (серверные, не браузерные).

Moneta шлёт webhook с сервера, часто без User-Agent. Если провайдер фильтрует такие запросы — webhook до бэкенда не дойдёт.

- Проверить настройки WAF / firewall
- Убедиться, что правила не отсекают запросы без User-Agent

---

### 5. IP-адрес kassa.payanyway.ru

Рекомендуется добавить в список разрешённых:

```
185.111.84.218
```

На уровне:
- Firewall (если есть)
- Nginx / Cloudflare / другой reverse proxy
- Security groups облачного провайдера

Бэкенд **не делает** проверку IP для Moneta — ограничения могут быть только на уровне инфраструктуры.

---

## Формат Pay URL (по документации Moneta)

### Параметры запроса

```
url?MNT_COMMAND=...&MNT_OPERATION_ID=...&MNT_ID=...&MNT_CURRENCY_CODE=...&MNT_AMOUNT=...
     &MNT_CORRACCOUNT=...&MNT_TEST_MODE=...&MNT_TRANSACTION_ID=...&MNT_SUBSCRIBER_ID=...
     &MNT_SIGNATURE=...
```

### MNT_COMMAND

| Значение          | Описание                    |
|-------------------|-----------------------------|
| DEBIT             | Списание средств            |
| CREDIT            | Зачисление средств          |
| CANCELLED_DEBIT   | Отмена списания             |
| CANCELLED_CREDIT  | Отмена зачисления           |
| AUTHORISE         | Авторизация средств         |

### Формула MNT_SIGNATURE

```
MNT_SIGNATURE = md5(
  MNT_COMMAND + MNT_ID + MNT_TRANSACTION_ID + MNT_OPERATION_ID +
  MNT_AMOUNT + MNT_CURRENCY_CODE + MNT_SUBSCRIBER_ID + MNT_TEST_MODE +
  Код_проверки_целостности_данных
);
```

### Пример (из документации Moneta)

```
MNT_COMMAND=AUTHORISE&MNT_OPERATION_ID=102345423&MNT_ID=96801571&MNT_CURRENCY_CODE=RUB
&MNT_AMOUNT=10.00&MNT_CORRACCOUNT=13655088&MNT_TEST_MODE=0&MNT_TRANSACTION_ID=qynt-514-pqme
&MNT_SIGNATURE=ed56b32f21cb8aa5e7e99b75345a0207

MNT_SIGNATURE = md5('AUTHORISE96801571qynt-514-pqme10234542310.00RUB0QWERTY');
(допустим, Код проверки целостности данных = QWERTY)
```

### Требуемый ответ

- HTTP status: **200**
- Тело: **SUCCESS** (plain text)

---

## Ручная проверка

### 1. Доступность URL

```bash
curl -v "https://trihoback.mediann.dev/api/v1/webhooks/moneta?MNT_ID=77892567&MNT_TRANSACTION_ID=test&MNT_OPERATION_ID=test&MNT_AMOUNT=0&MNT_CURRENCY_CODE=RUB&MNT_SUBSCRIBER_ID=&MNT_TEST_MODE=0&MNT_SIGNATURE=invalid"
```

Ожидаемый ответ: `200 OK`, тело `FAIL` (подпись неверная, но endpoint доступен). Если запрос не доходит — искать причину до nginx/сети.

### 2. Логи на сервере

После тестовой оплаты:

```bash
docker logs triback-backend-1 --tail=100 2>&1 | grep -i moneta
```

Должны быть записи:
- `moneta_pay_request` — запрос дошёл до бэкенда
- `moneta_signature_invalid` — ошибка подписи (секрет не совпадает)
- `moneta_webhook_processing_error` — ошибка при обработке

Если логов нет — запрос не доходит до приложения.

### 3. Логи nginx

```bash
# access log
docker exec triback-nginx-1 tail -50 /var/log/nginx/access.log | grep webhooks/moneta

# error log
docker exec triback-nginx-1 tail -50 /var/log/nginx/error.log
```

---

## Сводная проверка

| # | Проверка                            | Где проверить                  |
|---|-------------------------------------|---------------------------------|
| 1 | Pay URL без redirect (только https) | ЛК Moneta, настройки счёта     |
| 2 | Секрет в ЛК = MONETA_WEBHOOK_SECRET | ЛК Moneta, .env.prod           |
| 3 | Цепочка SSL                         | openssl s_client                |
| 4 | Запросы без User-Agent не блокируются | WAF, firewall, хостинг        |
| 5 | IP 185.111.84.218 в allowlist       | Firewall / security rules      |
