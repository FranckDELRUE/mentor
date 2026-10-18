"""Squelette d'un nouveau Mentor : copie de ``gabarit_app/`` avec substitution des marqueurs."""

from __future__ import annotations

import re
import shutil
import unicodedata
from pathlib import Path

from mentor_socle import __version__, registre

DOSSIER_GABARIT = Path(__file__).parent / "gabarit_app"
_CODE = re.compile(r"[A-Z]{3}")


def _mots(nom: str) -> list[str]:
    """Mots du nom, sans accents ni ponctuation : « Mentor Physique-Chimie » → ``[Mentor, Physique, Chimie]``."""
    sans_accents = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode("ascii")
    return re.findall(r"[A-Za-z0-9]+", sans_accents)


def _bornes_version(version: str) -> tuple[str, str]:
    """Bornes de dépendance : ``0.1.0`` → ``(0.1, 0.2)`` ; ``1.4.2`` → ``(1.4, 2.0)``."""
    majeur, mineur = (int(x) for x in version.split(".")[:2])
    return f"{majeur}.{mineur}", (f"0.{mineur + 1}" if majeur == 0 else f"{majeur + 1}.0")


def _port_libre(code: str) -> int:
    """Port réservé au code s'il est connu ; sinon le premier port au-dessus de tous ceux déjà attribués."""
    connu = registre.CODES_CONNUS.get(code)
    if connu:
        return connu[1]
    pris = {p for _, p in registre.CODES_CONNUS.values()} | {e.port for e in registre.lire().values()}
    return max(pris) + 1


def creer_projet(code: str, nom: str, dossier: Path | str, port: int | None = None) -> Path:
    """Crée le projet d'un nouveau Mentor dans ``dossier`` et rend ce dossier.

    ``code`` : trois majuscules (écrit dans chaque QR) ; ``nom`` : nom affiché. Lève ``ValueError`` si le code
    ou le nom est invalide, ``FileExistsError`` si ``dossier`` existe et n'est pas vide.
    """
    if not _CODE.fullmatch(code):
        raise ValueError(f"code invalide : {code!r} (trois majuscules attendues)")
    mots = _mots(nom)
    if not mots:
        raise ValueError(f"nom invalide : {nom!r}")
    dossier = Path(dossier)
    if dossier.exists() and any(dossier.iterdir()):
        raise FileExistsError(f"{dossier} existe déjà et n'est pas vide")
    mini, maxi = _bornes_version(__version__)
    remplacements = {
        "__PROJET__": "-".join(m.lower() for m in mots),
        "__PAQUET__": "_".join(m.lower() for m in mots),
        "__CLASSE__": "".join(m[0].upper() + m[1:] for m in mots),
        "__NOM__": nom,
        "__CODE__": code,
        "__code__": code.lower(),
        "__PORT__": str(port if port is not None else _port_libre(code)),
        "__VERSION_MIN__": mini,
        "__VERSION_MAX__": maxi,
    }

    def substituer(texte: str) -> str:
        for marqueur, valeur in remplacements.items():
            texte = texte.replace(marqueur, valeur)
        return texte

    for source in sorted(DOSSIER_GABARIT.rglob("*")):
        if not source.is_file() or "__pycache__" in source.parts:
            continue
        relatif = Path(*(substituer(p) for p in source.relative_to(DOSSIER_GABARIT).parts))
        cible = dossier / relatif
        cible.parent.mkdir(parents=True, exist_ok=True)
        try:
            texte = source.read_text(encoding="utf-8")
        except UnicodeDecodeError:  # fichier binaire : copié tel quel
            shutil.copyfile(source, cible)
        else:
            cible.write_text(substituer(texte), encoding="utf-8", newline="")
    return dossier
