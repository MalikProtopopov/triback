# Настройка SMTP для отправки писем

## Где указать

Переменные задаются в **файле окружения на сервере**, который подхватывает Docker Compose:

- **Файл:** `.env.prod` в корне проекта (на сервере).
- Сервисы `backend` и `worker` читают его через `env_file: .env.prod` в `docker-compose.prod.yml`.

Если на сервере используется симлинк (например `ln -sf .env.prod .env`), можно править `.env.prod` — симлинк просто указывает на него.

---

## Что указать

Добавьте или отредактируйте в `.env.prod` блок:

```env
# ===== SMTP =====
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your-smtp-login
SMTP_PASSWORD=your-smtp-password
SMTP_FROM=noreply@yourdomain.ru
```

| Переменная       | Описание                          | Пример |
|------------------|-----------------------------------|--------|
| `SMTP_HOST`      | Хост SMTP-сервера                | `smtp.yandex.ru`, `smtp.mail.ru`, `smtp.gmail.com` |
| `SMTP_PORT`      | Порт (обычно 587 для TLS)        | `587` |
| `SMTP_USER`      | Логин (часто совпадает с email)  | `noreply@yourdomain.ru` |
| `SMTP_PASSWORD`  | Пароль или пароль приложения     | — |
| `SMTP_FROM`      | Адрес отправителя в письмах      | `noreply@yourdomain.ru` |

После изменений перезапустите контейнеры:

```bash
docker compose -f docker-compose.prod.yml up -d backend worker
```

---

## Важно: текущее поведение кода

Сейчас в коде **нет реальной отправки писем через SMTP**. Конфиг читается в `app/core/config.py`, но:

- Таски в `app/tasks/email_tasks.py` только пишут в лог (`logger.info(...)`).
- `NotificationService.send_email()` в `app/services/notification_service.py` — заглушка (тоже только лог).

То есть **одних переменных в `.env.prod` недостаточно** — письма не будут уходить, пока не будет реализована отправка (например через `aiosmtplib` или отдельный email-сервис). Настройка SMTP в env нужна заранее, чтобы потом просто включить отправку в коде.

Если нужно, могу предложить план/правки для реальной отправки писем через SMTP в тасках и в `NotificationService`.
