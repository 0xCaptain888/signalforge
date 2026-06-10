"""
detect_leakage() — compares leaky vs IS-only calibration to detect data leakage.

Core logic:
- Naive calibration: regime_weights fitted on FULL sample (v1 early bug)
- IS-only calibration: weights fitted on IS period only, OOS strictly isolated
- Sharpe gap > threshold AND direction flip => leakage detected

v1 real case: naive=+0.85, honest=-0.99, gap=1.84 -> LEAKAGE_DETECTED  (verified)
"""
from __future__ import annotations


def detect_leakage(
    naive_sharpe: float,
    honest_sharpe: float,
    lookahead_test_result: str = "PASS",
    threshold: float = 0.80,
) -> dict:
    """
    Determine whether the backtest exhibits data leakage.

    Args:
        naive_sharpe: OOS Sharpe under leaky (full-sample) calibration
        honest_sharpe: OOS Sharpe under IS-only calibration (the truth)
        lookahead_test_result: unit-test look-ahead check (PASS / FAIL)
        threshold: Sharpe-gap threshold for the leakage verdict

    Returns:
        dict with `leaked` flag and all supporting fields
    """
    gap = naive_sharpe - honest_sharpe

    # Leakage rule: naive looks positive (inflated) but honest reveals <= 0
    direction_flip = naive_sharpe > 0 and honest_sharpe <= 0
    leaked = gap > threshold and direction_flip

    # Failed look-ahead test is a leakage *indicator* (does not alone flip verdict)
    lookahead_flag = lookahead_test_result != "PASS"

    return {
        "lookahead_test": lookahead_test_result,
        "is_only_calibration": "ENFORCED",
        "naive_sharpe_if_leaked": round(naive_sharpe, 4),
        "honest_sharpe": round(honest_sharpe, 4),
        "gap": round(gap, 4),
        "threshold": threshold,
        "direction_flip_detected": direction_flip,
        "lookahead_flag": lookahead_flag,
        "leaked": leaked,
    }


# -- Preset scenarios (for demos and tests) ---------------------------------
SCENARIO_V1_REAL = dict(
    naive_sharpe=0.85,
    honest_sharpe=-0.99,
    lookahead_test_result="PASS",
    threshold=0.80,
)

SCENARIO_CLEAN = dict(
    naive_sharpe=0.72,
    honest_sharpe=0.68,
    lookahead_test_result="PASS",
    threshold=0.80,
)

SCENARIO_WEAK = dict(
    naive_sharpe=0.30,
    honest_sharpe=-0.10,
    lookahead_test_result="PASS",
    threshold=0.80,
)
