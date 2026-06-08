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

from src.llm.deepseek_client import chat

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
    return chat(SYSTEM, user, temperature=0.5, tag="report")


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
