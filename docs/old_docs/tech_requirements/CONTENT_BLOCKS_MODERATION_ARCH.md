# Архитектура модерации контентных блоков (черновик)

> Статус: **не реализовано** — описание подхода для будущей реализации.

## Контекст

Контентные блоки (`ContentBlock`, `entity_type = "doctor_profile"`) сейчас
управляются только админами через `content_blocks_admin.py`.
Если врачи получат возможность самостоятельно создавать/редактировать
свои контентные блоки, нужна модерация по аналогии с `DoctorProfileChange`.

## Предлагаемый подход

### Новая модель: `ContentBlockChange`

```
content_block_changes
├── id                  UUID PK
├── entity_type         "doctor_profile"
├── entity_id           UUID (doctor_profile.id)
├── content_block_id    UUID | NULL (NULL = новый блок)
├── action              "create" | "update" | "delete"
├── changes             JSONB (block_type, title, content, media_url, ...)
├── status              "pending" | "approved" | "rejected"
├── submitted_at        timestamptz
├── reviewed_at         timestamptz | NULL
├── reviewed_by         UUID FK → users.id | NULL
├── rejection_reason    text | NULL
└── unique partial index: (entity_id) WHERE status = 'pending' AND action = ...
```

### Логика

1. **Врач** через API `/profile/content-blocks` создаёт/правит/удаляет блок:
   - Создается `ContentBlockChange` со `status = "pending"`.
   - Публичный API продолжает показывать текущие `ContentBlock`.

2. **Админ** через API `/admin/content-block-changes/{id}/review`:
   - `action = "approve"`:
     - `create` → создать новый `ContentBlock` из `changes`.
     - `update` → применить `changes` к существующему `ContentBlock`.
     - `delete` → удалить `ContentBlock`.
   - `action = "reject"` → установить `rejection_reason`, уведомить врача.

3. **Паттерн идентичен `DoctorProfileChange`** — одинаковый подход
   к черновикам для всех публичных данных врача.

### Файлы для реализации

| Файл | Что создать/изменить |
|------|---------------------|
| `models/content.py` | Добавить `ContentBlockChange` |
| `alembic/versions/...` | Миграция для `content_block_changes` |
| `schemas/content_blocks.py` | Схемы для черновиков |
| `services/content_block_service.py` | Методы для CRUD черновиков |
| `api/v1/profile.py` | Эндпоинты `/profile/content-blocks` |
| `api/v1/doctors_admin.py` | Эндпоинт для review черновиков |
