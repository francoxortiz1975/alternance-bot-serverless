"""Test de URLs SPA del Grupo B/C — 3 modos Firecrawl en secuencia.

Ejecuta: FIRECRAWL_API_KEY=xxx python scripts/test_fuentes_spa.py
O bien via GitHub Actions (workflow test_fuentes.yml).

Modos probados por URL:
  1. scrape  → markdown + extracción de links con keyword_filter
  2. map     → lista de URLs del dominio, filtra las que parecen ofertas
  3. extract → LLM extrae ofertas estructuradas directamente
"""

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import firecrawl_client
from scripts.keyword_filter import es_oferta_excluida, extraer_enlaces_filtrados, extraer_localizacion

PARIS_KEYWORDS = [
    "paris", "île-de-france", "idf", "nanterre", "boulogne", "la défense",
    "défense", "levallois", "issy", "courbevoie", "neuilly", "montreuil",
    "vincennes", "saint-denis", "clichy", "puteaux",
]

ROLE_KEYWORDS_RE = re.compile(
    r"data|engineer|ingénieur|développeur|developer|devops|software|"
    r"informatique|digital|tech|ia\b|intelligence artificielle|"
    r"alternance|apprentissage",
    re.IGNORECASE,
)

OFFER_URL_RE = re.compile(
    r"/job|/offre|/poste|/position|/career|/emploi|/apply|\d{5,}",
    re.IGNORECASE,
)

URLS = [
    # Grupo B — SPA que fallaban con Jina
    ("Société Générale",    "https://careers.societegenerale.com/fr/offres?contract=apprentissage&location=paris"),
    ("Crédit Agricole CIB", "https://careers.ca-cib.com/fr/offres"),
    ("BPCE",                "https://carrieres.bpce.fr/offres"),
    ("Amundi",              "https://jobs.amundi.com/go/Toutes-les-offres/"),
    ("La Banque Postale",   "https://carrieres.labanquepostale.fr/offres"),
    ("Decathlon Tech",      "https://www.decathlon.fr/landing/_/R-a-recrutement"),
    ("ManoMano",            "https://jobs.lever.co/manomano"),
    ("L'Oréal Tech",        "https://careers.loreal.com/fr_FR/jobs/SearchJobs/"),
    ("EDF Alternance",      "https://edf.csod.com/ux/ats/careersite/1/home?c=edf"),
    ("Air France",          "https://careers.airfranceklm.com/fr_FR/jobs?type=apprentissage"),
    # Grupo C — no probadas aún
    ("IBM France",          "https://www.ibm.com/fr-fr/employment/"),
    ("Salesforce France",   "https://careers.salesforce.com/en/jobs/?country=France"),
    ("SAP Alternance",      "https://jobs.sap.com/go/Alternance-France/"),
    ("ServiceNow France",   "https://careers.servicenow.com/careers/jobs?location=France"),
    ("Oracle France",       "https://careers.oracle.com/jobs/#en/sites/jobsearch/jobs?location=France"),
]


def es_paris(texto):
    t = texto.lower()
    return any(kw in t for kw in PARIS_KEYWORDS)


# ── Modo 1: scrape ────────────────────────────────────────────────────────────

def test_scrape(url):
    md = firecrawl_client.fetch_texto_pagina(url, timeout=40)
    if not md:
        return None, []
    links = extraer_enlaces_filtrados(md, url)
    links = [l for l in links if not es_oferta_excluida(l["titulo"])]
    links_paris = [
        l for l in links
        if extraer_localizacion(l["titulo"]) or es_paris(md[:3000])
    ]
    return len(md), links_paris


# ── Modo 2: map ───────────────────────────────────────────────────────────────

def test_map(url):
    all_urls = firecrawl_client.map_urls(url, timeout=30, limit=300)
    offer_urls = [
        u for u in all_urls
        if OFFER_URL_RE.search(u) and ROLE_KEYWORDS_RE.search(u)
    ]
    return all_urls, offer_urls


# ── Modo 3: extract ───────────────────────────────────────────────────────────

def test_extract(url):
    offers = firecrawl_client.extract_offers(url, timeout=60)
    return [
        o for o in offers
        if not es_oferta_excluida(o.get("title", ""))
        and ROLE_KEYWORDS_RE.search(o.get("title", ""))
    ]


# ── Runner principal ──────────────────────────────────────────────────────────

def main():
    print("\n" + "═" * 100)
    print(f"{'Empresa':<25} {'SCRAPE':^18} {'MAP':^18} {'EXTRACT':^18}  Mejor resultado")
    print("─" * 100)

    viables = []

    for name, url in URLS:
        cols = {}

        # — Modo 1: scrape
        try:
            chars, links_s = test_scrape(url)
            cols["scrape"] = f"{len(links_s)} links" if chars else "vacío"
            scrape_links = links_s
        except Exception as e:
            cols["scrape"] = f"ERR"
            scrape_links = []
        time.sleep(1)

        # — Modo 2: map
        try:
            all_urls, offer_urls = test_map(url)
            cols["map"] = f"{len(offer_urls)}/{len(all_urls)} URLs"
        except Exception as e:
            cols["map"] = "ERR"
            offer_urls = []
        time.sleep(1)

        # — Modo 3: extract (solo si scrape vacío o sin links)
        if not scrape_links:
            try:
                extracted = test_extract(url)
                cols["extract"] = f"{len(extracted)} ofertas"
            except Exception as e:
                cols["extract"] = "ERR"
                extracted = []
        else:
            cols["extract"] = "—"
            extracted = []
        time.sleep(1)

        # Determinar mejor resultado
        mejor = scrape_links or extracted or [{"titulo": u, "url": u} for u in offer_urls[:3]]
        muestra = mejor[0].get("titulo", mejor[0].get("url", "?"))[:45] if mejor else "(sin resultados)"

        status = "✅" if mejor else "❌"
        print(
            f"{status} {name:<23} "
            f"{cols.get('scrape','─'):^18} "
            f"{cols.get('map','─'):^18} "
            f"{cols.get('extract','─'):^18}  {muestra}"
        )

        if mejor:
            viables.append((name, url, mejor, cols))

    print("\n\n═══ RESUMEN VIABLES ═══\n")
    for name, url, ofertas, cols in viables:
        modo = ("scrape" if cols.get("scrape","").endswith("links") and "0" not in cols["scrape"]
                else "extract" if cols.get("extract","").startswith(tuple("123456789"))
                else "map")
        print(f"  ✅ {name} [{modo}]: {url}")
        for o in ofertas[:3]:
            titulo = o.get("titulo") or o.get("title") or o.get("url", "?")
            print(f"     → {titulo[:70]}")
        print()

    if not viables:
        print("  Ninguna URL viable con los 3 modos.")


if __name__ == "__main__":
    main()
