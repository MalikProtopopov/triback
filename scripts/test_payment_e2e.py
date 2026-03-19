#!/usr/bin/env python3
"""E2E smoke test for Moneta payment integration.

Tests against a **deployed** server over HTTP.  Supports three modes:

  --mode manual      Create payment, print URL, wait for you to pay with test card.
  --mode simulate    Create payment, then simulate Moneta webhook locally.
  --mode check-only  Just verify Moneta API connectivity (create + status check).

Examples:
  python scripts/test_payment_e2e.py --base-url https://trihoback.mediann.dev \\
      --email doctor@test.com --password TestPass123! --mode manual

  python scripts/test_payment_e2e.py --base-url https://trihoback.mediann.dev \\
      --email doctor@test.com --password TestPass123! --mode simulate \\
      --webhook-secret TrIcHo2026\\$ecReT --mnt-id 77892567

Test cards (non-3DS): 4000000000000002, any exp, any CVV
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import sys
import time
from uuid import uuid4

import httpx


def _md5(*parts: str) -> str:
    return hashlib.md5("".join(parts).encode("utf-8")).hexdigest()


def _log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def _ok(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] ✅ {msg}")


def _fail(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] ❌ {msg}")


# ------------------------------------------------------------------
# Core steps
# ------------------------------------------------------------------


async def authenticate(
    client: httpx.AsyncClient, base: str, email: str, password: str,
) -> tuple[str, str]:
    """Login and return (access_token, role)."""
    resp = await client.post(
        f"{base}/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    if resp.status_code != 200:
        _fail(f"Login failed ({resp.status_code}): {resp.text}")
        sys.exit(1)
    data = resp.json()
    _ok(f"Authenticated as {email} (role={data['role']})")
    return data["access_token"], data["role"]


async def get_status(
    client: httpx.AsyncClient, base: str, token: str,
) -> dict:
    resp = await client.get(
        f"{base}/api/v1/subscriptions/status",
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code != 200:
        _fail(f"Status request failed ({resp.status_code}): {resp.text}")
        sys.exit(1)
    return resp.json()


async def create_payment(
    client: httpx.AsyncClient, base: str, token: str, plan_id: str,
) -> dict:
    resp = await client.post(
        f"{base}/api/v1/subscriptions/pay",
        json={"plan_id": plan_id, "idempotency_key": f"e2e-{uuid4().hex[:12]}"},
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code not in (200, 201):
        _fail(f"Payment creation failed ({resp.status_code}): {resp.text}")
        sys.exit(1)
    return resp.json()


async def poll_status(
    client: httpx.AsyncClient, base: str, token: str,
    *, timeout: int = 120, interval: int = 5,
) -> dict:
    _log(f"Polling subscription status every {interval}s (timeout {timeout}s)…")
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = await get_status(client, base, token)
        if status.get("has_subscription"):
            return status
        next_action = status.get("next_action", "")
        _log(f"  status: has_subscription=False, next_action={next_action}")
        await asyncio.sleep(interval)
    return status


async def simulate_webhook(
    client: httpx.AsyncClient,
    base: str,
    payment_id: str,
    operation_id: str,
    amount: str,
    mnt_id: str,
    webhook_secret: str,
) -> bool:
    sig = _md5(mnt_id, payment_id, operation_id, amount, "RUB", "", "", webhook_secret)
    resp = await client.post(
        f"{base}/api/v1/webhooks/moneta",
        data={
            "MNT_ID": mnt_id,
            "MNT_TRANSACTION_ID": payment_id,
            "MNT_OPERATION_ID": operation_id,
            "MNT_AMOUNT": amount,
            "MNT_CURRENCY_CODE": "RUB",
            "MNT_SUBSCRIBER_ID": "",
            "MNT_TEST_MODE": "",
            "MNT_SIGNATURE": sig,
        },
    )
    if resp.text.strip() == "SUCCESS":
        _ok(f"Webhook returned SUCCESS for payment {payment_id}")
        return True
    _fail(f"Webhook returned: {resp.text}")
    return False


async def check_moneta_connectivity(
    base_service_url: str, username: str, password: str, payee: str,
) -> bool:
    """Create a 1-ruble invoice and check its status — verifies API connectivity."""
    txn_id = f"e2e-check-{uuid4().hex[:12]}"
    envelope = {
        "Envelope": {
            "Header": {
                "Security": {
                    "UsernameToken": {"Username": username, "Password": password}
                }
            },
            "Body": {
                "InvoiceRequest": {
                    "payee": payee,
                    "amount": 1.0,
                    "clientTransaction": txn_id,
                    "description": "E2E connectivity check",
                }
            },
        }
    }

    async with httpx.AsyncClient(timeout=15.0) as api:
        _log(f"Creating test invoice on {base_service_url}…")
        resp = await api.post(
            base_service_url,
            json=envelope,
            headers={"Content-Type": "application/json;charset=UTF-8"},
        )
        body = resp.json().get("Envelope", {}).get("Body", {})
        if "fault" in body:
            fault = body["fault"]
            _fail(f"InvoiceRequest fault: {fault.get('faultstring', fault)}")
            return False

        inv = body.get("InvoiceResponse", {})
        op_id = inv.get("transaction")
        status = inv.get("status")
        _ok(f"Invoice created: transaction={op_id}, status={status}")

        _log(f"Querying operation {op_id} status…")
        status_envelope = {
            "Envelope": {
                "Header": {
                    "Security": {
                        "UsernameToken": {"Username": username, "Password": password}
                    }
                },
                "Body": {"GetOperationDetailsByIdRequest": op_id},
            }
        }
        resp2 = await api.post(
            base_service_url,
            json=status_envelope,
            headers={"Content-Type": "application/json;charset=UTF-8"},
        )
        body2 = resp2.json().get("Envelope", {}).get("Body", {})
        if "fault" in body2:
            _fail(f"GetOperationDetailsById fault: {body2['fault']}")
            return False

        op = body2.get("GetOperationDetailsByIdResponse", {}).get("operation", {})
        attrs = {a["key"]: a["value"] for a in op.get("attribute", [])}
        _ok(f"Operation {op.get('id')}: statusid={attrs.get('statusid')}")
        return True


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------


async def main(args: argparse.Namespace) -> None:
    print("=" * 60)
    print("  Moneta E2E Payment Smoke Test")
    print("=" * 60)
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:

        # --- Mode: check-only ---
        if args.mode == "check-only":
            if not all([args.moneta_service_url, args.moneta_username, args.moneta_password, args.moneta_payee]):
                _fail("check-only mode requires --moneta-service-url, --moneta-username, "
                      "--moneta-password, --moneta-payee")
                sys.exit(1)
            ok = await check_moneta_connectivity(
                args.moneta_service_url, args.moneta_username,
                args.moneta_password, args.moneta_payee,
            )
            print()
            if ok:
                _ok("Moneta API connectivity: PASS")
            else:
                _fail("Moneta API connectivity: FAIL")
                sys.exit(1)
            return

        # --- Authenticate ---
        if not all([args.email, args.password]):
            _fail("--email and --password are required for manual/simulate modes")
            sys.exit(1)

        token, role = await authenticate(client, args.base_url, args.email, args.password)
        if role != "doctor":
            _fail(f"Expected role 'doctor', got '{role}'")
            sys.exit(1)

        # --- Check current status ---
        status = await get_status(client, args.base_url, token)
        _log(f"Current: has_subscription={status.get('has_subscription')}, "
             f"entry_fee_required={status.get('entry_fee_required')}, "
             f"next_action={status.get('next_action')}")

        plans = status.get("available_plans", [])
        if not plans:
            _fail("No available plans — cannot test payment")
            sys.exit(1)

        plan = plans[0]
        plan_id = plan["id"]
        _log(f"Using plan: {plan['name']} ({plan['price']} RUB, {plan['duration_months']}mo)")

        # --- Create payment ---
        pay = await create_payment(client, args.base_url, token, plan_id)
        payment_id = pay["payment_id"]
        payment_url = pay["payment_url"]
        amount = pay["amount"]

        _ok(f"Payment created: id={payment_id}, amount={amount}")
        _log(f"Payment URL: {payment_url}")
        print()

        # --- Mode: manual ---
        if args.mode == "manual":
            print("╔══════════════════════════════════════════════════════╗")
            print("║  Open the URL above in a browser and pay with:     ║")
            print("║  Card: 4000000000000002  Exp: any  CVV: any        ║")
            print("╚══════════════════════════════════════════════════════╝")
            print()

            final = await poll_status(client, args.base_url, token)
            if final.get("has_subscription"):
                _ok("Subscription activated!")
                sub = final.get("current_subscription", {})
                _log(f"  plan: {sub.get('plan', {}).get('name')}")
                _log(f"  starts_at: {sub.get('starts_at')}")
                _log(f"  ends_at: {sub.get('ends_at')}")
                _log(f"  days_remaining: {sub.get('days_remaining')}")
            else:
                _fail("Subscription NOT activated within timeout")
                sys.exit(1)

        # --- Mode: simulate ---
        elif args.mode == "simulate":
            if not all([args.webhook_secret, args.mnt_id]):
                _fail("simulate mode requires --webhook-secret and --mnt-id")
                sys.exit(1)

            fake_op_id = str(900000 + int(uuid4().int % 99999))
            amount_str = f"{amount:.2f}"

            ok = await simulate_webhook(
                client, args.base_url,
                payment_id=payment_id,
                operation_id=fake_op_id,
                amount=amount_str,
                mnt_id=args.mnt_id,
                webhook_secret=args.webhook_secret,
            )
            if not ok:
                sys.exit(1)

            await asyncio.sleep(1)
            final = await get_status(client, args.base_url, token)
            if final.get("has_subscription"):
                _ok("Subscription activated via simulated webhook!")
            else:
                _fail("Subscription NOT activated after webhook simulation")
                sys.exit(1)

    print()
    _ok("All checks passed.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Moneta payment E2E smoke test")
    p.add_argument("--base-url", required=True, help="Server base URL (e.g. https://trihoback.mediann.dev)")
    p.add_argument("--email", help="Doctor account email")
    p.add_argument("--password", help="Doctor account password")
    p.add_argument("--mode", choices=["manual", "simulate", "check-only"], default="manual")
    p.add_argument("--webhook-secret", help="MONETA_WEBHOOK_SECRET (for simulate mode)")
    p.add_argument("--mnt-id", help="MONETA_MNT_ID (for simulate mode)")
    p.add_argument("--moneta-service-url", default="https://service.moneta.ru/services")
    p.add_argument("--moneta-username", help="For check-only mode")
    p.add_argument("--moneta-password", help="For check-only mode")
    p.add_argument("--moneta-payee", help="For check-only mode")
    return p.parse_args()


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
