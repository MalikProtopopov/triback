# Runbook: деплой hot-fix-серии (платежи + email)

Этот документ — пошаговый план безопасного выката набора правок на прод.

> **Контекст.** Правки касаются работающего прода с реальными платежами и пользователями. Основные изменения:
> - Backend: case-insensitive поиск email в `/auth/forgot-password`, `/auth/login`, `/auth/register`, `/auth/change-email`.
> - Backend: новый фильтр `name` и `provider_id` + поля `external_payment_id`, `moneta_operation_id` в `/admin/payments`.
> - Backend: нормализация диапазона дат (`date_from`/`date_to`) в `/admin/payments` и `/admin/events` — MSK-день, end-exclusive.
> - Alembic: миграция `015_normalize_email_lower` — переводит `users.email` в lower-case + добавляет функциональный индекс `idx_users_email_lower`.

## Риски и как их снижаем

| Риск | Митигация |
|---|---|
| Миграция упадёт из-за case-дубликатов email | Диагностический SELECT перед миграцией (шаг 3). Миграция сама делает pre-flight check и падает до `UPDATE`, если дубли есть. |
| Потеря регистра в email нежелательна | Email — чувствительная только к local-part часть в RFC, но на практике все крупные провайдеры (Gmail, Yandex) лечат lower-case как канон. Риск низкий. |
| Фронтовый код падает на неизвестных полях | Новые поля `external_payment_id`, `moneta_operation_id` — опциональные `| null`. Старые фронты их просто проигнорируют. |
| Логика фильтра дат сломает существующие интеграции | Поведение: если `date_to` — полночь, он расширяется до конца MSK-дня. Если передаётся полный datetime — работает как раньше. Обратно совместимо. |
| Письма из Gmail всё равно не доходят | После деплоя — диагностика DNS + DKIM (шаг 7). |

## Шаг 0. Код-ревью и локальные проверки

```bash
# Локально — синтаксис
cd backend && python -m py_compile app/core/admin_filters.py app/services/auth_service.py \
  app/services/payment_admin_service.py app/services/events/events_admin_core.py \
  app/services/doctor_import_service.py app/services/doctors/doctor_admin_write.py \
  app/services/event_registration/guest_flow.py app/services/event_registration/service.py \
  app/api/v1/payments_admin.py app/schemas/payments.py \
  alembic/versions/n4o5p6q7r8s9_015_normalize_email_lower.py

# Тесты (если есть релевантные)
pytest tests/ -q
```

## Шаг 1. Бэкап БД на сервере

**До любого деплоя** снять pg_dump. На сервере:

```bash
ssh <prod-host>
cd /opt/trihoback  # или где развёрнут проект
TS=$(date +%Y%m%d-%H%M%S)
# Имя контейнера уточнить: docker compose ps
docker compose exec -T postgres pg_dump -U <db_user> -d <db_name> -F c -f /tmp/backup-${TS}.pgcustom
docker compose cp postgres:/tmp/backup-${TS}.pgcustom ./backups/backup-${TS}.pgcustom
ls -lh ./backups/backup-${TS}.pgcustom
```

Формат `-F c` (custom) — компактный и реверсируемый. Размер должен совпадать с прошлыми бэкапами.

> Если есть snapshot-ы у хостера (DigitalOcean/Hetzner) — дополнительно снять snapshot диска. Это 5 минут и отделяет бэкап БД от бэкапа приложения.

## Шаг 2. Выкат кода (без миграции)

Запушить ветку, создать PR, смёрджить в `main`. Затем на сервере:

```bash
git pull origin main
docker compose pull backend worker  # если образы из реестра
# или
docker compose build backend worker
docker compose up -d backend worker
docker compose logs -f backend worker --tail=100
```

Подождать, пока бэкенд и воркер стабильно ответят `/health`. Проверить:

```bash
curl -s https://api.trichology.ru/health
```

На этом этапе:
- ✅ Админка может использовать новые фильтры и поля.
- ✅ Код авторизации уже case-insensitive **для новых запросов** (через `func.lower()`).
- ⚠️ В БД email ещё в исходном регистре — это ок, `func.lower()` в коде справится.

## Шаг 3. Диагностический SELECT — есть ли case-дубликаты?

```bash
docker compose exec -T postgres psql -U <db_user> -d <db_name> <<'SQL'
-- 3.1. Сколько email нужно нормализовать (т.е. отличаются от lower)
SELECT COUNT(*) AS mixed_case_count
FROM users
WHERE email <> LOWER(email);

-- 3.2. Есть ли case-дубликаты (две записи с одинаковым lower(email))
SELECT LOWER(email) AS e, COUNT(*) AS n, array_agg(id::text) AS ids
FROM users
GROUP BY LOWER(email)
HAVING COUNT(*) > 1;

-- 3.3. Конкретные email'ы в разном регистре
SELECT id, email, created_at
FROM users
WHERE email <> LOWER(email)
ORDER BY created_at DESC
LIMIT 50;
SQL
```

Интерпретация:
- **3.2 пусто** → миграция пройдёт безопасно, переходим к шагу 4.
- **3.2 вернуло строки** → нельзя запускать миграцию, сначала вручную разрулить дубликаты (кто настоящий владелец почты, смёрджить/удалить альтернативного, возможно сменить email у второго).

## Шаг 4. Применить миграцию `015_normalize_email_lower`

```bash
docker compose exec backend alembic current
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current  # должен показать n4o5p6q7r8s9
```

Миграция сама делает pre-flight check и падает, если дубли всё-таки появились между шагом 3 и шагом 4. Если упала — повторить шаг 3 и разобраться.

Проверка пост-миграции:

```bash
docker compose exec -T postgres psql -U <db_user> -d <db_name> -c \
  "SELECT COUNT(*) FROM users WHERE email <> LOWER(email);"
# Должен быть 0

docker compose exec -T postgres psql -U <db_user> -d <db_name> -c \
  "\d+ users"
# Должен быть индекс idx_users_email_lower
```

## Шаг 5. Smoke-test на проде

1. Попробовать `/auth/forgot-password` с известным email в разном регистре (например, `ADMIN@trichology.ru` и `admin@trichology.ru`). Проверить логи:
   ```bash
   docker compose logs backend worker | grep -E "forgot_password_(enqueued|user_not_found)|email_sent|email_send_failed"
   ```
   Ожидается `forgot_password_enqueued` + позже `email_sent`.
2. В админке открыть `/admin/payments`, применить фильтр по ФИО (`?name=Романова`) — должны найтись платежи.
3. Применить фильтр по диапазону дат «сегодня по сегодня» — должны найтись сегодняшние платежи.
4. Проверить, что в ответе присутствуют `external_payment_id` / `moneta_operation_id`.

## Шаг 6. Откат (если что-то пошло не так)

### Откат кода

```bash
git revert <merge-sha>
git push origin main
docker compose pull backend worker
docker compose up -d backend worker
```

Код без миграции продолжит работать корректно: `func.lower()` в SQL сработает независимо от того, в каком регистре хранится email.

### Откат миграции

`downgrade` снимает только функциональный индекс. **Регистр email не восстанавливается** (это lossy-операция). Если принципиально нужен старый регистр — восстановить из pg_dump (шаг 1):

```bash
# Полностью заменить состояние БД (опасно — последние данные потеряются!)
docker compose stop backend worker
docker compose exec -T postgres dropdb -U <db_user> <db_name>
docker compose exec -T postgres createdb -U <db_user> <db_name>
docker compose cp ./backups/backup-<TS>.pgcustom postgres:/tmp/restore.pgcustom
docker compose exec -T postgres pg_restore -U <db_user> -d <db_name> /tmp/restore.pgcustom
docker compose start backend worker
```

Этот путь сотрёт всё, что произошло после бэкапа. Не использовать, если между бэкапом и откатом были реальные платежи. Предпочтительнее — жить с lower-case email (это корректнее и для RFC-корректных адресов семантически эквивалентно).

## Шаг 7. Диагностика email-доставки (параллельно)

Недоставка писем Gmail-адресам с `event@trichologia.ru` — скорее всего инфраструктура, не код. Чеклист:

### 7.1. Проверить DNS домена trichologia.ru

```bash
# SPF должен разрешать Яндекс-почту
dig +short TXT trichologia.ru | grep -i spf
# Ожидаем что-то вроде: "v=spf1 include:_spf.yandex.net ~all"

# DMARC-политика
dig +short TXT _dmarc.trichologia.ru
# Ожидаем: "v=DMARC1; p=quarantine; rua=mailto:…"

# DKIM-ключ. Selector у Яндекса — "mail". Фактический selector виден в
# панели Яндекс.Почты для домена.
dig +short TXT mail._domainkey.trichologia.ru
# Ожидаем длинный TXT с "v=DKIM1; k=rsa; p=<base64>"
```

Если хоть один отсутствует — настроить в DNS:
- SPF: `v=spf1 include:_spf.yandex.net ~all`
- DMARC: `v=DMARC1; p=none; rua=mailto:postmaster@trichologia.ru; adkim=r; aspf=r` (начать с `p=none`, потом повышать).
- DKIM: в админке Яндекс360 → «Почта для домена» → «DKIM-подпись» → скопировать публичный ключ в DNS.

### 7.2. Проверить сами логи

```bash
# Последние 500 email-событий за сутки
docker compose logs backend worker --since 24h \
  | grep -E "email_(sent|send_failed)|forgot_password" \
  | tail -n 100
```

Ожидаем пары `forgot_password_enqueued` → `email_sent`. Если есть `email_send_failed` с ошибкой аутентификации — перегенерировать SMTP-пароль в Яндексе.

### 7.3. Тестовая отправка на Gmail

Открыть swagger/админку, дёрнуть `POST /auth/forgot-password` с тестовым Gmail-адресом (предварительно зарегистрировать). Проверить:
- Приход в Inbox.
- Приход в Spam (если в спаме — DKIM/SPF/DMARC настроены неполностью).
- `mail-tester.com` — отправить туда тестовое письмо и получить оценку.

### 7.4. Gmail Postmaster Tools

Зарегистрировать `trichologia.ru` в https://postmaster.google.com — через неделю-две появится статистика по доставке, spam rate, authentication rate. Это единственный прямой способ увидеть, почему Gmail режет письма.

## Чек-лист деплоя

- [ ] Код смёржен в `main`, PR зелёный.
- [ ] Бэкап БД снят (шаг 1).
- [ ] Контейнеры перезапущены (шаг 2), `/health` отвечает.
- [ ] Диагностический SELECT пройден (шаг 3) — дубликатов нет либо разрулены.
- [ ] Миграция применена (шаг 4), индекс `idx_users_email_lower` существует.
- [ ] Smoke-test в админке и на `/auth/forgot-password` прошёл (шаг 5).
- [ ] Проверка SPF/DKIM/DMARC для `trichologia.ru` (шаг 7.1).
- [ ] Заказчик уведомлён, что «тест восстановления пароля» можно повторять.
