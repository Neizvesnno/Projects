import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

PRICE_FORMAT = '#,##0 "грн"'
PERCENT_FORMAT = '+0%;-0%;0%'
SHARE_FORMAT = '0%'
DATE_FORMAT = 'DD.MM.YYYY HH:MM'
DAY_FORMAT = 'DD.MM.YYYY'

HEADER_FONT = Font(bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="23A094")
TITLE_FONT = Font(bold=True, size=14)
SECTION_FONT = Font(bold=True, size=12, color="23A094")
NO_CONDITION = "Не вказано"

LISTING_COLUMNS = [
    ("Назва", 55),
    ("Ціна, грн", 14),
    ("Тип ціни", 13),
    ("Стан", 11),
    ("Місто", 18),
    ("Район", 18),
    ("Дата", 17),
    ("Від медіани", 12),
    ("ТОП", 6),
    ("Доставка", 10),
    ("Посилання", 11),
    ("Ціна на сайті", 22),
]


def uah_price(item: dict) -> float | None:
    return item["price"] if item["currency"] == "UAH" else None


def uah_prices(listings: list[dict]) -> list[float]:
    return [price for price in map(uah_price, listings) if price is not None]


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


def set_link(cell, url: str):
    cell.value = "Відкрити"
    cell.hyperlink = url
    cell.style = "Hyperlink"


def write_listings_sheet(ws, listings: list[dict], median: float | None, sort_label: str):
    ws.title = "Оголошення"
    for col, (header, width) in enumerate(LISTING_COLUMNS, start=1):
        ws.cell(row=1, column=col, value=header)
        ws.column_dimensions[get_column_letter(col)].width = width
    style_header(ws[1])

    for row, item in enumerate(listings, start=2):
        price = uah_price(item)
        if item["price_type"] == "Безкоштовно":
            price = 0
        posted = datetime.fromisoformat(item["posted"]) if item["posted"] else None
        deviation = price / median - 1 if price and median else None

        values = [
            item["title"], price, item["price_type"], item["condition"] or NO_CONDITION,
            item["city"], item["district"], posted, deviation,
            "так" if item["promoted"] else "", "так" if item["delivery"] else "",
            None, item["price_text"],
        ]
        for col, value in enumerate(values, start=1):
            ws.cell(row=row, column=col, value=value)
        ws.cell(row=row, column=2).number_format = PRICE_FORMAT
        ws.cell(row=row, column=7).number_format = DATE_FORMAT
        ws.cell(row=row, column=8).number_format = PERCENT_FORMAT
        set_link(ws.cell(row=row, column=11), item["link"])

    last_row = len(listings) + 1
    last_col = get_column_letter(len(LISTING_COLUMNS))
    table = Table(displayName="Listings", ref=f"A1:{last_col}{last_row}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleLight9", showRowStripes=True)
    ws.add_table(table)
    ws.freeze_panes = "B2"

    ws.conditional_formatting.add(
        f"B2:B{last_row}",
        ColorScaleRule(start_type="percentile", start_value=5, start_color="63BE7B",
                       mid_type="percentile", mid_value=50, mid_color="FFEB84",
                       end_type="percentile", end_value=95, end_color="F8696B"),
    )
    ws.conditional_formatting.add(
        f"H2:H{last_row}",
        ColorScaleRule(start_type="num", start_value=-0.5, start_color="63BE7B",
                       mid_type="num", mid_value=0, mid_color="FFFFFF",
                       end_type="num", end_value=0.5, end_color="F8696B"),
    )

    price_range = f"B2:B{last_row}"
    summary = [
        ("Середня ціна", f"=SUBTOTAL(101,{price_range})", PRICE_FORMAT),
        ("Мінімальна ціна", f"=SUBTOTAL(105,{price_range})", PRICE_FORMAT),
        ("Максимальна ціна", f"=SUBTOTAL(104,{price_range})", PRICE_FORMAT),
        ("Оголошень з ціною", f"=SUBTOTAL(102,{price_range})", "0"),
    ]
    row = last_row + 2
    ws.cell(row=row, column=1, value="Підсумок (з урахуванням фільтрів таблиці)").font = SECTION_FONT
    for label, formula, fmt in summary:
        row += 1
        ws.cell(row=row, column=1, value=label).font = Font(bold=True)
        cell = ws.cell(row=row, column=2, value=formula)
        cell.number_format = fmt
        cell.font = Font(bold=True)
    ws.cell(row=row + 2, column=1,
            value=f"Початкове сортування: {sort_label}. Кнопки в заголовку таблиці дозволяють "
                  f"пересортувати й відфільтрувати за будь-яким стовпцем.").font = Font(italic=True, color="666666")


class SheetWriter:
    def __init__(self, ws):
        self.ws = ws
        self.row = 1

    def title(self, text: str):
        self.ws.cell(row=self.row, column=1, value=text).font = TITLE_FONT
        self.row += 1

    def line(self, text: str):
        self.ws.cell(row=self.row, column=1, value=text).font = Font(color="666666")
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


def group_stats_rows(groups: dict[str, list[dict]], total: int, order: list[str]) -> list[list]:
    rows = []
    for name in order:
        items = groups[name]
        stats = price_stats(uah_prices(items))
        rows.append([
            name, len(items), len(items) / total,
            stats["mean"] if stats else None, stats["median"] if stats else None,
            stats["min"] if stats else None, stats["max"] if stats else None,
        ])
    return rows


def write_analysis_sheet(ws, listings: list[dict], query: str, fetched_at: datetime):
    ws.title = "Аналіз"
    for col, width in enumerate((34, 14, 10, 14, 14, 14, 14), start=1):
        ws.column_dimensions[get_column_letter(col)].width = width

    total = len(listings)
    prices = uah_prices(listings)
    stats = price_stats(prices)
    types = Counter(item["price_type"] for item in listings)

    out = SheetWriter(ws)
    out.title(f"Аналіз ринку OLX: «{query}»")
    out.line(f"Дані станом на {fetched_at:%d.%m.%Y %H:%M}")

    out.section("Загальне")
    out.pairs([
        ("Усього оголошень", total, "0"),
        ("З ціною в гривнях", len(prices), "0"),
        ("Ціна договірна", types.get("Договірна", 0), "0"),
        ("Безкоштовно", types.get("Безкоштовно", 0), "0"),
        ("Без ціни або інша валюта", total - len(prices) - types.get("Безкоштовно", 0), "0"),
        ("ТОП-оголошень (платне просування)", sum(item["promoted"] for item in listings), "0"),
        ("З OLX доставкою", sum(item["delivery"] for item in listings), "0"),
    ])

    if stats:
        out.section("Ціни, грн (без безкоштовних)")
        out.pairs([
            ("Середня", stats["mean"], PRICE_FORMAT),
            ("Медіана (типова ціна)", stats["median"], PRICE_FORMAT),
            ("Мінімальна", stats["min"], PRICE_FORMAT),
            ("Максимальна", stats["max"], PRICE_FORMAT),
            ("25% оголошень дешевші за", stats["q1"], PRICE_FORMAT),
            ("75% оголошень дешевші за", stats["q3"], PRICE_FORMAT),
            ("Стандартне відхилення", stats["stdev"], PRICE_FORMAT),
        ])
        if stats["mean"] > stats["median"] * 1.3:
            out.line("Середня значно вища за медіану: кілька дуже дорогих оголошень "
                     "тягнуть середню вгору, орієнтуйся на медіану.")

    stat_headers = ["Кількість", "Частка", "Середня", "Медіана", "Мін", "Макс"]
    stat_formats = [None, "0", SHARE_FORMAT, PRICE_FORMAT, PRICE_FORMAT, PRICE_FORMAT, PRICE_FORMAT]

    by_condition = defaultdict(list)
    for item in listings:
        by_condition[item["condition"] or NO_CONDITION].append(item)
    out.section("За станом")
    order = sorted(by_condition, key=lambda name: (name == NO_CONDITION, -len(by_condition[name])))
    out.table(["Стан"] + stat_headers, group_stats_rows(by_condition, total, order), stat_formats)

    by_city = defaultdict(list)
    for item in listings:
        by_city[item["city"] or NO_CONDITION].append(item)
    top_cities = sorted(by_city, key=lambda name: -len(by_city[name]))[:10]
    out.section(f"Міста (топ-{len(top_cities)} за кількістю оголошень)")
    out.table(["Місто"] + stat_headers, group_stats_rows(by_city, total, top_cities), stat_formats)

    if prices:
        out.section("Розподіл цін")
        buckets = price_histogram(prices)
        first, last = out.table(["Діапазон, грн", "Оголошень"], [list(b) for b in buckets], [None, "0"])
        chart = BarChart()
        chart.title = "Кількість оголошень за ціною"
        chart.y_axis.title = "Оголошень"
        chart.legend = None
        chart.add_data(Reference(ws, min_col=2, min_row=first, max_row=last), titles_from_data=True)
        chart.set_categories(Reference(ws, min_col=1, min_row=first + 1, max_row=last))
        chart.width, chart.height = 18, 8
        ws.add_chart(chart, f"I{first}")

    days = Counter(item["posted"][:10] for item in listings if item["posted"])
    if days:
        out.section("Активність за датами публікації або підняття")
        recent = sorted(days, reverse=True)[:14]
        out.table(["Дата", "Оголошень"],
                  [[datetime.fromisoformat(day), days[day]] for day in recent], [DAY_FORMAT, "0"])

    cheapest = sorted((item for item in listings if uah_price(item)), key=uah_price)[:10]
    if cheapest:
        out.section("10 найдешевших оголошень")
        header_row = out.row
        out.table(["Назва", "Ціна", "Стан", "Місто", "Посилання"],
                  [[item["title"], uah_price(item), item["condition"] or NO_CONDITION, item["city"], None]
                   for item in cheapest],
                  [None, PRICE_FORMAT, None, None, None])
        for offset, item in enumerate(cheapest, start=1):
            set_link(ws.cell(row=header_row + offset, column=5), item["link"])


def write_report(path: str, listings: list[dict], query: str, fetched_at: datetime, sort_label: str):
    stats = price_stats(uah_prices(listings))
    workbook = Workbook()
    write_listings_sheet(workbook.active, listings, stats["median"] if stats else None, sort_label)
    write_analysis_sheet(workbook.create_sheet(), listings, query, fetched_at)
    workbook.save(path)
