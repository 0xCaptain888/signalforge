#!/usr/bin/env python3
"""
TWAK signer demo — shows "keys stay local, agent signs autonomously".

Usage:
    python examples/twak_demo.py [--signer twak|evm]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main():
    parser = argparse.ArgumentParser(description="SignalForge signer demo")
    parser.add_argument("--signer", choices=["twak", "evm"], default="evm")
    args = parser.parse_args()

    print(f"\n[TWAK Demo] Using signer: {args.signer.upper()}")

    if args.signer == "twak":
        from src.twt.signer import TWAKWalletProvider
        wallet = TWAKWalletProvider()
        print(f"  Wallet address: {wallet.address}")
        msg = "SignalForge TWAK demo — keys stay local, agent signs autonomously"
        sig = wallet.sign_message(msg)
        print(f"  [Demo] personal_sign:")
        print(f"    message  : {msg}")
        print(f"    signature: {str(sig.get('signature'))[:50]}...")
        print("\n  NOTE: endpoints in src/twt/signer.py are PLACEHOLDERS.")
        print("  See docs/TWAK_GUIDE.md to wire the real TWAK API before the prize demo.")
    else:
        try:
            from src.twt.signer import get_wallet_provider
            wallet = get_wallet_provider(signer="evm")
            print(f"  Wallet address: {wallet.address}")
        except Exception as e:
            print(f"  EVM signer requires bnbagent + WALLET_PASSWORD: {e}")

    print("\n  Done.\n")


if __name__ == "__main__":
    main()
