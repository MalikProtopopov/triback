# Публичные URL на основе slug — справочник для клиентского фронтенда

> Дата: 2026-03-15  
> Бэкенд-API: `https://trihoback.mediann.dev/api/v1`

---

## Общий принцип

Все публичные детальные страницы сайта должны использовать **slug** вместо UUID в URL.  
Это необходимо для:
- Человекочитаемых URL (лучший UX)
- SEO-оптимизации (поисковики лучше индексируют осмысленные URL)
- Формирования canonical URL

**Пример:**
```
❌  /doctors/a1b2c3d4-e5f6-7890-abcd-ef1234567890
✅  /doctors/petrov-ivan
```

---

## Публичные эндпоинты по slug

### 1. Врачи

| Эндпоинт | Описание |
|---|---|
| `GET /api/v1/doctors` | Список врачей (каждый элемент содержит поле `slug`) |
| `GET /api/v1/doctors/{identifier}` | Детальная карточка врача. Принимает как UUID, так и slug. |

**Рекомендованные URL на фронте:**
```
/doctors                          → список врачей
/doctors/{slug}                   → детальная карточка
```

**Пример ответа** `GET /api/v1/doctors/petrov-ivan`:
```json
{
  "id": "a1b2c3d4-...",
  "first_name": "Иван",
  "last_name": "Петров",
  "slug": "petrov-ivan",
  "city": "Москва",
  "clinic_name": "Клиника здоровья",
  "specialization": "Трихология",
  "academic_degree": "к.м.н.",
  "bio": "...",
  "photo_url": "/media/doctors/photo.jpg",
  "public_phone": "+79001234567",
  "public_email": "doctor@example.com",
  "seo": {
    "title": "Врач-трихолог Петров Иван",
    "description": "...",
    "og_url": "https://site.com/doctors/petrov-ivan",
    "og_type": "profile",
    "og_image": "/media/doctors/photo.jpg",
    "twitter_card": "summary_large_image",
    "canonical_url": "https://site.com/doctors/petrov-ivan"
  }
}
```

**Фильтрация по городу (через slug):**
```
GET /api/v1/doctors?city_slug=moskva&limit=12&offset=0
```

---

### 2. Города

| Эндпоинт | Описание |
|---|---|
| `GET /api/v1/cities` | Список городов (каждый элемент содержит `slug`) |
| `GET /api/v1/cities?with_doctors=true` | Список городов с количеством врачей |
| `GET /api/v1/cities/{slug}` | Детальная информация о городе по slug |

**Рекомендованные URL на фронте:**
```
/doctors?city=moskva              → список врачей в городе
/cities/{slug}                    → страница города (если есть)
```

**Пример ответа** `GET /api/v1/cities/moskva`:
```json
{
  "id": "...",
  "name": "Москва",
  "slug": "moskva",
  "doctors_count": 42
}
```

---

### 3. Мероприятия

| Эндпоинт | Описание |
|---|---|
| `GET /api/v1/events` | Список мероприятий (каждый элемент содержит `slug`) |
| `GET /api/v1/events/{slug}` | Детальная страница мероприятия |

**Рекомендованные URL на фронте:**
```
/events                           → список мероприятий
/events/{slug}                    → детальная страница
```

**Пример ответа** `GET /api/v1/events/conference-2026`:
```json
{
  "id": "...",
  "title": "Конференция трихологов 2026",
  "slug": "conference-2026",
  "description": "...",
  "event_date": "2026-06-15T10:00:00Z",
  "location": "Москва, Крокус Экспо",
  "cover_image_url": "/media/events/cover.jpg",
  "tariffs": [...],
  "galleries": [...],
  "recordings": [...],
  "seo": {
    "title": "Конференция трихологов 2026",
    "description": "Ежегодная конференция...",
    "canonical_url": "https://site.com/events/conference-2026"
  }
}
```

---

### 4. Статьи

| Эндпоинт | Описание |
|---|---|
| `GET /api/v1/articles` | Список статей (каждый элемент содержит `slug`) |
| `GET /api/v1/articles?theme_slug=alopeciya` | Фильтрация по slug темы |
| `GET /api/v1/articles/{slug}` | Детальная страница статьи |
| `GET /api/v1/article-themes` | Список тем (каждая с `slug`) |

**Рекомендованные URL на фронте:**
```
/articles                         → список статей
/articles?theme=alopeciya         → фильтр по теме
/articles/{slug}                  → детальная страница
```

**Пример ответа** `GET /api/v1/articles/kak-ukhazhivat-za-volosami`:
```json
{
  "id": "...",
  "slug": "kak-ukhazhivat-za-volosami",
  "title": "Как ухаживать за волосами",
  "content": "<p>...</p>",
  "excerpt": "Краткое описание...",
  "cover_image_url": "/media/articles/cover.jpg",
  "published_at": "2026-03-01T12:00:00Z",
  "themes": [
    { "id": "...", "slug": "ukhod", "title": "Уход за волосами" }
  ],
  "seo": {
    "title": "Как ухаживать за волосами",
    "description": "...",
    "canonical_url": "https://site.com/articles/kak-ukhazhivat-za-volosami"
  }
}
```

---

### 5. Документы организации

| Эндпоинт | Описание |
|---|---|
| `GET /api/v1/organization-documents` | Список документов (каждый содержит `slug`) |
| `GET /api/v1/organization-documents/{slug}` | Детальная страница документа |

**Рекомендованные URL на фронте:**
```
/documents                        → список документов
/documents/{slug}                 → детальная страница
```

**Пример ответа** `GET /api/v1/organization-documents/ustav`:
```json
{
  "id": "...",
  "title": "Устав организации",
  "slug": "ustav",
  "content": "<p>Текст устава...</p>",
  "file_url": "/media/docs/ustav.pdf"
}
```

---

### 6. SEO-метаданные

| Эндпоинт | Описание |
|---|---|
| `GET /api/v1/seo/{slug}` | SEO-метаданные для произвольной страницы по slug |

Этот эндпоинт возвращает мета-теги для страниц, настроенных через админ-панель (таблица `page_seo`).

---

## Сводная таблица URL

| Страница | URL на фронте | API-запрос | Поле slug в ответе |
|---|---|---|---|
| Список врачей | `/doctors` | `GET /api/v1/doctors` | `slug` в каждом элементе |
| Карточка врача | `/doctors/{slug}` | `GET /api/v1/doctors/{slug}` | `slug` |
| Список городов | — | `GET /api/v1/cities` | `slug` в каждом элементе |
| Город | `/cities/{slug}` | `GET /api/v1/cities/{slug}` | `slug` |
| Врачи в городе | `/doctors?city={slug}` | `GET /api/v1/doctors?city_slug={slug}` | — |
| Список мероприятий | `/events` | `GET /api/v1/events` | `slug` в каждом элементе |
| Мероприятие | `/events/{slug}` | `GET /api/v1/events/{slug}` | `slug` |
| Список статей | `/articles` | `GET /api/v1/articles` | `slug` в каждом элементе |
| Статья | `/articles/{slug}` | `GET /api/v1/articles/{slug}` | `slug` |
| Список документов | `/documents` | `GET /api/v1/organization-documents` | `slug` в каждом элементе |
| Документ | `/documents/{slug}` | `GET /api/v1/organization-documents/{slug}` | `slug` |

---

## SEO-рекомендации для фронтенда

### Canonical URL

Для каждой детальной страницы формировать `<link rel="canonical">`:
```html
<link rel="canonical" href="https://site.com/doctors/petrov-ivan" />
```

Если в ответе API есть `seo.canonical_url` — использовать его. Иначе формировать из текущего URL.

### Open Graph теги

Если `seo` объект присутствует в ответе:
```html
<meta property="og:title" content="{seo.title}" />
<meta property="og:description" content="{seo.description}" />
<meta property="og:url" content="{seo.og_url || canonical_url}" />
<meta property="og:type" content="{seo.og_type || 'website'}" />
<meta property="og:image" content="{seo.og_image}" />
<meta name="twitter:card" content="{seo.twitter_card || 'summary_large_image'}" />
```

### Sitemap

Рекомендуется генерировать sitemap.xml на основе публичных эндпоинтов:
```xml
<url>
  <loc>https://site.com/doctors/petrov-ivan</loc>
  <lastmod>2026-03-15</lastmod>
</url>
<url>
  <loc>https://site.com/events/conference-2026</loc>
  <lastmod>2026-03-15</lastmod>
</url>
<url>
  <loc>https://site.com/articles/kak-ukhazhivat-za-volosami</loc>
  <lastmod>2026-03-15</lastmod>
</url>
```

### Навигация по slug (Next.js / Nuxt пример)

При переходе на детальную страницу:
1. Извлечь `slug` из URL: `/doctors/petrov-ivan` → `slug = "petrov-ivan"`
2. Запросить `GET /api/v1/doctors/petrov-ivan`
3. Если 404 — показать страницу «Не найдено»
4. Для SSR: использовать SEO-данные из ответа для мета-тегов

---

## Обработка ошибок

| HTTP-код | Описание |
|---|---|
| `200` | Успешный ответ |
| `404` | Сущность не найдена по указанному slug |
| `422` | Невалидные параметры запроса |
