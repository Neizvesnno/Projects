import argparse
import getpass
import os
import plistlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

from autorun import KEYCHAIN_CHAT, KEYCHAIN_TOKEN, LOG_FILE, PROJECT_DIR, SEARCHES_FILE, keychain_get

LABEL = "local.olx-market-parser"
PLIST_FILE = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
EXAMPLE_FILE = PROJECT_DIR / "searches.example.txt"
DOMAIN = f"gui/{os.getuid()}"


def launchctl(*args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(["/bin/launchctl", *args], capture_output=True, text=True, check=check)


def is_loaded() -> bool:
    return launchctl("print", f"{DOMAIN}/{LABEL}").returncode == 0


def keychain_store(service: str, prompt: str):
    print(prompt)
    print("Введення не відображається. macOS попросить ввести значення двічі.")
    result = subprocess.run(
        ["/usr/bin/security", "add-generic-password", "-U", "-a", getpass.getuser(), "-s", service, "-w"],
    )
    if result.returncode != 0:
        sys.exit("Не вдалося зберегти в Зв'язку ключів.")


def ensure_credentials(force: bool):
    if force or keychain_get(KEYCHAIN_TOKEN) is None:
        keychain_store(KEYCHAIN_TOKEN, "\nВстав токен Telegram-бота від @BotFather.")
    else:
        print("Токен уже є в Зв'язці ключів.")
    if force or keychain_get(KEYCHAIN_CHAT) is None:
        keychain_store(KEYCHAIN_CHAT, "\nВстав свій chat id (число).")
    else:
        print("Chat id уже є в Зв'язці ключів.")


def python_path() -> Path:
    venv_python = PROJECT_DIR / ".venv" / "bin" / "python"
    if venv_python.exists():
        return venv_python
    if sys.prefix == sys.base_prefix:
        sys.exit("Не знайдено .venv у проєкті. Створи його й встанови залежності (див. README).")
    return Path(sys.executable)


def write_plist(interval_minutes: int):
    PLIST_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    plist = {
        "Label": LABEL,
        "ProgramArguments": [str(python_path()), str(PROJECT_DIR / "autorun.py")],
        "StartInterval": interval_minutes * 60,
        "RunAtLoad": True,
        "ProcessType": "Background",
        "LowPriorityIO": True,
        "StandardOutPath": str(LOG_FILE),
        "StandardErrorPath": str(LOG_FILE),
        "EnvironmentVariables": {"PYTHONUNBUFFERED": "1"},
    }
    with open(PLIST_FILE, "wb") as f:
        plistlib.dump(plist, f)


def unload():
    if is_loaded():
        launchctl("bootout", f"{DOMAIN}/{LABEL}")
        for _ in range(20):
            if not is_loaded():
                break
            time.sleep(0.25)


def log_tail(lines: int = 20) -> str:
    try:
        return "\n".join(LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
    except FileNotFoundError:
        return "(журнал ще порожній)"


def cmd_install(args):
    if not SEARCHES_FILE.exists():
        shutil.copy(EXAMPLE_FILE, SEARCHES_FILE)
        print(f"Створено {SEARCHES_FILE.name} із прикладу. Відредагуй запити в ньому й запусти install ще раз.")
        return
    if args.every < 5:
        sys.exit("Інтервал має бути щонайменше 5 хвилин.")

    ensure_credentials(force=args.reset_token)
    unload()
    write_plist(args.every)
    result = launchctl("bootstrap", DOMAIN, str(PLIST_FILE))
    if result.returncode != 0:
        sys.exit(f"launchctl не зміг увімкнути автозапуск: {result.stderr.strip()}")

    print(f"\nАвтозапуск увімкнено: перевірка під час входу в систему і кожні {args.every} хв, поки Mac увімкнений.")
    print("Перша перевірка вже запущена, чекаю 20 секунд на результат…")
    time.sleep(20)
    tail = log_tail()
    print(tail)
    if "Operation not permitted" in tail:
        print("\nmacOS заборонив фоновому Python доступ до папки проєкту. Відкрий Системні параметри → "
              "Конфіденційність і безпека → Повний доступ до диска, додай туди\n"
              f"{Path(os.path.realpath(python_path()))}\nабо перенеси проєкт з Робочого столу, "
              f"наприклад у ~/Projects, і запусти install ще раз.")


def cmd_uninstall(args):
    unload()
    PLIST_FILE.unlink(missing_ok=True)
    print("Автозапуск вимкнено.")
    if args.forget_token:
        for service in (KEYCHAIN_TOKEN, KEYCHAIN_CHAT):
            subprocess.run(["/usr/bin/security", "delete-generic-password", "-a", getpass.getuser(), "-s", service],
                           capture_output=True)
        print("Токен і chat id видалено із Зв'язки ключів.")
    else:
        print("Токен і chat id лишились у Зв'язці ключів (видалити: uninstall --forget-token).")


def cmd_status(args):
    if not is_loaded():
        print("Автозапуск вимкнено.")
    else:
        info = launchctl("print", f"{DOMAIN}/{LABEL}").stdout
        state = next((line.strip() for line in info.splitlines() if line.strip().startswith("state =")), "")
        interval = plistlib.loads(PLIST_FILE.read_bytes()).get("StartInterval", 0) // 60
        print(f"Автозапуск увімкнено, кожні {interval} хв ({state or 'стан невідомий'}).")
    print(f"Токен у Зв'язці ключів: {'є' if keychain_get(KEYCHAIN_TOKEN) else 'немає'}; "
          f"chat id: {'є' if keychain_get(KEYCHAIN_CHAT) else 'немає'}")
    print(f"\nОстанні записи журналу ({LOG_FILE}):\n{log_tail(args.lines)}")


def cmd_run(args):
    if not is_loaded():
        sys.exit("Автозапуск вимкнено. Спершу: python autorun_setup.py install")
    launchctl("kickstart", "-k", f"{DOMAIN}/{LABEL}")
    print("Перевірку запущено. Журнал: python autorun_setup.py status")


def main():
    parser = argparse.ArgumentParser(description="Автозапуск перевірки OLX через launchd (macOS).")
    sub = parser.add_subparsers(dest="command", required=True)

    install = sub.add_parser("install", help="увімкнути автозапуск або змінити інтервал")
    install.add_argument("--every", type=int, default=30, help="інтервал перевірки, хвилин (за замовчуванням 30)")
    install.add_argument("--reset-token", action="store_true", help="заново ввести токен і chat id")
    install.set_defaults(func=cmd_install)

    uninstall = sub.add_parser("uninstall", help="вимкнути автозапуск")
    uninstall.add_argument("--forget-token", action="store_true", help="також видалити токен і chat id")
    uninstall.set_defaults(func=cmd_uninstall)

    status = sub.add_parser("status", help="стан і останні записи журналу")
    status.add_argument("--lines", type=int, default=20)
    status.set_defaults(func=cmd_status)

    run = sub.add_parser("run", help="запустити перевірку зараз")
    run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
