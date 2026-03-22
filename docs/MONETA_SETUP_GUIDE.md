# Moneta PayAnyWay — Полная настройка

## Данные аккаунта

| Параметр | Значение |
|----------|---------|
| Номер счёта | **77892567** |
| Название | Ассоциация Трихологов |
| Статус | Активный |
| Договор | 499006 |
| Тип пароля | Постоянный |
| Тарифы | 3.3% карты, 0.7% СБП |

## Реквизиты организации

| Параметр | Значение |
|----------|---------|
| Полное наименование | МЕЖРЕГИОНАЛЬНАЯ ОБЩЕСТВЕННАЯ ОРГАНИЗАЦИЯ ТРИХОЛОГОВ И СПЕЦИАЛИСТОВ В ОБЛАСТИ ИССЛЕДОВАНИЯ ВОЛОС «ПРОФЕССИОНАЛЬНОЕ ОБЩЕСТВО ТРИХОЛОГОВ» |
| Сокращённое | ПРОФЕССИОНАЛЬНОЕ ОБЩЕСТВО ТРИХОЛОГОВ |
| ИНН/КПП | 9701268115 / 770101001 |
| ОГРН | 1237700844325 |
| Юрадрес | 105082, г. Москва, Спартаковская площадь, 14, строение 4 |
| Налогообложение | УСН (без НДС) |
| Банк | ПАО «Банк ПСБ» |
| Р/с | 40703810800000010250 |
| БИК | 044525555 |
| К/с | 30101810400000000555 |
| Президент | Гаджигороева Аида Гусейхановна |
| Телефон | 8 (495) 545-43-75 |
| Email | event@trichologia.ru |

---

## Среды

| Параметр | Продакшн | Демо |
|----------|---------|------|
| ЛК | https://moneta.ru | https://demo.moneta.ru |
| MerchantAPI v2 | https://service.moneta.ru/services | https://demo.moneta.ru/services |
| Платёжная форма | https://www.payanyway.ru/assistant.htm | https://demo.moneta.ru/assistant.htm |
| SOAP WSDL | https://service.moneta.ru/services.wsdl | https://demo.moneta.ru/services.wsdl |

---

## Шаг 1: Настройка в ЛК Moneta

### Вкладка «Приём платежей» (Счёт 77892567)

Все поля, которые видны на скриншотах — заполнить так:

| Поле | Значение | Пояснение |
|------|---------|-----------|
| **Метод отправки** | **POST** | Наш бэкенд принимает POST (но также поддерживает GET) |
| **Pay URL** | `https://trihoback.mediann.dev/api/v1/webhooks/moneta` | Вызывается после успешной оплаты. Бэкенд верифицирует подпись и активирует подписку/регистрацию |
| **Check URL** | `https://trihoback.mediann.dev/api/v1/webhooks/moneta/check` | Предварительная проверка перед оплатой. Бэкенд проверяет что платёж существует и возвращает XML |
| **Подпись формы оплаты** | **Включить** (тумблер вправо) | Обязательно! Без этого подпись MNT_SIGNATURE не проверяется |
| **Код проверки целостности данных** | Придумать секрет, например: `TrIcHo2026$ecReT` | Это значение = `MONETA_WEBHOOK_SECRET` в `.env.prod`. Запомните его! |
| **Тестовый режим** | **Включить** для тестирования, **выключить** для продакшна | Когда включен — деньги не списываются, можно тестить с тестовыми картами |

### Секция «Возврат клиента после оплаты»

| Поле | Значение | Пояснение |
|------|---------|-----------|
| **Замена URL** | **Включить** (тумблер вправо) | Важно! Бэкенд передаёт MNT_SUCCESS_URL / MNT_FAIL_URL в платёжном запросе, и они должны перезаписывать значения из ЛК |
| **Success URL** | `https://trichologia.mediann.dev/payment/success` | Куда редиректить после успешной оплаты |
| **Fail URL** | `https://trichologia.mediann.dev/payment/fail` | Куда редиректить при ошибке |
| **InProgress URL** | (оставить пустым) | Опционально — для карт/терминалов где оплата не мгновенная |
| **Return URL** | `https://trichologia.mediann.dev/subscription` | Куда вернуть если клиент сам закрыл форму оплаты |
| **Возврат для iframe** | `_parent` | Оставить по умолчанию |

### Вкладка «Вызов URL»

Дополнительные callback'и. Заполнить для отслеживания статусов:

| Поле | Значение | Пояснение |
|------|---------|-----------|
| После списания средств | (пустое) | Не используем — Pay URL достаточно |
| После авторизации средств | (пустое) | Не используем |
| После зачисления средств | (пустое) | Опционально — для receipt webhook, но пока оставить пустым |
| После отмены списания средств | (пустое) | Не используем |
| После отмены зачисления средств | (пустое) | Не используем |

### Вкладка «Уведомления о балансе»

Опционально. Можно настроить уведомления на email при изменении баланса.

**После заполнения — нажать «Сохранить» на каждой вкладке!**

---

## Шаг 2: Настройка `.env.prod` на сервере

На сервере в файле `/opt/triback/.env.prod` нужно добавить блок Moneta-переменных.

### Что сейчас есть на сервере

Текущий `.env.prod` **НЕ содержит ни одной Moneta-переменной**. `PAYMENT_PROVIDER` тоже не указан (по умолчанию = `"moneta"`). Это значит:
- Бэкенд пытается создавать платежи через Moneta
- Но все credentials пустые → ошибка при оплате

### Что нужно добавить

```env
# ===== Payment provider =====
PAYMENT_PROVIDER=moneta

# ===== Moneta — MerchantAPI v2 =====
MONETA_USERNAME=<ваш-логин-от-ЛК-moneta.ru>
MONETA_PASSWORD=<ваш-пароль-от-ЛК-moneta.ru>
MONETA_SERVICE_URL=https://service.moneta.ru/services
MONETA_PAYEE_ACCOUNT=77892567
MONETA_PAYMENT_PASSWORD=41074107
MONETA_MNT_ID=77892567
MONETA_ASSISTANT_URL=https://www.payanyway.ru/assistant.htm
MONETA_WIDGET_URL=https://www.payanyway.ru/assistant.widget
MONETA_DEMO_MODE=false
MONETA_WEBHOOK_SECRET=<тот-же-секрет-что-в-ЛК>
MONETA_SUCCESS_URL=https://trichologia.mediann.dev/payment/success
MONETA_FAIL_URL=https://trichologia.mediann.dev/payment/fail
MONETA_INPROGRESS_URL=
MONETA_RETURN_URL=https://trichologia.mediann.dev/subscription
MONETA_FORM_VERSION=v3
```

**Опционально** (для полных URL в ответах API, например ссылка на скачивание сертификата):
```env
# Тест: https://trihoback.mediann.dev  Прод: https://api.trichologia.ru
PUBLIC_API_URL=https://trihoback.mediann.dev
```
Без `PUBLIC_API_URL` ссылка `download_url` в `GET /certificates` будет относительной — клиентский фронт должен сам добавить base URL.

### Пояснение каждой переменной

| Переменная | Значение | Откуда взять |
|-----------|---------|-------------|
| `MONETA_USERNAME` | Логин от ЛК moneta.ru | Email, которым регистрировались (видимо malek@protopopov.xyz) |
| `MONETA_PASSWORD` | Пароль от ЛК moneta.ru | Пароль для входа в https://moneta.ru |
| `MONETA_SERVICE_URL` | `https://service.moneta.ru/services` | Для прод. Для демо: `https://demo.moneta.ru/services` |
| `MONETA_PAYEE_ACCOUNT` | `77892567` | Номер расширенного счёта из ЛК |
| `MONETA_PAYMENT_PASSWORD` | `41074107` | Пароль платежей (для рефандов). Видимо это он |
| `MONETA_MNT_ID` | `77892567` | Тот же номер счёта — используется для проверки подписи вебхуков |
| `MONETA_WEBHOOK_SECRET` | Секрет из поля «Код проверки целостности» | Тот же секрет, что вы ввели в ЛК в настройках счёта |
| `MONETA_SUCCESS_URL` | `https://trichologia.mediann.dev/payment/success` | URL фронта для успешной оплаты |
| `MONETA_FAIL_URL` | `https://trichologia.mediann.dev/payment/fail` | URL фронта для ошибки оплаты |
| `MONETA_RETURN_URL` | `https://trichologia.mediann.dev/subscription` | URL фронта если пользователь сам ушёл с формы |
| `MONETA_DEMO_MODE` | `false` для прод, `true` для тестирования | Автоматически меняет URLs на demo.moneta.ru |
| `MONETA_FORM_VERSION` | `v3` | Версия формы оплаты (v3 поддерживает СБП, SberPay) |

---

## Шаг 3: Тестирование (рекомендуемый порядок)

### Вариант А: Тестировать на ПРОДАКШН-счёте с тестовым режимом

Это быстрее — счёт уже создан (77892567).

1. В ЛК moneta.ru включить **Тестовый режим** на счёте 77892567
2. В ЛК заполнить Pay URL, Check URL, секрет (см. таблицу выше)
3. На сервере добавить env vars (см. выше) с `MONETA_DEMO_MODE=false`
4. Перезапустить: `docker compose -f docker-compose.prod.yml up -d --no-deps backend worker`
5. Тестировать оплату с тестовыми картами
6. После успешного теста — выключить тестовый режим в ЛК

### Вариант Б: Тестировать на ДЕМО-среде

1. Зарегистрироваться на https://demo.moneta.ru/backoffice/auth/register
2. Написать PayAnyWay (com@payanyway.ru) для подтверждения
3. Создать расширенный счёт в демо-ЛК
4. Настроить счёт аналогично продакшну
5. На сервере поставить: `MONETA_DEMO_MODE=true`, `MONETA_SERVICE_URL=https://demo.moneta.ru/services`, `MONETA_ASSISTANT_URL=https://demo.moneta.ru/assistant.htm`, и credentials от демо-ЛК

### Тестовые карты

| Номер карты | Поведение |
|------------|----------|
| `4000000000000002` | Успешная оплата без 3DS |
| `4000000000000010` | Успешная оплата с 3DS |
| `4000000000000028` | Ошибка "нет денег" |
| `4000000000000036` | Ошибка "превышен лимит" |
| `4000000000000069` | Ошибка после 3DS |

Expiry date — любая будущая, CVV — любой 3-значный.

---

## Шаг 4: Чек-лист проверки

После настройки проверить:

- [ ] `POST /api/v1/subscriptions/pay` — возвращает `payment_url` (не 500)
- [ ] Переход по `payment_url` — открывается форма оплаты Moneta
- [ ] Ввод тестовой карты → успешная оплата
- [ ] Webhook Check URL → бэкенд отвечает XML с кодом 200
- [ ] Webhook Pay URL → бэкенд отвечает SUCCESS, подписка активируется
- [ ] `GET /api/v1/subscriptions/status` → подписка active, ends_at заполнен
- [ ] Логи: `docker logs triback-backend-1 --tail=50` — без ошибок

---

## Шаг 5: Переключение на продакшн

Когда тесты пройдены:

1. В ЛК: **выключить** тестовый режим
2. В `.env.prod`: `MONETA_DEMO_MODE=false`
3. Убедиться что Success/Fail URLs указывают на правильный фронт-домен
4. Перезапустить бэкенд

---

## Контакты поддержки Moneta

| | |
|---|---|
| Коммерческий отдел | Марат Габдрахманов, +7 495 646-58-48 доб. 4301 |
| Email поддержки | com@payanyway.ru |
| Email бизнес | business@support.payanyway.ru |

---

## Как работает интеграция (для понимания)

```
Клиент нажимает "Оплатить"
        │
        ▼
POST /subscriptions/pay
        │
        ▼
Бэкенд создаёт Payment (pending) в БД
        │
        ▼
Бэкенд отправляет InvoiceRequest → Moneta MerchantAPI v2
(JSON Envelope с Username/Password auth)
        │
        ▼
Moneta возвращает InvoiceResponse { transaction: 328498 }
        │
        ▼
Бэкенд строит URL: https://www.payanyway.ru/assistant.htm?operationId=328498&version=v3&...
        │
        ▼
Фронт редиректит клиента на этот URL
        │
        ▼
Клиент вводит данные карты на форме Moneta
        │
        ▼
Moneta вызывает Check URL → Бэкенд проверяет платёж → XML "200 OK"
        │
        ▼
Moneta проводит оплату
        │
        ▼
Moneta вызывает Pay URL → Бэкенд верифицирует подпись → активирует подписку → "SUCCESS"
        │
        ▼
Moneta редиректит клиента на Success URL
```
