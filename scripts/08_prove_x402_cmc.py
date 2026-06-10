#!/usr/bin/env python3
"""
08_prove_x402_cmc.py — one-click CMC x402 on-chain settlement evidence.

Prereqs: X402_PRIVATE_KEY in .env; wallet holds >= $0.02 USDC on Base mainnet.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def check_usdc_balance(private_key: str) -> float:
    try:
        from web3 import Web3
        from eth_account import Account
        w3 = Web3(Web3.HTTPProvider("https://mainnet.base.org"))
        USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
        ABI = [{"inputs": [{"name": "account", "type": "address"}],
                "name": "balanceOf", "outputs": [{"type": "uint256"}],
                "stateMutability": "view", "type": "function"}]
        addr = Account.from_key(private_key).address
        c = w3.eth.contract(address=Web3.to_checksum_address(USDC), abi=ABI)
        return c.functions.balanceOf(addr).call() / 1_000_000
    except Exception as e:
        print(f"  WARNING: balance check failed ({e}). Proceeding anyway.")
        return -1.0


def main():
    print("=" * 60)
    print("CMC x402 Proof Script — CMC Special Prize Evidence")
    print("=" * 60)
    key = os.getenv("X402_PRIVATE_KEY")
    if not key:
        print("\nERROR: X402_PRIVATE_KEY not set in .env")
        print("  Fund the wallet with >= $0.02 USDC on Base: https://bridge.base.org")
        sys.exit(1)

    print("\n[1/3] Checking USDC balance on Base mainnet...")
    bal = check_usdc_balance(key)
    if 0 <= bal < 0.02:
        print(f"  ERROR: balance too low (${bal:.4f}). Need >= $0.02.")
        sys.exit(1)
    if bal >= 0:
        print(f"  Balance: ${bal:.4f} USDC")

    print("\n[2/3] Calling CMC x402 /v3/fear-and-greed/latest ...")
    from src.cmc.x402_client import CMCx402Client
    from src.cmc.provenance import record

    client = CMCx402Client(private_key=key, network="base")
    try:
        data = client.get_fear_greed_latest()
        d = data.get("data", {})
        fg, klass = d.get("value", "N/A"), d.get("value_classification", "N/A")
        tx = client.last_payment_tx
        print(f"  Fear & Greed: {fg} ({klass})")
        if tx:
            print(f"  Payment TX  : {tx}")
            print(f"  BaseScan    : https://basescan.org/tx/{tx}")
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    print("\n[3/3] Recording to outputs/cmc_provenance.json ...")
    record(channel="x402",
           endpoint="https://mcp.coinmarketcap.com/x402/v3/fear-and-greed/latest",
           description="Real-time F&G via x402 — CMC special prize evidence",
           payment_tx=tx,
           response_summary=f"FG={fg}, class={klass}")
    print(f"  Recorded: channel=x402, tx={tx}")
    print("\n" + "=" * 60)
    print("x402 evidence complete!")
    print(f"  README evidence row: | x402 Base tx | https://basescan.org/tx/{tx or 'PENDING'} |")
    print("=" * 60)


if __name__ == "__main__":
    main()
