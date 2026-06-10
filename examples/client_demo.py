"""
APEX full client demo — 8-step lifecycle (BSC Testnet, Chain ID 97).

Demonstrates an external agent paying SignalForge for on-chain adjudication:
  1. Discover SignalForge (ERC-8004 registry)
  2. Negotiate (off-chain HTTP)
  3. create_job (on-chain ERC-8183)
  4. set_budget
  5. approve U token + fund (escrow)   <- P0-4 hardened
  6. trigger execution
  7. fetch verdict
  8. await UMA liveness -> COMPLETED, payment released

All tx hashes are written to outputs/onchain/client_demo_result.json.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ONCHAIN_DIR = Path(__file__).resolve().parent.parent / "outputs" / "onchain"

# P0-4: known ERC-8183 contract constant (do not rely on config attribute)
ERC8183_ADDRESS = "0x3464e64dD53bC093c53050cE5114062765e9F1b6"


def main():
    print("=" * 65)
    print("SignalForge APEX Client Demo — Full 8-Step Lifecycle")
    print("Network: BSC Testnet (Chain ID 97)")
    print("=" * 65)

    try:
        from bnbagent import EVMWalletProvider
    except ImportError:
        print("ERROR: bnbagent not installed. Run: pip install 'bnbagent[server,ipfs]'")
        sys.exit(1)

    wallet_password = os.environ.get("WALLET_PASSWORD")
    if not wallet_password:
        print("ERROR: WALLET_PASSWORD not set in .env")
        sys.exit(1)

    # Step 0: client wallet
    print("\n[Step 0] Initializing client wallet...")
    client_wallet = EVMWalletProvider(
        password=wallet_password,
        private_key=os.environ.get("CLIENT_PRIVATE_KEY")
        or os.environ.get("PRIVATE_KEY"),
    )
    print(f"  Client wallet: {client_wallet.address}")

    # Step 1: discover SignalForge via ERC-8004
    print("\n[Step 1] Discovering SignalForge agent via ERC-8004 registry...")
    from src.bnb.register import get_registration

    reg = get_registration()
    if not reg:
        print("  WARNING: No registration.json. Run: python src/bnb/register.py first")
        agent_id = 1
        provider_address = client_wallet.address
    else:
        agent_id = reg.get("agentId")
        provider_address = reg.get("wallet_address")
        print(f"  Found SignalForge: agentId={agent_id}, provider={provider_address}")
        print(f"  ERC-8004 registry tx: {reg.get('transactionHash')}")

    # P2-7: APEX URL precedence: APEX_URL > APEX_PUBLIC_URL > localhost
    apex_url = (
        os.environ.get("APEX_URL")
        or os.environ.get("APEX_PUBLIC_URL")
        or "http://localhost:8001"
    )
    print(f"  Connecting to APEX: {apex_url}")

    # Step 2: negotiate
    print(f"\n[Step 2] Negotiating price with {apex_url}...")
    import httpx

    adjudication_request = {
        "asset": "ETH",
        "candidate_signal": {
            "name": "cmc_fg_extreme_reversal_demo",
            "source": "cmc_fear_greed",
            "definition": "fg < 20 -> long; fg > 80 -> short",
            "holding_period_days": 5,
        },
        "risk": "balanced",
    }
    try:
        r = httpx.post(
            f"{apex_url}/negotiate",
            json={
                "description": json.dumps(adjudication_request),
                "client": client_wallet.address,
            },
            timeout=30,
        )
        negotiate_resp = r.json()
        service_price_wei = negotiate_resp.get("service_price", "10000000000000000000")
        print(f"  Agreed price: {int(service_price_wei) / 1e18:.2f} U tokens")
    except Exception as e:
        print(f"  WARNING: negotiate failed ({e}). Using default price.")
        service_price_wei = os.environ.get("SERVICE_PRICE", "10000000000000000000")

    # Steps 3-5: on-chain job lifecycle
    print("\n[Steps 3-5] Creating, funding job on BSC Testnet (ERC-8183)...")
    print("  Faucets: BNB https://www.bnbchain.org/en/testnet-faucet")
    print("           U   https://united-coin-u.github.io/u-faucet/")

    create_tx = fund_tx = None
    job_id = None
    try:
        import time
        from bnbagent.erc8183 import ERC8183Client

        client = ERC8183Client(wallet_provider=client_wallet, network="bsc-testnet")

        print("\n  [3/5] Creating job on-chain...")
        # expired_at: 2 days from now (must be >= now + dispute_window + buffer)
        expired_at = int(time.time()) + 172800
        create_result = client.create_job(
            provider=provider_address,
            expired_at=expired_at,
            description=json.dumps(adjudication_request),
        )
        job_id = create_result["jobId"]
        create_tx = create_result["transactionHash"]
        print(f"       jobId={job_id}, tx={create_tx}")
        print(f"       https://testnet.bscscan.com/tx/{create_tx}")

        print("\n  [4/5] Setting budget...")
        client.set_budget(job_id=job_id, amount=int(service_price_wei))

        # P0-4 hardened approve + fund
        print("\n  [5/5] Approving U token + funding escrow...")
        fund_result = client.fund(job_id=job_id, amount=int(service_price_wei))
        fund_tx = fund_result["transactionHash"]
        print(f"       funded, tx={fund_tx}")
        print(f"       https://testnet.bscscan.com/tx/{fund_tx}")

    except Exception as e:
        print(f"\n  NOTE: On-chain steps require testnet tokens. Error: {e}")
        print("  Get faucet tokens (links above) and retry.")
        job_id = job_id or 0

    # Step 6: trigger execution
    print(f"\n[Step 6] Triggering adjudication (POST {apex_url}/job/execute)...")
    try:
        r = httpx.post(f"{apex_url}/job/execute", json={"jobId": job_id}, timeout=120)
        print(f"  Response: {r.status_code}")
    except Exception as e:
        print(f"  NOTE: APEX server not running locally ({e})")

    # Step 7: fetch verdict
    print("\n[Step 7] Fetching verdict...")
    try:
        r = httpx.get(f"{apex_url}/job/{job_id}/response", timeout=30)
        if r.status_code == 200:
            v = r.json()
            print(f"  verdict          : {v.get('verdict')}")
            print(f"  edge_confidence  : {v.get('edge_confidence')}/100")
    except Exception as e:
        print(f"  NOTE: {e}. See outputs/verdicts/ for local verdicts.")

    # Step 8: UMA liveness
    print("\n[Step 8] UMA OOv3 liveness period: 30 minutes on BSC Testnet.")
    print("  After liveness passes without dispute -> COMPLETED, payment released.")
    print("  Track: https://testnet.bscscan.com/address/" + ERC8183_ADDRESS)

    # Persist results
    ONCHAIN_DIR.mkdir(parents=True, exist_ok=True)
    lifecycle = {
        "jobId": job_id,
        "agent_id": str(agent_id),
        "provider_address": provider_address,
        "client_address": client_wallet.address,
        "create_job_tx": create_tx,
        "fund_tx": fund_tx,
        "apex_url": apex_url,
        "bscscan_create": f"https://testnet.bscscan.com/tx/{create_tx}"
        if create_tx
        else None,
        "bscscan_fund": f"https://testnet.bscscan.com/tx/{fund_tx}"
        if fund_tx
        else None,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }
    out = ONCHAIN_DIR / "client_demo_result.json"
    with open(out, "w") as f:
        json.dump(lifecycle, f, indent=2)

    print("\n" + "=" * 65)
    print(f"Demo complete. Results saved to {out}")
    print("=" * 65)


if __name__ == "__main__":
    main()
