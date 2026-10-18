"""Outils de lecture et de contrôle des référentiels YAML (première partie ; le kit complet : lot 9)."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Anomalie:
    """Un défaut relevé dans un référentiel ; ``niveau`` : ``erreur`` ou ``alerte``."""

    niveau: str
    fichier: str
    message: str

    def __str__(self) -> str:
        return f"[{self.niveau.upper()}] {self.fichier} : {self.message}"


def charger_yaml(chemin: Path | str) -> Any:
    """Lit un fichier YAML en UTF-8 ; un fichier vide donne ``{}``."""
    contenu = yaml.safe_load(Path(chemin).read_text(encoding="utf-8"))
    return {} if contenu is None else contenu


def nombre(valeur: float | str) -> float:
    """Convertit en flottant un nombre venant d'un référentiel (``6.4e9`` et ``1/4`` compris).

    PyYAML (YAML 1.1) lit ``6.4e9`` comme une chaîne : toute valeur numérique passe par ici.
    """
    if isinstance(valeur, bool):
        raise TypeError(f"nombre attendu, reçu {valeur!r}")
    if isinstance(valeur, (int, float)):
        return float(valeur)
    texte = str(valeur).strip().replace(",", ".")
    if "/" in texte:
        return float(Fraction(texte))
    return float(texte)


def ids_uniques(elements: Iterable[dict[str, Any]], cle: str, fichier: str) -> list[Anomalie]:
    """Une anomalie d'erreur par identifiant porté par plusieurs éléments (ou absent)."""
    anomalies: list[Anomalie] = []
    valeurs = []
    for element in elements:
        if cle not in element:
            anomalies.append(Anomalie("erreur", fichier, f"élément sans « {cle} » : {element}"))
        else:
            valeurs.append(element[cle])
    for valeur, fois in Counter(valeurs).items():
        if fois > 1:
            anomalies.append(Anomalie("erreur", fichier, f"{cle} en double : {valeur}"))
    return anomalies


def references_connues(
    references: Iterable[str], connues: set[str], fichier: str, nature: str
) -> list[Anomalie]:
    """Une anomalie d'erreur par référence absente de ``connues`` (« chapitre inconnu : z »)."""
    return [
        Anomalie("erreur", fichier, f"{nature} inconnu : {ref}")
        for ref in references
        if ref not in connues
    ]


def verifier_kit(discipline: Any, afficher: bool = True) -> int:
    """Contrôle le kit d'une discipline ; rend 0 (aucune erreur) ou 1. Les alertes ne font pas échouer."""
    from mentor_socle.llm.modeles import charger_modeles
    from mentor_socle.llm.prompts import lire_prompt
    from mentor_socle.pedagogie import erreurs

    anomalies: list[Anomalie] = []
    for fichier in sorted(discipline.dossier_referentiel.glob("*.yaml")):
        try:
            charger_yaml(fichier)
        except (yaml.YAMLError, OSError, UnicodeDecodeError) as e:
            anomalies.append(Anomalie("erreur", fichier.name, f"YAML illisible : {e}"))
    try:
        roles = set(charger_modeles(discipline.dossier_config).roles)
    except (FileNotFoundError, ValueError, yaml.YAMLError) as e:
        anomalies.append(Anomalie("erreur", "modeles.yaml", f"modèles illisibles : {e}"))
    else:
        for fichier in sorted(discipline.dossier_prompts.glob("*.md")):
            try:
                role = lire_prompt(fichier).role
            except (ValueError, yaml.YAMLError) as e:
                anomalies.append(Anomalie("erreur", fichier.name, str(e)))
                continue
            if role not in roles:
                anomalies.append(Anomalie("erreur", fichier.name, f"rôle absent de modeles.yaml : {role}"))
    if discipline.fichier_taxonomie.is_file():
        nom = discipline.fichier_taxonomie.name
        try:
            doublons = erreurs.charger(discipline.fichier_taxonomie).doublons()
            anomalies += [Anomalie("erreur", nom, f"code en double : {c}") for c in doublons]
        except Exception as e:  # noqa: BLE001 — toute taxonomie illisible est une anomalie
            anomalies.append(Anomalie("erreur", nom, f"taxonomie illisible : {e}"))
    try:
        anomalies += discipline.verifier_referentiel(discipline.charger_referentiel())
    except Exception as e:  # noqa: BLE001
        anomalies.append(Anomalie("erreur", "referentiel", f"référentiel illisible : {e}"))
    if afficher:
        for a in anomalies:
            print(a)
        if not anomalies:
            print("Kit valide.")
    return int(any(a.niveau == "erreur" for a in anomalies))
