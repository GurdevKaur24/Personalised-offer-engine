"""A very small Telegram Bot API client (standard library only)."""
import json
import urllib.error
import urllib.request

Buttons = list[list[tuple[str, str]]]          # rows of (label, callback data)


class TelegramError(RuntimeError):
    pass


def keyboard(buttons: Buttons | None) -> dict | None:
    if not buttons:
        return None
    return {"inline_keyboard": [[{"text": label, "callback_data": data} for label, data in row] for row in buttons]}


class TelegramAPI:
    def __init__(self, token: str, timeout: int = 40):
        self.base = f"https://api.telegram.org/bot{token}/"
        self.timeout = timeout

    def call(self, method: str, **params):
        body = json.dumps({k: v for k, v in params.items() if v is not None}).encode()
        req = urllib.request.Request(self.base + method, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            data = json.loads(e.read() or b"{}")
        if not data.get("ok"):
            # Never include the URL: it contains the bot token.
            raise TelegramError(f"{method} failed: {data.get('description', 'no reply')}")
        return data["result"]

    def get_me(self):
        return self.call("getMe")

    def get_updates(self, offset: int | None, timeout: int = 25):
        return self.call("getUpdates", offset=offset, timeout=timeout, allowed_updates=["message", "callback_query"])

    def send_message(self, chat_id: int, text: str, buttons: Buttons | None = None) -> int:
        msg = self.call("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=keyboard(buttons),
                        link_preview_options={"is_disabled": True})
        return msg["message_id"]

    def answer_callback(self, callback_id: str, text: str | None = None):
        return self.call("answerCallbackQuery", callback_query_id=callback_id, text=text)

    def remove_buttons(self, chat_id: int, message_id: int):
        return self.call("editMessageReplyMarkup", chat_id=chat_id, message_id=message_id, reply_markup={"inline_keyboard": []})

    def set_commands(self, commands: list[tuple[str, str]]):
        return self.call("setMyCommands", commands=[{"command": c, "description": d} for c, d in commands])
