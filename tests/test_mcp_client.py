"""CMC MCP client tests (mock mode, no real API key needed)."""
import pytest
from unittest.mock import patch, MagicMock
from src.cmc.mcp_client import CMCMCPClient


class TestCMCMCPClientFallback:
    def test_discover_tools_hardcoded_fallback(self):
        client = CMCMCPClient(api_key="")
        with patch("httpx.post", side_effect=ConnectionError("no network")):
            tools = client.discover_tools()
        assert len(tools) == 12

    def test_known_tools_has_fear_greed(self):
        assert "get_fear_greed_index" in CMCMCPClient.KNOWN_TOOLS

    def test_known_tools_count_is_12(self):
        assert len(CMCMCPClient.KNOWN_TOOLS) == 12

    def test_list_tool_names_strings(self):
        client = CMCMCPClient()
        with patch("httpx.post", side_effect=Exception("offline")):
            names = client.list_tool_names()
        assert all(isinstance(n, str) for n in names)
        assert len(names) == 12


class TestCMCMCPClientSuccess:
    def _tools_resp(self, names):
        m = MagicMock()
        m.json.return_value = {"result": {"tools": [{"name": n, "description": n} for n in names]}}
        m.raise_for_status = MagicMock()
        return m

    def _content_resp(self, text):
        m = MagicMock()
        m.json.return_value = {"result": {"content": [{"type": "text", "text": text}]}}
        m.raise_for_status = MagicMock()
        return m

    def test_discover_tools_from_server(self):
        client = CMCMCPClient(api_key="test-key")
        client._initialized = True  # skip handshake in mock
        with patch("httpx.post", return_value=self._tools_resp(
                ["get_fear_greed_index", "get_global_metrics"])):
            tools = client.discover_tools()
        assert len(tools) == 2

    def test_get_fear_greed_latest_parses(self):
        client = CMCMCPClient(api_key="test-key")
        client._initialized = True
        client._tools_cache = [{"name": "get_fear_greed_index"}]
        with patch("httpx.post", return_value=self._content_resp(
                '{"data":{"value":42,"value_classification":"Fear"}}')):
            result = client.get_fear_greed_latest()
        assert result["data"]["value"] == 42

    def test_cache_prevents_rediscovery(self):
        client = CMCMCPClient(api_key="test-key")
        client._tools_cache = [{"name": "cached_tool"}]
        tools = client.discover_tools()  # no httpx mock needed — cache hit
        assert tools[0]["name"] == "cached_tool"

    def test_get_global_metrics(self):
        client = CMCMCPClient(api_key="test-key")
        client._initialized = True
        client._tools_cache = [{"name": "get_global_metrics"}]
        with patch("httpx.post", return_value=self._content_resp(
                '{"data":{"total_market_cap":1000000000000}}')):
            result = client.get_global_metrics()
        assert "data" in result

    def test_initialize_called_once(self):
        client = CMCMCPClient(api_key="test-key")
        ok = MagicMock()
        ok.raise_for_status = MagicMock()
        ok.json.return_value = {"result": {}}
        with patch("httpx.post", return_value=ok) as mock_post:
            client._ensure_initialized()
            client._ensure_initialized()  # second call is a no-op
        assert mock_post.call_count == 1
