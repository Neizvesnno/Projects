import json
import os
import tempfile
import time
from pathlib import Path

CACHE_FILE = Path(__file__).with_name("cache.json")
CACHE_VERSION = 1
CACHE_TTL = 30 * 60
CACHE_MAX_AGE = 7 * 24 * 60 * 60


class ListingCache:
    def __init__(self, path: Path = CACHE_FILE):
        self.path = path
        self.entries: dict[str, dict] = self._load()

    def _load(self) -> dict[str, dict]:
        try:
            with open(self.path, encoding="utf-8") as f:
                raw = json.load(f)
        except FileNotFoundError:
            return {}
        except (OSError, ValueError):
            print("Кеш пошкоджено, його буде створено заново.")
            return {}

        if not isinstance(raw, dict) or raw.get("version") != CACHE_VERSION:
            return {}
        entries = raw.get("entries")
        if not isinstance(entries, dict):
            return {}
        return {key: entry for key, entry in entries.items() if self._is_valid(entry)}

    @staticmethod
    def _is_valid(entry) -> bool:
        return (
            isinstance(entry, dict)
            and isinstance(entry.get("fetched_at"), (int, float))
            and isinstance(entry.get("listings"), list)
        )

    @staticmethod
    def age(entry: dict) -> float:
        return time.time() - entry["fetched_at"]

    def is_fresh(self, entry: dict) -> bool:
        return 0 <= self.age(entry) < CACHE_TTL

    def get(self, key: str) -> dict | None:
        return self.entries.get(key)

    def put(self, key: str, listings: list[dict], capped: bool):
        self.entries[key] = {
            "fetched_at": time.time(),
            "capped": capped,
            "listings": listings,
        }
        self._prune()
        self._save()

    def _prune(self):
        now = time.time()
        self.entries = {
            key: entry for key, entry in self.entries.items()
            if 0 <= now - entry["fetched_at"] < CACHE_MAX_AGE
        }

    def _save(self):
        payload = {"version": CACHE_VERSION, "entries": self.entries}
        fd, tmp_path = tempfile.mkstemp(dir=self.path.parent, prefix=".cache-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
            os.replace(tmp_path, self.path)
        except BaseException:
            try:
                os.remove(tmp_path)
            except FileNotFoundError:
                pass
            raise


def diff_listings(old: list[dict], new: list[dict]) -> dict[str, int]:
    old_by_id = {item["id"]: item for item in old}
    new_by_id = {item["id"]: item for item in new}
    return {
        "added": sum(1 for ad_id in new_by_id if ad_id not in old_by_id),
        "removed": sum(1 for ad_id in old_by_id if ad_id not in new_by_id),
        "price_changed": sum(
            1 for ad_id, item in new_by_id.items()
            if ad_id in old_by_id and old_by_id[ad_id]["price"] != item["price"]
        ),
        "title_changed": sum(
            1 for ad_id, item in new_by_id.items()
            if ad_id in old_by_id and old_by_id[ad_id]["title"] != item["title"]
        ),
    }
