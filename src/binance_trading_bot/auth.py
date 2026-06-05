"""HMAC-SHA256 request signing for Binance signed endpoints.

Binance authenticates ``SIGNED`` (TRADE / USER_DATA / MARGIN) endpoints by
appending a ``signature`` parameter: the HMAC-SHA256 of the request query
string keyed by the account's API *secret*, encoded as lowercase hex. This
module reproduces that scheme deterministically and offline — no network, no
clock dependency unless you ask for one.

Part of Binance Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Mapping
from urllib.parse import urlencode


def sign_query(query_string: str, secret: str) -> str:
    """Return the lowercase hex HMAC-SHA256 of ``query_string`` keyed by ``secret``.

    This is exactly the value Binance expects in the ``signature`` parameter of
    a signed request.

    Args:
        query_string: The URL-encoded query string to sign, e.g.
            ``"symbol=BTCUSDT&side=BUY&timestamp=1700000000000"``.
        secret: The API secret associated with the API key.

    Returns:
        The signature as a 64-character lowercase hexadecimal string.
    """
    return hmac.new(
        secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def encode_params(params: Mapping[str, object]) -> str:
    """URL-encode an ordered mapping of params into a query string.

    Insertion order is preserved, which matters because the signature is taken
    over the exact bytes of the query string.

    Args:
        params: Parameter name/value pairs. Values are stringified by
            :func:`urllib.parse.urlencode`.

    Returns:
        The URL-encoded query string (without a leading ``?``).
    """
    return urlencode(list(params.items()))


def current_timestamp_ms() -> int:
    """Return the current Unix time in milliseconds (Binance ``timestamp`` units)."""
    return int(time.time() * 1000)


def build_signed_query(
    params: Mapping[str, object],
    secret: str,
    *,
    timestamp_ms: int | None = None,
) -> str:
    """Build a fully signed Binance query string from ``params``.

    A ``timestamp`` parameter is appended (Binance requires it on signed
    endpoints), the resulting string is signed, and the ``signature`` parameter
    is appended last — matching Binance's documented ordering.

    Args:
        params: The request parameters, excluding ``timestamp`` and
            ``signature``. Insertion order is preserved.
        secret: The API secret used to compute the HMAC signature.
        timestamp_ms: Optional fixed timestamp in milliseconds. When ``None``
            the current time is used. Pass a fixed value for reproducible
            output (e.g. in tests).

    Returns:
        The complete signed query string, e.g.
        ``"symbol=BTCUSDT&timestamp=...&signature=..."``.
    """
    ts = current_timestamp_ms() if timestamp_ms is None else timestamp_ms
    ordered: dict[str, object] = {**params, "timestamp": ts}
    base = encode_params(ordered)
    signature = sign_query(base, secret)
    return f"{base}&signature={signature}"
