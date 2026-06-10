"""Tests for detect_leakage()."""
import pytest
from src.adjudicator.leakage import detect_leakage, SCENARIO_V1_REAL, SCENARIO_CLEAN


class TestDetectLeakage:
    def test_v1_real_scenario_detected(self, leakage_scenario):
        r = detect_leakage(**leakage_scenario)
        assert r["leaked"] is True
        assert r["gap"] == pytest.approx(1.84, abs=0.01)
        assert r["direction_flip_detected"] is True

    def test_clean_scenario_not_leaked(self, clean_scenario):
        r = detect_leakage(**clean_scenario)
        assert r["leaked"] is False
        assert r["gap"] < 0.80

    def test_lookahead_fail_flagged(self):
        r = detect_leakage(naive_sharpe=0.50, honest_sharpe=0.45,
                           lookahead_test_result="FAIL")
        assert r["lookahead_flag"] is True
        assert r["lookahead_test"] == "FAIL"

    def test_gap_below_threshold_not_leaked(self):
        r = detect_leakage(naive_sharpe=0.90, honest_sharpe=0.20)  # gap 0.70
        assert r["leaked"] is False

    def test_both_negative_not_leaked(self):
        r = detect_leakage(naive_sharpe=-0.10, honest_sharpe=-0.99)
        assert r["leaked"] is False
        assert r["direction_flip_detected"] is False

    def test_naive_negative_not_leaked(self):
        r = detect_leakage(naive_sharpe=-0.20, honest_sharpe=-1.50)
        assert r["leaked"] is False

    def test_output_fields_complete(self, leakage_scenario):
        r = detect_leakage(**leakage_scenario)
        for field in ["lookahead_test", "is_only_calibration", "naive_sharpe_if_leaked",
                      "honest_sharpe", "gap", "threshold", "direction_flip_detected",
                      "lookahead_flag", "leaked"]:
            assert field in r, f"Missing: {field}"

    def test_preset_v1_real(self):
        assert detect_leakage(**SCENARIO_V1_REAL)["leaked"] is True

    def test_preset_clean(self):
        assert detect_leakage(**SCENARIO_CLEAN)["leaked"] is False

    def test_deterministic(self, leakage_scenario):
        assert detect_leakage(**leakage_scenario) == detect_leakage(**leakage_scenario)

    def test_custom_threshold(self):
        r = detect_leakage(naive_sharpe=0.80, honest_sharpe=-0.10, threshold=0.50)
        assert r["leaked"] is True

    def test_rounding(self):
        r = detect_leakage(naive_sharpe=0.123456789, honest_sharpe=-0.987654321)
        assert r["naive_sharpe_if_leaked"] == pytest.approx(0.1235, abs=0.0001)
