from datetime import datetime, timedelta, timezone

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator

from signals.base import Signal


def get_technicals_signal(
    data_client: StockHistoricalDataClient,
    symbol: str,
    timeframe: TimeFrame = TimeFrame.Hour,
    lookback_days: int = 30,
) -> Signal:
    bars = _fetch_bars(data_client, symbol, timeframe, lookback_days)
    if len(bars) < 30:
        return Signal(
            source="technicals",
            signal="neutral",
            confidence=0.0,
            details={},
            rationale=f"insufficient bar history ({len(bars)} bars)",
        )

    close = bars["close"]
    volume = bars["volume"]

    sma_short = SMAIndicator(close, window=10).sma_indicator().iloc[-1]
    sma_long = SMAIndicator(close, window=30).sma_indicator().iloc[-1]
    rsi = RSIIndicator(close, window=14).rsi().iloc[-1]
    macd_ind = MACD(close)
    macd_line = macd_ind.macd().iloc[-1]
    macd_signal_line = macd_ind.macd_signal().iloc[-1]
    avg_volume = volume.rolling(20).mean().iloc[-1]
    last_price = close.iloc[-1]
    last_volume = volume.iloc[-1]

    details = {
        "price": round(last_price, 2),
        "sma_short": round(sma_short, 2),
        "sma_long": round(sma_long, 2),
        "rsi_14": round(rsi, 1),
        "macd": round(macd_line, 3),
        "macd_signal": round(macd_signal_line, 3),
        "volume": int(last_volume),
        "avg_volume_20": int(avg_volume),
    }

    bull_points = 0
    bear_points = 0
    reasons = []

    if sma_short > sma_long:
        bull_points += 1
        reasons.append(f"short SMA above long SMA ({sma_short:.2f} > {sma_long:.2f})")
    elif sma_short < sma_long:
        bear_points += 1
        reasons.append(f"short SMA below long SMA ({sma_short:.2f} < {sma_long:.2f})")

    if rsi < 30:
        bull_points += 1
        reasons.append(f"RSI oversold ({rsi:.1f})")
    elif rsi > 70:
        bear_points += 1
        reasons.append(f"RSI overbought ({rsi:.1f})")

    if macd_line > macd_signal_line:
        bull_points += 1
        reasons.append("MACD above signal line")
    elif macd_line < macd_signal_line:
        bear_points += 1
        reasons.append("MACD below signal line")

    if last_volume > 1.5 * avg_volume:
        reasons.append(f"volume {last_volume / avg_volume:.1f}x the 20-period average")

    if bull_points > bear_points:
        signal = "bullish"
        confidence = bull_points / 3
    elif bear_points > bull_points:
        signal = "bearish"
        confidence = bear_points / 3
    else:
        signal = "neutral"
        confidence = 0.0

    return Signal(
        source="technicals",
        signal=signal,
        confidence=round(confidence, 2),
        details=details,
        rationale="; ".join(reasons) if reasons else "no clear signal",
    )


def _fetch_bars(
    data_client: StockHistoricalDataClient,
    symbol: str,
    timeframe: TimeFrame,
    lookback_days: int,
) -> pd.DataFrame:
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=timeframe,
        start=datetime.now(timezone.utc) - timedelta(days=lookback_days),
    )
    bar_set = data_client.get_stock_bars(request)
    return bar_set.df.loc[symbol]
