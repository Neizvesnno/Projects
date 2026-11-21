import shutil
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

TRACKER_FILE = Path(__file__).with_name("olx_tracker.db")
SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS ads (
    ad_id TEXT PRIMARY KEY,
    title TEXT,
    price REAL,
    currency TEXT,
    link TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ad_queries (
    query_key TEXT NOT NULL,
    ad_id TEXT NOT NULL,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    PRIMARY KEY (query_key, ad_id)
);
CREATE TABLE IF NOT EXISTS price_history (
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
CREATE INDEX IF NOT EXISTS idx_history ON price_history (ad_id);
"""

MIGRATE_V1 = """
ALTER TABLE ads RENAME TO ads_v1;
ALTER TABLE price_history RENAME TO price_history_v1;
DROP INDEX IF EXISTS idx_history;
""" + SCHEMA + """
INSERT OR IGNORE INTO ads (ad_id, title, price, currency, link, first_seen, last_seen)
    SELECT ad_id, title, price, currency, link,
           (SELECT MIN(first_seen) FROM ads_v1 AS o WHERE o.ad_id = a.ad_id), last_seen
    FROM ads_v1 AS a ORDER BY last_seen DESC;
INSERT INTO ad_queries (query_key, ad_id, first_seen, last_seen)
    SELECT query_key, ad_id, first_seen, last_seen FROM ads_v1;
INSERT INTO price_history (ad_id, price, currency, seen_at)
    SELECT ad_id, price, currency, seen_at FROM price_history_v1;
DROP TABLE ads_v1;
DROP TABLE price_history_v1;
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
    """Оголошення зберігаються один раз за ID, тож кілька запитів, що знаходять ті самі речі,
    не повідомляють про одне оголошення двічі."""

    def __init__(self, path: Path = TRACKER_FILE):
        self.path = Path(path)
        self.connection = sqlite3.connect(self.path, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self._migrate()

    def _migrate(self):
        db = self.connection
        version = db.execute("PRAGMA user_version").fetchone()[0]
        if version >= SCHEMA_VERSION:
            return
        columns = {row["name"] for row in db.execute("PRAGMA table_info(ads)")}
        if "query_key" in columns:
            shutil.copy2(self.path, self.path.with_name(self.path.name + ".bak-v1"))
            db.executescript(f"BEGIN;\n{MIGRATE_V1}\nPRAGMA user_version = {SCHEMA_VERSION};\nCOMMIT;")
        else:
            db.executescript(f"BEGIN;\n{SCHEMA}\nPRAGMA user_version = {SCHEMA_VERSION};\nCOMMIT;")

    def is_baseline(self, query_key: str) -> bool:
        return self.connection.execute(
            "SELECT 1 FROM runs WHERE query_key = ? LIMIT 1", (query_key,)).fetchone() is None

    def _begin(self):
        if not self.connection.in_transaction:
            self.connection.execute("BEGIN")

    @contextmanager
    def step(self):
        """Усе, що записано всередині, скасовується, якщо блок завершився помилкою.
        Зроблене раніше в тій самій транзакції лишається."""
        self._begin()
        self.connection.execute("SAVEPOINT step")
        try:
            yield
        except BaseException:
            self.connection.execute("ROLLBACK TO step")
            self.connection.execute("RELEASE step")
            raise
        self.connection.execute("RELEASE step")

    def track(self, query_key: str, listings: list[dict]) -> Changes:
        now = datetime.now().isoformat(timespec="seconds")
        db = self.connection
        self._begin()
        baseline = self.is_baseline(query_key)
        changes = Changes(baseline=baseline)

        for item in listings:
            db.execute(
                "INSERT INTO ad_queries (query_key, ad_id, first_seen, last_seen) VALUES (?, ?, ?, ?) "
                "ON CONFLICT (query_key, ad_id) DO UPDATE SET last_seen = excluded.last_seen",
                (query_key, item["id"], now, now),
            )
            row = db.execute("SELECT price, currency FROM ads WHERE ad_id = ?", (item["id"],)).fetchone()
            if row is None:
                db.execute(
                    "INSERT INTO ads (ad_id, title, price, currency, link, first_seen, last_seen) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (item["id"], item["title"], item["price"], item["currency"], item["link"], now, now),
                )
                self._history(item, now)
                if not baseline:
                    changes.new.append(item)
                continue

            old_price, old_currency = row["price"], row["currency"]
            if item["price"] != old_price or item["currency"] != old_currency:
                self._history(item, now)
                if (old_price is not None and item["price"] is not None
                        and item["currency"] == old_currency and item["price"] < old_price):
                    changes.cheaper.append((item, old_price))

            db.execute(
                "UPDATE ads SET title = ?, price = ?, currency = ?, link = ?, last_seen = ? WHERE ad_id = ?",
                (item["title"], item["price"], item["currency"], item["link"], now, item["id"]),
            )

        db.execute("INSERT INTO runs (query_key, run_at, found) VALUES (?, ?, ?)", (query_key, now, len(listings)))
        return changes

    def _history(self, item: dict, now: str):
        self.connection.execute(
            "INSERT INTO price_history (ad_id, price, currency, seen_at) VALUES (?, ?, ?, ?)",
            (item["id"], item["price"], item["currency"], now),
        )

    def commit(self):
        if self.connection.in_transaction:
            self.connection.execute("COMMIT")

    def rollback(self):
        if self.connection.in_transaction:
            self.connection.execute("ROLLBACK")

    def close(self):
        self.rollback()
        self.connection.close()
