"""Rendu PDF d'une feuille avec Typst (deux passes pour imprimer le bon « page n / total »)."""

from __future__ import annotations

import datetime as dt
import json
import shutil
import tempfile
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pymupdf
import typst

from mentor_socle.db import dejs
from mentor_socle.scan import qr

if TYPE_CHECKING:
    from mentor_socle.contexte import Contexte

QR_PROVISOIRES = 12


def _gabarit_socle(nom: str) -> str:
    return (resources.files("mentor_socle.impression") / "gabarits" / nom).read_text(encoding="utf-8")


def choisir_gabarit(ctx: Contexte, type_: str) -> str:
    """Source Typst : ``templates/<type>.typ`` > ``templates/feuille.typ`` > gabarit du socle."""
    dossier = ctx.discipline.dossier_gabarits
    for nom in (f"{type_}.typ", "feuille.typ"):
        if (dossier / nom).is_file():
            return (dossier / nom).read_text(encoding="utf-8")
    return _gabarit_socle("feuille.typ")


def _donnees(ctx: Contexte, feuille: dict[str, Any], qr_max: int) -> dict[str, Any]:
    d = ctx.discipline
    donnees = dict(d.contexte_feuille(feuille))  # extras de la discipline ; les clés du socle priment
    donnees.update({
        "titre": feuille["titre"] or feuille["code"],
        "code": feuille["code"],
        "type": feuille["type"],
        "app": {"code": d.code, "nom": d.nom},
        "eleve": ctx.settings.eleve.prenom,
        "date": dt.date.today().strftime("%d/%m/%Y"),
        "duree_min": feuille.get("duree_min"),
        "qr_max": qr_max,
        "contenu": dejs(feuille.get("contenu"), {}),
    })
    return donnees


def _preparer(ctx: Contexte, feuille: dict[str, Any], dossier: Path) -> None:
    """Copie les fichiers de ``templates/`` (fonds, schémas), puis la bibliothèque et le gabarit."""
    source = ctx.discipline.dossier_gabarits
    if source.is_dir():
        for element in source.iterdir():
            if element.name == "web":
                continue
            if element.is_dir():
                shutil.copytree(element, dossier / element.name, dirs_exist_ok=True)
            else:
                shutil.copy2(element, dossier / element.name)
    (dossier / "mentor.typ").write_text(_gabarit_socle("mentor.typ"), encoding="utf-8")
    (dossier / "principal.typ").write_text(choisir_gabarit(ctx, feuille["type"]), encoding="utf-8")


def _compiler(ctx: Contexte, feuille: dict[str, Any], dossier: Path, total: int, qr_max: int) -> bytes:
    for page in range(1, qr_max + 1):
        texte = qr.encoder(ctx.discipline.code, feuille["code"], min(page, total), total)
        (dossier / f"qr-{page}.svg").write_text(qr.svg(texte), encoding="utf-8")
    (dossier / "donnees.json").write_text(
        json.dumps(_donnees(ctx, feuille, qr_max), ensure_ascii=False), encoding="utf-8")
    # root = dossier temporaire : aucun fichier extérieur n'est lisible depuis le contenu (``eval``)
    return typst.compile(str(dossier / "principal.typ"), root=str(dossier))


def rendre_pdf(ctx: Contexte, feuille: dict[str, Any], sortie: Path | str) -> int:
    """Écrit le PDF de la feuille dans ``sortie`` et rend son nombre de pages.

    Première passe : QR provisoires pour compter les pages ; seconde : « page n / total » exact.
    """
    sortie = Path(sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mentor-typst-") as tmp:
        dossier = Path(tmp)
        _preparer(ctx, feuille, dossier)
        brouillon = _compiler(ctx, feuille, dossier, QR_PROVISOIRES, QR_PROVISOIRES)
        with pymupdf.open(stream=brouillon, filetype="pdf") as doc:
            total = doc.page_count
        pdf = _compiler(ctx, feuille, dossier, total, total)
    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        if doc.page_count != total:
            raise RuntimeError(f"pagination instable ({total} puis {doc.page_count} pages)")
    sortie.write_bytes(pdf)
    return total
