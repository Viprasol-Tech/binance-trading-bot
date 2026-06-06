"""Offline Binance REST request builder.

``BinanceClient`` constructs the exact HTTP request (method, URL, headers,
query string) that a live call to Binance would send — including the
``X-MBX-APIKEY`` header and the HMAC ``signature`` on signed endpoints — but it
makes **no network calls**. Each method returns a :class:`PreparedRequest`
dict, which keeps the signing logic fully testable and lets you plug in any
HTTP transport you like.

Part of Binance Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypedDict

from binance_trading_bot.auth import build_signed_query, encode_params

DEFAULT_BASE_URL = "https://api.binance.com"
TESTNET_BASE_URL = "https://testnet.binance.vision"

#: Valid kline / candlestick intervals accepted by ``GET /api/v3/klines``.
VALID_INTERVALS: frozenset[str] = frozenset(
    {
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "6h",
        "8h",
        "12h",
        "1d",
        "3d",
        "1w",
        "1M",
    }
)


class PreparedRequest(TypedDict):
    """A fully prepared, ready-to-send HTTP request (never actually sent)."""

    method: str
    url: str
    headers: dict[str, str]
    query_string: str


class BinanceClient:
    """Build signed and unsigned Binance REST requests without sending them.

    Args:
        api_key: The public API key, sent in the ``X-MBX-APIKEY`` header.
        api_secret: The API secret, used to HMAC-sign signed requests.
        base_url: REST base URL. Defaults to Binance spot
            (``https://api.binance.com``); point it at a testnet for paper use.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        """Return the standard request headers including the API-key header."""
        return {"X-MBX-APIKEY": self.api_key}

    def prepare_public_request(
        self,
        method: str,
        path: str,
        params: Mapping[str, object] | None = None,
    ) -> PreparedRequest:
        """Prepare an unsigned (public) request, e.g. market data.

        Args:
            method: HTTP method such as ``"GET"``.
            path: Endpoint path beginning with ``/``, e.g. ``"/api/v3/ticker/price"``.
            params: Optional query parameters; insertion order is preserved.

        Returns:
            The prepared request. ``url`` includes the query string when
            ``params`` is non-empty.
        """
        query_string = encode_params(params) if params else ""
        url = f"{self.base_url}{path}"
        if query_string:
            url = f"{url}?{query_string}"
        return PreparedRequest(
            method=method.upper(),
            url=url,
            headers=self._headers(),
            query_string=query_string,
        )

    def prepare_signed_request(
        self,
        method: str,
        path: str,
        params: Mapping[str, object] | None = None,
        *,
        timestamp_ms: int | None = None,
    ) -> PreparedRequest:
        """Prepare a signed request for a TRADE / USER_DATA endpoint.

        A ``timestamp`` and an HMAC-SHA256 ``signature`` are appended to the
        query string per Binance's signed-endpoint contract.

        Args:
            method: HTTP method such as ``"POST"``.
            path: Endpoint path beginning with ``/``, e.g. ``"/api/v3/order"``.
            params: Request parameters excluding ``timestamp``/``signature``;
                insertion order is preserved.
            timestamp_ms: Optional fixed timestamp in milliseconds for
                reproducible output. ``None`` uses the current time.

        Returns:
            The prepared, signed request with the full query string both in
            ``url`` and in ``query_string``.
        """
        query_string = build_signed_query(
            params or {},
            self.api_secret,
            timestamp_ms=timestamp_ms,
        )
        url = f"{self.base_url}{path}?{query_string}"
        return PreparedRequest(
            method=method.upper(),
            url=url,
            headers=self._headers(),
            query_string=query_string,
        )

    def prepare_new_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        *,
        order_type: str = "MARKET",
        timestamp_ms: int | None = None,
    ) -> PreparedRequest:
        """Prepare a signed ``POST /api/v3/order`` request.

        Args:
            symbol: Trading pair, e.g. ``"BTCUSDT"``.
            side: ``"BUY"`` or ``"SELL"`` (upper-cased automatically).
            quantity: Base-asset quantity to trade.
            order_type: Binance order type; defaults to ``"MARKET"``.
            timestamp_ms: Optional fixed timestamp in milliseconds.

        Returns:
            The prepared, signed order request.
        """
        params: dict[str, object] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": quantity,
        }
        return self.prepare_signed_request(
            "POST",
            "/api/v3/order",
            params,
            timestamp_ms=timestamp_ms,
        )

    def prepare_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        *,
        time_in_force: str = "GTC",
        timestamp_ms: int | None = None,
    ) -> PreparedRequest:
        """Prepare a signed ``LIMIT`` ``POST /api/v3/order`` request.

        Args:
            symbol: Trading pair, e.g. ``"BTCUSDT"``.
            side: ``"BUY"`` or ``"SELL"`` (upper-cased automatically).
            quantity: Base-asset quantity to trade; must be positive.
            price: Limit price in quote currency; must be positive.
            time_in_force: ``"GTC"``, ``"IOC"`` or ``"FOK"``. Binance requires
                this on ``LIMIT`` orders.
            timestamp_ms: Optional fixed timestamp in milliseconds.

        Returns:
            The prepared, signed limit-order request.

        Raises:
            ValueError: If ``quantity``/``price`` are non-positive or
                ``time_in_force`` is not a recognised value.
        """
        _require_positive("quantity", quantity)
        _require_positive("price", price)
        tif = _validate_tif(time_in_force)
        params: dict[str, object] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "LIMIT",
            "timeInForce": tif,
            "quantity": quantity,
            "price": price,
        }
        return self.prepare_signed_request(
            "POST", "/api/v3/order", params, timestamp_ms=timestamp_ms
        )

    def prepare_stop_loss_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        stop_price: float,
        *,
        time_in_force: str = "GTC",
        timestamp_ms: int | None = None,
    ) -> PreparedRequest:
        """Prepare a signed ``STOP_LOSS_LIMIT`` order request.

        A stop-loss-limit triggers a limit order once the market trades through
        ``stop_price``.

        Args:
            symbol: Trading pair, e.g. ``"BTCUSDT"``.
            side: ``"BUY"`` or ``"SELL"``.
            quantity: Base-asset quantity; must be positive.
            price: Limit price once triggered; must be positive.
            stop_price: Trigger price; must be positive.
            time_in_force: ``"GTC"``, ``"IOC"`` or ``"FOK"``.
            timestamp_ms: Optional fixed timestamp in milliseconds.

        Returns:
            The prepared, signed stop-loss-limit order request.
        """
        _require_positive("quantity", quantity)
        _require_positive("price", price)
        _require_positive("stop_price", stop_price)
        tif = _validate_tif(time_in_force)
        params: dict[str, object] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "STOP_LOSS_LIMIT",
            "timeInForce": tif,
            "quantity": quantity,
            "price": price,
            "stopPrice": stop_price,
        }
        return self.prepare_signed_request(
            "POST", "/api/v3/order", params, timestamp_ms=timestamp_ms
        )

    def prepare_oco_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        stop_price: float,
        stop_limit_price: float,
        *,
        stop_limit_time_in_force: str = "GTC",
        timestamp_ms: int | None = None,
    ) -> PreparedRequest:
        """Prepare a signed OCO (one-cancels-the-other) order request.

        Targets ``POST /api/v3/order/oco`` and pairs a take-profit limit leg
        (``price``) with a protective stop leg (``stop_price`` /
        ``stop_limit_price``).

        Args:
            symbol: Trading pair, e.g. ``"BTCUSDT"``.
            side: ``"BUY"`` or ``"SELL"``.
            quantity: Base-asset quantity; must be positive.
            price: Limit price of the take-profit leg; must be positive.
            stop_price: Trigger price of the stop leg; must be positive.
            stop_limit_price: Limit price of the stop leg once triggered;
                must be positive.
            stop_limit_time_in_force: TIF for the stop-limit leg.
            timestamp_ms: Optional fixed timestamp in milliseconds.

        Returns:
            The prepared, signed OCO order request.
        """
        for label, value in (
            ("quantity", quantity),
            ("price", price),
            ("stop_price", stop_price),
            ("stop_limit_price", stop_limit_price),
        ):
            _require_positive(label, value)
        tif = _validate_tif(stop_limit_time_in_force)
        params: dict[str, object] = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "quantity": quantity,
            "price": price,
            "stopPrice": stop_price,
            "stopLimitPrice": stop_limit_price,
            "stopLimitTimeInForce": tif,
        }
        return self.prepare_signed_request(
            "POST", "/api/v3/order/oco", params, timestamp_ms=timestamp_ms
        )

    def prepare_klines(
        self,
        symbol: str,
        interval: str,
        *,
        limit: int = 500,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
    ) -> PreparedRequest:
        """Prepare an unsigned ``GET /api/v3/klines`` (candlestick) request.

        Args:
            symbol: Trading pair, e.g. ``"BTCUSDT"``.
            interval: Candle interval such as ``"1m"``, ``"1h"`` or ``"1d"``;
                must be one of :data:`VALID_INTERVALS`.
            limit: Number of candles to return (1..1000). Defaults to 500.
            start_time_ms: Optional inclusive start time in milliseconds.
            end_time_ms: Optional inclusive end time in milliseconds.

        Returns:
            The prepared public klines request.

        Raises:
            ValueError: If ``interval`` is unknown or ``limit`` is out of range.
        """
        if interval not in VALID_INTERVALS:
            raise ValueError(f"unknown interval {interval!r}")
        if not 1 <= limit <= 1000:
            raise ValueError(f"limit must be in 1..1000, got {limit}")
        params: dict[str, object] = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit,
        }
        if start_time_ms is not None:
            params["startTime"] = start_time_ms
        if end_time_ms is not None:
            params["endTime"] = end_time_ms
        return self.prepare_public_request("GET", "/api/v3/klines", params)

    def prepare_account(self, *, timestamp_ms: int | None = None) -> PreparedRequest:
        """Prepare a signed ``GET /api/v3/account`` (balances) request.

        Args:
            timestamp_ms: Optional fixed timestamp in milliseconds.

        Returns:
            The prepared, signed account request.
        """
        return self.prepare_signed_request("GET", "/api/v3/account", timestamp_ms=timestamp_ms)

    def prepare_cancel_order(
        self,
        symbol: str,
        *,
        order_id: int | None = None,
        orig_client_order_id: str | None = None,
        timestamp_ms: int | None = None,
    ) -> PreparedRequest:
        """Prepare a signed ``DELETE /api/v3/order`` request.

        Identify the order by exchange ``order_id`` or by the client-assigned
        ``orig_client_order_id``; exactly one is required.

        Args:
            symbol: Trading pair, e.g. ``"BTCUSDT"``.
            order_id: Exchange order id to cancel.
            orig_client_order_id: Original client order id to cancel.
            timestamp_ms: Optional fixed timestamp in milliseconds.

        Returns:
            The prepared, signed cancel request.

        Raises:
            ValueError: If neither or both identifiers are supplied.
        """
        if (order_id is None) == (orig_client_order_id is None):
            raise ValueError("supply exactly one of order_id or orig_client_order_id")
        params: dict[str, object] = {"symbol": symbol.upper()}
        if order_id is not None:
            params["orderId"] = order_id
        if orig_client_order_id is not None:
            params["origClientOrderId"] = orig_client_order_id
        return self.prepare_signed_request(
            "DELETE", "/api/v3/order", params, timestamp_ms=timestamp_ms
        )


def _require_positive(label: str, value: float) -> None:
    """Raise ``ValueError`` unless ``value`` is strictly positive."""
    if value <= 0:
        raise ValueError(f"{label} must be positive, got {value}")


def _validate_tif(time_in_force: str) -> str:
    """Normalise and validate a time-in-force value.

    Args:
        time_in_force: Candidate value; case-insensitive.

    Returns:
        The upper-cased, validated TIF (``"GTC"``, ``"IOC"`` or ``"FOK"``).

    Raises:
        ValueError: If the value is not a recognised TIF.
    """
    tif = time_in_force.upper()
    if tif not in {"GTC", "IOC", "FOK"}:
        raise ValueError(f"invalid time_in_force {time_in_force!r}; use GTC, IOC or FOK")
    return tif
