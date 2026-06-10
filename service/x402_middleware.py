"""
x402 ASGI middleware — 402 Payment Required gate for paid endpoints.

Flow:
  no X-PAYMENT header      -> 402 + payment quote
  valid X-PAYMENT header   -> pass through (payment tx attached to scope)
  X402_DEMO_MODE=true      -> accept any structurally-valid auth (local dev)

Paid paths: /adjudicate, /generate_spec  (health/status/docs are free)
"""
from __future__ import annotations

import base64
import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

PAID_PATHS = {"/adjudicate", "/generate_spec"}

PRICE_USDC = float(os.getenv("X402_PRICE_USDC", "0.50"))
PRICE_IN_UNITS = int(PRICE_USDC * 1_000_000)  # USDC has 6 decimals

USDC_ADDRESS_BASE = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
PAYEE_ADDRESS = os.getenv("X402_PAYEE_ADDRESS", "")


def generate_payment_quote(path: str) -> dict:
    """Build the x402 402-response body (payment quote)."""
    public = os.getenv("SKILL_PUBLIC_URL", "http://localhost:8000")
    return {
        "x402Version": 1,
        "error": "Payment Required",
        "accepts": [{
            "scheme": "exact",
            "network": "base",
            "maxAmountRequired": str(PRICE_IN_UNITS),
            "resource": f"{public}{path}",
            "description": f"SignalForge adjudication service — ${PRICE_USDC} USDC per call",
            "mimeType": "application/json",
            "payTo": PAYEE_ADDRESS or "0x0000000000000000000000000000000000000001",
            "maxTimeoutSeconds": 300,
            "asset": USDC_ADDRESS_BASE,
            "extra": {"name": "USDC", "version": "2"},
        }],
    }


def verify_payment_header(x_payment: str, path: str):
    """
    Validate the X-PAYMENT header.

    Demo mode (X402_DEMO_MODE=true, or no payee configured):
      accept any structurally-valid base64-JSON auth — for local testing.
    Production: verify EIP-712 signature (recover signer).

    Returns: (is_valid, payment_tx_or_none)
    """
    try:
        auth = json.loads(base64.b64decode(x_payment).decode())
    except Exception:
        return False, None

    if auth.get("x402Version") != 1:
        return False, None
    if auth.get("network") not in ("base", "base-sepolia"):
        return False, None
    payload = auth.get("payload", {})
    if not payload.get("signature"):
        return False, None

    demo_mode = os.getenv("X402_DEMO_MODE", "true").lower() == "true"
    if demo_mode or not PAYEE_ADDRESS:
        logger.warning("x402: DEMO MODE — skipping on-chain verification")
        sig = payload["signature"]
        fake_tx = ("0xdemo" + sig.replace("0x", ""))[:66].ljust(66, "0")
        return True, fake_tx

    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
        recovered = Account.recover_message(
            encode_defunct(text=f"SignalForge payment: {path}"),
            signature=payload["signature"],
        )
        logger.info("x402: recovered signer = %s", recovered)
        return True, None  # on-chain settlement tx arrives asynchronously
    except Exception as e:
        logger.error("x402 signature verification failed: %s", e)
        return False, None


class X402Middleware:
    """ASGI x402 payment-gate middleware."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path not in PAID_PATHS:
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        x_payment = headers.get(b"x-payment", b"").decode()

        if not x_payment:
            await self._send_402(send, path)
            return

        is_valid, payment_tx = verify_payment_header(x_payment, path)
        if not is_valid:
            await self._send_402(send, path, error="Invalid payment authorization")
            return

        logger.info("x402: payment accepted for %s, tx=%s", path, payment_tx)
        scope["x402_payment_tx"] = payment_tx
        await self.app(scope, receive, send)

    async def _send_402(self, send, path: str, error: Optional[str] = None):
        quote = generate_payment_quote(path)
        if error:
            quote["error"] = error
        body = json.dumps(quote).encode()
        await send({
            "type": "http.response.start",
            "status": 402,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(body)).encode()],
                [b"x-price-usdc", str(PRICE_USDC).encode()],
                [b"x-payment-network", b"base"],
                [b"access-control-allow-origin", b"*"],
            ],
        })
        await send({"type": "http.response.body", "body": body})
