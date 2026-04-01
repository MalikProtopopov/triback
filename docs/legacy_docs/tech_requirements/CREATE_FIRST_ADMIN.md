# Создание первого администратора

После первого развёртывания в базе нет ни одного пользователя с ролью admin. Войти в админку можно только после создания первого админа.

## Способ 1: Скрипт (рекомендуется)

Скрипт создаёт в БД все нужные роли (если их ещё нет), затем пользователя с указанным email/паролем и назначает ему роль **admin**.

### На сервере (Docker)

Из каталога проекта на сервере (например `/opt/triback`):

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python scripts/create_admin.py --email admin@your-domain.ru --password 'ВашНадёжныйПароль123!'
```

Пароль можно не передавать в командной строке — тогда скрипт запросит его интерактивно:

```bash
docker compose -f docker-compose.prod.yml exec backend \
  python scripts/create_admin.py --email admin@your-domain.ru
# Password: (введите пароль)
```

### Без интерактива (env)

Удобно для автоматизации или если не хотите светить пароль в истории:

```bash
CREATE_ADMIN_EMAIL=admin@your-domain.ru CREATE_ADMIN_PASSWORD='ВашПароль' \
  docker compose -f docker-compose.prod.yml exec backend python scripts/create_admin.py
```

### Локально (без Docker)

Если БД доступна с вашей машины (например, туннель до сервера):

```bash
cd backend
export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/triho_db"
python scripts/create_admin.py --email admin@example.com --password 'YourPass123!'
```

---

## Способ 2: Вручную через SQL (если скрипт недоступен)

1. **Хэш пароля** — нужен Argon2id-хэш. Получить можно в Python:

   ```bash
   docker compose -f docker-compose.prod.yml exec backend python -c "
   from app.core.security import hash_password
   print(hash_password('ВашПароль'))
   "
   ```

2. **ID роли admin** — в таблице `roles` найдите строку с `name = 'admin'` и запомните `id` (или вставьте роль, если таблица пустая).

3. **Вставка пользователя и привязки к роли** (в psql или любом клиенте к БД):

   - Сгенерируйте UUID (например, https://www.uuidgenerator.net/ или `gen_random_uuid()` в PostgreSQL).
   - Подставьте email, хэш пароля, uuid пользователя и id роли admin:

   ```sql
   -- Если таблица roles пустая — сначала создать роли (id 1–5 для admin, manager, accountant, doctor, user)
   INSERT INTO roles (id, name, title, created_at) VALUES
   (1, 'admin', 'Администратор', now()),
   (2, 'manager', 'Менеджер', now()),
   (3, 'accountant', 'Бухгалтер', now()),
   (4, 'doctor', 'Врач', now()),
   (5, 'user', 'Пользователь', now())
   ON CONFLICT DO NOTHING;

   -- Пользователь (подставьте свои значения)
   INSERT INTO users (id, email, password_hash, is_active, is_deleted, created_at, updated_at)
   VALUES (
     'aaaaaaaa-bbbb-7ccc-dddd-eeeeeeeeeeee',  -- любой UUID
     'admin@your-domain.ru',
     '$argon2id$v=19$m=65536,t=3,p=4$...',   -- результат hash_password()
     true,
     false,
     now(),
     now()
   );

   -- Назначить роль admin (role_id = 1, если вставили как выше)
   INSERT INTO user_roles (user_id, role_id, assigned_at)
   VALUES ('aaaaaaaa-bbbb-7ccc-dddd-eeeeeeeeeeee', 1, now());
   ```

После этого войдите в админку (например, `https://admin.trichologia.mediann.dev`) с указанным email и паролем через форму логина (`POST /api/v1/auth/login`).
