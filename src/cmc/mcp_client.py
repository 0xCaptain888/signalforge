"""
CMC Data MCP client — final version (v2.1.0).
P2-12 fix applied: MCP `initialize` handshake before tools/list.

Connects to https://mcp.coinmarketcap.com/mcp, discovers tools, and wraps
the common queries. Falls back to a hardcoded 12-tool list when offline.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CMCMCPClient:
    MCP_URL = "https://mcp.coinmarketcap.com/mcp"

    # Hardcoded fallback (server exposes 12 tools; used when discovery fails)
    KNOWN_TOOLS = [
        "get_cryptocurrency_quotes",
        "get_fear_greed_index",
        "get_global_metrics",
        "get_trending_cryptocurrencies",
        "get_technical_analysis",
        "get_on_chain_data",
        "get_derivatives_data",
        "get_sentiment_data",
        "get_news",
        "get_listings",
        "search_cryptocurrency",
        "get_ohlcv",
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CMC_API_KEY", "")
        self._tools_cache: Optional[list] = None
        self._request_id = 0
        self._initialized = False

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    # -- MCP initialize handshake (P2-12) ------------------------------------
    def _ensure_initialized(self):
        """MCP protocol requires `initialize` before tools/list (idempotent)."""
        if self._initialized:
            return
        try:
            import httpx
            body = {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "signalforge", "version": "2.1.0"},
                },
            }
            r = httpx.post(self.MCP_URL, json=body, headers=self._headers(), timeout=10)
            r.raise_for_status()
        except Exception:
            pass  # server may not require it; never block
        finally:
            self._initialized = True

    # -- Tool discovery -------------------------------------------------------
    def discover_tools(self) -> list:
        """List all tools on the MCP server (with hardcoded fallback)."""
        if self._tools_cache is not None:
            return self._tools_cache

        self._ensure_initialized()
        try:
            import httpx
            body = {"jsonrpc": "2.0", "id": self._next_id(),
                    "method": "tools/list", "params": {}}
            r = httpx.post(self.MCP_URL, json=body, headers=self._headers(), timeout=15)
            r.raise_for_status()
            tools = r.json().get("result", {}).get("tools", [])
            if tools:
                self._tools_cache = tools
                logger.info("MCP: discovered %d tools", len(tools))
                return tools
        except Exception as e:
            logger.warning("MCP tool discovery failed (%s). Using known tools list.", e)

        self._tools_cache = [{"name": t, "description": t} for t in self.KNOWN_TOOLS]
        return self._tools_cache

    def list_tool_names(self) -> list:
        return [t["name"] for t in self.discover_tools()]

    # -- Tool calls -----------------------------------------------------------
    def _call_tool(self, tool_name: str, arguments: dict) -> Any:
        import httpx
        self._ensure_initialized()
        body = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        r = httpx.post(self.MCP_URL, json=body, headers=self._headers(), timeout=30)
        r.raise_for_status()
        result = r.json().get("result", {})
        for block in result.get("content", []):
            if block.get("type") == "text":
                try:
                    return json.loads(block["text"])
                except json.JSONDecodeError:
                    return block["text"]
        return result

    # -- High-level helpers ---------------------------------------------------
    def get_fear_greed_latest(self) -> dict:
        """Latest CMC proprietary Fear & Greed (NOT Alternative.me)."""
        return self._call_tool("get_fear_greed_index", {"period": "latest"})

    def get_fear_greed_historical(self, limit: int = 30) -> Any:
        return self._call_tool("get_fear_greed_index", {"period": "historical", "limit": limit})

    def get_global_metrics(self) -> dict:
        return self._call_tool("get_global_metrics", {})

    def get_quotes(self, symbols: list) -> dict:
        return self._call_tool("get_cryptocurrency_quotes", {"symbols": ",".join(symbols)})

    def get_trending(self, limit: int = 10) -> Any:
        return self._call_tool("get_trending_cryptocurrencies", {"limit": limit})
