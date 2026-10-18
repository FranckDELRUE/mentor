"""Outils de test pour le socle et pour les Mentor : faux modèle et contexte jetable."""

from __future__ import annotations

import json
import os
import shutil
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml

from mentor_socle.contexte import Contexte
from mentor_socle.discipline import Discipline

_MODELES_PAR_DEFAUT = {
    "roles": {
        "vision": {"modele": "faux-vision"},
        "generateur": {"modele": "faux-generateur"},
        "correcteur": {"modele": "faux-correcteur"},
        "embeddings": {"modele": "faux-embed", "verrou_gpu": False},
    }
}


class FauxLLM:
    """Client de test : la réponse est choisie par le nom du prompt (``prompt_courant``).

    Une réponse peut être une ``str`` (rendue telle quelle), un ``dict`` (sérialisé en JSON), une
    fonction ``(messages) -> str | dict`` ou une **liste** consommée dans l'ordre (la dernière est
    répétée). ``file`` sert de réponse par défaut quand le prompt n'a pas de réponse propre.
    """

    def __init__(self, reponses: dict[str, Any] | None = None, file: list[Any] | None = None,
                 vecteur: Callable[[str], list[float]] | list[float] | None = None):
        self.reponses: dict[str, Any] = reponses if reponses is not None else {}
        self._file_defaut = file
        self._files: dict[str, tuple[int, deque]] = {}
        if vecteur is None:
            vecteur = [0.0, 1.0]
        self._vecteur: Callable[[str], list[float]] = vecteur if callable(vecteur) else (lambda _t: list(vecteur))
        self.appels: list[dict[str, Any]] = []
        self.decharges: list[str] = []
        self.charges: list[str] = []
        self.prompt_courant: str | None = None

    def _choisir(self, messages: list[dict[str, Any]]) -> Any:
        nom = self.prompt_courant or ""
        if nom in self.reponses:
            source = self.reponses[nom]
        elif self._file_defaut is not None:
            nom, source = "", self._file_defaut
        else:
            raise KeyError(f"FauxLLM : aucune réponse prévue pour le prompt « {nom} »")
        if callable(source):
            return source(messages)
        if isinstance(source, list):
            identite, file = self._files.get(nom, (None, None))
            if identite != id(source):
                file = deque(source)
                self._files[nom] = (id(source), file)
            return file.popleft() if len(file) > 1 else file[0]
        return source

    def chat(self, modele, messages, *, format=None, options=None, keep_alive=None) -> str:
        self.appels.append({"modele": modele, "messages": [dict(m) for m in messages], "format": format,
                            "options": options, "keep_alive": keep_alive, "prompt": self.prompt_courant})
        reponse = self._choisir(messages)
        return reponse if isinstance(reponse, str) else json.dumps(reponse, ensure_ascii=False)

    def embed(self, modele: str, textes: list[str]) -> list[list[float]]:
        return [self._vecteur(t) for t in textes]

    def modeles_charges(self) -> list[str]:
        return list(self.charges)

    def decharger(self, modele: str) -> None:
        self.decharges.append(modele)
        if modele in self.charges:
            self.charges.remove(modele)


def _fusion(base: dict[str, Any], ajout: dict[str, Any]) -> dict[str, Any]:
    for cle, valeur in ajout.items():
        if isinstance(valeur, dict) and isinstance(base.get(cle), dict):
            _fusion(base[cle], valeur)
        else:
            base[cle] = valeur
    return base


def contexte_de_test(cls: type[Discipline], dossier: Path | str, *, llm: Any = None,
                     racine_kit: Path | str | None = None, settings: dict[str, Any] | None = None) -> Contexte:
    """Contexte jetable : copie le kit dans ``dossier``, écrit des settings et modèles de test.

    Le verrou GPU et le registre sont isolés dans ``dossier/_commun`` (``MENTOR_COMMUN``).
    """
    dossier = Path(dossier)
    os.environ["MENTOR_COMMUN"] = str(dossier / "_commun")
    if racine_kit is not None:
        for sous in ("referentiel", "prompts", "templates", "migrations"):
            source = Path(racine_kit) / sous
            if source.is_dir():
                shutil.copytree(source, dossier / sous, dirs_exist_ok=True)
    (dossier / "templates").mkdir(exist_ok=True)  # les tests d'impression y déposent leurs gabarits
    config = dossier / "config"
    config.mkdir(parents=True, exist_ok=True)
    reglages = _fusion({"app": {"port": cls.port_defaut, "strict_offline": False}}, settings or {})
    (config / "settings.yaml").write_text(yaml.safe_dump(reglages, allow_unicode=True), encoding="utf-8")
    modeles = Path(racine_kit) / "config" / "modeles.example.yaml" if racine_kit else None
    contenu = (modeles.read_text(encoding="utf-8") if modeles and modeles.is_file()
               else yaml.safe_dump(_MODELES_PAR_DEFAUT))
    (config / "modeles.yaml").write_text(contenu, encoding="utf-8")
    return Contexte.ouvrir(cls(dossier), llm=llm if llm is not None else FauxLLM())
