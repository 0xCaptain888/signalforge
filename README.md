# SignalForge

> The first systematic factor-research engine for CoinMarketCap's **proprietary**
> Fear & Greed index — an under-researched alpha source distinct from Alternative.me.

Built for BNB Hack Track 2 (Strategy Skills). Produces backtestable, regime-aware
strategy specs from CMC proprietary market signals.

## Why this is different

Most F&G research uses Alternative.me's public index. CMC has its OWN F&G algorithm
(volatility + momentum + volume + dominance + social). We're the first to rigorously
test its factor efficacy and engineer it into a reproducible strategy spec.

We deliberately EXCLUDED ETF-flow / social / on-chain signals — they have no
historical API and cannot be honestly backtested. **Rigor over hype.**

## Status

Stage 2 in progress — M0 smoke executed; **partial blocker found**, decision pending.
Stage 3 (M1 factor layer) shipped — all 5 unit tests for no-look-ahead and
survivorship-bias are green. The factor code is data-source agnostic, so it
runs end-to-end as soon as price / dominance data arrives via any of the
fallback paths discussed in M0 findings.
See full plan in [development schedule](./docs/SignalForge-开发周期表.md).

| Stage | Status |
|---|---|
| 0 — Repo init | ✅ done |
| 1 — Scaffold | ✅ done |
| 2 — M0 Data layer smoke | ⚠️ partial — see "M0 findings" below |
| 3 — M1 Factor layer | ✅ done — code + 5/5 unit tests green |
| 4 — M2 Research layer | ⏳ pending |
| 5 — M3 Strategy layer | ⏳ pending |
| 6 — M4 LLM + Spec | ⏳ pending |
| 7 — M5 Reproducibility | ⏳ pending |
| 8 — M6 Submission | ⏳ pending |
| 9 — M7 Optional add-ons | ⏳ pending |

## M0 findings (Stage 2.5, run 2026-06-08)

Smoke test executed against the supplied CMC key — on the **free Basic plan**
(15 000 credits / month, 50 req / min). Endpoint availability:

| # | Endpoint | Status | Notes |
|---|---|---|---|
| A | `/v1/key/info` | ✅ 200 | plan + credits OK |
| B | `/v1/cryptocurrency/map` | ✅ 200 | all expected fields present |
| C | `/v1/cryptocurrency/listings/historical` | ❌ **403** | Basic plan does NOT include this |
| D | `/v2/cryptocurrency/ohlcv/historical` | ❌ **403** | Basic plan does NOT include this |
| E | `/v3/fear-and-greed/historical` ★ | ✅ 200 | 500 rows/page, paginates further |
| F | `/v1/global-metrics/quotes/historical` | ❌ **403** | Basic plan does NOT include this |
| G | `/v1/global-metrics/quotes/latest` | ✅ 200 | rich snapshot, no `altcoin_season` field |

**Implication.** The CMC proprietary F&G alpha source (E) is fully usable. But
the historical OHLCV (D) and historical global metrics (F) endpoints that the
backtest depends on are **not** on this plan tier — the strategy cannot be
backtested on CMC-native price data alone.

Stage 2.6 / 2.7 (back-fill `config/constants.py` + `src/cmc/schemas.py`) are
done with verified field shapes from the four working endpoints. Stage 2.9 /
2.10 (`scripts/01_pull_data.py` + full pull) is **blocked** pending a path
decision (CMC plan upgrade vs. hybrid price-source vs. narrative-only).

## Quickstart

```bash
cp .env.example .env
# edit .env, fill in CMC_API_KEY and DEEPSEEK_API_KEY

python -m venv .venv && source .venv/bin/activate
pip install -e .

# go/no-go smoke test (after Stage 2)
python scripts/00_smoke_test.py

# build factor panels (Stage 3 — needs parquet outputs from 01_pull_data.py)
python scripts/02_build_factors.py

# run unit tests (no-lookahead + survivorship-bias)
pytest tests/ -v
```

## Stage 3 — M1 Factor layer (shipped 2026-06-08)

Three factor families, all point-in-time and bias-tested:

| File | Factors |
|---|---|
| `src/factors/timeseries.py`    | `fg_level`, `fg_zscore_90`, `fg_momentum_7`, `fg_extreme_rev`, `fg_regime_dur`, `dom_trend_30`, `dom_zscore_90`, `mktcap_mom_30`, `fg_cross_dom` |
| `src/factors/cross_section.py` | `xs_rank_mom_30`, `xs_size`, `xs_ret_mom_90`, `xs_vol_60` (within-day pct-rank, centred) |
| `src/factors/regime.py`        | `dir_regime` × `sent_regime` (BULL/BEAR/CHOP × FEAR/NEUTRAL/GREED) |

Build script: `scripts/02_build_factors.py` — gracefully degrades when an
input parquet is missing (Basic-plan tolerance), so the F&G-only branch
still ships a usable `factors_timeseries.parquet`.

Unit tests (all green):
- `tests/test_no_lookahead.py` — tampering future values cannot change
  history; rolling windows return NaN before `min_periods` is met.
- `tests/test_survivorship.py` — universe at every rebalance date matches
  the snapshot for THAT date, including delisted coins and new listings.

## Architecture (planned)

```
config/        runtime settings + project constants
src/cmc/       CMC API client + endpoints + schemas
src/factors/   timeseries + cross-section + regime factors
src/research/  IC / IR / t-stat / FDR / robustness
src/strategy/  signals + portfolio + backtest
src/llm/       DeepSeek client + factor synth + report writer
src/spec/      pydantic StrategySpec schema + builder
scripts/       00_smoke → 06_write_report → reproduce
tests/         no-lookahead + survivorship-bias unit tests
outputs/       specs / reports / figures / llm_logs
```

## License

Apache-2.0 (TBD)
