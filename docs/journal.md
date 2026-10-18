# Journal de développement — mentor-socle

| Date | Lot | Fait | Décisions | Dettes / à tester à la main |
|---|---|---|---|---|
| 2026-10-18 | 0 | Squelette : `__init__.py` (0.1.0), `chemins.dossier_commun()` ; `uv sync --extra dev` ; 3 tests du lot 0 verts, ruff propre | Sous Windows, repli sur `~/AppData/Local` si `LOCALAPPDATA` est absent | Aucune |
| 2026-10-18 | 1 | `config.py` (sections Pydantic strictes, `charger_settings`), `offline.py` (patch `connect`/`connect_ex`) ; tests lots 0-1 verts, ruff propre | `app` est obligatoire dans `SocleSettings` (port sans défaut) ; `racine` est un champ interdit dans le YAML, déduit du dossier `config/` ; `inbox`/`sauvegardes` par défaut sous le `data` résolu ; noms hors loopback (hors `localhost`) refusés sans résolution DNS | Aucune |
| 2026-10-18 | 2 | `gpu.py` (verrou réentrant RLock + compteur, `gpu.lock` + `gpu.detenteur.json`, copie vers `.precedent.json`), `registre.py` (`apps.json`, conflits de port) ; tests lots 0-2 verts, ruff propre | Un détenteur resté en place (processus disparu) est rendu comme précédent ; écriture de `apps.json` atomique (fichier temporaire + `replace`) sous `apps.json.lock` ; le registre est écrit même en cas de conflit | Verrou entre deux processus testé seulement via le test fourni ; `CODES_CONNUS` = `(nom, port)` |

## Questions ouvertes
(Une question précise par ligne ; Claude Code les pose ici plutôt que d'inventer.)
