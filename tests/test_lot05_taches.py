"""Lot 5 — file de tâches, travailleur, validations."""

import time

from mentor_socle import taches


def test_file_de_taches_succes_validation_et_echec(ctx):
    def ok(c, payload, tid):
        return {"double": payload["n"] * 2}

    def douteux(c, payload, tid):
        raise taches.AValider("À relire", {"page": 2})

    def casse(c, payload, tid):
        raise RuntimeError("boum")

    g = {"ok": ok, "douteux": douteux, "casse": casse}
    t1 = taches.ajouter(ctx.cx, "ok", {"n": 21})
    t2 = taches.ajouter(ctx.cx, "douteux", priorite=1)
    t3 = taches.ajouter(ctx.cx, "casse", max_essais=2)
    ordre = []
    while taches.executer_une(ctx, g):
        ordre.append(ctx.cx.execute("SELECT id FROM taches WHERE statut!='en_attente' ORDER BY debut_le DESC, id DESC").fetchone()[0])
    statut = dict(ctx.cx.execute("SELECT id, statut FROM taches").fetchall())
    assert statut == {t1: "faite", t2: "a_valider", t3: "echec"}
    assert ctx.cx.execute("SELECT essais FROM taches WHERE id=?", (t3,)).fetchone()[0] == 2
    assert ctx.cx.execute("SELECT motif FROM validations").fetchone()[0] == "À relire"
    assert ctx.cx.execute("SELECT resultat FROM taches WHERE id=?", (t1,)).fetchone()[0] == '{"double": 42}'
    assert ordre[0] == t2  # la plus urgente d'abord


def test_tache_sans_gestionnaire_echoue_tout_de_suite(ctx):
    t = taches.ajouter(ctx.cx, "inconnu")
    assert taches.executer_une(ctx, {}) is True and taches.executer_une(ctx, {}) is False
    ligne = ctx.cx.execute("SELECT statut, essais FROM taches WHERE id=?", (t,)).fetchone()
    assert ligne["statut"] == "echec" and ligne["essais"] == 1


def test_reprise_des_taches_orphelines(ctx):
    t = taches.ajouter(ctx.cx, "x")
    taches.prendre(ctx.cx)
    assert ctx.cx.execute("SELECT statut FROM taches WHERE id=?", (t,)).fetchone()[0] == "en_cours"
    assert taches.reprendre_orphelines(ctx.cx) == 1
    assert ctx.cx.execute("SELECT statut FROM taches WHERE id=?", (t,)).fetchone()[0] == "en_attente"


def test_travailleur_en_fond(ctx):
    t = taches.ajouter(ctx.cx, "ok", {"n": 1})
    w = taches.Travailleur(ctx, {"ok": lambda c, p, i: {"fait": True}}, attente_s=0.05)
    w.start()
    for _ in range(100):
        if ctx.cx.execute("SELECT statut FROM taches WHERE id=?", (t,)).fetchone()[0] == "faite":
            break
        time.sleep(0.05)
    w.arreter()
    w.join(timeout=5)
    assert ctx.cx.execute("SELECT statut FROM taches WHERE id=?", (t,)).fetchone()[0] == "faite"
    assert not w.is_alive()
