# check_signals.py
"""
Single-shot checker for GitHub Actions:
- Fetches recent candles for every market (Binance futures via CCXT)
- Evaluates the last few closed candles with each strategy
- Sends Telegram alerts for NEW signals (dedup via state file)
- Exits. GitHub Actions re-runs this every 5 minutes.
"""
import logging

from config.config_loader import load_config
from data.fetcher import OHLCVFetcher
from strategies.liquidity_pinbars import LiquidityPinBars
from alerts.telegram import TelegramAlert
from state.state_store import StateStore

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("checker")

STRATEGY_REGISTRY = {
    LiquidityPinBars.name: LiquidityPinBars,
}

BARS_TO_CHECK = 3  # buffer in case GitHub's scheduler runs late


def main():
    cfg = load_config()
    fetcher = OHLCVFetcher(cfg["exchange"]["name"])
    tg = TelegramAlert(cfg["alerts"]["telegram"]["bot_token"],
                       cfg["alerts"]["telegram"]["chat_id"])
    state = StateStore()

    for market in cfg["markets"]:
        symbol = market["symbol"]
        timeframe = market["timeframe"]

        try:
            df = fetcher.fetch_ohlcv(symbol, timeframe,
                                     cfg["polling"]["lookback_bars"])
        except Exception as e:
            log.error(f"[{symbol} {timeframe}] fetch failed: {e}")
            continue

        closed = df.iloc[:-1]  # drop the still-open candle

        strategies = [STRATEGY_REGISTRY[s["name"]](symbol, timeframe, s.get("params", {}))
                      for s in cfg["strategies"]
                      if s.get("enabled", True) and s["name"] in STRATEGY_REGISTRY]

        for i in range(max(0, len(closed) - BARS_TO_CHECK), len(closed)):
            df_slice = closed.iloc[:i + 1]
            for strat in strategies:
                try:
                    signal = strat.evaluate(df_slice)
                except Exception as e:
                    log.error(f"[{symbol} {timeframe}] evaluate error: {e}")
                    continue
                if signal is None:
                    continue  # No-signal candle: silently ignored

                key = f"{signal.symbol}|{signal.timeframe}|{strat.name}"
                if state.already_alerted(key, signal.timestamp):
                    continue

                signal.strategy = strat.name
                log.info(f"SIGNAL: {signal.side} {signal.symbol} "
                         f"{signal.timeframe} @ {signal.price}")
                tg.send(signal)
                state.mark_alerted(key, signal.timestamp)

    log.info("Check complete.")


if __name__ == "__main__":
    main()
