"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from redis.asyncio import Redis
from slowapi.errors import RateLimitExceeded
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import check_db_connection, get_db_session
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import limiter
from app.core.redis import check_redis_connection, get_redis
from app.tasks import broker

logger = get_logger(__name__)

_INSECURE_DEFAULTS = {
    "SECRET_KEY": "change-me-in-production",
    "S3_ACCESS_KEY": "minioadmin",
    "S3_SECRET_KEY": "minioadmin",
}


def _validate_production_config() -> None:
    if settings.DEBUG:
        return
    for attr, insecure in _INSECURE_DEFAULTS.items():
        if getattr(settings, attr, None) == insecure:
            raise RuntimeError(
                f"{attr} still has its insecure default value. "
                "Set it via environment variable before running in production."
            )
    for key_attr in ("JWT_PRIVATE_KEY_PATH", "JWT_PUBLIC_KEY_PATH"):
        path = Path(getattr(settings, key_attr))
        if not path.exists():
            raise RuntimeError(
                f"JWT key file not found: {path}. "
                "Generate keys or set {key_attr} before running in production."
            )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup and shutdown lifecycle manager."""
    configure_logging(debug=settings.DEBUG)
    logger.info("starting_up", debug=settings.DEBUG)

    _validate_production_config()

    db_ok = await check_db_connection()
    redis_ok = await check_redis_connection()

    if not db_ok:
        logger.warning("database_unreachable", hint="Check DATABASE_URL in .env")
    if not redis_ok:
        logger.warning("redis_unreachable", hint="Check REDIS_URL in .env")

    await broker.startup()

    from app.tasks.scheduler import start_scheduler, stop_scheduler

    await start_scheduler()
    logger.info("startup_complete", db=db_ok, redis=redis_ok)
    yield
    logger.info("shutting_down")
    await stop_scheduler()
    await broker.shutdown()


def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": {"code": "RATE_LIMITED", "message": "Too many requests", "details": {}}},
    )


_API_DESCRIPTION = """\
Backend API для платформы «Ассоциация трихологов».

## Авторизация

Большинство эндпоинтов требуют JWT-токен в заголовке:
```
Authorization: Bearer <access_token>
```
Токен получается через `POST /api/v1/auth/login`. Время жизни — 15 минут.
Обновление — через `POST /api/v1/auth/refresh` (refresh token в httpOnly cookie).

## Формат ошибок

Все ошибки возвращаются в едином формате:
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Ресурс не найден",
    "details": {}
  }
}
```

| HTTP-код | code | Описание |
|----------|------|----------|
| 401 | `UNAUTHORIZED` | JWT отсутствует или невалиден |
| 403 | `FORBIDDEN` | Недостаточно прав (роль не подходит) |
| 404 | `NOT_FOUND` | Ресурс не найден |
| 409 | `CONFLICT` | Конфликт данных (дубликат email и т.д.) |
| 422 | `VALIDATION_ERROR` | Ошибка валидации запроса |
| 429 | `RATE_LIMITED` | Слишком много запросов |

## Пагинация

Списковые эндпоинты возвращают:
```json
{
  "data": [...],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```
Query-параметры: `limit` (1-100, default 20), `offset` (>=0, default 0).
"""

_OPENAPI_TAGS = [
    {"name": "Auth", "description": "Регистрация, логин, JWT-токены, смена пароля и email"},
    {"name": "Onboarding", "description": "Выбор роли, заполнение анкеты врача, загрузка документов, отправка на модерацию"},
    {"name": "Profile", "description": "Личный кабинет: личные и публичные данные врача, фото, документы"},
    {"name": "Subscriptions", "description": "Оплата членских взносов, статус подписки, история платежей, чеки"},
    {"name": "Certificates", "description": "Сертификаты членства и участия в мероприятиях"},
    {"name": "Public", "description": "Публичные эндпоинты без авторизации: врачи, мероприятия, статьи, регистрация на мероприятие"},
    {"name": "Voting", "description": "Голосование за президента ассоциации (для врачей с подпиской)"},
    {"name": "Telegram", "description": "Привязка Telegram-аккаунта, генерация кода, webhook бота"},
    {"name": "Admin - Events", "description": "Управление мероприятиями: CRUD, тарифы, галереи, записи, регистрации"},
    {"name": "Admin - Content", "description": "Управление контентом: статьи, темы статей, документы организации"},
    {"name": "Admin - Settings", "description": "Общие настройки сайта, города, тарифные планы подписки"},
    {"name": "Admin - Doctors", "description": "Управление врачами: список, модерация, импорт Excel, пользователи портала"},
    {"name": "Admin - Payments", "description": "Список всех платежей, ручное создание платежей"},
    {"name": "Admin - Dashboard", "description": "Сводная статистика: пользователи, подписки, платежи, мероприятия"},
    {"name": "Admin - Notifications", "description": "Отправка уведомлений пользователям, журнал уведомлений"},
    {"name": "Admin - SEO", "description": "Управление SEO-метаданными страниц"},
    {"name": "Admin - Users", "description": "Управление сотрудниками системы: администраторы, менеджеры, бухгалтеры"},
    {"name": "Admin - Content Blocks", "description": "Управление контентными блоками сущностей (статьи, мероприятия, профили врачей)"},
    {"name": "Webhooks", "description": "Внутренние webhook-эндпоинты (YooKassa). Не вызывать напрямую."},
    {"name": "System", "description": "Служебные эндпоинты: health check"},
]


def _validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    from fastapi.exceptions import RequestValidationError

    assert isinstance(exc, RequestValidationError)
    errors = []
    for err in exc.errors():
        clean = {
            "type": err.get("type", ""),
            "loc": list(err.get("loc", [])),
            "msg": err.get("msg", ""),
        }
        if "input" in err:
            try:
                import json
                json.dumps(err["input"])
                clean["input"] = err["input"]
            except (TypeError, ValueError):
                clean["input"] = str(err["input"])
        errors.append(clean)
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"errors": errors},
            }
        },
    )


def create_app() -> FastAPI:
    """Application factory."""
    from fastapi.exceptions import RequestValidationError

    app = FastAPI(
        title="Ассоциация трихологов — API",
        description=_API_DESCRIPTION,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_tags=_OPENAPI_TAGS,
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_error_handler)  # type: ignore[arg-type]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)

    from app.api.v1 import router as api_v1_router

    app.include_router(api_v1_router)

    return app


app = create_app()


# Health check endpoint — always available
@app.get("/api/v1/health", tags=["System"])
async def health_check() -> dict:
    """Return service health status including DB and Redis availability."""
    db_ok = await check_db_connection()
    redis_ok = await check_redis_connection()
    return {
        "status": "ok" if (db_ok and redis_ok) else "degraded",
        "db": db_ok,
        "redis": redis_ok,
    }


@app.get("/robots.txt", include_in_schema=False)
async def robots_txt() -> Response:
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {settings.FRONTEND_URL}/sitemap.xml\n"
    )
    return Response(content=body, media_type="text/plain")


_SITEMAP_CACHE_TTL = 3600


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> Response:
    cache_key = "cache:sitemap_xml"
    cached = await redis.get(cache_key)
    if cached:
        return Response(content=cached, media_type="application/xml")

    from sqlalchemy import select

    from app.models.content import Article
    from app.models.events import Event
    from app.models.profiles import DoctorProfile

    base_url = settings.FRONTEND_URL
    urls: list[str] = [
        base_url, f"{base_url}/doctors", f"{base_url}/events", f"{base_url}/articles",
    ]

    doctors = (await db.execute(
        select(DoctorProfile.slug).where(
            DoctorProfile.status == "active",
            DoctorProfile.slug.isnot(None),
        )
    )).scalars().all()
    for slug in doctors:
        urls.append(f"{base_url}/doctors/{slug}")

    events = (await db.execute(select(Event.slug))).scalars().all()
    for slug in events:
        urls.append(f"{base_url}/events/{slug}")

    articles = (await db.execute(
        select(Article.slug).where(Article.status == "published")
    )).scalars().all()
    for slug in articles:
        urls.append(f"{base_url}/articles/{slug}")

    xml_entries = "\n".join(f"  <url><loc>{u}</loc></url>" for u in urls)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{xml_entries}\n"
        "</urlset>\n"
    )

    await redis.set(cache_key, xml, ex=_SITEMAP_CACHE_TTL)
    return Response(content=xml, media_type="application/xml")
