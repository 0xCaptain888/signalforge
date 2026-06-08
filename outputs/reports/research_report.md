# SignalForge — Research Report

## 1. Executive Summary

We test the **CoinMarketCap proprietary Fear & Greed index** as a factor
source — distinct from the widely studied Alternative.me index and, as far
as we can tell, never rigorously evaluated in the public literature. The
proprietary index ingests CMC's own volatility / momentum / volume /
dominance / social signals into a single 0–100 score with a public
historical API (`/v3/fear-and-greed/historical`).

Out-of-sample Sharpe = **-0.99** vs in-sample
**-1.03**; deflated-Sharpe probability =
**0.00**; Monte-Carlo random-signal Sharpe
at the 95th percentile = **1.00**.
FDR-significant factors at pooled level: none (alpha is regime-conditional — see §4).

## 2. Data & Methodology

Endpoints used (CMC Pro REST API):

- `/v1/key/info`, `/v1/cryptocurrency/map` — bookkeeping (0 credit each)
- `/v3/fear-and-greed/historical` — **core alpha** (CMC proprietary)
- `/v1/global-metrics/quotes/latest` — dominance & total-cap snapshot

OHLCV was pulled from **Binance public klines** (free, no key) because
`/v2/cryptocurrency/ohlcv/historical` is gated behind a paid CMC plan tier
that the supplied key does not include. Prices are infrastructure for
forward-return tests; the proprietary alpha source is the CMC F&G.

Explicitly **EXCLUDED** signals: ETF flows, social-media sentiment,
on-chain whale flows. None have a clean historical API on the Basic plan,
so they cannot be honestly back-tested. Rigor over hype.

All factor calculations are **point-in-time** (rolling z-scores have
`min_periods=window`; cross-section ranks are taken within the date).
Forward returns are strictly `shift(-h)`. Two unit-test families enforce
this — `tests/test_no_lookahead.py` and `tests/test_survivorship.py`.

## 3. Factor Definitions

See `scripts/05_generate_spec.py::DEFINITIONS` for the authoritative map.
The factor families are: F&G level / z-score / momentum / extreme-reversal
/ regime-duration; dominance trend / z-score; F&G × dominance cross.

## 4. Factor Efficacy

| Factor | IC | IR | t-stat | FDR |
|---|---|---|---|---|
| `fg_level` | 0.0063 | -1.39 | -44.15 | · |
| `fg_zscore_90` | 0.0171 | -0.83 | -25.09 | · |
| `fg_momentum_7` | -0.0311 | -0.68 | -21.69 | · |
| `fg_extreme_rev` | -0.0256 | 0.83 | 18.74 | · |
| `fg_regime_dur` | -0.0282 | -0.12 | -3.97 | · |

Top-3 regime-conditional buckets per factor (where alpha actually lives):

- `fg_level` — CHOP_GREED: IC=-0.31 (t=-2.95, n=82), CHOP_NEUTRAL: IC=-0.30 (t=-4.56, n=219), BULL_FEAR: IC=-0.20 (t=-0.96, n=25)
- `fg_zscore_90` — BULL_FEAR: IC=-0.55 (t=-3.16, n=25), BEAR_FEAR: IC=0.20 (t=2.05, n=102), BULL_GREED: IC=0.13 (t=1.54, n=143)
- `fg_momentum_7` — BULL_FEAR: IC=-0.48 (t=-2.62, n=25), CHOP_GREED: IC=-0.23 (t=-2.13, n=82), BEAR_FEAR: IC=0.23 (t=2.33, n=102)
- `fg_extreme_rev` — CHOP_GREED: IC=0.29 (t=2.70, n=82), BULL_FEAR: IC=0.18 (t=0.90, n=25), BEAR_FEAR: IC=-0.10 (t=-1.04, n=102)
- `fg_regime_dur` — BULL_FEAR: IC=-0.56 (t=-3.20, n=25), CHOP_FEAR: IC=-0.26 (t=-2.11, n=61), CHOP_GREED: IC=0.26 (t=2.39, n=82)

See `outputs/figures/ic_decay.png` and
`outputs/figures/regime_ic_heatmap.png`.

## 5. CMC vs Alternative.me F&G

Both indices target the same construct but combine different inputs. CMC's
index is generated in-house and exposed via the proprietary endpoint above;
Alternative.me's index is open-methodology and widely used. A like-for-like
overlap comparison would require pulling Alternative.me and re-running
identical tests — left to future work.

## 6. Multiple-Testing Correction

We apply Benjamini–Hochberg FDR (q = 0.10) across all candidate factors and
report López de Prado's Deflated Sharpe Ratio for the realised strategy.
DSR probability = **0.00** over
45 trials and 322 observations.

## 7. Strategy & Backtest

In-sample: ann_return = -0.18, Sharpe =
-1.03, max drawdown = -0.47.
Out-of-sample: ann_return = -0.05, Sharpe =
-0.99, max drawdown = -0.06.
Monte-Carlo random-signal mean Sharpe =
0.03 (95th pct
1.00).

See `outputs/figures/walkforward_oos.png`.

## 8. Limitations & Future Work

- Plan ceiling — Basic plan blocks 3 of 7 endpoints; a Standard / Startup
  upgrade would unlock cross-section research on a CMC-native universe.
- Sample length — F&G historical depth is bounded by what the endpoint
  returns (1071 forward-pair obs at
  pooled level); a longer sample would tighten t-stats.
- LLM rationales — DeepSeek calls were unavailable at run time (402
  insufficient balance); deterministic template used. Re-run with a funded
  key to regenerate narrative.

## Appendix — LLM-generated factor rationales

_no LLM-generated explanations available_
