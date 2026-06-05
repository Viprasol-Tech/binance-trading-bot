"""Tests for the offline Binance REST request builder."""

from __future__ import annotations

from binance_trading_bot.auth import sign_query
from binance_trading_bot.client import DEFAULT_BASE_URL, BinanceClient


def test_public_request_has_no_signature_and_includes_query() -> None:
    """Public requests carry params but never a signature."""
    client = BinanceClient("key", "secret")
    req = client.prepare_public_request("GET", "/api/v3/ticker/price", {"symbol": "BTCUSDT"})
    assert req["method"] == "GET"
    assert req["url"] == f"{DEFAULT_BASE_URL}/api/v3/ticker/price?symbol=BTCUSDT"
    assert "signature" not in req["query_string"]
    assert req["headers"]["X-MBX-APIKEY"] == "key"


def test_signed_request_includes_valid_signature_and_api_key_header() -> None:
    """Signed requests append a correct HMAC signature and the API-key header."""
    client = BinanceClient("my-key", "my-secret")
    req = client.prepare_signed_request(
        "POST", "/api/v3/order", {"symbol": "BTCUSDT"}, timestamp_ms=1_700_000_000_000
    )
    qs = req["query_string"]
    base, _, sig = qs.partition("&signature=")

    assert req["headers"]["X-MBX-APIKEY"] == "my-key"
    assert base == "symbol=BTCUSDT&timestamp=1700000000000"
    assert sig == sign_query(base, "my-secret")
    assert req["url"] == f"{DEFAULT_BASE_URL}/api/v3/order?{qs}"


def test_prepare_new_order_builds_signed_market_order() -> None:
    """The order helper upper-cases inputs and produces a signed MARKET order."""
    client = BinanceClient("k", "s")
    req = client.prepare_new_order("btcusdt", "buy", 0.5, timestamp_ms=1_700_000_000_000)
    base, _, sig = req["query_string"].partition("&signature=")
    assert base == ("symbol=BTCUSDT&side=BUY&type=MARKET&quantity=0.5&timestamp=1700000000000")
    assert sig == sign_query(base, "s")


def test_base_url_is_overridable_for_testnet() -> None:
    """A custom base URL (e.g. testnet) is honoured and trailing slash trimmed."""
    client = BinanceClient("k", "s", base_url="https://testnet.binance.vision/")
    req = client.prepare_public_request("GET", "/api/v3/time")
    assert req["url"] == "https://testnet.binance.vision/api/v3/time"
