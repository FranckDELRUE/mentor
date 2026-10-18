"""Registre des Mentor installés sur la machine (``apps.json`` dans le dossier commun)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from filelock import FileLock

from mentor_socle.chemins import dossier_commun

# code -> (nom, port) ; les ports sont réservés pour éviter les conflits entre Mentor.
CODES_CONNUS: dict[str, tuple[str, int]] = {
    "LET": ("Mentor Lettres", 8765),
    "MAT": ("Mentor Maths", 8766),
    "HIS": ("Mentor Histoire", 8767),
    "SVT": ("Mentor SVT", 8768),
    "PHC": ("Mentor Physique-Chimie", 8769),
    "PHI": ("Mentor Philosophie", 8770),
    "LVA": ("Mentor Langues", 8771),
}


@dataclass
class EntreeRegistre:
    """Un Mentor installé : où il vit, sur quel port, où arrivent ses scans."""

    code: str
    nom: str
    port: int
    racine: str
    inbox: str
    version_socle: str


def _fichier() -> Path:
    return dossier_commun() / "apps.json"


def lire() -> dict[str, EntreeRegistre]:
    """Contenu du registre, indexé par code ; vide si le fichier manque ou est illisible."""
    try:
        brut = json.loads(_fichier().read_text(encoding="utf-8"))
        return {code: EntreeRegistre(**e) for code, e in brut.items()}
    except (OSError, ValueError, TypeError):
        return {}


def enregistrer(
    code: str, nom: str, port: int, racine: Path | str, inbox: Path | str, version_socle: str
) -> list[str]:
    """Inscrit (ou met à jour) un Mentor ; rend les conflits de port avec les autres entrées."""
    with FileLock(str(dossier_commun() / "apps.json.lock"), timeout=30):
        entrees = lire()
        conflits = [
            f"Le port {port} est déjà utilisé par {autre.nom} ({autre.code})"
            for autre in entrees.values()
            if autre.code != code and autre.port == port
        ]
        entrees[code] = EntreeRegistre(code, nom, port, str(racine), str(inbox), version_socle)
        tmp = _fichier().with_suffix(".json.tmp")
        tmp.write_text(
            json.dumps({c: asdict(e) for c, e in entrees.items()}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(_fichier())
    return conflits
