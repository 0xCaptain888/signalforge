"""
CMC x402 pay-per-call data client — COMPLETE FINAL VERSION v2.1.0
(this file is authoritative; ignore earlier draft versions).

Implements:
  - Standard x402 flow: GET -> 402 quote -> EIP-712 offline auth -> retry -> 200
  - EIP-3009 transferWithAuthorization (USDC-on-Base standard) signing
  - EIP-712 simplified fallback when EIP-3009 signing is unavailable
  - Payment-tx capture + provenance recording

Endpoints:
  REST:  https://mcp.coinmarketcap.com/x402/v3/...   ($0.01 USDC / call, Base)
  MCP:   https://mcp.coinmarketcap.com/x402/mcp
"""
from __future__ import annotations

import base64
import json
import logging
import os
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


class CMCx402Client:
    """CMC x402 pay-per-request data client."""

    BASE_URL = "https://mcp.coinmarketcap.com/x402"

    USDC_ADDRESS = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"  # USDC on Base
    BASE_CHAIN_ID = 8453
    BASE_SEPOLIA_CHAIN_ID = 84532

    def __init__(self, private_key: Optional[str] = None, network: str = "base"):
        self._private_key = private_key or os.getenv("X402_PRIVATE_KEY", "")
        self._network = network
        self._chain_id = self.BASE_CHAIN_ID if network == "base" else self.BASE_SEPOLIA_CHAIN_ID
        self._client = httpx.Client(timeout=30)
        self.last_payment_tx: Optional[str] = None
        self._acct = None

        if self._private_key:
            try:
                from eth_account import Account
                self._acct = Account.from_key(self._private_key)
            except ImportError:
                logger.warning("eth-account not installed. x402 signing unavailable.")

    @property
    def address(self) -> Optional[str]:
        return self._acct.address if self._acct else None

    # -- Public query helpers --------------------------------------------------
    def get_fear_greed_latest(self) -> dict:
        return self.get("/v3/fear-and-greed/latest", {})

    def get_fear_greed_historical(self, limit: int = 30) -> dict:
        return self.get("/v3/fear-and-greed/historical", {"limit": limit})

    def get_quotes_latest(self, symbols: str) -> dict:
        return self.get("/v3/cryptocurrency/quotes/latest", {"symbol": symbols})

    def get_global_metrics_latest(self) -> dict:
        return self.get("/v1/global-metrics/quotes/latest", {})

    def get(self, path: str, params: dict) -> dict:
        """x402 standard GET: first request -> 402 -> sign -> retry -> 200."""
        url = f"{self.BASE_URL}{path}"
        r = self._client.get(url, params=params)

        if r.status_code == 200:
            return r.json()
        if r.status_code != 402:
            r.raise_for_status()

        try:
            quote = r.json()
        except Exception:
            raise RuntimeError(f"x402: 402 response is not valid JSON: {r.text[:200]}")

        if not self._acct:
            raise RuntimeError(
                "x402 payment required but X402_PRIVATE_KEY is not set. "
                "Set it in .env to enable pay-per-request CMC data."
            )

        auth_header = self._sign_payment(quote)
        r2 = self._client.get(url, params=params, headers={"X-PAYMENT": auth_header})
        r2.raise_for_status()

        for header_name in ("X-Payment-Tx", "X-PAYMENT-TX", "x-payment-tx"):
            tx = r2.headers.get(header_name)
            if tx:
                self.last_payment_tx = tx
                logger.info("x402 payment settled: tx=%s", tx)
                self._record_provenance(path, tx)
                break

        return r2.json()

    # -- Signing ----------------------------------------------------------------
    def _sign_payment(self, quote: dict) -> str:
        """
        Full x402 EIP-712 signing.
        Tries EIP-3009 transferWithAuthorization (USDC-on-Base standard) first,
        falls back to a simplified EIP-712 personal-sign envelope.
        """
        accepts = quote.get("accepts", [{}])
        if not accepts:
            raise ValueError("x402 quote has no 'accepts' array")
        pay_spec = accepts[0]

        scheme = pay_spec.get("scheme", "exact")
        payto = pay_spec.get("payTo", "")
        amount = int(pay_spec.get("maxAmountRequired", "10000"))   # USDC 6-decimals
        timeout_sec = int(pay_spec.get("maxTimeoutSeconds", 300))
        valid_before = int(time.time()) + timeout_sec
        asset = pay_spec.get("asset", self.USDC_ADDRESS)
        extra = pay_spec.get("extra", {})

        try:
            nonce = os.urandom(32)
            domain = {
                "name": extra.get("name", "USD Coin"),
                "version": extra.get("version", "2"),
                "chainId": self._chain_id,
                "verifyingContract": asset,
            }
            types = {
                "TransferWithAuthorization": [
                    {"name": "from",        "type": "address"},
                    {"name": "to",          "type": "address"},
                    {"name": "value",       "type": "uint256"},
                    {"name": "validAfter",  "type": "uint256"},
                    {"name": "validBefore", "type": "uint256"},
                    {"name": "nonce",       "type": "bytes32"},
                ],
            }
            message_data = {
                "from": self._acct.address,
                "to": payto,
                "value": amount,
                "validAfter": 0,
                "validBefore": valid_before,
                "nonce": "0x" + nonce.hex(),
            }
            signed = self._acct.sign_typed_data(
                domain_data=domain,
                message_types=types,
                message_data=message_data,
            )
            auth_payload = {
                "x402Version": 1,
                "scheme": scheme,
                "network": self._network,
                "payload": {
                    "signature": signed.signature.hex(),
                    "authorization": {
                        "from": self._acct.address,
                        "to": payto,
                        "value": str(amount),
                        "validAfter": "0",
                        "validBefore": str(valid_before),
                        "nonce": "0x" + nonce.hex(),
                    },
                },
            }
            return base64.b64encode(
                json.dumps(auth_payload, separators=(",", ":")).encode()
            ).decode()
        except Exception as e:
            logger.warning("EIP-3009 signing failed (%s), trying EIP-712 fallback", e)
            return self._sign_payment_fallback(pay_spec, valid_before)

    def _sign_payment_fallback(self, pay_spec: dict, valid_before: int) -> str:
        """Simplified EIP-712 fallback (personal_sign over a canonical envelope)."""
        from eth_account.messages import encode_defunct

        amount = int(pay_spec.get("maxAmountRequired", "10000"))
        payto = pay_spec.get("payTo", "")
        nonce = os.urandom(32)

        message_data = {
            "from": self._acct.address,
            "to": payto,
            "amount": amount,
            "validBefore": valid_before,
            "nonce": "0x" + nonce.hex(),
        }
        combined = f"x402Payment:1:{self._chain_id}:" + json.dumps(message_data, sort_keys=True)
        signed = self._acct.sign_message(encode_defunct(text=combined))

        auth_payload = {
            "x402Version": 1,
            "scheme": "exact",
            "network": self._network,
            "payload": {
                "signature": signed.signature.hex(),
                "authorization": {k: str(v) for k, v in message_data.items()},
            },
        }
        return base64.b64encode(json.dumps(auth_payload).encode()).decode()

    def _record_provenance(self, path: str, tx: str):
        try:
            from src.cmc.provenance import record
            record(
                channel="x402",
                endpoint=f"{self.BASE_URL}{path}",
                description=f"x402 pay-per-call: {path}",
                payment_tx=tx,
            )
        except ImportError:
            pass

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
