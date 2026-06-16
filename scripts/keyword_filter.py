"""Filtrado por palabras clave (sin Gemini) de las páginas de listado de ofertas.

Jina Reader devuelve el contenido de la página en Markdown, donde los enlaces
aparecen como [texto](url). Buscamos enlaces cuyo texto contenga una palabra
clave de puesto, y extraemos una localización aproximada del texto de detalle.
"""

import re
from urllib.parse import urljoin

MARKDOWN_LINK_RE = re.compile(r"\[([^\]\n]+)\]\((https?://[^\s)]+|/[^\s)]*)\)")

# URLs qui pointent vers des pages de description de métier (pas des offres d'emploi).
NON_OFFER_URL_RE = re.compile(r"/m[eé]tiers?/", re.IGNORECASE)

ROLE_KEYWORDS = [
    "data engineer", "data analyst", "data scientist", "data analyste",
    "ingénieur data", "ingenieur data", "intelligence artificielle",
    "machine learning", "data ia", " ia ", "ia,", "ia)",
    "software engineer", "développeur", "developpeur", "devops",
    "business analyst", "chef de projet", "data",
]

LOCATION_PATTERNS = [
    re.compile(r"Paris\s*\d{1,2}(?:e|er|ème)?\b", re.IGNORECASE),
    re.compile(
        r"\b(Montreuil|Boulogne-Billancourt|Levallois-Perret|Issy-les-Moulineaux|"
        r"Nanterre|Saint-Denis|Neuilly-sur-Seine|Courbevoie|La Défense|Puteaux|"
        r"Vincennes|Ivry-sur-Seine|Clichy|Aubervilliers)\b",
        re.IGNORECASE,
    ),
]

# Organismes de formation qui republient leurs propres formations comme des
# offres d'emploi (ce ne sont pas de vraies offres d'un employeur), et offres
# de "stage" (Franco cherche une alternance, pas un stage) — exclus du scraping
# si ça apparaît dans l'employeur/titre de l'offre.
EXCLUDED_KEYWORDS_RE = re.compile(r"\b(iscod|cfa|stages?|stagiaires?)\b", re.IGNORECASE)


def es_oferta_excluida(*textos):
    """Renvoie True si l'un des textes fournis (titre, employeur...) matche
    un organisme de formation à exclure (ISCOD, CFA...) ou une offre de stage."""
    return any(texto and EXCLUDED_KEYWORDS_RE.search(texto) for texto in textos)


def extraer_enlaces_filtrados(texto_markdown, base_url):
    """Retourne une liste de {"titulo": ..., "url": ...} pour les liens dont le
    texte matche un ROLE_KEYWORD. URLs relatives résolues vers base_url."""
    encontrados = {}

    for match in MARKDOWN_LINK_RE.finditer(texto_markdown):
        titulo, url = match.group(1).strip(), match.group(2).strip()
        titulo_lower = titulo.lower()

        if not any(kw in titulo_lower for kw in ROLE_KEYWORDS):
            continue

        url_absoluta = urljoin(base_url, url)
        if NON_OFFER_URL_RE.search(url_absoluta):
            continue
        if url_absoluta not in encontrados:
            encontrados[url_absoluta] = titulo

    return [{"titulo": t, "url": u} for u, t in encontrados.items()]


def extraer_localizacion(texto):
    """Retourne la première localisation trouvée dans le texte, ou None."""
    for pattern in LOCATION_PATTERNS:
        match = pattern.search(texto)
        if match:
            return match.group(0)
    return None
