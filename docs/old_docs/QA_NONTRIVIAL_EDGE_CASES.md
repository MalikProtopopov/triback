# Нетривиальные кейсы API (QA, по коду)

Поведение собрано из реализации в `backend/app`, а не из ТЗ: условия, при которых ожидаемый «успех» меняется на другой HTTP-код, фильтрация внутри 200, зависимость от env/DEBUG/TTL и идемпотентность.

Таблица **не исчерпывает** весь API — только зоны, где легко ошибиться при тест-дизайне. См. также [`BUSINESS_SCENARIO_FLOWS.md`](BUSINESS_SCENARIO_FLOWS.md) и [`API_ENDPOINT_MATRIX.md`](API_ENDPOINT_MATRIX.md).

## Таблица

| Эндпоинт / зона | Условие | Ожидаемый ответ | Почему это не очевидно |
|-----------------|---------|-----------------|-------------------------|
| `GET /api/v1/public/events/{event_id}/recordings` | Запись с `access_level` `members_only` или `participants_only`, нет JWT или нет ни активной подписки, ни **confirmed** регистрации на **это** событие | **200**, запись отсутствует в `data` (фильтрация), не 403 | Часто ожидают 403/404 на весь список; здесь «пустое место» в том же 200 |
| `GET /api/v1/public/events/{event_id}/galleries` | Галерея `members_only`, нет доступа (как выше) | **200**, галерея пропущена | Аналогично recordings |
| `GET /api/v1/public/events/{event_id}/galleries` | Галерея `participants_only`, пользователь без доступа | **200**, галерея **всё равно в ответе** | В коде отфильтровывается только `members_only`; `participants_only` для галерей **не** скрывается (в отличие от recordings) |
| `GET /api/v1/public/events/{slug}` (деталь) | В БД есть галереи не `public` | В блоке галерей только `access_level == public` | Отдельный эндпоинт `/galleries` может отдавать больше/другое по правилам — три разных модели доступа к медиа |
| `POST /api/v1/public/events/{id}/register` | Гость, `guest_email` пустой | **422** `AppValidationError` | В доке акцент на сценариях с email; без email ветка не «verification», а валидация |
| `POST .../register` | Авторизованный пользователь, регистрация `pending`, повторный запрос | **201** + новый платёж, `reuse_registration`, `increment_seats=False` | Не дублируется строка регистрации, места тарифа второй раз не увеличиваются |
| `POST .../register` | Статус регистрации `cancelled`, повтор | **201**, `increment_seats=True` | Отличается от `pending` по инкременту мест |
| `POST .../confirm-guest-registration` | Код верный, но `event_id` в URL не совпадает с сессией в Redis | **422** event mismatch | Ошибка не «неверный код», а рассинхрон события |
| `POST /api/v1/subscriptions/pay` | Нет успешного entry fee и истёкшая подписка **> 60 дней** (`LAPSE_THRESHOLD_DAYS`) | Снова продукт `entry_fee` + сумма entry+план | Порог 60 дней и логика `determine_product_type` обычно не в ТЗ |
| `POST /api/v1/subscriptions/pay` | Последняя подписка с `ends_at is NULL` | Трактуется как ветка «без даты окончания» → тип продукта как для «нет подписки» | Нетипичная конфигурация данных сильно меняет тип платежа |
| `POST .../payments/{id}/check-status` | JWT есть, но `payment.user_id != sub` | **403** `ForbiddenError` | Публичный `GET .../status` без JWT знает статус по id; приватная «проверка в Moneta» — только владелец |
| `GET .../payments/{id}/status` | Любой знает `payment_id` | **200** с полным статусом (в т.ч. сумма, тип продукта) | Идемпотентность/безопасность: нет скрытия факта оплаты по секрету |
| `POST /api/v1/webhooks/yookassa` | Повтор того же события (Redis dedup) | **200** `{"status":"ok"}` **до** вызова бизнес-логики | Дубликат не 409; провайдеру всегда успех |
| `POST /api/v1/webhooks/yookassa` | `YOOKASSA_IP_WHITELIST` пуст, не `DEBUG` | **403** на этапе сервиса | В `DEBUG` пустой whitelist для YooKassa **разрешён** (`is_ip_allowed`); в prod — запрет |
| `POST /api/v1/webhooks/yookassa` (и inbox) | `YOOKASSA_WEBHOOK_VERIFY_WITH_API` + API статус ≠ succeeded | Обработка **прерывается** без исключения (inbox: строка может стать `done` без изменения платежа) | **200** провайдеру при webhook, но деньги в БД не «успешны» — легко принять за баг |
| `POST /api/v1/webhooks/yookassa/v2` | `WEBHOOK_INBOX_ENABLED=false` | **404** | Тот же провайдер, другой URL — включение только флагом |
| `POST /api/v1/webhooks/moneta/receipt` | Нет секрета и allowlist, не `DEBUG` | **403** JSON | В `DEBUG` без настроек — **разрешено** с warning в логах |
| `POST /api/v1/webhooks/moneta` (Pay URL) | Повтор с тем же `MNT_OPERATION_ID` после первого dedup в Redis | **200** текст `SUCCESS` без повторной бизнес-логики | Идемпотентность на уровне текста ответа Moneta, не HTTP-кода |
| TaskIQ `process_payment_webhook_inbox` | Повторная доставка задачи для `status` `done`/`dead` | Выход без работы | Идемпотентность очереди отдельно от Redis dedup HTTP |
| `poll_pending_moneta_payments` (фон) | Платёж моложе 2 минут | Не опрашивается | Окно «2 min» снижает гонку с только что созданной операцией |
| `expire_stale_pending_payments` | `expires_at IS NULL`, но возраст > `PAYMENT_EXPIRATION_HOURS` | Статус платежа **expired** (фон) | Две формулы срока (явный TTL и fallback по `created_at`) |
| `POST /api/v1/auth/resend-verification-email` | Email не в БД или уже верифицирован | **200** без письма | Намеренное сокрытие перечисления пользователей |
| `POST /api/v1/auth/resend-verification-email` | >3 запросов за 10 мин на email | **429** | Лимит только на этом эндпоинте, не на register |
| `POST /api/v1/auth/refresh` | Origin указывает на admin, но в cookie только клиентский refresh | **401** (нет токена в нужной cookie) | Выбор cookie зависит от `Origin`/`Referer`, не только от тела запроса |
| `POST /api/v1/auth/login` | Email не подтверждён, пароль верный | **200** с токенами (в `login` нет проверки `email_verified_at`) | Ожидают блокировку до verify; фактически вход разрешён — политика только на фронте/в других эндпоинтах |
| `POST /api/v1/auth/login` | Неверный пароль | **401** «Invalid email or password» | То же сообщение, что и при несуществующем email — без уточнения причины |
| `GET /api/v1/certificates`, скачивание в ЛК | Профиль врача не `active` или нет доступа по сервису | **403** | Роль `doctor` в JWT недостаточно — нужен «активный врач» в доменной модели |
| `POST /api/v1/voting/{session_id}/vote` | Доктор без активной подписки или профиль не `active` | **403** | Роль JWT ≠ членство в ассоциации |
| `POST .../vote` | Повтор голоса | **409** после `IntegrityError` | Дубль ловится БД, не отдельным «if exists» до insert |
| Админ `POST /api/v1/admin/payments/{id}/confirm` | Endpoint помечен как временный dev/test | Успех как от webhook | В проде может остаться обходом провайдера, если не убрать |

## Гонки и порядок операций

Две параллельные Moneta Pay URL с одним `MNT_OPERATION_ID` могут оба пройти `SET NX` dedup в Redis, если запросы приходят одновременно до установки ключа; дальше вторая обработка обычно упрётся в `payment.status == succeeded` в `_apply_payment_succeeded`, но теоретическое окно зависит от пути и блокировок БД.
