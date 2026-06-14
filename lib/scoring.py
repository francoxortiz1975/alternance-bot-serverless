"""Pondération de compatibilité, mapping CV et calcul du score global."""

# Poids compatibilité (doivent sommer à 1.0) — durée exclue : c'est un filtre dur
POIDS = {
    "stack":        0.30,
    "missions":     0.20,
    "salaire":      0.25,
    "localisation": 0.10,
    "entreprise":   0.15,
}

CV_MAP = {
    "Data_Engineer":     "Alternance_ORTIZ_M1MIAGE_Dauphine_INGDATApdf.pdf",
    "Data_IA":           "Alternance_ORTIZ_M1MIAGE_Dauphine_IngIA.pdf",
    "Data_Scientist":    "Alternance_ORTIZ_M1MIAGE_Dauphine_DataScientist.pdf",
    "Software_Engineer": "Alternance_ORTIZ_M1MIAGE_Dauphine_DevSoftware.pdf",
    "DevOps":            "Alternance_ORTIZ_M1MIAGE_Dauphine_IngDevOps.pdf",
    "Chef_de_Projet":    "Alternance_ORTIZ_M1MIAGE_Dauphine_ChefProjet.pdf",
    "Business_Analyst":  "Alternance_ORTIZ_M1MIAGE_Dauphine_BusinessAnalyst.pdf",
    "Data_Analyst":      "Alternance_ORTIZ_M1MIAGE_Dauphine_DataAnalyst.pdf",
    "IT_Generalist":     "Alternance_ORTIZ_M1MIAGE_Dauphine_GENERAL.pdf",
}

# ─── PARAGRAPHES TECHNIQUES DE BASE ─────────────────────────────────────────

PARAGRAPHES_TECH = {
    "Data_Engineer": (
        "Sur le plan technique, je maîtrise Python, les API REST et les pipelines de données "
        "orientés production. Je travaille notamment sur des architectures intégrant des flux de "
        "données structurés et non structurés, avec un souci constant d'industrialisation et de "
        "qualité. Je mets ces compétences en pratique chez MediLyft, une entreprise de santé "
        "numérique, où je conçois l'architecture de données et le workflow d'un chatbot "
        "pré-diagnostique, expérience qui m'a appris à faire face aux contraintes de scalabilité "
        "en environnement réel. Au-delà de ces compétences, je co-signe un papier accepté à "
        "ITiCSE 2026 (conférence ACM), pour lequel j'ai travaillé en cycles itératifs et validé "
        "des résultats de manière rigoureuse."
    ),
    "Data_IA": (
        "Sur le plan technique, je maîtrise Python, les API REST et les architectures LLM "
        "orientées production. Je m'intéresse particulièrement à l'industrialisation de "
        "solutions d'IA, de la conception du pipeline à la mise en production. Je mets ces "
        "compétences en pratique chez MediLyft, une entreprise de santé numérique, où je "
        "conçois l'architecture de données et le workflow d'un chatbot pré-diagnostique basé "
        "sur des modèles de langage, expérience qui m'a appris à allier performance et "
        "robustesse en contexte réel. Au-delà de ces compétences, je co-signe un papier "
        "accepté à ITiCSE 2026 (conférence ACM), pour lequel j'ai travaillé en cycles "
        "itératifs et validé des résultats de manière rigoureuse."
    ),
    "Data_Scientist": (
        "Sur le plan technique, je maîtrise Python, le Machine Learning et les pipelines "
        "de modélisation orientés production. Je m'intéresse particulièrement à la mise en "
        "œuvre de modèles prédictifs robustes, de l'exploration des données jusqu'à "
        "l'évaluation en conditions réelles. Je mets ces compétences en pratique chez "
        "MediLyft, une entreprise de santé numérique, où je conçois l'architecture de "
        "données et le workflow d'un chatbot pré-diagnostique, expérience qui m'a appris "
        "à combiner rigueur statistique et contraintes d'usage en production. Au-delà de "
        "ces compétences, je co-signe un papier accepté à ITiCSE 2026 (conférence ACM), "
        "pour lequel j'ai travaillé en cycles itératifs et validé des résultats de manière "
        "rigoureuse. J'ai également été sélectionné à l'ENSIMAG Summer School on AI 2025, "
        "ce qui témoigne de mon engagement sur ces sujets."
    ),
    "Software_Engineer": (
        "Sur le plan technique, je maîtrise Python, SQL et Git, et j'ai développé une "
        "sensibilité aux architectures logicielles robustes et aux pratiques de développement "
        "orienté production. Mon expérience avec les API REST et les environnements Big Data "
        "m'a appris à concevoir des solutions maintenables et évolutives. Je mets ces "
        "compétences en pratique chez MediLyft, une entreprise de santé numérique, où je "
        "conçois l'architecture de données et le workflow d'un chatbot pré-diagnostique, "
        "expérience qui m'a permis de consolider ma pratique du développement en cycle complet. "
        "Au-delà de ces compétences, je co-signe un papier accepté à ITiCSE 2026 (conférence "
        "ACM), pour lequel j'ai travaillé en cycles itératifs et validé des résultats de "
        "manière rigoureuse."
    ),
    "DevOps": (
        "Sur le plan technique, je maîtrise Python, SQL et Git, et j'ai développé une "
        "sensibilité aux pratiques DevOps : automatisation, conteneurisation avec Docker et "
        "déploiement cloud. Mon expérience avec les environnements distribués m'a appris à "
        "concevoir des pipelines robustes et facilement reproductibles. Je mets ces "
        "compétences en pratique chez MediLyft, une entreprise de santé numérique, où je "
        "conçois l'architecture de données et le workflow d'un chatbot pré-diagnostique, "
        "en gérant l'ensemble de la chaîne de déploiement. Au-delà de ces compétences, "
        "je co-signe un papier accepté à ITiCSE 2026 (conférence ACM), pour lequel j'ai "
        "travaillé en cycles itératifs et validé des résultats de manière rigoureuse."
    ),
    "Chef_de_Projet": (
        "Sur le plan opérationnel, j'ai développé une capacité à cadrer des projets "
        "techniques de bout en bout : identification des besoins, structuration fonctionnelle, "
        "coordination avec les équipes de développement et suivi des livrables. Ma formation "
        "MIAGE, à l'interface du technique et du métier, me prépare naturellement à ces "
        "responsabilités. Je mets ces compétences en pratique chez MediLyft, une entreprise "
        "de santé numérique, où je pilote la conception de l'architecture de données et du "
        "workflow d'un chatbot pré-diagnostique, en lien direct avec les exigences médicales "
        "et techniques. Au-delà de ces compétences, je co-signe un papier accepté à ITiCSE "
        "2026 (conférence ACM), expérience qui m'a appris à évoluer efficacement dans des "
        "environnements collaboratifs et exigeants."
    ),
    "Business_Analyst": (
        "Sur le plan technique, je maîtrise SQL et la structuration de données complexes, "
        "et j'ai développé une forte appétence pour les outils d'analyse décisionnelle comme "
        "Power Query et Power BI. Mon approche est orientée livrables : je veille à ce que "
        "chaque analyse produise une valeur opérationnelle claire pour les parties prenantes. "
        "Je mets ces compétences en pratique chez MediLyft, une entreprise de santé numérique, "
        "où je conçois l'architecture de données et le workflow d'un chatbot pré-diagnostique, "
        "en analysant les flux de données médicales pour en extraire des indicateurs pertinents. "
        "Au-delà de ces compétences, je co-signe un papier accepté à ITiCSE 2026 (conférence "
        "ACM), pour lequel j'ai travaillé en cycles itératifs et validé des résultats de "
        "manière rigoureuse."
    ),
    "Data_Analyst": (
        "Sur le plan technique, je maîtrise SQL et la structuration de données complexes, "
        "et je travaille régulièrement avec Power Query et Power BI pour produire des livrables "
        "orientés décision. Mon expérience m'a appris à combiner rigueur analytique et "
        "communication claire des résultats aux équipes métiers. Je mets ces compétences en "
        "pratique chez MediLyft, une entreprise de santé numérique, où je conçois "
        "l'architecture de données et le workflow d'un chatbot pré-diagnostique, en "
        "analysant des flux de données médicales. Au-delà de ces compétences, je co-signe "
        "un papier accepté à ITiCSE 2026 (conférence ACM), pour lequel j'ai travaillé en "
        "cycles itératifs et validé des résultats de manière rigoureuse."
    ),
    "IT_Generalist": (
        "Sur le plan technique, je maîtrise un socle généraliste — Python, SQL, Git et les "
        "API REST — que je combine à une appétence pour la coordination de projets et le "
        "dialogue entre équipes techniques et métier. Cette polyvalence me permet de "
        "m'adapter rapidement à des environnements et des missions variés. Je mets ces "
        "compétences en pratique chez MediLyft, une entreprise de santé numérique, où je "
        "conçois l'architecture de données et le workflow d'un chatbot pré-diagnostique, en "
        "assurant à la fois le développement et le suivi du projet. Au-delà de ces "
        "compétences, je co-signe un papier accepté à ITiCSE 2026 (conférence ACM), pour "
        "lequel j'ai travaillé en cycles itératifs et validé des résultats de manière "
        "rigoureuse."
    ),
}


def calcular_score_global(infos):
    """Calcule le score global pondéré à partir de infos['compatibilite']."""
    compat = infos.get("compatibilite", {})
    score_global = 0.0
    for cle, poids in POIDS.items():
        if cle in compat:
            score_global += compat[cle].get("score", 0) * poids
    return round(score_global, 1)
