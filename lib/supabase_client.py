"""Helpers Supabase : état de conversation, ofertas, sources."""

import os
import re

from supabase import create_client

_client = None

# Tier 1 : GAFAM/FAANG + labs IA, priorité absolue dans le top des offres ("hola").
TOP_PRIORITY_RE = re.compile(
    r"\bgoogle\b|\bapple\b|\bamazon\b|\bmicrosoft\b|\bopenai\b|\banthropic\b|"
    r"\bmeta\b|\bfacebook\b|\bnetflix\b",
    re.IGNORECASE,
)

# Tier 2 : grandes entreprises (banques CAC40, ESN, géants tech US, etc.) à faire remonter ensuite.
PRIORITY_COMPANIES_RE = re.compile(
    r"\bbnp\b|soci[ée]t[ée]\s+g[ée]n[ée]rale|\bsg\b|cr[ée]dit\s+agricole|\bthales\b|"
    r"\bbpce\b|l['’]?or[ée]al|air\s+france|capgemini|sopra\s*steria|\baxa\b|"
    r"\borange\b|\blvmh\b|decathlon|doctolib|\bedf\b|"
    r"\bibm\b|salesforce|\bcisco\b|\boracle\b|\bsap\b|servicenow|\badp\b",
    re.IGNORECASE,
)


def _offer_priority_rank(offer):
    """0 = GAFAM/IA (tier 1), 1 = grandes entreprises (tier 2), 2 = reste."""
    texto = " ".join(filter(None, [offer.get("title"), offer.get("location"), offer.get("raw_text")]))
    if TOP_PRIORITY_RE.search(texto):
        return 0
    if PRIORITY_COMPANIES_RE.search(texto):
        return 1
    return 2


def get_client():
    global _client
    if _client is None:
        _client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
    return _client


# ─── conversation_state ──────────────────────────────────────────────────────

def get_conversation_state(chat_id):
    res = (
        get_client()
        .table("conversation_state")
        .select("*")
        .eq("chat_id", chat_id)
        .execute()
    )
    if res.data:
        return res.data[0]
    return {"chat_id": chat_id, "state": "idle", "context": None}


def set_conversation_state(chat_id, state, context=None):
    get_client().table("conversation_state").upsert({
        "chat_id": chat_id,
        "state": state,
        "context": context,
    }).execute()


def clear_conversation_state(chat_id):
    set_conversation_state(chat_id, "idle", None)


# ─── offers ───────────────────────────────────────────────────────────────────

def get_offer_by_url(offer_url):
    res = get_client().table("offers").select("*").eq("offer_url", offer_url).execute()
    return res.data[0] if res.data else None


def get_offer(offer_id):
    res = get_client().table("offers").select("*").eq("id", offer_id).execute()
    return res.data[0] if res.data else None


def upsert_offer(offer_url, source_id=None, title=None, location=None, raw_text=None,
                  analysis=None, score_global=None, status="new"):
    row = {"offer_url": offer_url, "status": status}
    if source_id is not None:
        row["source_id"] = source_id
    if title is not None:
        row["title"] = title
    if location is not None:
        row["location"] = location
    if raw_text is not None:
        row["raw_text"] = raw_text
    if analysis is not None:
        row["analysis"] = analysis
    if score_global is not None:
        row["score_global"] = score_global

    res = (
        get_client()
        .table("offers")
        .upsert(row, on_conflict="offer_url")
        .execute()
    )
    return res.data[0]


def update_offer_status(offer_id, status):
    get_client().table("offers").update({"status": status}).eq("id", offer_id).execute()


def update_offer_analysis(offer_id, analysis, score_global, status=None):
    row = {"analysis": analysis, "score_global": score_global}
    if status is not None:
        row["status"] = status
    get_client().table("offers").update(row).eq("id", offer_id).execute()


def get_top_offers(limit=15):
    """Dernières offres trouvées par le scraping, en attente de revue (pas encore analysées par Gemini).

    Les offres GAFAM/IA (TOP_PRIORITY_RE) remontent en premier, puis les grandes
    entreprises (PRIORITY_COMPANIES_RE), puis le reste."""
    res = (
        get_client()
        .table("offers")
        .select("*")
        .eq("status", "new")
        .order("scraped_at", desc=True)
        .limit(limit * 3)
        .execute()
    )
    offers = sorted(res.data, key=_offer_priority_rank)
    return offers[:limit]


# ─── sources ─────────────────────────────────────────────────────────────────

def get_active_sources():
    res = get_client().table("sources").select("*").eq("active", True).execute()
    return res.data


def update_source_last_scraped(source_id, timestamp):
    get_client().table("sources").update({"last_scraped_at": timestamp}).eq("id", source_id).execute()


def add_source(url, name):
    res = (
        get_client()
        .table("sources")
        .upsert({"name": name, "url": url, "active": True}, on_conflict="url")
        .execute()
    )
    return res.data[0]


# ─── api_searches ────────────────────────────────────────────────────────────

def get_active_api_searches():
    res = get_client().table("api_searches").select("*").eq("active", True).execute()
    return res.data


def update_api_search_last_scraped(search_id, timestamp):
    get_client().table("api_searches").update({"last_scraped_at": timestamp}).eq("id", search_id).execute()
