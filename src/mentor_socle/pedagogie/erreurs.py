"""Erreurs de l'élève : taxonomie commune, enregistrement vérifié, erreurs récurrentes et tendance."""

from __future__ import annotations

import datetime as dt
import sqlite3
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, create_model

from mentor_socle.referentiel import charger_yaml

FENETRE_JOURS = 42
SEUIL = 3


@dataclass(frozen=True)
class TypeErreur:
    code: str
    libelle: str = ""
    famille: str = ""
    gravite: int = 2


class Taxonomie:
    """Liste des types d'erreurs d'une discipline."""

    def __init__(self, entrees: list[TypeErreur]):
        self.entrees = entrees
        self._par_code = {e.code: e for e in reversed(entrees)}  # en cas de doublon, la première gagne

    def codes(self) -> set[str]:
        return set(self._par_code)

    def doublons(self) -> list[str]:
        """Codes déclarés plus d'une fois (signalés par la vérification du kit)."""
        vus: set[str] = set()
        doubles: set[str] = set()
        for e in self.entrees:
            if e.code in vus:
                doubles.add(e.code)
            vus.add(e.code)
        return sorted(doubles)

    def modele_erreur(self) -> type[BaseModel]:
        """Modèle Pydantic d'une erreur relevée dont ``code`` est limité aux codes de la taxonomie.

        À utiliser dans le schéma de sortie d'un appel au modèle : le schéma JSON transmis à Ollama
        énumère les codes permis (décodage contraint), et toute valeur hors liste est rejetée à la
        validation puis réparée par ``appel_structure``.
        """
        if not self._par_code:
            raise ValueError("taxonomie vide : aucun code à proposer au modèle")
        return create_model(
            "ErreurRelevee",
            code=(Literal[tuple(sorted(self._par_code))], ...),
            chapitre=(str | None, None),
            competence=(str | None, None),
            extrait=(str | None, None),
        )

    def pour_prompt(self) -> str:
        """Liste lisible des codes permis (``code : libellé [famille]``), à insérer dans le prompt."""
        return "\n".join(f"- {e.code} : {e.libelle} [{e.famille}]" for e in self._par_code.values())

    def __getitem__(self, code: str) -> TypeErreur:
        return self._par_code[code]

    def __contains__(self, code: object) -> bool:
        return code in self._par_code

    def __iter__(self) -> Iterator[TypeErreur]:
        return iter(self.entrees)

    def __len__(self) -> int:
        return len(self.entrees)


def charger(fichier: Path | str) -> Taxonomie:
    """Lit ``taxonomie_erreurs.yaml`` (clé ``erreurs`` : liste de ``code``, ``libelle``, ``famille``, ``gravite``)."""
    brut = charger_yaml(fichier).get("erreurs") or []
    return Taxonomie([
        TypeErreur(str(e["code"]), str(e.get("libelle", "")), str(e.get("famille", "")), int(e.get("gravite", 2)))
        for e in brut
    ])


def enregistrer(cx: sqlite3.Connection, copie_id: int | None, erreurs: list[dict[str, Any]],
                taxonomie: Taxonomie, jour: dt.date | None = None) -> int:
    """Enregistre des erreurs relevées ; refuse (``ValueError``, rien d'écrit) tout code hors taxonomie.

    Chaque erreur : ``code`` (obligatoire), ``chapitre``, ``competence``, ``extrait``, ``gravite``
    (défaut : celle de la taxonomie). Rend le nombre de lignes écrites.
    """
    inconnus = sorted({str(e.get("code")) for e in erreurs if e.get("code") not in taxonomie})
    if inconnus:
        raise ValueError(f"codes d'erreur hors taxonomie : {', '.join(inconnus)}")
    date = (jour or dt.date.today()).isoformat()
    cx.execute("SAVEPOINT erreurs")
    try:
        for e in erreurs:
            cx.execute(
                "INSERT INTO erreurs (copie_id, code, chapitre, competence, extrait, gravite, date)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (copie_id, e["code"], e.get("chapitre"), e.get("competence"), e.get("extrait"),
                 int(e.get("gravite") or taxonomie[e["code"]].gravite), date),
            )
    except BaseException:
        cx.execute("ROLLBACK TO erreurs")
        cx.execute("RELEASE erreurs")
        raise
    cx.execute("RELEASE erreurs")
    return len(erreurs)


def recurrentes(cx: sqlite3.Connection, jour: dt.date | None = None, fenetre: int = FENETRE_JOURS,
                seuil: int = SEUIL) -> list[dict[str, Any]]:
    """Codes d'erreur survenus au moins ``seuil`` fois dans la fenêtre, avec leur tendance.

    Tendance : « recul » si les erreurs de la moitié récente ×2 ≤ celles de la moitié ancienne,
    « hausse » si elles sont plus nombreuses, « stable » sinon. Tri : fréquence décroissante.
    """
    jour = jour or dt.date.today()
    debut = jour - dt.timedelta(days=fenetre)
    milieu = jour - dt.timedelta(days=fenetre // 2)
    lignes = cx.execute(
        """SELECT code, COUNT(*) AS nb, MAX(gravite) AS gravite,
                  SUM(date >= ?) AS recentes, SUM(date < ?) AS anciennes
           FROM erreurs WHERE date >= ? AND date <= ? GROUP BY code HAVING COUNT(*) >= ?""",
        (milieu.isoformat(), milieu.isoformat(), debut.isoformat(), jour.isoformat(), seuil),
    ).fetchall()
    resultat = []
    for r in lignes:
        recentes, anciennes = r["recentes"], r["anciennes"]
        if recentes * 2 <= anciennes:
            tendance = "recul"
        elif recentes > anciennes:
            tendance = "hausse"
        else:
            tendance = "stable"
        resultat.append({"code": r["code"], "nb": r["nb"], "gravite": r["gravite"],
                         "recentes": recentes, "anciennes": anciennes, "tendance": tendance})
    resultat.sort(key=lambda d: (-d["nb"], d["code"]))
    return resultat
