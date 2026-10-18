"""Lot 10 — interface parent."""

from fastapi.testclient import TestClient

from mentor_socle.web.app import creer_app
from mentor_socle.web.auth import hacher_pin, verifier_pin


def test_interface_sans_pin(ctx):
    c = TestClient(creer_app(ctx))
    r = c.get("/")
    assert r.status_code == 200 and "Mentor Test" in r.text and "Aucun PIN parent" in r.text
    for page in ("/depot", "/validations", "/taches", "/feuilles"):
        assert c.get(page).status_code == 200


def test_interface_avec_pin(ctx):
    ctx.settings.parent.pin_hash = hacher_pin("2468")
    c = TestClient(creer_app(ctx), follow_redirects=False)
    assert c.get("/").headers["location"] == "/connexion"
    assert c.get("/connexion").status_code == 200
    assert c.post("/connexion", data={"pin": "0000"}).headers["location"].startswith("/connexion")
    assert c.post("/connexion", data={"pin": "2468"}).headers["location"] == "/"
    assert c.get("/").status_code == 200
    assert c.get("/deconnexion").status_code == 303 and c.get("/").status_code in (200, 303)
    assert verifier_pin("2468", ctx.settings.parent.pin_hash) and not verifier_pin("1", "n'importe")


def test_pin_invalide_refuse():
    import pytest

    with pytest.raises(ValueError):
        hacher_pin("abc")


def test_depot_par_l_interface(ctx):
    import numpy as np

    from mentor_socle.scan import image

    f = ctx.data / "x.png"
    image.enregistrer(np.full((400, 300, 3), 255, np.uint8), f)
    c = TestClient(creer_app(ctx))
    r = c.post("/depot", files={"fichier": ("cours.png", f.read_bytes(), "image/png")}, data={"type_document": "cours"})
    assert r.status_code == 200 and "reçu" in r.text
    assert ctx.cx.execute("SELECT type FROM documents").fetchone()[0] == "cours"
    assert ctx.cx.execute("SELECT type FROM taches").fetchone()[0] == "transcrire_document"
    assert c.post("/depot", files={"fichier": ("virus.exe", b"x", "application/octet-stream")}).status_code == 400


def test_validations_taches_feuilles(ctx):
    from mentor_socle import taches
    from mentor_socle.impression import feuilles

    vid = taches.ouvrir_validation(ctx.cx, "document", 1, "Transcription à relire", {"pages": [2]})
    t = taches.ajouter(ctx.cx, "x")
    ctx.cx.execute("UPDATE taches SET statut='echec' WHERE id=?", (t,))
    fid = feuilles.creer(ctx, type_="exercice", titre="T", contenu={"exercices": []}, sources=["ref:C01"])
    feuilles.verifier(ctx, fid)
    c = TestClient(creer_app(ctx))
    assert "Transcription à relire" in c.get("/validations").text
    c.post(f"/validations/{vid}", data={"statut": "acceptee", "decision": "ok"})
    assert ctx.cx.execute("SELECT statut FROM validations WHERE id=?", (vid,)).fetchone()[0] == "acceptee"
    assert c.post(f"/validations/{vid}", data={"statut": "n'importe"}).status_code == 400
    c.post(f"/taches/{t}/relancer")
    assert ctx.cx.execute("SELECT statut FROM taches WHERE id=?", (t,)).fetchone()[0] == "en_attente"
    assert c.post(f"/feuilles/{fid}/imprimer").status_code == 200
    code = ctx.cx.execute("SELECT code FROM feuilles").fetchone()[0]
    assert c.get(f"/pdf/{code}").headers["content-type"] == "application/pdf"
    assert c.get("/pdf/INCONNU").status_code == 404


def test_tableau_de_bord_affiche_le_plan(ctx):
    r = TestClient(creer_app(ctx)).get("/")
    assert "Cette semaine" in r.text and "approfondissement" in r.text


def test_la_discipline_ajoute_pages_et_menu(ctx, MentorTest, monkeypatch):
    from fastapi import APIRouter

    routeur = APIRouter()
    routeur.add_api_route("/oral", lambda: {"ok": True})
    monkeypatch.setattr(MentorTest, "routeurs", lambda self: [routeur])
    monkeypatch.setattr(MentorTest, "liens_menu", lambda self: [("Oral", "/oral")])
    c = TestClient(creer_app(ctx))
    assert c.get("/oral").json() == {"ok": True} and 'href="/oral"' in c.get("/").text
