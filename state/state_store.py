import json
import os
from datetime import datetime, timezone

STATE_FILE = "state/state.json"


class StateStore:
    def __init__(self, path: str = STATE_FILE):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self._data = {}
        if os.path.exists(path):
            try:
                with open(path) as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}

    def already_alerted(self, key: str, ts) -> bool:
        entry = self._data.get(key)
        if not entry:
            return False
        return str(ts) <= entry.get("last_ts", "")

    def mark_alerted(self, key: str, ts):
        self._data[key] = {"last_ts": str(ts),
                           "updated": datetime.now(timezone.utc).isoformat()}
        self._save()

    def _save(self):
        try:
            with open(self.path, "w") as f:
                json.dump(self._data, f, indent=2)
        except Exception as e:
            log.warning(f"state save failed: {e}")
