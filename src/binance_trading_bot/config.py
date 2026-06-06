"""Typed, validated configuration for the bot.

:class:`BotConfig` is a pydantic model that captures everything a run needs:
which market and strategy to trade, paper-account sizing, and execution
parameters. It validates eagerly so a bad value fails fast with a clear error
rather than midway through a backtest.

Part of Binance Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

StrategyName = Literal["sma_cross", "rsi"]


class BotConfig(BaseModel):
    """Validated run configuration for a backtest or paper session.

    Attributes:
        symbol: Trading pair, upper-cased on assignment, e.g. ``"BTCUSDT"``.
        strategy: Which strategy to run (``"sma_cross"`` or ``"rsi"``).
        start_cash: Starting quote-currency balance; must be positive.
        order_quantity: Base-asset quantity per trade; must be positive.
        fast: Fast SMA window (``sma_cross`` only).
        slow: Slow SMA window (``sma_cross`` only); must exceed ``fast``.
        rsi_period: RSI look-back (``rsi`` only); must be positive.
        rsi_lower: RSI oversold threshold.
        rsi_upper: RSI overbought threshold.
        fee_rate: Per-trade taker fee as a fraction (e.g. ``0.001`` = 0.1%).
    """

    model_config = {"frozen": True, "extra": "forbid"}

    symbol: str = Field(default="BTCUSDT", min_length=1)
    strategy: StrategyName = "sma_cross"
    start_cash: float = Field(default=10_000.0, gt=0)
    order_quantity: float = Field(default=1.0, gt=0)

    fast: int = Field(default=2, gt=0)
    slow: int = Field(default=4, gt=0)

    rsi_period: int = Field(default=14, gt=0)
    rsi_lower: float = Field(default=30.0, gt=0, lt=100)
    rsi_upper: float = Field(default=70.0, gt=0, lt=100)

    fee_rate: float = Field(default=0.0, ge=0, lt=1)

    @model_validator(mode="after")
    def _normalise_and_check(self) -> BotConfig:
        """Upper-case the symbol and enforce cross-field constraints."""
        # ``frozen`` forbids attribute assignment, so rebuild via __dict__.
        object.__setattr__(self, "symbol", self.symbol.upper())
        if self.fast >= self.slow:
            raise ValueError(f"fast ({self.fast}) must be less than slow ({self.slow})")
        if not self.rsi_lower < self.rsi_upper:
            raise ValueError(
                f"rsi_lower ({self.rsi_lower}) must be less than rsi_upper ({self.rsi_upper})"
            )
        return self
