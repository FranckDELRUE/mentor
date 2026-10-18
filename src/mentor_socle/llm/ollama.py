"""Client Ollama local (httpx) et protocole ``ClientLLM`` que les tests remplacent par ``FauxLLM``."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Protocol

import httpx


class ClientLLM(Protocol):
    def chat(
        self,
        modele: str,
        messages: list[dict[str, Any]],
        *,
        format: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
        keep_alive: str | int | None = None,
    ) -> str: ...

    def embed(self, modele: str, textes: list[str]) -> list[list[float]]: ...

    def modeles_charges(self) -> list[str]: ...

    def decharger(self, modele: str) -> None: ...


def image_b64(chemin: Path | str) -> str:
    """Contenu d'une image en base64 (format attendu par Ollama)."""
    return base64.b64encode(Path(chemin).read_bytes()).decode("ascii")


class ClientOllama:
    """Accès HTTP à Ollama, local uniquement (``trust_env=False`` : aucun proxy d'environnement)."""

    def __init__(self, url: str = "http://127.0.0.1:11434", timeout_s: float = 300.0):
        self._http = httpx.Client(base_url=url, timeout=timeout_s, trust_env=False)

    def _post(self, chemin: str, corps: dict[str, Any]) -> dict[str, Any]:
        reponse = self._http.post(chemin, json=corps)
        reponse.raise_for_status()
        return reponse.json()

    def _lire(self, chemin: str) -> dict[str, Any]:
        reponse = self._http.get(chemin)
        reponse.raise_for_status()
        return reponse.json()

    def chat(self, modele, messages, *, format=None, options=None, keep_alive=None) -> str:
        corps: dict[str, Any] = {"model": modele, "messages": messages, "stream": False}
        if format is not None:
            corps["format"] = format
        if options:
            corps["options"] = options
        if keep_alive is not None:
            corps["keep_alive"] = keep_alive
        return self._post("/api/chat", corps)["message"]["content"]

    def embed(self, modele: str, textes: list[str]) -> list[list[float]]:
        return self._post("/api/embed", {"model": modele, "input": textes})["embeddings"]

    def modeles_charges(self) -> list[str]:
        return [m["name"] for m in self._lire("/api/ps").get("models", [])]

    def modeles_installes(self) -> list[str]:
        return [m["name"] for m in self._lire("/api/tags").get("models", [])]

    def version(self) -> str:
        return self._lire("/api/version")["version"]

    def decharger(self, modele: str) -> None:
        self._post("/api/chat", {"model": modele, "messages": [], "keep_alive": 0})
