"""Tests for adjudicate() main entry — determinism, schema, v1 consistency."""
import pytest
from src.adjudicator.core import adjudicate, adjudicate_preset_leakage, adjudicate_preset_honest
from src.adjudicator.schema import Verdict

SAMPLE_SIGNAL = {
    "name": "test_fg_signal",
    "source": "cmc_fear_greed",
    "definition": "fg < 20 -> long",
    "holding_period_days": 5,
}


class TestAdjudicate:
    def test_returns_valid_schema(self):
        result = adjudicate(asset="ETH", candidate_signal=SAMPLE_SIGNAL,
                            include_cmc_snapshot=False)
        verdict = Verdict(**result)  # must not raise
        assert 0 <= verdict.edge_confidence <= 100

    def test_deterministic_same_input(self):
        r1 = adjudicate(asset="ETH", candidate_signal=SAMPLE_SIGNAL,
                        include_cmc_snapshot=False)
        r2 = adjudicate(asset="ETH", candidate_signal=SAMPLE_SIGNAL,
                        include_cmc_snapshot=False)
        assert r1["verdict"] == r2["verdict"]
        assert r1["edge_confidence"] == r2["edge_confidence"]
        assert r1["leakage_check"]["leaked"] == r2["leakage_check"]["leaked"]

    def test_v1_real_data_verdict(self):
        r = adjudicate_preset_leakage()
        assert r["verdict"] in ("REJECT", "LEAKAGE_DETECTED")
        assert r["edge_confidence"] < 40

    def test_v1_edge_confidence_is_12(self):
        r = adjudicate_preset_leakage()
        assert r["edge_confidence"] == 12

    def test_leakage_detected_for_v1_data(self):
        r = adjudicate_preset_leakage()
        assert r["leakage_check"]["leaked"] is True
        assert r["verdict"] == "LEAKAGE_DETECTED"

    def test_naive_vs_honest_sharpe(self):
        r = adjudicate_preset_leakage()
        lc = r["leakage_check"]
        assert lc["naive_sharpe_if_leaked"] > lc["honest_sharpe"]

    def test_output_fields_complete(self):
        r = adjudicate(asset="ETH", candidate_signal=SAMPLE_SIGNAL,
                       include_cmc_snapshot=False)
        for field in ["verdict", "edge_confidence", "reasons", "verdict_summary",
                      "leakage_check", "statistics", "strategy_spec_ref", "spec_id",
                      "cmc_data_provenance", "billing", "meta"]:
            assert field in r, f"Missing: {field}"

    def test_reasons_are_strings(self):
        r = adjudicate(asset="ETH", candidate_signal=SAMPLE_SIGNAL,
                       include_cmc_snapshot=False)
        assert isinstance(r["reasons"], list)
        assert all(isinstance(x, str) and x for x in r["reasons"])

    def test_leakage_check_fields(self):
        r = adjudicate(asset="ETH", candidate_signal=SAMPLE_SIGNAL,
                       include_cmc_snapshot=False)
        lc = r["leakage_check"]
        for f in ["leaked", "naive_sharpe_if_leaked", "honest_sharpe", "gap",
                  "direction_flip_detected", "lookahead_flag"]:
            assert f in lc
        assert isinstance(lc["leaked"], bool)

    def test_meta_reproducible(self):
        r = adjudicate(asset="ETH", candidate_signal=SAMPLE_SIGNAL,
                       include_cmc_snapshot=False)
        assert r["meta"]["reproducible"] is True
        assert r["meta"]["seed"] == 42

    def test_no_api_key_still_works(self, monkeypatch):
        """Zero-key mode works (P2-8: monkeypatch, thread-safe)."""
        monkeypatch.delenv("CMC_API_KEY", raising=False)
        r = adjudicate(asset="ETH", candidate_signal=SAMPLE_SIGNAL,
                       include_cmc_snapshot=False)
        assert "verdict" in r

    def test_edge_confidence_in_range(self):
        r = adjudicate_preset_leakage()
        assert 0 <= r["edge_confidence"] <= 100

    def test_cmc_provenance_channels(self):
        r = adjudicate(asset="ETH", candidate_signal=SAMPLE_SIGNAL,
                       include_cmc_snapshot=False)
        prov = r["cmc_data_provenance"]
        assert isinstance(prov["access_channels_used"], list)
        assert len(prov["access_channels_used"]) >= 1
        assert prov["historical_channels_documented"] == ["rest", "mcp", "x402"]

    def test_honest_preset_works(self):
        r = adjudicate_preset_honest()
        assert "verdict" in r
