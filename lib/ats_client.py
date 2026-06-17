"""Clients pour les APIs publiques d'ATS (Applicant Tracking Systems).

Lever, Greenhouse, SmartRecruiters et Workday exposent des endpoints JSON
publics sans authentification. Les offres sont filtrées par mots-clés de rôle
et localisation Paris.
"""

import re
import requests

_ROLE_RE = re.compile(
    r"data|engineer|ingénieur|développeur|developer|devops|software|"
    r"informatique|digital|tech|ia\b|intelligence artificielle|"
    r"alternance|apprentissage|stage",
    re.IGNORECASE,
)

_PARIS_RE = re.compile(
    r"paris|île-de-france|idf|nanterre|boulogne|la.?défense|"
    r"levallois|issy|courbevoie|neuilly|montreuil|saint-denis|clichy|puteaux",
    re.IGNORECASE,
)


def _is_relevant(title, location=""):
    return _ROLE_RE.search(title or "") and _PARIS_RE.search(location or title or "")


# ── Lever ─────────────────────────────────────────────────────────────────────

def fetch_lever(slug, timeout=20):
    """Retourne les offres d'une entreprise sur Lever (JSON public).

    slug : identifiant de l'entreprise sur jobs.lever.co (ex: 'manomano')
    """
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        postings = resp.json()
    except requests.RequestException:
        return []

    results = []
    for p in postings:
        title = p.get("text", "")
        location = (p.get("categories") or {}).get("location", "")
        offer_url = p.get("hostedUrl", "")
        if not offer_url or not _is_relevant(title, location):
            continue
        results.append({
            "title": title,
            "offer_url": offer_url,
            "location": location,
            "raw_text": (
                f"Entreprise : {slug.capitalize()}\n"
                f"Poste : {title}\n"
                f"Localisation : {location}\n"
                f"Département : {(p.get('categories') or {}).get('department', '')}\n"
                f"Lien : {offer_url}\n\n"
                + _strip_html(p.get("descriptionPlain") or p.get("description") or "")
            ),
        })
    return results


# ── Greenhouse ────────────────────────────────────────────────────────────────

def fetch_greenhouse(slug, timeout=20):
    """Retourne les offres d'une entreprise sur Greenhouse (JSON public).

    slug : identifiant du board Greenhouse (ex: 'doctolib')
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        jobs = resp.json().get("jobs", [])
    except requests.RequestException:
        return []

    results = []
    for j in jobs:
        title = j.get("title", "")
        location = (j.get("location") or {}).get("name", "")
        offer_url = j.get("absolute_url", "")
        if not offer_url or not _is_relevant(title, location):
            continue
        results.append({
            "title": title,
            "offer_url": offer_url,
            "location": location,
            "raw_text": (
                f"Entreprise : {slug.capitalize()}\n"
                f"Poste : {title}\n"
                f"Localisation : {location}\n"
                f"Lien : {offer_url}\n\n"
                + _strip_html(j.get("content") or "")
            ),
        })
    return results


# ── SmartRecruiters ───────────────────────────────────────────────────────────

def fetch_smartrecruiters(company_id, company_name, timeout=20):
    """Retourne les offres d'une entreprise sur SmartRecruiters (JSON public).

    company_id : identifiant SmartRecruiters (ex: 'SocieteGenerale4', 'SopraSteria1')
    """
    url = f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings"
    try:
        resp = requests.get(url, params={"limit": 100, "country": "fr"}, timeout=timeout)
        resp.raise_for_status()
        postings = resp.json().get("content", [])
    except requests.RequestException:
        return []

    results = []
    for p in postings:
        title = p.get("name", "")
        loc = p.get("location") or {}
        location = ", ".join(filter(None, [loc.get("city"), loc.get("region")]))
        posting_id = p.get("id", "")
        offer_url = f"https://jobs.smartrecruiters.com/{company_id}/{posting_id}"
        if not posting_id or not _is_relevant(title, location):
            continue
        results.append({
            "title": title,
            "offer_url": offer_url,
            "location": location,
            "raw_text": (
                f"Entreprise : {company_name}\n"
                f"Poste : {title}\n"
                f"Localisation : {location}\n"
                f"Département : {(p.get('department') or {}).get('label', '')}\n"
                f"Lien : {offer_url}\n"
            ),
        })
    return results


# ── Workday ───────────────────────────────────────────────────────────────────

def fetch_workday(subdomain, career_site, company_name, search_text="alternance", timeout=25):
    """Retourne les offres d'une entreprise sur Workday (API POST publique).

    subdomain   : ex 'thales' → thales.wd3.myworkdayjobs.com
    career_site : ex 'Careers'
    """
    # Workday uses wd3 for most European companies; try wd3 then wd1
    for wdN in ("wd3", "wd1", "wd5"):
        base = f"https://{subdomain}.{wdN}.myworkdayjobs.com"
        api_url = f"{base}/wday/cxs/{subdomain}/{career_site}/jobs"
        try:
            resp = requests.post(
                api_url,
                json={"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": search_text},
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )
            if resp.status_code == 404:
                continue
            resp.raise_for_status()
            postings = resp.json().get("jobPostings", [])
            results = []
            for p in postings:
                title = p.get("title", "")
                location = p.get("locationsText", "")
                external_path = p.get("externalPath", "")
                offer_url = f"{base}/{career_site}{external_path}" if external_path else ""
                if not offer_url or not _is_relevant(title, location):
                    continue
                results.append({
                    "title": title,
                    "offer_url": offer_url,
                    "location": location,
                    "raw_text": (
                        f"Entreprise : {company_name}\n"
                        f"Poste : {title}\n"
                        f"Localisation : {location}\n"
                        f"Lien : {offer_url}\n"
                    ),
                })
            return results
        except requests.RequestException:
            continue
    return []


# ── Utilitaire ────────────────────────────────────────────────────────────────

def _strip_html(html):
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r" {2,}", " ", text).strip()


def fetch_lever(slug, timeout=20):
    """Retourne les offres d'une entreprise sur Lever (JSON public).

    slug : identifiant de l'entreprise sur jobs.lever.co (ex: 'manomano')
    """
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        postings = resp.json()
    except requests.RequestException:
        return []

    results = []
    for p in postings:
        title = p.get("text", "")
        location = (p.get("categories") or {}).get("location", "")
        offer_url = p.get("hostedUrl", "")
        if not offer_url or not _is_relevant(title, location):
            continue
        results.append({
            "title": title,
            "offer_url": offer_url,
            "location": location,
            "raw_text": (
                f"Entreprise : {slug.capitalize()}\n"
                f"Poste : {title}\n"
                f"Localisation : {location}\n"
                f"Département : {(p.get('categories') or {}).get('department', '')}\n"
                f"Lien : {offer_url}\n\n"
                + _strip_html(p.get("descriptionPlain") or p.get("description") or "")
            ),
        })
    return results


# ── Greenhouse ────────────────────────────────────────────────────────────────

def fetch_greenhouse(slug, timeout=20):
    """Retourne les offres d'une entreprise sur Greenhouse (JSON public).

    slug : identifiant du board Greenhouse (ex: 'doctolib')
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        jobs = resp.json().get("jobs", [])
    except requests.RequestException:
        return []

    results = []
    for j in jobs:
        title = j.get("title", "")
        location = (j.get("location") or {}).get("name", "")
        offer_url = j.get("absolute_url", "")
        if not offer_url or not _is_relevant(title, location):
            continue
        content = _strip_html(
            (j.get("content") or "")
        )
        results.append({
            "title": title,
            "offer_url": offer_url,
            "location": location,
            "raw_text": (
                f"Entreprise : {slug.capitalize()}\n"
                f"Poste : {title}\n"
                f"Localisation : {location}\n"
                f"Lien : {offer_url}\n\n"
                + content
            ),
        })
    return results


# ── Utilitaire ────────────────────────────────────────────────────────────────

def _strip_html(html):
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r" {2,}", " ", text).strip()
