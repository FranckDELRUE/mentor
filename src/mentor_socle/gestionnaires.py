"""Gestionnaires de tâches fournis par le socle, puis ceux de la discipline."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mentor_socle.scan.transcription import transcrire_document
from mentor_socle.taches import Gestionnaire

if TYPE_CHECKING:
    from mentor_socle.contexte import Contexte


def socle() -> dict[str, Gestionnaire]:
    """Tâches du socle (sauvegarde et indexation s'ajouteront aux lots suivants)."""
    return {"transcrire_document": transcrire_document}


def tous(ctx: Contexte) -> dict[str, Gestionnaire]:
    """Socle puis discipline : la discipline peut remplacer un gestionnaire du socle par homonymie."""
    return {**socle(), **ctx.discipline.gestionnaires()}
