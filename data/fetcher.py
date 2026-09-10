import logging
import pandas as pd
import ccxt

log = logging.getLogger(__name__)

ALLOWED_EXCHANGES = ["okx", "kucoin", "kucoinfutures", "gate", "bitget", "kraken"]

_clients: dict = {}


class OHLCVFetcher:
    def __init__(self, exchange_id: str):
        assert exchange_id in ALLOWED_EXCHANGES, f"exchange {exchange_id} not allowed"
        self.exchange_id = exchange_id
        self._client = self._get_client()

    def _get_client(self):
        if self.exchange_id not in _clients:
            cls = getattr(ccxt, self.exchange_id)
            client = cls({"enableRateLimit": True, "timeout": 15000})
            client.load_markets()
            _clients[self.exchange_id] = client
            log.info(f"Loaded markets from '{self.exchange_id}'")
        return _clients[self.exchange_id]

    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 200):
        if symbol not in self._client.markets:
            raise ValueError(f"unknown symbol {symbol} on {self.exchange_id}")
        rows = self._client.fetch_ohlcv(symbol, timeframe, limit=limit)
        df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        log.info(f"Fetched {len(df)} bars: {symbol} {timeframe} from {self.exchange_id}")
        return df
