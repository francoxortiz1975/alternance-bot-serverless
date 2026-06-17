"""Entrypoint du cron GitHub Actions : scrape les pages carrières (Jina + mots-clés)
et interroge l'API "La bonne alternance" (recherches géo/ROME configurées).

Aucun appel Gemini ici — on stocke juste titre/localisation/lien + le texte brut
de l'offre. L'analyse Gemini (compatibilité, score, lettre) se fait plus tard,
à la demande, quand Franco sélectionne une offre depuis le bot.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import api_alternance_client, jina_client, supabase_client, telegram_client
from scripts.keyword_filter import es_oferta_excluida, extraer_enlaces_filtrados, extraer_localizacion


def scrape_sources():
    sources = supabase_client.get_active_sources()
    print(f"📚 {len(sources)} source(s) active(s)")
    nuevas = 0

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

            if es_oferta_excluida(oferta["titulo"]):
                print(f"   🚫 Exclu : {oferta['titulo']}")
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
            nuevas += 1
            print(f"      ✅ Sauvegardé — {localisation or 'localisation inconnue'}")

        supabase_client.update_source_last_scraped(source["id"], datetime.now(timezone.utc).isoformat())

    return nuevas


def scrape_api_searches():
    searches = supabase_client.get_active_api_searches()
    print(f"\n🔌 {len(searches)} recherche(s) API Alternance active(s)")
    nuevas = 0

    for search in searches:
        print(f"\n🔌 {search['name']}")

        try:
            jobs = api_alternance_client.search_offers(
                romes=search.get("romes"),
                latitude=search.get("latitude"),
                longitude=search.get("longitude"),
                radius=search.get("radius") or 30,
                target_diploma_level=search.get("target_diploma_level"),
            )
        except Exception as e:
            print(f"   ⚠️  Erreur API : {e}")
            continue

        print(f"   🔎 {len(jobs)} offre(s) trouvée(s)")

        for job in jobs:
            offer_url = job.get("apply", {}).get("url")
            if not offer_url or supabase_client.get_offer_by_url(offer_url):
                continue

            title = job.get("offer", {}).get("title")
            workplace = job.get("workplace", {})
            employeur = workplace.get("name") or workplace.get("brand") or workplace.get("legal_name")
            location = workplace.get("location", {}).get("address")

            if es_oferta_excluida(title, employeur):
                print(f"   🚫 Exclu : {title} — {employeur}")
                continue

            print(f"   ➡️  Nouveau : {title} ({offer_url})")

            supabase_client.upsert_offer(
                offer_url,
                title=title,
                location=location,
                raw_text=api_alternance_client.job_to_text(job),
                status="new",
            )
            nuevas += 1
            print(f"      ✅ Sauvegardé — {location or 'localisation inconnue'}")

        supabase_client.update_api_search_last_scraped(search["id"], datetime.now(timezone.utc).isoformat())

    return nuevas


def _build_telegram_message(nuevas_sources, nuevas_api):
    total_nuevas = nuevas_sources + nuevas_api
    offers = supabase_client.get_top_offers(15)

    lines = []
    if total_nuevas > 0:
        lines.append(f"🆕 *{total_nuevas} nueva(s) oferta(s)* encontrada(s) hoy")
    else:
        lines.append("📋 Sin nuevas ofertas hoy — aquí el top actual:")
    lines.append("")

    for i, offer in enumerate(offers, start=1):
        lines.append(f"{i}. *{offer.get('title') or '?'}*")
        if offer.get("location"):
            lines.append(f"   📍 {offer['location']}")
        lines.append(f"   🔗 {offer['offer_url']}")
        lines.append("")

    lines.append("_Escribe al bot para analizar cualquier oferta._")
    return "\n".join(lines)


def notify_telegram(nuevas_sources, nuevas_api):
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not chat_id:
        print("⚠️  TELEGRAM_CHAT_ID no configurado, skip notificación.")
        return
    try:
        msg = _build_telegram_message(nuevas_sources, nuevas_api)
        telegram_client.send_message(chat_id, msg)
        print("📨 Notificación Telegram enviada.")
    except Exception as e:
        print(f"⚠️  Error al enviar Telegram: {e}")


def main():
    nuevas_sources = scrape_sources()
    nuevas_api = scrape_api_searches()
    print("\n✅ Scraping terminé.")
    notify_telegram(nuevas_sources, nuevas_api)


if __name__ == "__main__":
    main()
