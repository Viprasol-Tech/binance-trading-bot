"""Tests for the offline Binance REST request builder."""

from __future__ import annotations

import pytest

from binance_trading_bot.auth import sign_query
from binance_trading_bot.client import (
    DEFAULT_BASE_URL,
    TESTNET_BASE_URL,
    VALID_INTERVALS,
    BinanceClient,
)


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
    client = BinanceClient("k", "s", base_url=TESTNET_BASE_URL + "/")
    req = client.prepare_public_request("GET", "/api/v3/time")
    assert req["url"] == "https://testnet.binance.vision/api/v3/time"


def test_limit_order_includes_time_in_force_and_price() -> None:
    """A LIMIT order carries timeInForce and price in the documented order."""
    client = BinanceClient("k", "s")
    req = client.prepare_limit_order(
        "ethusdt", "sell", 2.0, 3000.0, time_in_force="ioc", timestamp_ms=1_700_000_000_000
    )
    base, _, sig = req["query_string"].partition("&signature=")
    assert base == (
        "symbol=ETHUSDT&side=SELL&type=LIMIT&timeInForce=IOC"
        "&quantity=2.0&price=3000.0&timestamp=1700000000000"
    )
    assert sig == sign_query(base, "s")


def test_limit_order_rejects_bad_time_in_force() -> None:
    """An unrecognised TIF is rejected."""
    client = BinanceClient("k", "s")
    with pytest.raises(ValueError, match="invalid time_in_force"):
        client.prepare_limit_order("BTCUSDT", "BUY", 1.0, 100.0, time_in_force="ZZZ")


@pytest.mark.parametrize("qty,price", [(0.0, 100.0), (1.0, -1.0)])
def test_limit_order_rejects_non_positive(qty: float, price: float) -> None:
    """Non-positive quantity or price is rejected on LIMIT orders."""
    client = BinanceClient("k", "s")
    with pytest.raises(ValueError):
        client.prepare_limit_order("BTCUSDT", "BUY", qty, price)


def test_stop_loss_limit_order_includes_stop_price() -> None:
    """A STOP_LOSS_LIMIT order carries stopPrice and a valid signature."""
    client = BinanceClient("k", "s")
    req = client.prepare_stop_loss_limit_order(
        "BTCUSDT", "SELL", 1.0, 24000.0, 24500.0, timestamp_ms=1_700_000_000_000
    )
    base, _, sig = req["query_string"].partition("&signature=")
    assert "type=STOP_LOSS_LIMIT" in base
    assert "stopPrice=24500.0" in base
    assert sig == sign_query(base, "s")


def test_oco_order_targets_oco_path_and_pairs_legs() -> None:
    """An OCO order hits /order/oco and includes both legs' prices."""
    client = BinanceClient("k", "s")
    req = client.prepare_oco_order(
        "BTCUSDT", "SELL", 1.0, 26000.0, 24000.0, 23900.0, timestamp_ms=1_700_000_000_000
    )
    assert "/api/v3/order/oco?" in req["url"]
    base, _, sig = req["query_string"].partition("&signature=")
    assert "price=26000.0" in base
    assert "stopPrice=24000.0" in base
    assert "stopLimitPrice=23900.0" in base
    assert sig == sign_query(base, "s")


def test_klines_builds_public_request_with_params() -> None:
    """Klines is unsigned and carries symbol/interval/limit."""
    client = BinanceClient("k", "s")
    req = client.prepare_klines("btcusdt", "1h", limit=100)
    assert req["method"] == "GET"
    assert req["url"] == f"{DEFAULT_BASE_URL}/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=100"
    assert "signature" not in req["query_string"]


def test_klines_optional_time_window() -> None:
    """Start/end times appear only when provided."""
    client = BinanceClient("k", "s")
    req = client.prepare_klines("BTCUSDT", "1d", limit=5, start_time_ms=1, end_time_ms=2)
    assert "startTime=1" in req["query_string"]
    assert "endTime=2" in req["query_string"]


def test_klines_rejects_bad_interval_and_limit() -> None:
    """Unknown interval or out-of-range limit raises ValueError."""
    client = BinanceClient("k", "s")
    with pytest.raises(ValueError, match="unknown interval"):
        client.prepare_klines("BTCUSDT", "7m")
    with pytest.raises(ValueError, match="limit must be"):
        client.prepare_klines("BTCUSDT", "1h", limit=0)
    assert "1h" in VALID_INTERVALS


def test_account_request_is_signed() -> None:
    """The account endpoint is signed and carries the API-key header."""
    client = BinanceClient("k", "s")
    req = client.prepare_account(timestamp_ms=1_700_000_000_000)
    base, _, sig = req["query_string"].partition("&signature=")
    assert req["url"].startswith(f"{DEFAULT_BASE_URL}/api/v3/account?")
    assert base == "timestamp=1700000000000"
    assert sig == sign_query(base, "s")
    assert req["headers"]["X-MBX-APIKEY"] == "k"


def test_cancel_order_requires_exactly_one_identifier() -> None:
    """Cancel needs exactly one of order_id / orig_client_order_id."""
    client = BinanceClient("k", "s")
    with pytest.raises(ValueError, match="exactly one"):
        client.prepare_cancel_order("BTCUSDT")
    with pytest.raises(ValueError, match="exactly one"):
        client.prepare_cancel_order("BTCUSDT", order_id=1, orig_client_order_id="x")


def test_cancel_order_by_order_id_is_signed_delete() -> None:
    """Cancel by order id is a signed DELETE with orderId in the query."""
    client = BinanceClient("k", "s")
    req = client.prepare_cancel_order("BTCUSDT", order_id=42, timestamp_ms=1_700_000_000_000)
    assert req["method"] == "DELETE"
    base, _, sig = req["query_string"].partition("&signature=")
    assert base == "symbol=BTCUSDT&orderId=42&timestamp=1700000000000"
    assert sig == sign_query(base, "s")
