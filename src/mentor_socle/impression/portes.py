"""Portes de vérification avant impression."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from mentor_socle import taches
from mentor_socle.db import dejs, js

if TYPE_CHECKING:
    from mentor_socle.contexte import Contexte

STATUTS_REEVALUABLES = ("brouillon", "a_valider", "prete")


@dataclass
class ResultatPorte:
    """Verdict d'une porte ; une porte non bloquante n'empêche pas l'impression."""

    porte: str
    ok: bool
    bloquante: bool = True
    messages: list[str] = field(default_factory=list)


def porte_sources(ctx: Contexte, feuille: dict[str, Any]) -> ResultatPorte:
    """Chaque source est un ``seg:<code>`` du corpus ou un ``ref:<id>`` du référentiel ; au moins une."""
    sources = dejs(feuille.get("sources"), []) or []
    messages: list[str] = []
    if not sources:
        messages.append("Aucune source : une feuille doit s'appuyer sur le cours ou le référentiel.")
    for source in sources:
        type_, _, valeur = str(source).partition(":")
        if type_ == "seg" and valeur:
            if not ctx.cx.execute("SELECT 1 FROM segments WHERE code = ?", (valeur,)).fetchone():
                messages.append(f"Segment de cours inconnu : {valeur}")
        elif type_ == "ref" and valeur:
            if not ctx.discipline.reference_existe(valeur):
                messages.append(f"Référence inconnue du référentiel : {valeur}")
        else:
            messages.append(f"Source mal formée (attendu seg:… ou ref:…) : {source}")
    return ResultatPorte("sources", not messages, True, messages)


def porte_charge(ctx: Contexte, feuille: dict[str, Any]) -> ResultatPorte:
    """Alerte (non bloquante) si la durée dépasse la séance maximale."""
    duree = feuille.get("duree_min")
    maxi = ctx.settings.charge.seance_max_min
    if duree is not None and duree > maxi:
        return ResultatPorte("charge", False, False,
                             [f"Durée prévue {duree} min, au-dessus de la séance maximale ({maxi} min)."])
    return ResultatPorte("charge", True, False)


def passer(ctx: Contexte, feuille_id: int) -> list[ResultatPorte]:
    """Passe les portes du socle puis celles de la discipline et met à jour le statut de la feuille.

    « prete » si aucune porte bloquante n'échoue ; sinon « a_valider » et une validation ouverte.
    """
    ligne = ctx.cx.execute("SELECT * FROM feuilles WHERE id = ?", (feuille_id,)).fetchone()
    if ligne is None:
        raise KeyError(f"feuille inconnue : {feuille_id}")
    feuille = dict(ligne)  # les portes reçoivent un dict, jamais un sqlite3.Row
    resultats = [porte_sources(ctx, feuille), porte_charge(ctx, feuille)]
    resultats += [porte(ctx, feuille) for porte in ctx.discipline.portes()]
    if feuille["statut"] not in STATUTS_REEVALUABLES:
        return resultats
    bloquantes = [r for r in resultats if not r.ok and r.bloquante]
    if not bloquantes:
        ctx.cx.execute("UPDATE feuilles SET statut = 'prete' WHERE id = ?", (feuille_id,))
        return resultats
    details = {"portes": [{"porte": r.porte, "messages": r.messages} for r in bloquantes]}
    ctx.cx.execute("UPDATE feuilles SET statut = 'a_valider' WHERE id = ?", (feuille_id,))
    ouverte = ctx.cx.execute(
        "SELECT id FROM validations WHERE objet_type = 'feuille' AND objet_id = ? AND statut = 'ouverte'",
        (feuille_id,)).fetchone()
    if ouverte:
        ctx.cx.execute("UPDATE validations SET details = ? WHERE id = ?", (js(details), ouverte["id"]))
    else:
        taches.ouvrir_validation(ctx.cx, "feuille", feuille_id,
                                 f"Feuille {feuille['code']} bloquée par une porte de vérification", details)
    return resultats
