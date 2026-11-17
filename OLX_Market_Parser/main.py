import re
import time
from datetime import datetime, timedelta
from urllib.parse import quote, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from cache import ListingCache, diff_listings
from report import write_report

BASE_URL = "https://www.olx.ua/uk/list/q-{query}/"
MAX_PAGES = 25
RESULTS_FILE = "results.xlsx"

KNOWN_CONDITIONS = ("Нове", "Вживане", "Відновлене", "Пошкоджене")
CONDITION_ORDER = {name: index for index, name in enumerate(KNOWN_CONDITIONS)}

MONTHS = {
    "січня": 1, "лютого": 2, "березня": 3, "квітня": 4, "травня": 5, "червня": 6,
    "липня": 7, "серпня": 8, "вересня": 9, "жовтня": 10, "листопада": 11, "грудня": 12,
}

CURRENCIES = (("грн", "UAH"), ("$", "USD"), ("€", "EUR"))


def build_url(search: str, page: int) -> str:
    url = BASE_URL.format(query=search)
    if page > 1:
        url += f"?page={page}"
    return url


def get_soup(url: str) -> tuple[BeautifulSoup, str]:
    response = requests.get(url, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    for style in soup.find_all("style"):
        style.decompose()
    return soup, response.url


def clean_link(href: str, page_url: str) -> str:
    parts = urlsplit(urljoin(page_url, href))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def parse_price(text: str) -> dict:
    lowered = text.lower()
    result = {"price": None, "currency": "", "price_type": "Не вказана"}
    if not text:
        return result
    if "безкоштовно" in lowered:
        result["price_type"] = "Безкоштовно"
        return result

    match = re.search(r"\d[\d\s]*(?:[.,]\d+)?", text)
    if match is None:
        result["price_type"] = text
        return result

    result["price"] = float(re.sub(r"\s", "", match.group()).replace(",", "."))
    result["currency"] = next((code for sign, code in CURRENCIES if sign in lowered), "")
    result["price_type"] = "Договірна" if "договірна" in lowered else "Фіксована"
    return result


def parse_posted(text: str, now: datetime) -> str | None:
    text = text.strip()
    match = re.match(r"(Сьогодні|Вчора) о (\d{1,2}):(\d{2})", text)
    if match:
        day = now if match.group(1) == "Сьогодні" else now - timedelta(days=1)
        posted = day.replace(hour=int(match.group(2)), minute=int(match.group(3)),
                             second=0, microsecond=0)
        return posted.isoformat()

    match = re.match(r"(\d{1,2}) (\w+) (\d{4})", text)
    if match and match.group(2) in MONTHS:
        try:
            return datetime(int(match.group(3)), MONTHS[match.group(2)], int(match.group(1))).isoformat()
        except ValueError:
            return None
    return None


def parse_location_date(card, now: datetime) -> dict:
    tag = card.select_one('[data-testid="location-date"]')
    text = tag.get_text(" ", strip=True) if tag else ""
    location, _, date_text = text.rpartition(" - ")
    if not location:
        location, date_text = text, ""
    city, _, district = location.partition(",")
    return {
        "city": city.strip(),
        "district": district.strip(),
        "posted": parse_posted(date_text, now),
    }


def parse_condition(card) -> str:
    for text in card.stripped_strings:
        if text in KNOWN_CONDITIONS:
            return text
    return ""


def parse_listings(soup: BeautifulSoup, page_url: str, seen_ids: set[str]) -> list[dict]:
    grid = soup.select_one('[data-testid="listing-grid"]')
    if grid is None:
        return []

    now = datetime.now()
    listings = []
    for card in grid.select('[data-cy="l-card"]'):
        link_tag = card.select_one('a[data-testid="card-title-link"]') or card.select_one("a[href]")
        if link_tag is None or not link_tag.get("href"):
            continue

        link = clean_link(link_tag["href"], page_url)
        ad_id = card.get("id") or link
        if ad_id in seen_ids:
            continue
        seen_ids.add(ad_id)

        price_tag = card.select_one('[data-testid="ad-price"]')
        price_text = price_tag.get_text(" ", strip=True) if price_tag else ""

        listings.append({
            "id": ad_id,
            "title": link_tag.get_text(" ", strip=True),
            "price_text": price_text,
            **parse_price(price_text),
            "condition": parse_condition(card),
            **parse_location_date(card, now),
            "promoted": "promoted" in link_tag["href"],
            "delivery": card.select_one('[data-testid="card-delivery-badge"]') is not None,
            "link": link,
        })
    return listings


def get_page_count(soup: BeautifulSoup) -> int:
    pagination = soup.select_one('[data-cy="pagination"]')
    if pagination is None:
        return 1
    numbers = [int(a.get_text(strip=True)) for a in pagination.find_all("a")
               if a.get_text(strip=True).isdigit()]
    return max(numbers, default=1)


def fetch_all(search: str) -> tuple[list[dict], bool]:
    seen_ids: set[str] = set()
    soup, page_url = get_soup(build_url(search, 1))
    total_pages = get_page_count(soup)
    pages = min(total_pages, MAX_PAGES)

    listings = []
    for page in range(1, pages + 1):
        if page > 1:
            soup, page_url = get_soup(build_url(search, page))
        found = parse_listings(soup, page_url, seen_ids)
        listings.extend(found)
        print(f"Сторінка {page}/{pages}: {len(found)} оголошень")

    capped = total_pages >= MAX_PAGES
    return listings, capped


def apply_stop_words(listings: list[dict], stop_words: list[str]) -> list[dict]:
    return [item for item in listings
            if not any(word in item["title"].lower() for word in stop_words)]


def sort_price(item: dict) -> float | None:
    if item["price_type"] == "Безкоштовно":
        return 0.0
    if item["currency"] == "UAH":
        return item["price"]
    return None


SORT_MODES = {
    "1": ("ціна, від дешевших",
          lambda items: sorted(items, key=lambda i: (sort_price(i) is None, sort_price(i) or 0))),
    "2": ("ціна, від дорожчих",
          lambda items: sorted(items, key=lambda i: (sort_price(i) is None, -(sort_price(i) or 0)))),
    "3": ("стан, потім ціна",
          lambda items: sorted(items, key=lambda i: (CONDITION_ORDER.get(i["condition"], len(CONDITION_ORDER)),
                                                     sort_price(i) is None, sort_price(i) or 0))),
    "4": ("дата, спершу новіші",
          lambda items: sorted(items, key=lambda i: i["posted"] or "", reverse=True)),
    "5": ("місто, потім ціна",
          lambda items: sorted(items, key=lambda i: (not i["city"], i["city"],
                                                     sort_price(i) is None, sort_price(i) or 0))),
}


def ask_sort_mode() -> str:
    options = ", ".join(f"{key} — {label}" for key, (label, _) in SORT_MODES.items())
    choice = input(f"Сортування ({options}) [1]: ").strip() or "1"
    if choice not in SORT_MODES:
        print("Невідомий варіант, сортую за ціною.")
        choice = "1"
    return choice


def format_age(seconds: float) -> str:
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes} хв тому"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} год тому"
    return f"{hours // 24} дн тому"


def print_diff(old_entry: dict, new_listings: list[dict], capped: bool):
    diff = diff_listings(old_entry["listings"], new_listings)
    print(f"Порівняно з кешем ({format_age(ListingCache.age(old_entry))}): "
          f"нових {diff['added']}, зникло {diff['removed']}, "
          f"змінилась ціна {diff['price_changed']}, змінилась назва {diff['title_changed']}")
    if capped or old_entry.get("capped"):
        print(f"Увага: OLX показує лише {MAX_PAGES} сторінок, тож частина «нових» і «зниклих» "
              f"могла просто зсунутися за межу видачі.")


def ask_yes(prompt: str) -> bool:
    return input(prompt).strip().lower() in ("y", "yes", "т", "так", "д", "да")


def get_listings(search: str, cache: ListingCache) -> tuple[list[dict] | None, float]:
    entry = cache.get(search)

    if entry is not None and cache.is_fresh(entry):
        print(f"Є кеш для цього запиту ({format_age(cache.age(entry))}, "
              f"{len(entry['listings'])} оголошень).")
        if not ask_yes("Оновити з OLX? [y/N]: "):
            return entry["listings"], entry["fetched_at"]

    try:
        listings, capped = fetch_all(search)
    except requests.RequestException as error:
        if entry is None:
            print(f"Не вдалося завантажити дані з OLX: {error}")
            return None, time.time()
        print(f"Не вдалося завантажити дані з OLX ({error}). "
              f"Використовую кеш ({format_age(cache.age(entry))}).")
        return entry["listings"], entry["fetched_at"]

    if not listings:
        return listings, time.time()

    if entry is not None:
        print_diff(entry, listings, capped)
    cache.put(search, listings, capped)
    return listings, cache.get(search)["fetched_at"]


def main():
    query = input("Введіть пошуковий запит: ").strip()
    search = quote("-".join(query.lower().split()), safe="-")
    if not search:
        print("Порожній запит.")
        return

    raw_stop = input("Слова для виключення через кому (Enter — без фільтра): ")
    stop_words = [w.strip().lower() for w in raw_stop.split(",") if w.strip()]
    sort_mode = ask_sort_mode()

    listings, fetched_at = get_listings(search, ListingCache())
    if listings is None:
        return

    filtered = apply_stop_words(listings, stop_words)
    if not filtered:
        print("Нічого не знайдено.")
        return

    label, sorter = SORT_MODES[sort_mode]
    try:
        write_report(RESULTS_FILE, sorter(filtered), query, datetime.fromtimestamp(fetched_at), label)
    except PermissionError:
        print(f"Не вдалося записати {RESULTS_FILE}: закрий файл в Excel і запусти ще раз.")
        return
    print(f"Excellent, I found {len(filtered)} products! Звіт збережено в {RESULTS_FILE}")


if __name__ == "__main__":
    main()
