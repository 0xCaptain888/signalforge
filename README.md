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
Stage 4 (M2 research layer) shipped — IC / rolling IR / t-stat / IC-decay /
regime-layered attribution / BH-FDR multiple-testing correction / Deflated
Sharpe. 14 / 14 unit tests are green (5 from Stage 3 + 9 new). The pipeline
script `scripts/03_run_research.py` is ready to consume the parquet panels
the moment they exist.
Stage 5 (M3 strategy layer) shipped — signals → regime-conditional and
cross-section positions → vectorised backtest with strict t → t+1 execution,
realistic cost model, Monte-Carlo random-signal baseline, and a
calibrate-weights-from-research helper. 23 / 23 unit tests are green,
including a "cheat" signal sanity check that proves the backtest does not
leak same-day returns.
See full plan in [development schedule](./docs/SignalForge-开发周期表.md).

| Stage | Status |
|---|---|
| 0 — Repo init | ✅ done |
| 1 — Scaffold | ✅ done |
| 2 — M0 Data layer smoke | ⚠️ partial — see "M0 findings" below |
| 3 — M1 Factor layer | ✅ done — code + 5/5 unit tests green |
| 4 — M2 Research layer | ✅ done — IC/IR/FDR/regime/DSR + 14/14 tests green |
| 5 — M3 Strategy layer | ✅ done — t→t+1 backtest + cost/MC + 23/23 tests green |
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

# run factor research (Stage 4 — IC / IR / FDR / regime + figures)
python scripts/03_run_research.py

# run backtest (Stage 5 — IS/OOS + DSR + cost grid + monte-carlo + equity)
python scripts/04_backtest.py

# run unit tests (no-lookahead + survivorship + IC + multiple-testing + strategy)
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

## Stage 4 — M2 Research layer (shipped 2026-06-08)

The scoring core. Every metric pairs the factor at t with a **strictly
future** return; the few rolling estimators emit values only after a full
window of history exists.

| File | What it provides |
|---|---|
| `src/research/ic.py`               | `forward_returns`, `timeseries_ic`, `rolling_ic_series`, `ir_and_tstat`, `cross_section_ic`, `ic_decay` |
| `src/research/regime_attrib.py`    | `regime_layered_ic` (per-bucket IC + t-stat), `regime_ic_matrix` (factor × regime heatmap source) |
| `src/research/multiple_testing.py` | `bh_fdr` (Benjamini–Hochberg FDR), `deflated_sharpe` (López de Prado DSR) |
| `src/research/robustness.py`       | `time_split`, `walk_forward_windows`, `parameter_plateau`, `cost_sensitivity`, `stationary_block_bootstrap` |

Orchestrator: `scripts/03_run_research.py` runs every factor in
`factors_timeseries.parquet` through {pooled IC, rolling-60d IR/t-stat,
IC decay at HOLDING_PERIODS, regime-layered attribution, BH-FDR}, then
writes:

- `outputs/research_results.json` — machine-readable scorecard
- `outputs/figures/ic_decay.png`
- `outputs/figures/regime_ic_heatmap.png`

The script depends on `ohlcv.parquet` for BTC forward returns, so it
becomes runnable end-to-end the moment the Stage 2 price-data blocker
is resolved.

Additional unit tests (all green):
- `tests/test_ic.py` — `forward_returns` uses only future closes, IC
  recovers a constructed monotone signal, rolling IC respects window.
- `tests/test_multiple_testing.py` — BH-FDR flags only truly small p's,
  handles NaN inputs, DSR shrinks monotonically with more trials.

## Stage 5 — M3 Strategy layer (shipped 2026-06-08)

Signal → position → backtest, with the execution lag and cost accounting
done correctly so the OOS numbers are honestly comparable to HODL.

| File | What it provides |
|---|---|
| `src/strategy/signals.py`   | `factor_to_signal` (tanh squash, NaN-safe), `combine_signals` (L1-normalised weighted sum, bounded) |
| `src/strategy/portfolio.py` | `regime_conditional_positions` (single-asset timing), `cross_section_positions` (top-q L/S with cap), `default_regime_weights` |
| `src/strategy/backtest.py`  | `backtest_single`, `backtest_panel` (both apply strict t → t+1 shift), `_perf` (Sharpe/Sortino/Calmar/DD/alpha/beta/turnover/equity), `monte_carlo_random` baseline |
| `scripts/04_backtest.py`    | end-to-end: IS/OOS split, calibrate regime weights from `research_results.json`, Deflated Sharpe, cost-grid sensitivity, MC random-signal Sharpe, writes `backtest_results.json` + `walkforward_oos.png` |

New unit tests in `tests/test_strategy.py` (9 added, all green):
- bounded / NaN-safe / long-only signal transforms
- L1-normalised `combine_signals` cancels equal-opposite inputs
- t → t+1 execution lag verified by symmetry of long vs short positions
- **anti look-ahead**: a "cheat" signal equal to today's return earns
  near-zero Sharpe after the shift (would be > 30 without it)
- costs reduce returns; long/short XS basket is dollar-neutral and
  respects the per-asset cap
- unmapped regime ⇒ zero position; MC random-Sharpe stats are sensible

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
