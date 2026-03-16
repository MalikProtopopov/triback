# Content blocks в админских API статей, мероприятий и врачей

> Обновление бекенда: поля `content_blocks` добавлены в детальные ответы статей, мероприятий и профилей врачей. Документы организации уже поддерживали блоки — см. [ADMIN_ORG_DOCS_CONTENT_BLOCKS.md](ADMIN_ORG_DOCS_CONTENT_BLOCKS.md).

---

## Эндпоинты с `content_blocks`

| Эндпоинт | Страница админки | Поле |
|----------|------------------|------|
| `GET /api/v1/admin/articles/{id}` | `/admin/content/articles/[id]/edit` | `content_blocks` |
| `GET /api/v1/admin/events/{id}` | `/admin/events/[id]/edit` | `content_blocks` |
| `GET /api/v1/admin/doctors/{profile_id}` | `/admin/doctors/[id]` | `content_blocks` |
| `GET /api/v1/admin/organization-documents/{id}` | `/admin/content/documents/[id]` | `content_blocks` (ранее) |

---

## Формат `ContentBlockNested` (admin)

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | UUID | ID блока |
| `block_type` | string | `text`, `image`, `video`, `gallery`, `link` |
| `sort_order` | number | Порядок отображения |
| `title` | string \| null | Заголовок |
| `content` | string \| null | HTML-контент |
| `media_url` | string \| null | URL медиа |
| `thumbnail_url` | string \| null | URL превью |
| `link_url` | string \| null | Ссылка |
| `link_label` | string \| null | Подпись ссылки |
| `device_type` | string | `both`, `mobile`, `desktop` |
| `block_metadata` | object \| null | Дополнительные данные (например, массив фото галереи) |

---

## Управление блоками

Content blocks создаются и редактируются через отдельный API:

| Метод | URL | Описание |
|-------|-----|----------|
| GET | `/api/v1/admin/content-blocks?entity_type=article&entity_id={id}` | Список блоков |
| POST | `/api/v1/admin/content-blocks` | Создать блок |
| PATCH | `/api/v1/admin/content-blocks/{id}` | Обновить блок |
| DELETE | `/api/v1/admin/content-blocks/{id}` | Удалить блок |
| PATCH | `/api/v1/admin/content-blocks/reorder` | Переставить блоки |

### entity_type для каждой сущности

| Сущность | entity_type |
|----------|-------------|
| Статья | `article` |
| Мероприятие | `event` |
| Профиль врача | `doctor_profile` |
| Документ организации | `organization_document` |

---

## Рекомендации для фронтенда

1. **ContentBlocksEditor** — компонент уже используется для документов. Подключить аналогично для статей, мероприятий и врачей с соответствующими `entityType` и `entityId`.
2. **Детальный просмотр** — поле `content_blocks` в ответе позволяет отображать блоки при загрузке формы редактирования без отдельного запроса.
3. **Сортировка** — блоки приходят по `sort_order` ASC. Редактор должен поддерживать drag-and-drop с вызовом `PATCH /content-blocks/reorder`.

---

## Ссылки

- [ADMIN_ORG_DOCS_CONTENT_BLOCKS.md](ADMIN_ORG_DOCS_CONTENT_BLOCKS.md) — документы организации, ContentBlocksEditor
- Swagger: `GET /admin/articles/{id}`, `GET /admin/events/{id}`, `GET /admin/doctors/{profile_id}`
