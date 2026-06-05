"""Tests for the paper-trading account."""

from __future__ import annotations

import pytest

from binance_trading_bot.paper import Fill, PaperAccount, Side


def test_buy_updates_cash_and_position() -> None:
    """A buy debits cash by notional and increases the position."""
    acc = PaperAccount(cash=1_000.0)
    fill = acc.buy("BTCUSDT", quantity=2.0, price=100.0)

    assert acc.cash == pytest.approx(800.0)
    assert acc.position("BTCUSDT") == pytest.approx(2.0)
    assert fill == Fill("BTCUSDT", Side.BUY, 2.0, 100.0)
    assert fill.notional == pytest.approx(200.0)


def test_sell_updates_cash_and_position() -> None:
    """A sell credits cash by notional and decreases the position."""
    acc = PaperAccount(cash=1_000.0, positions={"BTCUSDT": 5.0})
    acc.sell("BTCUSDT", quantity=3.0, price=50.0)

    assert acc.cash == pytest.approx(1_150.0)
    assert acc.position("BTCUSDT") == pytest.approx(2.0)


def test_buy_then_sell_round_trip_is_cash_neutral_at_flat_price() -> None:
    """Buying and selling the same qty at the same price restores starting cash."""
    acc = PaperAccount(cash=500.0)
    acc.buy("ETHUSDT", 1.0, 200.0)
    acc.sell("ETHUSDT", 1.0, 200.0)

    assert acc.cash == pytest.approx(500.0)
    assert acc.position("ETHUSDT") == pytest.approx(0.0)
    assert len(acc.fills) == 2


def test_buy_rejects_insufficient_cash() -> None:
    """Buying beyond available cash raises ValueError and leaves state intact."""
    acc = PaperAccount(cash=100.0)
    with pytest.raises(ValueError, match="insufficient cash"):
        acc.buy("BTCUSDT", 2.0, 100.0)
    assert acc.cash == pytest.approx(100.0)
    assert acc.position("BTCUSDT") == pytest.approx(0.0)


def test_sell_rejects_insufficient_position() -> None:
    """Selling more than held raises ValueError."""
    acc = PaperAccount(cash=0.0, positions={"BTCUSDT": 1.0})
    with pytest.raises(ValueError, match="insufficient position"):
        acc.sell("BTCUSDT", 2.0, 100.0)


@pytest.mark.parametrize("qty,price", [(0.0, 100.0), (-1.0, 100.0), (1.0, 0.0), (1.0, -5.0)])
def test_non_positive_inputs_rejected(qty: float, price: float) -> None:
    """Non-positive quantity or price is rejected for both sides."""
    acc = PaperAccount(cash=10_000.0, positions={"BTCUSDT": 100.0})
    with pytest.raises(ValueError):
        acc.buy("BTCUSDT", qty, price)
    with pytest.raises(ValueError):
        acc.sell("BTCUSDT", qty, price)


def test_equity_marks_positions_to_market() -> None:
    """Equity equals cash plus position value at the supplied marks."""
    acc = PaperAccount(cash=1_000.0, positions={"BTCUSDT": 2.0})
    assert acc.equity({"BTCUSDT": 150.0}) == pytest.approx(1_300.0)
    # Unmarked symbols are valued at zero.
    assert acc.equity({}) == pytest.approx(1_000.0)
