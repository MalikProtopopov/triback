"""Application configuration via Pydantic Settings."""

import json
from typing import Annotated, Any

from pydantic import BeforeValidator, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_allowed_hosts(value: Any) -> list[str]:
    """Parse ALLOWED_HOSTS from env: JSON array or comma-separated string."""
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
    ALLOWED_HOSTS: Annotated[list[str], BeforeValidator(_parse_allowed_hosts)] = ["*"]

    # JWT (RS256)
    JWT_PRIVATE_KEY_PATH: str = "keys/private.pem"
    JWT_PUBLIC_KEY_PATH: str = "keys/public.pem"
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

    # Payment provider selection
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

    # Moneta — redirect URLs for buyer
    MONETA_SUCCESS_URL: str = ""
    MONETA_FAIL_URL: str = ""
    MONETA_INPROGRESS_URL: str = ""
    MONETA_RETURN_URL: str = ""

    # Moneta — payment form version (v3 supports SBP, SberPay)
    MONETA_FORM_VERSION: str = "v3"

    # Legacy YooKassa (used when PAYMENT_PROVIDER=yookassa)
    YOOKASSA_SHOP_ID: str = ""
    YOOKASSA_SECRET_KEY: str = ""
    YOOKASSA_API_URL: str = "https://api.yookassa.ru/v3"
    YOOKASSA_RETURN_URL: str = "https://trichology.ru/payment/result"
    YOOKASSA_IP_WHITELIST: str = "185.71.76.0/27,185.71.77.0/27,77.75.153.0/25,77.75.156.11/32,77.75.156.35/32"
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
    TELEGRAM_WEBHOOK_SECRET: str = ""

    # Frontend
    FRONTEND_URL: str = "https://trichology.ru"
    ADMIN_FRONTEND_URL: str = ""  # URL админки; если пусто — письма staff идут на FRONTEND_URL

    # Auth cookies (domain for cross-subdomain sharing, e.g. .trichologia.mediann.dev)
    COOKIE_DOMAIN: str | None = None


settings = Settings()
