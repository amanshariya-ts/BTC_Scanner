import time
import logging

log = logging.getLogger(__name__)


class CandlePoller:
    """Yields every time a new candle closes for the given symbol/timeframe."""

    def __init__(self, fetcher, symbol: str, timeframe: str,
                 interval: int = 60, lookback: int = 200):
        self.fetcher = fetcher
        self.symbol = symbol
        self.timeframe = timeframe
        self.interval = interval
        self.lookback = lookback
        self._last_seen = None

    def poll_forever(self):
        while True:
            try:
                df = self.fetcher.fetch_ohlcv(self.symbol, self.timeframe,
                                              limit=self.lookback)
                if len(df):
                    latest = df.iloc[-1]["timestamp"]
                    if self._last_seen is None:
                        self._last_seen = latest
                    elif latest > self._last_seen:
                        self._last_seen = latest
                        yield latest
            except Exception as e:
                log.warning(f"[{self.symbol} {self.timeframe}] poll error: {e}")
            time.sleep(self.interval)
