# Content blocks в публичных API статей, мероприятий и врачей

> Обновление бекенда: поля `content_blocks` добавлены в детальные ответы статей, мероприятий и профилей врачей. Документы организации уже поддерживали блоки — см. [CLIENT_ORG_DOCS_CONTENT_BLOCKS.md](CLIENT_ORG_DOCS_CONTENT_BLOCKS.md).

---

## Эндпоинты с `content_blocks`

| Эндпоинт | Страница | Поле |
|----------|----------|------|
| `GET /api/v1/articles/{slug}` | `/articles/[slug]` | `content_blocks` |
| `GET /api/v1/events/{slug}` | `/events/[slug]` | `content_blocks` |
| `GET /api/v1/doctors/{identifier}` | `/doctors/[slug]` | `content_blocks` |
| `GET /api/v1/organization-documents/{slug}` | `/documents/[slug]` | `content_blocks` (ранее) |

---

## Формат `ContentBlockPublicNested`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | string (UUID) | ID блока |
| `block_type` | string | `text`, `image`, `video`, `gallery`, `link` |
| `sort_order` | number | Порядок отображения (ASC) |
| `title` | string \| null | Заголовок блока |
| `content` | string \| null | HTML-контент блока |
| `media_url` | string \| null | URL изображения или видео |
| `thumbnail_url` | string \| null | URL превью |
| `link_url` | string \| null | Ссылка |
| `link_label` | string \| null | Подпись ссылки |
| `device_type` | string | `both`, `mobile`, `desktop` |

---

## Сортировка

Блоки возвращаются отсортированными по `sort_order` (по возрастанию). Отображать в том порядке, в котором приходят.

---

## Учёт `device_type`

- `both` — показывать на всех устройствах
- `mobile` — только на мобильных
- `desktop` — только на десктопе

Пример фильтрации (клиент):
```js
const visibleBlocks = content_blocks.filter(b => {
  if (b.device_type === 'both') return true;
  if (isMobile) return b.device_type === 'mobile';
  return b.device_type === 'desktop';
});
```

---

## Рендеринг по `block_type`

| block_type | Описание | Рендеринг |
|------------|----------|-----------|
| `text` | HTML-текст | `content` как HTML |
| `image` | Изображение | `<img :src="media_url" />` |
| `video` | Видео | `<video>` или iframe embed |
| `gallery` | Галерея | `block_metadata` может содержать массив фото (в public схеме нет `block_metadata` — только базовые поля) |
| `link` | Ссылка | `<a :href="link_url">{{ link_label }}</a>` |

См. подробности в [CLIENT_ORG_DOCS_CONTENT_BLOCKS.md](CLIENT_ORG_DOCS_CONTENT_BLOCKS.md).

---

## Пример ответа (статья)

```json
{
  "id": "uuid...",
  "slug": "kak-ukhazhivat-za-volosami",
  "title": "Как ухаживать за волосами",
  "content": "<p>Основной текст статьи...</p>",
  "excerpt": "Краткое описание",
  "cover_image_url": "/media/...",
  "published_at": "2026-03-01T12:00:00Z",
  "themes": [...],
  "seo": {...},
  "content_blocks": [
    {
      "id": "uuid...",
      "block_type": "text",
      "sort_order": 0,
      "title": "Дополнительный раздел",
      "content": "<p>Дополнительный HTML...</p>",
      "media_url": null,
      "thumbnail_url": null,
      "link_url": null,
      "link_label": null,
      "device_type": "both"
    }
  ]
}
```
