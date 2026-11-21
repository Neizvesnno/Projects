import argparse
import html
import sys
import time
from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import requests

from cache import ListingCache, diff_listings
from export import write_csv, write_json
from notify import NotifyError, format_changes, format_combined, send_telegram, telegram_credentials
from olx_client import MAX_PAGES, ORDERS, SELLERS, OlxClient, PathNotFound, SearchParams
from olx_parser import KNOWN_CONDITIONS
from report import ReportMeta, write_report
from tracker import Changes, Tracker

CONDITION_ORDER = {name: index for index, name in enumerate(KNOWN_CONDITIONS)}
FORMATS = ("xlsx", "csv", "json")


def sort_price(item: dict) -> float | None:
    if item["price_type"] == "Безкоштовно":
        return 0.0
    if item["currency"] == "UAH":
        return item["price"]
    return None


def by_price(item: dict, sign: int = 1) -> tuple:
    price = sort_price(item)
    return price is None, sign * (price or 0)


SORT_MODES = {
    "price": ("ціна, від дешевших", lambda items: sorted(items, key=by_price)),
    "price-desc": ("ціна, від дорожчих", lambda items: sorted(items, key=lambda i: by_price(i, -1))),
    "condition": ("стан, потім ціна",
                  lambda items: sorted(items, key=lambda i: (CONDITION_ORDER.get(i["condition"], len(CONDITION_ORDER)),
                                                             *by_price(i)))),
    "date": ("дата, спершу новіші", lambda items: sorted(items, key=lambda i: i["posted"] or "", reverse=True)),
    "city": ("місто, потім ціна", lambda items: sorted(items, key=lambda i: (not i["city"], i["city"], *by_price(i)))),
    "seller": ("продавець, потім ціна",
               lambda items: sorted(items, key=lambda i: (i["business"] is None, bool(i["business"]), *by_price(i)))),
}


@dataclass
class Options:
    search: SearchParams
    stop_words: list[str] = field(default_factory=list)
    sort: str = "price"
    formats: tuple[str, ...] = ("xlsx",)
    output: Path = Path("results.xlsx")
    refresh: bool = False
    track: bool = False
    notify: bool = False
    every: float | None = None
    delay: float = 1.0
    workers: int = 3
    interactive: bool = False


def parse_stop_words(raw: str) -> list[str]:
    return [word.strip().lower() for word in raw.split(",") if word.strip()]


def positive_float(value: str) -> float:
    number = float(value)
    if number < 0:
        raise argparse.ArgumentTypeError("значення не може бути від'ємним")
    return number


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Парсер оголошень OLX.ua з аналізом цін, кешем і відстеженням змін.",
        epilog="Без аргументів запускається в інтерактивному режимі з питаннями.",
    )
    parser.add_argument("query", nargs="*", help="пошуковий запит, напр. iphone 13")
    parser.add_argument("-x", "--exclude", default="", help="стоп-слова через кому, напр. \"чохол,скло\"")
    parser.add_argument("--city", help="місто в адресі OLX латиницею: kiev, lvov, kharkov, odessa, dnepr…")
    parser.add_argument("--category", help="шлях категорії з адреси OLX, напр. moda-i-stil/aksessuary/sumki")
    parser.add_argument("--min-price", type=positive_float, help="мінімальна ціна, грн")
    parser.add_argument("--max-price", type=positive_float, help="максимальна ціна, грн")
    parser.add_argument("--seller", choices=SELLERS, help="тільки приватні особи або бізнес")
    parser.add_argument("--order", choices=list(ORDERS), default="relevance",
                        help="порядок видачі на OLX (важливо, коли оголошень більше 1000)")
    parser.add_argument("--pages", type=int, default=MAX_PAGES, help=f"скільки сторінок завантажити (1–{MAX_PAGES})")
    parser.add_argument("-s", "--sort", choices=list(SORT_MODES), default="price", help="сортування у звіті")
    parser.add_argument("-f", "--format", nargs="+", choices=FORMATS, default=["xlsx"], dest="formats",
                        help="формати звіту, можна кілька: xlsx csv json")
    parser.add_argument("-o", "--output", type=Path, default=Path("results.xlsx"),
                        help="файл звіту; csv/json отримають ту саму назву з іншим розширенням")
    parser.add_argument("--refresh", action="store_true", help="не брати дані з кешу, завантажити заново")
    parser.add_argument("--track", action="store_true",
                        help="відстежувати нові оголошення й зниження цін між запусками (SQLite)")
    parser.add_argument("--notify", action="store_true",
                        help="надсилати зміни в Telegram (потрібні TELEGRAM_BOT_TOKEN і TELEGRAM_CHAT_ID)")
    parser.add_argument("--every", type=positive_float, metavar="ХВИЛИН",
                        help="повторювати перевірку кожні N хвилин (вмикає --track)")
    parser.add_argument("--delay", type=positive_float, default=1.0,
                        help="мінімальна пауза між запитами до OLX, с (за замовчуванням 1)")
    parser.add_argument("--workers", type=int, default=3, help="скільки сторінок качати паралельно (1–5)")
    return parser


def options_from_args(argv: list[str]) -> Options:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    query = " ".join(args.query).strip()
    if not query:
        parser.error("вкажи пошуковий запит")
    if not 1 <= args.pages <= MAX_PAGES:
        parser.error(f"--pages має бути від 1 до {MAX_PAGES}")
    if not 1 <= args.workers <= 5:
        parser.error("--workers має бути від 1 до 5")
    if args.min_price is not None and args.max_price is not None and args.min_price > args.max_price:
        parser.error("--min-price більша за --max-price")
    if args.notify and telegram_credentials() is None:
        parser.error("для --notify задай змінні середовища TELEGRAM_BOT_TOKEN і TELEGRAM_CHAT_ID")
    if args.every is not None and args.every < 1:
        parser.error("--every має бути щонайменше 1 хвилина")

    return Options(
        search=SearchParams(
            query=query,
            city=args.city.strip().lower() if args.city else None,
            category=args.category.strip().strip("/").lower() or None if args.category else None,
            min_price=args.min_price,
            max_price=args.max_price,
            seller=args.seller,
            order=args.order,
            max_pages=args.pages,
        ),
        stop_words=parse_stop_words(args.exclude),
        sort=args.sort,
        formats=tuple(dict.fromkeys(args.formats)),
        output=args.output,
        refresh=args.refresh,
        track=args.track or args.notify or args.every is not None,
        notify=args.notify,
        every=args.every,
        delay=args.delay,
        workers=args.workers,
    )


def options_interactive() -> Options | None:
    query = input("Введіть пошуковий запит: ").strip()
    if not query:
        print("Порожній запит.")
        return None
    stop_words = parse_stop_words(input("Слова для виключення через кому (Enter — без фільтра): "))

    modes = list(SORT_MODES)
    menu = ", ".join(f"{number} — {SORT_MODES[mode][0]}" for number, mode in enumerate(modes, start=1))
    choice = input(f"Сортування ({menu}) [1]: ").strip() or "1"
    if not choice.isdigit() or not 1 <= int(choice) <= len(modes):
        print("Невідомий варіант, сортую за ціною.")
        choice = "1"
    return Options(search=SearchParams(query=query), stop_words=stop_words,
                   sort=modes[int(choice) - 1], interactive=True)


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
        print("Увага: OLX віддає не всю видачу, тож частина «нових» і «зниклих» "
              "могла просто зсунутися за межу завантажених сторінок.")


def ask_yes(prompt: str) -> bool:
    return input(prompt).strip().lower() in ("y", "yes", "т", "так", "д", "да")


@dataclass
class Snapshot:
    listings: list[dict]
    fetched_at: float
    total_found: int | None
    fresh: bool


def get_listings(opts: Options, client: OlxClient, cache: ListingCache) -> Snapshot | None:
    key = opts.search.cache_key()
    entry = cache.get(key)

    if entry is not None and cache.is_fresh(entry) and not opts.refresh and not opts.track:
        print(f"Є кеш для цього запиту ({format_age(cache.age(entry))}, {len(entry['listings'])} оголошень).")
        if not opts.interactive or not ask_yes("Оновити з OLX? [y/N]: "):
            return Snapshot(entry["listings"], entry["fetched_at"], entry.get("total_found"), fresh=False)

    try:
        result = client.fetch_all(opts.search)
    except PathNotFound as error:
        print(f"OLX не знайшов сторінку {error}. Перевір --city і --category: їх треба брати з адреси сайту, "
              f"напр. kiev або moda-i-stil/aksessuary/sumki.")
        return None
    except requests.RequestException as error:
        reason = error.__class__.__name__
        if entry is None:
            print(f"Не вдалося завантажити дані з OLX ({reason}).")
            return None
        if opts.track:
            print(f"Не вдалося завантажити дані з OLX ({reason}). Відстеження пропущено, "
                  f"бо старий кеш не покаже нових змін.")
            return None
        print(f"Не вдалося завантажити дані з OLX ({reason}). Використовую кеш ({format_age(cache.age(entry))}).")
        return Snapshot(entry["listings"], entry["fetched_at"], entry.get("total_found"), fresh=False)

    if result["source"] == "html":
        print("Увага: OLX не віддав JSON зі сторінки, дані розібрано з HTML, частина полів може бути порожня.")

    listings = result["listings"]
    if listings:
        if entry is not None and not opts.track:
            print_diff(entry, listings, result["capped"])
        cache.put(key, listings, result["capped"], result["total_found"])
        return Snapshot(listings, cache.get(key)["fetched_at"], result["total_found"], fresh=True)
    return Snapshot(listings, time.time(), result["total_found"], fresh=True)


def apply_stop_words(listings: list[dict], stop_words: list[str]) -> list[dict]:
    return [item for item in listings if not any(word in item["title"].lower() for word in stop_words)]


def write_outputs(opts: Options, listings: list[dict], meta: ReportMeta) -> list[Path]:
    written = []
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    for fmt in opts.formats:
        path = opts.output.with_suffix(f".{fmt}")
        if fmt == "xlsx":
            write_report(path, listings, meta)
        elif fmt == "csv":
            write_csv(path, listings)
        elif fmt == "json":
            write_json(path, listings, {
                "query": meta.query,
                "filters": meta.filters,
                "fetched_at": meta.fetched_at.isoformat(timespec="seconds"),
                "total_found": meta.total_found,
                "sort": opts.sort,
                "excluded_words": opts.stop_words,
            })
        written.append(path)
    return written


@dataclass
class SearchResult:
    opts: Options
    changes: Changes | None


def collect(opts: Options, client: OlxClient, cache: ListingCache, tracker: Tracker | None) -> SearchResult | None:
    """Завантажує видачу, записує зміни в базу (без commit) і зберігає звіт."""
    snapshot = get_listings(opts, client, cache)
    if snapshot is None:
        return None

    listings = apply_stop_words(snapshot.listings, opts.stop_words)
    if not listings:
        print("Нічого не знайдено.")
        return SearchResult(opts, None)

    label, sorter = SORT_MODES[opts.sort]
    try:
        with tracker.step() if tracker is not None else nullcontext():
            changes = None
            if tracker is not None:
                changes = tracker.track(opts.search.cache_key(), listings)
            meta = ReportMeta(
                query=opts.search.query,
                filters=opts.search.describe(),
                fetched_at=datetime.fromtimestamp(snapshot.fetched_at),
                sort_label=label,
                total_found=snapshot.total_found,
                changes=changes,
            )
            written = write_outputs(opts, sorter(listings), meta)
    except PermissionError as error:
        print(f"Не вдалося записати {error.filename}: закрий файл в Excel і запусти ще раз.")
        return None

    if changes is not None:
        if changes.baseline:
            print(f"Відстеження почато: {len(listings)} оголошень збережено як базу. "
                  f"Зміни буде видно з наступного запуску.")
        else:
            print(f"Нових оголошень: {len(changes.new)}, подешевшали: {len(changes.cheaper)}.")
    total = f" з {snapshot.total_found:,} на OLX".replace(",", " ") if snapshot.total_found else ""
    print(f"Знайдено {len(listings)} оголошень{total}. Збережено: {', '.join(str(p) for p in written)}")
    return SearchResult(opts, changes)


def deliver(tracker: Tracker, messages: list[str]) -> bool:
    """Надсилає повідомлення і лише тоді фіксує зміни в базі. Інакше відкочує все,
    щоб ці самі зміни прийшли наступного разу."""
    if messages:
        token, chat_id = telegram_credentials()
        try:
            send_telegram(token, chat_id, messages)
            print("Зміни надіслано в Telegram.")
        except NotifyError as error:
            tracker.rollback()
            print(f"Не вдалося надіслати в Telegram ({error}). Зміни не позначено як переглянуті, "
                  f"їх буде надіслано наступного разу.")
            return False
    tracker.commit()
    return True


def run_once(opts: Options, client: OlxClient, cache: ListingCache, tracker: Tracker | None) -> bool:
    result = collect(opts, client, cache, tracker)
    if tracker is None:
        return result is not None
    if result is None:
        tracker.rollback()
        return False
    changes = result.changes
    messages = []
    if opts.notify and changes is not None and not changes.baseline:
        messages = format_changes(opts.search.query, opts.search.describe(), changes)
    return deliver(tracker, messages)


def run_batch(argv_list: list[list[str]], log=print) -> int:
    """Проганяє кілька запитів зі спільною базою і надсилає одне повідомлення без дублів.
    Повертає кількість запитів, що завершилися помилкою."""
    searches = []
    for argv in argv_list:
        try:
            opts = options_from_args(argv)
        except SystemExit:
            log(f"Пропускаю запит з неправильними параметрами: {' '.join(argv)}")
            continue
        opts.track = True
        searches.append(opts)
    failed = len(argv_list) - len(searches)
    if not searches:
        return failed

    client = OlxClient(delay=min(o.delay for o in searches), workers=max(o.workers for o in searches))
    cache = ListingCache()
    tracker = Tracker()
    try:
        # Запити, що запускаються вперше, ідуть останніми: запис їхньої бази
        # не повинен сховати справжні новинки від інших запитів.
        searches.sort(key=lambda o: tracker.is_baseline(o.search.cache_key()))
        sections = []
        for opts in searches:
            log(f"Запит: {opts.search.query} ({opts.search.describe()})")
            try:
                result = collect(opts, client, cache, tracker)
            except Exception as error:
                log(f"Помилка: {error.__class__.__name__}: {error}")
                result = None
            if result is None:
                failed += 1
            elif result.changes is not None and not result.changes.baseline:
                sections.append((opts.search.query, result.changes))

        notify = any(o.notify for o in searches)
        queries = ", ".join(f"«{html.escape(o.search.query)}»" for o in searches)
        messages = format_combined(f"<b>OLX: {queries}</b>", sections) if notify else []
        if not deliver(tracker, messages):
            failed = len(argv_list)
    finally:
        tracker.close()
    return failed


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        opts = options_from_args(argv) if argv else options_interactive()
    except (EOFError, KeyboardInterrupt):
        print("\nСкасовано.")
        return 1
    if opts is None:
        return 1

    client = OlxClient(delay=opts.delay, workers=opts.workers)
    cache = ListingCache()
    tracker = Tracker() if opts.track else None

    try:
        if opts.every is None:
            return 0 if run_once(opts, client, cache, tracker) else 1

        print(f"Перевірка кожні {opts.every:g} хв. Зупинити: Ctrl+C.")
        while True:
            print(f"\n[{datetime.now():%d.%m %H:%M}] Перевіряю OLX…")
            try:
                run_once(opts, client, cache, tracker)
            except Exception as error:
                if tracker is not None:
                    tracker.rollback()
                print(f"Помилка під час перевірки: {error.__class__.__name__}: {error}")
            time.sleep(opts.every * 60)
    except KeyboardInterrupt:
        print("\nЗупинено.")
        return 0
    finally:
        if tracker is not None:
            tracker.close()


if __name__ == "__main__":
    sys.exit(main())
