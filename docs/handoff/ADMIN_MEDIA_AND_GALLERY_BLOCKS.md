# Медиатека и галереи в контент-блоках (handoff для фронта)

## Медиатека (админ)

Базовый путь: `/api/v1/admin/media`. Роли: **admin** или **manager**, заголовок `Authorization: Bearer <JWT>`.

### `POST /api/v1/admin/media`

- Тело: `multipart/form-data`, поле **`file`** — одно изображение (JPEG, PNG, WebP), до 10 MB.
- Ответ `201`: `id`, **`s3_key`** (это значение нужно сохранять в данных блоков), `public_url` (полный URL для превью в UI), `original_filename`, `mime_type`.
- Файл кладётся в S3 под префиксом `media-library/…`; в БД создаётся строка в `media_assets` для списка.

### `GET /api/v1/admin/media`

- Query: `limit` (1–100, по умолчанию 20), `offset` (по умолчанию 0).
- Ответ: `{ "data": [ { "id", "s3_key", "public_url", "original_filename", "mime_type", "size_bytes", "width", "height", "created_at" } ], "total" }`.
- Сортировка: новые сверху (`created_at` DESC).

## Контент-блок типа `gallery`

### Хранение (запись в API)

- `POST/PATCH /api/v1/admin/content-blocks` с `block_type: "gallery"`.
- В **`block_metadata`** передавайте объект вида:

```json
{
  "images": [
    { "url": "media-library/uuid.jpg", "alt": "Подпись" }
  ]
}
```

- Поле **`url`** в каждом элементе — **S3 object key** (как в ответе медиатеки), без домена. Допустимы и уже сохранённые абсолютные `http(s)://` URL (например старые данные); при отдаче наружу они не дублируются с `S3_PUBLIC_URL`.

### Валидация

- Для `gallery` обязательны непустой массив **`images`** и непустой **`url`** у каждого элемента. Иначе ответ **422** с кодом `VALIDATION_ERROR`.

### Публичные ответы

- В ответах публичных деталок (статья, событие, профиль врача, документ организации) у каждого элемента `content_blocks[]` поле **`block_metadata`** присутствует для типа `gallery`.
- В **`block_metadata.images[].url`** приходят **полные публичные URL** (через `S3_PUBLIC_URL`), если в БД лежал ключ.

## Риски

- Удаление записи из медиатеки или объекта в S3 при использовании того же ключа в `content_blocks` не отслеживается автоматически; отдельного `DELETE` в API пока нет.
