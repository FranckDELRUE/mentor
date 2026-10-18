# CLAUDE.md — mentor-socle (construction)

Tu construis **mentor-socle**, le paquet Python commun des applications Mentor (professeurs virtuels
100 % locaux, travail sur papier, élève mineur). Plusieurs applications en dépendront : la qualité de ce
paquet compte plus que sa vitesse de réalisation.

## À lire avant tout travail
1. `docs/01-perimetre.md` — ce qui a sa place dans le socle (règle des trois conditions).
2. `docs/02-architecture.md` — modules, flux papier, ressources partagées.
3. `docs/03-contrat-discipline.md` — le contrat avec les disciplines (c'est l'API publique).
4. `docs/07-plan-lots.md` — **ne réaliser que le lot demandé**, avec les signatures attendues.
5. `docs/08-pieges.md` — erreurs déjà rencontrées : ne pas les refaire.

## Méthode
- **Les tests sont la spécification** (`tests/test_lotNN_*.py`, déjà écrits). Ne les modifie jamais. S'ils te
  semblent faux ou contradictoires, arrête-toi et consigne la question dans `docs/journal.md`.
- Un lot à la fois, dans l'ordre. Un lot est fini quand ses tests passent **et** que les précédents passent encore.
- Les fichiers de `assets/` (SQL, Typst, pages web, gabarit de Mentor) sont à **recopier tels quels** aux lots
  indiqués ; ne les réécris pas.
- Vérifie le rendu réel : au lot 6, ouvre le PDF produit (convertis une page en PNG et regarde-la) ; au lot 10,
  lance `serve` et regarde la page.
- À la fin de chaque lot : `uv run pytest`, `uv run ruff check src`, une ligne dans `docs/journal.md`
  (date, lot, fait, décisions, dettes), un commit `lot NN : titre`.

## Règles du projet
1. **Rien de disciplinaire** dans le code : ni notion, ni grille, ni notation, ni nom d'œuvre.
2. **Hors ligne** : aucune dépendance réseau à l'exécution ; Ollama en local uniquement.
3. **Un seul chemin vers les modèles** : `llm.appel_structure` (schéma, verrou GPU, réparation, journal).
4. **Migrations additives** uniquement ; le schéma commun est `assets/sql/0001_socle.sql`.
5. **Testable sans modèle** : tout passe par `ClientLLM` (protocole) ; `FauxLLM` pour les tests.
6. **Windows 11** en cible : `pathlib`, pas de dépendance POSIX, chemins accentués, encodage UTF-8 explicite.
7. Textes visibles en français ; docstrings en français.
8. Ne jamais écrire de donnée d'élève réelle dans le dépôt ni dans les tests.

## Commandes
- `uv sync --extra dev` · `uv run pytest` · `uv run pytest tests/test_lot04_modeles.py` · `uv run ruff check src`
- `/lot N` — réaliser le lot N · `/etat` — où en est-on · `/revue` — relecture avant de passer au lot suivant
