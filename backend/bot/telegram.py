"""A very small Telegram Bot API client (standard library only)."""
import http.client
import json
import socket

Buttons = list[list[tuple[str, str]]]          # rows of (label, callback data)


class TelegramError(RuntimeError):
    pass


def keyboard(buttons: Buttons | None) -> dict | None:
    if not buttons:
        return None
    return {"inline_keyboard": [[{"text": label, "callback_data": data} for label, data in row] for row in buttons]}


def menu_keyboard(rows: list[list[str]]) -> dict:
    """A menu that stays under the chat; tapping a button sends its text as a message."""
    return {"keyboard": [[{"text": label} for label in row] for row in rows], "resize_keyboard": True, "is_persistent": True}


class _IPv4HTTPSConnection(http.client.HTTPSConnection):
    """Connects over IPv4 only. Many home and college networks advertise IPv6 but can't route it, and trying it
    first costs about 20 seconds on every request."""

    def connect(self):
        addr = socket.getaddrinfo(self.host, self.port, socket.AF_INET, socket.SOCK_STREAM)[0][4]
        sock = socket.create_connection(addr, self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


class TelegramAPI:
    HOST = "api.telegram.org"

    def __init__(self, token: str, timeout: int = 40):
        self.path = f"/bot{token}/"
        self.timeout = timeout
        self.conn: http.client.HTTPSConnection | None = None

    def _post(self, method: str, body: bytes) -> dict:
        if self.conn is None:                                # one kept-alive connection for every request
            self.conn = _IPv4HTTPSConnection(self.HOST, 443, timeout=self.timeout)
        self.conn.request("POST", self.path + method, body, {"Content-Type": "application/json"})
        return json.loads(self.conn.getresponse().read() or b"{}")

    def call(self, method: str, **params):
        body = json.dumps({k: v for k, v in params.items() if v is not None}).encode()
        try:
            data = self._post(method, body)
        except (http.client.HTTPException, OSError):
            if self.conn:
                self.conn.close()
            self.conn = None
            data = self._post(method, body)                  # once more on a fresh connection
        if not data.get("ok"):
            # Never include the URL: it contains the bot token.
            raise TelegramError(f"{method} failed: {data.get('description', 'no reply')}")
        return data["result"]

    def get_me(self):
        return self.call("getMe")

    def get_updates(self, offset: int | None, timeout: int = 25):
        return self.call("getUpdates", offset=offset, timeout=timeout, allowed_updates=["message", "callback_query"])

    def send_message(self, chat_id: int, text: str, buttons: Buttons | None = None, menu: list[list[str]] | None = None) -> int:
        """`buttons` go under this message; `menu` (used when there are no buttons) replaces the menu under the chat."""
        markup = keyboard(buttons) or (menu_keyboard(menu) if menu else None)
        msg = self.call("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=markup,
                        link_preview_options={"is_disabled": True})
        return msg["message_id"]

    def send_typing(self, chat_id: int):
        try:
            self.call("sendChatAction", chat_id=chat_id, action="typing")
        except TelegramError:
            pass

    def answer_callback(self, callback_id: str, text: str | None = None):
        """Only stops the button's loading spinner, so it never blocks the real work (old taps can't be answered)."""
        try:
            return self.call("answerCallbackQuery", callback_query_id=callback_id, text=text)
        except TelegramError:
            return None

    def remove_buttons(self, chat_id: int, message_id: int):
        try:
            return self.call("editMessageReplyMarkup", chat_id=chat_id, message_id=message_id, reply_markup={"inline_keyboard": []})
        except TelegramError:                                # already removed, or message too old to edit
            return None

    def set_commands(self, commands: list[tuple[str, str]]):
        return self.call("setMyCommands", commands=[{"command": c, "description": d} for c, d in commands])

    def set_descriptions(self, description: str, short: str, language_code: str | None = None):
        """What people see on the bot's page before pressing Start (language_code None = everyone else)."""
        self.call("setMyDescription", description=description, language_code=language_code)
        self.call("setMyShortDescription", short_description=short, language_code=language_code)
