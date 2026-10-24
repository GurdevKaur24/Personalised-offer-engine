"""Marketer page server.

GET  /                 the app page (prototype/index.html), which switches to live mode when /api/status answers
GET  /api/status       bot, AI model and data size
GET  /api/rules        the rules the bot uses now
PUT  /api/rules        save new rules (refused with plain-English problems if any value is out of range)
GET  /api/live         live results: classmates, offers, claims, stops, budget, and the latest offers
GET  /api/decisions    the decision log: every time the engine decided, including when nothing was sent

Only listens on this computer (127.0.0.1). Classmates are shown only as the synthetic shopper they play.
"""
import json
import sqlite3
import threading
from collections import Counter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from peshkash.features import SEGMENTS
from peshkash.rules import LIMITS, OFFER_TYPES, Rules, RulesError, load_rules, save_rules

DELIVERED = ("sent", "claimed", "later", "stopped")
COMMITTED = ("queued", "sent", "claimed", "later")


class Api:
    def __init__(self, data_dir: Path, page: Path, customers: list[dict], status: dict | None = None):
        self.data_dir, self.page = Path(data_dir), Path(page)
        self.rules_path = self.data_dir / "rules.json"
        self.db_path = self.data_dir / "live.db"
        self.shoppers = {c["id"]: {"name": c["name"], "seg": c["seg"], "seg_label": SEGMENTS[c["seg"]]["label"],
                                   "city": c["city"], "lang": c["lang"]} for c in customers}
        self.info = {"live": True, "customers": len(customers), "bot": None, "ai_model": None, **(status or {})}

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

    def live(self, limit: int = 100) -> tuple[int, dict]:
        db = self._db()
        rules = load_rules(self.rules_path)
        empty = {"classmates": 0, "stopped_users": 0, "offers": 0, "delivered": 0, "queued": 0, "claimed": 0, "later": 0,
                 "stopped": 0, "no_answer": 0, "claim_rate": None, "stop_rate": None, "spent": 0, "budget": rules.budget,
                 "by_source": {}, "by_type": {}, "recent": []}
        if db is None:
            return 200, empty
        with db:
            users = db.execute("SELECT COUNT(*), COALESCE(SUM(stopped), 0) FROM users WHERE lang IS NOT NULL").fetchone()
            rows = db.execute("SELECT * FROM offers ORDER BY id DESC").fetchall()
            decisions = self._decisions_by_offer(db)
        status = Counter(r["status"] for r in rows)
        delivered = sum(status[s] for s in DELIVERED)
        live_rows = [r for r in rows if r["status"] != "cancelled"]
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
            "classmates": users[0], "stopped_users": users[1], "offers": len(live_rows), "delivered": delivered,
            "queued": status["queued"], "claimed": status["claimed"], "later": status["later"], "stopped": status["stopped"],
            "no_answer": status["sent"],
            "claim_rate": status["claimed"] / delivered if delivered else None,
            "stop_rate": status["stopped"] / delivered if delivered else None,
            "spent": sum(r["cost"] for r in rows if r["status"] in COMMITTED), "budget": rules.budget,
            "by_source": dict(Counter(r["source"] or "rules" for r in live_rows)),
            "by_type": dict(Counter(r["type"] for r in live_rows)),
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


def make_handler(api: Api):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):                        # keep the bot's console readable
            pass

        def _json(self, code: int, data: dict):
            body = json.dumps(data, ensure_ascii=False, default=str).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlparse(self.path)
            q = parse_qs(url.query)
            limit = int(q["limit"][0]) if q.get("limit", [""])[0].isdigit() else None
            if url.path in ("/", "/index.html"):
                body = api.page.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif url.path == "/api/status":
                self._json(200, api.info)
            elif url.path == "/api/rules":
                self._json(*api.get_rules())
            elif url.path == "/api/live":
                self._json(*api.live(**({"limit": limit} if limit else {})))
            elif url.path == "/api/decisions":
                self._json(*api.decisions(**({"limit": limit} if limit else {})))
            else:
                self._json(404, {"problems": ["Not found."]})

        def do_PUT(self):
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
    """Start the page in a background thread and return the server (call .shutdown() to stop it)."""
    server = ThreadingHTTPServer((host, port), make_handler(api))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server
