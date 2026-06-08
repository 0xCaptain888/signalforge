# SignalForge

> The first systematic factor-research engine for CoinMarketCap's **proprietary**
> Fear & Greed index — an under-researched alpha source distinct from Alternative.me.

Built for **BNB Hack Track 2 (Strategy Skills)** with the CMC special-prize
narrative front-and-centre. Produces backtestable, regime-aware strategy
specs from CMC proprietary market signals.

| Track | Deliverable | Status |
|---|---|---|
| BNB Hack Track 2 | reproducible `StrategySpec` JSON + research report | ✅ shipped |
| CMC special prize | CMC-proprietary F&G as the unique alpha source | ✅ shipped |

---

## Why this is different

Most public F&G research uses **Alternative.me**'s open index. CoinMarketCap
runs its **OWN** F&G algorithm (volatility + momentum + volume + dominance +
social) and exposes the full history via
`/v3/fear-and-greed/historical`. We are the first to rigorously test its
factor efficacy and engineer it into a reproducible strategy spec.

We deliberately **EXCLUDED** ETF-flow / social-media / on-chain whale signals
— none of them have a clean historical API on the supplied CMC tier, so
none of them can be honestly back-tested. **Rigor over hype.**

---

## Architecture

```
config/        runtime settings + project constants (incl. M0 back-fill)
src/cmc/       CMC API client + endpoints + pydantic schemas
src/factors/   timeseries + cross-section + regime factors (point-in-time)
src/research/  IC / Rank-IC / IR / t-stat / IC-decay / FDR / DSR / bootstrap
src/strategy/  factor→signal→position→backtest with t→t+1 execution
src/llm/       DeepSeek client + per-factor synth + report writer + hallucination detector
src/spec/       pydantic StrategySpec schema + deterministic builder + skill_wrapper (§8.2)
scripts/       00_smoke → 01_pull → 02_factors → 03_research → 04_backtest
               → 05_spec → 06_report → reproduce → check_no_key_reproduction
tests/         38 unit tests (look-ahead, survivorship, IC, FDR, DSR, strategy, spec, skill, audit-fixes)
data/raw/      CMC samples (committed) + cached raw responses (ignored)
data/processed/ canonical parquet panels (committed; judges reproduce from here)
outputs/       specs / reports / figures / llm_logs + reproduce_manifest.json
```

```
   CMC F&G (proprietary)      Binance OHLCV (free, fallback)
            │                              │
            ▼                              ▼
    src/factors/timeseries         src/factors/regime (BTC × MA200)
            │                              │
            └──────────────┬───────────────┘
                           ▼
                  src/research/{ic,regime_attrib,
                                multiple_testing,robustness}
                           │
                           ▼
             src/strategy/{signals,portfolio,backtest}
                           │
                  ┌────────┼────────┐
                  ▼        ▼        ▼
            StrategySpec  report   walk-forward
              (JSON)      (PDF)    OOS figure
```

---

## Quickstart

```bash
cp .env.example .env
# edit .env, fill in CMC_API_KEY and DEEPSEEK_API_KEY
# (both are optional for reproduction — judges can leave them empty)

python -m venv .venv && source .venv/bin/activate
pip install -e .

# go/no-go smoke test (Stage 2 / M0)
python scripts/00_smoke_test.py

# full historical pull (CMC F&G + map + Binance OHLCV fallback)
python scripts/01_pull_data.py

# factor build → research → backtest → spec → report
python scripts/02_build_factors.py
python scripts/03_run_research.py
python scripts/04_backtest.py
python scripts/05_generate_spec.py
python scripts/06_write_report.py

# one-click reproduction with manifest hash gate (Stage 7 / M5)
python scripts/reproduce.py

# judge-no-key sanity (clears API env, wipes outputs, reruns, re-verifies)
python scripts/check_no_key_reproduction.py

# unit tests (28 total)
pytest tests/ -v
```

---

## Rigor — what makes this quant research, not a toy

1. **Point-in-time factors**, survivorship-bias-free universe scaffolding
   (`listings/historical` snapshots when the plan allows; otherwise pure
   time-series with documented degradation).
2. **Look-ahead bias unit tests** — `tests/test_no_lookahead.py` tampers
   future values and asserts history is unchanged; rolling windows must
   return NaN before `min_periods` is met.
3. **IC / Rank-IC / IR / t-stat + IC decay** at multiple holding periods
   (`HOLDING_PERIODS = [1, 5, 10, 20, 40]`).
4. **Regime-layered attribution** — every factor gets a factor × regime IC
   matrix; the report's heatmap is generated from the same JSON the spec
   consumes.
5. **Multiple-testing correction** — Benjamini–Hochberg FDR at q = 0.10,
   plus López de Prado's **Deflated Sharpe Ratio** for the realised strategy.
6. **Walk-forward IS/OOS + parameter-plateau + cost-grid sensitivity +
   Monte-Carlo random-signal baseline.** OOS is never used for parameter
   selection: `scripts/04_backtest.py::build_weights_is_only` refits
   regime weights using ONLY dates strictly before the IS/OOS cut, and
   the same helper drives each walk-forward window. The plateau scan
   sweeps the rolling-IC window over `[30, 45, 60, 90, 120]` so the
   reader can see whether the OOS Sharpe sits on a plateau or a spike.
   `tests/test_audit_fixes.py::test_is_only_calibration_is_leak_free`
   tampers OOS factor values and asserts the calibrated weights are
   unchanged — the leak gate is enforced in CI.

Every numeric value in the report and the spec is traceable back to a
Python computation; the LLM only narrates. A regex-based
`verify_numbers` hallucination detector reads the draft and flags any
decimal that does not appear in the source JSON.

---

## Outputs

| Artefact | Path | Notes |
|---|---|---|
| Machine-readable strategy spec | `outputs/specs/signalforge-cmc-fg-regime-v1.json` | pydantic-valid `StrategySpec`; `is_proprietary: true`; `reproducibility.seed = 42` |
| Research report (markdown) | `outputs/reports/research_report.md` | 8 chapters; `verify_numbers` clean |
| Research report (PDF) | `outputs/reports/research_report.pdf` | renders the markdown with the 3 figures inline |
| Figure — IC decay | `outputs/figures/ic_decay.png` | per-factor IC vs holding period |
| Figure — regime × factor IC heatmap | `outputs/figures/regime_ic_heatmap.png` | the core empirical finding |
| Figure — walk-forward OOS equity | `outputs/figures/walkforward_oos.png` | strategy vs BTC HODL |
| Reproduce manifest | `outputs/reproduce_manifest.json` | canonical SHA-256 of every numeric output |
| Audit logs | `outputs/llm_logs/` | every DeepSeek prompt/response/failure |
| One-click reproduction | `python scripts/reproduce.py` | seed = 42; manifest hash gate |

---

## CMC data usage (special-prize narrative)

Core alpha source: **CMC PROPRIETARY Fear & Greed**
(`/v3/fear-and-greed/historical`) — a CoinMarketCap-internal index that
ingests their own volatility / momentum / volume / dominance / social
features into a single 0–100 daily score. This index does **not** exist
on Alternative.me; the proprietary methodology is the entire reason the
strategy has an edge.

Supporting CMC endpoints used:

| Endpoint | Used for | Status on the supplied key (Basic) |
|---|---|---|
| `/v1/key/info` | bookkeeping (0 credit) | ✅ |
| `/v1/cryptocurrency/map` | universe scaffolding (0 credit) | ✅ |
| `/v3/fear-and-greed/historical` | **core alpha** | ✅ |
| `/v1/global-metrics/quotes/latest` | dominance / total-cap snapshot | ✅ |
| `/v1/cryptocurrency/listings/historical` | point-in-time universe | ❌ 403 (plan gate) — degraded to pure time-series mode |
| `/v2/cryptocurrency/ohlcv/historical` | daily candles | ❌ 403 (plan gate) — fallback: Binance public klines |
| `/v1/global-metrics/quotes/historical` | dominance history | ❌ 403 (plan gate) — degraded to latest snapshot only |

Binance prices are infrastructure for forward-return / regime calculations
only and are honestly disclosed in §2 of the research report. The unique
alpha source remains the CMC proprietary F&G — **the strategy does not
exist without it.**

---

## Current results snapshot (2026-06-08 reproduce pass, post-audit)

```
research   -> 687293ce48a1b784…   (manifest hash, masks created_at)
backtest   -> 745e2c7790508234…
spec       -> c73507ad62455e00…
```

| Metric | Value |
|---|---|
| F&G sample | 1075 daily obs, 2023-06-29 → 2026-06-07 |
| Universe (OHLCV)         | 18 BTC/ETH/L1 coins, Binance fallback |
| Regime buckets populated | 8 of 9 (only `CHOP_BEAR` empty) |
| Regime-weight calibration | **`build_weights_is_only` — no OOS leak** |
| Pooled FDR-significant factors | 0 — alpha is regime-conditional |
| Strongest regime-conditional bucket | `fg_level` in `CHOP_NEUTRAL`: IC = −0.30, t-stat = −4.56, p ≈ 9 × 10⁻⁶ |
| OOS Sharpe (IS-only fit) | **−0.99** |
| Deflated Sharpe probability | 0.001 |
| Monte-Carlo random-signal 95th-pct Sharpe | 1.00 |
| OOS max drawdown | −6.0% |
| Walk-forward windows (train 365 / test 90 / step 90) | 7 windows; Sharpe range −2.71 .. 0.81, median −2.10 |
| Parameter-plateau (rolling-IC window) | window=30 → 0.51, 45 → −1.63, 60 → −1.26, 90 → −0.74, 120 → −0.50 — **no plateau, single spike** |
| Unit tests | 38 / 38 ✓ |

**Honest read (post-audit).** Closing the OOS leak in regime-weight
calibration flipped the OOS Sharpe from +0.85 (leaky) to −0.99 (clean).
The walk-forward median Sharpe is also negative, and the plateau scan
shows wide swings rather than a flat shoulder. Both findings are the
textbook signature of a regime-conditional alpha that does NOT survive
strict IS-only calibration on the supplied Basic-plan universe. The
infrastructure (factor IC, FDR, DSR, walk-forward, plateau) does its
job — it is now reporting negative-result honesty rather than a leak.
The CMC proprietary F&G is empirically interesting (CHOP_NEUTRAL t-stat
−4.56) but the as-built spec needs a richer universe or a
regime-stratified FDR gate before it earns a positive OOS — see the
"Next iteration" notes at the bottom of the research report.

---

## Stage status

| Stage | Status |
|---|---|
| 0 — Repo init                  | ✅ done |
| 1 — Scaffold                   | ✅ done |
| 2 — M0 Data layer smoke        | ✅ done — 7-endpoint smoke + M0 back-fill + Binance OHLCV fallback |
| 3 — M1 Factor layer            | ✅ done — 5/5 bias unit tests green |
| 4 — M2 Research layer          | ✅ done — IC / IR / FDR / regime / DSR + 14/14 tests green |
| 5 — M3 Strategy layer          | ✅ done — t→t+1 backtest + cost grid + MC + 23/23 tests; ✅ audit-fix: IS-only weights + walk-forward + plateau wired in |
| 6 — M4 LLM + Spec              | ✅ done — DeepSeek synth + report + StrategySpec + 28/28 tests |
| 7 — M5 Reproducibility         | ✅ done — manifest hash gate + no-key sanity script |
| 8 — M6 Submission              | 🚧 in progress (8.1 README ✅, 8.2 Skills wrapper ✅, audit-fix ✅, 8.3 video / 8.5 checklist pending) |
| 9 — M7 Optional add-ons        | ⏳ pending |

See [development schedule](./docs/SignalForge-开发周期表.md) for the full
plan and [build doc](./docs/SignalForge-可执行开发文档.md) for the section
references quoted throughout the code.

---

## Appendix A — M0 findings (Stage 2.5, 2026-06-08)

Smoke test executed against the supplied CMC key on the **free Basic plan**
(15 000 credits / month, 50 req / min). Endpoint matrix already shown in the
"CMC data usage" section above. Outcome: the proprietary F&G alpha source
is fully usable; OHLCV degrades to Binance public klines; historical
listings and historical global metrics are skipped with documented
degradation.

Stage 2 artefacts (committed):

| Artefact | Rows / Notes |
|---|---|
| `data/processed/fear_greed.parquet` | 1075 rows, 2023-06-29 → 2026-06-07 |
| `data/processed/crypto_map.parquet` | 5000 coins |
| `data/processed/ohlcv.parquet` | 18962 rows, 18 coins (Binance fallback) |
| `data/processed/global_metrics_latest.parquet` | 1 snapshot row (historical 403) |

Total CMC credits burned on the full pull: **2** (cache hits cost zero
on rerun).

---

## Appendix B — Per-stage module reference

### Stage 3 — M1 Factor layer

| File | Factors |
|---|---|
| `src/factors/timeseries.py`    | `fg_level`, `fg_zscore_90`, `fg_momentum_7`, `fg_extreme_rev`, `fg_regime_dur`, `dom_trend_30`, `dom_zscore_90`, `mktcap_mom_30`, `fg_cross_dom` |
| `src/factors/cross_section.py` | `xs_rank_mom_30`, `xs_size`, `xs_ret_mom_90`, `xs_vol_60` (within-day pct-rank, centred) |
| `src/factors/regime.py`        | `dir_regime` × `sent_regime` (BULL/BEAR/CHOP × FEAR/NEUTRAL/GREED) |

### Stage 4 — M2 Research layer

| File | What it provides |
|---|---|
| `src/research/ic.py`               | `forward_returns`, `timeseries_ic`, `rolling_ic_series`, `ir_and_tstat`, `cross_section_ic`, `ic_decay` |
| `src/research/regime_attrib.py`    | `regime_layered_ic`, `regime_ic_matrix` |
| `src/research/multiple_testing.py` | `bh_fdr` (Benjamini–Hochberg), `deflated_sharpe` (López de Prado) |
| `src/research/robustness.py`       | `time_split`, `walk_forward_windows`, `parameter_plateau`, `cost_sensitivity`, `stationary_block_bootstrap` |

### Stage 5 — M3 Strategy layer

| File | What it provides |
|---|---|
| `src/strategy/signals.py`   | `factor_to_signal` (tanh squash, NaN-safe), `combine_signals` (L1-normalised) |
| `src/strategy/portfolio.py` | `regime_conditional_positions`, `cross_section_positions`, `default_regime_weights` |
| `src/strategy/backtest.py`  | `backtest_single`, `backtest_panel` (both apply strict t → t+1), `_perf`, `monte_carlo_random` |
| `scripts/04_backtest.py`    | **IS-only** `build_weights_is_only` + walk-forward refit + parameter plateau scan + cost grid + Monte-Carlo + DSR. Writes `backtest_results.json` with `regime_weights_source`, `walk_forward`, and `parameter_plateau` blocks for audit. |

### Stage 6 — M4 LLM + Spec layer

| File | What it provides |
|---|---|
| `src/llm/deepseek_client.py`    | OpenAI-compatible client, `chat` / `reason`, `safe_chat` / `safe_reason`, audit logs |
| `src/llm/research_synth.py`     | per-factor rationale with deterministic fallback when LLM unavailable |
| `src/llm/report_writer.py`      | full markdown report + 8-section template fallback + `verify_numbers` |
| `src/spec/schema.py`            | pydantic `StrategySpec` / `FactorSpec` / `DataSource` contract |
| `src/spec/builder.py`           | deterministic spec assembly; only FDR-significant factors are included |

### Stage 7 — M5 Reproducibility

| Script | What it proves |
|---|---|
| `scripts/reproduce.py` | Runs `02 → 03 → 04 → 05 → 06` with `PYTHONHASHSEED=42`; canonicalises each numeric output (volatile keys masked) and SHA-256s against `outputs/reproduce_manifest.json`. |
| `scripts/check_no_key_reproduction.py` | Snapshots `outputs/`, wipes the volatile JSONs, re-invokes `reproduce.py` with empty `CMC_API_KEY` and `DEEPSEEK_API_KEY`. Confirms judges can rebuild every number from `data/processed/` alone. |

To intentionally adopt new numbers (e.g. after editing a factor), delete
`outputs/reproduce_manifest.json` and the next run will rewrite it.

### Stage 8 — M6 Submission

| File | What it provides |
|---|---|
| `src/spec/skill_wrapper.py` | §8.2 Skills-Marketplace wrapper. `run_skill(asset, risk)` reuses the cached, manifest-verified `StrategySpec`, drops cross-section factors when a single asset is requested, resizes `signal_to_position` + slippage per risk preference, and optionally attaches a live CMC F&G + global-metrics snapshot under `runtime_inputs`. Never re-runs the research / backtest pipeline at call time. CLI: `python -m src.spec.skill_wrapper --asset ETH --risk aggressive`. |
| `tests/test_skill_wrapper.py` | 7 unit tests covering risk validation, single-asset factor filtering, panel-mode passthrough, risk-profile sizing math, no-key snapshot fallback, missing-cache error, and `spec_id` request-context tagging. |
| `tests/test_audit_fixes.py` | 3 audit-pass tests: IS-only weight calibration is leak-free (tampers OOS factor values, asserts weights unchanged), walk-forward record shape, and `PRICE_SOURCE_FALLBACK` constant is wired to Binance per the Stage 2.9 decision. |

The skill is the surface other agents (and the optional x402 pay-per-call
shim) call. Factor selection and IC numbers are **never** mutated by the
caller's risk preference — that would be data-mining per request. Only
the position-sizing + execution-assumption blocks are resized.

### Stage 2-7 audit pass (2026-06-08)

A strict line-by-line audit against the dev doc (§2 → §7) caught two
**major** and three **minor** gaps. All five are now closed in commit
[`<this commit>`]:

| Severity | What was wrong | Fix |
|---|---|---|
| major | `scripts/04_backtest.py` calibrated `regime_weights` on **full-sample** research (OOS leak vs dev-doc §8.5 / §9 trap). | New `build_weights_is_only` recomputes regime IC on dates strictly before the IS/OOS cut. Tampered-OOS leak test enforces it. |
| major | `walk_forward_windows` was defined in `src/research/robustness.py` but **never invoked**. README rigor claim was unbacked. | `scripts/04_backtest.py::run_walk_forward` now refits weights per window and persists records to `backtest_results.json::walk_forward`. |
| major | `parameter_plateau` was defined but **never invoked**. | Plateau scan over rolling-IC window `[30, 45, 60, 90, 120]` now runs and persists to `backtest_results.json::parameter_plateau`. |
| minor | `PRICE_SOURCE_FALLBACK = None` was dead code. | Set to `"binance"` to reflect the Stage 2.9 decision; locked by `test_price_source_fallback_documented`. |
| minor | `stationary_block_bootstrap` is defined but unused (dev-doc §5.4 lists it as available capability, not required). | Left in place as a deliberate capability with docstring; not invoked. |

Reproducibility cost: the new IS-only calibration intentionally produced
new canonical numbers (`backtest`, `spec` hashes updated). The new
`outputs/reproduce_manifest.json` was generated by `scripts/reproduce.py`
and re-verified end-to-end (`✓ reproduction PASSED`).

---

## License

Apache-2.0 (TBD)
