"""Tests for the paper backtester and its metrics."""

from __future__ import annotations

import pytest

from binance_trading_bot.backtest import (
    build_strategy,
    max_drawdown,
    run_backtest,
    sharpe_ratio,
)
from binance_trading_bot.config import BotConfig
from binance_trading_bot.strategy import RsiStrategy, SmaCrossStrategy


def test_max_drawdown_simple_case() -> None:
    """Drawdown is the worst peak-to-trough drop as a fraction."""
    # Peak 100 -> trough 80 is a 20% drawdown.
    assert max_drawdown([100.0, 110.0, 88.0, 120.0]) == pytest.approx(0.2)


def test_max_drawdown_monotonic_increase_is_zero() -> None:
    """A never-declining curve has zero drawdown."""
    assert max_drawdown([10.0, 20.0, 30.0]) == pytest.approx(0.0)


def test_max_drawdown_empty_is_zero() -> None:
    """An empty curve yields zero drawdown rather than an error."""
    assert max_drawdown([]) == 0.0


def test_sharpe_zero_for_flat_curve() -> None:
    """A flat equity curve has zero volatility -> Sharpe 0."""
    assert sharpe_ratio([100.0, 100.0, 100.0]) == pytest.approx(0.0)


def test_sharpe_positive_for_steady_growth() -> None:
    """Steadily compounding equity yields a positive Sharpe."""
    curve = [100.0 * (1.01**i) for i in range(20)]
    assert sharpe_ratio(curve) > 0.0


def test_sharpe_short_curve_is_zero() -> None:
    """Fewer than two returns gives a defined zero."""
    assert sharpe_ratio([100.0]) == 0.0


def test_build_strategy_dispatches_on_name() -> None:
    """build_strategy returns the correct concrete strategy."""
    assert isinstance(build_strategy(BotConfig(strategy="sma_cross")), SmaCrossStrategy)
    assert isinstance(build_strategy(BotConfig(strategy="rsi")), RsiStrategy)


def test_run_backtest_rejects_empty_prices() -> None:
    """An empty price series is rejected."""
    with pytest.raises(ValueError, match="non-empty"):
        run_backtest([], BotConfig())


def test_run_backtest_records_full_equity_curve() -> None:
    """The equity curve has one point per price bar."""
    prices = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    result = run_backtest(prices, BotConfig(fast=2, slow=3, order_quantity=1.0))
    assert len(result.equity_curve) == len(prices)
    assert result.start_equity == pytest.approx(10_000.0)


def test_run_backtest_profits_on_uptrend_with_sma() -> None:
    """Buying into a clean uptrend leaves equity above the start."""
    prices = [float(p) for p in range(100, 140)]
    result = run_backtest(prices, BotConfig(fast=2, slow=5, order_quantity=1.0))
    assert result.trades > 0
    assert result.final_equity > result.start_equity
    assert result.total_return > 0.0


def test_run_backtest_no_trades_leaves_cash_untouched() -> None:
    """A series shorter than warm-up produces no trades and flat equity."""
    result = run_backtest([100.0, 101.0], BotConfig(fast=2, slow=4))
    assert result.trades == 0
    assert result.final_equity == pytest.approx(result.start_equity)


def test_fee_rate_reduces_final_equity() -> None:
    """A non-zero fee makes the fee'd run end with less equity than free trading."""
    prices = [float(p) for p in range(100, 140)]
    free = run_backtest(prices, BotConfig(fast=2, slow=5, order_quantity=1.0, fee_rate=0.0))
    fees = run_backtest(prices, BotConfig(fast=2, slow=5, order_quantity=1.0, fee_rate=0.01))
    assert fees.trades == free.trades
    assert fees.final_equity < free.final_equity


def test_run_backtest_with_rsi_strategy_runs() -> None:
    """The RSI strategy backtests end-to-end and reports its name."""
    prices = [100.0 + (i % 7) for i in range(60)]
    result = run_backtest(prices, BotConfig(strategy="rsi", rsi_period=14, order_quantity=0.5))
    assert result.strategy == "rsi"
    assert len(result.equity_curve) == len(prices)
