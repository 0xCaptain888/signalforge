"""
ERC-8004 on-chain identity registration (BSC Testnet, gas-free via MegaFuel).

Registers SignalForge as a discoverable on-chain agent:
- unique agentId (ERC-721 token)
- on-chain profile: name / description / A2A endpoint
Result is persisted to outputs/onchain/registration.json (agentId + tx hash).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ONCHAIN_DIR = Path(__file__).resolve().parent.parent.parent / "outputs" / "onchain"
REGISTRATION_FILE = ONCHAIN_DIR / "registration.json"


def register_signalforge(
    skill_card_url: str = "",
    network: str = "bsc-testnet",
    force: bool = False,
) -> dict:
    """
    Register SignalForge's ERC-8004 identity on BSC Testnet.

    Args:
        skill_card_url: public A2A skill-card URL
        network: only "bsc-testnet" is currently supported by the SDK
        force: re-register even if registration.json already exists
    """
    ONCHAIN_DIR.mkdir(parents=True, exist_ok=True)

    if REGISTRATION_FILE.exists() and not force:
        with open(REGISTRATION_FILE) as f:
            existing = json.load(f)
        print(f"[ERC-8004] Already registered: agentId={existing.get('agentId')}")
        print(f"           tx={existing.get('transactionHash')}")
        return existing

    try:
        from bnbagent import ERC8004Agent, AgentEndpoint, EVMWalletProvider
    except ImportError:
        raise ImportError("bnbagent not installed. Run: pip install 'bnbagent[server,ipfs]'")

    wallet_password = os.environ.get("WALLET_PASSWORD")
    if not wallet_password:
        raise ValueError("WALLET_PASSWORD environment variable not set")

    print(f"[ERC-8004] Initializing wallet on {network}...")
    wallet = EVMWalletProvider(
        password=wallet_password,
        private_key=os.environ.get("PRIVATE_KEY"),  # only needed on first run
    )
    print(f"[ERC-8004] Wallet address: {wallet.address}")

    sdk = ERC8004Agent(network=network, wallet_provider=wallet)

    endpoints = []
    if skill_card_url:
        endpoints.append(AgentEndpoint(name="A2A", endpoint=skill_card_url, version="0.3.0"))
    else:
        endpoints.append(AgentEndpoint(
            name="repo",
            endpoint="https://github.com/0xCaptain888/signalforge",
            version="2.1.0",
        ))

    agent_uri = sdk.generate_agent_uri(
        name="signalforge-adjudicator",
        description=(
            "Signal Edge Adjudicator — validates any trading signal for real alpha "
            "vs overfit/leakage. Powered by CMC proprietary Fear & Greed index and "
            "Lopez de Prado's Deflated Sharpe Ratio."
        ),
        endpoints=endpoints,
    )

    print("[ERC-8004] Registering on-chain (gas-free on testnet)...")
    result = sdk.register_agent(agent_uri=agent_uri)

    agent_id = result.get("agentId")
    tx_hash = result.get("transactionHash")
    print(f"[ERC-8004] Registered! agentId={agent_id}")
    print(f"[ERC-8004]   tx={tx_hash}")
    print(f"[ERC-8004]   BscScan: https://testnet.bscscan.com/tx/{tx_hash}")

    registration_data = {
        "agentId": agent_id,
        "transactionHash": tx_hash,
        "network": network,
        "wallet_address": wallet.address,
        "agent_uri": agent_uri,
        "skill_card_url": skill_card_url,
        "bscscan_url": f"https://testnet.bscscan.com/tx/{tx_hash}",
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(REGISTRATION_FILE, "w") as f:
        json.dump(registration_data, f, indent=2)
    print(f"[ERC-8004]   Saved to {REGISTRATION_FILE}")
    return registration_data


def get_registration() -> dict:
    if not REGISTRATION_FILE.exists():
        return {}
    with open(REGISTRATION_FILE) as f:
        return json.load(f)


def discover_agents(network: str = "bsc-testnet") -> list:
    """List all registered ERC-8004 agents on BSC Testnet (discovery demo)."""
    try:
        from bnbagent import ERC8004Agent, EVMWalletProvider
    except ImportError:
        return []
    wallet = EVMWalletProvider(password=os.environ.get("WALLET_PASSWORD", "demo"))
    sdk = ERC8004Agent(network=network, wallet_provider=wallet)
    return sdk.get_all_agents().get("items", [])


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else os.getenv("SKILL_PUBLIC_URL", "")
    if url and not url.endswith("skill-card.json"):
        url = url.rstrip("/") + "/.well-known/skill-card.json"
    register_signalforge(skill_card_url=url)
