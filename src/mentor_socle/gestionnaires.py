"""Gestionnaires de tâches fournis par le socle, puis ceux de la discipline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mentor_socle.corpus import indexer
from mentor_socle.sauvegarde import gestionnaire_sauvegarde
from mentor_socle.scan.transcription import transcrire_document
from mentor_socle.taches import Gestionnaire

if TYPE_CHECKING:
    from mentor_socle.contexte import Contexte


def _indexer_corpus(ctx: Contexte, payload: dict, tache_id: int) -> dict:
    return {"indexes": indexer(ctx)}


def socle() -> dict[str, Gestionnaire]:
    """Tâches du socle : transcription, sauvegarde, indexation du corpus."""
    return {
        "transcrire_document": transcrire_document,
        "sauvegarde": gestionnaire_sauvegarde,
        "indexer_corpus": _indexer_corpus,
    }


def tous(ctx: Contexte) -> dict[str, Gestionnaire]:
    """Socle puis discipline : la discipline peut remplacer un gestionnaire du socle par homonymie."""
    return {**socle(), **ctx.discipline.gestionnaires()}
