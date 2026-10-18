"""Lot 8 — répétition espacée, modèle de l'élève, erreurs, planificateur."""

import datetime as dt

import pytest

from mentor_socle.config import Evaluation, Periode
from mentor_socle.pedagogie import competences, erreurs, planificateur, srs

LUNDI = dt.date(2026, 11, 9)


def test_leitner(ctx):
    cid = srs.ajouter(ctx.cx, "Recto", "Verso", "ref:C01", "C01", jour=LUNDI)
    assert [r["id"] for r in srs.a_reviser(ctx.cx, LUNDI)] == [cid]
    assert srs.reviser(ctx.cx, cid, True, LUNDI) == LUNDI + dt.timedelta(days=3)
    assert srs.reviser(ctx.cx, cid, True, LUNDI) == LUNDI + dt.timedelta(days=7)
    assert srs.reviser(ctx.cx, cid, False, LUNDI) == LUNDI + dt.timedelta(days=1)
    assert srs.a_reviser(ctx.cx, LUNDI) == []
    assert srs.a_reviser(ctx.cx, LUNDI + dt.timedelta(days=1), chapitres=["C02"]) == []


def test_competences_convergent_et_priorites(ctx):
    for _ in range(6):
        competences.observer(ctx.cx, "CA-1", 0.9, chapitre="C01", jour=LUNDI)
    _, u = competences.observer(ctx.cx, "CA-2", 0.2, chapitre="C02", jour=LUNDI)
    m1 = ctx.cx.execute("SELECT maitrise, incertitude, nb_observations FROM competences WHERE code='CA-1'").fetchone()
    assert m1["maitrise"] > 0.8 and m1["incertitude"] < u and m1["nb_observations"] == 6
    assert competences.priorites(ctx.cx, jour=LUNDI)[0]["code"] == "CA-2"
    assert [c["code"] for c in competences.priorites(ctx.cx, chapitres=["C01"], jour=LUNDI)] == ["CA-1"]
    with pytest.raises(ValueError):
        competences.observer(ctx.cx, "CA-1", 1.5)


def test_incertitude_remonte_sans_observation(ctx):
    for _ in range(8):
        competences.observer(ctx.cx, "CA-1", 0.9, jour=LUNDI)
    apres = competences.priorites(ctx.cx, jour=LUNDI)[0]["incertitude"]
    plus_tard = competences.priorites(ctx.cx, jour=LUNDI + dt.timedelta(days=120))[0]["incertitude"]
    assert plus_tard > apres


def test_erreurs_taxonomie_et_tendance(ctx):
    tax = erreurs.charger(ctx.discipline.fichier_taxonomie)
    assert tax.codes() == {"E-A", "E-B"} and tax["E-B"].gravite == 3
    with pytest.raises(ValueError):
        erreurs.enregistrer(ctx.cx, None, [{"code": "E-INVENTE"}], tax)
    for jours in (40, 35, 30, 28, 25):
        erreurs.enregistrer(ctx.cx, None, [{"code": "E-A"}], tax, LUNDI - dt.timedelta(days=jours))
    erreurs.enregistrer(ctx.cx, None, [{"code": "E-A"}], tax, LUNDI - dt.timedelta(days=3))
    for jours in (10, 5, 2):
        erreurs.enregistrer(ctx.cx, None, [{"code": "E-B"}], tax, LUNDI - dt.timedelta(days=jours))
    r = {x["code"]: x for x in erreurs.recurrentes(ctx.cx, jour=LUNDI)}
    assert r["E-A"]["tendance"] == "recul" and r["E-B"]["tendance"] == "hausse"
    assert ctx.cx.execute("SELECT gravite FROM erreurs WHERE code='E-B' LIMIT 1").fetchone()[0] == 3


def test_planificateur_priorise_et_respecte_le_budget(ctx):
    ctx.settings.calendrier.evaluations = [Evaluation(date=LUNDI + dt.timedelta(days=4), type="ds",
                                                      chapitres=["C02"], coefficient=2, libelle="DS 3")]
    tax = erreurs.charger(ctx.discipline.fichier_taxonomie)
    for j in (3, 2, 1):
        erreurs.enregistrer(ctx.cx, None, [{"code": "E-B"}], tax, LUNDI - dt.timedelta(days=j))
    competences.observer(ctx.cx, "CA-2", 0.1, jour=LUNDI)
    plan = planificateur.planifier(ctx, LUNDI)
    assert [e.type for e in plan[:3]] == ["preparation_evaluation", "remediation", "competence"]
    assert "DS 3" in plan[0].raison and plan[0].cible == "C02"
    assert sum(e.duree_min for e in plan) <= ctx.settings.charge.hebdo_min
    assert all(5 <= e.duree_min <= ctx.settings.charge.seance_max_min for e in plan)


def test_planificateur_sans_rien_remplit_en_approfondissement(ctx):
    plan = planificateur.planifier(ctx, LUNDI)
    assert plan and {e.type for e in plan} == {"approfondissement"}
    assert sum(e.duree_min for e in plan) == ctx.settings.charge.hebdo_min


def test_budget_vacances(ctx):
    ctx.settings.calendrier.vacances = [Periode(nom="Noël", debut=dt.date(2026, 12, 19), fin=dt.date(2027, 1, 4))]
    assert planificateur.budget_semaine(ctx, dt.date(2026, 12, 21)) == int(90 * 1.5)
    assert planificateur.budget_semaine(ctx, LUNDI) == 90
