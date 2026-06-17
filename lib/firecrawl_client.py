"""Récupération de pages web via Firecrawl (headless Chrome).

Trois modes disponibles :
  - scrape  : page unique → markdown (mode actuel, fallback Jina)
  - map     : liste toutes les URLs d'un domaine (1 crédit)
  - extract : extrait des données structurées via LLM (~5 crédits)
"""

import os

import requests

_BASE = "https://api.firecrawl.dev/v1"

_EXTRACT_PROMPT = (
    "Extract all job offers listed on this career page. "
    "For each offer return: title (job title in French or English), "
    "url (direct link to the offer, absolute URL), "
    "location (city or region, empty string if not found). "
    "Only include apprenticeship / alternance / internship positions. "
    "Return an empty list if no offers are found."
)

_EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "offers": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title":    {"type": "string"},
                    "url":      {"type": "string"},
                    "location": {"type": "string"},
                },
                "required": ["title", "url"],
            },
        }
    },
    "required": ["offers"],
}


def _api_key():
    return os.environ.get("FIRECRAWL_API_KEY")


def fetch_texto_pagina(url, timeout=30):
    """Scrape (mode 1) → markdown. Utilisé comme fallback de Jina."""
    api_key = _api_key()
    if not api_key:
        return None

    try:
        resp = requests.post(
            f"{_BASE}/scrape",
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


def map_urls(url, timeout=30, limit=200):
    """Mode map : retourne la liste des URLs trouvées sur le domaine (1 crédit).

    Utile pour repérer des URLs d'offres individuelles sans parser le markdown.
    """
    api_key = _api_key()
    if not api_key:
        return []

    try:
        resp = requests.post(
            f"{_BASE}/map",
            json={"url": url, "limit": limit},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("links") or []
    except requests.RequestException:
        return []


def extract_offers(url, timeout=60):
    """Mode extract : LLM extrait les offres structurées depuis la page rendue (~5 crédits).

    Retourne une liste de dicts {title, url, location}.
    """
    api_key = _api_key()
    if not api_key:
        return []

    try:
        resp = requests.post(
            f"{_BASE}/scrape",
            json={
                "url": url,
                "formats": ["extract"],
                "extract": {
                    "prompt": _EXTRACT_PROMPT,
                    "schema": _EXTRACT_SCHEMA,
                },
            },
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )
        resp.raise_for_status()
        extracted = resp.json().get("data", {}).get("extract") or {}
        return extracted.get("offers") or []
    except requests.RequestException:
        return []
