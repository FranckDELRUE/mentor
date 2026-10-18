"""Modèle de l'élève : maîtrise et incertitude par compétence (mise à jour de type filtre de Kalman)."""

from __future__ import annotations

import datetime as dt
import math
import sqlite3
from typing import Any

MAITRISE_DEFAUT = 0.5
INCERTITUDE_DEFAUT = 0.35
INCERTITUDE_MIN = 0.05
BRUIT_BASE = 0.25
DERIVE_JOUR = 0.004


def _jour(jour: dt.date | None) -> dt.date:
    return jour or dt.date.today()


def _deriver(incertitude: float, depuis: str | None, jour: dt.date) -> float:
    """L'incertitude remonte avec le temps écoulé sans observation."""
    if not depuis:
        return incertitude
    jours = max(0, (jour - dt.date.fromisoformat(depuis)).days)
    return min(INCERTITUDE_DEFAUT, math.sqrt(incertitude**2 + DERIVE_JOUR**2 * jours * 10))


def observer(cx: sqlite3.Connection, code: str, score: float, poids: float = 1.0,
             chapitre: str | None = None, jour: dt.date | None = None) -> tuple[float, float]:
    """Intègre une observation ``score`` ∈ [0, 1] ; rend ``(maîtrise, incertitude)``."""
    if not 0.0 <= score <= 1.0:
        raise ValueError(f"score hors de [0, 1] : {score}")
    if poids < 0:
        raise ValueError(f"poids négatif : {poids}")
    jour = _jour(jour)
    ligne = cx.execute("SELECT maitrise, incertitude, nb_observations, maj_le FROM competences WHERE code = ?",
                       (code,)).fetchone()
    if ligne:
        m, u, n = ligne["maitrise"], ligne["incertitude"], ligne["nb_observations"]
        u = _deriver(u, ligne["maj_le"], jour)
    else:
        m, u, n = MAITRISE_DEFAUT, INCERTITUDE_DEFAUT, 0
    bruit = BRUIT_BASE / math.sqrt(max(poids, 0.05))
    gain = u**2 / (u**2 + bruit**2)
    m += gain * (score - m)
    u = max(INCERTITUDE_MIN, math.sqrt(1 - gain) * u)
    cx.execute(
        """INSERT INTO competences (code, chapitre, maitrise, incertitude, nb_observations, maj_le)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(code) DO UPDATE SET chapitre = COALESCE(excluded.chapitre, competences.chapitre),
               maitrise = excluded.maitrise, incertitude = excluded.incertitude,
               nb_observations = excluded.nb_observations, maj_le = excluded.maj_le""",
        (code, chapitre, m, u, n + 1, jour.isoformat()),
    )
    return m, u


def priorites(cx: sqlite3.Connection, chapitres: list[str] | None = None, jour: dt.date | None = None,
              limite: int | None = None) -> list[dict[str, Any]]:
    """Compétences à travailler d'abord : ``(1 − maîtrise) + 0,5·incertitude`` décroissant.

    L'incertitude rendue tient compte de la dérive due au temps ; la base n'est pas modifiée.
    """
    jour = _jour(jour)
    sql = "SELECT * FROM competences"
    params: list[object] = []
    if chapitres is not None:
        sql += f" WHERE chapitre IN ({','.join('?' * len(chapitres))})"
        params = list(chapitres)
    resultat = []
    for ligne in cx.execute(sql, params):
        d = dict(ligne)
        d["incertitude"] = _deriver(d["incertitude"], d["maj_le"], jour)
        d["priorite"] = (1 - d["maitrise"]) + 0.5 * d["incertitude"]
        resultat.append(d)
    resultat.sort(key=lambda d: (-d["priorite"], d["code"]))
    return resultat[:limite] if limite is not None else resultat
