"""Contexte d'exécution transmis aux gestionnaires, portes et pages."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mentor_socle import offline
from mentor_socle.config import SocleSettings, charger_settings
from mentor_socle.db import connecter, migrer
from mentor_socle.discipline import Discipline
from mentor_socle.llm.modeles import RegistreModeles, charger_modeles
from mentor_socle.llm.ollama import ClientLLM, ClientOllama
from mentor_socle.llm.prompts import BibliothequePrompts


@dataclass
class Contexte:
    """Tout ce dont une discipline a besoin ; ``referentiel`` est chargé à la première utilisation."""

    discipline: Discipline
    settings: SocleSettings
    cx: sqlite3.Connection
    modeles: RegistreModeles
    prompts: BibliothequePrompts
    llm: ClientLLM
    data: Path
    _referentiel: dict[str, Any] | None = field(default=None, repr=False)

    @property
    def referentiel(self) -> dict[str, Any]:
        if self._referentiel is None:
            self._referentiel = self.discipline.charger_referentiel()
        return self._referentiel

    @classmethod
    def ouvrir(
        cls,
        discipline: Discipline,
        *,
        llm: ClientLLM | None = None,
        fichier_settings: Path | str | None = None,
    ) -> Contexte:
        """Lit les settings, prépare les dossiers, ouvre et migre la base de la discipline."""
        fichier = Path(fichier_settings) if fichier_settings else discipline.dossier_config / "settings.yaml"
        if not fichier.is_file():
            raise FileNotFoundError(
                f"Settings introuvables : {fichier}. Copier config/settings.example.yaml "
                "en config/settings.yaml puis le compléter."
            )
        settings = charger_settings(fichier, discipline.settings_modele)
        if settings.app.strict_offline:
            offline.activer()
        chemins = settings.chemins
        for dossier in (chemins.data, chemins.inbox, chemins.sauvegardes):
            dossier.mkdir(parents=True, exist_ok=True)
        code = discipline.code.lower()
        cx = connecter(chemins.data / f"mentor-{code}.sqlite3")
        migrer(cx, code, discipline.dossier_migrations)
        return cls(
            discipline=discipline,
            settings=settings,
            cx=cx,
            modeles=charger_modeles(discipline.dossier_config),
            prompts=BibliothequePrompts(discipline.dossier_prompts),
            llm=llm if llm is not None else ClientOllama(settings.ollama.url, settings.ollama.timeout_s),
            data=chemins.data,
        )
