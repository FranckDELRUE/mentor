"""Configuration commune (``settings.yaml``) : sections partagées par tous les Mentor."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Strict(BaseModel):
    """Base de toutes les sections : toute clé inconnue est refusée."""

    model_config = ConfigDict(extra="forbid")


class AppConfig(_Strict):
    """Serveur local de l'interface parent."""

    host: str = "127.0.0.1"
    port: int = Field(ge=1024, le=65535)
    strict_offline: bool = True


class CheminsConfig(_Strict):
    """Dossiers de travail ; relatifs à la racine du projet tant qu'ils ne sont pas résolus."""

    data: Path = Path("data")
    inbox: Path | None = None
    sauvegardes: Path | None = None

    def resolus(self, racine: Path) -> CheminsConfig:
        """Copie aux chemins absolus ; ``inbox`` et ``sauvegardes`` valent par défaut ``<data>/…``."""
        racine = Path(racine)
        data = (racine / self.data).resolve()
        inbox = (racine / self.inbox).resolve() if self.inbox else data / "inbox"
        sauvegardes = (racine / self.sauvegardes).resolve() if self.sauvegardes else data / "sauvegardes"
        return CheminsConfig(data=data, inbox=inbox, sauvegardes=sauvegardes)


class EleveConfig(_Strict):
    prenom: str = ""
    classe: str = ""
    etablissement: str = ""
    annee_scolaire: str = "2026-2027"


class ParentConfig(_Strict):
    pin_hash: str = ""


class SauvegardeConfig(_Strict):
    automatique: Literal["aucune", "quotidienne", "hebdomadaire"] = "quotidienne"
    conserver: int = Field(default=30, ge=1)


class ChargeConfig(_Strict):
    """Charge de travail hebdomadaire de l'élève."""

    hebdo_min: int = Field(default=90, ge=0)
    seance_max_min: int = Field(default=25, ge=5)
    coefficient_vacances: float = Field(default=1.5, gt=0)


class Periode(_Strict):
    nom: str
    debut: dt.date
    fin: dt.date

    @model_validator(mode="after")
    def _fin_apres_debut(self) -> Periode:
        if self.fin < self.debut:
            raise ValueError("la fin de la période précède son début")
        return self

    def contient(self, jour: dt.date) -> bool:
        return self.debut <= jour <= self.fin


class Evaluation(_Strict):
    date: dt.date
    type: str
    chapitres: list[str] = Field(default_factory=list)
    coefficient: float = 1.0
    libelle: str = ""


class CalendrierConfig(_Strict):
    zone: Literal["A", "B", "C"] = "B"
    vacances: list[Periode] = Field(default_factory=list)
    evaluations: list[Evaluation] = Field(default_factory=list)

    def en_vacances(self, jour: dt.date) -> bool:
        """Vrai si ``jour`` tombe dans une période de vacances (bornes incluses)."""
        return any(p.contient(jour) for p in self.vacances)


class OllamaConfig(_Strict):
    url: str = "http://127.0.0.1:11434"
    timeout_s: float = Field(default=300.0, gt=0)


class SocleSettings(_Strict):
    """Racine des settings ; les disciplines en héritent pour ajouter leurs sections."""

    racine: Path = Path(".")
    app: AppConfig
    chemins: CheminsConfig = CheminsConfig()
    eleve: EleveConfig = EleveConfig()
    parent: ParentConfig = ParentConfig()
    sauvegarde: SauvegardeConfig = SauvegardeConfig()
    charge: ChargeConfig = ChargeConfig()
    calendrier: CalendrierConfig = CalendrierConfig()
    ollama: OllamaConfig = OllamaConfig()


def charger_settings[T: SocleSettings](chemin: Path | str, modele: type[T] = SocleSettings) -> T:
    """Lit ``settings.yaml`` ; la racine du projet est le parent du dossier ``config/``."""
    chemin = Path(chemin).resolve()
    brut = yaml.safe_load(chemin.read_text(encoding="utf-8")) or {}
    racine = chemin.parent.parent
    if "racine" in brut:
        raise ValueError("la clé « racine » est déduite de l'emplacement du fichier")
    reglages = modele.model_validate({**brut, "racine": racine})
    reglages.chemins = reglages.chemins.resolus(racine)
    return reglages
