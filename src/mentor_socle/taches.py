"""File de tâches SQLite, travailleur en arrière-plan et validations parentales."""

from __future__ import annotations

import logging
import threading
import traceback
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from mentor_socle.db import dejs, js

if TYPE_CHECKING:
    import sqlite3

    from mentor_socle.contexte import Contexte

log = logging.getLogger(__name__)

Gestionnaire = Callable[["Contexte", dict[str, Any], int], Any]


class AValider(Exception):
    """Levée par un gestionnaire quand le résultat doit être tranché par le parent."""

    def __init__(self, motif: str, resultat: Any = None) -> None:
        super().__init__(motif)
        self.motif = motif
        self.resultat = resultat


def ajouter(cx: sqlite3.Connection, type_: str, payload: dict[str, Any] | None = None, *,
            priorite: int = 5, max_essais: int = 2) -> int:
    """Met une tâche en file et renvoie son identifiant."""
    cur = cx.execute(
        "INSERT INTO taches (type, payload, priorite, max_essais) VALUES (?, ?, ?, ?)",
        (type_, js(payload or {}), priorite, max_essais),
    )
    return int(cur.lastrowid)


def prendre(cx: sqlite3.Connection) -> dict[str, Any] | None:
    """Prend la tâche la plus urgente, de façon atomique (une seule instruction)."""
    ligne = cx.execute(
        """
        UPDATE taches
           SET statut = 'en_cours', essais = essais + 1,
               debut_le = strftime('%Y-%m-%dT%H:%M:%S','now','localtime')
         WHERE id = (SELECT id FROM taches WHERE statut = 'en_attente'
                      ORDER BY priorite, id LIMIT 1)
        RETURNING *
        """
    ).fetchone()
    return dict(ligne) if ligne else None


def reprendre_orphelines(cx: sqlite3.Connection) -> int:
    """Remet en file les tâches restées « en_cours » (arrêt brutal) ; renvoie leur nombre."""
    return cx.execute("UPDATE taches SET statut = 'en_attente' WHERE statut = 'en_cours'").rowcount


def ouvrir_validation(cx: sqlite3.Connection, objet_type: str, objet_id: int, motif: str,
                      details: dict[str, Any] | None = None) -> int:
    """Ouvre une validation à destination du parent et renvoie son identifiant."""
    cur = cx.execute(
        "INSERT INTO validations (objet_type, objet_id, motif, details) VALUES (?, ?, ?, ?)",
        (objet_type, objet_id, motif, js(details or {})),
    )
    return int(cur.lastrowid)


def _terminer(cx: sqlite3.Connection, tid: int, statut: str, *, resultat: Any = None,
              erreur: str | None = None) -> None:
    cx.execute(
        "UPDATE taches SET statut = ?, resultat = ?, erreur = ?, "
        "fin_le = strftime('%Y-%m-%dT%H:%M:%S','now','localtime') WHERE id = ?",
        (statut, None if resultat is None else js(resultat), erreur, tid),
    )


def executer_une(ctx: Contexte, gestionnaires: Mapping[str, Gestionnaire]) -> bool:
    """Exécute la prochaine tâche ; renvoie ``False`` si la file est vide."""
    cx = ctx.cx
    tache = prendre(cx)
    if tache is None:
        return False
    tid = tache["id"]
    gestionnaire = gestionnaires.get(tache["type"])
    if gestionnaire is None:
        _terminer(cx, tid, "echec", erreur=f"Aucun gestionnaire pour le type « {tache['type']} ».")
        return True
    try:
        resultat = gestionnaire(ctx, dejs(tache["payload"]) or {}, tid)
    except AValider as demande:
        _terminer(cx, tid, "a_valider", resultat=demande.resultat)
        details = demande.resultat if isinstance(demande.resultat, dict) else {"resultat": demande.resultat}
        ouvrir_validation(cx, "tache", tid, demande.motif, details)
    except Exception:  # noqa: BLE001 - toute erreur d'un gestionnaire est consignée
        trace = traceback.format_exc()
        log.warning("Tâche %s en erreur : %s", tid, trace)
        if tache["essais"] >= tache["max_essais"]:
            _terminer(cx, tid, "echec", erreur=trace)
        else:
            cx.execute("UPDATE taches SET statut = 'en_attente', erreur = ? WHERE id = ?", (trace, tid))
    else:
        _terminer(cx, tid, "faite", resultat=resultat)
    return True


class Travailleur(threading.Thread):
    """Exécute les tâches en fond (thread démon) jusqu'à ``arreter()``."""

    def __init__(self, ctx: Contexte, gestionnaires: Mapping[str, Gestionnaire], attente_s: float = 2.0) -> None:
        super().__init__(daemon=True, name="mentor-travailleur")
        self.ctx = ctx
        self.gestionnaires = gestionnaires
        self.attente_s = attente_s
        self._arret = threading.Event()  # pas ``_stop`` : écraserait Thread._stop

    def run(self) -> None:
        try:
            reprendre_orphelines(self.ctx.cx)
        except Exception:
            log.exception("Reprise des tâches orphelines impossible : le travailleur s'arrête")
            raise
        while not self._arret.is_set():
            try:
                if executer_une(self.ctx, self.gestionnaires):
                    continue
            except Exception:
                log.exception("Erreur du travailleur")
            self._arret.wait(self.attente_s)

    def arreter(self) -> None:
        """Demande l'arrêt ; le thread termine la tâche en cours puis s'arrête."""
        self._arret.set()
