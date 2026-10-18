"""Transcription des pages d'un document par le modèle de vision, une page à la fois."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from mentor_socle.db import dejs, js
from mentor_socle.llm.structure import appel_structure
from mentor_socle.taches import AValider

if TYPE_CHECKING:
    from mentor_socle.contexte import Contexte

SEUIL_CONFIANCE = 0.75


class ZoneLue(BaseModel):
    """Une zone d'une page : texte, schéma, graphique, calcul, carte, figure."""

    type: str = "texte"
    texte: str = ""
    confiance: float = Field(ge=0.0, le=1.0)
    bbox: list[float] | None = None


class PageLue(BaseModel):
    """Ce que le modèle a lu sur une page."""

    zones: list[ZoneLue] = Field(default_factory=list)


def _enregistrer_zones(ctx: Contexte, page_id: int, lue: PageLue) -> None:
    """Remplace les zones de la page (une reprise de tâche ne doit pas les doubler)."""
    ctx.cx.execute("DELETE FROM zones WHERE page_id = ?", (page_id,))
    for z in lue.zones:
        ctx.cx.execute(
            "INSERT INTO zones (page_id, type, bbox, texte_ocr, confiance) VALUES (?, ?, ?, ?, ?)",
            (page_id, z.type, None if z.bbox is None else js(z.bbox), z.texte, z.confiance))


def transcrire_document(ctx: Contexte, payload: dict[str, Any], tache_id: int) -> dict[str, Any]:
    """Gestionnaire de tâche : ``payload = {"document_id": n}``.

    Une zone de confiance inférieure à 0,75 met le document « a_valider » et ouvre une validation
    qui liste les numéros des pages concernées.
    """
    doc_id = payload["document_id"]
    doc = ctx.cx.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
    if doc is None:
        raise KeyError(f"document inconnu : {doc_id}")
    chapitres = dejs(doc["chapitres"], [])
    lexique = ctx.discipline.lexique_ocr(chapitres[0] if chapitres else None)
    douteuses: list[int] = []
    nb_zones = 0
    pages = ctx.cx.execute("SELECT id, numero, image FROM pages WHERE document_id = ? ORDER BY numero",
                           (doc_id,)).fetchall()
    for page in pages:
        lue = appel_structure(
            ctx, "transcription", PageLue, images=[page["image"]], tache_id=tache_id,
            type_document=doc["type"], numero_page=page["numero"], lexique=lexique)
        _enregistrer_zones(ctx, page["id"], lue)
        nb_zones += len(lue.zones)
        if any(z.confiance < SEUIL_CONFIANCE for z in lue.zones):
            douteuses.append(page["numero"])
    statut = "a_valider" if douteuses else "transcrit"
    ctx.cx.execute("UPDATE documents SET statut = ?, "
                   "modifie_le = strftime('%Y-%m-%dT%H:%M:%S','now','localtime') WHERE id = ?", (statut, doc_id))
    if douteuses:
        ctx.cx.execute("UPDATE copies SET statut = 'a_valider' WHERE document_id = ?", (doc_id,))
        raise AValider("Transcription peu sûre : relire les pages signalées", {"pages": douteuses})
    return {"document_id": doc_id, "pages": len(pages), "zones": nb_zones}
