"""Unit tests for src/spec/skill_wrapper.py (dev doc §8.2).

The skill MUST be deterministic and offline-friendly:
  * never re-run the research / backtest pipeline at call time;
  * never overwrite cached pipeline numbers with live snapshots;
  * never call the network when no CMC key is configured.

Live CMC fetches are stubbed out via monkeypatch so the test suite stays
green for judges who reproduce with empty env (Stage 7 / M5).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.spec import skill_wrapper as sw


@pytest.fixture()
def cached_spec(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """Write a minimal cached spec into a temp outputs/ tree and point
    settings.outputs_dir at it."""
    spec = {
        "spec_version": "1.0",
        "spec_id": "signalforge-cmc-fg-regime-v1",
        "name": "Test Spec",
        "created_at": "2026-01-01T00:00:00+00:00",
        "description": "test",
        "data_sources": [
            {"provider": "CoinMarketCap",
             "endpoint": "/v3/fear-and-greed/historical",
             "field": "value", "is_proprietary": True}
        ],
        "universe": {"selection": "top_N_by_market_cap", "N": 100},
        "factors": [
            {"id": "fg_extreme_rev", "definition": "x",
             "type": "timeseries", "rank_ic": 0.08,
             "ir": 0.41, "t_stat": 3.1, "fdr_significant": True,
             "rationale": "r"},
            {"id": "xs_size", "definition": "y",
             "type": "cross_section", "rank_ic": 0.05,
             "ir": 0.30, "t_stat": 2.4, "fdr_significant": True,
             "rationale": "r2"},
        ],
        "regime": {"definition": {}, "factor_weights_by_regime": {}},
        "signal_to_position": {
            "method": "IR-weighted",
            "max_asset_weight": 0.30,
            "max_gross_leverage": 1.0,
            "rebalance_frequency": "daily",
        },
        "execution_assumptions": {
            "signal_to_trade_lag_days": 1,
            "fee_bps": 10,
            "slippage_bps_by_size": {
                "large_cap": 5, "mid_cap": 10, "small_cap": 20
            },
        },
        "backtest_window": {"in_sample_to_oos_cut": "2025-01-01"},
        "reported_performance": {},
        "reproducibility": {"seed": 42},
    }
    (tmp_path / "specs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "specs" / "signalforge-cmc-fg-regime-v1.json").write_text(
        json.dumps(spec)
    )
    monkeypatch.setattr(sw.settings, "outputs_dir", str(tmp_path))
    # Force no-key path so no network ever fires.
    monkeypatch.setattr(sw.settings, "cmc_api_key", "")
    return spec


def test_unknown_risk_rejected(cached_spec: dict) -> None:
    with pytest.raises(ValueError, match="unknown risk preference"):
        sw.run_skill(asset="BTC", risk="yolo")


def test_single_asset_drops_cross_section(cached_spec: dict) -> None:
    out = sw.run_skill(asset="BTC", risk="moderate")
    ids = [f["id"] for f in out["factors"]]
    assert "fg_extreme_rev" in ids
    assert "xs_size" not in ids, "cross-section factor must be dropped"
    assert out["skill_inputs"] == {
        "asset": "BTC",
        "risk": "moderate",
        "source_spec_id": "signalforge-cmc-fg-regime-v1",
    }


def test_panel_keeps_cross_section(cached_spec: dict) -> None:
    out = sw.run_skill(asset="PANEL", risk="moderate")
    ids = [f["id"] for f in out["factors"]]
    assert {"fg_extreme_rev", "xs_size"}.issubset(set(ids))


def test_risk_profile_scales_position_block(cached_spec: dict) -> None:
    cons = sw.run_skill(asset="BTC", risk="conservative")
    agg = sw.run_skill(asset="BTC", risk="aggressive")
    assert cons["signal_to_position"]["max_gross_leverage"] == 0.5
    assert agg["signal_to_position"]["max_gross_leverage"] == 1.5
    assert cons["signal_to_position"]["max_asset_weight"] == 0.15
    assert agg["signal_to_position"]["max_asset_weight"] == 0.50
    # Conservative scales slippage up 1.5x; aggressive leaves it as-is.
    assert cons["execution_assumptions"]["slippage_bps_by_size"][
        "large_cap"
    ] == 8  # round(5 * 1.5) = 8
    assert agg["execution_assumptions"]["slippage_bps_by_size"][
        "large_cap"
    ] == 5


def test_no_key_yields_none_snapshot(cached_spec: dict) -> None:
    out = sw.run_skill(asset="ETH", risk="moderate")
    assert out["runtime_inputs"]["cmc_snapshot"] is None
    assert "CMC_API_KEY" in out["runtime_inputs"]["snapshot_note"]


def test_missing_cache_raises(tmp_path: Path,
                              monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sw.settings, "outputs_dir", str(tmp_path))
    monkeypatch.setattr(sw.settings, "cmc_api_key", "")
    with pytest.raises(FileNotFoundError, match="cached spec missing"):
        sw.run_skill(asset="BTC", risk="moderate")


def test_spec_id_carries_request_context(cached_spec: dict) -> None:
    out = sw.run_skill(asset="eth", risk="aggressive")
    assert out["spec_id"].endswith("::ETH::aggressive")
