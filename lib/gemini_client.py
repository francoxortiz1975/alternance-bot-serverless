"""Analyse d'offres via Gemini : prompt, appel avec cascade de modèles, parsing JSON."""

import json
import re
import time

import google.generativeai as genai

from .scoring import PARAGRAPHES_TECH

GEMINI_API_KEY = None  # injecté via configure_api_key()

PROMPT_TEMPLATE = """Tu es un assistant de candidature pour Franco Ortiz.

Profil complet :
- 21 ans (né le 26/01/2005), nationalité équatorienne — titre de séjour étudiant, autorisé à travailler en France via contrat d'apprentissage (CFA NumiA gère l'administratif)
- Master MIAGE — Université Paris Dauphine-PSL, 16e arrondissement (sept. 2026–2028)
- Rythme alternance : 1 semaine école / 1 semaine entreprise — disponible 1er août 2026
- Licence Informatique & Mathématiques — Grenoble-Alpes + échange University of Toronto
- Stack technique : Python, PostgreSQL, SQL, Git, REST APIs, LLM, RAG, Docker, JavaScript, React, Firebase, Meta API
- Expérience : MediLyft (chatbot pré-diagnostic médical, Python/Meta API/PostgreSQL), Campus France EC
- Projets : Etudly (EdTech LLM), Sumay Coffee Club (PWA React/Supabase)
- Article co-signé accepté ITiCSE 2026 (ACM) — LLM dans l'enseignement
- ENSIMAG Summer School AI 2025 sélectionné, Apple Swift Challenge, Claude Code Builders hackathon
- Langues : espagnol natif, anglais C1 (IELTS), français B2 (DELF)
- Portfolio : https://francoxortiz.vercel.app

Salaire légal minimum apprentissage (21–25 ans) :
- 1ère année : ~53% SMIC ≈ 955 €/mois | 2ème année : ~61% SMIC ≈ 1 099 €/mois
- Grandes entreprises (BNP, SG, CA) paient généralement 1 100–1 300 €/mois

Analyse cette offre d'emploi et retourne un JSON avec EXACTEMENT ces champs :

{{
  "entreprise_nom": "Nom complet de l'entreprise",
  "equipe_departement": "Nom de l'équipe ou département",
  "localisation": "Ville et arrondissement si Paris (ex: Paris 13e, Montreuil 93100)",
  "distance_dauphine": "Trajet précis depuis Dauphine (Place du Maréchal de Lattre de Tassigny, 16e arr.). Donne le temps ET la ligne concrète. Ex: '~25 min — Métro 9 dir. Mairie de Montreuil' ou '~40 min — RER C dir. Versailles puis Bus 91'. Si plusieurs options, garde la plus rapide.",
  "titre_objet": "Candidature à l'alternance [Poste exact]. Supprime TOUTES les mentions H/F, F/H, H/F/X et similaires. Supprime TOUTES les références (Réf., référence, #, numéro d'offre). Le titre doit être uniquement : 'Candidature à l'alternance [Poste propre]'.",
  "duree_mois": 24,
  "salaire": "Salaire mensuel brut si mentionné dans l'offre. Si non mentionné, estime-le selon : l'âge de Franco (21 ans, minimum légal ~955 €/mois en 1ère année), le type d'entreprise (grande banque/CAC40 = 1 100–1 300 €, ESN/PME = 950–1 100 €, startup = 900–1 050 €) et le niveau du poste. Indique clairement si c'est une estimation. Ex: '~1 200 €/mois (estimé — grande banque, poste data)' ou '1 150 €/mois (indiqué dans l'offre)'.",
  "taches": ["tâche 1", "tâche 2", "tâche 3"],
  "technologies": ["tech1", "tech2", "tech3"],
  "jour_type": "2-3 phrases décrivant concrètement une semaine typique à ce poste. Pas générique — basé sur les missions réelles de l'offre.",
  "avantages": ["avantage 1", "avantage 2"],
  "inconvenients": ["inconvénient 1", "inconvénient 2"],
  "compatibilite": {{
    "stack":        {{"score": 0, "note": "quelles techs matchent, lesquelles manquent"}},
    "missions":     {{"score": 0, "note": "explication courte"}},
    "salaire":      {{"score": 0, "note": "montant estimé ou indiqué vs minimum légal ~955 €"}},
    "localisation": {{"score": 0, "note": "distance + impact rythme 1S/1S"}},
    "entreprise":   {{"score": 0, "note": "explication courte"}}
  }},
  "opinion": "3-5 phrases d'opinion directe et objective. Bons points, mauvais points. Est-ce une bonne offre pour 2 ans ? Pas de langue de bois.",
  "phrase_motivation": "Ce que Franco veut développer. Commencer par verbe infinitif.",
  "domaine_technique": "Domaine technique principal",
  "secteur": "Secteur de l'entreprise",
  "type_cv": "Un parmi : Data_Engineer, Data_IA, Data_Scientist, Software_Engineer, DevOps, Chef_de_Projet, Business_Analyst, Data_Analyst, IT_Generalist",
  "paragraphe_tech_adapte": "Voir instructions ci-dessous"
}}

Règles pour les scores de compatibilité (0-100) :
- stack : basé sur le % de technologies de l'offre que Franco maîtrise déjà
- salaire : 100 = ≥1 300 €/mois | 80 = 1 150–1 300 € | 60 = 1 000–1 150 € | 40 = ~955 € (minimum légal) | 20 = sous le minimum ou très flou
- missions : adéquation entre les missions et le profil MIAGE data/dev de Franco
- localisation : 100 = moins de 20 min de Dauphine, 80 = 20-30 min, 60 = 30-45 min, 40 = 45-60 min, 20 = plus d'1h. Tiens compte du rythme 1S/1S.
- entreprise : prestige, dynamisme tech, valeur CV, ambiance probable

Pour "type_cv", utilise IT_Generalist si l'offre est un poste généraliste informatique/gestion (support IT, coordination, polyvalence technique et métier) qui ne correspond clairement à aucune des autres catégories.

Pour "paragraphe_tech_adapte" :
- Prends le paragraphe de base correspondant au type_cv (voir ci-dessous)
- Ajoute 1-2 références aux technologies spécifiques de l'offre
- Garde la même structure et longueur
- Ne modifie pas MediLyft ni ITiCSE 2026
- Pas de tirets doubles (--)
- Si type_cv est Software_Engineer ou DevOps : ajoute à la fin (après la phrase ITiCSE) : "Mon portfolio (francoxortiz.dev) illustre ces réalisations concrètes."
- Si type_cv est Data_IA, Data_Engineer ou Data_Scientist : après la phrase ITiCSE, ajoute : "J'ai également été sélectionné à l'ENSIMAG Summer School on AI 2025, ce qui témoigne de mon engagement sur ces sujets."

Paragraphes de base :

Data_Engineer :
{para_Data_Engineer}

Data_IA :
{para_Data_IA}

Software_Engineer :
{para_Software_Engineer}

DevOps :
{para_DevOps}

Chef_de_Projet :
{para_Chef_de_Projet}

Business_Analyst :
{para_Business_Analyst}

Data_Analyst :
{para_Data_Analyst}

IT_Generalist :
{para_IT_Generalist}

IMPORTANT — LANGUE :
Les champs suivants doivent être rédigés en ESPAÑOL (pour affichage dans le bot) :
  taches, avantages, inconvenients, opinion, jour_type, salaire,
  distance_dauphine, et tous les champs "note" dans compatibilite.

Tous les autres champs doivent rester en FRANÇAIS, car ils sont insérés
directement dans la lettre de motivation ou dans les documents officiels :
  entreprise_nom, equipe_departement, localisation, titre_objet,
  phrase_motivation, domaine_technique, secteur, paragraphe_tech_adapte.

Offre :
{offre}

Réponds UNIQUEMENT avec le JSON valide, sans markdown, sans commentaire."""


def configure_api_key(api_key):
    genai.configure(api_key=api_key)


def _gemini_generate(prompt, model_name="gemini-2.5-flash", max_retries=2, max_attente=12):
    """Appel Gemini avec cascade de modèles + retry sur 429.

    `max_attente` borne le temps d'attente entre tentatives, pour ne pas dépasser
    le `maxDuration` de la fonction Vercel (le webhook doit répondre en <60s).
    """
    cascade = [model_name, "gemini-2.0-flash", "gemini-2.0-flash-lite"]
    seen = set()
    cascade = [m for m in cascade if not (m in seen or seen.add(m))]

    last_exc = None
    for modele in cascade:
        model = genai.GenerativeModel(modele)
        for tentative in range(1, max_retries + 1):
            try:
                return model.generate_content(prompt)
            except Exception as e:
                msg = str(e)
                is_rate = "429" in msg or "quota" in msg.lower() or "rate" in msg.lower()
                is_daily = "day" in msg.lower() or "GenerateRequestsPerDay" in msg
                if is_rate:
                    if is_daily:
                        last_exc = e
                        break
                    m = re.search(r'retry[^\d]*(\d+)', msg, re.IGNORECASE)
                    attente = min(int(m.group(1)) + 5 if m else max_attente, max_attente)
                    if tentative < max_retries:
                        time.sleep(attente)
                        continue
                last_exc = e
                break

    raise last_exc


def _extraire_json(texte):
    texte = texte.strip()
    if texte.startswith("```"):
        texte = texte.split("```")[1]
        if texte.startswith("json"):
            texte = texte[4:]

    try:
        return json.loads(texte)
    except json.JSONDecodeError:
        pass

    try:
        from json_repair import repair_json
        return json.loads(repair_json(texte))
    except Exception:
        pass

    prompt_retry = (
        "Le JSON suivant est invalide. Corrige-le et retourne UNIQUEMENT le JSON valide, "
        "sans markdown, sans commentaire, sans saut de ligne à l'intérieur des valeurs string.\n\n"
        f"{texte}"
    )
    response2 = _gemini_generate(prompt_retry)
    return _extraire_json(response2.text)


def check_duree_contrat(offre_texte):
    """Mini-appel Gemini (Flash-Lite) pour extraire la durée du contrat.

    Retourne le nombre de mois (int) si trouvé et < 24, sinon None.
    Utilise uniquement les 2 000 premiers caractères — la durée est presque
    toujours dans l'en-tête ou les premières lignes de l'offre.
    """
    prompt = (
        "Extrae la duración del contrato de esta oferta de empleo. "
        "Responde ÚNICAMENTE con el número de meses (entero). "
        "Si no está especificada o es ambigua, responde 0.\n\n"
        + (offre_texte or "")[:2000]
    )
    try:
        resp = _gemini_generate(prompt, model_name="gemini-2.0-flash-lite", max_retries=1, max_attente=5)
        mois = int(resp.text.strip())
        return mois if mois > 0 else None
    except Exception:
        return None


def analyser_offre(offre_texte):
    """Analyse une offre et retourne le dict `infos` (même format que candidature_auto.py)."""
    prompt = PROMPT_TEMPLATE.format(
        para_Data_Engineer    = PARAGRAPHES_TECH["Data_Engineer"],
        para_Data_IA          = PARAGRAPHES_TECH["Data_IA"],
        para_Software_Engineer= PARAGRAPHES_TECH["Software_Engineer"],
        para_DevOps           = PARAGRAPHES_TECH["DevOps"],
        para_Chef_de_Projet   = PARAGRAPHES_TECH["Chef_de_Projet"],
        para_Business_Analyst = PARAGRAPHES_TECH["Business_Analyst"],
        para_Data_Analyst     = PARAGRAPHES_TECH["Data_Analyst"],
        para_IT_Generalist    = PARAGRAPHES_TECH["IT_Generalist"],
        offre                 = offre_texte,
    )

    response = _gemini_generate(prompt)
    return _extraire_json(response.text)


def raccourcir_para_tech(infos, cible_chars):
    """Demande à Gemini de raccourcir le paragraphe technique."""
    para_actuel = infos.get("paragraphe_tech_adapte", "")
    prompt = (
        f"Raccourcis ce paragraphe de lettre de motivation à environ {cible_chars} caractères maximum.\n"
        "Garde les éléments clés (MediLyft, ITiCSE, stack principal). Sois concis et professionnel.\n\n"
        f"Paragraphe original :\n{para_actuel}\n\n"
        "Réponds UNIQUEMENT avec le paragraphe raccourci, sans guillemets ni commentaires."
    )
    nouveau = _gemini_generate(prompt).text.strip()
    infos["paragraphe_tech_adapte"] = nouveau
    return nouveau
