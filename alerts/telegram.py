import logging
import requests

log = logging.getLogger(__name__)


class TelegramAlert:
    def __init__(self, bot_token: str = "", chat_id: str = ""):
        self.bot_token = bot_token or ""
        self.chat_id = chat_id or ""

    def send_text(self, text: str) -> bool:
        if not self.bot_token or not self.chat_id:
            log.warning("Telegram not configured — skipping send")
            return False
        try:
            resp = requests.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={"chat_id": self.chat_id, "text": text},
                timeout=10,
            )
            if resp.status_code == 200:
                return True
            log.warning(f"Telegram HTTP {resp.status_code}: {resp.text[:200]}")
            return False
        except Exception as e:
            log.warning(f"Telegram send failed: {e}")
            return False

    def send(self, signal) -> bool:
        arrow = "🟢 BUY" if signal.side == "buy" else "🔴 SELL"
        text = (f"{arrow} pinbar — {signal.symbol} [{signal.timeframe}]\n"
                f"Price: {signal.price:.2f}\n"
                f"Strategy: {signal.strategy}")
        return self.send_text(text)
