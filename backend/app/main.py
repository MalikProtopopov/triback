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
    logger.info("startup_complete", db=db_ok, redis=redis_ok)
    yield
    logger.info("shutting_down")
    await broker.shutdown()


def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"error": {"code": "RATE_LIMITED", "message": "Too many requests", "details": {}}},
    )


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title="Ассоциация трихологов — API",
        description="Backend API for the Association of Trichologists platform",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)  # type: ignore[arg-type]

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
