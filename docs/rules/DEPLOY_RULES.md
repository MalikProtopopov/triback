# Deploy Rules — AI Coding Guide

> Этот файл используется как контекст/rules при работе с AI-ассистентом.
> Описывает инфраструктуру, контейнеры, деплой dev и prod окружений.

---

## Архитектура

```
┌─────────────────────────────────────────────┐
│                   Nginx                      │
│  (reverse proxy, SSL termination, SPA)       │
│  :80, :443                                   │
├─────────┬────────────┬──────────────────────┤
│         │            │                       │
│  api.domain.com   admin.domain.com   domain  │
│  → backend:8000   → static SPA       → фронт │
└─────┬───┴────────────┴──────────┬────────────┘
      │                           │
┌─────▼──────┐  ┌──────────┐  ┌──▼───────┐
│  Backend   │  │ Postgres │  │  Redis   │
│  FastAPI   │  │  :5432   │  │  :6379   │
│  Uvicorn   │  │          │  │          │
│  :8000     │  │          │  │          │
└────────────┘  └──────────┘  └──────────┘
```

---

## Контейнеры

| Сервис | Образ | Порт | Описание |
|--------|-------|------|----------|
| backend | python:3.11 + FastAPI/Uvicorn | 8000 | API сервер |
| postgres | postgres:16-alpine | 5432 | База данных |
| redis | redis:7-alpine | 6379 | Кэш, сессии |
| nginx | nginx:alpine | 80, 443 | Reverse proxy, SSL, SPA |
| certbot | certbot/certbot | — | Получение/обновление SSL |
| minio | minio/minio | 9000, 9001 | S3-совместимое хранилище (dev only) |

---

## Dev vs Prod

### Два файла docker-compose

| | Dev | Prod |
|-|-----|------|
| **Файл** | `docker-compose.yml` | `docker-compose.prod.yml` |
| **Env** | `.env` (из `env.dev`) | `.env.prod` (из `env.prod.example`) |
| **Backend** | hot-reload (uvicorn --reload) | gunicorn + uvicorn workers |
| **Порты** | Открыты наружу (5432, 6379...) | Закрыты, только через nginx |
| **SSL** | Нет (http://localhost) | Let's Encrypt (Certbot) |
| **MinIO** | Включён | Внешний S3 или MinIO отдельно |
| **Nginx** | Не нужен (direct access) | Обязателен |
| **Debug** | `DEBUG=true`, verbose logs | `DEBUG=false`, JSON logs |

---

## Env-файлы

```bash
# Dev: скопировать и настроить
cp env.dev .env

# Prod: скопировать и заполнить реальные значения
cp env.prod.example .env.prod
```

### Обязательные переменные (Prod)

```env
# Домен
DOMAIN=domain.com
API_DOMAIN=api.domain.com
ADMIN_DOMAIN=admin.domain.com

# БД
POSTGRES_USER=app_user
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=app_db

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
JWT_SECRET_KEY=<random-64-chars>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Email
EMAIL_FROM=noreply@domain.com
SMTP_HOST=smtp.provider.com
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...

# Шифрование
ENCRYPTION_KEY=<Fernet-key>
```

### Генерация секретов

```bash
# JWT секрет
openssl rand -hex 32

# Fernet ключ (для шифрования)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## Docker Compose: Dev

```yaml
# docker-compose.yml
services:
  backend:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./app:/app/app    # hot-reload
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
```

---

## Docker Compose: Prod

```yaml
# docker-compose.prod.yml
services:
  backend:
    build: .
    command: >
      gunicorn app.main:app
        -w 4
        -k uvicorn.workers.UvicornWorker
        --bind 0.0.0.0:8000
    env_file: .env.prod
    # Порты НЕ открываем наружу — только через nginx
    expose:
      - "8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    env_file: .env.prod
    volumes:
      - postgres_data:/var/lib/postgresql/data
    # Порт НЕ открываем наружу
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/conf.d:/etc/nginx/conf.d
      - ./certbot/www:/var/www/certbot
      - ./certbot/conf:/etc/letsencrypt
      - ./admin-dist:/var/www/admin  # собранная админка
    depends_on:
      - backend
    restart: unless-stopped

  certbot:
    image: certbot/certbot
    volumes:
      - ./certbot/www:/var/www/certbot
      - ./certbot/conf:/etc/letsencrypt
```

---

## Nginx конфиг

### API (api.domain.com)

```nginx
server {
    listen 443 ssl http2;
    server_name api.domain.com;

    ssl_certificate /etc/letsencrypt/live/api.domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.domain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Admin SPA (admin.domain.com)

```nginx
server {
    listen 443 ssl http2;
    server_name admin.domain.com;

    ssl_certificate /etc/letsencrypt/live/admin.domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/admin.domain.com/privkey.pem;

    root /var/www/admin;
    index index.html;

    # SPA fallback — все роуты возвращают index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Кэширование статики
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### HTTP → HTTPS редирект

```nginx
server {
    listen 80;
    server_name api.domain.com admin.domain.com;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}
```

---

## SSL (Let's Encrypt)

### Первичная инициализация

```bash
# 1. Временный nginx без SSL для ACME challenge
# 2. Получение сертификатов
certbot certonly --webroot \
  -w /var/www/certbot \
  -d api.domain.com \
  -d admin.domain.com \
  --email admin@domain.com \
  --agree-tos \
  --non-interactive

# 3. Перезапуск nginx с SSL
docker compose -f docker-compose.prod.yml restart nginx
```

### Автообновление (cron)

```bash
# /etc/cron.d/certbot-renew
0 3 * * * docker compose -f /path/to/docker-compose.prod.yml run --rm certbot renew --quiet && docker compose -f /path/to/docker-compose.prod.yml restart nginx
```

---

## Makefile команды

```makefile
# === Dev ===
dev-up:
	docker compose up -d --build

dev-down:
	docker compose down

dev-logs:
	docker compose logs -f backend

# === Prod ===
prod-up:
	docker compose -f docker-compose.prod.yml up -d --build

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f

# === Database ===
migrate:
	docker compose exec backend alembic upgrade head

migration:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

# === Deploy ===
deploy:
	git pull origin main
	docker compose -f docker-compose.prod.yml up -d --build
	docker compose -f docker-compose.prod.yml exec backend alembic upgrade head
	docker compose -f docker-compose.prod.yml restart backend

# === SSL ===
ssl-init:
	./scripts/init-ssl.sh

ssl-renew:
	docker compose -f docker-compose.prod.yml run --rm certbot renew
	docker compose -f docker-compose.prod.yml restart nginx

# === Backup ===
db-backup:
	./scripts/backup.sh

db-restore:
	./scripts/restore.sh $(file)
```

---

## Deploy-скрипт (zero-downtime)

```bash
#!/bin/bash
# deploy.sh — Zero-downtime deployment

set -e

echo "=== Pulling latest code ==="
git pull origin main

echo "=== Building new image ==="
docker compose -f docker-compose.prod.yml build backend

echo "=== Running migrations ==="
docker compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

echo "=== Restarting backend (zero-downtime) ==="
docker compose -f docker-compose.prod.yml up -d --no-deps --build backend

echo "=== Cleaning old images ==="
docker image prune -f

echo "=== Health check ==="
sleep 5
curl -sf https://api.domain.com/health || echo "WARNING: Health check failed!"

echo "=== Deploy complete ==="
```

---

## Backup-скрипт

```bash
#!/bin/bash
# backup.sh — Database backup

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="db_backup_${DATE}.sql.gz"

mkdir -p $BACKUP_DIR

docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} | gzip > "${BACKUP_DIR}/${FILENAME}"

echo "Backup created: ${BACKUP_DIR}/${FILENAME}"

# Удалить бэкапы старше 30 дней
find $BACKUP_DIR -name "db_backup_*.sql.gz" -mtime +30 -delete
```

---

## Домены (DNS)

```
Тип     Имя                    Значение            Описание
A       api.domain.com         <server-ip>         Backend API
A       admin.domain.com       <server-ip>         Admin SPA
CNAME   admin.client.com       admin.domain.com    Клиентский домен (если multi-tenant)
```

---

## Health Checks

Каждый контейнер имеет healthcheck:

```yaml
# Backend
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3

# Postgres
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]

# Redis
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
```

---

## Чек-лист для AI

При настройке деплоя убедись что:

- [ ] `docker-compose.yml` (dev) и `docker-compose.prod.yml` (prod) существуют
- [ ] Env-файлы: `.env` (dev), `.env.prod` (prod) — секреты НЕ в git
- [ ] `.dockerignore` настроен (venv, __pycache__, .env)
- [ ] Nginx конфиги для каждого домена (API, admin)
- [ ] SSL: init-ssl.sh + cron для автообновления
- [ ] Healthcheck на каждый контейнер
- [ ] Порты БД и Redis НЕ открыты наружу в prod
- [ ] `restart: unless-stopped` на всех prod-сервисах
- [ ] Backup-скрипт + cron для автобэкапа
- [ ] Makefile с командами dev/prod
