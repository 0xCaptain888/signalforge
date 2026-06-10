"""Tests for edge_confidence() (6 rules, baseline 59) and verdict_from_score()."""

import pytest
from src.adjudicator.scoring import edge_confidence, verdict_from_score, verify_v1_score


class TestEdgeConfidence:
    def test_v1_real_scores_exactly_12(self, v1_stats):
        r = edge_confidence(
            {
                "dsr_probability": v1_stats["dsr_probability"],
                "fdr_significant_factors": v1_stats["fdr_significant_factors"],
                "walk_forward_median_sharpe": v1_stats["walk_forward_median_sharpe"],
                "parameter_plateau": v1_stats["parameter_plateau"],
                "lookahead_test": v1_stats["lookahead_test"],
                "strongest_t_stat": v1_stats["strongest_t_stat"],
            }
        )
        assert r.score == 12, f"Expected exactly 12, got {r.score} ({r.breakdown})"

    def test_verify_v1_score_helper(self):
        assert verify_v1_score() is True

    def test_strong_stats_high_score(self, strong_stats):
        r = edge_confidence(strong_stats)
        assert r.score >= 75, f"Expected >=75, got {r.score}"

    def test_score_clamp_min(self):
        r = edge_confidence(
            {
                "dsr_probability": 0.0,
                "fdr_significant_factors": 0,
                "walk_forward_median_sharpe": -5.0,
                "parameter_plateau": "spike",
                "lookahead_test": "FAIL",
                "strongest_t_stat": 0,
            }
        )
        assert r.score >= 0

    def test_score_clamp_max(self):
        r = edge_confidence(
            {
                "dsr_probability": 1.0,
                "fdr_significant_factors": 10,
                "walk_forward_median_sharpe": 3.0,
                "parameter_plateau": "plateau",
                "lookahead_test": "PASS",
                "strongest_t_stat": 10,
            }
        )
        assert r.score <= 100

    def test_deterministic(self, v1_stats):
        r1 = edge_confidence(v1_stats)
        r2 = edge_confidence(v1_stats)
        assert r1.score == r2.score and r1.reasons == r2.reasons

    def test_rule5_lookahead_fail_penalizes_30(self):
        # Use values that don't hit the 100 cap, so the -30 penalty is exact
        base = {
            "dsr_probability": 0.80,
            "fdr_significant_factors": 2,
            "walk_forward_median_sharpe": 0.0,
            "parameter_plateau": "plateau",
            "strongest_t_stat": 0,
        }
        r_pass = edge_confidence({**base, "lookahead_test": "PASS"})
        r_fail = edge_confidence({**base, "lookahead_test": "FAIL"})
        assert r_pass.score - r_fail.score == 30

    def test_plateau_vs_spike_20pt_swing(self):
        base = {
            "dsr_probability": 0.50,
            "fdr_significant_factors": 1,
            "walk_forward_median_sharpe": 0.5,
            "lookahead_test": "PASS",
            "strongest_t_stat": 0,
        }
        plat = edge_confidence({**base, "parameter_plateau": "plateau"})
        spike = edge_confidence({**base, "parameter_plateau": "spike"})
        assert plat.score - spike.score == 20

    def test_rule6_regime_tstat_bands(self):
        base = {
            "dsr_probability": 0.50,
            "fdr_significant_factors": 0,
            "walk_forward_median_sharpe": 0.0,
            "parameter_plateau": "spike",
            "lookahead_test": "PASS",
        }
        high = edge_confidence({**base, "strongest_t_stat": 4.5})
        mid = edge_confidence({**base, "strongest_t_stat": 2.5})
        low = edge_confidence({**base, "strongest_t_stat": 1.0})
        assert high.breakdown["rule6_regime"] == 15
        assert mid.breakdown["rule6_regime"] == 8
        assert low.breakdown["rule6_regime"] == 0

    def test_rule6_handles_none(self):
        r = edge_confidence(
            {
                "dsr_probability": 0.5,
                "fdr_significant_factors": 0,
                "walk_forward_median_sharpe": 0.0,
                "parameter_plateau": "spike",
                "lookahead_test": "PASS",
                "strongest_t_stat": None,
            }
        )
        assert r.breakdown["rule6_regime"] == 0

    def test_breakdown_keys(self, v1_stats):
        r = edge_confidence(v1_stats)
        for k in [
            "rule1_dsr",
            "rule2_fdr",
            "rule3_walkforward",
            "rule4_plateau",
            "rule5_lookahead",
            "rule6_regime",
        ]:
            assert k in r.breakdown

    def test_reasons_count_six(self, v1_stats):
        r = edge_confidence(v1_stats)
        assert len(r.reasons) == 6  # one reason per rule


class TestVerdictFromScore:
    def test_strong_accept(self):
        assert verdict_from_score(75, False) == "STRONG_ACCEPT"
        assert verdict_from_score(100, False) == "STRONG_ACCEPT"

    def test_accept(self):
        assert verdict_from_score(60, False) == "ACCEPT"
        assert verdict_from_score(74, False) == "ACCEPT"

    def test_weak(self):
        assert verdict_from_score(40, False) == "WEAK"
        assert verdict_from_score(59, False) == "WEAK"

    def test_reject(self):
        assert verdict_from_score(0, False) == "REJECT"
        assert verdict_from_score(39, False) == "REJECT"

    def test_leakage_overrides_score(self):
        assert verdict_from_score(80, True) == "LEAKAGE_DETECTED"
        assert verdict_from_score(0, True) == "LEAKAGE_DETECTED"

    def test_boundaries(self):
        assert verdict_from_score(74, False) == "ACCEPT"
        assert verdict_from_score(75, False) == "STRONG_ACCEPT"
        assert verdict_from_score(59, False) == "WEAK"
        assert verdict_from_score(60, False) == "ACCEPT"
        assert verdict_from_score(39, False) == "REJECT"
        assert verdict_from_score(40, False) == "WEAK"
