# alerts/aggregator.py
import logging
import threading
import queue
import time

log = logging.getLogger(__name__)

FLUSH_INTERVAL = 20      # seconds between flush checks
BATCH_WINDOW = 75        # alerts older than this get flushed


class SignalAggregator:
    """Collects signals from market threads and sends one grouped
    Telegram message per (side, symbol, timeframe) batch."""

    def __init__(self, telegram):
        self.q = queue.Queue()
        self.tg = telegram
        self._buffer = []          # list of signal dicts
        self._lock = threading.Lock()

    def submit(self, signal, exchange):
        self.q.put({"exchange": exchange, "signal": signal})

    def start(self):
        t = threading.Thread(target=self._run, daemon=True)
        t.start()
        log.info("Aggregator started")
        return t

    def _run(self):
        while True:
            time.sleep(FLUSH_INTERVAL)
            try:
                # drain queue into buffer
                while True:
                    self._buffer.append(self.q.get_nowait())
            except queue.Empty:
                pass

            if not self._buffer:
                continue

            with self._lock:
                batch = self._buffer
                self._buffer = []

            groups = {}
            for item in batch:
                s = item["signal"]
                key = (s.side.upper(), s.symbol, s.timeframe)
                groups.setdefault(key, []).append(item)

            for (side, symbol, timeframe), items in groups.items():
                venues = [it["exchange"] for it in items]
                prices = [it["signal"].price for it in items]
                arrow = "🟢 BUY" if side == "BUY" else "🔴 SELL"
                text = (f"{arrow} pinbar — {symbol} [{timeframe}]\n"
                        f"Confirmed by {len(items)} feed(s): "
                        f"{', '.join(sorted(venues))}\n"
                        f"Price range: {min(prices):.2f} – {max(prices):.2f}\n"
                        f"Strategy: liquidity_pinbars")
                log.info(f"ALERT(grouped): {side} {symbol} {timeframe} "
                         f"via {venues}")
                self.tg.send_text(text)
