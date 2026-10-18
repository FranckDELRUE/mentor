"""Lot 6 — QR, prétraitement d'image, feuilles, portes avant impression, rendu PDF Typst."""

import cv2
import numpy as np
import pymupdf
import pytest
import segno

from mentor_socle.impression import feuilles
from mentor_socle.scan import image, qr

def test_qr_aller_retour_et_lecture_image(tmp_path):
    t = qr.encoder("MAT", "MAT-26-0042", 2, 3)
    assert t == "MENTOR1|MAT|MAT-26-0042|2/3"
    assert qr.decoder(t) == qr.InfoQR("MAT", "MAT-26-0042", 2, 3)
    assert qr.decoder("autre chose") is None
    with pytest.raises(ValueError):
        qr.encoder("maths", "X", 1, 1)
    f = tmp_path / "q.png"
    segno.make(t, error="h").save(str(f), scale=8, border=4)
    assert qr.lire(image.pages(f)[0]) == [qr.InfoQR("MAT", "MAT-26-0042", 2, 3)]
    assert qr.svg(t).startswith("<svg")


def test_image_chemin_accentue_redressement_et_taille(tmp_path):
    img = np.full((900, 700, 3), 255, np.uint8)
    for y in range(120, 800, 45):  # lignes d'écriture
        cv2.line(img, (60, y), (640, y), (0, 0, 0), 2)
    f = image.enregistrer(img, tmp_path / "dossier é" / "page é.png")
    relue = image.pages(f)[0]
    assert relue.shape == img.shape
    h, w = img.shape[:2]
    penchee = cv2.warpAffine(img, cv2.getRotationMatrix2D((w / 2, h / 2), 3, 1), (w, h), borderValue=(255, 255, 255))
    _, angle = image.redresser(penchee)
    assert 1.5 < abs(angle) < 4.5
    assert max(image.pour_vision(np.zeros((4000, 3000, 3), np.uint8), 1800).shape[:2]) == 1800
    assert image.ameliorer(img).ndim == 2




CONTENU = {
    "consignes": "Répondez *au crayon* dans les cadres.",
    "exercices": [
        {"titre": "Échauffement", "enonce": "Donner la définition de la photosynthèse.", "bareme": 2,
         "reponse": {"type": "lignes", "hauteur_cm": 4}},
        {"enonce": "Construire un tableau.", "reponse": {"type": "carreaux", "hauteur_cm": 6}},
        {"enonce": "Schéma légendé.", "reponse": {"type": "cadre", "hauteur_cm": 22}},
    ],
}


def _feuille(ctx, sources, **kw):
    return feuilles.creer(ctx, type_="exercice", titre="Feuille d'essai", contenu=CONTENU, sources=sources,
                          chapitres=["C01"], duree_min=kw.pop("duree_min", 20), **kw)


def test_codes_de_feuille_croissants(ctx):
    _feuille(ctx, ["ref:C01"])
    _feuille(ctx, ["ref:C01"])
    assert [r[0] for r in ctx.cx.execute("SELECT code FROM feuilles ORDER BY id")] == ["TST-26-0001", "TST-26-0002"]


def test_porte_sources_bloque_et_ouvre_une_validation(ctx):
    fid = _feuille(ctx, ["ref:C99", "seg:INCONNU", "n'importe quoi"])
    res = feuilles.verifier(ctx, fid)
    sources = next(r for r in res if r.porte == "sources")
    assert not sources.ok and sources.bloquante and len(sources.messages) == 3
    assert ctx.cx.execute("SELECT statut FROM feuilles WHERE id=?", (fid,)).fetchone()[0] == "a_valider"
    assert ctx.cx.execute("SELECT COUNT(*) FROM validations WHERE objet_type='feuille'").fetchone()[0] == 1
    with pytest.raises(feuilles.FeuilleNonPrete):
        feuilles.imprimer(ctx, fid)


def test_porte_sans_source_et_segment_connu(ctx):
    assert not next(r for r in feuilles.verifier(ctx, _feuille(ctx, [])) if r.porte == "sources").ok
    ctx.cx.execute("INSERT INTO segments(code, chapitre, texte) VALUES ('C01-001','C01','texte')")
    res = feuilles.verifier(ctx, _feuille(ctx, ["seg:C01-001", "ref:C02"]))
    assert all(r.ok for r in res)


def test_porte_charge_alerte_non_bloquante(ctx):
    fid = _feuille(ctx, ["ref:C01"], duree_min=60)
    res = feuilles.verifier(ctx, fid)
    charge = next(r for r in res if r.porte == "charge")
    assert not charge.ok and not charge.bloquante
    assert ctx.cx.execute("SELECT statut FROM feuilles WHERE id=?", (fid,)).fetchone()[0] == "prete"


def test_porte_de_la_discipline(ctx, MentorTest, monkeypatch):
    from mentor_socle.impression.portes import ResultatPorte

    monkeypatch.setattr(MentorTest, "portes", lambda self: [lambda c, f: ResultatPorte("sympy", False, True, ["2+2≠5"])])
    fid = _feuille(ctx, ["ref:C01"])
    feuilles.verifier(ctx, fid)
    assert ctx.cx.execute("SELECT statut FROM feuilles WHERE id=?", (fid,)).fetchone()[0] == "a_valider"
    assert "sympy" in ctx.cx.execute("SELECT details FROM validations").fetchone()[0]


def test_pdf_deux_pages_texte_et_qr_par_page(ctx, tmp_path):
    fid = _feuille(ctx, ["ref:C01"])
    assert all(r.ok for r in feuilles.verifier(ctx, fid))
    pdf = feuilles.imprimer(ctx, fid)
    assert pdf.exists() and ctx.cx.execute("SELECT statut FROM feuilles WHERE id=?", (fid,)).fetchone()[0] == "imprimee"
    with pymupdf.open(pdf) as doc:
        assert doc.page_count == 2
        texte = doc[0].get_text()
        assert "Exercice 1" in texte and "TST-26-0001" in texte and "Page 1 / 2" in texte
    infos = [qr.lire(img) for img in image.pages(pdf)]
    assert infos[0] == [qr.InfoQR("TST", "TST-26-0001", 1, 2)]
    assert infos[1] == [qr.InfoQR("TST", "TST-26-0001", 2, 2)]


def test_gabarit_de_la_discipline_prioritaire(ctx):
    (ctx.discipline.dossier_gabarits / "exercice.typ").write_text(
        '#import "mentor.typ": *\n#show: mentor-page\nGABARIT PROPRE #donnees.contenu.consignes\n', encoding="utf-8")
    fid = _feuille(ctx, ["ref:C01"])
    feuilles.verifier(ctx, fid)
    with pymupdf.open(feuilles.imprimer(ctx, fid)) as doc:
        assert "GABARIT PROPRE" in doc[0].get_text()
