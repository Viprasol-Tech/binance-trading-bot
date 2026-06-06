"""Tests for the SMA-crossover strategy."""

from __future__ import annotations

import pytest

from binance_trading_bot.strategy import (
    RsiStrategy,
    Signal,
    SmaCrossStrategy,
    rsi,
    sma,
)


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


def test_sma_warmup_equals_slow() -> None:
    """The SMA strategy's warm-up equals its slow window."""
    assert SmaCrossStrategy(fast=3, slow=10).warmup == 10


def test_rsi_all_gains_is_100() -> None:
    """A strictly rising series has no losses, so RSI is 100."""
    prices = [float(p) for p in range(1, 20)]
    assert rsi(prices, 14) == pytest.approx(100.0)


def test_rsi_all_losses_is_zero() -> None:
    """A strictly falling series has no gains, so RSI is 0."""
    prices = [float(p) for p in range(20, 1, -1)]
    assert rsi(prices, 14) == pytest.approx(0.0)


def test_rsi_alternating_is_near_fifty() -> None:
    """A balanced up/down series sits around the midpoint."""
    prices = [100.0]
    for _ in range(20):
        prices.append(prices[-1] + 1.0)
        prices.append(prices[-1] - 1.0)
    value = rsi(prices, 14)
    assert 30.0 < value < 70.0


def test_rsi_bounded_and_known_vector() -> None:
    """RSI stays within [0, 100] and matches a hand-checked simple case."""
    # Six up moves of +1 then nothing: with period 3 the first 3 are gains.
    value = rsi([1.0, 2.0, 3.0, 4.0], 3)
    assert value == pytest.approx(100.0)
    assert 0.0 <= rsi([1.0, 3.0, 2.0, 4.0, 3.0, 5.0], 3) <= 100.0


def test_rsi_rejects_bad_inputs() -> None:
    """Non-positive period or too few prices raises ValueError."""
    with pytest.raises(ValueError):
        rsi([1.0, 2.0, 3.0], 0)
    with pytest.raises(ValueError):
        rsi([1.0, 2.0], 14)


def test_rsi_strategy_buys_oversold_sells_overbought() -> None:
    """RsiStrategy buys on a falling series and sells on a rising one."""
    strat = RsiStrategy(period=14, lower=30.0, upper=70.0)
    falling = [float(p) for p in range(40, 10, -1)]
    rising = [float(p) for p in range(10, 40)]
    assert strat.signal(falling) is Signal.BUY
    assert strat.signal(rising) is Signal.SELL


def test_rsi_strategy_holds_in_neutral_zone() -> None:
    """A balanced series keeps RSI between thresholds -> HOLD."""
    strat = RsiStrategy(period=14)
    prices = [100.0]
    for _ in range(20):
        prices.append(prices[-1] + 1.0)
        prices.append(prices[-1] - 1.0)
    assert strat.signal(prices) is Signal.HOLD


def test_rsi_strategy_validates_thresholds() -> None:
    """Thresholds must satisfy 0 < lower < upper < 100, period positive."""
    with pytest.raises(ValueError):
        RsiStrategy(period=14, lower=80.0, upper=20.0)
    with pytest.raises(ValueError):
        RsiStrategy(period=0)


def test_rsi_strategy_warmup() -> None:
    """Warm-up is period + 1 (need one extra price to measure a change)."""
    assert RsiStrategy(period=14).warmup == 15
