"""Récupération du texte d'une page web via Jina Reader (https://r.jina.ai)."""

import os

import requests

JINA_READER_URL = "https://r.jina.ai/"


def fetch_texto_pagina(url, timeout=30):
    """Récupère le texte propre d'une page web via Jina Reader.

    Retourne le texte (str) ou None en cas d'échec.
    """
    headers = {}
    jina_key = os.environ.get("JINA_API_KEY")
    if jina_key:
        headers["Authorization"] = f"Bearer {jina_key}"

    try:
        resp = requests.get(f"{JINA_READER_URL}{url}", headers=headers, timeout=timeout)
        resp.raise_for_status()
        texte = resp.text
    except requests.RequestException:
        return None

    lignes = [l.strip() for l in texte.splitlines() if l.strip()]
    texte_propre = "\n".join(lignes)
    if len(texte_propre) > 300:
        return texte_propre
    return None
