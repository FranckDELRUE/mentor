"""Lot 7 — inbox (dédoublonnage, pages, QR, renvoi entre Mentor) et transcription."""

import shutil

import numpy as np
import segno

from mentor_socle import registre, taches
from mentor_socle.scan import image, inbox, qr


def _feuille_imprimee(ctx):
    from mentor_socle.impression import feuilles

    contenu = {"consignes": "Au crayon.", "exercices": [
        {"enonce": "Définir.", "reponse": {"type": "lignes", "hauteur_cm": 4}},
        {"enonce": "Schéma.", "reponse": {"type": "cadre", "hauteur_cm": 22}}]}
    fid = feuilles.creer(ctx, type_="exercice", titre="Essai", contenu=contenu, sources=["ref:C01"], duree_min=20)
    feuilles.verifier(ctx, fid)
    return fid, feuilles.imprimer(ctx, fid)


def _scanner_pdf(pdf, sortie, dpi=150):
    import pymupdf

    with pymupdf.open(pdf) as doc:
        nouveau = pymupdf.open()
        for page in doc:
            pix = page.get_pixmap(dpi=dpi)
            p = nouveau.new_page(width=page.rect.width, height=page.rect.height)
            p.insert_image(p.rect, pixmap=pix)
        nouveau.save(sortie)
    return sortie


def test_ingestion_transcription_et_doublon(ctx, llm, tmp_path):
    from mentor_socle.gestionnaires import tous

    fid, pdf = _feuille_imprimee(ctx)
    scan = _scanner_pdf(pdf, ctx.settings.chemins.inbox / "copie.pdf")
    garde = shutil.copy(scan, tmp_path / "garde.pdf")
    bilan = inbox.scanner(ctx)
    assert len(bilan.recus) == 1 and not scan.exists()
    doc_id = bilan.recus[0]
    assert ctx.cx.execute("SELECT type FROM documents WHERE id=?", (doc_id,)).fetchone()[0] == "copie_mentor"
    pages = ctx.cx.execute("SELECT qr FROM pages WHERE document_id=? ORDER BY numero", (doc_id,)).fetchall()
    assert '"page": 2' in pages[1]["qr"] and '"total": 2' in pages[1]["qr"]
    assert ctx.cx.execute("SELECT statut FROM feuilles WHERE id=?", (fid,)).fetchone()[0] == "rendue"

    llm.reponses = {"transcription": [
        {"zones": [{"type": "texte", "texte": "La photosynthèse…", "confiance": 0.92}]},
        {"zones": [{"type": "schema", "texte": "[schéma]", "confiance": 0.5}]},
    ]}
    while taches.executer_une(ctx, tous(ctx)):
        pass
    assert ctx.cx.execute("SELECT COUNT(*) FROM zones").fetchone()[0] == 2
    assert ctx.cx.execute("SELECT statut FROM documents WHERE id=?", (doc_id,)).fetchone()[0] == "a_valider"
    assert "photosynthèse" in llm.appels[0]["messages"][0]["content"]  # lexique de la discipline injecté
    assert "images" in llm.appels[0]["messages"][-1]
    assert ctx.cx.execute("SELECT details FROM validations").fetchone()[0] == '{"pages": [2]}'

    shutil.copy(garde, ctx.settings.chemins.inbox / "copie-bis.pdf")
    b2 = inbox.scanner(ctx)
    assert b2.doublons == ["copie-bis.pdf"] and b2.recus == []
    assert (ctx.settings.chemins.inbox / "_doublons" / "copie-bis.pdf").exists()


def test_feuille_d_un_autre_mentor_est_renvoyee(ctx, tmp_path):
    inbox_svt = tmp_path / "inbox_svt"
    inbox_svt.mkdir()
    registre.enregistrer("SVT", "Mentor SVT", 8768, tmp_path, inbox_svt, "0.1.0")
    segno.make(qr.encoder("SVT", "SVT-26-0007", 1, 1), error="h").save(
        str(ctx.settings.chemins.inbox / "svt.png"), scale=8, border=4)
    bilan = inbox.scanner(ctx)
    assert bilan.renvoyes == [("svt.png", "SVT")] and (inbox_svt / "svt.png").exists()
    assert ctx.cx.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 0


def test_scan_sans_qr_demande_un_classement(ctx):
    image.enregistrer(np.full((800, 600, 3), 255, np.uint8), ctx.settings.chemins.inbox / "cours.png")
    bilan = inbox.scanner(ctx)
    assert ctx.cx.execute("SELECT type FROM documents WHERE id=?", (bilan.recus[0],)).fetchone()[0] == "a_classer"
    assert ctx.cx.execute("SELECT COUNT(*) FROM taches").fetchone()[0] == 0
    assert "Type de document" in ctx.cx.execute("SELECT motif FROM validations").fetchone()[0]


def test_fichier_illisible_ecarte(ctx):
    (ctx.settings.chemins.inbox / "casse.png").write_bytes(b"pas une image")
    bilan = inbox.scanner(ctx)
    assert len(bilan.illisibles) == 1 and (ctx.settings.chemins.inbox / "_illisibles" / "casse.png").exists()
