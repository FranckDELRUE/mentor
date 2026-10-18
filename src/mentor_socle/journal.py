"""Journal applicatif : fichier tournant dans le dossier donné."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

NOM = "mentor"


def configurer(dossier: Path | str, niveau: int = logging.INFO) -> logging.Logger:
    """Branche ``mentor.log`` (1 Mo × 5 fichiers, UTF-8) sur le logger ``mentor`` ; idempotent par dossier."""
    dossier = Path(dossier)
    dossier.mkdir(parents=True, exist_ok=True)
    fichier = (dossier / "mentor.log").resolve()
    logger = logging.getLogger(NOM)
    logger.setLevel(niveau)
    for h in logger.handlers:
        if isinstance(h, RotatingFileHandler) and Path(h.baseFilename) == fichier:
            return logger
    h = RotatingFileHandler(fichier, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s : %(message)s"))
    logger.addHandler(h)
    return logger
