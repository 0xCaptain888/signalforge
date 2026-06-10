#!/usr/bin/env python3
"""
Manual APEX Fund Script (Web3.py bypass)
Bypasses bnbagent SDK to directly interact with the ERC-8183 AgenticCommerce contract on BSC Testnet.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web3 import Web3

# --- Configuration ---
RPC_URL = "https://data-seed-prebsc-1-s1.binance.org:8545/"
PRIVATE_KEY = os.environ.get(
    "PRIVATE_KEY", "0xb1d8115e762cbaa1541e60cda3448fb6acbe4562b36c029d2e9e528160256bdd"
)
WALLET_ADDRESS = Web3().eth.account.from_key(PRIVATE_KEY).address

COMMERCE_ADDRESS = Web3.to_checksum_address(
    "0xa206c0517B6371C6638CD9e4a42Cc9f02A33B0DE"
)
U_TOKEN_ADDRESS = Web3.to_checksum_address("0xc70b8741b8b07a6d61e54fd4b20f22fa648e5565")

JOB_ID = 140
FUND_AMOUNT = 10_000_000_000_000_000_000  # 10 U (18 decimals)

# --- ABIs (Minimal) ---
ERC20_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "spender", "type": "address"},
            {"name": "amount", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "owner", "type": "address"},
            {"name": "spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function",
    },
]

COMMERCE_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "jobId", "type": "uint256"},
            {"name": "amount", "type": "uint256"},
        ],
        "name": "fund",
        "outputs": [],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "jobId", "type": "uint256"}],
        "name": "getJob",
        "outputs": [
            {
                "components": [
                    {"name": "id", "type": "uint256"},
                    {"name": "client", "type": "address"},
                    {"name": "provider", "type": "address"},
                    {"name": "evaluator", "type": "address"},
                    {"name": "description", "type": "string"},
                    {"name": "budget", "type": "uint256"},
                    {"name": "expiredAt", "type": "uint256"},
                    {"name": "status", "type": "uint8"},
                    {"name": "hook", "type": "address"},
                    {"name": "deliverable", "type": "bytes32"},
                    {"name": "submittedAt", "type": "uint256"},
                ],
                "name": "",
                "type": "tuple",
            }
        ],
        "type": "function",
    },
]


def main():
    print("=" * 60)
    print("APEX Manual Fund (Web3.py Direct Call)")
    print("=" * 60)

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    if not w3.is_connected():
        print("❌ Failed to connect to BSC Testnet RPC.")
        sys.exit(1)
    print(f"✅ Connected to BSC Testnet (Chain ID: {w3.eth.chain_id})")

    account = w3.eth.account.from_key(PRIVATE_KEY)
    print(f"👛 Wallet: {account.address}")

    # 1. Check Job Status
    commerce = w3.eth.contract(address=COMMERCE_ADDRESS, abi=COMMERCE_ABI)
    try:
        job = commerce.functions.getJob(JOB_ID).call()
        print(
            f"📋 Job {JOB_ID} Status: {job[7]} (0=OPEN, 1=FUNDED, 2=SUBMITTED, 3=COMPLETED, 4=CANCELLED)"
        )
        print(f"   Current Budget: {job[5]} wei")
        if job[7] >= 1:
            print("⚠️  Job is already funded or in a later state. Skipping fund.")
            return
    except Exception as e:
        print(f"⚠️  Could not fetch job details: {e}")

    # 2. Check U Token Balance & Allowance
    u_token = w3.eth.contract(address=U_TOKEN_ADDRESS, abi=ERC20_ABI)
    balance = u_token.functions.balanceOf(account.address).call()
    print(f"💰 U Token Balance: {w3.from_wei(balance, 'ether')} U")

    if balance < FUND_AMOUNT:
        print("❌ Insufficient U Token balance to fund this job.")
        sys.exit(1)

    allowance = u_token.functions.allowance(account.address, COMMERCE_ADDRESS).call()
    print(f"🔑 Current Allowance to Commerce: {w3.from_wei(allowance, 'ether')} U")

    # 3. Approve if necessary
    if allowance < FUND_AMOUNT:
        print(
            f"⏳ Approving {w3.from_wei(FUND_AMOUNT, 'ether')} U for Commerce contract..."
        )
        tx = u_token.functions.approve(COMMERCE_ADDRESS, FUND_AMOUNT).build_transaction(
            {
                "from": account.address,
                "nonce": w3.eth.get_transaction_count(account.address),
                "gas": 100000,
                "gasPrice": w3.eth.gas_price,
            }
        )
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"✅ Approve TX: https://testnet.bscscan.com/tx/{tx_hash.hex()}")
    else:
        print("✅ Allowance is sufficient.")

    # 4. Fund the Job
    print(f"⏳ Funding Job {JOB_ID} with {w3.from_wei(FUND_AMOUNT, 'ether')} U...")
    try:
        tx = commerce.functions.fund(JOB_ID, FUND_AMOUNT).build_transaction(
            {
                "from": account.address,
                "nonce": w3.eth.get_transaction_count(account.address),
                "gas": 200000,
                "gasPrice": w3.eth.gas_price,
            }
        )
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        if receipt["status"] == 1:
            print(
                f"🎉 SUCCESS! Fund TX: https://testnet.bscscan.com/tx/{tx_hash.hex()}"
            )
        else:
            print(
                f"❌ Transaction reverted. TX: https://testnet.bscscan.com/tx/{tx_hash.hex()}"
            )
    except Exception as e:
        print(f"❌ Fund transaction failed: {e}")


if __name__ == "__main__":
    main()
