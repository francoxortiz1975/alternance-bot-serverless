"""Envoi de messages et documents via l'API HTTP de Telegram (sans librairie)."""

import os

import requests

TELEGRAM_API_URL = "https://api.telegram.org"


def _base_url():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    return f"{TELEGRAM_API_URL}/bot{token}"


def send_message(chat_id, text, parse_mode="Markdown"):
    resp = requests.post(
        f"{_base_url()}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
        timeout=15,
    )
    if not resp.ok:
        # Retry sans parse_mode si le Markdown casse le rendu
        resp = requests.post(
            f"{_base_url()}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=15,
        )
    resp.raise_for_status()
    return resp.json()


def send_document(chat_id, file_bytes, filename, caption=None):
    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption
    resp = requests.post(
        f"{_base_url()}/sendDocument",
        data=data,
        files={"document": (filename, file_bytes)},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
