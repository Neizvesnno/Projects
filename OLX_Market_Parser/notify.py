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


def ad_line(item: dict, extra: str = "") -> str:
    title = html.escape(item["title"][:90])
    city = html.escape(item["city"]) if item["city"] else ""
    details = " · ".join(part for part in (extra or format_price(item["price"], item["currency"]), city) if part)
    return f'• <a href="{html.escape(item["link"], quote=True)}">{title}</a>\n  {details}'


def format_changes(query: str, filters: str, changes: Changes) -> list[str]:
    lines = [f"<b>OLX: «{html.escape(query)}»</b> ({html.escape(filters)})"]
    if changes.new:
        lines.append(f"\n<b>Нові оголошення: {len(changes.new)}</b>")
        lines += [ad_line(item) for item in changes.new[:ITEMS_LIMIT]]
        if len(changes.new) > ITEMS_LIMIT:
            lines.append(f"…і ще {len(changes.new) - ITEMS_LIMIT}, усі є в звіті")
    if changes.cheaper:
        lines.append(f"\n<b>Подешевшали: {len(changes.cheaper)}</b>")
        for item, old_price in changes.cheaper[:ITEMS_LIMIT]:
            drop = (1 - item["price"] / old_price) * 100 if old_price else 0
            extra = (f"{format_price(old_price, item['currency'])} → "
                     f"{format_price(item['price'], item['currency'])} (−{drop:.0f}%)")
            lines.append(ad_line(item, extra))
        if len(changes.cheaper) > ITEMS_LIMIT:
            lines.append(f"…і ще {len(changes.cheaper) - ITEMS_LIMIT}, усі є в звіті")
    return split_messages(lines)


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
