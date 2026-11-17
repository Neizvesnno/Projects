import csv
import json
from pathlib import Path

CSV_FIELDS = [
    "id", "title", "price", "currency", "price_type", "condition", "business", "seller",
    "seller_since", "city", "district", "region", "posted", "created", "promoted",
    "delivery", "photo", "link", "price_text",
]


def csv_value(value):
    if isinstance(value, bool):
        return "так" if value else "ні"
    if value is None:
        return ""
    return value


def write_csv(path: Path, listings: list[dict]):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, delimiter=";", extrasaction="ignore")
        writer.writeheader()
        for item in listings:
            writer.writerow({key: csv_value(item.get(key)) for key in CSV_FIELDS})


def write_json(path: Path, listings: list[dict], meta: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "listings": listings}, f, ensure_ascii=False, indent=2)
