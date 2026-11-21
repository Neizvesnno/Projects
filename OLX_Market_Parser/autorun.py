import getpass
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

PROJECT_DIR = Path(__file__).resolve().parent
SEARCHES_FILE = PROJECT_DIR / "searches.txt"
REPORTS_DIR = PROJECT_DIR / "reports"
LOG_FILE = Path.home() / "Library" / "Logs" / "olx-market-parser.log"
LOG_MAX_BYTES = 1_000_000

KEYCHAIN_TOKEN = "olx-telegram-token"
KEYCHAIN_CHAT = "olx-telegram-chat"
NETWORK_WAIT = 120
FORBIDDEN_ARGS = {"--every"}


def log(message: str):
    print(f"[{datetime.now():%d.%m.%Y %H:%M:%S}] {message}", flush=True)


def trim_log():
    try:
        if LOG_FILE.stat().st_size > LOG_MAX_BYTES:
            tail = LOG_FILE.read_bytes()[-LOG_MAX_BYTES // 2:]
            LOG_FILE.write_bytes(tail[tail.find(b"\n") + 1:])
    except OSError:
        pass


def keychain_get(service: str) -> str | None:
    result = subprocess.run(
        ["/usr/bin/security", "find-generic-password", "-a", getpass.getuser(), "-s", service, "-w"],
        capture_output=True, text=True,
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def load_credentials() -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN") or keychain_get(KEYCHAIN_TOKEN)
    chat_id = os.environ.get("TELEGRAM_CHAT_ID") or keychain_get(KEYCHAIN_CHAT)
    if not token or not chat_id:
        return False
    os.environ["TELEGRAM_BOT_TOKEN"] = token
    os.environ["TELEGRAM_CHAT_ID"] = chat_id
    return True


def load_searches() -> list[list[str]]:
    searches = []
    for number, line in enumerate(SEARCHES_FILE.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            args = shlex.split(line)
        except ValueError as error:
            log(f"searches.txt, рядок {number}: не вдалося розібрати ({error}), пропускаю.")
            continue
        if FORBIDDEN_ARGS & set(args):
            log(f"searches.txt, рядок {number}: параметр {', '.join(FORBIDDEN_ARGS & set(args))} тут не потрібен, "
                f"розклад задає автозапуск. Пропускаю рядок.")
            continue
        searches.append(args)
    return searches


def wait_for_network() -> bool:
    deadline = time.monotonic() + NETWORK_WAIT
    while True:
        try:
            requests.head("https://www.olx.ua", timeout=5)
            return True
        except requests.RequestException:
            if time.monotonic() >= deadline:
                return False
            time.sleep(10)


def output_args(args: list[str], number: int) -> list[str]:
    if "-o" in args or "--output" in args:
        return []
    return ["-o", str(REPORTS_DIR / f"search-{number}.xlsx")]


def main() -> int:
    trim_log()
    os.chdir(PROJECT_DIR)
    log("Перевірка OLX")

    if not SEARCHES_FILE.exists():
        log(f"Немає файлу {SEARCHES_FILE.name}. Створи його за зразком searches.example.txt.")
        return 1
    searches = load_searches()
    if not searches:
        log(f"У {SEARCHES_FILE.name} немає жодного запиту.")
        return 1
    if not load_credentials():
        log("Немає токена або chat id у Зв'язці ключів. Запусти: python autorun_setup.py install")
        return 1
    if not wait_for_network():
        log("Немає інтернету. Зміни не втрачено: вони прийдуть під час наступної перевірки.")
        return 1

    import main as parser_main

    batch = [args + ["--notify"] + output_args(args, number) for number, args in enumerate(searches, start=1)]
    try:
        failed = parser_main.run_batch(batch, log=log)
    except Exception as error:
        log(f"Помилка: {error.__class__.__name__}: {error}")
        failed = len(searches)

    log(f"Готово, з помилками: {failed} з {len(searches)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
