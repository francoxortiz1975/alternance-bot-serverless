"""Récupération du texte d'une page web via Jina Reader (https://r.jina.ai),
avec fallback Firecrawl pour les SPA JavaScript."""

import os

import requests

JINA_READER_URL = "https://r.jina.ai/"


def _fetch_via_jina(url, timeout):
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
    return texte_propre if len(texte_propre) > 300 else None


def fetch_texto_pagina(url, timeout=30):
    """Récupère le texte d'une page web. Essaie Jina Reader d'abord,
    puis Firecrawl en fallback si Jina renvoie du contenu vide (SPA JS)."""
    texte = _fetch_via_jina(url, timeout)
    if texte:
        return texte

    from lib import firecrawl_client
    return firecrawl_client.fetch_texto_pagina(url, timeout)
