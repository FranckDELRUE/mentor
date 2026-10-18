"""Cycle de vie des feuilles : création, vérification, impression."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mentor_socle.db import js
from mentor_socle.impression import portes, typst_rendu
from mentor_socle.impression.portes import ResultatPorte

if TYPE_CHECKING:
    from mentor_socle.contexte import Contexte


class FeuilleNonPrete(RuntimeError):
    """Impression refusée : la feuille n'est ni « prete » ni « imprimee »."""


def _annee_rentree(ctx: Contexte) -> str:
    """Année de rentrée sur deux chiffres (``2026-2027`` → ``26``)."""
    m = re.match(r"\s*(\d{4})", ctx.settings.eleve.annee_scolaire)
    if not m:
        raise ValueError(f"année scolaire illisible : {ctx.settings.eleve.annee_scolaire!r}")
    return m.group(1)[2:]


def nouveau_code(ctx: Contexte) -> str:
    """Prochain code de feuille, ex. ``TST-26-0001`` (code, année de rentrée, numéro)."""
    prefixe = f"{ctx.discipline.code}-{_annee_rentree(ctx)}-"
    derniers = ctx.cx.execute("SELECT code FROM feuilles WHERE code LIKE ?", (prefixe + "%",)).fetchall()
    numeros = [int(c[0][len(prefixe):]) for c in derniers if c[0][len(prefixe):].isdigit()]
    return f"{prefixe}{max(numeros, default=0) + 1:04d}"


def creer(ctx: Contexte, *, type_: str, titre: str, contenu: dict[str, Any], sources: list[str],
          chapitres: list[str] | None = None, duree_min: int | None = None,
          competences: list[str] | None = None, niveau_exigence: int | None = None,
          corrige: Any = None) -> int:
    """Crée une feuille « brouillon » et rend son identifiant."""
    ctx.cx.execute("BEGIN IMMEDIATE")  # le code se calcule et s'écrit sans qu'un autre l'attribue
    try:
        cur = ctx.cx.execute(
            "INSERT INTO feuilles (code, type, titre, chapitres, competences, niveau_exigence, contenu, "
            "corrige, sources, duree_min) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (nouveau_code(ctx), type_, titre, js(chapitres or []), js(competences or []), niveau_exigence,
             js(contenu), None if corrige is None else js(corrige), js(sources), duree_min))
        ctx.cx.execute("COMMIT")
    except Exception:
        ctx.cx.execute("ROLLBACK")
        raise
    return int(cur.lastrowid)


def verifier(ctx: Contexte, feuille_id: int) -> list[ResultatPorte]:
    """Passe les portes du socle et de la discipline (voir ``portes.passer``)."""
    return portes.passer(ctx, feuille_id)


def imprimer(ctx: Contexte, feuille_id: int) -> Path:
    """Rend le PDF d'une feuille « prete » (ou déjà « imprimee ») et le consigne."""
    ligne = ctx.cx.execute("SELECT * FROM feuilles WHERE id = ?", (feuille_id,)).fetchone()
    if ligne is None:
        raise KeyError(f"feuille inconnue : {feuille_id}")
    feuille = dict(ligne)
    if feuille["statut"] not in ("prete", "imprimee"):
        raise FeuilleNonPrete(
            f"La feuille {feuille['code']} est « {feuille['statut']} » : elle doit être « prete » pour s'imprimer.")
    sortie = ctx.data / "feuilles" / f"{feuille['code']}.pdf"
    typst_rendu.rendre_pdf(ctx, feuille, sortie)
    ctx.cx.execute(
        "UPDATE feuilles SET statut = 'imprimee', pdf = ?, "
        "imprime_le = strftime('%Y-%m-%dT%H:%M:%S','now','localtime') WHERE id = ?",
        (str(sortie), feuille_id))
    return sortie
