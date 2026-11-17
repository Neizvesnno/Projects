import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

KNOWN_CONDITIONS = ("Нове", "Вживане", "Відновлене", "Пошкоджене")
MONTHS = {
    "січня": 1, "лютого": 2, "березня": 3, "квітня": 4, "травня": 5, "червня": 6,
    "липня": 7, "серпня": 8, "вересня": 9, "жовтня": 10, "листопада": 11, "грудня": 12,
}
CURRENCIES = (("грн", "UAH"), ("$", "USD"), ("€", "EUR"))
STATE_PATTERN = re.compile(r'window\.__PRERENDERED_STATE__\s*=\s*("(?:[^"\\]|\\.)*")')


@dataclass
class PageResult:
    listings: list[dict]
    total_pages: int
    total_found: int | None
    source: str


def clean_link(href: str, page_url: str) -> str:
    parts = urlsplit(urljoin(page_url, href))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def to_local_iso(value: str | None) -> str | None:
    if not value:
        return None
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return None
    if moment.tzinfo is not None:
        moment = moment.astimezone().replace(tzinfo=None)
    return moment.isoformat(timespec="minutes")


def empty_listing() -> dict:
    return {
        "id": "", "title": "", "price_text": "", "price": None, "currency": "",
        "price_type": "Не вказана", "condition": "", "business": None, "seller": "",
        "seller_since": None, "city": "", "district": "", "region": "",
        "posted": None, "created": None, "promoted": False, "delivery": False,
        "photo": "", "link": "",
    }


def parse_price_text(text: str) -> dict:
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


def parse_json_price(price: dict | None) -> dict:
    price = price or {}
    regular = price.get("regularPrice") or {}
    display = price.get("displayValue") or ""
    if price.get("free"):
        return {"price": None, "currency": "", "price_type": "Безкоштовно"}
    if price.get("exchange"):
        return {"price": None, "currency": "", "price_type": "Обмін"}
    if regular.get("value") is not None:
        return {
            "price": float(regular["value"]),
            "currency": regular.get("currencyCode") or "",
            "price_type": "Договірна" if regular.get("negotiable") else "Фіксована",
        }
    return parse_price_text(display)


def extract_state(html: str) -> dict | None:
    match = STATE_PATTERN.search(html)
    if match is None:
        return None
    try:
        state = json.loads(json.loads(match.group(1)))
        listing = state["listing"]["listing"]
    except (ValueError, KeyError, TypeError):
        return None
    if not isinstance(listing, dict) or not isinstance(listing.get("ads"), list):
        return None
    return listing


def delivery_badges(soup: BeautifulSoup) -> dict[str, bool]:
    grid = soup.select_one('[data-testid="listing-grid"]')
    if grid is None:
        return {}
    return {
        card.get("id"): card.select_one('[data-testid="card-delivery-badge"]') is not None
        for card in grid.select('[data-cy="l-card"]') if card.get("id")
    }


def listing_from_json(ad: dict, page_url: str, badges: dict[str, bool]) -> dict | None:
    if ad.get("id") is None or not ad.get("url"):
        return None
    ad_id = str(ad["id"])
    location = ad.get("location") or {}
    user = ad.get("user") or {}
    contact = ad.get("contact") or {}
    promotion = ad.get("promotion") or {}
    photos = ad.get("photos") or []

    item = empty_listing()
    item.update(parse_json_price(ad.get("price")))
    item.update({
        "id": ad_id,
        "title": (ad.get("title") or "").strip(),
        "price_text": (ad.get("price") or {}).get("displayValue") or "",
        "condition": ad.get("itemCondition") or "",
        "business": ad.get("isBusiness"),
        "seller": user.get("company_name") or user.get("name") or contact.get("name") or "",
        "seller_since": to_local_iso(user.get("memberSince") or user.get("created")),
        "city": location.get("cityName") or "",
        "district": location.get("districtName") or "",
        "region": location.get("regionName") or "",
        "posted": to_local_iso(ad.get("lastRefreshTime") or ad.get("createdTime")),
        "created": to_local_iso(ad.get("createdTime")),
        "promoted": bool(ad.get("isPromoted") or promotion.get("top_ad")),
        "delivery": badges.get(ad_id, bool(contact.get("courier"))),
        "photo": photos[0] if photos else "",
        "link": clean_link(ad["url"], page_url),
    })
    return item


def parse_posted_text(text: str, now: datetime) -> str | None:
    text = text.strip()
    match = re.match(r"(Сьогодні|Вчора) о (\d{1,2}):(\d{2})", text)
    if match:
        day = now if match.group(1) == "Сьогодні" else now - timedelta(days=1)
        posted = day.replace(hour=int(match.group(2)), minute=int(match.group(3)), second=0, microsecond=0)
        return posted.isoformat(timespec="minutes")

    match = re.match(r"(\d{1,2}) (\w+) (\d{4})", text)
    if match and match.group(2) in MONTHS:
        try:
            return datetime(int(match.group(3)), MONTHS[match.group(2)],
                            int(match.group(1))).isoformat(timespec="minutes")
        except ValueError:
            return None
    return None


def listing_from_card(card, page_url: str, now: datetime) -> dict | None:
    link_tag = card.select_one('a[data-testid="card-title-link"]') or card.select_one("a[href]")
    if link_tag is None or not link_tag.get("href"):
        return None

    link = clean_link(link_tag["href"], page_url)
    price_tag = card.select_one('[data-testid="ad-price"]')
    price_text = price_tag.get_text(" ", strip=True) if price_tag else ""

    location_tag = card.select_one('[data-testid="location-date"]')
    location_text = location_tag.get_text(" ", strip=True) if location_tag else ""
    location, _, date_text = location_text.rpartition(" - ")
    if not location:
        location, date_text = location_text, ""
    city, _, district = location.partition(",")

    image = card.find("img")
    photo = image.get("src", "") if image else ""

    item = empty_listing()
    item.update(parse_price_text(price_text))
    item.update({
        "id": card.get("id") or link,
        "title": link_tag.get_text(" ", strip=True),
        "price_text": price_text,
        "condition": next((text for text in card.stripped_strings if text in KNOWN_CONDITIONS), ""),
        "city": city.strip(),
        "district": district.strip(),
        "posted": parse_posted_text(date_text, now),
        "promoted": "promoted" in link_tag["href"],
        "delivery": card.select_one('[data-testid="card-delivery-badge"]') is not None,
        "photo": photo if photo.startswith("http") else "",
        "link": link,
    })
    return item


def html_page_count(soup: BeautifulSoup) -> int:
    pagination = soup.select_one('[data-cy="pagination"]')
    if pagination is None:
        return 1
    numbers = [int(a.get_text(strip=True)) for a in pagination.find_all("a")
               if a.get_text(strip=True).isdigit()]
    return max(numbers, default=1)


def parse_page(content: bytes | str, page_url: str) -> PageResult:
    html = content.decode("utf-8", errors="replace") if isinstance(content, bytes) else content
    soup = BeautifulSoup(html, "html.parser")
    for style in soup.find_all("style"):
        style.decompose()

    state = extract_state(html)
    if state is not None:
        badges = delivery_badges(soup)
        listings = [item for ad in state["ads"]
                    if isinstance(ad, dict) and (item := listing_from_json(ad, page_url, badges))]
        total_pages = state.get("totalPages")
        return PageResult(
            listings=listings,
            total_pages=total_pages if isinstance(total_pages, int) else html_page_count(soup),
            total_found=state.get("visibleElements") if isinstance(state.get("visibleElements"), int) else None,
            source="json",
        )

    grid = soup.select_one('[data-testid="listing-grid"]')
    now = datetime.now()
    cards = grid.select('[data-cy="l-card"]') if grid else []
    listings = [item for card in cards if (item := listing_from_card(card, page_url, now))]
    return PageResult(listings=listings, total_pages=html_page_count(soup), total_found=None, source="html")
