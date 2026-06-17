"""Test de URLs SPA del Grupo B/C via Firecrawl.

Ejecuta: FIRECRAWL_API_KEY=xxx python scripts/test_fuentes_spa.py
O bien via GitHub Actions (workflow test_fuentes.yml).
"""

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


def test_url(name, url):
    md = firecrawl_client.fetch_texto_pagina(url, timeout=40)
    if not md:
        return {"status": "vacio", "chars": 0, "links": []}

    links = extraer_enlaces_filtrados(md, url)
    links = [l for l in links if not es_oferta_excluida(l["titulo"])]

    # Filtrar por Paris si hay localización en el texto de la página
    links_paris = []
    for l in links:
        loc = extraer_localizacion(l["titulo"])
        if loc or es_paris(md[:3000]):
            links_paris.append(l)

    return {"status": "ok", "chars": len(md), "links": links, "links_paris": links_paris}


def main():
    print(f"\n{'Empresa':<25} {'Chars':>7} {'Links':>5} {'Paris':>5}  Estado / Muestra")
    print("─" * 90)

    resultados_ok = []

    for name, url in URLS:
        try:
            r = test_url(name, url)
            if r["status"] == "vacio":
                print(f"❌ {name:<23} {'0':>7} {'─':>5} {'─':>5}  vacío con Firecrawl")
            else:
                links_paris = r.get("links_paris", r["links"])
                muestra = links_paris[0]["titulo"][:40] if links_paris else "(sin keywords de rol)"
                print(f"✅ {name:<23} {r['chars']:>7} {len(r['links']):>5} {len(links_paris):>5}  {muestra}")
                if links_paris:
                    resultados_ok.append((name, url, links_paris))
        except Exception as e:
            print(f"💥 {name:<23}       -     -     -  ERROR: {e}")

        time.sleep(1.5)

    print("\n\n═══ URLs VIABLES (tienen links con keywords, agregar a Supabase) ═══\n")
    for name, url, links in resultados_ok:
        print(f"  {name}: {url}")
        for l in links[:3]:
            print(f"    → {l['titulo']}")
        print()


if __name__ == "__main__":
    main()
