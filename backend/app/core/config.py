"""Application configuration via Pydantic Settings."""

import json
from typing import Annotated, Any, Literal

from pydantic import AliasChoices, BeforeValidator, Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_cors_origins(value: Any) -> list[str]:
    """Parse CORS origins from env: JSON array or comma-separated string.

    Env: ``CORS_ALLOWED_ORIGINS`` (preferred) or legacy ``ALLOWED_HOSTS``.
    """
    if isinstance(value, list):
        return [str(v).strip() for v in value if v]
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return ["*"]
        if s.startswith("["):
            try:
                parsed = json.loads(s)
                return [str(v).strip() for v in parsed if v]
            except json.JSONDecodeError:
                pass
        return [v.strip() for v in s.split(",") if v.strip()]
    return ["*"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Application
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ENCRYPTION_KEY: str = ""  # Fernet base64 key for encrypting sensitive data (e.g. bot tokens)
    CORS_ALLOWED_ORIGINS: Annotated[list[str], BeforeValidator(_parse_cors_origins)] = Field(
        default=["*"],
        validation_alias=AliasChoices("CORS_ALLOWED_ORIGINS", "ALLOWED_HOSTS"),
    )

    # JWT (RS256)
    JWT_PRIVATE_KEY_PATH: str = "keys/private.pem"
    JWT_PUBLIC_KEY_PATH: str = "keys/public.pem"
    JWT_AUDIENCE: str = "trihoback-api"
    JWT_ISSUER: str = "trihoback"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Database
    DATABASE_URL: PostgresDsn = PostgresDsn(
        "postgresql+asyncpg://triho_user:triho_pass@localhost:5432/triho_db"
    )

    # Redis
    REDIS_URL: RedisDsn = RedisDsn("redis://localhost:6379/0")

    # S3 / Object Storage
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "triho-dev"
    S3_PUBLIC_URL: str = ""

    # Payment provider: Moneta (PayAnyWay / MerchantAPI v2) is the default production path.
    # YooKassa remains available for legacy / alternate deployments (set PAYMENT_PROVIDER=yookassa).
    PAYMENT_PROVIDER: str = "moneta"  # "moneta" | "yookassa"

    # Moneta — MerchantAPI v2 auth
    MONETA_USERNAME: str = ""
    MONETA_PASSWORD: str = ""
    MONETA_SERVICE_URL: str = "https://service.moneta.ru/services"
    MONETA_PAYEE_ACCOUNT: str = ""
    MONETA_PAYMENT_PASSWORD: str = ""

    # Moneta — Assistant (payment form)
    MONETA_MNT_ID: str = ""
    MONETA_ASSISTANT_URL: str = "https://www.payanyway.ru/assistant.htm"
    MONETA_WIDGET_URL: str = "https://www.payanyway.ru/assistant.widget"
    MONETA_DEMO_MODE: bool = False

    # Moneta — webhook (Pay URL / Check URL)
    MONETA_WEBHOOK_SECRET: str = ""

    # Moneta — receipt webhook (54-FZ JSON callback). If secret is set, require header
    # ``X-Moneta-Receipt-Secret`` with the same value (preferred). If secret is empty
    # but MONETA_RECEIPT_IP_ALLOWLIST is set, client IP must match (CIDR list like YooKassa).
    # If both empty: allow only when DEBUG=True (logged); in production returns 403.
    MONETA_RECEIPT_WEBHOOK_SECRET: str = ""
    MONETA_RECEIPT_IP_ALLOWLIST: str = ""

    # Moneta — redirect URLs for buyer
    MONETA_SUCCESS_URL: str = ""
    MONETA_FAIL_URL: str = ""
    MONETA_INPROGRESS_URL: str = ""
    MONETA_RETURN_URL: str = ""

    # Moneta — payment form version (v3 supports SBP, SberPay)
    MONETA_FORM_VERSION: str = "v3"

    # Feature flags
    # Enable the new inbox-based YooKassa webhook pipeline (/webhooks/yookassa/v2).
    # When True, the new endpoint persists raw webhooks to payment_webhook_inbox and
    # processes them asynchronously via TaskIQ (requires the inbox migration to be applied).
    WEBHOOK_INBOX_ENABLED: bool = False

    # YooKassa — только при PAYMENT_PROVIDER=yookassa (не нужны при работе через Moneta)
    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""
    YOOKASSA_API_URL: str = "https://api.yookassa.ru/v3"
    YOOKASSA_RETURN_URL: str = "https://trichology.ru/payment/result"
    YOOKASSA_IP_WHITELIST: str = "185.71.76.0/27,185.71.77.0/27,77.75.153.0/25,77.75.156.11/32,77.75.156.35/32"
    # After IP allowlist, optionally confirm payment.succeeded via GET /payments/{id}.
    # Enable in production (set ``YOOKASSA_WEBHOOK_VERIFY_WITH_API=true``); default off for dev/tests.
    YOOKASSA_WEBHOOK_VERIFY_WITH_API: bool = False
    PAYMENT_IDEMPOTENCY_TTL: int = 86400
    PAYMENT_EXPIRATION_HOURS: int = 24

    # SMTP
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@triho.ru"
    SMTP_TLS: bool = False

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHANNEL_ID: str = ""
    # Чат для выгрузок XLSX (POST /exports/*/telegram); если пусто — используется TELEGRAM_CHANNEL_ID
    TELEGRAM_EXPORTS_CHAT_ID: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""

    # API (для полных URL в ответах, например download_url сертификатов)
    # Если пусто — возвращаются относительные пути (клиент должен добавить base)
    PUBLIC_API_URL: str = ""

    # Frontend
    FRONTEND_URL: str = "https://trichology.ru"
    ADMIN_FRONTEND_URL: str = ""  # URL админки; если пусто — письма staff идут на FRONTEND_URL

    # Certificates
    CERTIFICATE_QR_BASE_URL: str = ""  # fallback to FRONTEND_URL when empty

    # Auth cookies (domain for cross-subdomain sharing, e.g. .trichologia.mediann.dev)
    COOKIE_DOMAIN: str | None = None
    # ``none`` — required for cross-site credentialed requests; XSS on allowed origins is a risk.
    # ``lax`` — safer if API and SPA share a site (no cross-origin cookie auth).
    ACCESS_TOKEN_COOKIE_SAMESITE: Literal["lax", "none"] = "none"


settings = Settings()
