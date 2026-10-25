"""Live bot state in SQLite: who started the bot, which synthetic shopper they are, offers, carts and an audit log.

Only the Telegram chat id is kept about a bot user; no names or usernames.
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY, customer_id TEXT, lang TEXT, started_at TEXT, stopped INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS profiles (chat_id INTEGER, customer_id TEXT, assigned_at TEXT);
CREATE TABLE IF NOT EXISTS offers (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, customer_id TEXT, type TEXT,
  summary TEXT, code TEXT, expiry TEXT, cost INTEGER, text TEXT, reason TEXT, status TEXT, trigger TEXT, source TEXT, created_at TEXT, send_at TEXT,
  sent_at TEXT, answered_at TEXT, message_id INTEGER, checks TEXT);
CREATE TABLE IF NOT EXISTS carts (chat_id INTEGER PRIMARY KEY, items TEXT, started_at TEXT, updated_at TEXT, reminded INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS live_orders (chat_id INTEGER, customer_id TEXT, at TEXT, value INTEGER, items TEXT);
CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT, chat_id INTEGER, kind TEXT, detail TEXT);
"""
COMMITTED = ("queued", "sent", "claimed", "later")      # offers that count against the budget


class Store:
    def __init__(self, path: Path | str):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        if "source" not in {r[1] for r in self.db.execute("PRAGMA table_info(offers)")}:   # made before the AI agent
            self.db.execute("ALTER TABLE offers ADD COLUMN source TEXT")

    def _one(self, sql, *args):
        return self.db.execute(sql, args).fetchone()

    def _run(self, sql, *args):
        cur = self.db.execute(sql, args)
        self.db.commit()
        return cur

    # ----- users and profiles -----
    def user(self, chat_id: int):
        return self._one("SELECT * FROM users WHERE chat_id=?", chat_id)

    def add_user(self, chat_id: int, now: datetime):
        self._run("INSERT OR IGNORE INTO users (chat_id, started_at) VALUES (?, ?)", chat_id, now.isoformat())

    def set_lang(self, chat_id: int, lang: str):
        self._run("UPDATE users SET lang=? WHERE chat_id=?", lang, chat_id)

    def set_stopped(self, chat_id: int, stopped: bool):
        self._run("UPDATE users SET stopped=? WHERE chat_id=?", int(stopped), chat_id)

    def assign(self, chat_id: int, customer_id: str, now: datetime):
        self._run("UPDATE users SET customer_id=? WHERE chat_id=?", customer_id, chat_id)
        self._run("INSERT INTO profiles VALUES (?, ?, ?)", chat_id, customer_id, now.isoformat())

    def taken_customers(self) -> set[str]:
        return {r[0] for r in self.db.execute("SELECT customer_id FROM profiles")}

    # ----- offers -----
    def add_offer(self, chat_id, customer_id, offer, summary, status, trigger, now, send_at, checks, source="rules") -> int:
        cur = self._run(
            "INSERT INTO offers (chat_id, customer_id, type, summary, code, expiry, cost, text, reason, status, trigger, source, created_at, send_at, checks)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            chat_id, customer_id, offer.type, summary, offer.code, offer.expiry_label, offer.cost, offer.text, offer.reason, status, trigger, source,
            now.isoformat(), send_at.isoformat(), json.dumps([{"id": c.id, "ok": c.ok, "detail": c.detail} for c in checks], ensure_ascii=False))
        return cur.lastrowid

    def offer(self, offer_id: int):
        return self._one("SELECT * FROM offers WHERE id=?", offer_id)

    def mark_sent(self, offer_id: int, message_id: int, now: datetime):
        self._run("UPDATE offers SET status='sent', sent_at=?, message_id=? WHERE id=?", now.isoformat(), message_id, offer_id)

    def set_status(self, offer_id: int, status: str, now: datetime):
        self._run("UPDATE offers SET status=?, answered_at=? WHERE id=?", status, now.isoformat(), offer_id)

    def cancel_queued(self, chat_id: int, now: datetime):
        self._run("UPDATE offers SET status='cancelled', answered_at=? WHERE chat_id=? AND status='queued'", now.isoformat(), chat_id)

    def due_offers(self, now: datetime):
        return self.db.execute("SELECT * FROM offers WHERE status='queued' AND send_at<=? ORDER BY id", (now.isoformat(),)).fetchall()

    def sent_times(self, customer_id: str) -> list[datetime]:
        """When this synthetic customer was actually sent live offers (most recent first)."""
        rows = self.db.execute("SELECT sent_at FROM offers WHERE customer_id=? AND sent_at IS NOT NULL ORDER BY sent_at DESC", (customer_id,))
        return [datetime.fromisoformat(r[0]) for r in rows]

    def spent(self) -> int:
        return self._one(f"SELECT COALESCE(SUM(cost), 0) FROM offers WHERE status IN ({','.join('?' * len(COMMITTED))})", *COMMITTED)[0]

    # ----- carts and orders -----
    def cart(self, chat_id: int):
        r = self._one("SELECT * FROM carts WHERE chat_id=?", chat_id)
        return None if r is None or not json.loads(r["items"]) else {**dict(r), "items": json.loads(r["items"])}

    def add_to_cart(self, chat_id: int, item: dict, now: datetime):
        cur = self.cart(chat_id)
        items = (cur["items"] if cur else []) + [item]
        started = cur["started_at"] if cur else now.isoformat()
        self._run("INSERT OR REPLACE INTO carts VALUES (?, ?, ?, ?, 0)", chat_id, json.dumps(items, ensure_ascii=False), started, now.isoformat())

    def clear_cart(self, chat_id: int):
        self._run("DELETE FROM carts WHERE chat_id=?", chat_id)

    def carts_to_remind(self, before: datetime):
        return self.db.execute("SELECT chat_id FROM carts WHERE reminded=0 AND updated_at<=?", (before.isoformat(),)).fetchall()

    def mark_reminded(self, chat_id: int):
        self._run("UPDATE carts SET reminded=1 WHERE chat_id=?", chat_id)

    def add_live_order(self, chat_id: int, customer_id: str, now: datetime, items: list[dict]):
        self._run("INSERT INTO live_orders VALUES (?, ?, ?, ?, ?)", chat_id, customer_id, now.isoformat(),
                  sum(x["price"] for x in items), json.dumps(items, ensure_ascii=False))

    def live_orders(self, customer_id: str):
        return self.db.execute("SELECT * FROM live_orders WHERE customer_id=? ORDER BY at DESC", (customer_id,)).fetchall()

    # ----- audit log -----
    def log(self, chat_id: int | None, kind: str, detail: str, now: datetime):
        self._run("INSERT INTO events (at, chat_id, kind, detail) VALUES (?, ?, ?, ?)", now.isoformat(), chat_id, kind, detail)
