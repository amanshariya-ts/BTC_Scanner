# config/config_loader.py
import os
import yaml
from pathlib import Path

def load_config(path: str = "config/config.yaml") -> dict:
    with open(Path(path), "r") as f:
        cfg = yaml.safe_load(f)

    # Environment variables override placeholders (used on GitHub Actions)
    tg = cfg.get("alerts", {}).get("telegram", {})
    if tg.get("bot_token") in (None, "", "PLACEHOLDER_TOKEN"):
        tg["bot_token"] = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if tg.get("chat_id") in (None, "", "PLACEHOLDER_CHAT_ID"):
        tg["chat_id"] = os.environ.get("TELEGRAM_CHAT_ID", "")
    cfg["alerts"]["telegram"] = tg

    return cfg
