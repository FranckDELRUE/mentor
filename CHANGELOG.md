# Journal des versions

Numérotation et règles : voir `docs/06-versionnement.md`.

## 0.1.0 — 2026-10-18

Première version : lots 1 à 11 du plan (`docs/07-plan-lots.md`).

- Schéma commun `0001_socle.sql` et migrations additives.
- Contrat de discipline (`Discipline`, `Contexte`), réglages, registre des Mentor installés.
- Accès aux modèles par `llm.appel_structure` seul (schéma, verrou GPU, réparation, journal) ; `FauxLLM` pour les tests.
- File de tâches et travailleur ; boîte de dépôt, impression Typst, sauvegarde automatique.
- Interface parent (FastAPI) avec PIN ; bandeau quand le travailleur est arrêté.
- CLI `mentor` (`check`, `serve`, `worker`, `inbox`, `migrate`, `backup`, `kit`, `plan`, `gpu`, `parent set-pin`)
  et `mentor-socle` (`nouveau`, `registre`, `gpu`) ; gabarit de nouveau Mentor.

Limites connues :
- `test_cli_sur_un_mentor_cree` suppose Ollama absent : il échoue sur un poste où Ollama tourne avec les modèles.
- Ctrl+C réel sur `serve` et `worker` (simple et double) à confirmer à la main après les derniers changements.
