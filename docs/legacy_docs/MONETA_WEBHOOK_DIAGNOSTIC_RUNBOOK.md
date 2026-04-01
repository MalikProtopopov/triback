# План диагностики Moneta Pay URL webhook

Пошаговый runbook для проверки, почему Pay URL не получает уведомления. Выполнять по порядку; при первом негативном результате — останавливаться и исправлять.

---

## Шаг 1: Проверка доступности endpoint (локально)

**Цель:** убедиться, что URL доступен извне и возвращает ответ.

```bash
curl -v "https://trihoback.mediann.dev/api/v1/webhooks/moneta?MNT_ID=77892567&MNT_TRANSACTION_ID=test&MNT_OPERATION_ID=test&MNT_AMOUNT=0&MNT_CURRENCY_CODE=RUB&MNT_SUBSCRIBER_ID=&MNT_TEST_MODE=0&MNT_SIGNATURE=invalid"
```

| Результат | Интерпретация |
|-----------|----------------|
| HTTP 200, тело `FAIL` | Endpoint доступен, подпись неверная (ожидаемо). Ок. |
| HTTP 301/302 | Redirect — Pay URL в ЛК Moneta указан как `http://`. Исправить на `https://`. |
| Timeout / Connection refused | Проблема сети, firewall или DNS. Проверить доступность хоста. |
| HTTP 502/503 | Nginx/бэкенд недоступны. Проверить контейнеры на сервере. |

---

## Шаг 2: Проверка SSL

**Цель:** убедиться, что цепочка сертификатов полная (Moneta может отклонять при проблемах с SSL).

```bash
openssl s_client -connect trihoback.mediann.dev:443 -showcerts 2>/dev/null | openssl x509 -noout -subject -issuer
```

Должны быть видны subject и issuer. Полная проверка цепочки:

```bash
openssl s_client -connect trihoback.mediann.dev:443 -showcerts
```

В выводе — несколько блоков `-----BEGIN CERTIFICATE-----` (сайт + промежуточный + корневой). Ошибки `unable to get local issuer certificate` — исправить настройки SSL.

---

## Шаг 3: Настройки в ЛК Moneta (ручная проверка)

Открыть https://moneta.ru → Счёт 77892567 → Приём платежей.

| Параметр | Ожидаемое значение |
|----------|--------------------|
| Pay URL | Только `https://trihoback.mediann.dev/api/v1/webhooks/moneta` (без `http://`) |
| Код проверки целостности данных | Запомнить/скопировать точное значение |

---

## Шаг 4: Совпадение секрета на сервере

**Цель:** убедиться, что `MONETA_WEBHOOK_SECRET` совпадает с секретом в ЛК.

```bash
ssh root@31.130.149.62 "grep MONETA_WEBHOOK_SECRET /opt/triback/.env.prod"
```

Сравнить вывод с полем «Код проверки целостности данных» в ЛК. Регистр и пробелы должны совпадать **строго**.

---

## Шаг 5: Тестовая оплата + логи backend

**Цель:** понять, доходят ли запросы до бэкенда.

1. Выполнить тестовую оплату (тестовая карта `4000000000000002`, тестовый режим в ЛК включён).
2. Сразу после оплаты:

```bash
ssh root@31.130.149.62 "docker logs triback-backend-1 --tail=200 2>&1 | grep -i moneta"
```

| Результат | Интерпретация |
|-----------|----------------|
| `moneta_pay_request` есть | Запрос дошёл. Дальше смотреть: `moneta_signature_invalid` → секрет не совпадает; `moneta_webhook_processing_error` → ошибка в коде. |
| Записей нет | Запрос не доходит до приложения. Идти к шагу 6 (nginx, firewall, IP). |

---

## Шаг 6: Логи nginx (если запрос не доходит)

**Цель:** понять, доходит ли запрос до nginx.

```bash
ssh root@31.130.149.62 "docker exec triback-nginx-1 tail -100 /var/log/nginx/access.log | grep webhooks/moneta"
```

```bash
ssh root@31.130.149.62 "docker exec triback-nginx-1 tail -50 /var/log/nginx/error.log"
```

| Результат | Интерпретация |
|-----------|----------------|
| access.log: есть 200/301 к webhooks/moneta | Nginx получает запросы. Проблема в proxy_pass или backend. |
| access.log: пусто по webhooks/moneta | Запросы не доходят до nginx. Проверить firewall, IP allowlist (185.111.84.218), WAF. |

---

## Шаг 7: Firewall и IP Moneta

**Цель:** разрешить трафик с kassa.payanyway.ru.

IP Moneta: `185.111.84.218`

Проверить, не блокируется ли трафик:

- Firewall на сервере (`ufw`, `iptables`)
- Security groups в облаке
- Cloudflare / WAF (если используются): не блокировать запросы без User-Agent к `/api/v1/webhooks/moneta`

---

## Сводный чек-лист

| # | Проверка | Где |
|---|----------|-----|
| 1 | curl → HTTP 200, FAIL | Локально |
| 2 | SSL цепочка полная | openssl s_client |
| 3 | Pay URL только https:// в ЛК | moneta.ru |
| 4 | Секрет в ЛК = MONETA_WEBHOOK_SECRET | .env.prod |
| 5 | После оплаты — moneta_pay_request в логах | docker logs triback-backend-1 |
| 6 | Nginx видит запросы | nginx access.log |
| 7 | IP 185.111.84.218 в allowlist | Firewall / security groups |

---

## Референс

Подробности и формула MNT_SIGNATURE: [MONETA_WEBHOOK_TROUBLESHOOTING.md](MONETA_WEBHOOK_TROUBLESHOOTING.md)
