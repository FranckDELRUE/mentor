"""Répétition espacée de Leitner : six boîtes, réussite = boîte +1, échec = retour en boîte 1."""

from __future__ import annotations

import datetime as dt
import sqlite3

from mentor_socle.db import dejs, js

INTERVALLES = (1, 3, 7, 16, 35, 80)


def _jour(jour: dt.date | None) -> dt.date:
    return jour or dt.date.today()


def ajouter(cx: sqlite3.Connection, recto: str, verso: str, source: str,
            chapitre: str | None = None, jour: dt.date | None = None) -> int:
    """Crée une carte en boîte 1, à revoir dès ``jour`` ; rend son identifiant."""
    cur = cx.execute(
        "INSERT INTO cartes (recto, verso, source, chapitre, boite, prochaine_revue) VALUES (?, ?, ?, ?, 1, ?)",
        (recto, verso, source, chapitre, _jour(jour).isoformat()),
    )
    return int(cur.lastrowid)


def a_reviser(cx: sqlite3.Connection, jour: dt.date | None = None,
              chapitres: list[str] | None = None) -> list[sqlite3.Row]:
    """Cartes non suspendues dont la revue est échue, les plus en retard d'abord."""
    sql = "SELECT * FROM cartes WHERE suspendue = 0 AND prochaine_revue <= ?"
    params: list[object] = [_jour(jour).isoformat()]
    if chapitres is not None:
        sql += f" AND chapitre IN ({','.join('?' * len(chapitres))})"
        params += list(chapitres)
    return cx.execute(sql + " ORDER BY prochaine_revue, id", params).fetchall()


def reviser(cx: sqlite3.Connection, carte_id: int, reussite: bool, jour: dt.date | None = None) -> dt.date:
    """Enregistre une revue et rend la date de la prochaine."""
    jour = _jour(jour)
    carte = cx.execute("SELECT boite, historique FROM cartes WHERE id = ?", (carte_id,)).fetchone()
    if carte is None:
        raise ValueError(f"carte inconnue : {carte_id}")
    boite = min(carte["boite"] + 1, len(INTERVALLES)) if reussite else 1
    prochaine = jour + dt.timedelta(days=INTERVALLES[boite - 1])
    historique = dejs(carte["historique"], [])
    historique.append({"date": jour.isoformat(), "reussite": bool(reussite), "boite": boite})
    cx.execute("UPDATE cartes SET boite = ?, prochaine_revue = ?, historique = ? WHERE id = ?",
               (boite, prochaine.isoformat(), js(historique), carte_id))
    return prochaine
