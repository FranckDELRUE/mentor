from pathlib import Path

from mentor_socle.referentiel import verifier_kit
from mentor_socle.testing import FauxLLM, contexte_de_test

from __PAQUET__.discipline import __CLASSE__

RACINE = Path(__file__).resolve().parents[1]


def test_kit_coherent():
    assert verifier_kit(__CLASSE__(RACINE), afficher=False) == 0


def test_contexte_ouvre_la_base(tmp_path):
    ctx = contexte_de_test(__CLASSE__, tmp_path, llm=FauxLLM(), racine_kit=RACINE)
    tables = {r[0] for r in ctx.cx.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"feuilles", "copies", "__code___notes_internes"} <= tables
