# Документы организации: content и content_blocks (Фронт — Админка)

Обновление API: теперь документы организации поддерживают HTML-поле `content` в списке и `content_blocks` в детальном просмотре.

---

## Изменения в API

### GET /api/v1/admin/organization-documents

**Было:** в объекте списка не было поля `content`.

**Стало:** поле `content: string | null` добавлено в каждый элемент списка.

```json
{
  "data": [
    {
      "id": "019cf249-7f75-7803-814f-42f43999ef05",
      "title": "Политика конфиденциальности",
      "slug": "politika-konfidentsialnosti",
      "content": "<p>Текст политики...</p>",
      "file_url": "organization-documents/file.pdf",
      "sort_order": 0,
      "is_active": true,
      "updated_at": "2026-03-15T16:17:08.981717Z"
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

---

### GET /api/v1/admin/organization-documents/{doc_id}

**Стало:** в детальном ответе появилось поле `content_blocks: ContentBlockNested[]`.

```json
{
  "id": "019cf249-7f75-7803-814f-42f43999ef05",
  "title": "Политика конфиденциальности",
  "slug": "politika-konfidentsialnosti",
  "content": "<p>Основной текст документа...</p>",
  "file_url": "organization-documents/file.pdf",
  "sort_order": 0,
  "is_active": true,
  "updated_by": "uuid...",
  "created_at": "2026-03-10T10:00:00Z",
  "updated_at": "2026-03-15T16:17:08.981717Z",
  "content_blocks": [
    {
      "id": "uuid...",
      "block_type": "text",
      "sort_order": 0,
      "title": "Дополнительный раздел",
      "content": "<p>Дополнительный текст...</p>",
      "media_url": null,
      "thumbnail_url": null,
      "link_url": null,
      "link_label": null,
      "device_type": "all",
      "block_metadata": null
    }
  ]
}
```

---

### POST /api/v1/admin/organization-documents
### PATCH /api/v1/admin/organization-documents/{doc_id}

Поле `content` поддерживалось и раньше — HTML-текст основного описания.  
Отправляется как flat `Form` параметр (multipart/form-data):

| Поле         | Тип    | Описание                        |
|--------------|--------|---------------------------------|
| `title`      | string | Заголовок документа             |
| `slug`       | string | URL-slug (необязательно)        |
| `content`    | string | HTML-контент основного описания |
| `sort_order` | int    | Порядок сортировки              |
| `is_active`  | bool   | Активен ли документ             |
| `file`       | file   | PDF/DOC файл (необязательно)    |
| `remove_file`| string | `"true"` — удалить прикреплённый файл (очистить `file_url`) |

#### Удаление прикреплённого файла (PATCH)

Чтобы убрать файл у документа (очистить `file_url`), в PATCH-запрос добавьте поле:

```
remove_file = "true"
```

Если при этом передан и новый `file`, новый файл загружается (заменяет старый). Приоритет у нового файла.

**Пример (fetch + FormData):**
```js
const formData = new FormData();
formData.append("remove_file", "true");
// остальные поля по необходимости

await fetch(`/api/v1/admin/organization-documents/${docId}`, {
  method: "PATCH",
  headers: { Authorization: `Bearer ${token}` },
  body: formData,
});
```

**Чек-лист для реализации в админке:**
1. В форме редактирования документа показать текущий файл (если `file_url` есть) и кнопку/чекбокс «Удалить файл».
2. При нажатии «Удалить файл» — ставить флаг (чекбокс checked или state).
3. При отправке PATCH: если флаг «удалить» включён и **новый файл не выбран** → `formData.append("remove_file", "true")`.
4. Если выбран новый файл — отправлять его как `file`; `remove_file` можно не передавать (новый файл заменит старый).
5. После успешного PATCH обновить UI: `file_url` станет `null`, скрыть превью/ссылку на старый файл.

---

## Чек-лист для фронтенда: удаление файла документа

| Шаг | Действие |
|-----|----------|
| 1 | На странице редактирования документа — отображать текущий `file_url` (название, ссылка на скачивание) |
| 2 | Добавить чекбокс «Удалить прикреплённый файл» (показывать только когда `file_url` не пустой) |
| 3 | При отправке PATCH: если чекбокс отмечен → добавить в FormData: `formData.append("remove_file", "true")` |
| 4 | После успешного ответа — убрать отображение файла, сбросить чекбокс, обновить локальное состояние |
| 5 | Если пользователь одновременно выбрал новый файл и чекбокс — отправлять оба; API загрузит новый файл (приоритет у нового файла) |

---

## Управление content_blocks для документов

Контентные блоки добавляются/редактируются через отдельный API блоков:

| Метод  | URL                             | Описание                             |
|--------|---------------------------------|--------------------------------------|
| GET    | /api/v1/admin/content-blocks?entity_type=organization_document&entity_id={id} | Список блоков документа |
| POST   | /api/v1/admin/content-blocks    | Создать блок                         |
| PATCH  | /api/v1/admin/content-blocks/{block_id} | Обновить блок              |
| DELETE | /api/v1/admin/content-blocks/{block_id} | Удалить блок               |
| PATCH  | /api/v1/admin/content-blocks/reorder   | Переставить блоки по sort_order |

### Пример создания блока:

```json
POST /api/v1/admin/content-blocks
{
  "entity_type": "organization_document",
  "entity_id": "019cf249-7f75-7803-814f-42f43999ef05",
  "block_type": "text",
  "sort_order": 0,
  "title": "Раздел 1",
  "content": "<p>HTML-текст</p>",
  "device_type": "all"
}
```

### Доступные `block_type`:

| Тип           | Описание                         |
|---------------|----------------------------------|
| `text`        | Текстовый блок с HTML            |
| `image`       | Изображение с подписью           |
| `video`       | Видео (URL или embed)            |
| `file`        | Файл для скачивания              |
| `link`        | Ссылка с меткой                  |
| `gallery`     | Галерея изображений              |
| `banner`      | Баннер                           |

---

## Рекомендации для UI

1. **Страница редактирования документа** — добавьте rich-text редактор (Quill, TipTap, CKEditor) для поля `content`.
2. **Секция "Контентные блоки"** — добавьте раздел ниже основной формы, аналогично редактору статей. Позволяет добавлять, редактировать, удалять и перетаскивать блоки.
3. **Список документов** — можно показывать превью `content` (обрезанный текст) в строке таблицы, если нужен предпросмотр.
4. **Структура страницы документа для клиента:**
   - Заголовок (`title`)
   - Основной текст (`content`) — рендерить как HTML
   - Ссылка на файл (`file_url`) если есть
   - Список content_blocks — рендерить по типу блока
