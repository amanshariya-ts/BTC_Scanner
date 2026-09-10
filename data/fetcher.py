# data/fetcher.py
import logging

import ccxt
import pandas as pd

log = logging.getLogger(__name__)

# Binance geo-blocks some cloud IPs (GitHub Actions -> HTTP 451).
# We try exchanges in order; the first one that answers wins.
EXCHANGE_FALLBACKS = [
    "binanceusdm",    # Binance USDT-M futures (primary; works from home IPs)
    "kucoinfutures",  # KuCoin futures (accessible from most cloud IPs)
    "okx",            # OKX swap (another fallback)
    "kraken",         # Kraken spot (US-based, never geo-blocked)
]

TIMEFRAME_MS = {
    "1m": 60_000, "3m": 180_000, "5m": 300_000, "15m": 900_000,
    "30m": 1_800_000, "1h": 3_600_000, "2h": 7_200_000,
    "4h": 14_400_000, "1d": 86_400_000,
}


class OHLCVFetcher:
    """Fetches OHLCV candles, trying several exchanges until one works."""

    def __init__(self, exchange_name: str = "binanceusdm"):
        self.exchange_ids = [exchange_name] + [
            e for e in EXCHANGE_FALLBACKS if e != exchange_name
        ]
        self._clients = {}
        self._preferred = None  # first exchange that answered successfully

    def _client(self, exchange_id):
        if exchange_id not in self._clients:
            cls = getattr(ccxt, exchange_id)
            self._clients[exchange_id] = cls({"enableRateLimit": True})
        return self._clients[exchange_id]

    @staticmethod
    def _resolve_symbol(client, symbol):
        """Use the perp symbol if listed, otherwise the spot equivalent."""
        if symbol in client.markets:
            return symbol
        spot = symbol.split(":")[0]  # "BTC/USDT:USDT" -> "BTC/USDT"
        if spot in client.markets:
            return spot
        return None

    def _try(self, exchange_id, symbol, timeframe, limit):
        try:
            client = self._client(exchange_id)
            if not client.markets:
                client.load_markets()
            real_symbol = self._resolve_symbol(client, symbol)
            if real_symbol is None:
                return None
            rows = client.fetch_ohlcv(real_symbol, timeframe=timeframe, limit=limit)
            df = pd.DataFrame(rows, columns=["timestamp", "open", "high",
                                             "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            return df
        except Exception as e:
            log.warning(f"{exchange_id} failed for {symbol} {timeframe}: "
                        f"{type(e).__name__}: {e}")
            return None

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 200) -> pd.DataFrame:
        # Reuse the exchange that worked last time
        if self._preferred:
            df = self._try(self._preferred, symbol, timeframe, limit)
            if df is not None:
                return df
            self._preferred = None

        for exchange_id in self.exchange_ids:
            df = self._try(exchange_id, symbol, timeframe, limit)
            if df is not None:
                self._preferred = exchange_id
                log.info(f"Using exchange '{exchange_id}' for {symbol}")
                return df

        raise RuntimeError(f"All exchanges failed for {symbol} {timeframe}")

    @staticmethod
    def timeframe_to_seconds(tf: str) -> int:
        return TIMEFRAME_MS[tf] // 1000
