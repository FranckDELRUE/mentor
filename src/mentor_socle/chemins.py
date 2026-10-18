"""Chemins communs à toutes les applications Mentor de la machine."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def dossier_commun() -> Path:
    """Dossier partagé entre les Mentor (verrou GPU, registre) ; il est créé s'il manque.

    Priorité à la variable ``MENTOR_COMMUN`` ; sinon ``%LOCALAPPDATA%/mentor`` sous Windows,
    ``$XDG_STATE_HOME/mentor`` ou ``~/.local/state/mentor`` ailleurs.
    """
    surcharge = os.environ.get("MENTOR_COMMUN")
    if surcharge:
        dossier = Path(surcharge)
    elif sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA")
        dossier = (Path(base) if base else Path.home() / "AppData" / "Local") / "mentor"
    else:
        base = os.environ.get("XDG_STATE_HOME")
        dossier = (Path(base) if base else Path.home() / ".local" / "state") / "mentor"
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier
