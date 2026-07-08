from dataclasses import dataclass


@dataclass
class Signal:
    source: str
    signal: str  # "bullish", "bearish", or "neutral"
    confidence: float  # 0.0-1.0
    details: dict
    rationale: str


@dataclass
class SymbolSignals:
    symbol: str
    signals: list[Signal]
