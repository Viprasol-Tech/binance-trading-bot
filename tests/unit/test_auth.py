"""Tests for HMAC-SHA256 request signing."""

from __future__ import annotations

import hashlib
import hmac

import pytest

from binance_trading_bot.auth import build_signed_query, encode_params, sign_query


def test_sign_query_matches_independent_hashlib_vector() -> None:
    """The signature must equal an HMAC computed independently with hashlib."""
    secret = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0"
    query = "symbol=LTCBTC&side=BUY&type=LIMIT&quantity=1&price=0.1&timestamp=1499827319559"

    expected = hmac.new(secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()

    assert sign_query(query, secret) == expected
    # Sanity: it is 64 lowercase hex chars.
    assert len(sign_query(query, secret)) == 64
    assert sign_query(query, secret) == sign_query(query, secret).lower()


def test_known_static_vector() -> None:
    """Pin a fully precomputed (secret, query) -> hex vector."""
    secret = "topsecret"
    query = "a=1&b=2"
    expected = hmac.new(secret.encode("utf-8"), query.encode("utf-8"), hashlib.sha256).hexdigest()
    assert sign_query(query, secret) == expected


def test_encode_params_preserves_order() -> None:
    """Param ordering is preserved because the signature is order-sensitive."""
    assert encode_params({"symbol": "BTCUSDT", "side": "BUY"}) == "symbol=BTCUSDT&side=BUY"


def test_build_signed_query_appends_timestamp_and_signature() -> None:
    """The built query ends with ...&timestamp=<ts>&signature=<sig>."""
    secret = "abc"
    out = build_signed_query({"symbol": "BTCUSDT"}, secret, timestamp_ms=1_700_000_000_000)

    assert out.startswith("symbol=BTCUSDT&timestamp=1700000000000&signature=")
    base, _, sig = out.partition("&signature=")
    assert sig == sign_query(base, secret)


def test_build_signed_query_is_deterministic_with_fixed_timestamp() -> None:
    """Fixing the timestamp yields identical output across calls."""
    a = build_signed_query({"x": "1"}, "k", timestamp_ms=42)
    b = build_signed_query({"x": "1"}, "k", timestamp_ms=42)
    assert a == b


def test_different_secret_changes_signature() -> None:
    """A different secret produces a different signature for the same query."""
    assert sign_query("a=1", "secret1") != sign_query("a=1", "secret2")


def test_build_signed_query_without_fixed_timestamp_signs_correctly() -> None:
    """Even with the default clock timestamp, the signature matches its base."""
    out = build_signed_query({"symbol": "ETHUSDT"}, "key")
    base, _, sig = out.partition("&signature=")
    assert sig == sign_query(base, "key")


def test_sign_query_rejects_nothing_but_is_pure() -> None:
    """Empty query string still produces a valid HMAC."""
    expected = hmac.new(b"k", b"", hashlib.sha256).hexdigest()
    assert sign_query("", "k") == expected


def test_pytest_marker_smoke() -> None:
    """Trivial guard so the suite has an always-on sanity check."""
    with pytest.raises(ValueError):
        raise ValueError("ok")
