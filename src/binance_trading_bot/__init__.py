"""Binance API trading bot with HMAC request signing and paper trading.

Part of Binance Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from binance_trading_bot.auth import build_signed_query, sign_query
from binance_trading_bot.backtest import (
    BacktestResult,
    build_strategy,
    max_drawdown,
    run_backtest,
    sharpe_ratio,
)
from binance_trading_bot.client import BinanceClient
from binance_trading_bot.config import BotConfig
from binance_trading_bot.paper import Fill, PaperAccount, Side
from binance_trading_bot.strategy import (
    RsiStrategy,
    Signal,
    SmaCrossStrategy,
    rsi,
    sma,
)

__version__ = "0.2.0"

__all__ = [
    "BacktestResult",
    "BinanceClient",
    "BotConfig",
    "Fill",
    "PaperAccount",
    "RsiStrategy",
    "Side",
    "Signal",
    "SmaCrossStrategy",
    "__version__",
    "build_signed_query",
    "build_strategy",
    "max_drawdown",
    "rsi",
    "run_backtest",
    "sharpe_ratio",
    "sign_query",
    "sma",
]
