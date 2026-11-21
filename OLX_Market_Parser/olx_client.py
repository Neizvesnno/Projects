import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from olx_parser import parse_page

BASE_URL = "https://www.olx.ua/uk/{path}/q-{query}/"
MAX_PAGES = 25
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
ORDERS = {
    "relevance": None,
    "cheap": "filter_float_price:asc",
    "expensive": "filter_float_price:desc",
    "new": "created_at:desc",
}
SELLERS = ("private", "business")


class PathNotFound(Exception):
    pass


@dataclass(frozen=True)
class SearchParams:
    query: str
    city: str | None = None
    category: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    seller: str | None = None
    order: str = "relevance"
    max_pages: int = MAX_PAGES

    @property
    def slug(self) -> str:
        return quote("-".join(self.query.lower().split()), safe="-")

    def url(self) -> str:
        path = "/".join(part for part in (self.category, self.city) if part) or "list"
        return BASE_URL.format(path=path, query=self.slug)

    def request_params(self, page: int) -> dict:
        params = {}
        if page > 1:
            params["page"] = page
        if self.min_price is not None:
            params["search[filter_float_price:from]"] = f"{self.min_price:g}"
        if self.max_price is not None:
            params["search[filter_float_price:to]"] = f"{self.max_price:g}"
        if self.seller:
            params["search[private_business]"] = self.seller
        if ORDERS.get(self.order):
            params["search[order]"] = ORDERS[self.order]
        return params

    def cache_key(self) -> str:
        data = asdict(self)
        data["query"] = self.slug
        return "|".join(f"{key}={value}" for key, value in data.items() if value not in (None, ""))

    def describe(self) -> str:
        parts = []
        if self.category:
            parts.append(f"категорія: {self.category}")
        if self.city:
            parts.append(f"місто: {self.city}")
        if self.min_price is not None or self.max_price is not None:
            low = f"{self.min_price:g}" if self.min_price is not None else "0"
            high = f"{self.max_price:g}" if self.max_price is not None else "∞"
            parts.append(f"ціна: {low}–{high} грн")
        if self.seller:
            parts.append("продавець: " + ("приватна особа" if self.seller == "private" else "бізнес"))
        if self.order != "relevance":
            parts.append(f"порядок OLX: {self.order}")
        if self.max_pages < MAX_PAGES:
            parts.append(f"сторінок: до {self.max_pages}")
        return ", ".join(parts) or "без фільтрів"


class RateLimiter:
    def __init__(self, interval: float):
        self.interval = max(interval, 0.0)
        self._lock = threading.Lock()
        self._next_slot = 0.0

    def wait(self):
        with self._lock:
            now = time.monotonic()
            slot = max(now, self._next_slot)
            self._next_slot = slot + self.interval * random.uniform(0.8, 1.2)
        if slot > now:
            time.sleep(slot - now)


class OlxClient:
    def __init__(self, delay: float = 1.0, workers: int = 3, retries: int = 3,
                 timeout: tuple[float, float] = (10, 30)):
        self.workers = max(1, workers)
        self.retries = retries
        self.timeout = timeout
        self.limiter = RateLimiter(delay)
        self._local = threading.local()

    def _session(self) -> requests.Session:
        session = getattr(self._local, "session", None)
        if session is None:
            retry = Retry(
                total=self.retries,
                backoff_factor=1.5,
                status_forcelist=(429, 500, 502, 503, 504),
                allowed_methods=frozenset({"GET"}),
                respect_retry_after_header=True,
            )
            session = requests.Session()
            session.mount("https://", HTTPAdapter(max_retries=retry))
            session.mount("http://", HTTPAdapter(max_retries=retry))
            session.headers.update({
                "User-Agent": USER_AGENT,
                "Accept-Language": "uk-UA,uk;q=0.9",
            })
            self._local.session = session
        return session

    def get(self, url: str, params: dict | None = None) -> requests.Response:
        self.limiter.wait()
        response = self._session().get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response

    def fetch_page(self, search: SearchParams, page: int):
        try:
            response = self.get(search.url(), search.request_params(page))
        except requests.HTTPError as error:
            if error.response is not None and error.response.status_code == 404 and (search.city or search.category):
                raise PathNotFound(search.url()) from error
            raise
        return parse_page(response.content, response.url)

    def fetch_all(self, search: SearchParams, progress=print) -> dict:
        first = self.fetch_page(search, 1)
        pages = max(1, min(first.total_pages, search.max_pages, MAX_PAGES))
        progress(f"Сторінка 1/{pages}: {len(first.listings)} оголошень")

        results = {1: first}
        if pages > 1:
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                futures = {pool.submit(self.fetch_page, search, page): page for page in range(2, pages + 1)}
                for done, future in enumerate(as_completed(futures), start=2):
                    page = futures[future]
                    results[page] = future.result()
                    progress(f"Сторінка {page}/{pages}: {len(results[page].listings)} оголошень "
                             f"({done}/{pages})")

        seen_ids = set()
        listings = []
        for page in range(1, pages + 1):
            for item in results[page].listings:
                if item["id"] not in seen_ids:
                    seen_ids.add(item["id"])
                    listings.append(item)

        return {
            "listings": listings,
            "capped": first.total_pages > pages or first.total_pages >= MAX_PAGES,
            "total_found": first.total_found,
            "source": first.source,
        }
