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
