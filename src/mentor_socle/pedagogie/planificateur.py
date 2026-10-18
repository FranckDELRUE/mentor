"""Planificateur hebdomadaire : transforme l'état de l'élève en éléments de travail motivés."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from mentor_socle.contexte import Contexte
from mentor_socle.pedagogie import competences, erreurs, srs

MIN_ELEMENT = 5
HORIZON_EVALUATION_JOURS = 14
DUREE_REMEDIATION = 20
DUREE_COMPETENCE = 15
NB_COMPETENCES = 4
CARTES_MAX_MIN = 15


@dataclass(frozen=True)
class ElementPlan:
    """Un temps de travail proposé ; ``priorite`` 1 = à faire en premier."""

    type: str  # preparation_evaluation, remediation, competence, cartes, approfondissement
    cible: str
    duree_min: int
    raison: str
    priorite: int


def budget_semaine(ctx: Contexte, jour: dt.date | None = None) -> int:
    """Minutes de travail de la semaine à planifier, majorées si ≥ 4 jours de vacances.

    La semaine va du mardi au lundi et commence au premier mardi à partir de ``jour`` : un plan établi
    le lundi couvre les sept jours à venir.
    """
    jour = jour or dt.date.today()
    mardi = jour + dt.timedelta(days=(1 - jour.weekday()) % 7)
    charge = ctx.settings.charge
    vacances = sum(ctx.settings.calendrier.en_vacances(mardi + dt.timedelta(days=i)) for i in range(7))
    return int(charge.hebdo_min * charge.coefficient_vacances) if vacances >= 4 else charge.hebdo_min


def planifier(ctx: Contexte, jour: dt.date | None = None) -> list[ElementPlan]:
    """Plan de la semaine, dans l'ordre : évaluations proches, erreurs à corriger, compétences, cartes, reste."""
    jour = jour or dt.date.today()
    reste = budget_semaine(ctx, jour)
    maxi = ctx.settings.charge.seance_max_min
    plan: list[ElementPlan] = []

    def ajouter(type_: str, cible: str, souhaite: int, raison: str) -> bool:
        nonlocal reste
        duree = min(souhaite, maxi, reste)
        if duree < MIN_ELEMENT:
            return False
        plan.append(ElementPlan(type_, cible, duree, raison, len(plan) + 1))
        reste -= duree
        return True

    proches = sorted(
        (e for e in ctx.settings.calendrier.evaluations
         if 0 <= (e.date - jour).days <= HORIZON_EVALUATION_JOURS),
        key=lambda e: (e.date, -e.coefficient),
    )
    for ev in proches:
        nom = ev.libelle or ev.type
        dans = (ev.date - jour).days
        for chapitre in ev.chapitres or [""]:
            ajouter("preparation_evaluation", chapitre, maxi,
                    f"{nom} dans {dans} jour(s) (coefficient {ev.coefficient:g})")

    for r in erreurs.recurrentes(ctx.cx, jour):
        if r["tendance"] != "recul":
            ajouter("remediation", r["code"], DUREE_REMEDIATION,
                    f"{r['nb']} erreurs {r['code']} en {erreurs.FENETRE_JOURS} jours (tendance : {r['tendance']})")

    for c in competences.priorites(ctx.cx, jour=jour, limite=NB_COMPETENCES):
        ajouter("competence", c["code"], DUREE_COMPETENCE,
                f"maîtrise estimée {c['maitrise']:.2f}, incertitude {c['incertitude']:.2f}")

    dues = srs.a_reviser(ctx.cx, jour)
    if dues:
        ajouter("cartes", "cartes", min(max(len(dues), MIN_ELEMENT), CARTES_MAX_MIN),
                f"{len(dues)} carte(s) à revoir")

    while ajouter("approfondissement", "", maxi, "temps libre : approfondir ce qui a été vu"):
        pass
    return plan
