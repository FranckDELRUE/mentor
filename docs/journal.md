# Journal de développement — mentor-socle

| Date | Lot | Fait | Décisions | Dettes / à tester à la main |
|---|---|---|---|---|
| 2026-10-18 | 0 | Squelette : `__init__.py` (0.1.0), `chemins.dossier_commun()` ; `uv sync --extra dev` ; 3 tests du lot 0 verts, ruff propre | Sous Windows, repli sur `~/AppData/Local` si `LOCALAPPDATA` est absent | Aucune |
| 2026-10-18 | 1 | `config.py` (sections Pydantic strictes, `charger_settings`), `offline.py` (patch `connect`/`connect_ex`) ; tests lots 0-1 verts, ruff propre | `app` est obligatoire dans `SocleSettings` (port sans défaut) ; `racine` est un champ interdit dans le YAML, déduit du dossier `config/` ; `inbox`/`sauvegardes` par défaut sous le `data` résolu ; noms hors loopback (hors `localhost`) refusés sans résolution DNS | Aucune |

## Questions ouvertes
(Une question précise par ligne ; Claude Code les pose ici plutôt que d'inventer.)
