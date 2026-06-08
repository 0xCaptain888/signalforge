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

Stage 2 shipped — M0 smoke executed, blocker resolved via Binance public-API
fallback for OHLCV. `scripts/01_pull_data.py` now produces the full set of
parquet inputs needed by Stages 3–6 (1075 days of CMC F&G, 18 coins of daily
OHLCV from 2023-06-29 onwards, 5000-row crypto map, 1-row global metrics
snapshot).
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
Stage 6 (M4 LLM + Spec layer) shipped — DeepSeek client (chat + reasoner,
fully logged), per-factor rationale synthesis, markdown report writer with
a post-hoc hallucination detector, pydantic `StrategySpec` schema with a
deterministic builder, plus `scripts/05_generate_spec.py`,
`scripts/06_write_report.py`, and `scripts/reproduce.py`. 28 / 28 tests
green (no live LLM call required — schema, builder, and detector are
verified deterministically).
See full plan in [development schedule](./docs/SignalForge-开发周期表.md).

| Stage | Status |
|---|---|
| 0 — Repo init | ✅ done |
| 1 — Scaffold | ✅ done |
| 2 — M0 Data layer smoke | ✅ done — 7-endpoint smoke + M0 back-fill + Binance OHLCV fallback |
| 3 — M1 Factor layer | ✅ done — code + 5/5 unit tests green |
| 4 — M2 Research layer | ✅ done — IC/IR/FDR/regime/DSR + 14/14 tests green |
| 5 — M3 Strategy layer | ✅ done — t→t+1 backtest + cost/MC + 23/23 tests green |
| 6 — M4 LLM + Spec | ✅ done — DeepSeek synth + report + StrategySpec + 28/28 tests green |
| 7 — M5 Reproducibility | ✅ done — reproduce.py + manifest hash gate + no-key sanity script |
| 8 — M6 Submission | ⏳ pending |
| 9 — M7 Optional add-ons | ⏳ pending |

## End-to-end pipeline status (2026-06-08)

Full reproduce pass against the fresh data pull:

| Step | Output | Notes |
|---|---|---|
| `01_pull_data.py`     | 4 parquet files in `data/processed/` | CMC F&G + map + Binance OHLCV fallback |
| `02_build_factors.py` | `factors_timeseries.parquet`, `regime.parquet` | 1075 days, 8 of 9 regime buckets populated |
| `03_run_research.py`  | `research_results.json` + 2 figures | **0 factors FDR-significant at pooled level** — alpha is regime-conditional (e.g. `fg_level` t-stat = −4.56 in `CHOP_NEUTRAL`, p ≈ 9e-6) |
| `04_backtest.py`      | `backtest_results.json` + walkforward fig | OOS Sharpe = 0.85 vs Monte-Carlo 95th pct = 1.00 — strategy is borderline; iteration on regime weights / horizon needed |
| `05_generate_spec.py` | `outputs/specs/signalforge-cmc-fg-regime-v1.json` | DeepSeek key currently 402 (insufficient balance); deterministic-template fallback engaged, spec still pydantic-valid |
| `06_write_report.py`  | `outputs/reports/research_report.md` | LLM-fallback template; `verify_numbers` clean |
| `reproduce.py`        | re-runs 02 → 05 | passes; 28 / 28 tests still green |

**Honest read.** The pooled IC of CMC F&G washes out because the sign flips
across regimes — a textbook finding that the doc anticipated. The
regime-conditional t-stats are very strong, but the strategy that the
default `regime_weights` builder consumes only picks up factors that cleared
pooled FDR. Next iteration: lower the FDR gate to regime-stratified or
add a parameter sweep over `HOLDING_PERIODS`.

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

**Implication.** The CMC proprietary F&G alpha source (E) is fully usable. To
unblock downstream stages without a paid plan upgrade, `scripts/01_pull_data.py`
falls back to **Binance public klines** (free, no API key) for OHLCV. CMC F&G
remains the unique alpha source — Binance prices are infrastructure for
forward-return / regime calculations and are honestly disclosed in the report.

Stage 2.6 / 2.7 (back-fill `config/constants.py` + `src/cmc/schemas.py`) and
Stage 2.9 / 2.10 (`scripts/01_pull_data.py` + full pull) are now complete:

| Artefact | Rows / Notes |
|---|---|
| `data/processed/fear_greed.parquet` | 1075 rows, 2023-06-29 → 2026-06-07 |
| `data/processed/crypto_map.parquet` | 5000 coins |
| `data/processed/ohlcv.parquet` | 18962 rows, 18 coins (Binance fallback) |
| `data/processed/global_metrics_latest.parquet` | 1 snapshot row (historical 403) |

Total CMC credits spent on the full pull: **2** (cache hits cost zero on rerun).

## Quickstart

```bash
cp .env.example .env
# edit .env, fill in CMC_API_KEY and DEEPSEEK_API_KEY

python -m venv .venv && source .venv/bin/activate
pip install -e .

# go/no-go smoke test (after Stage 2)
python scripts/00_smoke_test.py

# full historical data pull (CMC F&G + map + Binance OHLCV fallback)
python scripts/01_pull_data.py

# build factor panels (Stage 3 — needs parquet outputs from 01_pull_data.py)
python scripts/02_build_factors.py

# run factor research (Stage 4 — IC / IR / FDR / regime + figures)
python scripts/03_run_research.py

# run backtest (Stage 5 — IS/OOS + DSR + cost grid + monte-carlo + equity)
python scripts/04_backtest.py

# generate machine-readable StrategySpec (Stage 6 — LLM rationales + spec.json)
python scripts/05_generate_spec.py

# write the markdown research report (Stage 6 — with hallucination check)
python scripts/06_write_report.py

# one-click reproduction of 02 -> 06 with manifest hash check (judges run this)
python scripts/reproduce.py

# judge-no-key sanity: clears API env, wipes outputs, reruns, re-verifies
python scripts/check_no_key_reproduction.py

# run unit tests (all 28)
pytest tests/ -v
```

## Stage 7 — M5 Reproducibility (shipped 2026-06-08)

Two guarantees the judges can verify with a single command each.

| Script | What it proves |
|---|---|
| `scripts/reproduce.py` | Runs `02 -> 03 -> 04 -> 05 -> 06` with `PYTHONHASHSEED=42`, then canonicalises every numeric output (volatile keys like `created_at` are masked) and compares its SHA-256 to `outputs/reproduce_manifest.json`. Exits non-zero on any mismatch. |
| `scripts/check_no_key_reproduction.py` | Snapshots `outputs/`, wipes the volatile JSONs, then re-invokes `reproduce.py` in a subprocess whose `CMC_API_KEY` and `DEEPSEEK_API_KEY` are both `""`. Confirms that the cached parquets under `data/processed/` plus the deterministic LLM-fallback templates are enough for any reviewer to rebuild every numerical field — no API credentials required. |

Canonical hashes (manifest at `outputs/reproduce_manifest.json`):

```
research   -> 687293ce48a1b784…
backtest   -> 3a39935acb085f32…
spec       -> 17a0743447437651…
```

Re-run anytime; a clean pass prints `✓ reproduction PASSED — every
numerical field matches the manifest`. To intentionally adopt new numbers
(e.g. after editing a factor), delete `outputs/reproduce_manifest.json`
and the next run will rewrite it.

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

## Stage 6 — M4 LLM + Spec layer (shipped 2026-06-08)

The LLM never computes numbers; it only narrates them. Every prompt and
response is logged for audit.

| File | What it provides |
|---|---|
| `src/llm/deepseek_client.py`    | lazy OpenAI-compatible client for DeepSeek; `chat()` (deepseek-chat) and `reason()` (deepseek-reasoner); writes every call to `outputs/llm_logs/` |
| `src/llm/research_synth.py`     | per-factor economic / behavioural rationale, grounded only in supplied stats |
| `src/llm/report_writer.py`      | full markdown report writer + `verify_numbers` hallucination detector (regex-extracts decimals from the draft and flags any not present in the source JSON) |
| `src/spec/schema.py`            | pydantic `StrategySpec` / `FactorSpec` / `DataSource` contract |
| `src/spec/builder.py`           | deterministic spec assembly from research + backtest + LLM rationales; only FDR-significant factors are included |
| `scripts/05_generate_spec.py`   | DeepSeek synth pass → writes `outputs/specs/<spec_id>.json` |
| `scripts/06_write_report.py`    | DeepSeek report pass → writes `outputs/reports/research_report.md` + prints any hallucination warnings |
| `scripts/reproduce.py`          | judge-facing one-click rerun of 02 → 03 → 04 → 05 with seed=42 |

New unit tests in `tests/test_spec.py` (5 added, all green — no LLM call):
- `build_spec` only includes FDR-significant factors; numbers are copied
  verbatim from the research JSON
- `StrategySpec` round-trips through `model_dump_json` / `model_validate`
- `verify_numbers` passes when all decimals trace back; flags fabricated
  ones (e.g. `9.99` not in source); accepts sign-flips (e.g. drawdown
  reported as `22.5%` when source has `-22.5`)

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
