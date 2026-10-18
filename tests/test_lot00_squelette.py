"""Lot 0 — squelette du paquet."""

import re
import tomllib
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def test_paquet_importable_et_versionne():
    import mentor_socle

    assert re.fullmatch(r"\d+\.\d+\.\d+", mentor_socle.__version__)


def test_version_identique_dans_pyproject():
    import mentor_socle

    projet = tomllib.loads((RACINE / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert projet["name"] == "mentor-socle"
    assert projet["version"] == mentor_socle.__version__
    assert projet["requires-python"].startswith(">=3.12")


def test_dossier_commun_surchargeable(tmp_path, monkeypatch):
    from mentor_socle.chemins import dossier_commun

    monkeypatch.setenv("MENTOR_COMMUN", str(tmp_path / "c"))
    assert dossier_commun() == tmp_path / "c" and (tmp_path / "c").is_dir()
