#!/usr/bin/env python3
"""Generate docs/API_ENDPOINT_MATRIX.md from the FastAPI app (OpenAPI + route deps).

Run from repo root:
  cd backend && PYTHONPATH=. poetry run python ../scripts/generate_api_endpoint_matrix.py
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

# Ensure backend is on path when run as ../scripts/ from backend/
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
if _BACKEND.is_dir():
    sys.path.insert(0, str(_BACKEND))

from fastapi.routing import APIRoute  # noqa: E402

from app.main import app  # noqa: E402

DOC_PATH = Path(__file__).resolve().parent.parent / "docs" / "API_ENDPOINT_MATRIX.md"

# Paths where dependency introspection is "no JWT" but external trust applies
TRUST_OVERRIDES: dict[str, str] = {
    "/api/v1/webhooks/yookassa": "IP allowlist `YOOKASSA_IP_WHITELIST` (+ dedup Redis)",
    "/api/v1/webhooks/yookassa/v2": "Feature flag; IP allowlist; inbox + TaskIQ",
    "/api/v1/webhooks/moneta": "Подпись Moneta Pay URL (MD5) + dedup Redis",
    "/api/v1/webhooks/moneta/check": "Подпись Moneta Check URL (MD5)",
    "/api/v1/webhooks/moneta/receipt": "Заголовок `X-Moneta-Receipt-Secret` и/или `MONETA_RECEIPT_IP_ALLOWLIST`",
    "/api/v1/telegram/webhook": "Telegram (legacy; без JWT)",
    "/api/v1/telegram/webhook/{webhook_secret}": "Секрет в пути (`TELEGRAM_WEBHOOK_SECRET`)",
}


def auth_info(dep) -> tuple[bool, str, bool]:
    """(jwt_or_role_required, roles_or_note, optional_jwt)."""
    roles_found: str | None = None
    has_current_user = False
    has_optional = False
    if not dep.dependencies:
        return False, "—", False
    for d in dep.dependencies:
        fn = d.call
        if fn is None:
            continue
        name = getattr(fn, "__name__", "")
        if name == "_check_role":
            cv = inspect.getclosurevars(fn)
            r = cv.nonlocals.get("roles")
            if r:
                roles_found = ", ".join(r)
        elif name in ("get_current_user", "get_current_user_id"):
            has_current_user = True
        elif name == "get_optional_user_id":
            has_optional = True
    if roles_found:
        return True, roles_found, False
    if has_current_user:
        return True, "любая роль из JWT (doctor / user / admin / manager / accountant)", False
    if has_optional:
        return False, "публично; опционально JWT — см. §2", True
    return False, "—", False


def side_effect_heuristic(method: str, path: str) -> str:
    if "/webhooks/" in path:
        return "Да (обработка уведомления; см. §3)"
    if method in ("POST", "PUT", "PATCH", "DELETE"):
        return "Да (обычно БД; см. §3)"
    if path == "/sitemap.xml":
        return "Да (кеш Redis при промахе)"
    return "Нет (чтение)"


def walk_routes(routes, prefix: str = ""):
    for r in routes:
        if isinstance(r, APIRoute):
            path = prefix + r.path
            for m in r.methods:
                if m == "HEAD":
                    continue
                yield m, path, r.summary or "", r.dependant
        elif hasattr(r, "routes"):
            p = prefix + (getattr(r, "path", "") or "")
            yield from walk_routes(r.routes, p)


def main() -> None:
    rows: list[tuple[str, str, str, str, str, str]] = []
    for method, path, summary, dep in sorted(walk_routes(app.routes), key=lambda x: (x[1], x[0])):
        jwt_or_role, roles_note, opt_jwt = auth_info(dep)
        if path in TRUST_OVERRIDES:
            roles_note = TRUST_OVERRIDES[path]
            jwt_or_role = False
            opt_jwt = False
        if jwt_or_role:
            auth_req = "Да"
        elif path in TRUST_OVERRIDES or (
            path.startswith("/api/v1/webhooks") and path not in TRUST_OVERRIDES
        ):
            auth_req = "Спец."
        elif opt_jwt:
            auth_req = "Нет (опц. JWT)"
        else:
            auth_req = "Нет"
        se = side_effect_heuristic(method, path)
        rows.append((method, path, roles_note, auth_req, summary, se))

    lines: list[str] = [
        "# Матрица эндпоинтов API (trihoback)",
        "",
        "Документ сгенерирован скриптом [`scripts/generate_api_endpoint_matrix.py`](../scripts/generate_api_endpoint_matrix.py).",
        "",
        "**OpenAPI / Swagger:** на поднятом backend — `/openapi.json`, `/docs`. Публичный стенд: [Swagger UI](https://trihoback.mediann.dev/docs#/), [openapi.json](https://trihoback.mediann.dev/openapi.json). Число операций на стенде может быть меньше, чем строк в §1, пока не выкатена текущая версия API из репозитория.",
        "",
        "## 1. Полная таблица эндпоинтов",
        "",
        "| Метод | Путь | Роли / доверие | Auth (JWT/роль) | Краткое описание | Side-effect (эвристика) |",
        "|-------|------|----------------|-----------------|------------------|---------------------------|",
    ]
    for method, path, roles, auth_req, summary, se in rows:
        summ = (summary or "").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {method} | `{path}` | {roles} | {auth_req} | {summ} | {se} |"
        )

    lines.extend(
        [
            "",
            "## 2. Нетривиальная матрица доступа",
            "",
            "Здесь — случаи, когда **одной роли из таблицы недостаточно**: ответ или допуск зависят от состояния объекта, опционального токена или внешней подписи.",
            "",
            "| Эндпоинт | Условие | Поведение |",
            "|----------|---------|-----------|",
            "| `GET/POST` `/api/v1/events/{id}/register` | Есть валидный JWT | Регистрация авторизованного пользователя; без токена — сценарий гостя / `login_required` |",
            "| `GET/POST` `/api/v1/events/{id}/register` | Нет JWT, не передан guest-поток | Возможен **422** (нужен email и т.д.) |",
            "| `GET` `/api/v1/events/{event_id}/galleries`, `/recordings` | `access_level` members_only / participants_only | Контент скрыт без активной подписки или подтверждённой регистрации на это событие |",
            "| `POST` `/api/v1/voting/{session_id}/vote` | JWT роль `doctor` | Дополнительно: **403**, если нет активного членства (подписка) — см. `voting_service` |",
            "| `GET` … `/subscriptions/payments/...`, `check-status` | JWT `doctor` | Платёж должен принадлежать текущему пользователю; иначе **403** (`payment_status_service`) |",
            "| `GET` … `/certificates` (ЛК) | JWT `doctor` | Сертификаты только для активных врачей; иначе **403** |",
            "| `POST` `/api/v1/webhooks/yookassa` | IP не в whitelist | **403** |",
            "| `POST` `/api/v1/webhooks/moneta/receipt` | Prod без секрета и allowlist | **403** |",
            "| `POST` `/api/v1/webhooks/yookassa/v2` | `WEBHOOK_INBOX_ENABLED=false` | **404** |",
            "| Админ `DELETE` части контента (статьи, темы, …) | См. код | Часть операций только **`admin`**, хотя PATCH/GET — admin+manager |",
            "",
            "_Уточняйте по сервисам: `event_public_service`, `event_registration_service`, `voting_service`, `payment_status_service`, `certificate_service`._",
            "",
            "## 3. Side-эффекты (важные для тестирования)",
            "",
            "### 3.1 Всегда с побочными эффектами",
            "",
            "- **Все** `POST` / `PUT` / `PATCH` / `DELETE` в админке и ЛК (запись в БД, часто S3 для файлов).",
            "- **Auth:** регистрация, сброс пароля, смена email — отправка писем (SMTP / очередь).",
            "- **Webhooks Moneta:** Pay URL — обновление платежа, подписки, регистрации; Check URL — XML, возможны commit полей Moneta operation id; Receipt — запись чека, задачи email/Telegram.",
            "- **Webhooks YooKassa:** обработка события, Redis dedup.",
            "- **Admin:** `POST .../notifications/send`, ручные платежи / refund / cancel, импорт врачей, модерация, генерация сертификатов.",
            "",
            "### 3.2 GET с эффектами",
            "",
            "- `GET /sitemap.xml` — при промахе кеша пересборка и запись в Redis.",
            "- Остальные `GET` по умолчанию только чтение (кеш Redis на публичных списках возможен — см. сервисы).",
            "",
            "### 3.3 Rate limit (отдельно от RBAC)",
            "",
            "- Часть маршрутов помечена `slowapi` (например auth, публичные события, YooKassa legacy webhook).",
            "- Эндпоинты **Moneta** Pay / Check / receipt **без** лимита (серверные вызовы Moneta).",
            "",
        ]
    )

    DOC_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {DOC_PATH}")


if __name__ == "__main__":
    main()
