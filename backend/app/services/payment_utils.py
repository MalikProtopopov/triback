"""Shared payment utilities — IP whitelist, receipt builder."""

from __future__ import annotations

from decimal import Decimal
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network, ip_address, ip_network
from typing import Any

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

LAPSE_THRESHOLD_DAYS = 60

_YOOKASSA_NETWORKS: list[IPv4Network | IPv6Network] = []


def get_yookassa_networks() -> list[IPv4Network | IPv6Network]:
    global _YOOKASSA_NETWORKS  # noqa: PLW0603
    if not _YOOKASSA_NETWORKS:
        raw = getattr(settings, "YOOKASSA_IP_WHITELIST", "")
        for cidr in raw.split(","):
            cidr = cidr.strip()
            if cidr:
                _YOOKASSA_NETWORKS.append(ip_network(cidr, strict=False))
    return _YOOKASSA_NETWORKS


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
