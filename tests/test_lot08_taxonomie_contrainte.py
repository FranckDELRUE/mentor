"""Lot 8 (complément) — le schéma de sortie interdit tout code hors taxonomie."""

import pytest
from pydantic import ValidationError

from mentor_socle.pedagogie import erreurs


def test_schema_limite_les_codes(ctx):
    tax = erreurs.charger(ctx.discipline.fichier_taxonomie)
    Erreur = tax.modele_erreur()
    assert Erreur.model_json_schema()["properties"]["code"]["enum"] == ["E-A", "E-B"]
    assert Erreur(code="E-A").code == "E-A"
    with pytest.raises(ValidationError):
        Erreur(code="E-INVENTE")
    assert "E-B : Erreur B [calcul]" in tax.pour_prompt()
