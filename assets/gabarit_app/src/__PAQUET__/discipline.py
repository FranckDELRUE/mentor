"""__NOM__ : ce que le socle ne sait pas faire seul.

Tout le reste (configuration, verrou GPU, appels de modèles, base, tâches, scans, QR, PDF, portes,
répétition espacée, modèle de l'élève, planificateur, interface parent, sauvegarde) vient de
mentor-socle. Voir ../mentor-socle/docs/03-contrat-discipline.md.
"""

from __future__ import annotations

from typing import Any

from mentor_socle.config import SocleSettings
from mentor_socle.discipline import Discipline
from mentor_socle.referentiel import Anomalie, charger_yaml, ids_uniques
from pydantic import BaseModel


class Pedagogie(BaseModel):
    niveau_exigence: int = 2            # 1 Bac, 2 Mention TB, 3 Excellence


class Settings__CODE__(SocleSettings):
    pedagogie: Pedagogie = Pedagogie()


class __CLASSE__(Discipline):
    code = "__CODE__"
    nom = "__NOM__"
    port_defaut = __PORT__
    settings_modele = Settings__CODE__

    def charger_referentiel(self) -> dict[str, Any]:
        return charger_yaml(self.dossier_referentiel / "programme.yaml")

    def verifier_referentiel(self, referentiel: dict[str, Any]) -> list[Anomalie]:
        return ids_uniques(referentiel.get("chapitres", []), "id", "programme.yaml")

    def reference_existe(self, identifiant: str) -> bool:
        ref = self.charger_referentiel()
        return any(c.get("id") == identifiant for c in ref.get("chapitres", []))

    def gestionnaires(self) -> dict:
        return {}   # ex. {"corriger_copie": corriger_copie, "generer_exercice": generer_exercice}

    def portes(self) -> list:
        return []   # ex. [porte_calculs_sympy, porte_faits]
