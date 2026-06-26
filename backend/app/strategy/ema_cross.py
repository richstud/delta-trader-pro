"""EMA 6 / EMA 50 crossover signal."""
from __future__ import annotations

from collections import deque
from typing import Literal

Side = Literal["buy", "sell"]


def ema(values: list[float], period: int) -> float:
    if not values:
        return 0.0
    k = 2 / (period + 1)
    e = values[0]
    for v in values[1:]:
        e = v * k + e * (1 - k)
    return e


class EMACross:
    def __init__(self, fast: int = 6, slow: int = 50) -> None:
        self.fast = fast
        self.slow = slow
        self._closes: dict[str, deque[float]] = {}
        self._prev_diff: dict[str, float] = {}

    def feed(self, symbol: str, close: float) -> tuple[Side | None, float, float]:
        buf = self._closes.setdefault(symbol, deque(maxlen=self.slow * 5))
        buf.append(close)
        if len(buf) < self.slow:
            return None, 0.0, 0.0
        vals = list(buf)
        e_fast = ema(vals[-self.slow * 2:], self.fast)
        e_slow = ema(vals[-self.slow * 2:], self.slow)
        diff = e_fast - e_slow
        prev = self._prev_diff.get(symbol)
        self._prev_diff[symbol] = diff
        side: Side | None = None
        if prev is not None:
            if prev <= 0 and diff > 0:
                side = "buy"
            elif prev >= 0 and diff < 0:
                side = "sell"
        return side, e_fast, e_slow
