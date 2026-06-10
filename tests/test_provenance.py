"""Tests for CMC 3-channel provenance recording."""
import pytest
from pathlib import Path


@pytest.fixture
def tmp_provenance(tmp_path, monkeypatch):
    import src.cmc.provenance as prov_mod
    tmp_file = tmp_path / "cmc_provenance.json"
    monkeypatch.setattr(prov_mod, "PROVENANCE_FILE", tmp_file)
    return tmp_file


class TestProvenance:
    def test_record_rest(self, tmp_provenance):
        from src.cmc.provenance import record, load
        record(channel="rest", endpoint="/v3/fear-and-greed/historical",
               description="Historical F&G", credits_used=1)
        entries = load()
        assert len(entries) == 1
        assert entries[0]["channel"] == "rest"

    def test_record_mcp(self, tmp_provenance):
        from src.cmc.provenance import record, load
        record(channel="mcp", endpoint="get_fear_greed_index", description="MCP call")
        assert load()[0]["channel"] == "mcp"

    def test_record_x402_with_tx(self, tmp_provenance):
        from src.cmc.provenance import record, load
        record(channel="x402", endpoint="/v3/fear-and-greed/latest",
               description="x402 snapshot", payment_tx="0xabcdef")
        assert load()[0]["payment_tx"] == "0xabcdef"

    def test_multiple_appended(self, tmp_provenance):
        from src.cmc.provenance import record, load
        record(channel="rest", endpoint="A", description="A")
        record(channel="mcp", endpoint="B", description="B")
        record(channel="x402", endpoint="C", description="C", payment_tx="0xd")
        assert len(load()) == 3

    def test_summary_all_channels(self, tmp_provenance):
        from src.cmc.provenance import record, summary
        record(channel="rest", endpoint="A", description="A")
        record(channel="mcp", endpoint="B", description="B")
        record(channel="x402", endpoint="C", description="C", payment_tx="0xd")
        s = summary()
        assert sorted(s["channels_used"]) == ["mcp", "rest", "x402"]
        assert s["x402_txs"] == ["0xd"]
        assert s["total_calls"] == 3

    def test_empty_returns_empty(self, tmp_provenance):
        from src.cmc.provenance import load
        assert load() == []

    def test_required_fields(self, tmp_provenance):
        from src.cmc.provenance import record, load
        record(channel="rest", endpoint="/t", description="d")
        e = load()[0]
        for f in ["timestamp_utc", "channel", "endpoint", "description"]:
            assert f in e
