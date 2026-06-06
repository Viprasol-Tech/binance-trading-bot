"""Command-line interface for Binance Trading Bot.

Subcommands:

* ``demo`` - build a signed order request (not sent) and run a tiny paper loop.
* ``sign`` - sign an arbitrary ``key=value`` payload and print the request.
* ``backtest`` - run a strategy over a price series and print metrics.
* ``strategies`` - list the built-in strategies.
* ``version`` - print the installed version.

Nothing here makes a network call: signing is offline and the backtest is pure
arithmetic over an in-memory series. No API keys, no risk.

Part of Binance Trading Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from binance_trading_bot import __version__
from binance_trading_bot.backtest import run_backtest
from binance_trading_bot.client import BinanceClient
from binance_trading_bot.config import BotConfig
from binance_trading_bot.paper import PaperAccount
from binance_trading_bot.strategy import SmaCrossStrategy

app = typer.Typer(add_completion=False, help="Binance Trading Bot - by Viprasol Tech.")
console = Console()

#: A sample sine-ish price series used by ``demo`` and as the backtest default.
SAMPLE_PRICES: tuple[float, ...] = (
    100.0,
    101.0,
    102.0,
    103.0,
    102.0,
    101.0,
    100.0,
    99.0,
    100.5,
    102.5,
    104.0,
    103.0,
    101.0,
    99.5,
    98.0,
    99.0,
    101.0,
    103.5,
    105.0,
    106.0,
)


@app.command()
def version() -> None:
    """Print the installed version."""
    console.print(f"binance-trading-bot [bold cyan]{__version__}[/] - by Viprasol Tech")


@app.command()
def strategies() -> None:
    """List the built-in strategies and their parameters."""
    table = Table(title="Built-in strategies")
    table.add_column("Name", style="cyan")
    table.add_column("Parameters")
    table.add_column("Logic")
    table.add_row("sma_cross", "fast, slow", "BUY when fast SMA > slow SMA, else SELL/HOLD")
    table.add_row("rsi", "rsi_period, rsi_lower, rsi_upper", "BUY oversold, SELL overbought")
    console.print(table)


@app.command()
def sign(
    payload: str = typer.Argument(..., help="Params as 'k=v&k=v', e.g. 'symbol=BTCUSDT&side=BUY'."),
    path: str = typer.Option("/api/v3/order", help="Endpoint path."),
    method: str = typer.Option("POST", help="HTTP method."),
    api_key: str = typer.Option("DEMO_API_KEY", help="API key for the X-MBX-APIKEY header."),
    api_secret: str = typer.Option("DEMO_API_SECRET", help="API secret used to sign."),
    timestamp_ms: int = typer.Option(1_700_000_000_000, help="Fixed timestamp (ms)."),
) -> None:
    """Sign a ``key=value`` payload and print the prepared request (not sent)."""
    params: dict[str, object] = {}
    for pair in payload.split("&"):
        if not pair:
            continue
        key, sep, value = pair.partition("=")
        if not sep:
            console.print(f"[red]bad pair (missing '='): {pair!r}[/]")
            raise typer.Exit(code=1)
        params[key] = value
    client = BinanceClient(api_key, api_secret)
    req = client.prepare_signed_request(method, path, params, timestamp_ms=timestamp_ms)
    console.print("[bold]Prepared signed request (not sent):[/]")
    console.print(f"  method:       {req['method']}")
    console.print(f"  url:          {req['url']}")
    console.print(f"  headers:      {req['headers']}")
    console.print(f"  query_string: {req['query_string']}")


@app.command()
def backtest(
    symbol: str = typer.Option("BTCUSDT", help="Trading pair."),
    strategy: str = typer.Option("sma_cross", help="Strategy: sma_cross or rsi."),
    start_cash: float = typer.Option(10_000.0, help="Starting paper balance."),
    order_quantity: float = typer.Option(1.0, help="Quantity per trade."),
    fast: int = typer.Option(2, help="Fast SMA window (sma_cross)."),
    slow: int = typer.Option(4, help="Slow SMA window (sma_cross)."),
    rsi_period: int = typer.Option(14, help="RSI period (rsi)."),
    fee_rate: float = typer.Option(0.0, help="Per-trade fee fraction, e.g. 0.001."),
) -> None:
    """Run a strategy over the sample price series and print metrics."""
    try:
        config = BotConfig(
            symbol=symbol,
            strategy=strategy,
            start_cash=start_cash,
            order_quantity=order_quantity,
            fast=fast,
            slow=slow,
            rsi_period=rsi_period,
            fee_rate=fee_rate,
        )
    except ValueError as exc:
        console.print(f"[red]invalid config:[/] {exc}")
        raise typer.Exit(code=1) from exc

    result = run_backtest(list(SAMPLE_PRICES), config)
    table = Table(title=f"Backtest: {result.strategy} on {result.symbol}")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    table.add_row("Start equity", f"${result.start_equity:,.2f}")
    table.add_row("Final equity", f"${result.final_equity:,.2f}")
    table.add_row("Total return", f"{result.total_return * 100:+.2f}%")
    table.add_row("Max drawdown", f"{result.max_drawdown * 100:.2f}%")
    table.add_row("Sharpe (per-bar)", f"{result.sharpe:.3f}")
    table.add_row("Trades", str(result.trades))
    console.print(table)


@app.command()
def demo(
    symbol: str = typer.Option("BTCUSDT", help="Trading pair to demo."),
    start_cash: float = typer.Option(10_000.0, help="Starting paper USDT balance."),
) -> None:
    """Build a signed request, run a SMA-cross strategy, and print balances."""
    # 1. Build a real signed order request (demo keys; nothing is sent).
    client = BinanceClient("DEMO_API_KEY", "DEMO_API_SECRET")
    prepared = client.prepare_limit_order(
        symbol, "BUY", 0.01, 25_000.0, timestamp_ms=1_700_000_000_000
    )
    console.print("[bold]Prepared signed LIMIT order request (not sent):[/]")
    console.print(f"  method:  {prepared['method']}")
    console.print(f"  url:     {prepared['url']}")
    console.print(f"  headers: {prepared['headers']}")

    # 2. Drive the paper account with a tiny SMA-cross strategy.
    prices = list(SAMPLE_PRICES[:10])
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
