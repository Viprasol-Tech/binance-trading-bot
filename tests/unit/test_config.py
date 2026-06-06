"""Tests for the typed BotConfig."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from binance_trading_bot.config import BotConfig


def test_defaults_are_sane() -> None:
    """Default config is valid and uses sma_cross on BTCUSDT."""
    cfg = BotConfig()
    assert cfg.symbol == "BTCUSDT"
    assert cfg.strategy == "sma_cross"
    assert cfg.start_cash > 0


def test_symbol_is_upper_cased() -> None:
    """A lower-case symbol is normalised to upper case."""
    assert BotConfig(symbol="ethusdt").symbol == "ETHUSDT"


def test_config_is_frozen() -> None:
    """The model is immutable after construction."""
    cfg = BotConfig()
    with pytest.raises(ValidationError):
        cfg.start_cash = 5.0  # type: ignore[misc]


def test_fast_must_be_less_than_slow() -> None:
    """Cross-field validation rejects fast >= slow."""
    with pytest.raises(ValidationError, match="must be less than slow"):
        BotConfig(fast=10, slow=5)


def test_rsi_lower_must_be_less_than_upper() -> None:
    """RSI thresholds are ordered."""
    with pytest.raises(ValidationError, match="must be less than rsi_upper"):
        BotConfig(rsi_lower=80.0, rsi_upper=20.0)


def test_rejects_non_positive_cash_and_quantity() -> None:
    """start_cash and order_quantity must be strictly positive."""
    with pytest.raises(ValidationError):
        BotConfig(start_cash=0.0)
    with pytest.raises(ValidationError):
        BotConfig(order_quantity=-1.0)


def test_rejects_unknown_strategy() -> None:
    """Only the documented strategy names are accepted."""
    with pytest.raises(ValidationError):
        BotConfig(strategy="momentum")  # type: ignore[arg-type]


def test_rejects_extra_fields() -> None:
    """Unknown fields are forbidden to catch typos early."""
    with pytest.raises(ValidationError):
        BotConfig(symboll="BTCUSDT")  # type: ignore[call-arg]


def test_fee_rate_bounds() -> None:
    """Fee rate is a fraction in [0, 1)."""
    assert BotConfig(fee_rate=0.001).fee_rate == pytest.approx(0.001)
    with pytest.raises(ValidationError):
        BotConfig(fee_rate=1.0)
