import json
import os
from pathlib import Path

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from pipeline import screen_watchlist
from signals.technicals import get_technicals_signal

load_dotenv()

ALPACA_API_KEY = os.environ["ALPACA_API_KEY"]
ALPACA_SECRET_KEY = os.environ["ALPACA_SECRET_KEY"]

# paper=True is intentionally hardcoded — this server must never place a live
# trade, regardless of which keys end up in the environment.
trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=True)
data_client = StockHistoricalDataClient(ALPACA_API_KEY, ALPACA_SECRET_KEY)

WATCHLIST_PATH = Path(__file__).parent / "watchlist.json"

mcp = FastMCP("alpaca-paper-trading", stateless_http=True, host="0.0.0.0", port=8000)


def load_watchlist() -> list[str]:
    return json.loads(WATCHLIST_PATH.read_text())


def save_watchlist(symbols: list[str]) -> None:
    WATCHLIST_PATH.write_text(json.dumps(symbols, indent=2) + "\n")


@mcp.tool()
def get_account() -> str:
    """Get paper trading account summary: cash, buying power, portfolio value."""
    account = trading_client.get_account()
    return (
        f"cash=${account.cash}, buying_power=${account.buying_power}, "
        f"portfolio_value=${account.portfolio_value}, equity=${account.equity}"
    )


@mcp.tool()
def get_quotes(symbols: list[str] | None = None) -> str:
    """Get the latest bid/ask quote for one or more stock symbols.

    Args:
        symbols: Tickers to quote, e.g. ["AAPL", "TSLA"]. Defaults to the
            saved watchlist if omitted.
    """
    symbols = [s.upper() for s in (symbols or load_watchlist())]
    request = StockLatestQuoteRequest(symbol_or_symbols=symbols)
    quotes = data_client.get_stock_latest_quote(request)
    return "\n".join(
        f"{symbol}: bid=${quotes[symbol].bid_price} ask=${quotes[symbol].ask_price}"
        for symbol in symbols
    )


@mcp.tool()
def screen_technicals(symbols: list[str] | None = None) -> str:
    """Screen symbols for a non-neutral technical signal (bullish/bearish).

    Cheap, deterministic filter based on SMA/RSI/MACD/volume - no LLM
    judgment involved. Use this first to narrow down which symbols are
    worth investigating further with news/sentiment before deciding.

    Args:
        symbols: Tickers to screen. Defaults to the saved watchlist if omitted.
    """
    symbols = [s.upper() for s in (symbols or load_watchlist())]
    shortlist = screen_watchlist(data_client, symbols)
    if not shortlist:
        return "No symbols cleared the technicals filter."
    lines = []
    for entry in shortlist:
        technicals = entry.signals[0]
        lines.append(
            f"{entry.symbol}: {technicals.signal} (confidence={technicals.confidence}) "
            f"- {technicals.rationale}"
        )
    return "\n".join(lines)


@mcp.tool()
def get_technicals(symbol: str) -> str:
    """Get the technical indicator signal for a single stock symbol.

    Computes SMA/RSI/MACD/volume from recent hourly bars and classifies
    the result as bullish, bearish, or neutral, with the underlying
    indicator values included for the caller's own judgment.

    Args:
        symbol: Stock ticker, e.g. AAPL.
    """
    signal = get_technicals_signal(data_client, symbol.upper())
    return (
        f"{symbol.upper()}: {signal.signal} (confidence={signal.confidence})\n"
        f"details: {signal.details}\n"
        f"rationale: {signal.rationale}"
    )


@mcp.tool()
def get_watchlist() -> str:
    """List the tickers currently on the watchlist."""
    return ", ".join(load_watchlist())


@mcp.tool()
def add_to_watchlist(symbol: str) -> str:
    """Add a ticker to the watchlist."""
    symbols = load_watchlist()
    symbol = symbol.upper()
    if symbol not in symbols:
        symbols.append(symbol)
        save_watchlist(symbols)
    return ", ".join(symbols)


@mcp.tool()
def remove_from_watchlist(symbol: str) -> str:
    """Remove a ticker from the watchlist."""
    symbols = [s for s in load_watchlist() if s != symbol.upper()]
    save_watchlist(symbols)
    return ", ".join(symbols)


@mcp.tool()
def is_market_open() -> str:
    """Check whether the US stock market is currently open.

    Accounts for weekends and market holidays via Alpaca's trading calendar.
    """
    clock = trading_client.get_clock()
    if clock.is_open:
        return f"Market is open. Closes at {clock.next_close}."
    return f"Market is closed. Opens at {clock.next_open}."


@mcp.tool()
def list_positions() -> str:
    """List all current open positions in the paper trading account."""
    positions = trading_client.get_all_positions()
    if not positions:
        return "No open positions."
    return "\n".join(
        f"{p.symbol}: qty={p.qty}, market_value=${p.market_value}, unrealized_pl=${p.unrealized_pl}"
        for p in positions
    )


@mcp.tool()
def place_order(symbol: str, qty: float, side: str) -> str:
    """Place a market order in the paper trading account.

    Args:
        symbol: Stock ticker, e.g. AAPL.
        qty: Number of shares to buy or sell.
        side: "buy" or "sell".
    """
    order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
    order = trading_client.submit_order(
        MarketOrderRequest(
            symbol=symbol.upper(),
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.DAY,
        )
    )
    return f"Order submitted: {order.side} {order.qty} {order.symbol}, status={order.status}"


@mcp.tool()
def list_orders() -> str:
    """List recent orders on the paper trading account."""
    orders = trading_client.get_orders()
    if not orders:
        return "No orders."
    return "\n".join(
        f"{o.id}: {o.symbol} {o.side} qty={o.qty}, status={o.status}, submitted_at={o.submitted_at}"
        for o in orders
    )


@mcp.tool()
def cancel_order(order_id: str) -> str:
    """Cancel a single open order by its ID.

    Args:
        order_id: The order ID, as shown by list_orders.
    """
    trading_client.cancel_order_by_id(order_id)
    return f"Order {order_id} canceled."


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
