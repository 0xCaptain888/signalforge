#!/usr/bin/env python3
"""check_env.py — one-click pre-development configuration check."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

results = {}
print("=" * 60)
print("SignalForge v2.1 — Environment Check")
print("=" * 60)

# CMC
key = os.getenv("CMC_API_KEY", "")
results["CMC_API_KEY"] = "OK" if len(key) > 20 else "MISSING"
print(f"  CMC_API_KEY: {results['CMC_API_KEY']}")

# Base wallet
x4 = os.getenv("X402_PRIVATE_KEY", "")
if x4.startswith("0x") and len(x4) == 66:
    try:
        from eth_account import Account
        addr = Account.from_key(x4).address
        print(f"  X402 wallet: {addr} OK")
        results["X402_PRIVATE_KEY"] = "OK"
    except Exception as e:
        print(f"  X402 wallet: INVALID ({e})")
        results["X402_PRIVATE_KEY"] = "FAIL"
else:
    print("  X402_PRIVATE_KEY: MISSING or wrong format (need 0x + 64 hex)")
    results["X402_PRIVATE_KEY"] = "MISSING"

# BSC wallet
pwd = os.getenv("WALLET_PASSWORD", "")
results["WALLET_PASSWORD"] = "OK" if len(pwd) >= 8 else "MISSING"
print(f"  WALLET_PASSWORD: {results['WALLET_PASSWORD']}")

# Pinata
jwt = os.getenv("STORAGE_API_KEY", "")
results["STORAGE_API_KEY"] = "OK" if jwt.startswith("eyJ") else "MISSING"
print(f"  STORAGE_API_KEY (Pinata): {results['STORAGE_API_KEY']}")

missing = [k for k, v in results.items() if v != "OK"]
print("\n" + ("All basics ready!" if not missing else f"Fix first: {', '.join(missing)}"))
