# SignalForge — Signal Edge Adjudicator

> The referee for the agent economy.
> Give it any trading signal; it tells you whether the alpha is **real, noise, or leakage**.

## Skill Identity
- **name**: `signalforge-adjudicator`
- **version**: `2.1.0`
- **author**: `0xCaptain888`
- **license**: `Apache-2.0`
- **category**: `quant-research / signal-validation`

## find_skill Keywords
```
signal validation, overfitting detection, backtest audit, deflated sharpe,
fear and greed, edge confidence, quant research, leakage detection, CMC,
alpha, strategy skills, backtestable spec, factor research, regime analysis
```

## What This Skill Does
1. **Accepts** a candidate trading signal (name, source, definition, holding period)
2. **Runs** rigorous statistical validation:
   - Lopez de Prado Deflated Sharpe Ratio (selection-bias corrected)
   - Benjamini-Hochberg FDR at q=0.10
   - Walk-forward IS/OOS analysis (7 windows)
   - Parameter plateau scan (overfit signature)
   - Leakage detection (naive vs IS-only Sharpe)
   - Regime-conditional alpha significance
3. **Returns** verdict: `STRONG_ACCEPT / ACCEPT / WEAK / REJECT / LEAKAGE_DETECTED`
4. **Includes** edge_confidence (0-100), itemized reasons, reproducible StrategySpec

## Data Sources
- **Primary alpha**: CMC **proprietary** Fear & Greed `/v3/fear-and-greed/historical` (NOT Alternative.me)
- **MCP**: `mcp.coinmarketcap.com/mcp` (12 tools)
- **x402**: `mcp.coinmarketcap.com/x402` ($0.01 USDC/call on Base)

## Endpoints

### POST /adjudicate — $0.50 USDC via x402 (Base)
Request:
```json
{
  "asset": "ETH",
  "candidate_signal": {
    "name": "my_signal",
    "source": "cmc_fear_greed",
    "definition": "fg < 20 -> long; fg > 80 -> short",
    "holding_period_days": 5
  },
  "risk": "balanced"
}
```
Response: full verdict (see docs/PRODUCT.md). Example highlight:
```json
{
  "verdict": "LEAKAGE_DETECTED",
  "edge_confidence": 12,
  "leakage_check": { "naive_sharpe_if_leaked": 0.85, "honest_sharpe": -0.99, "leaked": true }
}
```

### POST /generate_spec — $0.50 USDC via x402
Returns a backtestable StrategySpec following the Track 2 contract.

### GET /status, GET /.well-known/skill-card.json — free

## x402 Payment Flow
```
Agent -> POST /adjudicate (no payment)      <- 402 + quote
Agent signs EIP-712 auth locally (key never leaves device)
Agent -> POST /adjudicate + X-PAYMENT       <- 200 + verdict
```

## Reproducibility
Deterministic (seed=42). `python scripts/09_e2e_smoke_test.py` verifies the
full pipeline. v1 research reproducible via `python scripts/reproduce.py`.
