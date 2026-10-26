"""Marketer console server.

GET  /                 the console (prototype/index.html), which switches to live mode when /api/status answers
GET  /login, POST /login, GET /logout   sign-in page and session (only when a password is set)
GET  /api/status       bot, AI model and data size
GET  /api/rules        the rules the bot uses now
PUT  /api/rules        save new rules (refused with plain-English problems if any value is out of range)
GET  /api/live         live results: subscribers, offers, claims, stops, budget, charts data and the latest offers
GET  /api/decisions    the decision log: every time the engine decided, including when nothing was sent
GET  /api/export.csv   every offer as a spreadsheet (no chat ids)
GET  /health           "ok" for uptime monitors (no password; says nothing about the data)

On this computer it listens on 127.0.0.1 with no password. When hosted (public), everything except /health and the
sign-in page needs a session from signing in with PESHKASH_PAGE_PASSWORD; without one set, the console stays locked.
Bot users are shown only as the sample customer they shop as.
"""
import csv
import hashlib
import hmac
import io
import json
import secrets
import sqlite3
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from peshkash.features import SEGMENTS
from peshkash.rules import LIMITS, OFFER_TYPES, Rules, RulesError, load_rules, save_rules

DELIVERED = ("sent", "claimed", "later", "stopped")
COMMITTED = ("queued", "sent", "claimed", "later")
COOKIE = "peshkash_session"
SESSION_DAYS = 7
MAX_FAILED, FAILED_WINDOW = 10, 600          # sign-in attempts per address per 10 minutes


class Api:
    def __init__(self, data_dir: Path, page: Path, customers: list[dict], status: dict | None = None,
                 password: str | None = None, public: bool = False):
        self.data_dir, self.page = Path(data_dir), Path(page)
        self.login_page = self.page.parent / "login.html"
        self.password = password or None
        self.public = public
        self.locked = public and not self.password           # public with no password: show nothing
        self.rules_path = self.data_dir / "rules.json"
        self.db_path = self.data_dir / "live.db"
        self.shoppers = {c["id"]: {"name": c["name"], "seg": c["seg"], "seg_label": SEGMENTS[c["seg"]]["label"],
                                   "city": c["city"], "lang": c["lang"]} for c in customers}
        self.info = {"live": True, "customers": len(customers), "bot": None, "ai_model": None,
                     "signed_in_with_password": bool(self.password), **(status or {})}
        self._failed: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    # ----- sign-in -----
    def session_token(self) -> str:
        """Same for every signed-in browser; changes (signing everyone out) when the password changes."""
        return hmac.new(self.password.encode(), b"peshkash-console-session-v1", hashlib.sha256).hexdigest()

    def valid_session(self, cookie_header: str) -> bool:
        for part in (cookie_header or "").split(";"):
            name, _, value = part.strip().partition("=")
            if name == COOKIE and secrets.compare_digest(value.encode(), self.session_token().encode()):
                return True
        return False

    def too_many_tries(self, address: str) -> bool:
        with self._lock:
            now = time.time()
            self._failed[address] = [t for t in self._failed[address] if now - t < FAILED_WINDOW]
            return len(self._failed[address]) >= MAX_FAILED

    def check_password(self, address: str, given: str) -> bool:
        ok = secrets.compare_digest(given.encode(), self.password.encode())
        if not ok:
            with self._lock:
                self._failed[address].append(time.time())
        return ok

    def render_login(self, error: str = "") -> bytes:
        html = self.login_page.read_text(encoding="utf-8")
        note = f'<p class="error" role="alert">{error}</p>' if error else ""
        return html.replace("{{error}}", note).replace("{{bot}}", self.info.get("bot") or "the bot").encode()

    def _db(self) -> sqlite3.Connection | None:
        if not self.db_path.exists():
            return None
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        return db

    # ----- rules -----
    def get_rules(self) -> tuple[int, dict]:
        return 200, {"rules": load_rules(self.rules_path).to_dict(),
                     "limits": {k: {"min": lo, "max": hi, "label": label} for k, (lo, hi, label) in LIMITS.items()},
                     "offer_types": OFFER_TYPES}

    def put_rules(self, body: dict) -> tuple[int, dict]:
        if not isinstance(body, dict):
            return 400, {"problems": ["Send the rules as a JSON object."]}
        try:
            rules = Rules.from_dict(body)
        except RulesError as e:
            return 400, {"problems": e.problems}
        except TypeError:
            return 400, {"problems": ["The rules could not be read."]}
        save_rules(rules, self.rules_path)
        return 200, {"rules": rules.to_dict(), "message": "Saved. The bot uses these rules from its next decision."}

    # ----- live results -----
    def _decisions_by_offer(self, db) -> dict[int, dict]:
        out = {}
        for e in db.execute("SELECT detail FROM events WHERE kind='decision' ORDER BY id"):
            d = json.loads(e["detail"])
            if d.get("offer_id"):
                out[d["offer_id"]] = d
        return out

    @staticmethod
    def _timeline(rows) -> list[dict]:
        """Offers per hour (if everything is within two days) or per day, split by what happened."""
        stamps = [datetime.fromisoformat(r["created_at"]) for r in rows]
        if not stamps:
            return []
        hourly = max(stamps) - min(stamps) <= timedelta(days=2)
        key = (lambda t: t.replace(minute=0, second=0, microsecond=0)) if hourly else (lambda t: t.replace(hour=0, minute=0, second=0, microsecond=0))
        buckets: dict[datetime, Counter] = {}
        for r, t in zip(rows, stamps):
            buckets.setdefault(key(t), Counter())[r["status"]] += 1
        start, end, step = min(buckets), max(buckets), timedelta(hours=1) if hourly else timedelta(days=1)
        out, t = [], start
        while t <= end and len(out) < 96:                    # fill gaps so the chart shows quiet periods too
            c = buckets.get(t, Counter())
            label = t.strftime("%d %b, %I %p").replace(" 0", " ") if hourly else t.strftime("%d %b")
            out.append({"label": label.lstrip("0"), "claimed": c["claimed"], "later": c["later"], "no_answer": c["sent"],
                        "stopped": c["stopped"], "queued": c["queued"]})
            t += step
        return out

    def live(self, limit: int = 100) -> tuple[int, dict]:
        db = self._db()
        rules = load_rules(self.rules_path)
        empty = {"subscribers": 0, "stopped_users": 0, "offers": 0, "delivered": 0, "queued": 0, "claimed": 0, "later": 0,
                 "stopped": 0, "no_answer": 0, "claim_rate": None, "stop_rate": None, "spent": 0, "budget": rules.budget,
                 "by_source": {}, "by_type": {}, "by_segment": [], "by_trigger": {}, "by_language": {}, "timeline": [], "recent": []}
        if db is None:
            return 200, empty
        with db:
            users = db.execute("SELECT COUNT(*), COALESCE(SUM(stopped), 0) FROM users WHERE lang IS NOT NULL").fetchone()
            langs = dict(Counter(r[0] for r in db.execute("SELECT lang FROM users WHERE lang IS NOT NULL")))
            rows = db.execute("SELECT * FROM offers ORDER BY id DESC").fetchall()
            decisions = self._decisions_by_offer(db)
        status = Counter(r["status"] for r in rows)
        delivered = sum(status[s] for s in DELIVERED)
        live_rows = [r for r in rows if r["status"] != "cancelled"]
        seg = defaultdict(Counter)
        for r in live_rows:
            s = self.shoppers.get(r["customer_id"], {}).get("seg")
            if s:
                seg[s]["offers"] += 1
                seg[s][r["status"]] += 1
        by_segment = [{"seg": s, "label": SEGMENTS[s]["label"], "offers": c["offers"], "claimed": c["claimed"],
                       "stopped": c["stopped"]} for s, c in sorted(seg.items(), key=lambda x: -x[1]["offers"])]
        recent = []
        for r in rows[:limit]:
            d = decisions.get(r["id"], {})
            recent.append({
                "id": r["id"], "at": r["created_at"], "sent_at": r["sent_at"], "shopper": self.shoppers.get(r["customer_id"], {}),
                "customer_id": r["customer_id"], "type": r["type"], "summary": r["summary"], "cost": r["cost"],
                "source": r["source"] or "rules", "status": r["status"], "trigger": r["trigger"], "reason": r["reason"],
                "text": r["text"], "code": r["code"], "checks": json.loads(r["checks"] or "[]"),
                "ai_attempts": d.get("ai_attempts") or [],
            })
        return 200, {
            "subscribers": users[0], "stopped_users": users[1], "offers": len(live_rows), "delivered": delivered,
            "queued": status["queued"], "claimed": status["claimed"], "later": status["later"], "stopped": status["stopped"],
            "no_answer": status["sent"],
            "claim_rate": status["claimed"] / delivered if delivered else None,
            "stop_rate": status["stopped"] / delivered if delivered else None,
            "spent": sum(r["cost"] for r in rows if r["status"] in COMMITTED), "budget": rules.budget,
            "by_source": dict(Counter(r["source"] or "rules" for r in live_rows)),
            "by_type": dict(Counter(r["type"] for r in live_rows)),
            "by_segment": by_segment,
            "by_trigger": dict(Counter(r["trigger"] for r in live_rows)),
            "by_language": langs,
            "timeline": self._timeline(sorted(live_rows, key=lambda r: r["created_at"])),
            "recent": recent,
        }

    def decisions(self, limit: int = 200) -> tuple[int, dict]:
        db = self._db()
        if db is None:
            return 200, {"decisions": []}
        with db:
            rows = db.execute("SELECT at, detail FROM events WHERE kind='decision' ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        out = []
        for e in rows:
            d = json.loads(e["detail"])
            out.append({"at": e["at"], "trigger": d.get("trigger"), "shopper": self.shoppers.get(d.get("customer"), {}),
                        "customer_id": d.get("customer"), "outcome": d.get("outcome"), "offer": d.get("offer"),
                        "offer_id": d.get("offer_id"), "source": d.get("source") or "rules", "reason": d.get("reason"),
                        "failed": d.get("failed") or [], "ai_attempts": d.get("ai_attempts") or []})
        return 200, {"decisions": out}

    def export_csv(self) -> bytes:
        """Every offer as a spreadsheet for the marketing team. Never includes chat ids."""
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(["offer_id", "created_at", "sent_at", "shopper", "segment", "city", "language", "offer_type", "offer",
                    "chosen_by", "status", "trigger", "cost_if_used_rs", "code"])
        db = self._db()
        if db is not None:
            with db:
                for r in db.execute("SELECT * FROM offers ORDER BY id"):
                    s = self.shoppers.get(r["customer_id"], {})
                    w.writerow([r["id"], r["created_at"], r["sent_at"] or "", s.get("name", ""), s.get("seg_label", ""),
                                s.get("city", ""), s.get("lang", ""), r["type"], r["summary"], r["source"] or "rules",
                                r["status"], r["trigger"], r["cost"], r["code"]])
        return ("﻿" + out.getvalue()).encode("utf-8")       # the BOM lets Excel read ₹ and Indian scripts


def make_handler(api: Api):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):                        # keep the bot's console readable
            pass

        def _send(self, code: int, body: bytes, content_type: str, headers: dict | None = None):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "same-origin")
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, data: dict):
            self._send(code, json.dumps(data, ensure_ascii=False, default=str).encode(), "application/json; charset=utf-8")

        def _redirect(self, where: str, cookie: str | None = None):
            self._send(303, b"", "text/plain", {"Location": where, **({"Set-Cookie": cookie} if cookie else {})})

        def _address(self) -> str:
            forwarded = self.headers.get("X-Forwarded-For", "")
            return forwarded.split(",")[0].strip() or self.client_address[0]

        def _cookie(self, value: str, max_age: int) -> str:
            secure = "; Secure" if api.public else ""
            return f"{COOKIE}={value}; Path=/; HttpOnly; SameSite=Lax; Max-Age={max_age}{secure}"

        def _allowed(self, page: bool) -> bool:
            """Answers the request itself (and returns False) when the caller may not see the console."""
            if api.locked:
                if page:
                    self._send(503, b"<h1>Locked</h1><p>Set PESHKASH_PAGE_PASSWORD on the server to open the marketer console.</p>",
                               "text/html; charset=utf-8")
                else:
                    self._json(503, {"problems": ["The marketer console is locked: set PESHKASH_PAGE_PASSWORD on the server."]})
                return False
            if not api.password or api.valid_session(self.headers.get("Cookie", "")):
                return True
            if page:
                self._redirect("/login")
            else:
                self._json(401, {"problems": ["Sign in first."], "signin": "/login"})
            return False

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/health":
                return self._json(200, {"ok": True})
            if url.path == "/login":
                if not api.password or api.locked:
                    return self._redirect("/")
                if api.valid_session(self.headers.get("Cookie", "")):
                    return self._redirect("/")
                return self._send(200, api.render_login(), "text/html; charset=utf-8")
            if url.path == "/logout":
                return self._redirect("/login", self._cookie("", 0))
            if not self._allowed(page=url.path in ("/", "/index.html")):
                return
            q = parse_qs(url.query)
            limit = int(q["limit"][0]) if q.get("limit", [""])[0].isdigit() else None
            if url.path in ("/", "/index.html"):
                self._send(200, api.page.read_bytes(), "text/html; charset=utf-8")
            elif url.path == "/api/status":
                self._json(200, api.info)
            elif url.path == "/api/rules":
                self._json(*api.get_rules())
            elif url.path == "/api/live":
                self._json(*api.live(**({"limit": limit} if limit else {})))
            elif url.path == "/api/decisions":
                self._json(*api.decisions(**({"limit": limit} if limit else {})))
            elif url.path == "/api/export.csv":
                self._send(200, api.export_csv(), "text/csv; charset=utf-8",
                           {"Content-Disposition": f'attachment; filename="peshkash-offers-{datetime.now():%Y-%m-%d}.csv"'})
            else:
                self._json(404, {"problems": ["Not found."]})

        def do_HEAD(self):                                   # some uptime monitors use HEAD
            self._send(200 if urlparse(self.path).path == "/health" else 404, b"", "text/plain")

        def do_POST(self):
            if urlparse(self.path).path != "/login" or not api.password or api.locked:
                return self._json(404, {"problems": ["Not found."]})
            address = self._address()
            if api.too_many_tries(address):
                return self._send(429, api.render_login("Too many tries. Please wait a few minutes and try again."),
                                  "text/html; charset=utf-8")
            size = min(int(self.headers.get("Content-Length") or 0), 4096)
            form = parse_qs(self.rfile.read(size).decode("utf-8", "replace"))
            if api.check_password(address, (form.get("password") or [""])[0]):
                return self._redirect("/", self._cookie(api.session_token(), SESSION_DAYS * 86400))
            self._send(401, api.render_login("That password isn't right. Please try again."), "text/html; charset=utf-8")

        def do_PUT(self):
            if not self._allowed(page=False):
                return
            if urlparse(self.path).path != "/api/rules":
                return self._json(404, {"problems": ["Not found."]})
            size = int(self.headers.get("Content-Length") or 0)
            if size > 100_000:
                return self._json(413, {"problems": ["Too much data."]})
            try:
                body = json.loads(self.rfile.read(size) or b"null")
            except json.JSONDecodeError:
                return self._json(400, {"problems": ["The rules could not be read."]})
            self._json(*api.put_rules(body))

    return Handler


def serve(api: Api, port: int = 8010, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    """Start the console in a background thread and return the server (call .shutdown() to stop it)."""
    server = ThreadingHTTPServer((host, port), make_handler(api))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
