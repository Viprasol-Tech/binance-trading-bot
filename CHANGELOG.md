# Changelog

All notable changes to this project are documented here. Format based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning follows
[SemVer](https://semver.org/).

## [0.2.0] - 2025

### Added
- Endpoint builders for klines/candlesticks (`prepare_klines`) and the signed
  account/balances endpoint (`prepare_account`).
- New order types: `prepare_limit_order`, `prepare_stop_loss_limit_order`, and
  `prepare_oco_order`, plus a signed `prepare_cancel_order`.
- Time-in-force validation (`GTC` / `IOC` / `FOK`) shared across order builders.
- Wilder's RSI indicator (`rsi`) and an `RsiStrategy` mean-reversion strategy,
  with a `warmup` property added to all strategies.
- Typed, validated `BotConfig` (pydantic) for run configuration.
- A deterministic paper `run_backtest` with metrics: total return, max drawdown,
  per-bar Sharpe ratio, equity curve, and an optional taker `fee_rate`.
- New CLI subcommands: `sign`, `backtest`, and `strategies`.
- Roughly doubled the test suite (30 -> 81 tests) covering new orders,
  endpoints, RSI, config validation, the backtester, and the CLI.

### Changed
- `demo` now showcases a signed `LIMIT` order and a longer sample price series.
- Public API re-exported from the package root for ergonomic imports.

## [0.1.0] - 2025

### Added
- Initial release of binance-trading-bot: Binance API trading bot with HMAC request signing and paper trading.
