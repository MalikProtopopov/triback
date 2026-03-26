# Сертификаты — Админ-панель

**Дата:** 2026-03-21  
**Кому:** Фронтенд-разработчик админ-панели  
**Тема:** Управление настройками сертификатов, просмотр, скачивание, регенерация

---

## Что добавлено

1. Новый раздел **«Настройки сертификатов»** — задание данных организации, загрузка логотипа, печати, подписи.
2. На странице **детали врача** — вкладка/блок «Сертификаты» с предпросмотром и скачиванием.
3. Возможность **регенерации** сертификата вручную.
4. Возможность **вкл/выкл** активности сертификата.
5. **Массовая регенерация** всех активных сертификатов текущего года.

---

## 1. Настройки сертификатов

### 1.1. Получить настройки: `GET /api/v1/admin/certificate-settings`

**Роль:** admin

```json
{
  "id": 1,
  "president_full_name": "Гаджигороева Аида Гусейхановна",
  "president_title": "Президент д.м.н.",
  "organization_full_name": "Межрегиональная общественная организация...",
  "organization_short_name": "Профессиональное общество трихологов",
  "certificate_member_text": "является действительным членом...",
  "logo_url": "https://s3.../certificate-assets/uuid.png",
  "stamp_url": "https://s3.../certificate-assets/uuid.png",
  "signature_url": "https://s3.../certificate-assets/uuid.png",
  "background_url": null,
  "certificate_number_prefix": "TRICH",
  "validity_text_template": "Действителен с {year} г.",
  "updated_at": "2026-03-21T12:00:00+00:00"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `president_full_name` | string / null | ФИО президента (отображается на сертификате) |
| `president_title` | string / null | Должность (напр. "Президент д.м.н.") |
| `organization_full_name` | string / null | Полное название организации |
| `organization_short_name` | string / null | Краткое название |
| `certificate_member_text` | string / null | Шаблон тела сертификата. Поддерживает `{full_name}`, `{year}` |
| `logo_url` | string / null | URL логотипа (отображать как превью) |
| `stamp_url` | string / null | URL печати |
| `signature_url` | string / null | URL подписи |
| `background_url` | string / null | URL фонового изображения (watermark) |
| `certificate_number_prefix` | string | Префикс номера (напр. "TRICH") |
| `validity_text_template` | string / null | Шаблон строки валидности. Поддерживает `{year}` |

### 1.2. Обновить настройки: `PATCH /api/v1/admin/certificate-settings`

**Роль:** admin

Тело запроса (partial, отправлять только изменённые поля):

```json
{
  "president_full_name": "Новый Президент",
  "president_title": "Президент к.м.н.",
  "certificate_number_prefix": "PROF"
}
```

### 1.3. Загрузка изображений

Четыре отдельных эндпоинта, каждый принимает `multipart/form-data` с полем `file`:

| Эндпоинт | Что загружает |
|----------|---------------|
| `POST /api/v1/admin/certificate-settings/logo` | Логотип организации |
| `POST /api/v1/admin/certificate-settings/stamp` | Изображение печати (PNG с прозрачностью) |
| `POST /api/v1/admin/certificate-settings/signature` | Подпись президента (PNG с прозрачностью) |
| `POST /api/v1/admin/certificate-settings/background` | Фоновое изображение / watermark |

**Ограничения:** PNG/JPEG/WebP, максимум 2 МБ.

Пример загрузки:

```js
const formData = new FormData()
formData.append('file', selectedFile)

await api.post('/admin/certificate-settings/stamp', formData, {
  headers: { 'Content-Type': 'multipart/form-data' }
})
```

Ответ — обновлённый объект настроек (как в GET).

### Дизайн страницы настроек

Форма с текстовыми полями + три блока загрузки изображений:
- Каждый блок: текущее превью (если URL не null) + кнопка "Загрузить"
- Кнопка "Сохранить" отправляет PATCH с текстовыми полями
- Загрузка изображений — отдельные POST запросы

---

## 2. Сертификаты врача (на странице детали врача)

### 2.1. Список: `GET /api/v1/admin/doctors/{doctor_id}/certificates`

**Роль:** admin, manager

```json
[
  {
    "id": "uuid",
    "certificate_type": "member",
    "year": 2026,
    "certificate_number": "TRICH-2026-000001",
    "is_active": true,
    "generated_at": "2026-03-21T12:00:00+00:00",
    "download_url": "https://s3.../presigned..."
  }
]
```

### 2.2. Предпросмотр / скачивание: `GET /api/v1/admin/certificates/{certificate_id}/download`

**Роль:** admin, manager

| Query параметр | Значение | Описание |
|----------------|----------|----------|
| `disposition` | `inline` (по умолч.) | Открыть в браузере (предпросмотр) |
| `disposition` | `attachment` | Скачать файл |

Ответ: **302 redirect** на presigned S3 URL.

```js
// Предпросмотр в новой вкладке
window.open(`/api/v1/admin/certificates/${certId}/download`)

// Скачивание
window.open(`/api/v1/admin/certificates/${certId}/download?disposition=attachment`)
```

### 2.3. Регенерация: `POST /api/v1/admin/doctors/{doctor_id}/certificates/regenerate`

**Роль:** admin, manager

Тело:

```json
{
  "year": 2026
}
```

Если `year` не указан — используется текущий год.

Ответ — обновлённый объект сертификата.

### 2.4. Вкл/выкл активности: `PATCH /api/v1/admin/certificates/{certificate_id}`

**Роль:** admin

```json
{
  "is_active": false
}
```

### Дизайн на странице врача

Таблица/список с колонками:
- Номер сертификата
- Тип (`member` / `event`)
- Год
- Статус (активен / неактивен — цветной бейдж)
- Дата генерации
- Действия: «Просмотр» (inline), «Скачать» (attachment), «Регенерировать», «Деактивировать»

---

## 3. Массовая регенерация

### `POST /api/v1/admin/certificate-settings/regenerate-all`

**Роль:** admin

Тело: не требуется.

```json
// Ответ
{
  "dispatched": 42,
  "year": 2026
}
```

Запускает фоновую регенерацию всех активных member-сертификатов текущего года. Полезно после смены настроек (новый президент, новый логотип и т.д.).

Рекомендуется добавить кнопку на странице настроек сертификатов:
- "Перегенерировать все сертификаты ({year})"
- Показать confirmation dialog: "Будет перегенерировано N сертификатов. Продолжить?"
- После — показать toast: "Запущена регенерация {dispatched} сертификатов"

---

## 4. Sidebar / навигация

Добавить пункт в сайдбар admin-панели:

- Раздел **«Настройки»** → подпункт **«Сертификаты»** → ведёт на страницу настроек сертификатов
- На странице **детали врача** → вкладка/секция **«Сертификаты»**

---

## 5. Резюме новых эндпоинтов

| Метод | Путь | Роль | Описание |
|-------|------|------|----------|
| GET | `/admin/certificate-settings` | admin | Получить настройки |
| PATCH | `/admin/certificate-settings` | admin | Обновить текстовые настройки |
| POST | `/admin/certificate-settings/logo` | admin | Загрузить логотип |
| POST | `/admin/certificate-settings/stamp` | admin | Загрузить печать |
| POST | `/admin/certificate-settings/signature` | admin | Загрузить подпись |
| POST | `/admin/certificate-settings/background` | admin | Загрузить фон |
| POST | `/admin/certificate-settings/regenerate-all` | admin | Массовая регенерация |
| GET | `/admin/doctors/{id}/certificates` | admin, manager | Список сертификатов врача |
| GET | `/admin/certificates/{id}/download` | admin, manager | Скачать/предпросмотр |
| POST | `/admin/doctors/{id}/certificates/regenerate` | admin, manager | Регенерация |
| PATCH | `/admin/certificates/{id}` | admin | Вкл/выкл активности |
