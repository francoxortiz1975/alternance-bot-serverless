"""Entrypoint du cron GitHub Actions : scrape les pages carrières via filtres de mots-clés.

Aucun appel Gemini ici — on stocke juste titre/localisation/lien + le texte brut
de l'offre. L'analyse Gemini (compatibilité, score, lettre) se fait plus tard,
à la demande, quand Franco sélectionne une offre depuis le bot.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import jina_client, supabase_client
from scripts.keyword_filter import extraer_enlaces_filtrados, extraer_localizacion


def main():
    sources = supabase_client.get_active_sources()
    print(f"📚 {len(sources)} source(s) active(s)")

    for source in sources:
        print(f"\n🌐 Scraping {source['name']} ({source['url']})")

        texto_listing = jina_client.fetch_texto_pagina(source["url"])
        if not texto_listing:
            print("   ⚠️  Impossible de lire la page de listing, skip.")
            continue

        ofertas = extraer_enlaces_filtrados(texto_listing, source["url"])
        print(f"   🔎 {len(ofertas)} lien(s) correspondant aux mots-clés")

        for oferta in ofertas:
            offer_url = oferta["url"]

            if supabase_client.get_offer_by_url(offer_url):
                continue

            print(f"   ➡️  Nouveau : {oferta['titulo']} ({offer_url})")

            texto_detalle = jina_client.fetch_texto_pagina(offer_url)
            if not texto_detalle:
                print("      ⚠️  Page de détail illisible, skip.")
                continue

            localisation = extraer_localizacion(texto_detalle)

            supabase_client.upsert_offer(
                offer_url,
                source_id=source["id"],
                title=oferta["titulo"],
                location=localisation,
                raw_text=texto_detalle,
                status="new",
            )
            print(f"      ✅ Sauvegardé — {localisation or 'localisation inconnue'}")

        supabase_client.update_source_last_scraped(source["id"], datetime.now(timezone.utc).isoformat())

    print("\n✅ Scraping terminé.")


if __name__ == "__main__":
    main()
