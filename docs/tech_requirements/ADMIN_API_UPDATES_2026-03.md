# Обновления админских API — админка

**Дата:** 2026-03-17  
**Релиз:** Модерация публичных данных, фильтр по подписке

---

## Кратко

Изменения затрагивают модерацию черновиков профиля врача. Черновик теперь может содержать **фото** (`photo_url`), которое тоже проходит модерацию.

---

## 1. Черновики профиля — новое поле `photo_url`

### `GET /api/v1/admin/doctors/{profile_id}` (или эндпоинт деталей врача)

В ответе уже есть `pending_draft`. В `pending_draft.changes` и `pending_draft.changed_fields` теперь может быть **`photo_url`**.

**Пример:**

```json
{
  "id": "...",
  "first_name": "Иван",
  "photo_url": "https://api.../media/old.jpg",
  "pending_draft": {
    "id": "...",
    "changes": {
      "bio": "Новая биография",
      "photo_url": "doctors/uuid/photo/new-key.jpg"
    },
    "changed_fields": ["bio", "photo_url"],
    "status": "pending",
    "submitted_at": "2026-03-17T12:00:00Z"
  }
}
```

**Для админки:**
1. Если `"photo_url"` в `changed_fields` — показывать превью нового фото
2. URL для превью: `${MEDIA_BASE_URL}/${pending_draft.changes.photo_url}` (в `changes.photo_url` хранится S3-ключ)
3. Сравнивать с текущим `photo_url` профиля, чтобы админ видел «было / стало»

---

## 2. Одобрение черновика

### `POST /api/v1/admin/doctors/{profile_id}/approve-draft`

**Запрос (без изменений):**

```json
{
  "action": "approve",
  "rejection_reason": null
}
```

```json
{
  "action": "reject",
  "rejection_reason": "Фото не соответствует требованиям"
}
```

**Изменение на бэкенде:** При `action: "approve"` применяются **все** поля из `changes`, включая `photo_url`. Раньше `photo_url` в черновиках не было, теперь — есть.

**Для админки:**
1. При просмотре черновика показывать блок «Новое фото», если `photo_url` в `changed_fields`
2. Логика approve/reject не меняется — бэкенд сам применит `photo_url` при одобрении
3. После одобрения уведомление врачу отправляется как и раньше

---

## 3. Список врачей — новое поле `has_photo_in_draft`

### `GET /api/v1/admin/doctors`

В ответе у каждого врача добавлено поле **`has_photo_in_draft`**:

```json
{
  "data": [
    {
      "id": "...",
      "last_name": "Петров",
      "first_name": "Иван",
      "has_pending_changes": true,
      "has_photo_in_draft": true
    }
  ]
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `has_photo_in_draft` | boolean | `true`, если в pending-черновике есть изменение фото (`photo_url`) |

**Для админки (колонка «Правки»):**

- Если `has_photo_in_draft === true` — показывать иконку/метку «+ фото» рядом с индикатором «на модерации»
- Это позволяет админу видеть в списке, у каких врачей изменено именно фото, без перехода в карточку

---

## 4. Сводка изменений

| Компонент | Изменение |
|-----------|-----------|
| `GET /admin/doctors` | Новое поле `has_photo_in_draft: boolean` в каждом элементе |
| `GET /admin/doctors/{id}` | `pending_draft.changes` может содержать `photo_url` (S3-ключ) |
| `pending_draft.changed_fields` | Может содержать `"photo_url"` |
| `POST approve-draft` | При approve применяет `photo_url` к профилю |
| Схемы запросов | Без изменений |

---

## 5. Рекомендации по UI

1. **Сравнение фото:** Показывать текущее и новое фото рядом при модерации
2. **Превью нового фото:** Использовать `${MEDIA_BASE_URL}/${changes.photo_url}` (см. [FRONTEND_MEDIA_URLS_HANDOFF.md](./FRONTEND_MEDIA_URLS_HANDOFF.md))
3. **Метка в списке:** Если в черновике есть `photo_url`, отображать метку «+ фото» рядом с «на модерации»
