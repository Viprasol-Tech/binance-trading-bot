"""Tests for the SMA-crossover strategy."""

from __future__ import annotations

import pytest

from binance_trading_bot.strategy import Signal, SmaCrossStrategy, sma


def test_sma_computes_trailing_mean() -> None:
    """SMA averages exactly the last ``window`` prices."""
    assert sma([1.0, 2.0, 3.0, 4.0], 2) == pytest.approx(3.5)
    assert sma([1.0, 2.0, 3.0, 4.0], 4) == pytest.approx(2.5)


def test_sma_rejects_bad_window() -> None:
    """A non-positive or oversized window raises ValueError."""
    with pytest.raises(ValueError):
        sma([1.0, 2.0], 0)
    with pytest.raises(ValueError):
        sma([1.0], 5)


def test_buy_when_fast_above_slow() -> None:
    """Rising prices push the fast SMA above the slow SMA -> BUY."""
    strat = SmaCrossStrategy(fast=2, slow=4)
    assert strat.signal([1.0, 2.0, 3.0, 4.0]) is Signal.BUY


def test_sell_when_fast_below_slow() -> None:
    """Falling prices push the fast SMA below the slow SMA -> SELL."""
    strat = SmaCrossStrategy(fast=2, slow=4)
    assert strat.signal([4.0, 3.0, 2.0, 1.0]) is Signal.SELL


def test_hold_when_equal() -> None:
    """A flat series gives equal SMAs -> HOLD."""
    strat = SmaCrossStrategy(fast=2, slow=4)
    assert strat.signal([5.0, 5.0, 5.0, 5.0]) is Signal.HOLD


def test_constructor_validates_windows() -> None:
    """fast must be positive and strictly less than slow."""
    with pytest.raises(ValueError):
        SmaCrossStrategy(fast=4, slow=2)
    with pytest.raises(ValueError):
        SmaCrossStrategy(fast=0, slow=4)


def test_signal_requires_enough_prices() -> None:
    """Fewer than ``slow`` prices raises ValueError."""
    strat = SmaCrossStrategy(fast=2, slow=4)
    with pytest.raises(ValueError):
        strat.signal([1.0, 2.0])
