"""Boîte de dépôt des scans : dédoublonnage, pages redressées, QR, renvoi vers un autre Mentor."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mentor_socle import registre, taches
from mentor_socle.db import js
from mentor_socle.scan import image, qr

if TYPE_CHECKING:
    from mentor_socle.contexte import Contexte

_IGNORES = {"desktop.ini", "thumbs.db"}
_ACCEPTES = image.EXTENSIONS_IMAGE | {".pdf"}

_PageLue = tuple[Any, float, list[qr.InfoQR]]  # (image redressée, angle corrigé, QR Mentor trouvés)


@dataclass
class BilanInbox:
    """Résultat d'un passage sur la boîte de dépôt."""

    recus: list[int] = field(default_factory=list)                  # identifiants de documents
    doublons: list[str] = field(default_factory=list)               # noms de fichiers
    renvoyes: list[tuple[str, str]] = field(default_factory=list)   # (nom de fichier, code du Mentor)
    illisibles: list[str] = field(default_factory=list)             # noms de fichiers


def sha256(fichier: Path | str) -> str:
    """Empreinte SHA-256 du contenu d'un fichier."""
    h = hashlib.sha256()
    with open(fichier, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def _deplacer(fichier: Path, dossier: Path) -> Path:
    """Déplace ``fichier`` dans ``dossier`` sans écraser un homonyme."""
    dossier.mkdir(parents=True, exist_ok=True)
    cible = dossier / fichier.name
    n = 1
    while cible.exists():
        n += 1
        cible = dossier / f"{fichier.stem}-{n}{fichier.suffix}"
    return Path(shutil.move(str(fichier), str(cible)))


def _lire_pages(fichier: Path) -> list[_PageLue]:
    """Pages redressées et QR de chacune ; ``ValueError`` si le fichier n'est pas exploitable."""
    if fichier.suffix.lower() not in _ACCEPTES:
        raise ValueError(f"type de fichier non pris en charge : {fichier.suffix or '(sans extension)'}")
    try:
        brutes = image.pages(fichier)
    except Exception as e:  # PDF ou image corrompus : les causes sont multiples
        raise ValueError(f"fichier illisible : {e}") from e
    if not brutes:
        raise ValueError("fichier sans page")
    resultat: list[_PageLue] = []
    for brute in brutes:
        redressee, angle = image.redresser(brute)
        codes = qr.lire(redressee) or (qr.lire(brute) if angle else [])
        resultat.append((redressee, angle, codes))
    return resultat


def ingerer_fichier(ctx: Contexte, fichier: Path | str, type_document: str | None = None,
                    date_document: str | None = None) -> tuple[str, Any]:
    """Range un scan ; rend ``(statut, valeur)``.

    - ``("recu", id_document)`` : document créé, pages enregistrées, transcription mise en file
      (ou validation « Type de document à préciser » si le type est inconnu) ;
    - ``("doublon", id_existant)`` : même contenu déjà reçu, fichier déplacé dans ``_doublons`` ;
    - ``("renvoye", code)`` : feuille d'un autre Mentor installé, fichier déplacé dans sa boîte ;
    - ``("illisible", motif)`` : fichier déplacé dans ``_illisibles``.
    """
    fichier = Path(fichier)
    inbox = ctx.settings.chemins.inbox
    empreinte = sha256(fichier)
    existant = ctx.cx.execute("SELECT id FROM documents WHERE empreinte_sha256 = ?", (empreinte,)).fetchone()
    if existant:
        _deplacer(fichier, inbox / "_doublons")
        return "doublon", existant[0]
    try:
        pages = _lire_pages(fichier)
    except ValueError as e:
        _deplacer(fichier, inbox / "_illisibles")
        return "illisible", str(e)

    info = next((c[0] for _, _, c in pages if c), None)
    if info and info.app != ctx.discipline.code:
        autre = registre.lire().get(info.app)
        if autre:  # un code absent du registre n'est pas renvoyé : scan sans feuille reconnue
            _deplacer(fichier, Path(autre.inbox))
            return "renvoye", info.app

    feuille = None
    if info and info.app == ctx.discipline.code:
        ligne = ctx.cx.execute("SELECT * FROM feuilles WHERE code = ?", (info.feuille,)).fetchone()
        feuille = dict(ligne) if ligne else None
    type_final = type_document or ("copie_mentor" if feuille else "a_classer")
    return "recu", _creer_document(ctx, fichier, pages, empreinte, type_final, date_document, feuille)


def _creer_document(ctx: Contexte, fichier: Path, pages: list[_PageLue], empreinte: str, type_: str,
                    date_document: str | None, feuille: dict[str, Any] | None) -> int:
    """Crée le document, ses pages et la suite à donner, en une transaction."""
    cx = ctx.cx
    meta = {"nom_origine": fichier.name, **({"feuille": feuille["code"]} if feuille else {})}
    classe = type_ != "a_classer"
    cx.execute("BEGIN IMMEDIATE")
    original: Path | None = None
    dossier: Path | None = None
    try:
        doc_id = int(cx.execute(
            "INSERT INTO documents (type, date_document, fichier_source, empreinte_sha256, statut, meta) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (type_, date_document, str(fichier), empreinte, "pretraite" if classe else "recu", js(meta)),
        ).lastrowid)
        dossier = ctx.data / "scans" / str(doc_id)
        for numero, (img, angle, codes) in enumerate(pages, start=1):
            chemin = image.enregistrer(img, dossier / f"page-{numero:02d}.png")
            code = codes[0] if codes else None
            cx.execute(
                "INSERT INTO pages (document_id, numero, image, qr, redressee) VALUES (?, ?, ?, ?, ?)",
                (doc_id, numero, str(chemin),
                 js({"app": code.app, "feuille": code.feuille, "page": code.page, "total": code.total})
                 if code else None, int(bool(angle))))
        original = _deplacer(fichier, dossier / "original")
        cx.execute("UPDATE documents SET fichier_source = ? WHERE id = ?", (str(original), doc_id))
        if feuille:
            cx.execute("UPDATE feuilles SET statut = 'rendue' WHERE id = ? AND statut IN ('prete', 'imprimee')",
                       (feuille["id"],))
            cx.execute("INSERT INTO copies (feuille_id, document_id) VALUES (?, ?)", (feuille["id"], doc_id))
        if classe:
            taches.ajouter(cx, "transcrire_document", {"document_id": doc_id})
        else:
            taches.ouvrir_validation(cx, "document", doc_id, "Type de document à préciser",
                                     {"fichier": fichier.name})
        cx.execute("COMMIT")
    except Exception:
        cx.execute("ROLLBACK")
        if original is not None and original.exists():
            shutil.move(str(original), str(fichier))  # le scan reste dans la boîte
        if dossier is not None:
            shutil.rmtree(dossier, ignore_errors=True)
        raise
    return doc_id


def scanner(ctx: Contexte) -> BilanInbox:
    """Traite tous les fichiers déposés à la racine de la boîte (les dossiers ``_…`` sont ignorés)."""
    bilan = BilanInbox()
    dossier = ctx.settings.chemins.inbox
    if not dossier.is_dir():
        return bilan
    for fichier in sorted(p for p in dossier.iterdir() if p.is_file()):
        if fichier.name.startswith((".", "~")) or fichier.name.lower() in _IGNORES:
            continue
        statut, valeur = ingerer_fichier(ctx, fichier)
        if statut == "recu":
            bilan.recus.append(valeur)
        elif statut == "doublon":
            bilan.doublons.append(fichier.name)
        elif statut == "renvoye":
            bilan.renvoyes.append((fichier.name, valeur))
        else:
            bilan.illisibles.append(fichier.name)
    return bilan
