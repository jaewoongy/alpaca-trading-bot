# Alpaca Trading Bot (MCP Server)

An MCP server exposing Alpaca **paper trading** as tools for Claude (or any MCP client): check quotes, manage a watchlist, check market hours, and place simulated trades. No real money is ever at risk — `paper=True` is hardcoded in `trading_mcp_server.py`.

## Setup

```bash
python -m venv .venv
.venv/Scripts/activate   # or source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env     # then fill in your Alpaca paper trading keys
```

Get paper trading API keys from the Alpaca dashboard (alpaca.markets) — sign up, then generate a key under the Paper Trading section (not Live).

## Running

```bash
python trading_mcp_server.py
```

This runs as a stdio MCP server. To register it with Claude Code:

```bash
claude mcp add alpaca-trading -- python /full/path/to/trading_mcp_server.py
```

## Tools

- `get_account` — cash, buying power, portfolio value
- `get_quotes(symbols?)` — latest bid/ask for given tickers, or the whole watchlist if omitted
- `get_watchlist` / `add_to_watchlist(symbol)` / `remove_from_watchlist(symbol)` — manage `watchlist.json`
- `is_market_open` — checks Alpaca's trading calendar (accounts for weekends + market holidays)
- `list_positions` — current open positions
- `place_order(symbol, qty, side)` — market order, paper trading only
- `list_orders` — recent order history

## Watchlist

`watchlist.json` seeds the top 25 QQQM (Nasdaq-100) holdings by weight, verified via stockanalysis.com. Edit the file directly, or use the `add_to_watchlist` / `remove_from_watchlist` tools.

## Not yet built

- **Scheduled runs** (e.g. every 30 minutes during market hours): the MCP server itself only responds to on-demand tool calls — it does not self-schedule. Options discussed but not decided: a local script + Task Scheduler/cron, or an Azure Function with a timer trigger (Azure Functions has GA support for MCP tool triggers as of Build 2026 — see `functions-bindings-mcp-tool-trigger` docs). `is_market_open` is the building block for whichever scheduler wraps it.
- **Autonomous vs. approval-gated trading**: not yet decided whether the AI should place orders on its own or require confirmation each time.
