"""Contrat entre le socle et une discipline (voir ``docs/03-contrat-discipline.md``)."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any

from mentor_socle.config import SocleSettings
from mentor_socle.referentiel import Anomalie

if TYPE_CHECKING:
    from mentor_socle.contexte import Contexte

_CODE = re.compile(r"[A-Z]{3}")


class Discipline(ABC):
    """Un Mentor = une sous-classe ; seul ``charger_referentiel`` est obligatoire.

    Les attributs de classe ``code`` (trois majuscules, écrit dans chaque QR), ``nom`` et
    ``port_defaut`` sont à définir ; ``racine`` est le dossier du projet du Mentor.
    """

    code: str
    nom: str
    port_defaut: int
    settings_modele: type[SocleSettings] = SocleSettings
    version: str = "0.1.0"

    def __init__(self, racine: Path | str):
        code = getattr(self, "code", None)
        if not isinstance(code, str) or not _CODE.fullmatch(code):
            raise ValueError(f"code de discipline invalide : {code!r} (trois majuscules attendues)")
        self.racine = Path(racine)

    # --- chemins conventionnels -------------------------------------------------------------
    @property
    def dossier_config(self) -> Path:
        return self.racine / "config"

    @property
    def dossier_referentiel(self) -> Path:
        return self.racine / "referentiel"

    @property
    def dossier_prompts(self) -> Path:
        return self.racine / "prompts"

    @property
    def dossier_gabarits(self) -> Path:
        return self.racine / "templates"

    @property
    def dossier_migrations(self) -> Path:
        return self.racine / "migrations"

    @property
    def fichier_taxonomie(self) -> Path:
        return self.dossier_referentiel / "taxonomie_erreurs.yaml"

    # --- points d'extension -----------------------------------------------------------------
    @abstractmethod
    def charger_referentiel(self) -> dict[str, Any]:
        """Lit le référentiel de la discipline."""

    def verifier_referentiel(self, referentiel: dict[str, Any]) -> list[Anomalie]:
        return []

    def reference_existe(self, identifiant: str) -> bool:
        """Vrai si ``identifiant`` existe dans le référentiel (porte « sources »)."""
        return False

    def gestionnaires(self) -> dict[str, Any]:
        """Tâches de fond propres : ``{type_de_tache: fonction(ctx, payload, tache_id)}``."""
        return {}

    def portes(self) -> list[Any]:
        """Vérifications avant impression : ``(ctx, feuille) -> ResultatPorte``."""
        return []

    def routeurs(self) -> list[Any]:
        """``APIRouter`` FastAPI propres à la discipline."""
        return []

    def liens_menu(self) -> list[tuple[str, str]]:
        return []

    def lexique_ocr(self, chapitre: Any) -> list[str]:
        return []

    def contexte_feuille(self, feuille: Any) -> dict[str, Any]:
        """Variables supplémentaires pour les gabarits Typst."""
        return {}

    def verifications_demarrage(self, ctx: Contexte) -> list[tuple[str, bool, str]]:
        """Pour ``mentor check`` : ``(libellé, réussi, détail)``."""
        return []
