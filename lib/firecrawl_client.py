"""Récupération du texte d'une page web via Firecrawl (rend les SPA JavaScript)."""

import os

import requests

FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1/scrape"


def fetch_texto_pagina(url, timeout=30):
    """Scrape via Firecrawl (headless Chrome). Retourne le texte ou None."""
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        return None

    try:
        resp = requests.post(
            FIRECRAWL_API_URL,
            json={"url": url, "formats": ["markdown"]},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )
        resp.raise_for_status()
        texte = resp.json().get("data", {}).get("markdown") or ""
    except requests.RequestException:
        return None

    lignes = [l.strip() for l in texte.splitlines() if l.strip()]
    texte_propre = "\n".join(lignes)
    return texte_propre if len(texte_propre) > 300 else None
