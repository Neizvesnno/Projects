import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from tracker import Changes

PRICE_FORMAT = '#,##0 "грн"'
PERCENT_FORMAT = '+0%;-0%;0%'
SHARE_FORMAT = '0%'
DATE_FORMAT = 'DD.MM.YYYY HH:MM'
DAY_FORMAT = 'DD.MM.YYYY'

ACCENT = "23A094"
HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor=ACCENT)
TITLE_FONT = Font(bold=True, size=14)
SECTION_FONT = Font(bold=True, size=12, color=ACCENT)
NOTE_FONT = Font(italic=True, color="666666")
NOT_SET = "Не вказано"


Bounds = tuple[float, float] | None


@dataclass


class ReportMeta:
    query: str
    filters: str
    fetched_at: datetime
    sort_label: str
    total_found: int | None = None
    changes: Changes | None = None


def uah_price(item: dict) -> float | None:
    return item["price"] if item["currency"] == "UAH" else None


def table_price(item: dict) -> float | None:
    return 0 if item["price_type"] == "Безкоштовно" else uah_price(item)


def uah_prices(listings: list[dict]) -> list[float]:
    return [price for price in map(uah_price, listings) if price is not None]


def seller_label(item: dict) -> str:
    if item.get("business") is None:
        return NOT_SET
    return "Бізнес" if item["business"] else "Приватна особа"


def parse_date(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def price_stats(prices: list[float]) -> dict | None:
    if not prices:
        return None
    quartiles = statistics.quantiles(prices, n=4) if len(prices) > 1 else [prices[0]] * 3
    return {
        "count": len(prices),
        "mean": statistics.fmean(prices),
        "median": statistics.median(prices),
        "min": min(prices),
        "max": max(prices),
        "q1": quartiles[0],
        "q3": quartiles[2],
        "stdev": statistics.stdev(prices) if len(prices) > 1 else 0.0,
    }


def iqr_bounds(prices: list[float]) -> Bounds:
    """Межі звичайної ціни за правилом Тьюкі: [Q1 − 1,5·IQR; Q3 + 1,5·IQR]."""
    if len(prices) < 4:
        return None
    q1, _, q3 = statistics.quantiles(prices, n=4)
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def is_outlier(price: float | None, bounds: Bounds) -> bool:
    if bounds is None or price is None:
        return False
    low, high = bounds
    return price < low or price > high


def without_outliers(prices: list[float], bounds: Bounds) -> list[float]:
    return [price for price in prices if not is_outlier(price, bounds)]


def format_money(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")


def nice_step(raw: float) -> float:
    magnitude = 10 ** math.floor(math.log10(raw))
    for factor in (1, 2, 2.5, 5, 10):
        if factor * magnitude >= raw:
            return factor * magnitude
    return 10 * magnitude


def price_histogram(prices: list[float], target_bins: int = 8) -> list[tuple[str, int]]:
    if len(prices) < 2:
        return [(format_money(p), 1) for p in prices]

    cuts = statistics.quantiles(prices, n=20)
    low, high = cuts[0], cuts[-1]
    if high <= low:
        return [(f"{format_money(min(prices))}–{format_money(max(prices))}", len(prices))]

    step = nice_step((high - low) / target_bins)
    start = math.floor(low / step) * step
    edges = [start]
    while edges[-1] < high:
        edges.append(edges[-1] + step)

    buckets = []
    below = sum(1 for p in prices if p < start)
    if below:
        buckets.append((f"< {format_money(start)}", below))
    for left, right in zip(edges, edges[1:]):
        count = sum(1 for p in prices if left <= p < right)
        buckets.append((f"{format_money(left)}–{format_money(right)}", count))
    above = sum(1 for p in prices if p >= edges[-1])
    if above:
        buckets.append((f"≥ {format_money(edges[-1])}", above))
    return buckets


def style_header(cells):
    for cell in cells:
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def set_link(cell, url: str, text: str = "Відкрити"):
    if not url:
        return
    cell.value = text
    cell.hyperlink = url
    cell.style = "Hyperlink"


def listing_columns(median: float | None, bounds: Bounds) -> list[tuple]:
    def deviation(item):
        price = uah_price(item)
        return price / median - 1 if price and median else None

    return [
        ("Назва", 55, lambda i: i["title"], None),
        ("Ціна, грн", 14, table_price, PRICE_FORMAT),
        ("Тип ціни", 13, lambda i: i["price_type"], None),
        ("Стан", 11, lambda i: i["condition"] or NOT_SET, None),
        ("Продавець", 15, seller_label, None),
        ("Місто", 18, lambda i: i["city"], None),
        ("Район", 18, lambda i: i["district"], None),
        ("Область", 22, lambda i: i["region"], None),
        ("Опубліковано/піднято", 17, lambda i: parse_date(i["posted"]), DATE_FORMAT),
        ("Створено", 17, lambda i: parse_date(i["created"]), DATE_FORMAT),
        ("Від медіани", 12, deviation, PERCENT_FORMAT),
        ("Викид", 8, lambda i: "так" if is_outlier(uah_price(i), bounds) else "", None),
        ("ТОП", 6, lambda i: "так" if i["promoted"] else "", None),
        ("Доставка", 10, lambda i: "так" if i["delivery"] else "", None),
        ("Посилання", 11, "link", None),
        ("Фото", 8, "photo", None),
        ("Ім'я продавця", 20, lambda i: i["seller"], None),
        ("Ціна на сайті", 22, lambda i: i["price_text"], None),
        ("ID", 12, lambda i: i["id"], None),
    ]


def column_index(columns: list[tuple], header: str) -> int:
    return next(index for index, column in enumerate(columns, start=1) if column[0] == header)


def write_listings_sheet(ws, listings: list[dict], median: float | None, bounds: Bounds, sort_label: str):
    ws.title = "Оголошення"
    columns = listing_columns(median, bounds)
    for col, (header, width, _, _) in enumerate(columns, start=1):
        ws.cell(row=1, column=col, value=header)
        ws.column_dimensions[get_column_letter(col)].width = width
    style_header(ws[1])

    for row, item in enumerate(listings, start=2):
        for col, (header, _, getter, fmt) in enumerate(columns, start=1):
            cell = ws.cell(row=row, column=col)
            if getter == "link":
                set_link(cell, item["link"])
            elif getter == "photo":
                set_link(cell, item["photo"], "Фото")
            else:
                cell.value = getter(item)
                if fmt:
                    cell.number_format = fmt

    last_row = len(listings) + 1
    last_col = get_column_letter(len(columns))
    table = Table(displayName="Listings", ref=f"A1:{last_col}{last_row}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
    ws.add_table(table)
    ws.freeze_panes = "B2"

    price_col = get_column_letter(column_index(columns, "Ціна, грн"))
    deviation_col = get_column_letter(column_index(columns, "Від медіани"))
    ws.conditional_formatting.add(
        f"{price_col}2:{price_col}{last_row}",
        ColorScaleRule(start_type="percentile", start_value=5, start_color="63BE7B",
                       mid_type="percentile", mid_value=50, mid_color="FFEB84",
                       end_type="percentile", end_value=95, end_color="F8696B"),
    )
    ws.conditional_formatting.add(
        f"{deviation_col}2:{deviation_col}{last_row}",
        ColorScaleRule(start_type="num", start_value=-0.5, start_color="63BE7B",
                       mid_type="num", mid_value=0, mid_color="FFFFFF",
                       end_type="num", end_value=0.5, end_color="F8696B"),
    )

    price_range = f"{price_col}2:{price_col}{last_row}"
    summary = [
        ("Середня ціна", f"=SUBTOTAL(101,{price_range})", PRICE_FORMAT),
        ("Мінімальна ціна", f"=SUBTOTAL(105,{price_range})", PRICE_FORMAT),
        ("Максимальна ціна", f"=SUBTOTAL(104,{price_range})", PRICE_FORMAT),
        ("Оголошень з ціною", f"=SUBTOTAL(102,{price_range})", "0"),
    ]
    price_index = column_index(columns, "Ціна, грн")
    row = last_row + 2
    ws.cell(row=row, column=1, value="Підсумок (з урахуванням фільтрів таблиці)").font = SECTION_FONT
    for label, formula, fmt in summary:
        row += 1
        ws.cell(row=row, column=1, value=label).font = Font(bold=True)
        cell = ws.cell(row=row, column=price_index, value=formula)
        cell.number_format = fmt
        cell.font = Font(bold=True)
    ws.cell(row=row + 2, column=1,
            value=f"Початкове сортування: {sort_label}. Кнопки в заголовку таблиці дозволяють "
                  f"пересортувати й відфільтрувати за будь-яким стовпцем. Щоб прибрати викиди "
                  f"з підсумку, відфільтруй стовпець «Викид».").font = NOTE_FONT


class SheetWriter:
    def __init__(self, ws):
        self.ws = ws
        self.row = 1

    def title(self, text: str):
        self.ws.cell(row=self.row, column=1, value=text).font = TITLE_FONT
        self.row += 1

    def line(self, text: str):
        self.ws.cell(row=self.row, column=1, value=text).font = NOTE_FONT
        self.row += 1

    def section(self, text: str):
        self.row += 1
        self.ws.cell(row=self.row, column=1, value=text).font = SECTION_FONT
        self.row += 1

    def pairs(self, rows: list[tuple[str, object, str | None]]):
        for label, value, fmt in rows:
            self.ws.cell(row=self.row, column=1, value=label)
            cell = self.ws.cell(row=self.row, column=2, value=value)
            if fmt:
                cell.number_format = fmt
            self.row += 1

    def table(self, headers: list[str], rows: list[list], formats: list[str | None]) -> tuple[int, int]:
        header_row = self.row
        for col, header in enumerate(headers, start=1):
            self.ws.cell(row=self.row, column=col, value=header)
        style_header(self.ws[self.row][:len(headers)])
        self.row += 1
        for values in rows:
            for col, (value, fmt) in enumerate(zip(values, formats), start=1):
                cell = self.ws.cell(row=self.row, column=col, value=value)
                if fmt:
                    cell.number_format = fmt
            self.row += 1
        return header_row, self.row - 1

    def ad_table(self, headers: list[str], items: list[dict], values, formats: list[str | None], link_col: int):
        header_row, _ = self.table(headers, [values(item) for item in items], formats)
        for offset, item in enumerate(items, start=1):
            set_link(self.ws.cell(row=header_row + offset, column=link_col), item["link"])


STAT_HEADERS = ["Кількість", "Частка", "Середня", "Медіана", "Мін", "Макс"]
STAT_FORMATS = [None, "0", SHARE_FORMAT, PRICE_FORMAT, PRICE_FORMAT, PRICE_FORMAT, PRICE_FORMAT]


def group_stats_rows(groups: dict[str, list[dict]], total: int, order: list[str], bounds: Bounds) -> list[list]:
    rows = []
    for name in order:
        items = groups[name]
        stats = price_stats(without_outliers(uah_prices(items), bounds))
        rows.append([
            name, len(items), len(items) / total,
            stats["mean"] if stats else None, stats["median"] if stats else None,
            stats["min"] if stats else None, stats["max"] if stats else None,
        ])
    return rows


def group_by(listings: list[dict], key) -> dict[str, list[dict]]:
    groups = defaultdict(list)
    for item in listings:
        groups[key(item) or NOT_SET].append(item)
    return groups


def by_size(groups: dict[str, list[dict]]) -> list[str]:
    return sorted(groups, key=lambda name: (name == NOT_SET, -len(groups[name])))


def add_price_chart(ws, first: int, last: int):
    chart = BarChart()
    chart.title = "Кількість оголошень за ціною"
    chart.x_axis.title = "Ціна, грн"
    chart.y_axis.title = "Оголошень"
    chart.legend = None
    chart.varyColors = False
    chart.gapWidth = 40
    # openpyxl 3.1+ ховає осі за замовчуванням: без цього не видно ні діапазонів, ні чисел
    chart.x_axis.delete = False
    chart.y_axis.delete = False
    chart.x_axis.tickLblPos = "low"
    chart.add_data(Reference(ws, min_col=2, min_row=first, max_row=last), titles_from_data=True)
    chart.set_categories(Reference(ws, min_col=1, min_row=first + 1, max_row=last))
    series = chart.series[0]
    series.graphicalProperties.solidFill = ACCENT
    series.graphicalProperties.line.solidFill = ACCENT
    chart.width, chart.height = 20, 9
    ws.add_chart(chart, f"I{first}")


def write_analysis_sheet(ws, listings: list[dict], meta: ReportMeta):
    ws.title = "Аналіз"
    for col, width in enumerate((34, 14, 10, 14, 14, 14, 14), start=1):
        ws.column_dimensions[get_column_letter(col)].width = width

    total = len(listings)
    prices = uah_prices(listings)
    stats = price_stats(prices)
    bounds = iqr_bounds(prices)
    clean_prices = without_outliers(prices, bounds)
    clean_stats = price_stats(clean_prices)
    outliers = len(prices) - len(clean_prices)
    types = Counter(item["price_type"] for item in listings)

    out = SheetWriter(ws)
    out.title(f"Аналіз ринку OLX: «{meta.query}»")
    out.line(f"Дані станом на {meta.fetched_at:%d.%m.%Y %H:%M}; фільтри: {meta.filters}")

    out.section("Загальне")
    rows = []
    if meta.total_found is not None:
        rows.append(("Усього на OLX за запитом", meta.total_found, "#,##0"))
    rows += [
        ("Оголошень у звіті", total, "#,##0"),
        ("З ціною в гривнях", len(prices), "0"),
        ("Ціна договірна", types.get("Договірна", 0), "0"),
        ("Безкоштовно", types.get("Безкоштовно", 0), "0"),
        ("Обмін", types.get("Обмін", 0), "0"),
        ("ТОП-оголошень (платне просування)", sum(item["promoted"] for item in listings), "0"),
        ("З OLX доставкою", sum(item["delivery"] for item in listings), "0"),
    ]
    out.pairs(rows)
    if meta.total_found and meta.total_found > total:
        out.line(f"OLX віддає щонайбільше 1 000 оголошень на запит, тому статистика порахована "
                 f"за вибіркою. Звузь запит фільтрами (--city, --min-price, --max-price), щоб охопити все.")

    if stats:
        out.section("Ціни, грн (без безкоштовних)")
        rows = [
            ("Середня (усі оголошення)", stats["mean"], PRICE_FORMAT),
            ("Середня без викидів", clean_stats["mean"], PRICE_FORMAT),
            ("Медіана (типова ціна)", stats["median"], PRICE_FORMAT),
            ("Мінімальна", stats["min"], PRICE_FORMAT),
            ("Максимальна", stats["max"], PRICE_FORMAT),
            ("25% оголошень дешевші за", stats["q1"], PRICE_FORMAT),
            ("75% оголошень дешевші за", stats["q3"], PRICE_FORMAT),
            ("Стандартне відхилення без викидів", clean_stats["stdev"], PRICE_FORMAT),
        ]
        if bounds:
            rows += [
                ("Межі звичайної ціни (IQR)",
                 f"{format_money(max(bounds[0], 0))} – {format_money(bounds[1])} грн", None),
                ("Викидів", outliers, "0"),
            ]
        out.pairs(rows)
        if outliers:
            out.line(f"Оголошень з ціною поза межами Q1 − 1,5·IQR … Q3 + 1,5·IQR: {outliers}. Вони не враховані "
                     f"в «Середня без викидів», у таблицях за групами та на графіку. "
                     f"У таблиці «Оголошення» вони позначені в стовпці «Викид».")

    for title, key, limit in (
        ("За станом", lambda i: i["condition"], None),
        ("За типом продавця", seller_label, None),
        ("Міста (топ-10 за кількістю оголошень)", lambda i: i["city"], 10),
        ("Області (топ-10)", lambda i: i["region"], 10),
    ):
        groups = group_by(listings, key)
        if set(groups) == {NOT_SET}:
            continue
        order = by_size(groups)[:limit]
        out.section(f"{title}, ціни без викидів" if outliers else title)
        out.table([title.split(" (")[0]] + STAT_HEADERS,
                  group_stats_rows(groups, total, order, bounds), STAT_FORMATS)

    if clean_prices:
        out.section("Розподіл цін (без викидів)" if outliers else "Розподіл цін")
        buckets = price_histogram(clean_prices)
        first, last = out.table(["Діапазон, грн", "Оголошень"], [list(b) for b in buckets], [None, "0"])
        add_price_chart(ws, first, last)

    days = Counter(item["posted"][:10] for item in listings if item["posted"])
    if days:
        out.section("Активність за датами публікації або підняття")
        recent = sorted(days, reverse=True)[:14]
        out.table(["Дата", "Оголошень"],
                  [[datetime.fromisoformat(day), days[day]] for day in recent], [DAY_FORMAT, "0"])

    cheapest = sorted((item for item in listings if uah_price(item)), key=uah_price)[:10]
    if cheapest:
        out.section("10 найдешевших оголошень")
        out.ad_table(["Назва", "Ціна", "Стан", "Місто", "Посилання"], cheapest,
                     lambda i: [i["title"], uah_price(i), i["condition"] or NOT_SET, i["city"], None],
                     [None, PRICE_FORMAT, None, None, None], link_col=5)


def write_changes_sheet(ws, changes: Changes):
    ws.title = "Зміни"
    for col, width in enumerate((55, 14, 14, 10, 18, 11), start=1):
        ws.column_dimensions[get_column_letter(col)].width = width

    out = SheetWriter(ws)
    out.title("Зміни з попереднього запуску")
    if changes.baseline:
        out.line("Перший запуск відстеження: усі оголошення збережено як базу. "
                 "Нові оголошення й зниження цін з'являться тут з наступного запуску.")
        return
    if changes.empty:
        out.line("Нових оголошень і знижень цін немає.")
        return

    if changes.new:
        out.section(f"Нові оголошення: {len(changes.new)}")
        out.ad_table(["Назва", "Ціна", "Стан", "Продавець", "Місто", "Посилання"], changes.new,
                     lambda i: [i["title"], table_price(i), i["condition"] or NOT_SET, seller_label(i),
                                i["city"], None],
                     [None, PRICE_FORMAT, None, None, None, None], link_col=6)
    if changes.cheaper:
        out.section(f"Подешевшали: {len(changes.cheaper)}")
        items = [item for item, _ in changes.cheaper]
        old_prices = {item["id"]: old for item, old in changes.cheaper}
        out.ad_table(["Назва", "Було", "Стало", "Зміна", "Місто", "Посилання"], items,
                     lambda i: [i["title"], old_prices[i["id"]], i["price"],
                                i["price"] / old_prices[i["id"]] - 1 if old_prices[i["id"]] else None,
                                i["city"], None],
                     [None, PRICE_FORMAT, PRICE_FORMAT, PERCENT_FORMAT, None, None], link_col=6)


def write_report(path, listings: list[dict], meta: ReportMeta):
    prices = uah_prices(listings)
    stats = price_stats(prices)
    bounds = iqr_bounds(prices)
    workbook = Workbook()
    write_listings_sheet(workbook.active, listings, stats["median"] if stats else None, bounds, meta.sort_label)
    write_analysis_sheet(workbook.create_sheet(), listings, meta)
    if meta.changes is not None:
        write_changes_sheet(workbook.create_sheet(), meta.changes)
    workbook.save(path)
