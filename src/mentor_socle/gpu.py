"""Verrou GPU inter-applications : un seul Mentor à la fois utilise le GPU de la machine."""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from filelock import FileLock, Timeout

from mentor_socle.chemins import dossier_commun

_RLOCK = threading.RLock()
_profondeur = 0
_precedent_courant: dict | None = None


class GpuOccupe(TimeoutError):
    """Le GPU est tenu par une autre application ; ``detenteur`` décrit qui (ou ``None``)."""

    def __init__(self, detenteur: dict | None):
        self.detenteur = detenteur
        qui = f"{detenteur.get('app')} ({detenteur.get('tache')})" if detenteur else "inconnu"
        super().__init__(f"GPU occupé par {qui}")


def _fichier(nom: str) -> Path:
    return dossier_commun() / nom


def _lire_json(chemin: Path) -> dict | None:
    try:
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return donnees if isinstance(donnees, dict) else None


def etat() -> dict | None:
    """Détenteur courant du GPU (``app, tache, pid, depuis``), ou ``None`` si libre."""
    return _lire_json(_fichier("gpu.detenteur.json"))


def _supprimer(chemin: Path) -> None:
    try:
        chemin.unlink()
    except OSError:
        pass


@contextmanager
def verrou(app: str, tache: str, attente_s: float = 3600) -> Iterator[dict | None]:
    """Prend le GPU pour ``app``/``tache`` ; rend le détenteur précédent (``dict | None``).

    Réentrant dans un processus : seul le niveau 0 prend le verrou de fichier.
    Lève ``GpuOccupe`` si le GPU n'est pas libéré avant ``attente_s`` secondes.
    """
    global _profondeur, _precedent_courant
    debut = datetime.now()
    if not _RLOCK.acquire(timeout=attente_s):
        raise GpuOccupe(etat())
    try:
        if _profondeur > 0:
            _profondeur += 1
            try:
                yield _precedent_courant
            finally:
                _profondeur -= 1
            return
        fichier = FileLock(str(_fichier("gpu.lock")))
        try:
            fichier.acquire(timeout=attente_s)
        except Timeout:
            raise GpuOccupe(etat()) from None
        try:
            # Un détenteur resté en place est celui d'un processus disparu : il est le précédent.
            precedent = etat() or _lire_json(_fichier("gpu.detenteur.precedent.json"))
            courant = {
                "app": app,
                "tache": tache,
                "pid": os.getpid(),
                "depuis": debut.astimezone().isoformat(timespec="seconds"),
            }
            _fichier("gpu.detenteur.json").write_text(
                json.dumps(courant, ensure_ascii=False), encoding="utf-8"
            )
            _profondeur = 1
            _precedent_courant = precedent
            try:
                yield precedent
            finally:
                _profondeur = 0
                _precedent_courant = None
                _fichier("gpu.detenteur.precedent.json").write_text(
                    json.dumps(courant, ensure_ascii=False), encoding="utf-8"
                )
                _supprimer(_fichier("gpu.detenteur.json"))
        finally:
            fichier.release()
    finally:
        _RLOCK.release()
