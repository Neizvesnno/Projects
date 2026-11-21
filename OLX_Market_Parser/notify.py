import html
import os

import requests

from tracker import Changes

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
MESSAGE_LIMIT = 4000
ITEMS_LIMIT = 15


class NotifyError(Exception):
    pass


def telegram_credentials() -> tuple[str, str] | None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if token and chat_id:
        return token, chat_id
    return None


def format_price(value: float | None, currency: str = "UAH") -> str:
    if value is None:
        return "—"
    amount = f"{value:,.0f}".replace(",", " ")
    return f"{amount} грн" if currency in ("UAH", "") else f"{amount} {currency}"


def ad_line(item: dict, extra: str = "", source: str = "") -> str:
    title = html.escape(item["title"][:90])
    city = html.escape(item["city"]) if item["city"] else ""
    found_by = f"«{html.escape(source)}»" if source else ""
    details = " · ".join(part for part in (extra or format_price(item["price"], item["currency"]), city, found_by)
                         if part)
    return f'• <a href="{html.escape(item["link"], quote=True)}">{title}</a>\n  {details}'


def format_changes(query: str, filters: str, changes: Changes) -> list[str]:
    header = f"<b>OLX: «{html.escape(query)}»</b> ({html.escape(filters)})"
    return format_combined(header, [(query, changes)], show_source=False)


def format_combined(header: str, sections: list[tuple[str, Changes]], show_source: bool = True) -> list[str]:
    """Об'єднує зміни кількох запитів в одне повідомлення без повторів одного оголошення."""
    new, cheaper, seen_new, seen_cheaper = [], [], set(), set()
    for source, changes in sections:
        label = source if show_source else ""
        for item in changes.new:
            if item["id"] not in seen_new:
                seen_new.add(item["id"])
                new.append((item, label))
        for item, old_price in changes.cheaper:
            if item["id"] not in seen_cheaper and item["id"] not in seen_new:
                seen_cheaper.add(item["id"])
                cheaper.append((item, old_price, label))

    lines = [header]
    if new:
        lines.append(f"\n<b>Нові оголошення: {len(new)}</b>")
        lines += [ad_line(item, source=label) for item, label in new[:ITEMS_LIMIT]]
        if len(new) > ITEMS_LIMIT:
            lines.append(f"…і ще {len(new) - ITEMS_LIMIT}, усі є в звітах")
    if cheaper:
        lines.append(f"\n<b>Подешевшали: {len(cheaper)}</b>")
        for item, old_price, label in cheaper[:ITEMS_LIMIT]:
            drop = (1 - item["price"] / old_price) * 100 if old_price else 0
            extra = (f"{format_price(old_price, item['currency'])} → "
                     f"{format_price(item['price'], item['currency'])} (−{drop:.0f}%)")
            lines.append(ad_line(item, extra, label))
        if len(cheaper) > ITEMS_LIMIT:
            lines.append(f"…і ще {len(cheaper) - ITEMS_LIMIT}, усі є в звітах")
    return split_messages(lines) if new or cheaper else []


def split_messages(lines: list[str]) -> list[str]:
    messages, current = [], ""
    for line in lines:
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > MESSAGE_LIMIT and current:
            messages.append(current)
            current = line
        else:
            current = candidate
    if current:
        messages.append(current)
    return messages


def send_telegram(token: str, chat_id: str, messages: list[str]):
    for text in messages:
        try:
            response = requests.post(
                TELEGRAM_API.format(token=token),
                json={"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                      "disable_web_page_preview": True},
                timeout=(10, 30),
            )
        except requests.RequestException as error:
            raise NotifyError(f"Telegram недоступний: {error.__class__.__name__}") from None
        if response.status_code != 200:
            try:
                description = response.json().get("description", "")
            except ValueError:
                description = ""
            raise NotifyError(f"Telegram відповів {response.status_code}: {description}")
