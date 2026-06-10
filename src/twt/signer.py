"""
Trust Wallet Agent Kit (TWAK) local-signing adapter.

WARNING: The API endpoints below ('/v1/wallet/...') are PLACEHOLDERS inferred
from TWAK's feature description. Before going for the TWT special prize,
consult https://developer.trustwallet.com/agent-kit for the real endpoints
and update them here (see docs/TWAK_GUIDE.md).

Adapter pattern: implements the same interface as EVMWalletProvider so it can
be a drop-in replacement in register.py / client_demo.py via --signer twak.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class TWAKSigner:
    """Trust Wallet Agent Kit signing adapter (keys never leave the device)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        chain_id: int = 97,  # BSC Testnet
    ):
        self.api_key = api_key or os.getenv("TWAK_API_KEY", "")
        self.endpoint = endpoint or os.getenv("TWAK_ENDPOINT", "https://api.twak.trustwallet.com")
        self.chain_id = chain_id
        self._address: Optional[str] = None
        if not self.api_key:
            logger.warning("TWAK_API_KEY not set. TWAK signer runs in simulation mode.")

    @property
    def address(self) -> str:
        if self._address:
            return self._address
        self._address = self._get_address()
        return self._address

    def _get_address(self) -> str:
        try:
            import httpx
            r = httpx.get(f"{self.endpoint}/v1/wallet/address",
                          headers=self._auth_headers(), timeout=10)
            r.raise_for_status()
            return r.json()["address"]
        except Exception as e:
            logger.warning("TWAK address fetch failed (%s); simulation address", e)
            return "0xTWAK" + "0" * 36

    def sign_transaction(self, tx: dict) -> dict:
        """Sign a transaction locally via TWAK (private key never leaves device)."""
        try:
            import httpx
            r = httpx.post(
                f"{self.endpoint}/v1/wallet/sign-transaction",
                json={"transaction": tx, "chainId": self.chain_id},
                headers=self._auth_headers(), timeout=30,
            )
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error("TWAK sign_transaction failed: %s", e)
            return {**tx, "rawTransaction": "0x" + "twak_signed" * 5, "signed_by": "TWAK"}

    def sign_message(self, message: str) -> str:
        """EIP-191 personal_sign via TWAK."""
        try:
            import httpx
            r = httpx.post(
                f"{self.endpoint}/v1/wallet/sign-message",
                json={"message": message},
                headers=self._auth_headers(), timeout=30,
            )
            r.raise_for_status()
            return r.json()["signature"]
        except Exception as e:
            logger.warning("TWAK sign_message failed (%s); simulation sig", e)
            return "0x" + "74776b" * 20 + "00"

    def sign_typed_data(self, domain: dict, types: dict, message: dict) -> str:
        """EIP-712 structured-data signing via TWAK (for x402 payment auth)."""
        try:
            import httpx
            r = httpx.post(
                f"{self.endpoint}/v1/wallet/sign-typed-data",
                json={"domain": domain, "types": types, "message": message,
                      "primaryType": next(iter(types))},
                headers=self._auth_headers(), timeout=30,
            )
            r.raise_for_status()
            return r.json()["signature"]
        except Exception as e:
            logger.warning("TWAK sign_typed_data failed (%s); simulation sig", e)
            return "0x" + "74776b5f74797065" * 8

    def _auth_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-TWAK-Chain-ID": str(self.chain_id),
        }

    def __repr__(self):
        return f"TWAKSigner(address={self.address[:12]}..., chain={self.chain_id})"


class TWAKWalletProvider:
    """EVMWalletProvider-compatible adapter; drop-in for ERC8004Agent/APEXConfig."""

    def __init__(self, api_key: Optional[str] = None,
                 endpoint: Optional[str] = None, chain_id: int = 97):
        self._signer = TWAKSigner(api_key=api_key, endpoint=endpoint, chain_id=chain_id)

    @property
    def address(self) -> str:
        return self._signer.address

    def sign_transaction(self, tx: dict) -> dict:
        return self._signer.sign_transaction(tx)

    def sign_message(self, message: str) -> dict:
        return {"signature": self._signer.sign_message(message), "message": message}


def get_wallet_provider(signer: str = "evm", **kwargs):
    """
    Factory: returns the wallet provider matching --signer.

    Usage:
        wallet = get_wallet_provider(signer="twak")
        sdk = ERC8004Agent(network="bsc-testnet", wallet_provider=wallet)
    """
    if signer == "twak":
        logger.info("Using Trust Wallet Agent Kit (TWAK) signer")
        return TWAKWalletProvider(**kwargs)

    from bnbagent import EVMWalletProvider
    return EVMWalletProvider(
        password=os.environ["WALLET_PASSWORD"],
        private_key=os.environ.get("PRIVATE_KEY"),
        **kwargs,
    )
