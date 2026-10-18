"""Sauvegarde à chaud de la base (``Connection.backup``) avec rotation."""

from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mentor_socle.contexte import Contexte

_FORMAT = "%Y%m%d-%H%M%S"
_PERIODE = {"quotidienne": dt.timedelta(days=1), "hebdomadaire": dt.timedelta(days=7)}


def _prefixe(ctx: Contexte) -> str:
    return f"mentor-{ctx.discipline.code.lower()}-"


def _existantes(ctx: Contexte) -> list[Path]:
    return sorted(ctx.settings.chemins.sauvegardes.glob(f"{_prefixe(ctx)}*.sqlite3"))


def sauvegarder(ctx: Contexte) -> Path:
    """Copie cohérente de la base dans le dossier de sauvegardes, puis rotation."""
    dossier = ctx.settings.chemins.sauvegardes
    dossier.mkdir(parents=True, exist_ok=True)
    cible = dossier / f"{_prefixe(ctx)}{dt.datetime.now():{_FORMAT}}.sqlite3"
    temporaire = cible.with_suffix(".tmp")
    temporaire.unlink(missing_ok=True)
    destination = sqlite3.connect(temporaire)
    try:
        ctx.cx.backup(destination)
    finally:
        destination.close()
    temporaire.replace(cible)
    tourner(ctx)
    return cible


def tourner(ctx: Contexte) -> list[Path]:
    """Supprime les plus anciennes sauvegardes au-delà de ``conserver`` ; rend les fichiers supprimés."""
    existantes = _existantes(ctx)
    en_trop = existantes[: max(0, len(existantes) - ctx.settings.sauvegarde.conserver)]
    for f in en_trop:
        f.unlink(missing_ok=True)
    return en_trop


def derniere(ctx: Contexte) -> Path | None:
    """La sauvegarde la plus récente, ou ``None``."""
    existantes = _existantes(ctx)
    return existantes[-1] if existantes else None


def due(ctx: Contexte, maintenant: dt.datetime | None = None) -> bool:
    """Vrai si une sauvegarde automatique est attendue (aucune, ou trop ancienne)."""
    periode = _PERIODE.get(ctx.settings.sauvegarde.automatique)
    if periode is None:
        return False
    dernier = derniere(ctx)
    if dernier is None:
        return True
    try:
        quand = dt.datetime.strptime(dernier.stem.removeprefix(_prefixe(ctx)), _FORMAT)
    except ValueError:
        quand = dt.datetime.fromtimestamp(dernier.stat().st_mtime)
    return (maintenant or dt.datetime.now()) - quand >= periode


def gestionnaire_sauvegarde(ctx: Contexte, payload: dict[str, Any], tache_id: int) -> dict[str, Any]:
    """Tâche de fond « sauvegarde »."""
    return {"fichier": str(sauvegarder(ctx))}
