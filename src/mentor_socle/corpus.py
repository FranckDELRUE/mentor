"""Corpus du cours : segments sourcés et recherche sémantique (vecteurs NumPy normalisés, float32)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import numpy as np

from mentor_socle.db import js
from mentor_socle.llm.structure import embeddings

if TYPE_CHECKING:
    from mentor_socle.contexte import Contexte

LOT_EMBEDDINGS = 32


def ajouter_segment(
    ctx: Contexte, code: str, chapitre: str, texte: str, *, nature: str = "cours",
    document_id: int | None = None, zone_ids: list[int] | None = None, meta: dict[str, Any] | None = None,
) -> int:
    """Crée ou remplace le segment ``code`` ; son embedding est remis à NULL (à réindexer)."""
    ctx.cx.execute(
        "INSERT INTO segments(code, chapitre, document_id, zone_ids, texte, nature, embedding, meta) "
        "VALUES (?, ?, ?, ?, ?, ?, NULL, ?) "
        "ON CONFLICT(code) DO UPDATE SET chapitre=excluded.chapitre, document_id=excluded.document_id, "
        "zone_ids=excluded.zone_ids, texte=excluded.texte, nature=excluded.nature, "
        "embedding=NULL, meta=excluded.meta",
        (code, chapitre, document_id, js(zone_ids or []), texte, nature, js(meta or {})),
    )
    return ctx.cx.execute("SELECT id FROM segments WHERE code = ?", (code,)).fetchone()["id"]


def _normaliser(vecteurs: list[list[float]]) -> np.ndarray:
    m = np.asarray(vecteurs, dtype=np.float32).reshape(len(vecteurs), -1)
    normes = np.linalg.norm(m, axis=1, keepdims=True)
    return m / np.where(normes == 0, 1.0, normes)


def indexer(ctx: Contexte) -> int:
    """Calcule l'embedding des segments qui n'en ont pas ; rend leur nombre."""
    lignes = ctx.cx.execute("SELECT id, texte FROM segments WHERE embedding IS NULL ORDER BY id").fetchall()
    for debut in range(0, len(lignes), LOT_EMBEDDINGS):
        lot = lignes[debut:debut + LOT_EMBEDDINGS]
        vecteurs = _normaliser(embeddings(ctx, [ligne["texte"] for ligne in lot]))
        for ligne, v in zip(lot, vecteurs, strict=True):
            ctx.cx.execute("UPDATE segments SET embedding = ? WHERE id = ?", (v.tobytes(), ligne["id"]))
    return len(lignes)


def rechercher(
    ctx: Contexte, requete: str, k: int = 5, chapitres: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Les ``k`` segments indexés les plus proches de ``requete`` (à égalité : ordre de création)."""
    sql, params = "SELECT * FROM segments WHERE embedding IS NOT NULL", []
    if chapitres:
        sql += f" AND chapitre IN ({','.join('?' * len(chapitres))})"
        params = list(chapitres)
    lignes = ctx.cx.execute(sql + " ORDER BY id", params).fetchall()
    if not lignes:
        return []
    matrice = np.stack([np.frombuffer(ligne["embedding"], dtype=np.float32) for ligne in lignes])
    q = _normaliser(embeddings(ctx, [requete]))[0]
    scores = matrice @ q
    ordre = np.argsort(-scores, kind="stable")[:k]
    return [
        {
            "code": lignes[i]["code"], "chapitre": lignes[i]["chapitre"], "texte": lignes[i]["texte"],
            "nature": lignes[i]["nature"], "zone_ids": json.loads(lignes[i]["zone_ids"]),
            "score": float(scores[i]),
        }
        for i in ordre
    ]
