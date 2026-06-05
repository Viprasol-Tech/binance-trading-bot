"""Command-line interface for Binance Trading Bot.

``binance-trading-bot demo`` builds a real signed Binance order request (without
sending it) and then runs a few market trades through the paper account,
printing the resulting balances — no API keys, no network, no risk.

Part of Binance Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import typer
from rich.console import Console

from binance_trading_bot import __version__
from binance_trading_bot.client import BinanceClient
from binance_trading_bot.paper import PaperAccount
from binance_trading_bot.strategy import SmaCrossStrategy

app = typer.Typer(add_completion=False, help="Binance Trading Bot - by Viprasol Tech.")
console = Console()


@app.command()
def version() -> None:
    """Print the installed version."""
    console.print(f"binance-trading-bot [bold cyan]{__version__}[/] - by Viprasol Tech")


@app.command()
def demo(
    symbol: str = typer.Option("BTCUSDT", help="Trading pair to demo."),
    start_cash: float = typer.Option(10_000.0, help="Starting paper USDT balance."),
) -> None:
    """Build a signed request, run a SMA-cross strategy, and print balances."""
    # 1. Build a real signed order request (demo keys; nothing is sent).
    client = BinanceClient("DEMO_API_KEY", "DEMO_API_SECRET")
    prepared = client.prepare_new_order(symbol, "BUY", 0.01, timestamp_ms=1_700_000_000_000)
    console.print("[bold]Prepared signed order request (not sent):[/]")
    console.print(f"  method:  {prepared['method']}")
    console.print(f"  url:     {prepared['url']}")
    console.print(f"  headers: {prepared['headers']}")

    # 2. Drive the paper account with a tiny SMA-cross strategy.
    prices = [100.0, 101.0, 102.0, 103.0, 102.0, 101.0, 100.0, 99.0, 100.5, 102.5]
    strat = SmaCrossStrategy(fast=2, slow=4)
    account = PaperAccount(cash=start_cash)
    quantity = 1.0

    console.print(f"\n[bold]Paper trading {symbol} (SMA {strat.fast}/{strat.slow}):[/]")
    for i in range(strat.slow, len(prices)):
        window = prices[: i + 1]
        price = prices[i]
        sig = strat.signal(window)
        if sig.value == "BUY" and account.cash >= quantity * price:
            account.buy(symbol, quantity, price)
            console.print(f"  t={i:>2}  price={price:7.2f}  [green]BUY[/]  {quantity}")
        elif sig.value == "SELL" and account.position(symbol) >= quantity:
            account.sell(symbol, quantity, price)
            console.print(f"  t={i:>2}  price={price:7.2f}  [red]SELL[/] {quantity}")
        else:
            console.print(f"  t={i:>2}  price={price:7.2f}  HOLD")

    final_price = prices[-1]
    equity = account.equity({symbol: final_price})
    console.print(f"\nFills:        {len(account.fills)}")
    console.print(f"Cash:         [bold]${account.cash:,.2f}[/]")
    console.print(f"Position:     {account.position(symbol)} {symbol}")
    console.print(f"Final equity: [bold green]${equity:,.2f}[/] (started ${start_cash:,.2f})")


if __name__ == "__main__":
    app()
