"""Envoi de messages et documents via l'API HTTP de Telegram (sans librairie)."""

import os

import requests

TELEGRAM_API_URL = "https://api.telegram.org"
MAX_MESSAGE_LENGTH = 4096


def _base_url():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    return f"{TELEGRAM_API_URL}/bot{token}"


def _post(endpoint, **kwargs):
    resp = requests.post(f"{_base_url()}/{endpoint}", **kwargs)
    if not resp.ok:
        try:
            description = resp.json().get("description", resp.text)
        except ValueError:
            description = resp.text
        raise requests.HTTPError(f"{resp.status_code} {description}", response=resp)
    return resp.json()


def _split_message(text, limit=MAX_MESSAGE_LENGTH):
    if len(text) <= limit:
        return [text]

    chunks = []
    current_lines = []
    current_len = 0

    for line in text.split("\n"):
        while len(line) > limit:
            if current_lines:
                chunks.append("\n".join(current_lines))
                current_lines = []
                current_len = 0
            chunks.append(line[:limit])
            line = line[limit:]

        added_len = len(line) + (1 if current_lines else 0)
        if current_lines and current_len + added_len > limit:
            chunks.append("\n".join(current_lines))
            current_lines = []
            current_len = 0
            added_len = len(line)

        current_lines.append(line)
        current_len += added_len

    if current_lines:
        chunks.append("\n".join(current_lines))

    return chunks


def _send_chunk(chat_id, text, parse_mode):
    try:
        return _post("sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode}, timeout=15)
    except requests.HTTPError:
        # Retry sans parse_mode si le Markdown casse le rendu
        return _post("sendMessage", json={"chat_id": chat_id, "text": text}, timeout=15)


def send_message(chat_id, text, parse_mode="Markdown"):
    result = None
    for chunk in _split_message(text):
        result = _send_chunk(chat_id, chunk, parse_mode)
    return result


def send_document(chat_id, file_bytes, filename, caption=None):
    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption
    return _post(
        "sendDocument",
        data=data,
        files={"document": (filename, file_bytes)},
        timeout=30,
    )
