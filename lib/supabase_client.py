"""Helpers Supabase : état de conversation, ofertas, sources."""

import os

from supabase import create_client

_client = None


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
    """Dernières offres trouvées par le scraping, en attente de revue (pas encore analysées par Gemini)."""
    res = (
        get_client()
        .table("offers")
        .select("*")
        .eq("status", "new")
        .order("scraped_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data


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
