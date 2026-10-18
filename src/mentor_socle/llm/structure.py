"""Seul chemin vers les modèles : sortie structurée, verrou GPU, réparation et journal."""

from __future__ import annotations

import hashlib
import json
import re
import time
from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ValidationError

from mentor_socle import gpu
from mentor_socle.llm.ollama import image_b64

if TYPE_CHECKING:
    from mentor_socle.contexte import Contexte


class SortieInvalide(ValueError):
    """Le modèle n'a pas produit une sortie conforme au schéma, même après réparation."""


_CLOTURE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _extraire_json(texte: str) -> str:
    """Retire les clôtures Markdown puis garde du premier ``{`` au dernier ``}``."""
    clos = _CLOTURE.search(texte)
    if clos:
        texte = clos.group(1)
    debut, fin = texte.find("{"), texte.rfind("}")
    return texte[debut:fin + 1] if 0 <= debut < fin else texte.strip()


def _erreurs(e: ValidationError) -> str:
    return "\n".join(
        f"- {'.'.join(str(p) for p in err['loc']) or '(racine)'} : {err['msg']}" for err in e.errors()
    )


def _decharger_autres(ctx: Contexte, modele: str) -> None:
    for charge in ctx.llm.modeles_charges():
        if charge != modele:
            ctx.llm.decharger(charge)


def _journaliser(ctx: Contexte, **c: Any) -> None:
    ctx.cx.execute(
        "INSERT INTO llm_appels (role, modele, prompt, version_prompt, entree_sha256, sortie, ok,"
        " reparation, erreur, duree_ms, tache_id) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (c["role"], c["modele"], c["prompt"], c["version"], c["sha"], c["sortie"], c["ok"],
         c["reparation"], c["erreur"], c["duree_ms"], c["tache_id"]),
    )


def appel_structure[S: BaseModel](
    ctx: Contexte,
    prompt: str,
    schema: type[S],
    *,
    images: list[Path | str] | None = None,
    tache_id: int | None = None,
    **variables: Any,
) -> S:
    """Rend le prompt, interroge le modèle du rôle et renvoie une instance valide de ``schema``.

    Une seule relance de réparation ; ``SortieInvalide`` ensuite. Une ligne de ``llm_appels`` par
    appel (``reparation`` = 1 si la relance a eu lieu). Verrou GPU pris si le rôle l'exige.
    """
    modele_prompt = ctx.prompts[prompt]
    role = ctx.modeles.role(modele_prompt.role)
    messages = modele_prompt.rendre(**variables)
    if images:
        messages[-1]["images"] = [image_b64(i) for i in images]
    if hasattr(ctx.llm, "prompt_courant"):
        ctx.llm.prompt_courant = prompt
    sha = hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    debut = time.monotonic()
    sortie, erreur, resultat, reparation = "", None, None, 0
    verrou = gpu.verrou(ctx.discipline.nom, prompt) if role.verrou_gpu else nullcontext()
    with verrou:
        if role.verrou_gpu:
            _decharger_autres(ctx, role.modele)
        for tentative in (0, 1):
            sortie = ctx.llm.chat(
                role.modele, messages, format=schema.model_json_schema(),
                options=role.options or None, keep_alive=role.keep_alive,
            )
            try:
                resultat = schema.model_validate_json(_extraire_json(sortie))
                erreur = None
                break
            except ValidationError as e:
                erreur = _erreurs(e)
            if tentative == 0:
                reparation = 1
                messages = [
                    *messages,
                    {"role": "assistant", "content": sortie},
                    {"role": "user", "content": "Ta réponse est invalide. Erreurs :\n" + erreur
                     + "\nRéponds uniquement avec un JSON valide conforme au schéma."},
                ]
    _journaliser(
        ctx, role=modele_prompt.role, modele=role.modele, prompt=prompt, version=modele_prompt.version,
        sha=sha, sortie=sortie, ok=int(resultat is not None), reparation=reparation, erreur=erreur,
        duree_ms=int((time.monotonic() - debut) * 1000), tache_id=tache_id,
    )
    if resultat is None:
        raise SortieInvalide(f"sortie invalide pour le prompt « {prompt} » après réparation :\n{erreur}")
    return resultat


def embeddings(ctx: Contexte, textes: list[str], role: str = "embeddings") -> list[list[float]]:
    """Vecteurs des ``textes`` ; le GPU n'est verrouillé que si le rôle le demande."""
    r = ctx.modeles.role(role)
    verrou = gpu.verrou(ctx.discipline.nom, f"embeddings:{role}") if r.verrou_gpu else nullcontext()
    with verrou:
        return ctx.llm.embed(r.modele, textes)
