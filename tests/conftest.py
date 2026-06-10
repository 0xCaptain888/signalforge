"""Shared pytest fixtures for SignalForge v2 tests."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


@pytest.fixture
def v1_stats():
    """v1 real statistics (matches _demo_results in core.py)."""
    return {
        "dsr_probability": 0.001,
        "fdr_significant_factors": 0,
        "lookahead_test": "PASS",
        "oos_sharpe_is_only": -0.99,
        "oos_max_drawdown": -0.06,
        "naive_sharpe_before_audit": 0.85,
        "walk_forward_median_sharpe": -2.10,
        "walk_forward_windows": 7,
        "parameter_plateau": "spike",
        "strongest_regime_bucket": "CHOP_NEUTRAL",
        "strongest_ic": -0.30,
        "strongest_t_stat": -4.56,
    }


@pytest.fixture
def strong_stats():
    """Strong-alpha stats (for STRONG_ACCEPT paths)."""
    return {
        "dsr_probability": 0.98,
        "fdr_significant_factors": 4,
        "lookahead_test": "PASS",
        "walk_forward_median_sharpe": 1.20,
        "parameter_plateau": "plateau",
        "strongest_t_stat": 5.0,
    }


@pytest.fixture
def leakage_scenario():
    return dict(naive_sharpe=0.85, honest_sharpe=-0.99)


@pytest.fixture
def clean_scenario():
    return dict(naive_sharpe=0.72, honest_sharpe=0.68)


@pytest.fixture
def sample_adjudication_request():
    return {
        "asset": "ETH",
        "candidate_signal": {
            "name": "cmc_fg_test",
            "source": "cmc_fear_greed",
            "definition": "fg < 20 -> long",
            "holding_period_days": 5,
        },
        "risk": "balanced",
    }
