"""In-memory paper-trading account.

``PaperAccount`` simulates a single-quote-currency spot account: it holds cash
and a per-symbol base-asset position, and fills market buy/sell orders at a
caller-supplied price. No fees, no slippage, no network — just exact arithmetic
so you can dry-run a strategy with confidence before risking real funds.

Part of Binance Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Side(str, Enum):
    """Order side."""

    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class Fill:
    """A single executed paper trade."""

    symbol: str
    side: Side
    quantity: float
    price: float

    @property
    def notional(self) -> float:
        """The quote-currency value of this fill (``quantity * price``)."""
        return self.quantity * self.price


@dataclass
class PaperAccount:
    """A simulated spot account with cash and per-symbol positions.

    Args:
        cash: Starting quote-currency balance (e.g. USDT).
        positions: Optional starting base-asset positions keyed by symbol.
    """

    cash: float
    positions: dict[str, float] = field(default_factory=dict)
    fills: list[Fill] = field(default_factory=list)

    def position(self, symbol: str) -> float:
        """Return the current base-asset quantity held for ``symbol``."""
        return self.positions.get(symbol, 0.0)

    def buy(self, symbol: str, quantity: float, price: float) -> Fill:
        """Market-buy ``quantity`` of ``symbol`` at ``price``.

        Cash is debited by ``quantity * price`` and the position increases.

        Args:
            symbol: Trading pair, e.g. ``"BTCUSDT"``.
            quantity: Base-asset quantity to buy; must be positive.
            price: Fill price in quote currency; must be positive.

        Returns:
            The recorded :class:`Fill`.

        Raises:
            ValueError: If ``quantity``/``price`` are non-positive or there is
                insufficient cash to cover the notional.
        """
        self._validate(quantity, price)
        cost = quantity * price
        if cost > self.cash:
            raise ValueError(f"insufficient cash: need {cost:.8f}, have {self.cash:.8f}")
        self.cash -= cost
        self.positions[symbol] = self.position(symbol) + quantity
        fill = Fill(symbol, Side.BUY, quantity, price)
        self.fills.append(fill)
        return fill

    def sell(self, symbol: str, quantity: float, price: float) -> Fill:
        """Market-sell ``quantity`` of ``symbol`` at ``price``.

        The position is reduced and cash is credited by ``quantity * price``.

        Args:
            symbol: Trading pair, e.g. ``"BTCUSDT"``.
            quantity: Base-asset quantity to sell; must be positive.
            price: Fill price in quote currency; must be positive.

        Returns:
            The recorded :class:`Fill`.

        Raises:
            ValueError: If ``quantity``/``price`` are non-positive or the
                position is too small to cover the sale.
        """
        self._validate(quantity, price)
        held = self.position(symbol)
        if quantity > held:
            raise ValueError(
                f"insufficient position in {symbol}: need {quantity:.8f}, have {held:.8f}"
            )
        self.positions[symbol] = held - quantity
        self.cash += quantity * price
        fill = Fill(symbol, Side.SELL, quantity, price)
        self.fills.append(fill)
        return fill

    def equity(self, marks: dict[str, float]) -> float:
        """Return total account value: cash plus positions marked to ``marks``.

        Args:
            marks: Current price per symbol. Symbols absent from ``marks`` are
                valued at zero.

        Returns:
            Total equity in quote currency.
        """
        holdings = sum(qty * marks.get(sym, 0.0) for sym, qty in self.positions.items())
        return self.cash + holdings

    @staticmethod
    def _validate(quantity: float, price: float) -> None:
        """Reject non-positive quantity or price."""
        if quantity <= 0:
            raise ValueError(f"quantity must be positive, got {quantity}")
        if price <= 0:
            raise ValueError(f"price must be positive, got {price}")
