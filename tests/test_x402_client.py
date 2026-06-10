"""CMC x402 client tests (mock mode; no real on-chain tx; correct headers mock)."""
import pytest
from unittest.mock import patch, MagicMock
from src.cmc.x402_client import CMCx402Client


def make_402_response():
    quote = {"x402Version": 1, "accepts": [{
        "scheme": "exact", "network": "base", "maxAmountRequired": "10000",
        "payTo": "0x" + "a" * 40, "maxTimeoutSeconds": 300,
        "asset": "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
        "extra": {"name": "USDC", "version": "2"},
    }]}
    m = MagicMock()
    m.status_code = 402
    m.json.return_value = quote
    return m


def make_200_response(data: dict, tx: str = "0xabc123cafe"):
    """
    Correct 200 mock: headers.get() must behave like dict.get()
    (a plain dict assignment on MagicMock breaks .get()).
    """
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = data
    m.raise_for_status = MagicMock()
    _headers = {"X-Payment-Tx": tx, "X-PAYMENT-TX": tx, "x-payment-tx": tx}
    m.headers = MagicMock()
    m.headers.get = lambda k, d=None: _headers.get(k, d)
    return m


class TestInit:
    def test_no_key_none_acct(self):
        client = CMCx402Client(private_key="")
        assert client._acct is None
        assert client.last_payment_tx is None

    def test_with_test_key(self):
        client = CMCx402Client(private_key="0x" + "1" * 64)
        assert client._acct is not None
        assert client.address is not None


class TestGet:
    def test_direct_200_no_payment(self):
        client = CMCx402Client(private_key="")
        with patch.object(client._client, "get",
                          return_value=make_200_response({"ok": True})):
            result = client.get("/test", {})
        assert result == {"ok": True}

    def test_402_then_200_two_calls(self):
        client = CMCx402Client(private_key="0x" + "b" * 64)
        calls = [0]
        responses = [make_402_response(), make_200_response({"fg": 45})]

        def se(*a, **kw):
            r = responses[calls[0]]
            calls[0] += 1
            return r

        with patch.object(client._client, "get", side_effect=se):
            result = client.get("/v3/fear-and-greed/latest", {})
        assert calls[0] == 2
        assert result == {"fg": 45}

    def test_payment_tx_captured_from_headers(self):
        client = CMCx402Client(private_key="0x" + "c" * 64)
        responses = [make_402_response(), make_200_response({"d": "ok"}, tx="0xdeadbeef")]
        idx = [0]

        def se(*a, **kw):
            r = responses[idx[0]]
            idx[0] += 1
            return r

        with patch.object(client._client, "get", side_effect=se):
            client.get("/test", {})
        assert client.last_payment_tx == "0xdeadbeef"  # str, not MagicMock

    def test_no_key_402_raises(self):
        client = CMCx402Client(private_key="")
        with patch.object(client._client, "get", return_value=make_402_response()):
            with pytest.raises(RuntimeError, match="X402_PRIVATE_KEY"):
                client.get("/test", {})

    def test_context_manager(self):
        with CMCx402Client(private_key="") as c:
            assert c is not None

    def test_convenience_method_calls_get(self):
        client = CMCx402Client(private_key="")
        with patch.object(client, "get",
                          return_value={"data": {"value": 55}}) as mock_get:
            result = client.get_fear_greed_latest()
        mock_get.assert_called_once_with("/v3/fear-and-greed/latest", {})
        assert result["data"]["value"] == 55
