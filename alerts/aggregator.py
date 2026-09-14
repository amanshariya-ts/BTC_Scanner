# alerts/aggregator.py
import logging
import threading
import queue
import time

log = logging.getLogger(__name__)

FLUSH_INTERVAL = 20
BATCH_WINDOW = 75


class SignalAggregator:
    """Collects signals from market threads and sends one grouped
    Telegram message per (side, symbol, timeframe) batch."""

    def __init__(self, telegram):
        self.q = queue.Queue()
        self.tg = telegram
        self._buffer = []
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
            drained = []
            try:
                while True:
                    drained.append(self.q.get_nowait())
            except queue.Empty:
                pass

            if not drained:
                continue

            with self._lock:
                self._buffer.extend(drained)
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
                text = (arrow + " pinbar — " + symbol + " [" + timeframe + "]\n"
                        + "Confirmed by " + str(len(items)) + " feed(s): "
                        + ", ".join(sorted(venues)) + "\n"
                        + "Price range: " + f"{min(prices):.2f}" + " – " + f"{max(prices):.2f}"
                        + "\nStrategy: liquidity_pinbars")
                log.info("ALERT(grouped): %s %s %s via %s", side, symbol, timeframe, venues)
                self.tg.send_text(text)
