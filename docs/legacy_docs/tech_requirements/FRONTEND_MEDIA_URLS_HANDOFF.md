# Handoff: изображения и файлы теперь возвращаются как полные URL

**Дата:** 2026-03-17

---

## Что изменилось

Ранее API возвращал S3-ключи (например `events/covers/uuid.jpg`) в полях изображений и файлов. Теперь API возвращает **полные URL**, готовые к использованию в `<img src>`, `<a href>` и т.д.

Пример до:
```json
{ "cover_image_url": "events/covers/a1b2c3.jpg" }
```

Пример после:
```json
{ "cover_image_url": "https://api.trichologia.ru/media/events/covers/a1b2c3.jpg" }
```

Если поле равно `null` — оно остаётся `null`.

---

## Затронутые поля

Все поля ниже теперь возвращают полный URL или `null`:

| Поле | Где встречается |
|------|-----------------|
| `cover_image_url` | Статьи, мероприятия |
| `photo_url` | Профили врачей, кандидаты голосования |
| `diploma_photo_url` | Профиль врача (админ, личный кабинет) |
| `media_url` | Content blocks |
| `thumbnail_url` | Content blocks, фото галерей, превью |
| `file_url` | Документы врачей, документы организации, фото галерей |
| `og_image_url` | SEO-страницы |
| `og_image` | SEO-вложения в ответах (статьи, мероприятия, врачи) |

---

## Затронутые эндпоинты

### Клиентский сайт (публичные)

| Эндпоинт | Поля |
|----------|------|
| `GET /doctors` | `photo_url` |
| `GET /doctors/{id}` | `photo_url`, `og_image`, `media_url`, `thumbnail_url` в content_blocks |
| `GET /events` | `cover_image_url` |
| `GET /events/{slug}` | `cover_image_url`, `og_image`, `thumbnail_url` (превью галерей), `media_url`, `thumbnail_url` в content_blocks |
| `GET /events/{id}/galleries` | `file_url`, `thumbnail_url` в фотографиях |
| `GET /articles` | `cover_image_url` |
| `GET /articles/{slug}` | `cover_image_url`, `og_image`, `media_url`, `thumbnail_url` в content_blocks |
| `GET /organization-documents` | `file_url` |
| `GET /organization-documents/{slug}` | `file_url`, `media_url`, `thumbnail_url` в content_blocks |
| `GET /seo/{slug}` | `og_image_url` |
| `GET /voting/active` | `photo_url` у кандидатов |

### Личный кабинет

| Эндпоинт | Поля |
|----------|------|
| `GET /profile/personal` | `diploma_photo_url` |
| `GET /profile/public` | `photo_url` |
| `POST /profile/photo` | `photo_url` в ответе |
| `POST /profile/diploma-photo` | `diploma_photo_url` в ответе |

### Админ-панель

| Эндпоинт | Поля |
|----------|------|
| `GET /admin/articles` | `cover_image_url` |
| `GET /admin/articles/{id}` | `cover_image_url`, `media_url`, `thumbnail_url` в content_blocks |
| `GET /admin/events` | `cover_image_url` |
| `GET /admin/events/{id}` | `cover_image_url`, `media_url`, `thumbnail_url` в content_blocks |
| `POST /admin/events/{id}/galleries/{gid}/photos` | `file_url`, `thumbnail_url` в photos |
| `GET /admin/doctors/{id}` | `photo_url`, `diploma_photo_url`, `file_url` в documents, `media_url`, `thumbnail_url` в content_blocks |
| `GET /admin/organization-documents` | `file_url` |
| `GET /admin/organization-documents/{id}` | `file_url`, `media_url`, `thumbnail_url` в content_blocks |
| `GET /admin/content-blocks` | `media_url`, `thumbnail_url` |
| `GET /admin/seo-pages` | `og_image_url` |
| `GET /admin/voting/{id}` | `photo_url` у кандидатов |
| `GET /admin/voting/{id}/results` | (через кандидатов) |

---

## Что делать фронтенду

### Клиентский сайт + Админка

1. **Использовать URL напрямую.** Значения `cover_image_url`, `photo_url`, `media_url`, `thumbnail_url`, `file_url`, `og_image_url` — это готовые URL. Подставлять их в `src`, `href` и мета-теги без преобразований.

2. **Убрать конкатенацию**, если ранее на фронте URL собирался вручную из базового адреса и ключа.

3. **Обработка `null`.** Если поле `null` — изображения нет, показывать placeholder или скрывать элемент.

4. **Переменные окружения фронта не меняются.** `NEXT_PUBLIC_API_URL` остаётся прежним.

---

## Исключения (не затронуто)

| Что | Причина |
|-----|---------|
| `download_url` сертификатов (`GET /certificates`) | Используются presigned URL с ограниченным TTL |
| `video_playback_url` записей мероприятий | Используются presigned URL с ограниченным TTL |

Эти поля продолжают возвращать временные presigned URL — с ними ничего делать не нужно.

---

## Окружения

| Окружение | Базовый URL медиа | Пример полного URL |
|-----------|-------------------|--------------------|
| Dev (localhost) | `http://localhost:9000/triho-dev` | `http://localhost:9000/triho-dev/events/covers/uuid.jpg` |
| Prod | `https://api.trichologia.ru/media` | `https://api.trichologia.ru/media/events/covers/uuid.jpg` |

В prod запросы к `/media/*` проксируются nginx на MinIO.
