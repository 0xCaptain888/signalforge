# SignalForge — Judge Verification Checklist

Verify every claim in ~5 minutes.

## 1. Technical Execution

| Claim | Command | Expected |
|-------|---------|----------|
| Scoring is exact | `python src/adjudicator/scoring.py` | `score=12 ... PASS` |
| All tests green | `pytest tests/ -m "not onchain"` | ~80 passed |
| E2E pipeline works | `python scripts/09_e2e_smoke_test.py` | All 5 PASS |
| Demo runs | `python scripts/07_adjudicate_demo.py` | LEAKAGE_DETECTED, conf=12 |

## 2. Creativity — leakage adjudication

| Claim | Check |
|-------|-------|
| Negative result = product proof | README "Why SignalForge" |
| Leakage quantified | `outputs/verdicts/sample_leakage.json`: naive=0.85, honest=-0.99, leaked=true |
| Transparent scoring | `src/adjudicator/scoring.py` — 6 readable rules |

## 3. Application Value

| Claim | Command | Expected |
|-------|---------|----------|
| x402 gate | `curl -X POST <url>/adjudicate -d '{...}'` | HTTP 402 + quote |
| Pays then works | retry with X-PAYMENT header | HTTP 200 + verdict |
| Skill discoverable | `curl <url>/.well-known/skill-card.json` | JSON with keywords |
| Backtestable spec | `outputs/specs/signalforge-cmc-fg-regime-v1.json` | full spec with backtest_function |

## 4. CMC Special Prize evidence

| Evidence | Location |
|----------|----------|
| Proprietary F&G | provenance entry: `/v3/fear-and-greed/historical` |
| MCP channel | `outputs/cmc_provenance.json` channel=mcp entry |
| x402 real tx | `outputs/cmc_provenance.json` channel=x402, payment_tx + BaseScan link |
| Marketplace listing | skill-card URL + submission screenshot |

## 5. BNB Special Prize evidence

| Evidence | Location |
|----------|----------|
| ERC-8004 registration | `outputs/onchain/registration.json` + BscScan tx |
| APEX create/fund | `outputs/onchain/client_demo_result.json` + BscScan txs |
| Settled job (COMPLETED) | BscScan testnet |
| IPFS deliverable | Pinata gateway CID |

### APEX Settlement Note
APEX settlement requires a 30-minute UMA OOv3 liveness (no-dispute) period.
The demo shows a pre-settled job; live settlement can be re-triggered any time
with `python examples/client_demo.py`.

## 6. Trust Wallet AK (optional)

`python examples/twak_demo.py --signer twak` + docs/TWAK_GUIDE.md
