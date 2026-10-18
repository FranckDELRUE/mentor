---
description: Réaliser un lot du plan de développement (ex. /lot 3)
argument-hint: "<numéro du lot>"
---
Réalise le lot $ARGUMENTS de `docs/04-plan-lots.md`.

1. Relis `CLAUDE.md`, la ligne du lot, les sections concernées des docs, la dernière entrée de `docs/journal.md`,
   et `../mentor-socle/docs/03-contrat-discipline.md`.
2. Liste ce que le socle fournit déjà pour ce lot : n'écris que la partie propre à la discipline.
3. Propose un plan court (fichiers, tests, critère de fin) ; attends mon accord s'il touche au référentiel,
   au schéma de base ou aux prompts.
4. Implémente avec tests (données fictives, `mentor_socle.testing`).
5. `uv run pytest -q` et `uv run mentor kit` doivent passer.
6. Ajoute une ligne à `docs/journal.md` (y compris « Pour le socle » si un besoin commun est apparu).
