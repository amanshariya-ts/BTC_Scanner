# state/state_store.py
import json
from pathlib import Path

STATE_FILE = Path(__file__).parent / "state.json"


class StateStore:
    """Remembers which signals have already been alerted, so each
    candle fires at most one alert per strategy."""

    def __init__(self):
        self._data = {}
        if STATE_FILE.exists():
            try:
                self._data = json.loads(STATE_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def already_alerted(self, key: str, timestamp) -> bool:
        # Accepts both list (new format) and string (old format) entries
        entry = self._data.get(key)
        if entry is None:
            return False
        if isinstance(entry, list):
            return str(timestamp) in entry
        return str(timestamp) == str(entry)

    def mark_alerted(self, key: str, timestamp) -> None:
        entry = self._data.get(key)
        if entry is None:
            entry = []
        elif isinstance(entry, str):
            entry = [entry]          # migrate old single-string format
        elif isinstance(entry, list):
            pass
        else:
            entry = []

        ts = str(timestamp)
        if ts not in entry:
            entry.append(ts)

        # Keep only the most recent 50 timestamps per key (prevents
        # the file growing forever)
        entry = sorted(entry)[-50:]
        self._data[key] = entry
        STATE_FILE.write_text(json.dumps(self._data, indent=2))
