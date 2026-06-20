"""Webhook Telegram (Vercel serverless function, sans framework)."""

import hashlib
import json
import os
import re
import sys
import traceback
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from lib import docx_gen, gemini_client, jina_client, pdf_convert, supabase_client, telegram_client
from lib.scoring import CV_MAP, POIDS, calcular_score_global

gemini_client.configure_api_key(os.environ["GEMINI_API_KEY"])

ASSETS_CVS = Path(__file__).parent.parent / "assets" / "cvs"

GREETINGS = {"hola", "hello", "hi", "/start", "/top"}
CONFIRM_YES = {"s", "si", "sí", "o", "oui", "yes", "y"}
CONFIRM_NO = {"n", "no", "non"}
URL_RE = re.compile(r"https?://\S+")

# ── Détection de durée incompatible avant d'appeler Gemini ───────────────────

# Contexte suivi de X mois
_DUREE_MOIS_RE = re.compile(
    r"(?:"
    r"dur[ée]e\s*(?:du\s+contrat\s*)?:?\s*(?:de\s+)?"
    r"|contrat\s+(?:d[e']\s*)?(?:apprentissage\s+|alternance\s+)?(?:de\s+)?"
    r"|alternance\s+(?:de\s+)?"
    r"|apprentissage\s+(?:de\s+)?"
    r"|(?:pour|sur|pendant)\s+(?:une\s+dur[ée]e\s+de\s+)?"
    r")"
    r"(\d+)\s*mois",
    re.IGNORECASE,
)

# X mois d'alternance / d'apprentissage (durée en suffixe)
_DUREE_MOIS_SUFFIX_RE = re.compile(
    r"(\d+)\s*mois\s+d[e']\s*(?:alternance|apprentissage|contrat)",
    re.IGNORECASE,
)

# Contexte suivi de X an / un an → converti en mois
_DUREE_AN_RE = re.compile(
    r"(?:"
    r"dur[ée]e\s*(?:du\s+contrat\s*)?:?\s*(?:de\s+)?"
    r"|contrat\s+(?:d[e']\s*)?(?:apprentissage\s+|alternance\s+)?(?:de\s+)?"
    r"|alternance\s+(?:d[e']\s*)?"
    r"|apprentissage\s+(?:d[e']\s*)?"
    r"|(?:pour|sur|pendant)\s+(?:une\s+dur[ée]e\s+de\s+)?"
    r")"
    r"(un|une|1|2)\s*an(?:née)?s?",
    re.IGNORECASE,
)


def _duree_incompatible(raw_text):
    """Retourne le nombre de mois si durée < 24 détectée dans raw_text, sinon None."""
    raw = raw_text or ""

    for pat in (_DUREE_MOIS_RE, _DUREE_MOIS_SUFFIX_RE):
        m = pat.search(raw)
        if m:
            mois = int(m.group(1))
            if mois < 24:
                return mois

    m = _DUREE_AN_RE.search(raw)
    if m:
        val = m.group(1).lower()
        mois = 12 if val in ("un", "une", "1") else 24
        if mois < 24:
            return mois

    return None


# ─── Formatage (migré de bot_telegram.py) ────────────────────────────────────

def score_emoji(score):
    if score >= 80:
        return "✅"
    if score >= 55:
        return "🟡"
    return "🔴"


def formater_analyse(infos):
    L = []

    duree = infos.get("duree_mois", "?")
    duree_ok = duree == 24
    salaire = infos.get("salaire", "Non précisé")
    flag = "✅" if duree_ok else "⚠️"

    L.append(f"📌 *{infos.get('entreprise_nom', '?')}*")
    dept = infos.get("equipe_departement", "")
    if dept:
        L.append(f"   {dept}")
    L.append(f"   {flag} {duree} mois  |  {salaire}")
    L.append("")

    loc = infos.get("localisation", "?")
    dist = infos.get("distance_dauphine", "?")
    L.append(f"📍 {loc}")
    L.append(f"   {dist}")
    L.append("")

    taches = infos.get("taches", [])
    if taches:
        L.append("📋 *Tareas:*")
        for t in taches:
            L.append(f"• {t}")
        L.append("")

    techs = infos.get("technologies", [])
    if techs:
        L.append(f"🛠 {', '.join(techs)}")
        L.append("")

    jour = infos.get("jour_type", "")
    if jour:
        L.append(f"🗓 {jour}")
        L.append("")

    avantages = infos.get("avantages", [])
    if avantages:
        L.append("🎁 *Ventajas:*")
        for a in avantages:
            L.append(f"• {a}")
        L.append("")

    inconvenients = infos.get("inconvenients", [])
    if inconvenients:
        L.append("⚠️ *Puntos de atención:*")
        for i in inconvenients:
            L.append(f"• {i}")
        L.append("")

    compat = infos.get("compatibilite", {})
    if compat:
        score_global = 0
        labels = {
            "stack": "Stack técnico",
            "missions": "Misiones",
            "salaire": "Salario",
            "localisation": "Localización",
            "entreprise": "Empresa",
        }
        L.append("📊 *Compatibilidad:*")
        for cle, label in labels.items():
            if cle in compat:
                s = compat[cle].get("score", 0)
                note = compat[cle].get("note", "")
                poids = POIDS.get(cle, 0)
                score_global += s * poids
                em = score_emoji(s)
                L.append(f"{em} {label}: {s}%  —  {note}")
        L.append("─────────────────────")
        L.append(f"🎯 *Score global: {score_global:.0f}%*")
        L.append("")

    opinion = infos.get("opinion", "")
    if opinion:
        L.append("💬 *Opinión:*")
        L.append(opinion)
        L.append("")

    if not duree_ok:
        L.append(f"🚫 *Duración {duree} meses — incompatible con los 24 meses del Máster MIAGE.*")
        L.append("❌ Candidatura imposible.")
    else:
        L.append("─────────────────────")
        L.append("¿Genero la candidatura? Responde *s* o *n*")

    return "\n".join(L)


# ─── Flujos ───────────────────────────────────────────────────────────────────

def handle_add_source(chat_id, url):
    dominio = urlparse(url).netloc or url

    source = supabase_client.add_source(url, name=dominio)

    telegram_client.send_message(
        chat_id,
        f"✅ Fuente agregada: *{dominio}*\n🔗 {source['url']}\n\nSe revisará en el próximo scraping.",
    )


def handle_new_offer_url(chat_id, url):
    existing = supabase_client.get_offer_by_url(url)

    if existing and existing.get("analysis"):
        offer = existing
        infos = existing["analysis"]
    else:
        telegram_client.send_message(chat_id, "🔎 Analizando oferta...")

        texto = jina_client.fetch_texto_pagina(url)
        if not texto:
            telegram_client.send_message(chat_id, "⚠️ Jina no pudo leer esa oferta. ¿La URL es correcta y pública?")
            return

        try:
            infos = gemini_client.analyser_offre(texto)
        except Exception as e:
            telegram_client.send_message(chat_id, f"⚠️ Gemini no pudo analizar la oferta: {e}")
            return

        score = calcular_score_global(infos)
        offer = supabase_client.upsert_offer(url, analysis=infos, score_global=score, raw_text=texto, status="new")

    telegram_client.send_message(chat_id, formater_analyse(infos))

    if infos.get("duree_mois") == 24:
        supabase_client.set_conversation_state(chat_id, "awaiting_confirmation", {"offer_id": offer["id"]})
    else:
        supabase_client.update_offer_status(offer["id"], "incompatible")
        supabase_client.clear_conversation_state(chat_id)


STOP_WORDS = {"no", "non", "nada", "listo", "gracias", "stop"}


def _empresa_oferta(offer):
    """Renvoie toujours un nom d'entreprise (source > 'Entreprise :' > domaine du lien)."""
    source_name = (offer.get("sources") or {}).get("name")
    if source_name:
        return source_name
    raw_text = offer.get("raw_text") or ""
    m = re.search(r"Entreprise\s*:\s*(.+)", raw_text)
    if m:
        return m.group(1).strip()
    return urlparse(offer.get("offer_url", "")).netloc.removeprefix("www.") or "Entreprise inconnue"


def _ofertas_a_cards(offers):
    L = ["👋 *Ofertas encontradas:*", ""]
    for i, offer in enumerate(offers, start=1):
        L.append(f"{i}. *{offer.get('title') or '?'}*")
        L.append(f"   🏢 {_empresa_oferta(offer)}")
        if offer.get("location"):
            L.append(f"   📍 {offer['location']}")
        L.append(f"   🔗 {offer['offer_url']}")
        L.append("")
    L.append("Responde con el número para ver el análisis completo de esa oferta.")
    return "\n".join(L)


def _proponer_otra_oferta(chat_id, offer_ids):
    if offer_ids:
        telegram_client.send_message(
            chat_id, f"¿Quieres ver otra oferta? Responde con un número (1-{len(offer_ids)}) o 'no'."
        )
        supabase_client.set_conversation_state(chat_id, "awaiting_selection", {"offer_ids": offer_ids})
    else:
        supabase_client.clear_conversation_state(chat_id)


def handle_top10(chat_id):
    offers = supabase_client.get_top_offers(15)
    if not offers:
        telegram_client.send_message(chat_id, "👋 Hola Franco! No tengo ofertas nuevas todavía.")
        return

    telegram_client.send_message(chat_id, _ofertas_a_cards(offers))
    supabase_client.set_conversation_state(chat_id, "awaiting_selection", {"offer_ids": [o["id"] for o in offers]})


def handle_selection(chat_id, text, context):
    t = text.strip().lower()
    offer_ids = context.get("offer_ids", [])

    if t in STOP_WORDS:
        supabase_client.clear_conversation_state(chat_id)
        telegram_client.send_message(chat_id, "👌 Listo. Escribe *hola* cuando quieras ver más ofertas.")
        return

    try:
        idx = int(t) - 1
    except ValueError:
        telegram_client.send_message(chat_id, f"Responde con un número del 1 al {len(offer_ids)}, o 'no' para terminar.")
        return

    if idx < 0 or idx >= len(offer_ids):
        telegram_client.send_message(chat_id, "Número inválido.")
        return

    offer_id = offer_ids[idx]
    offer = supabase_client.get_offer(offer_id)

    infos = offer.get("analysis")
    if not infos:
        raw = offer.get("raw_text") or ""
        # 1. Regex gratuito
        mois = _duree_incompatible(raw)
        # 2. Mini Gemini (Flash-Lite, cuota separada) si el regex no detectó nada
        if mois is None:
            mois = gemini_client.check_duree_contrat(raw)

        if mois is not None and mois < 24:
            telegram_client.send_message(
                chat_id,
                f"🚫 Duración {mois} meses — incompatible con los 24 meses del Máster MIAGE.\n❌ Candidatura imposible.",
            )
            supabase_client.update_offer_analysis(offer_id, {"duree_mois": mois}, score_global=0, status="incompatible")
            _proponer_otra_oferta(chat_id, offer_ids)
            return

        telegram_client.send_message(chat_id, "🔎 Analizando oferta con Gemini...")
        try:
            infos = gemini_client.analyser_offre(offer["raw_text"])
        except Exception as e:
            telegram_client.send_message(chat_id, f"⚠️ Gemini no pudo analizar la oferta: {e}")
            return
        score = calcular_score_global(infos)
        status = "new" if infos.get("duree_mois") == 24 else "incompatible"
        supabase_client.update_offer_analysis(offer_id, infos, score, status=status)

    telegram_client.send_message(chat_id, formater_analyse(infos))

    if infos.get("duree_mois") == 24:
        supabase_client.set_conversation_state(
            chat_id, "awaiting_confirmation", {"offer_id": offer_id, "offer_ids": offer_ids}
        )
    else:
        _proponer_otra_oferta(chat_id, offer_ids)


def handle_confirmation(chat_id, text, context):
    offer_id = context.get("offer_id")
    offer_ids = context.get("offer_ids")
    t = text.strip().lower()

    if t in CONFIRM_YES:
        offer = supabase_client.get_offer(offer_id)
        infos = offer["analysis"]

        telegram_client.send_message(chat_id, "✍️ Generando candidatura...")

        try:
            docx_bytes = docx_gen.generer_lettre_bytes(infos)
            pdf_bytes = pdf_convert.docx_a_pdf(docx_bytes, filename="lettre.docx")

            entreprise = infos.get("entreprise_nom", "Entreprise").replace(" ", "_")
            telegram_client.send_document(chat_id, pdf_bytes, f"Lettre_Motivation_{entreprise}.pdf")
            telegram_client.send_document(chat_id, docx_bytes, f"Lettre_Motivation_{entreprise}.docx")

            cv_filename = CV_MAP.get(infos.get("type_cv"), CV_MAP["Data_Engineer"])
            cv_bytes = (ASSETS_CVS / cv_filename).read_bytes()
            telegram_client.send_document(chat_id, cv_bytes, cv_filename)
        except Exception as e:
            telegram_client.send_message(chat_id, f"⚠️ Error generando la candidatura: {e}")
            return

        supabase_client.update_offer_status(offer_id, "applied")
        _proponer_otra_oferta(chat_id, offer_ids)

    elif t in CONFIRM_NO:
        supabase_client.update_offer_status(offer_id, "discarded")
        telegram_client.send_message(chat_id, "👌 Descartado.")
        _proponer_otra_oferta(chat_id, offer_ids)

    else:
        telegram_client.send_message(chat_id, "Responde *s* (sí) o *n* (no).")


# ─── Routage principal ──────────────────────────────────────────────────────

def process_update(update):
    message = update.get("message")
    if not message or "text" not in message:
        return

    chat_id = message["chat"]["id"]

    allowed = os.environ.get("ALLOWED_CHAT_ID")
    if allowed and str(chat_id) != str(allowed):
        return

    text = message["text"].strip()

    try:
        _dispatch(chat_id, text)
    except Exception as e:
        traceback.print_exc()
        try:
            telegram_client.send_message(chat_id, f"❌ Error inesperado: {type(e).__name__}: {e}")
        except Exception:
            pass


def handle_raw_text_offer(chat_id, text):
    """Analiza el texto de una oferta pegado directamente (sin URL)."""
    pseudo_url = "text://" + hashlib.sha256(text.encode()).hexdigest()[:16]

    existing = supabase_client.get_offer_by_url(pseudo_url)
    if existing and existing.get("analysis"):
        infos = existing["analysis"]
        telegram_client.send_message(chat_id, formater_analyse(infos))
        if infos.get("duree_mois") == 24:
            supabase_client.set_conversation_state(
                chat_id, "awaiting_confirmation", {"offer_id": existing["id"]}
            )
        return

    mois = _duree_incompatible(text)
    if mois is None:
        mois = gemini_client.check_duree_contrat(text)
    if mois is not None and mois < 24:
        telegram_client.send_message(
            chat_id,
            f"🚫 Duración {mois} meses — incompatible con los 24 meses del Máster MIAGE.\n❌ Candidatura imposible.",
        )
        return

    telegram_client.send_message(chat_id, "🔎 Analizando oferta con Gemini...")
    try:
        infos = gemini_client.analyser_offre(text)
    except Exception as e:
        telegram_client.send_message(chat_id, f"⚠️ Gemini no pudo analizar la oferta: {e}")
        return

    score = calcular_score_global(infos)
    status = "new" if infos.get("duree_mois") == 24 else "incompatible"
    offer = supabase_client.upsert_offer(
        pseudo_url, analysis=infos, score_global=score, raw_text=text, status=status
    )

    telegram_client.send_message(chat_id, formater_analyse(infos))

    if infos.get("duree_mois") == 24:
        supabase_client.set_conversation_state(
            chat_id, "awaiting_confirmation", {"offer_id": offer["id"]}
        )
    else:
        supabase_client.clear_conversation_state(chat_id)


def _dispatch(chat_id, text):
    conv = supabase_client.get_conversation_state(chat_id)
    state = conv.get("state", "idle")
    context = conv.get("context") or {}

    if state == "awaiting_confirmation":
        handle_confirmation(chat_id, text, context)
        return

    if state == "awaiting_selection":
        handle_selection(chat_id, text, context)
        return

    url_match = URL_RE.search(text)

    if text.lower().startswith("/add"):
        if url_match:
            handle_add_source(chat_id, url_match.group(0))
        else:
            telegram_client.send_message(chat_id, "Uso: `/add https://empresa.com/carreras`")
    elif url_match:
        handle_new_offer_url(chat_id, url_match.group(0))
    elif text.lower() in GREETINGS:
        handle_top10(chat_id)
    elif len(text) >= 150:
        handle_raw_text_offer(chat_id, text)
    else:
        telegram_client.send_message(
            chat_id,
            "👋 Envíame la URL de una oferta, pega el texto completo de la oferta, "
            "escribe *hola* para ver ofertas guardadas, "
            "o `/add <url>` para agregar una página de carreras.",
        )


# ─── Entrée Vercel ──────────────────────────────────────────────────────────

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        secret_expected = os.environ.get("TELEGRAM_WEBHOOK_SECRET")
        if secret_expected:
            secret_received = self.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if secret_received != secret_expected:
                self.send_response(401)
                self.end_headers()
                return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            update = json.loads(body)
            process_update(update)
        except Exception as e:
            print(f"Error processing update: {e}")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')
