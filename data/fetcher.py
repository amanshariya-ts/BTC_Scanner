import logging
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
        o = self._client.amount_to_precision(symbol, 0)  # touch markets to validate
        rows = self._client.fetch_ohlcv(symbol, timeframe, limit=limit)
        import pandas as pd
        df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        log.info(f"Fetched {len(df)} bars: {symbol} {timeframe} from {self.exchange_id}")
        return df
