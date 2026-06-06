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

    @property
    def warmup(self) -> int:
        """Minimum number of prices required before a signal can be emitted."""
        return self.slow

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


def rsi(prices: Sequence[float], period: int = 14) -> float:
    """Return Wilder's Relative Strength Index over the last ``period`` changes.

    Uses Wilder's smoothing of average gains and losses. The result is bounded
    in ``[0, 100]``; values above 70 are conventionally "overbought" and below
    30 "oversold".

    Args:
        prices: Price series with the most recent price last. Must contain at
            least ``period + 1`` prices so ``period`` changes can be measured.
        period: Look-back length; must be positive. Defaults to 14.

    Returns:
        The RSI value in ``[0, 100]``. Returns ``100.0`` when there are no
        losses over the window.

    Raises:
        ValueError: If ``period`` is non-positive or there are too few prices.
    """
    if period <= 0:
        raise ValueError(f"period must be positive, got {period}")
    if len(prices) < period + 1:
        raise ValueError(f"need at least {period + 1} prices, got {len(prices)}")

    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]

    # Seed with the simple average over the first ``period`` changes.
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    # Then apply Wilder's smoothing across the remainder.
    for g, loss in zip(gains[period:], losses[period:], strict=True):
        avg_gain = (avg_gain * (period - 1) + g) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0.0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


class RsiStrategy:
    """A mean-reversion strategy driven by Wilder's RSI.

    Emits :attr:`Signal.BUY` when RSI falls to/under ``lower`` (oversold) and
    :attr:`Signal.SELL` when it rises to/over ``upper`` (overbought); otherwise
    :attr:`Signal.HOLD`.

    Args:
        period: RSI look-back length; must be positive.
        lower: Oversold threshold in ``(0, upper)``.
        upper: Overbought threshold in ``(lower, 100)``.
    """

    name = "rsi"

    def __init__(self, period: int = 14, *, lower: float = 30.0, upper: float = 70.0) -> None:
        if period <= 0:
            raise ValueError(f"period must be positive, got {period}")
        if not 0.0 < lower < upper < 100.0:
            raise ValueError(f"require 0 < lower < upper < 100, got {lower}/{upper}")
        self.period = period
        self.lower = lower
        self.upper = upper

    @property
    def warmup(self) -> int:
        """Minimum number of prices required before a signal can be emitted."""
        return self.period + 1

    def signal(self, prices: Sequence[float]) -> Signal:
        """Compute the RSI signal for the current price window.

        Args:
            prices: Price series with the most recent price last. Must contain
                at least ``period + 1`` prices.

        Returns:
            :attr:`Signal.BUY` when oversold, :attr:`Signal.SELL` when
            overbought, else :attr:`Signal.HOLD`.

        Raises:
            ValueError: If fewer than ``period + 1`` prices are supplied.
        """
        value = rsi(prices, self.period)
        if value <= self.lower:
            return Signal.BUY
        if value >= self.upper:
            return Signal.SELL
        return Signal.HOLD
