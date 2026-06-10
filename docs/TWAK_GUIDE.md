# Trust Wallet Agent Kit (TWAK) Integration Guide

> Goal: maximize the Best Use of Trust Wallet Agent Kit prize ($2,000).

## IMPORTANT: current endpoints are placeholders

The API endpoints in `src/twt/signer.py` (`/v1/wallet/...`) were inferred from
TWAK's feature description and are NOT confirmed. You MUST consult the official
docs and replace them before the prize demo.

## 1. Get a real API key

1. Visit https://developer.trustwallet.com/agent-kit
2. Request API access (project: BNB Hack 2026 Track 2, SignalForge)
3. Put the key in `.env` as `TWAK_API_KEY`

## 2. Update `src/twt/signer.py`

Replace these placeholder paths with the documented ones:
- `/v1/wallet/sign-transaction`
- `/v1/wallet/sign-message`
- `/v1/wallet/sign-typed-data`
- `/v1/wallet/address`

## 3. Minimal evidence path

Option A (strongest — on-chain tx):
```
python examples/twak_demo.py --signer twak
# sign an ERC-8004 registration with TWAK -> BSC Testnet tx hash
```

Option B (minimum viable — local signing demo):
```
python examples/twak_demo.py --signer twak
# screenshot of a real (non-simulated) TWAK API response + signature
```

## 4. Acceptance checklist

- [ ] TWAK_API_KEY set and real (not simulation)
- [ ] Endpoints in signer.py updated to documented values
- [ ] `--signer twak` produces a non-simulated signature
- [ ] One verifiable evidence artifact (tx or screenshot)
- [ ] TWAK usage declared in the DoraHacks submission
