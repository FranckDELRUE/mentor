"""Rôles de modèles : un nom de rôle (vision, correcteur…) désigne un modèle Ollama et ses options."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

_FICHIERS = ("modeles.yaml", "models.yaml", "modeles.example.yaml", "models.example.yaml")


class Role(BaseModel):
    model_config = ConfigDict(extra="forbid")

    modele: str
    options: dict[str, Any] = Field(default_factory=dict)
    keep_alive: str = "5m"
    verrou_gpu: bool = True
    description: str = ""


class RegistreModeles(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roles: dict[str, Role] = Field(default_factory=dict)

    def role(self, nom: str) -> Role:
        """Le rôle ``nom`` ; ``KeyError`` explicite s'il n'est pas déclaré."""
        try:
            return self.roles[nom]
        except KeyError:
            connus = ", ".join(self.roles) or "aucun"
            raise KeyError(f"rôle de modèle inconnu : « {nom} » (connus : {connus})") from None


def charger_modeles(dossier_config: Path | str) -> RegistreModeles:
    """Lit ``modeles.yaml``, sinon ``models.yaml``, sinon les fichiers ``.example``."""
    dossier = Path(dossier_config)
    for nom in _FICHIERS:
        fichier = dossier / nom
        if fichier.is_file():
            brut = yaml.safe_load(fichier.read_text(encoding="utf-8")) or {}
            return RegistreModeles.model_validate(brut)
    raise FileNotFoundError(f"aucun fichier de modèles dans {dossier} (attendu : {_FICHIERS[0]})")
