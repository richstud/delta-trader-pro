"""Redis key namespace conventions: everything is `delta:*`."""

def price_key(symbol: str) -> str: return f"delta:price:{symbol}"
def candles_key(symbol: str) -> str: return f"delta:candles:1m:{symbol}"   # list of JSON candles
def last_signal_key(symbol: str) -> str: return f"delta:lastsignal:{symbol}"
def status_key(name: str) -> str: return f"delta:status:{name}"             # ws, algo
TICKS_CHANNEL = "delta:ticks"
SIGNALS_CHANNEL = "delta:signals"
def user_fills_channel(user_id: str) -> str: return f"delta:fills:{user_id}"
