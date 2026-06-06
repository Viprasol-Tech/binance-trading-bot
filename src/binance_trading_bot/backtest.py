"""Deterministic paper backtester with performance metrics.

:func:`run_backtest` walks a price series, asks a strategy for a signal at each
step (once enough warm-up data exists), and routes BUY/SELL signals through a
:class:`~binance_trading_bot.paper.PaperAccount`. It records the equity curve
and returns a :class:`BacktestResult` with the metrics traders actually look at:
total return, max drawdown, Sharpe-like ratio, and trade count.

Everything is pure arithmetic over an in-memory list — no network, no clock,
fully reproducible. Optional ``fee_rate`` deducts a taker fee on each fill.

Part of Binance Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from math import sqrt
from typing import Protocol

from binance_trading_bot.config import BotConfig
from binance_trading_bot.paper import PaperAccount
from binance_trading_bot.strategy import RsiStrategy, Signal, SmaCrossStrategy


class Strategy(Protocol):
    """Structural type for any object usable as a backtest strategy."""

    name: str

    @property
    def warmup(self) -> int:
        """Number of leading prices needed before the first signal."""
        ...

    def signal(self, prices: Sequence[float]) -> Signal:
        """Return a trading signal for the supplied price window."""
        ...


@dataclass(frozen=True)
class BacktestResult:
    """Outcome and metrics of a single backtest run.

    Attributes:
        symbol: The traded symbol.
        strategy: Strategy name.
        start_equity: Equity before the first bar.
        final_equity: Equity marked at the last price.
        trades: Number of fills executed.
        total_return: Fractional return, e.g. ``0.05`` for +5%.
        max_drawdown: Worst peak-to-trough drop as a positive fraction.
        sharpe: Annualisation-free Sharpe-like ratio of per-bar returns.
        equity_curve: Equity marked to market after every bar.
    """

    symbol: str
    strategy: str
    start_equity: float
    final_equity: float
    trades: int
    total_return: float
    max_drawdown: float
    sharpe: float
    equity_curve: tuple[float, ...]


def build_strategy(config: BotConfig) -> Strategy:
    """Instantiate the strategy named by ``config``.

    Args:
        config: The validated run configuration.

    Returns:
        A ready-to-use strategy instance.
    """
    if config.strategy == "rsi":
        return RsiStrategy(config.rsi_period, lower=config.rsi_lower, upper=config.rsi_upper)
    return SmaCrossStrategy(fast=config.fast, slow=config.slow)


def max_drawdown(equity_curve: Sequence[float]) -> float:
    """Return the maximum peak-to-trough drawdown as a positive fraction.

    Args:
        equity_curve: Equity values over time.

    Returns:
        The worst drawdown (e.g. ``0.2`` for a 20% drop), or ``0.0`` if the
        curve never declines or is empty.
    """
    peak = float("-inf")
    worst = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        if peak > 0:
            worst = max(worst, (peak - value) / peak)
    return worst


def sharpe_ratio(equity_curve: Sequence[float]) -> float:
    """Return a simple (non-annualised) Sharpe ratio of per-bar returns.

    Computes the mean of bar-to-bar returns divided by their population
    standard deviation. With fewer than two equity points, or zero volatility,
    returns ``0.0``.

    Args:
        equity_curve: Equity values over time.

    Returns:
        Mean return divided by standard deviation, or ``0.0`` when undefined.
    """
    if len(equity_curve) < 2:
        return 0.0
    returns = [
        (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
        for i in range(1, len(equity_curve))
        if equity_curve[i - 1] != 0
    ]
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / len(returns)
    std = sqrt(variance)
    if std == 0.0:
        return 0.0
    return mean / std


def run_backtest(prices: Sequence[float], config: BotConfig) -> BacktestResult:
    """Run ``config``'s strategy over ``prices`` and return its metrics.

    On each bar after warm-up the strategy emits a signal: a ``BUY`` opens or
    adds to the position when cash allows; a ``SELL`` closes ``order_quantity``
    when held. A taker ``fee_rate`` (if any) is debited from cash per fill.

    Args:
        prices: Closing-price series, oldest first; must be non-empty.
        config: The validated run configuration.

    Returns:
        A :class:`BacktestResult` with the equity curve and metrics.

    Raises:
        ValueError: If ``prices`` is empty.
    """
    if not prices:
        raise ValueError("prices must be non-empty")

    strategy = build_strategy(config)
    account = PaperAccount(cash=config.start_cash)
    symbol = config.symbol
    qty = config.order_quantity
    fee_rate = config.fee_rate
    equity_curve: list[float] = []

    for i, price in enumerate(prices):
        window = prices[: i + 1]
        if len(window) >= strategy.warmup:
            sig = strategy.signal(window)
            if sig is Signal.BUY:
                cost = qty * price * (1 + fee_rate)
                if account.cash >= cost:
                    account.buy(symbol, qty, price)
                    account.cash -= qty * price * fee_rate
            elif sig is Signal.SELL and account.position(symbol) >= qty:
                account.sell(symbol, qty, price)
                account.cash -= qty * price * fee_rate
        equity_curve.append(account.equity({symbol: price}))

    start_equity = config.start_cash
    final_equity = equity_curve[-1]
    total_return = (final_equity - start_equity) / start_equity if start_equity else 0.0

    return BacktestResult(
        symbol=symbol,
        strategy=strategy.name,
        start_equity=start_equity,
        final_equity=final_equity,
        trades=len(account.fills),
        total_return=total_return,
        max_drawdown=max_drawdown(equity_curve),
        sharpe=sharpe_ratio(equity_curve),
        equity_curve=tuple(equity_curve),
    )
