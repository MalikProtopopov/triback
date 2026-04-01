# Deploy: Frontend Server (147.45.146.38)

> Настройка сервера для клиентского сайта и админки.
> Домены: `dev.trichologia.ru`, `admin.trichologia.ru`
> IP: 147.45.146.38

---

## DNS (уже настроено)

| Домен | Тип | Значение |
|-------|-----|----------|
| `dev.trichologia.ru` | A | 147.45.146.38 |
| `admin.trichologia.ru` | A | 147.45.146.38 |
| `api.trichologia.ru` | A | 31.130.149.62 |

---

## 1. Подготовка сервера

```bash
# Обновление пакетов
apt update && apt upgrade -y

# Установить nginx и certbot
apt install -y nginx certbot python3-certbot-nginx

# Включить и запустить nginx
systemctl enable nginx
systemctl start nginx

# Открыть порты (если используется ufw)
ufw allow 80
ufw allow 443
```

---

## 2. Настройка Nginx для клиентского сайта (dev.trichologia.ru)

Создать файл конфигурации:

```bash
nano /etc/nginx/sites-available/dev.trichologia.ru
```

Содержимое (для SPA на Next.js / React — static build):

```nginx
server {
    listen 80;
    server_name dev.trichologia.ru;

    root /var/www/dev.trichologia.ru;
    index index.html;

    # SPA: все маршруты отдаём через index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Кэш статики
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

> **Если фронтенд работает как Node.js-сервер (Next.js SSR)**, замените `root` и `try_files` на проксирование:
>
> ```nginx
> location / {
>     proxy_pass http://127.0.0.1:3000;
>     proxy_set_header Host $host;
>     proxy_set_header X-Real-IP $remote_addr;
>     proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
>     proxy_set_header X-Forwarded-Proto $scheme;
> }
> ```

Активировать:

```bash
ln -s /etc/nginx/sites-available/dev.trichologia.ru /etc/nginx/sites-enabled/
```

---

## 3. Настройка Nginx для админки (admin.trichologia.ru)

```bash
nano /etc/nginx/sites-available/admin.trichologia.ru
```

Содержимое (SPA static build):

```nginx
server {
    listen 80;
    server_name admin.trichologia.ru;

    root /var/www/admin.trichologia.ru;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

> **Для Node.js SSR** — аналогично, `proxy_pass http://127.0.0.1:3001;`

Активировать:

```bash
ln -s /etc/nginx/sites-available/admin.trichologia.ru /etc/nginx/sites-enabled/
```

---

## 4. Проверить и перезапустить Nginx

```bash
nginx -t
systemctl reload nginx
```

---

## 5. Получить SSL-сертификаты (Let's Encrypt)

```bash
# Сертификат для обоих доменов одной командой
certbot --nginx -d dev.trichologia.ru -d admin.trichologia.ru \
    --email admin@trichologia.ru \
    --agree-tos \
    --non-interactive
```

Certbot автоматически:
- получит сертификаты
- обновит конфиги nginx (добавит `listen 443 ssl`, редирект 80 -> 443)
- настроит автообновление через systemd timer

Проверить автообновление:

```bash
certbot renew --dry-run
```

---

## 6. Деплой файлов фронтенда

### Вариант A: Static build (React / Next.js export)

```bash
# Создать директории
mkdir -p /var/www/dev.trichologia.ru
mkdir -p /var/www/admin.trichologia.ru

# Загрузить билд (пример с локальной машины)
scp -r ./dist/* root@147.45.146.38:/var/www/dev.trichologia.ru/
scp -r ./admin-dist/* root@147.45.146.38:/var/www/admin.trichologia.ru/
```

### Вариант B: Node.js SSR (pm2)

```bash
# Установить Node.js (если нет)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# Установить pm2
npm install -g pm2

# Клиентский сайт
cd /opt/trihofront
npm ci && npm run build
pm2 start npm --name "client" -- start -- -p 3000

# Админка
cd /opt/trihoadmin
npm ci && npm run build
pm2 start npm --name "admin" -- start -- -p 3001

# Автостарт при перезагрузке
pm2 save
pm2 startup
```

---

## 7. Переменные окружения фронтенда

На фронтенд-сервере задать API URL в `.env` / `.env.production` каждого проекта:

**Клиентский сайт** (`dev.trichologia.ru`):
```env
NEXT_PUBLIC_API_URL=https://api.trichologia.ru
```

**Админка** (`admin.trichologia.ru`):
```env
NEXT_PUBLIC_API_URL=https://api.trichologia.ru
```

> После смены env пересобрать фронтенд (`npm run build`) — Next.js инлайнит `NEXT_PUBLIC_*` при сборке.

---

## 8. Проверка

```bash
# Проверить что сайты отвечают
curl -sI https://dev.trichologia.ru | head -5
curl -sI https://admin.trichologia.ru | head -5

# Проверить SSL
openssl s_client -connect dev.trichologia.ru:443 -servername dev.trichologia.ru < /dev/null 2>/dev/null | openssl x509 -noout -dates
openssl s_client -connect admin.trichologia.ru:443 -servername admin.trichologia.ru < /dev/null 2>/dev/null | openssl x509 -noout -dates
```

---

## Backend SSL (сервер 31.130.149.62)

На бэкенд-сервере SSL уже настроен через docker compose. При смене домена на `api.trichologia.ru`:

1. Обновить `.env.prod`:
   ```env
   API_DOMAIN=api.trichologia.ru
   PUBLIC_API_URL=https://api.trichologia.ru
   CORS_ALLOWED_ORIGINS=["https://trichologia.ru","https://admin.trichologia.ru","https://dev.trichologia.ru","https://api.trichologia.ru"]
   ```

2. Перевыпустить SSL-сертификат:
   ```bash
   cd /opt/triback
   ./scripts/init-ssl.sh
   ```

3. Перезапустить сервисы:
   ```bash
   make deploy
   # или вручную:
   docker compose -f docker-compose.prod.yml restart nginx backend worker
   ```

4. Проверить:
   ```bash
   curl -sf https://api.trichologia.ru/api/v1/health
   ```
