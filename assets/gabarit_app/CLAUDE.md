# CLAUDE.md — __NOM__

Professeur virtuel **100 % local**, travail **sur papier** (l'élève ne touche pas l'ordinateur), bâti
sur **mentor-socle** (`../mentor-socle`).

## Règle n°1 : ne pas réécrire le socle
Configuration, verrou GPU, appels de modèles (`appel_structure`), base et migrations, file de tâches,
inbox et QR, transcription générique, rendu PDF (Typst), portes avant impression, répétition espacée,
modèle de l'élève, taxonomie d'erreurs, planificateur, interface parent, sauvegarde, CLI : **tout est
dans mentor-socle**. Avant d'écrire du code, lis `../mentor-socle/docs/03-contrat-discipline.md`.
Si le socle ne couvre pas un besoin commun à plusieurs Mentor, **ne le contourne pas ici** : note-le
dans `docs/journal.md` (rubrique « Pour le socle ») et propose une évolution du socle.

## Ce qui vit ici
- `src/__PAQUET__/discipline.py` — la classe `__CLASSE__` (points d'extension).
- `referentiel/` — programme officiel, grilles, taxonomie d'erreurs (YAML, sourcés).
- `prompts/` — un fichier par tâche de modèle (en-tête `role`, `version`), sortie JSON.
- `templates/` — gabarits Typst (`#import "mentor.typ": *`) et pages web (`templates/web/`).
- `migrations/` — tables propres à la discipline (préfixe `__code___`).

## Règles communes à tous les Mentor
1. Données de l'élève (mineur) : jamais versionnées, jamais envoyées sur le réseau ; tests sur données fictives.
2. Papier d'abord : toute fonctionnalité élève produit un PDF ; l'interface web sert au parent.
3. Le cours du professeur fait foi ; le référentiel officiel sert de garde-fou.
4. Tout fait d'une feuille générée est sourcé (`seg:…` ou `ref:…`) ; tout calcul est recalculé par le code.
5. Aucun appel de modèle hors `mentor_socle.llm.appel_structure` (schéma Pydantic, verrou GPU, journal).
6. Le code orchestre, les fichiers décrivent : rien du référentiel ni des prompts en dur dans le code.

## Commandes
- `uv sync` · `uv run mentor check` · `uv run mentor serve` (http://127.0.0.1:__PORT__)
- `uv run pytest -q` · `uv run mentor kit` · `uv run mentor plan`
