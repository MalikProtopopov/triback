"""Shared payment utilities — IP whitelist, receipt builder."""

from __future__ import annotations

import secrets
from decimal import Decimal
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address, ip_network
from typing import Any

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

LAPSE_THRESHOLD_DAYS = 60

_YOOKASSA_NETWORKS: list[IPv4Network | IPv6Network] = []
_MONETA_RECEIPT_NETWORKS: list[IPv4Network | IPv6Network] = []


def get_yookassa_networks() -> list[IPv4Network | IPv6Network]:
    global _YOOKASSA_NETWORKS  # noqa: PLW0603
    if not _YOOKASSA_NETWORKS:
        raw = getattr(settings, "YOOKASSA_IP_WHITELIST", "")
        for cidr in raw.split(","):
            cidr = cidr.strip()
            if cidr:
                _YOOKASSA_NETWORKS.append(ip_network(cidr, strict=False))
    return _YOOKASSA_NETWORKS


def get_moneta_receipt_networks() -> list[IPv4Network | IPv6Network]:
    global _MONETA_RECEIPT_NETWORKS  # noqa: PLW0603
    if not _MONETA_RECEIPT_NETWORKS:
        raw = getattr(settings, "MONETA_RECEIPT_IP_ALLOWLIST", "")
        for cidr in raw.split(","):
            cidr = cidr.strip()
            if cidr:
                _MONETA_RECEIPT_NETWORKS.append(ip_network(cidr, strict=False))
    return _MONETA_RECEIPT_NETWORKS


def is_moneta_receipt_ip_allowed(client_ip: str) -> bool:
    if not client_ip:
        return False
    networks = get_moneta_receipt_networks()
    if not networks:
        return False
    try:
        addr: IPv4Address | IPv6Address = ip_address(client_ip)
    except ValueError:
        return False
    return any(addr in net for net in networks)


def is_moneta_receipt_webhook_authorized(
    *,
    client_ip: str,
    header_secret: str | None,
) -> bool:
    """True if the Moneta receipt callback is allowed (secret, IP allowlist, or DEBUG)."""
    expected = (settings.MONETA_RECEIPT_WEBHOOK_SECRET or "").strip()
    if expected:
        got = (header_secret or "").strip()
        return bool(got) and secrets.compare_digest(got, expected)

    if is_moneta_receipt_ip_allowed(client_ip):
        return True

    if settings.DEBUG:
        logger.warning(
            "moneta_receipt_webhook_unauthenticated_debug",
            client_ip=client_ip,
            hint="Set MONETA_RECEIPT_WEBHOOK_SECRET or MONETA_RECEIPT_IP_ALLOWLIST in production",
        )
        return True

    logger.error(
        "moneta_receipt_webhook_rejected_no_auth",
        client_ip=client_ip,
    )
    return False


def is_ip_allowed(client_ip: str) -> bool:
    if not client_ip:
        return False
    networks = get_yookassa_networks()
    if not networks:
        if settings.DEBUG:
            logger.warning("yookassa_ip_whitelist_empty_debug_mode")
            return True
        logger.error("yookassa_ip_whitelist_empty_production")
        return False
    try:
        addr: IPv4Address | IPv6Address = ip_address(client_ip)
    except ValueError:
        return False
    return any(addr in net for net in networks)


def build_receipt(
    email: str, description: str, amount: Decimal
) -> dict[str, Any]:
    """Build a 54-FZ compliant receipt payload for YooKassa."""
    return {
        "customer": {"email": email},
        "items": [
            {
                "description": description[:128],
                "quantity": "1",
                "amount": {"value": str(amount), "currency": "RUB"},
                "vat_code": 1,
                "payment_subject": "service",
                "payment_mode": "full_payment",
            }
        ],
    }
