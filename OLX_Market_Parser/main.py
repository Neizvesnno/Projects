import requests
from bs4 import BeautifulSoup
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl import Workbook
from urllib.parse import quote, urljoin, urlsplit, urlunsplit
import random
import os

BASE_URL = "https://www.olx.ua/uk/list/q-{query}/"
MAX_PAGES = 25

data_len: int = 0
row_numo: int = 0
search: str
stop_words: list[str] = []
seen_ids: set[str] = set()


def build_url(page: int) -> str:
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


def parse_listings(soup: BeautifulSoup, page_url: str) -> list[list[str]]:
    grid = soup.select_one('[data-testid="listing-grid"]')
    if grid is None:
        return []

    listings = []
    for card in grid.select('[data-cy="l-card"]'):
        link_tag = card.select_one('a[data-testid="card-title-link"]') or card.select_one("a[href]")
        if link_tag is None or not link_tag.get("href"):
            continue

        ad_id = card.get("id") or link_tag["href"]
        if ad_id in seen_ids:
            continue
        seen_ids.add(ad_id)

        title = link_tag.get_text(" ", strip=True)
        price_tag = card.select_one('[data-testid="ad-price"]')
        price = price_tag.get_text(" ", strip=True) if price_tag else ""

        lowered = title.lower()
        if any(word in lowered for word in stop_words):
            continue

        listings.append([title, price, clean_link(link_tag["href"], page_url)])
    return listings


def get_page_count(soup: BeautifulSoup) -> int:
    pagination = soup.select_one('[data-cy="pagination"]')
    if pagination is None:
        return 1
    numbers = [int(a.get_text(strip=True)) for a in pagination.find_all("a")
               if a.get_text(strip=True).isdigit()]
    return min(max(numbers, default=1), MAX_PAGES)


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


def every_main(kols, soup=None, page_url=None):
    if soup is None:
        soup, page_url = get_soup(build_url(kols))
    data = parse_listings(soup, page_url)
    if data:
        save_to_excel(data)
    return len(data)


def main():
    global row_numo, search, data_len, stop_words

    try:
        os.remove("results.xlsx")
    except FileNotFoundError:
        pass

    query = input("Введіть пошуковий запит: ").strip()
    search = quote("-".join(query.split()), safe="-")

    raw_stop = input("Слова для виключення через кому (Enter — без фільтра): ")
    stop_words = [w.strip().lower() for w in raw_stop.split(",") if w.strip()]

    soup_first, url_first = get_soup(build_url(1))
    pages = get_page_count(soup_first)

    for ssp in range(1, pages + 1):
        if ssp == 1:
            data_len = every_main(ssp, soup_first, url_first)
        else:
            data_len = every_main(ssp)
        row_numo += data_len
        print(f"Сторінка {ssp}/{pages}: {data_len} оголошень")

    if row_numo == 0:
        print("Нічого не знайдено.")
    else:
        print(f"Excellent, I found {row_numo} products!")


if __name__ == "__main__":
    main()
