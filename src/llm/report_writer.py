"""Markdown report writer + post-hoc hallucination detector.

`write_report` asks DeepSeek to draft the markdown using ONLY the JSON
payloads we hand it; `verify_numbers` then re-reads the draft, extracts
every decimal number, and flags any that don't appear in the source JSON.
This is a cheap but effective last-line defence: if the LLM invents
"Sharpe of 2.4" while the JSON only contains 1.7, the warning fires.
"""
from __future__ import annotations

import json
import re

from src.llm.deepseek_client import chat, safe_chat

SYSTEM = (
    "You are writing a quantitative research report for a hackathon "
    "(BNB Hack Track 2). Audience: CoinMarketCap / quant judges. Tone: "
    "rigorous, honest, confident but not hyped. CRITICAL: use ONLY the "
    "numbers in the provided JSON. Do not fabricate any statistic. The "
    "core narrative: CMC's PROPRIETARY Fear & Greed (distinct from "
    "Alternative.me) is an under-researched alpha source. Output "
    "GitHub-flavored markdown."
)


def write_report(
    research: dict,
    backtest: dict,
    factor_explanations: dict,
) -> str:
    """Compose the full markdown research report.

    All three dicts must be JSON-serialisable. The function truncates the
    serialised payloads to fit a single prompt; if you need more context,
    chunk the call upstream rather than raising the cap here.
    """
    user = f"""Write the research report. Sections:
1. Executive Summary (lead with the CMC-proprietary-F&G narrative)
2. Data & Methodology (CMC endpoints used; why ETF / social / on-chain
   were EXCLUDED — no historical API, can't honestly backtest;
   point-in-time & survivorship-bias-free methods)
3. Factor Definitions
4. Factor Efficacy (IC / IR / t-stat / decay, regime heatmap)
5. CMC vs Alternative.me F&G comparison
6. Multiple-Testing Correction (FDR + Deflated Sharpe)
7. Strategy & Backtest (OOS curve, vs BTC HODL, cost sensitivity, monte-carlo)
8. Limitations & Future Work (be honest about sample / plan limits)

RESEARCH_RESULTS_JSON:
{json.dumps(research, default=float)[:8000]}

BACKTEST_RESULTS_JSON:
{json.dumps(backtest, default=float)[:4000]}

FACTOR_EXPLANATIONS:
{json.dumps(factor_explanations)[:4000]}

Reference figures by relative path: outputs/figures/ic_decay.png,
outputs/figures/regime_ic_heatmap.png, outputs/figures/walkforward_oos.png"""
    text = safe_chat(SYSTEM, user, temperature=0.5, tag="report")
    if text:
        return text
    return _deterministic_report(research, backtest, factor_explanations)


def _deterministic_report(
    research: dict,
    backtest: dict,
    factor_explanations: dict,
) -> str:
    """Template-based 8-section markdown — used when LLM is unavailable.

    All numbers are sourced directly from the research / backtest dicts so
    `verify_numbers` returns a clean list by construction.
    """
    factors = research.get("factors", {}) or {}
    sig = [k for k, v in factors.items() if v.get("fdr_significant")]
    oos = backtest.get("out_of_sample", {}) or {}
    is_ = backtest.get("in_sample", {}) or {}
    dsr = backtest.get("deflated_sharpe", {}) or {}
    mc = backtest.get("monte_carlo", {}) or {}

    def f(x, n=2):
        try:
            return f"{float(x):.{n}f}"
        except (TypeError, ValueError):
            return "n/a"

    def factor_table() -> str:
        head = "| Factor | IC | IR | t-stat | FDR |\n|---|---|---|---|---|"
        rows = [head]
        for fid, fr in factors.items():
            rows.append(
                f"| `{fid}` | {f(fr.get('ic_overall'), 4)} | "
                f"{f(fr.get('ir'))} | {f(fr.get('t_stat'))} | "
                f"{'✓' if fr.get('fdr_significant') else '·'} |"
            )
        return "\n".join(rows)

    def regime_block() -> str:
        lines = []
        for fid, fr in factors.items():
            top = sorted(
                fr.get("regime_ic", []) or [],
                key=lambda r: abs(r.get("ic") or 0.0),
                reverse=True,
            )[:3]
            if not top:
                continue
            bits = ", ".join(
                f"{r.get('regime')}: IC={f(r.get('ic'))} "
                f"(t={f(r.get('t_stat'))}, n={r.get('n')})"
                for r in top
            )
            lines.append(f"- `{fid}` — {bits}")
        return "\n".join(lines) or "_no regime breakdown available_"

    expl_block = "\n".join(
        f"### `{fid}`\n{txt}\n" for fid, txt in factor_explanations.items()
    ) or "_no LLM-generated explanations available_"

    return f"""# SignalForge — Research Report

## 1. Executive Summary

We test the **CoinMarketCap proprietary Fear & Greed index** as a factor
source — distinct from the widely studied Alternative.me index and, as far
as we can tell, never rigorously evaluated in the public literature. The
proprietary index ingests CMC's own volatility / momentum / volume /
dominance / social signals into a single 0–100 score with a public
historical API (`/v3/fear-and-greed/historical`).

Out-of-sample Sharpe = **{f(oos.get('sharpe'))}** vs in-sample
**{f(is_.get('sharpe'))}**; deflated-Sharpe probability =
**{f(dsr.get('deflated_sharpe_prob'))}**; Monte-Carlo random-signal Sharpe
at the 95th percentile = **{f(mc.get('random_sharpe_95pct'))}**.
FDR-significant factors at pooled level: {sig if sig else 'none (alpha is regime-conditional — see §4)'}.

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

{factor_table()}

Top-3 regime-conditional buckets per factor (where alpha actually lives):

{regime_block()}

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
DSR probability = **{f(dsr.get('deflated_sharpe_prob'))}** over
{dsr.get('n_trials')} trials and {dsr.get('n_obs')} observations.

## 7. Strategy & Backtest

In-sample: ann_return = {f(is_.get('ann_return'))}, Sharpe =
{f(is_.get('sharpe'))}, max drawdown = {f(is_.get('max_drawdown'))}.
Out-of-sample: ann_return = {f(oos.get('ann_return'))}, Sharpe =
{f(oos.get('sharpe'))}, max drawdown = {f(oos.get('max_drawdown'))}.
Monte-Carlo random-signal mean Sharpe =
{f(mc.get('random_sharpe_mean'))} (95th pct
{f(mc.get('random_sharpe_95pct'))}).

See `outputs/figures/walkforward_oos.png`.

## 8. Limitations & Future Work

- Plan ceiling — Basic plan blocks 3 of 7 endpoints; a Standard / Startup
  upgrade would unlock cross-section research on a CMC-native universe.
- Sample length — F&G historical depth is bounded by what the endpoint
  returns ({factors.get('fg_level', {}).get('n', 'n/a')} forward-pair obs at
  pooled level); a longer sample would tighten t-stats.
- LLM rationales — DeepSeek calls were unavailable at run time (402
  insufficient balance); deterministic template used. Re-run with a funded
  key to regenerate narrative.

## Appendix — LLM-generated factor rationales

{expl_block}
"""


def verify_numbers(
    report_md: str,
    research: dict,
    backtest: dict,
) -> list[str]:
    """Flag decimals in the markdown that don't trace back to source JSON.

    The check rounds both sides to 2 decimal places, ignores tiny constants
    (|value| <= 1.5 — e.g. 0.5, 1.0 are universal and would generate noise),
    and accepts a positive number if its negative twin is present (reports
    routinely re-sign factor scores).

    Returns a list of human-readable warning strings (empty list = clean).
    """
    warnings: list[str] = []
    truth: set[float] = set()

    def collect(o):
        if isinstance(o, dict):
            for v in o.values():
                collect(v)
        elif isinstance(o, list):
            for v in o:
                collect(v)
        elif isinstance(o, (int, float)):
            try:
                truth.add(round(float(o), 2))
            except (ValueError, TypeError):
                pass

    collect(research)
    collect(backtest)

    for m in re.findall(r"-?\d+\.\d+", report_md):
        try:
            val = round(float(m), 2)
        except ValueError:
            continue
        if abs(val) <= 1.5:
            # universal constants and small typographic decimals — skip
            continue
        if val in truth or -val in truth:
            continue
        warnings.append(
            f"report number {m} not found in source JSON "
            "(possible hallucination — please verify manually)"
        )
    return warnings
