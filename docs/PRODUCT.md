# SignalForge — Product API Contract

## What it is

**Signal Edge Adjudicator**: any agent submits a candidate trading signal;
SignalForge returns a structured verdict on whether the alpha is
**real, noise, or leakage**.

## POST /adjudicate  (x402: $0.50 USDC/call on Base)

### Request
```json
{
  "asset": "ETH",
  "candidate_signal": {
    "name": "cmc_fg_extreme_reversal",
    "source": "cmc_fear_greed",
    "definition": "fg < 20 -> long; fg > 80 -> short",
    "holding_period_days": 5
  },
  "risk": "balanced"
}
```

### Response (LEAKAGE_DETECTED example)
```json
{
  "verdict": "LEAKAGE_DETECTED",
  "edge_confidence": 12,
  "reasons": [
    "DSR prob=0.001 < 0.20 -> strong signal: no alpha (-25)",
    "0 factors pass BH-FDR q=0.10 (pooled) -> no alpha in universe (-15)",
    "WF median Sharpe=-2.10 < -1.0 -> severe out-of-sample loss (-12)",
    "Parameter scan shows single spike -> overfit risk (-10)",
    "Look-ahead test PASS -> no look-ahead bias (+0)",
    "Strongest regime t-stat=4.56 >= 4.0 -> local regime alpha significant (+15)"
  ],
  "verdict_summary": "REJECT this signal. Data leakage detected: naive Sharpe=0.85 vs honest Sharpe=-0.99...",
  "leakage_check": {
    "lookahead_test": "PASS",
    "is_only_calibration": "ENFORCED",
    "naive_sharpe_if_leaked": 0.85,
    "honest_sharpe": -0.99,
    "gap": 1.84,
    "threshold": 0.80,
    "direction_flip_detected": true,
    "lookahead_flag": false,
    "leaked": true
  },
  "statistics": { "...": "DSR/FDR/WF/plateau/regime stats" },
  "strategy_spec_ref": "outputs/specs/signalforge-cmc-fg-regime-v1.json",
  "cmc_data_provenance": {
    "access_channels_used": ["rest"],
    "historical_channels_documented": ["rest", "mcp", "x402"]
  },
  "billing": { "protocol": "x402", "price_usdc": 0.50, "network": "base" },
  "meta": { "adjudicator_version": "2.1.0", "seed": 42, "reproducible": true }
}
```

## Verdict scale

| Verdict | Condition |
|---------|-----------|
| STRONG_ACCEPT | edge_confidence >= 75 |
| ACCEPT | 60-74 |
| WEAK | 40-59 |
| REJECT | < 40 |
| LEAKAGE_DETECTED | leakage flag overrides any score |

## Edge Confidence scoring (transparent, deterministic)

Baseline 59, six rules:
1. Deflated Sharpe Ratio probability (Lopez de Prado): -25..+25
2. BH-FDR significant factor count (q=0.10): -15..+15
3. Walk-forward median OOS Sharpe (7 windows): -12..+15
4. Parameter plateau vs spike: -10/+10
5. Look-ahead test red line: -30/0
6. Regime-conditional t-stat: 0..+15

v1 real data: 59-25-15-12-10+0+15 = **12** (verified in CI).

## Other endpoints

| Endpoint | Payment | Purpose |
|----------|---------|---------|
| POST /generate_spec | x402 $0.50 | Backtestable StrategySpec |
| GET /spec/{id} | free | Fetch spec JSON |
| GET /.well-known/skill-card.json | free | Marketplace discovery |
| GET /status | free | Pricing + provenance summary |
| GET /health | free | Health check |
