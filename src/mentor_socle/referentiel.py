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
