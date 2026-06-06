"""Tests for the Typer CLI surface."""

from __future__ import annotations

from typer.testing import CliRunner

from binance_trading_bot import __version__
from binance_trading_bot.cli import app

runner = CliRunner()


def test_version_command_prints_version() -> None:
    """`version` prints the current package version."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_strategies_command_lists_builtins() -> None:
    """`strategies` lists both built-in strategies."""
    result = runner.invoke(app, ["strategies"])
    assert result.exit_code == 0
    assert "sma_cross" in result.stdout
    assert "rsi" in result.stdout


def test_sign_command_outputs_signed_request() -> None:
    """`sign` produces a signed query string ending in a signature."""
    result = runner.invoke(app, ["sign", "symbol=BTCUSDT&side=BUY"])
    assert result.exit_code == 0
    assert "signature=" in result.stdout
    assert "symbol=BTCUSDT" in result.stdout


def test_sign_command_rejects_bad_pair() -> None:
    """A payload token without '=' exits non-zero."""
    result = runner.invoke(app, ["sign", "symbolBTCUSDT"])
    assert result.exit_code == 1


def test_backtest_command_prints_metrics() -> None:
    """`backtest` runs and prints the metrics table."""
    result = runner.invoke(app, ["backtest", "--strategy", "sma_cross"])
    assert result.exit_code == 0
    assert "Total return" in result.stdout
    assert "Trades" in result.stdout


def test_backtest_command_rejects_invalid_config() -> None:
    """An invalid strategy name exits non-zero with a message."""
    result = runner.invoke(app, ["backtest", "--strategy", "nope"])
    assert result.exit_code == 1


def test_demo_command_runs() -> None:
    """`demo` builds a signed order and runs the paper loop."""
    result = runner.invoke(app, ["demo"])
    assert result.exit_code == 0
    assert "Final equity" in result.stdout
