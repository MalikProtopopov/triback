# Changelog бэкенда — 17.03.2026

**Коммит:** `8c308ab`  
**Дата:** 17 марта 2026

---

## Обзор

Релиз включает две основные доработки:

1. **Раздельные cookies для админки и клиента** — изоляция сессий admin/client по Origin
2. **Обратная связь по модерации** — врач видит причину отклонения черновика профиля в `GET /profile/public`

---

## 1. Раздельные cookies (admin vs client)

### Проблема

Раньше один cookie `refresh_token` использовался и для клиентского сайта (trichologia.ru), и для админки (admin.trichologia.ru). Это могло приводить к конфликтам сессий при одновременной работе в обеих средах.

### Решение

| Компонент | Было | Стало |
|-----------|------|-------|
| Cookie клиента | `refresh_token` | `refresh_token` (без изменений) |
| Cookie админки | — | `refresh_token_admin` (новый) |
| Login | Всегда `refresh_token` | По Origin: admin. → `refresh_token_admin`, иначе `refresh_token` |
| Refresh | Только `refresh_token` | По Origin: admin. → `refresh_token_admin`, иначе `refresh_token` |
| Logout | Очищает `refresh_token` | Очищает оба cookie, отзывает оба токена |
| Domain | Не задан | Опционально `COOKIE_DOMAIN` (например `.trichologia.ru`) |

### Как определяется админка

По заголовкам `Origin` или `Referer`: если в URL есть подстрока `admin.` (например `https://admin.trichologia.mediann.dev`), используется ключ `refresh_token_admin`.

### Изменённые файлы

- `backend/app/api/v1/auth.py` — константа `REFRESH_COOKIE_KEY_ADMIN`, функции `_is_admin_origin()`, `_get_refresh_cookie_key()`, обновлены login/refresh/logout
- `backend/app/core/config.py` — новая настройка `COOKIE_DOMAIN`
- `env.prod.example` — добавлен пример `COOKIE_DOMAIN=.trichologia.ru`

### Настройка для продакшена

Для кросс-субдоменного доступа (api, admin, клиент на одном родительском домене) добавьте в `.env.prod`:

```env
# Auth cookies: домен для cross-subdomain. Прод: .trichologia.ru
COOKIE_DOMAIN=.trichologia.ru
```

Если не задать — cookie будет привязан к текущему хосту (работает, но не шарится между субдоменами).

---

## 2. Обратная связь по модерации публичного профиля

### Проблема

При отклонении черновика (`POST /admin/doctors/{id}/approve-draft` с `rejection_reason`) врач не видел причину отклонения в `GET /profile/public`. Черновик возвращался только при `status=pending`, а при `rejected` поле `pending_draft` отсутствовало.

### Решение

| Было | Стало |
|------|-------|
| `pending_draft` только при status=pending | `pending_draft` (или `draft`) при pending **и** при rejected |
| Нет полей rejection_reason, reviewed_at | Добавлены `rejection_reason`, `reviewed_at` в ответ |
| При rejected черновик скрывался | Возвращается последний отклонённый с причиной и датой |

### Логика `GET /profile/public`

1. Если есть **pending** черновик → возвращаем его (`status=pending`, `rejection_reason=null`, `reviewed_at=null`)
2. Если pending нет → ищем последний **rejected** (`ORDER BY reviewed_at DESC LIMIT 1`)
3. Если есть rejected → возвращаем его с `status=rejected`, `rejection_reason`, `reviewed_at`, `changes`
4. Если ничего нет → `draft: null` (или не включаем поле)

### Расширенная схема `PendingDraftNested`

```python
class PendingDraftNested(BaseModel):
    status: str
    changes: dict
    submitted_at: datetime
    rejection_reason: str | None = None   # NEW
    reviewed_at: datetime | None = None   # NEW
```

### Изменённые файлы

- `backend/app/schemas/profile.py` — расширен `PendingDraftNested`
- `backend/app/services/profile_service.py` — обновлена логика `get_public`, загрузка rejected при отсутствии pending
- `backend/tests/factories.py` — фабрика `create_profile_change` принимает `status`, `rejection_reason`, `reviewed_at`
- `backend/tests/test_profile.py` — тесты `test_get_public_returns_rejected_draft_with_reason`, `test_get_public_pending_draft_has_no_rejection`

---

## 3. Деплой

### Выполнено

- Закоммичены и запушены изменения в `main`
- Репозиторий: `https://github.com/MalikProtopopov/triback.git`

### Деплой на сервер

Скрипт `./scripts/deploy.sh` нужно запускать **на сервере**, где есть `.env.prod` и Docker:

```bash
# На сервере в директории проекта
./scripts/deploy.sh
```

Скрипт:

1. Подтягивает `git pull origin main`
2. Собирает образ backend
3. Запускает миграции
4. Перезапускает backend + worker + nginx
5. Проверяет health check

### Миграции

В этом релизе миграции БД **не требуются** — все изменения используют существующие колонки (`doctor_profile_changes.rejection_reason`, `reviewed_at` уже есть).

---

## 4. Обратная совместимость

| Изменение | Совместимость |
|-----------|---------------|
| Auth cookies | Клиентский фронт продолжает работать с `refresh_token` без изменений. Админка должна отправлять запросы с Origin `https://admin.*` — тогда получит `refresh_token_admin` |
| GET /profile/public | Новые поля `rejection_reason`, `reviewed_at` — опциональные. Старые клиенты могут их игнорировать |
| Draft при rejected | Новое поведение — клиент увидит причину отклонения, можно обновить UI для отображения |

---

## 5. Тесты

Все тесты проходят (17 шт.):

- `tests/test_auth.py` — login, refresh, logout, register, verify-email
- `tests/test_profile.py` — onboarding, personal/profile, draft (pending + rejected)

Запуск:

```bash
cd backend && pytest tests/test_auth.py tests/test_profile.py -v
```
