import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

TRACKER_FILE = Path(__file__).with_name("olx_tracker.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS ads (
    query_key TEXT NOT NULL,
    ad_id TEXT NOT NULL,
    title TEXT,
    price REAL,
    currency TEXT,
    link TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    PRIMARY KEY (query_key, ad_id)
);
CREATE TABLE IF NOT EXISTS price_history (
    query_key TEXT NOT NULL,
    ad_id TEXT NOT NULL,
    price REAL,
    currency TEXT,
    seen_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    query_key TEXT NOT NULL,
    run_at TEXT NOT NULL,
    found INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history ON price_history (query_key, ad_id);
"""


@dataclass
class Changes:
    baseline: bool
    new: list[dict] = field(default_factory=list)
    cheaper: list[tuple[dict, float]] = field(default_factory=list)

    @property
    def empty(self) -> bool:
        return not self.new and not self.cheaper


class Tracker:
    def __init__(self, path: Path = TRACKER_FILE):
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.executescript(SCHEMA)
        self.connection.commit()

    def track(self, query_key: str, listings: list[dict]) -> Changes:
        now = datetime.now().isoformat(timespec="seconds")
        db = self.connection
        baseline = db.execute("SELECT 1 FROM runs WHERE query_key = ? LIMIT 1", (query_key,)).fetchone() is None
        changes = Changes(baseline=baseline)

        for item in listings:
            row = db.execute("SELECT price, currency FROM ads WHERE query_key = ? AND ad_id = ?",
                             (query_key, item["id"])).fetchone()
            if row is None:
                db.execute(
                    "INSERT INTO ads (query_key, ad_id, title, price, currency, link, first_seen, last_seen) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (query_key, item["id"], item["title"], item["price"], item["currency"], item["link"], now, now),
                )
                self._history(query_key, item, now)
                if not baseline:
                    changes.new.append(item)
                continue

            old_price, old_currency = row["price"], row["currency"]
            if item["price"] != old_price or item["currency"] != old_currency:
                self._history(query_key, item, now)
                if (old_price is not None and item["price"] is not None
                        and item["currency"] == old_currency and item["price"] < old_price):
                    changes.cheaper.append((item, old_price))

            db.execute(
                "UPDATE ads SET title = ?, price = ?, currency = ?, link = ?, last_seen = ? "
                "WHERE query_key = ? AND ad_id = ?",
                (item["title"], item["price"], item["currency"], item["link"], now, query_key, item["id"]),
            )

        db.execute("INSERT INTO runs (query_key, run_at, found) VALUES (?, ?, ?)", (query_key, now, len(listings)))
        return changes

    def _history(self, query_key: str, item: dict, now: str):
        self.connection.execute(
            "INSERT INTO price_history (query_key, ad_id, price, currency, seen_at) VALUES (?, ?, ?, ?, ?)",
            (query_key, item["id"], item["price"], item["currency"], now),
        )

    def commit(self):
        self.connection.commit()

    def rollback(self):
        self.connection.rollback()

    def close(self):
        self.connection.close()
