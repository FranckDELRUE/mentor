"""Base SQLite commune : connexion, migrations par espace, aide JSON."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from importlib import resources
from pathlib import Path
from typing import Any

ESPACE_SOCLE = "socle"

_CREATION_SUIVI = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    espace     TEXT NOT NULL,
    version    TEXT NOT NULL,
    applique_le TEXT NOT NULL,
    PRIMARY KEY (espace, version)
)
"""


def connecter(chemin: Path | str) -> sqlite3.Connection:
    """Ouvre la base (créée avec ses dossiers) en WAL, clés étrangères actives, transactions manuelles."""
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    cx = sqlite3.connect(chemin, isolation_level=None, check_same_thread=False, timeout=30)
    cx.row_factory = sqlite3.Row
    cx.execute("PRAGMA journal_mode=WAL")
    cx.execute("PRAGMA foreign_keys=ON")
    cx.execute("PRAGMA busy_timeout=30000")
    return cx


def _instructions(sql: str) -> list[str]:
    """Découpe un script en instructions complètes (sans `executescript`, qui valide implicitement)."""
    resultat: list[str] = []
    courante = ""
    for ligne in sql.splitlines(keepends=True):
        courante += ligne
        if sqlite3.complete_statement(courante):
            resultat.append(courante)
            courante = ""
    if courante.strip():
        resultat.append(courante)
    return resultat


def _appliquer(cx: sqlite3.Connection, espace: str, nom: str, sql: str) -> None:
    """Applique une migration et la note dans `schema_migrations`, en une transaction annulée si erreur."""
    cx.execute("BEGIN")
    try:
        for instruction in _instructions(sql):
            cx.execute(instruction)
        cx.execute("INSERT INTO schema_migrations (espace, version, applique_le) VALUES (?, ?, ?)",
                   (espace, nom, datetime.now().isoformat(timespec="seconds")))
        cx.execute("COMMIT")
    except BaseException:
        cx.execute("ROLLBACK")
        raise


def _migrations_socle() -> list[tuple[str, str]]:
    racine = resources.files("mentor_socle.db").joinpath("sql")
    fichiers = sorted((f for f in racine.iterdir() if f.name.endswith(".sql")), key=lambda f: f.name)
    return [(f.name, f.read_text(encoding="utf-8")) for f in fichiers]


def _migrations_dossier(dossier: Path) -> list[tuple[str, str]]:
    return [(f.name, f.read_text(encoding="utf-8")) for f in sorted(Path(dossier).glob("*.sql"))]


def migrer(cx: sqlite3.Connection, espace: str | None = None, dossier: Path | str | None = None) -> list[str]:
    """Applique les migrations du socle puis celles de la discipline `espace` (dossier `dossier`).

    Renvoie les noms « espace/fichier » nouvellement appliqués ; un second appel renvoie `[]`.
    """
    cx.execute(_CREATION_SUIVI)
    groupes = [(ESPACE_SOCLE, _migrations_socle())]
    if espace and dossier:
        groupes.append((espace, _migrations_dossier(Path(dossier))))
    appliques: list[str] = []
    for nom_espace, migrations in groupes:
        deja = {r[0] for r in cx.execute("SELECT version FROM schema_migrations WHERE espace = ?",
                                         (nom_espace,))}
        for nom, sql in migrations:
            if nom not in deja:
                _appliquer(cx, nom_espace, nom, sql)
                appliques.append(f"{nom_espace}/{nom}")
    return appliques


def js(valeur: Any) -> str:
    """Sérialise en JSON en conservant les accents."""
    return json.dumps(valeur, ensure_ascii=False)


def dejs(texte: str | None, defaut: Any = None) -> Any:
    """Relit un JSON stocké ; `defaut` si le texte est vide ou absent."""
    if texte is None or texte == "":
        return defaut
    return json.loads(texte)
