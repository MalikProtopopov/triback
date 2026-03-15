# Документы организации: content и content_blocks (Клиентский фронт)

Обновление публичного API: страница детального просмотра документа теперь возвращает `content_blocks` для расширенного отображения контента.

---

## Изменения в публичном API

### GET /api/v1/organization-documents

Список активных документов (без изменений — поле `content` уже было):

```json
{
  "data": [
    {
      "id": "019cf249-7f75-7803-814f-42f43999ef05",
      "title": "Политика конфиденциальности",
      "slug": "politika-konfidentsialnosti",
      "content": "<p>Краткое описание или полный текст...</p>",
      "file_url": "https://cdn.example.com/org-docs/file.pdf"
    }
  ]
}
```

---

### GET /api/v1/organization-documents/{slug}

**Новое поле:** `content_blocks: ContentBlockPublicNested[]`

```json
{
  "id": "019cf249-7f75-7803-814f-42f43999ef05",
  "title": "Политика конфиденциальности",
  "slug": "politika-konfidentsialnosti",
  "content": "<p>Основной текст документа в HTML...</p>",
  "file_url": "https://cdn.example.com/org-docs/file.pdf",
  "content_blocks": [
    {
      "id": "uuid...",
      "block_type": "text",
      "sort_order": 0,
      "title": "Раздел 1: Общие положения",
      "content": "<p>Текст раздела...</p>",
      "media_url": null,
      "thumbnail_url": null,
      "link_url": null,
      "link_label": null,
      "device_type": "all"
    },
    {
      "id": "uuid...",
      "block_type": "file",
      "sort_order": 1,
      "title": "Скачать полный текст",
      "content": null,
      "media_url": "https://cdn.example.com/files/policy_full.pdf",
      "thumbnail_url": null,
      "link_url": null,
      "link_label": "Скачать PDF",
      "device_type": "all"
    }
  ]
}
```

---

## Схема `ContentBlockPublicNested`

| Поле            | Тип            | Описание                               |
|-----------------|----------------|----------------------------------------|
| `id`            | string (UUID)  | ID блока                               |
| `block_type`    | string         | Тип блока (см. таблицу ниже)           |
| `sort_order`    | number         | Порядок отображения (ASC)              |
| `title`         | string \| null | Заголовок блока                        |
| `content`       | string \| null | HTML-контент блока                     |
| `media_url`     | string \| null | URL изображения или видео              |
| `thumbnail_url` | string \| null | URL превью для видео/галереи           |
| `link_url`      | string \| null | Ссылка                                 |
| `link_label`    | string \| null | Подпись ссылки                         |
| `device_type`   | string         | `all` \| `desktop` \| `mobile`        |

---

## Рендеринг блоков по `block_type`

### `text`
Рендерить `content` как HTML:
```html
<div v-html="block.content" class="rich-text"></div>
```

### `image`
```html
<figure>
  <img :src="block.media_url" :alt="block.title" />
  <figcaption v-if="block.title">{{ block.title }}</figcaption>
</figure>
```

### `video`
```html
<video :src="block.media_url" controls :poster="block.thumbnail_url" />
<!-- или iframe embed если media_url — YouTube/Vimeo ссылка -->
```

### `file`
```html
<a :href="block.media_url" download>
  {{ block.link_label || block.title || 'Скачать файл' }}
</a>
```

### `link`
```html
<a :href="block.link_url" target="_blank">
  {{ block.link_label || block.link_url }}
</a>
```

### `gallery`
Массив изображений — используйте `media_url` и `thumbnail_url` для lightbox-галереи.

### `banner`
```html
<div class="banner">
  <img :src="block.media_url" />
  <div class="banner-text" v-html="block.content"></div>
  <a v-if="block.link_url" :href="block.link_url">{{ block.link_label }}</a>
</div>
```

---

## Рекомендуемая структура страницы документа

```
/documents/:slug  →  GET /api/v1/organization-documents/:slug
```

Структура отображения:
1. **Заголовок** — `doc.title`
2. **Основной текст** — `doc.content` (HTML, рендерить через v-html или dangerouslySetInnerHTML)
3. **Кнопка скачать** — если `doc.file_url` не null, показать ссылку/кнопку
4. **Контентные блоки** — перебрать `doc.content_blocks` по `sort_order`, рендерить по `block_type`

---

## Фильтрация по `device_type`

Если нужно адаптировать отображение под устройства:

```javascript
const visibleBlocks = doc.content_blocks.filter(
  b => b.device_type === 'all' || b.device_type === currentDevice
)
```

где `currentDevice` — `'desktop'` или `'mobile'`.

---

## URL-структура

| Страница          | URL                    | API                                        |
|-------------------|------------------------|--------------------------------------------|
| Список документов | `/documents`           | `GET /api/v1/organization-documents`       |
| Страница документа | `/documents/:slug`    | `GET /api/v1/organization-documents/:slug` |

---

## SEO-рекомендации

- `<title>`: `doc.title + " — Название сайта"`
- `<meta name="description">`: первые 160 символов из `doc.content` (очищенный от HTML)
- `<link rel="canonical">`: полный URL страницы
- Если `doc.file_url` есть — добавить `<link rel="alternate" type="application/pdf" href="...">`
