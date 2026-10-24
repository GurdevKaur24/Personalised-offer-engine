"""Run the Telegram bot:  python -m bot.main

Reads TELEGRAM_BOT_TOKEN from the environment or from the .env file in the project folder (never commit it).
"""
import argparse
import os
import sys
import time
import traceback
from datetime import timedelta
from pathlib import Path

from peshkash.datagen import generate, load_sqlite, write_csv, write_sqlite
from peshkash.features import customer_view

from . import texts
from .app import OfferBot
from .store import Store
from .telegram import TelegramAPI, TelegramError

BACKEND = Path(__file__).resolve().parent.parent
DATA = BACKEND / "data"


def load_env(path: Path) -> None:
    """Minimal .env reader: KEY=VALUE lines; values already in the environment win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Run the Peshkash Telegram bot.")
    ap.add_argument("--cart-minutes", type=float, default=2, help="minutes before a left cart gets a reminder")
    args = ap.parse_args()

    load_env(BACKEND.parent / ".env")
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("No bot token found.\n"
              "1. In Telegram, open @BotFather, send /newbot and follow the steps.\n"
              "2. Copy .env.example to .env in the project folder and paste the token after TELEGRAM_BOT_TOKEN=\n"
              "3. Run this again. Never commit .env or share the token.")
        sys.exit(1)

    db = DATA / "generated" / "peshkash.db"
    if not db.exists():
        print("Generating synthetic customers (first run)...")
        raw = generate()
        write_sqlite(raw, db)
        write_csv(raw, db.parent)
    customers = [customer_view(c) for c in load_sqlite(db)]

    api = TelegramAPI(token)
    try:
        me = api.get_me()
    except (TelegramError, OSError) as e:
        print(f"Could not reach Telegram: {e}. Check the token and the internet connection.")
        sys.exit(1)
    api.set_commands(texts.COMMANDS)
    bot = OfferBot(api, Store(DATA / "live.db"), customers, DATA / "rules.json", cart_delay=timedelta(minutes=args.cart_minutes))
    print(f"Bot @{me['username']} is running with {len(customers):,} shoppers. Share this link: https://t.me/{me['username']}")
    print("Press Ctrl+C to stop.")

    offset = None
    while True:
        try:
            updates = api.get_updates(offset, timeout=20)
        except KeyboardInterrupt:
            print("Stopped.")
            return
        except (TelegramError, OSError) as e:
            print(f"Telegram not reachable ({e}); trying again in 5 seconds.")
            time.sleep(5)
            continue
        for u in updates:
            offset = u["update_id"] + 1
            try:
                bot.handle(u)
            except Exception:                                # one bad update must not stop the bot
                traceback.print_exc()
        try:
            bot.tick()
        except Exception:
            traceback.print_exc()


if __name__ == "__main__":
    main()
