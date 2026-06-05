"""A minimal SMA-crossover signal.

The classic dual moving-average crossover: when a fast simple moving average
(SMA) rises above a slow one, that's a bullish ``BUY``; when it falls below,
that's a bearish ``SELL``. Otherwise ``HOLD``. Pure functions of a price
window — trivial to test and to feed into the paper account.

Part of Binance Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum


class Signal(str, Enum):
    """Trading signal emitted by a strategy."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


def sma(prices: Sequence[float], window: int) -> float:
    """Return the simple moving average of the last ``window`` prices.

    Args:
        prices: Price series; the most recent price is last.
        window: Number of trailing prices to average; must be positive.

    Returns:
        The mean of the final ``window`` prices.

    Raises:
        ValueError: If ``window`` is non-positive or longer than ``prices``.
    """
    if window <= 0:
        raise ValueError(f"window must be positive, got {window}")
    if window > len(prices):
        raise ValueError(f"need at least {window} prices, got {len(prices)}")
    recent = prices[-window:]
    return sum(recent) / window


class SmaCrossStrategy:
    """A dual-SMA crossover strategy.

    Args:
        fast: Fast (short) SMA window.
        slow: Slow (long) SMA window; must be greater than ``fast``.
    """

    name = "sma_cross"

    def __init__(self, fast: int, slow: int) -> None:
        if fast <= 0 or slow <= 0:
            raise ValueError("fast and slow windows must be positive")
        if fast >= slow:
            raise ValueError(f"fast ({fast}) must be less than slow ({slow})")
        self.fast = fast
        self.slow = slow

    def signal(self, prices: Sequence[float]) -> Signal:
        """Compute the crossover signal for the current price window.

        Args:
            prices: Price series with the most recent price last. Must contain
                at least ``slow`` prices.

        Returns:
            :attr:`Signal.BUY` when the fast SMA is above the slow SMA,
            :attr:`Signal.SELL` when it is below, else :attr:`Signal.HOLD`.

        Raises:
            ValueError: If fewer than ``slow`` prices are supplied.
        """
        fast_ma = sma(prices, self.fast)
        slow_ma = sma(prices, self.slow)
        if fast_ma > slow_ma:
            return Signal.BUY
        if fast_ma < slow_ma:
            return Signal.SELL
        return Signal.HOLD
