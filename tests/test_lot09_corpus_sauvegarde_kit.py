"""Lot 9 — corpus, sauvegarde, vérification du kit d'une discipline."""

import time

from mentor_socle import corpus, sauvegarde
from mentor_socle.referentiel import (Anomalie, ids_uniques, nombre, references_connues, verifier_kit)


def test_corpus_recherche(ctx):
    corpus.ajouter_segment(ctx, "C01-001", "C01", "La photosynthèse produit du dioxygène.")
    corpus.ajouter_segment(ctx, "C02-001", "C02", "Rimbaud écrit le Cahier de Douai.")
    assert corpus.indexer(ctx) == 2 and corpus.indexer(ctx) == 0
    assert corpus.rechercher(ctx, "photosynthèse dioxygène", k=1)[0]["code"] == "C01-001"
    assert corpus.rechercher(ctx, "x", chapitres=["C02"])[0]["code"] == "C02-001"
    corpus.ajouter_segment(ctx, "C01-001", "C01", "Texte corrigé.")  # modifié → à réindexer
    assert corpus.indexer(ctx) == 1


def test_sauvegarde_et_rotation(ctx):
    ctx.settings.sauvegarde.conserver = 2
    assert sauvegarde.due(ctx)
    fichiers = []
    for _ in range(3):
        fichiers.append(sauvegarde.sauvegarder(ctx))
        time.sleep(1.05)
    assert sorted(ctx.settings.chemins.sauvegardes.glob("*.sqlite3")) == fichiers[1:]
    assert not sauvegarde.due(ctx)
    ctx.settings.sauvegarde.automatique = "aucune"
    assert not sauvegarde.due(ctx)


def test_sauvegarde_restaurable(ctx):
    import sqlite3

    ctx.cx.execute("INSERT INTO notes_reelles(evaluation, date, note) VALUES ('DS1','2026-10-01',14)")
    f = sauvegarde.sauvegarder(ctx)
    assert sqlite3.connect(f).execute("SELECT note FROM notes_reelles").fetchone()[0] == 14


def test_outils_de_referentiel():
    assert nombre("6.4e9") == 6.4e9 and nombre("1/4") == 0.25 and nombre(3) == 3.0
    assert ids_uniques([{"id": "a"}, {"id": "a"}], "id", "f.yaml")[0].niveau == "erreur"
    assert references_connues(["a", "z"], {"a"}, "f", "chapitre")[0].message == "chapitre inconnu : z"
    assert "[ALERTE]" in str(Anomalie("alerte", "f.yaml", "m"))


def test_verifier_kit_valide_et_detecte_les_erreurs(ctx, capsys):
    assert verifier_kit(ctx.discipline, afficher=False) == 0
    (ctx.discipline.dossier_prompts / "orphelin.md").write_text(
        "---\nrole: role-inconnu\nversion: 1\n---\ntexte", encoding="utf-8")
    assert verifier_kit(ctx.discipline) == 1
    assert "role-inconnu" in capsys.readouterr().out
