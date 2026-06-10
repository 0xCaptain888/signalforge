# SignalForge — Changelog & Audit Trail

> Full iteration history and audit passes. The README shows the product;
> engineering audit detail lives here.

## v2.1.0 — 2026-06 (Signal Edge Adjudicator)

### Added
- `src/adjudicator/` — verdict engine (schema / scoring / leakage / core)
- `src/cmc/mcp_client.py` — CMC Data MCP client (with `initialize` handshake)
- `src/cmc/x402_client.py` — x402 pay-per-call (EIP-3009 + fallback)
- `src/cmc/provenance.py` — 3-channel usage evidence recorder
- `service/` — FastAPI Skill + x402 ASGI middleware + SKILL.md
- `src/bnb/` — ERC-8004 registration + APEX adjudication server
- `examples/client_demo.py` — APEX 8-step client lifecycle
- `examples/twak_demo.py` + `src/twt/signer.py` — Trust Wallet Agent Kit branch
- `ui/` — React demo console (gauge + Sharpe comparison + evidence panel)
- `scripts/07_adjudicate_demo.py` / `08_prove_x402_cmc.py` / `09_e2e_smoke_test.py`
- 7 test modules, ~80 tests
- `outputs/specs/signalforge-cmc-fg-regime-v1.json` — backtestable StrategySpec

### Fixed (vs v2.0 draft)
- P0-1: scoring Rule 2/4 format bugs; baseline tuned to 59; Rule 6 added
  so v1 real data outputs edge_confidence exactly 12 (CI-verified)
- P0-2: `/generate_spec` defensive wrapper around v1 `run_skill`
- P0-3: `LeakageCheck` includes `direction_flip_detected` + `lookahead_flag`
- P0-4: APEX client `approve_token` hardened with ERC8183_ADDRESS constant
- P2-9: UI SERVICE_URL no longer hardcodes localhost in production
- P2-12: MCP `initialize` handshake before tools/list

## v1.x — Quant research audit history

### Audit Pass 3 — IS-only calibration fix
- Problem: `build_weights()` fitted regime_weights on the FULL sample (OOS leak)
- Fix: `build_weights_is_only()`; OOS strictly uses IS-only weights
- Impact: naive OOS Sharpe +0.85 -> honest OOS Sharpe -0.99
- Conclusion: do NOT trade v1; this honest negative is now the v2 product's proof

### Audit Pass 2 — Look-ahead unit tests
- Added tamper-future-values tests; all pass; no look-ahead bias

### Audit Pass 1 — BH-FDR multiple-testing correction
- BH-FDR (q=0.10), pooled: 0 factors significant (DSR prob = 0.001)
