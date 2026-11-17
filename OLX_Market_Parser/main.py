import requests
from bs4 import BeautifulSoup
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl import Workbook
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
import random
import os

from cache import ListingCache, diff_listings

BASE_URL = "https://www.olx.ua/uk/list/q-{query}/"
MAX_PAGES = 25


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


def parse_listings(soup: BeautifulSoup, page_url: str, seen_ids: set[str]) -> list[dict]:
    grid = soup.select_one('[data-testid="listing-grid"]')
    if grid is None:
        return []

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
        listings.append({
            "id": ad_id,
            "title": link_tag.get_text(" ", strip=True),
            "price": price_tag.get_text(" ", strip=True) if price_tag else "",
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


def save_to_excel(data: list[list[str]]):
    header = ["Назва", "Ціна", "Посилання"]
    links = ["This is HyperLink", "Touch me", "Click here", "Hello, I'm Link!"]

    try:
        workbook = load_workbook('results.xlsx')
    except FileNotFoundError:
        workbook = Workbook()

    worksheet = workbook.active

    worksheet.column_dimensions['A'].width = 50
    worksheet.column_dimensions['B'].width = 15
    worksheet.column_dimensions['C'].width = 20

    if worksheet['A1'].value != header[0] or worksheet['B1'].value != header[1] or worksheet['C1'].value != header[2]:
        for col_num, value in enumerate(header, start=1):
            col_letter = get_column_letter(col_num)
            worksheet[f'{col_letter}1'] = value

    last_row = worksheet.max_row

    for row_num, info in enumerate(data, start=1):
        for col_num, value in enumerate(info, start=1):
            col_letter = get_column_letter(col_num)
            colip = f'{col_letter}{last_row + row_num}'
            if col_letter == "C":
                worksheet[colip].hyperlink = value
                worksheet[colip].value = random.choice(links)
                worksheet[colip].style = "Hyperlink"
            else:
                worksheet[colip] = value

    workbook.save('results.xlsx')


def get_listings(search: str, cache: ListingCache) -> list[dict] | None:
    entry = cache.get(search)

    if entry is not None and cache.is_fresh(entry):
        print(f"Є кеш для цього запиту ({format_age(cache.age(entry))}, "
              f"{len(entry['listings'])} оголошень).")
        if not ask_yes("Оновити з OLX? [y/N]: "):
            return entry["listings"]

    try:
        listings, capped = fetch_all(search)
    except requests.RequestException as error:
        if entry is None:
            print(f"Не вдалося завантажити дані з OLX: {error}")
            return None
        print(f"Не вдалося завантажити дані з OLX ({error}). "
              f"Використовую кеш ({format_age(cache.age(entry))}).")
        return entry["listings"]

    if not listings:
        return listings

    if entry is not None:
        print_diff(entry, listings, capped)
    cache.put(search, listings, capped)
    return listings


def main():
    try:
        os.remove("results.xlsx")
    except FileNotFoundError:
        pass

    query = input("Введіть пошуковий запит: ").strip()
    search = quote("-".join(query.lower().split()), safe="-")
    if not search:
        print("Порожній запит.")
        return

    raw_stop = input("Слова для виключення через кому (Enter — без фільтра): ")
    stop_words = [w.strip().lower() for w in raw_stop.split(",") if w.strip()]

    listings = get_listings(search, ListingCache())
    if listings is None:
        return

    filtered = apply_stop_words(listings, stop_words)
    if not filtered:
        print("Нічого не знайдено.")
        return

    save_to_excel([[item["title"], item["price"], item["link"]] for item in filtered])
    print(f"Excellent, I found {len(filtered)} products!")


if __name__ == "__main__":
    main()
