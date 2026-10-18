"""Lot 11 — ligne de commande, squelette de nouveau Mentor, gestionnaires du socle."""

import importlib
import sys

import pytest

from mentor_socle import gpu
from mentor_socle.cli import main, main_socle
from mentor_socle.contexte import Contexte
from mentor_socle.gabarit import creer_projet
from mentor_socle.gestionnaires import tous
from mentor_socle.referentiel import verifier_kit
from mentor_socle.testing import FauxLLM


def test_gestionnaires_du_socle_et_surcharge(ctx, MentorTest, monkeypatch):
    assert {"transcrire_document", "sauvegarde", "indexer_corpus"} <= set(tous(ctx))
    monkeypatch.setattr(MentorTest, "gestionnaires", lambda self: {"sauvegarde": lambda c, p, i: {"propre": 1}})
    assert tous(ctx)["sauvegarde"](ctx, {}, 1) == {"propre": 1}


def test_cli_sur_un_mentor_cree(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("MENTOR_COMMUN", str(tmp_path / "commun"))
    dossier = creer_projet("PHC", "Mentor Physique-Chimie", tmp_path / "mentor-physique-chimie")
    (dossier / "config" / "settings.yaml").write_text(
        (dossier / "config" / "settings.example.yaml").read_text(encoding="utf-8")
        .replace("strict_offline: true", "strict_offline: false"), encoding="utf-8")
    (dossier / "config" / "modeles.yaml").write_text(
        (dossier / "config" / "modeles.example.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    sys.path.insert(0, str(dossier / "src"))
    try:
        cls = importlib.import_module("mentor_physique_chimie.discipline").MentorPhysiqueChimie
        main(cls, dossier, ["migrate"])
        assert "Base à jour" in capsys.readouterr().out
        main(cls, dossier, ["backup"])
        assert "mentor-phc-" in capsys.readouterr().out
        main(cls, dossier, ["plan"])
        assert "approfondissement" in capsys.readouterr().out
        main(cls, dossier, ["gpu"])
        assert "GPU libre" in capsys.readouterr().out
        with pytest.raises(SystemExit) as e:
            main(cls, dossier, ["kit"])
        assert e.value.code == 0
        with pytest.raises(SystemExit) as e:
            main(cls, dossier, ["check"])
        assert "Ollama" in capsys.readouterr().out and e.value.code == 1  # Ollama absent en test
    finally:
        sys.path.remove(str(dossier / "src"))
        for m in [m for m in sys.modules if m.startswith("mentor_physique_chimie")]:
            del sys.modules[m]


def test_mentor_socle_registre_et_gpu(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("MENTOR_COMMUN", str(tmp_path / "c"))
    main_socle(["gpu"])
    assert "GPU libre" in capsys.readouterr().out
    with gpu.verrou("Mentor Maths", "x"):
        main_socle(["gpu"])
        assert "Mentor Maths" in capsys.readouterr().out
    main_socle(["nouveau", "PHI", "Mentor Philosophie", str(tmp_path / "phi")])
    assert (tmp_path / "phi" / "src" / "mentor_philosophie" / "discipline.py").exists()


def test_nouveau_mentor_genere_un_projet_fonctionnel(tmp_path):
    dossier = creer_projet("PHC", "Mentor Physique-Chimie", tmp_path / "mentor-physique-chimie")
    assert (dossier / "migrations" / "0001_phc.sql").exists() and (dossier / "CLAUDE.md").exists()
    assert (dossier / ".claude" / "commands" / "lot.md").exists()
    assert "mentor-socle>=0.1,<0.2" in (dossier / "pyproject.toml").read_text(encoding="utf-8")
    assert "8769" in (dossier / "config" / "settings.example.yaml").read_text(encoding="utf-8")
    with pytest.raises(FileExistsError):
        creer_projet("PHC", "Mentor Physique-Chimie", dossier)
    with pytest.raises(ValueError):
        creer_projet("physique", "x", tmp_path / "x")
    sys.path.insert(0, str(dossier / "src"))
    try:
        cls = importlib.import_module("mentor_physique_chimie.discipline").MentorPhysiqueChimie
        assert cls.code == "PHC" and cls.port_defaut == 8769
        assert verifier_kit(cls(dossier), afficher=False) == 0
        (dossier / "config" / "settings.yaml").write_text(
            (dossier / "config" / "settings.example.yaml").read_text(encoding="utf-8")
            .replace("strict_offline: true", "strict_offline: false"), encoding="utf-8")
        ctx = Contexte.ouvrir(cls(dossier), llm=FauxLLM())
        assert ctx.settings.pedagogie.niveau_exigence == 2
        assert ctx.cx.execute("SELECT 1 FROM sqlite_master WHERE name='phc_notes_internes'").fetchone()
    finally:
        sys.path.remove(str(dossier / "src"))
        for m in [m for m in sys.modules if m.startswith("mentor_physique_chimie")]:
            del sys.modules[m]
