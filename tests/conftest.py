"""Fixtures communes. Les imports de mentor_socle sont faits dans les fixtures : les tests d'un lot
ne dépendent jamais de modules écrits dans un lot ultérieur."""

from __future__ import annotations

from functools import cache
from pathlib import Path

import pytest

KIT = Path(__file__).parent / "kit_test"


@cache
def classe_discipline_test():
    """Discipline fictive « TST » (disponible à partir du lot 4)."""
    from mentor_socle.discipline import Discipline
    from mentor_socle.referentiel import charger_yaml

    class MentorTest(Discipline):
        code = "TST"
        nom = "Mentor Test"
        port_defaut = 18999

        def charger_referentiel(self):
            return charger_yaml(self.dossier_referentiel / "programme.yaml")

        def reference_existe(self, identifiant: str) -> bool:
            return identifiant in {c["id"] for c in self.charger_referentiel()["chapitres"]}

        def lexique_ocr(self, chapitre):
            return ["photosynthèse", "Rimbaud"]

    return MentorTest


@pytest.fixture(autouse=True)
def commun_isole(tmp_path, monkeypatch):
    """Verrou GPU et registre dans un dossier jetable : jamais ceux de la vraie machine."""
    monkeypatch.setenv("MENTOR_COMMUN", str(tmp_path / "_commun"))


@pytest.fixture
def MentorTest():
    return classe_discipline_test()


@pytest.fixture
def llm():
    from mentor_socle.testing import FauxLLM

    return FauxLLM()


@pytest.fixture
def ctx(tmp_path, llm):
    from mentor_socle.testing import contexte_de_test

    return contexte_de_test(classe_discipline_test(), tmp_path, llm=llm, racine_kit=KIT)
