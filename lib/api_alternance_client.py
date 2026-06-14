"""Recherche d'offres via l'API publique "La bonne alternance" (api.apprentissage.beta.gouv.fr)."""

import os

import requests

API_URL = "https://api.apprentissage.beta.gouv.fr/api/job/v1/search"


def search_offers(romes=None, latitude=None, longitude=None, radius=30, target_diploma_level=None):
    """Recherche des offres d'apprentissage. Retourne la liste `jobs` de la réponse (peut être vide)."""
    api_key = os.environ["API_ALTERNANCE_KEY"]

    params = {"radius": radius}
    if romes:
        params["romes"] = romes
    if latitude is not None:
        params["latitude"] = latitude
    if longitude is not None:
        params["longitude"] = longitude
    if target_diploma_level:
        params["target_diploma_level"] = target_diploma_level

    resp = requests.get(
        API_URL,
        params=params,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("jobs", [])


def job_to_text(job):
    """Construit un texte descriptif à partir d'une offre JSON, pour l'analyse Gemini différée."""
    offer = job.get("offer", {})
    workplace = job.get("workplace", {})
    contract = job.get("contract", {})

    L = [offer.get("title", "")]

    entreprise = workplace.get("name") or workplace.get("brand") or workplace.get("legal_name")
    if entreprise:
        L.append(f"Entreprise : {entreprise}")

    adresse = workplace.get("location", {}).get("address")
    if adresse:
        L.append(f"Lieu : {adresse}")

    types_contrat = contract.get("type") or []
    duree = contract.get("duration")
    if types_contrat or duree:
        L.append(f"Contrat : {', '.join(types_contrat)} — {duree} mois" if duree else f"Contrat : {', '.join(types_contrat)}")

    diplome = offer.get("target_diploma")
    if diplome:
        L.append(f"Diplôme visé : {diplome.get('label')}")

    description = offer.get("description")
    if description:
        L.append("")
        L.append("Description :")
        L.append(description)

    competences = offer.get("desired_skills") or []
    if competences:
        L.append("")
        L.append("Compétences recherchées : " + ", ".join(competences))

    a_acquerir = offer.get("to_be_acquired_skills") or []
    if a_acquerir:
        L.append("Compétences à acquérir : " + ", ".join(a_acquerir))

    return "\n".join(L)
