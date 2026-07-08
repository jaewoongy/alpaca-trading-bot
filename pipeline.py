from alpaca.data.historical import StockHistoricalDataClient

from signals.base import SymbolSignals
from signals.technicals import get_technicals_signal


def screen_watchlist(
    data_client: StockHistoricalDataClient, symbols: list[str]
) -> list[SymbolSignals]:
    """Run the technicals provider across the full watchlist and keep only
    symbols with a non-neutral signal.

    This is the cheap filter stage: pure computation, no LLM call, no
    external rate-limited APIs, so it's fine to run against every symbol
    every cycle. Everything it shortlists is bundled into a SymbolSignals
    so slower/pricier providers (news, etc.) can append their own Signal
    to the same symbol before it reaches the synthesis agent.
    """
    shortlist = []
    for symbol in symbols:
        technicals = get_technicals_signal(data_client, symbol)
        if technicals.signal != "neutral":
            shortlist.append(SymbolSignals(symbol=symbol, signals=[technicals]))
    return shortlist
