"""Prompts : fichiers Markdown à en-tête YAML, rendus avec Jinja en mode strict."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jinja2 import Environment, StrictUndefined

_ENV = Environment(undefined=StrictUndefined, autoescape=False, keep_trailing_newline=False)
_ENV.filters["tojson"] = lambda v, **kw: json.dumps(v, ensure_ascii=False, **kw)

_ENTETE = re.compile(r"\A---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)
_TITRE = re.compile(r"^# (Système|Utilisateur)[ \t]*$", re.MULTILINE)


@dataclass
class Prompt:
    nom: str
    role: str
    version: str
    systeme: str
    utilisateur: str | None
    meta: dict[str, Any] = field(default_factory=dict)

    def rendre(self, **variables: Any) -> list[dict[str, str]]:
        """Messages ``system`` (puis ``user`` s'il y en a un) ; variable manquante : ``UndefinedError``."""
        messages = [{"role": "system", "content": _ENV.from_string(self.systeme).render(**variables).strip()}]
        if self.utilisateur is not None:
            messages.append(
                {"role": "user", "content": _ENV.from_string(self.utilisateur).render(**variables).strip()}
            )
        return messages


def lire_prompt(chemin: Path | str) -> Prompt:
    """Lit un prompt ; ``ValueError`` si l'en-tête YAML ou son champ ``role`` manque."""
    chemin = Path(chemin)
    texte = chemin.read_text(encoding="utf-8").lstrip("﻿")
    entete = _ENTETE.match(texte)
    if not entete:
        raise ValueError(f"{chemin.name} : en-tête YAML (---) obligatoire")
    meta = yaml.safe_load(entete.group(1)) or {}
    if not isinstance(meta, dict) or not meta.get("role"):
        raise ValueError(f"{chemin.name} : le champ « role » est obligatoire dans l'en-tête")
    corps = texte[entete.end():]
    systeme, utilisateur = "", None
    titres = list(_TITRE.finditer(corps))
    if not titres:
        systeme = corps
    for i, titre in enumerate(titres):
        fin = titres[i + 1].start() if i + 1 < len(titres) else len(corps)
        section = corps[titre.end():fin]
        if titre.group(1) == "Système":
            systeme = section
        else:
            utilisateur = section
    role, version = meta.pop("role"), meta.pop("version", 0)
    return Prompt(
        nom=chemin.stem,
        role=str(role),
        version=str(version),
        systeme=systeme.strip(),
        utilisateur=None if utilisateur is None else utilisateur.strip(),
        meta=meta,
    )


class BibliothequePrompts:
    """Les prompts d'un dossier, lus à la demande (modifiables sans redémarrer)."""

    def __init__(self, dossier: Path | str):
        self.dossier = Path(dossier)

    def __getitem__(self, nom: str) -> Prompt:
        fichier = self.dossier / f"{nom}.md"
        if not fichier.is_file():
            raise KeyError(f"prompt introuvable : « {nom} » (dossier {self.dossier})")
        return lire_prompt(fichier)

    def tous(self) -> dict[str, Prompt]:
        return {f.stem: lire_prompt(f) for f in sorted(self.dossier.glob("*.md"))}
