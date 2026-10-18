# 6. Versions et évolution du socle

## Dépendance depuis un Mentor

Développement (le socle à côté, modifications visibles tout de suite) :

```toml
[project]
dependencies = ["mentor-socle>=0.1,<0.2"]

[tool.uv.sources]
mentor-socle = { path = "../mentor-socle", editable = true }
```

Stabilisé (chaque Mentor figé sur une version taguée du dépôt Git local) :

```toml
[tool.uv.sources]
mentor-socle = { git = "file:///C:/Mentor/mentor-socle", tag = "v0.1.0" }
```

Passer en mode figé dès qu'un Mentor est utilisé au quotidien : une évolution du socle pour Maths ne
doit jamais casser Lettres la veille d'un DS.

## Numérotation

- `0.x` tant que le contrat bouge : un changement de mineure (`0.1` → `0.2`) peut casser ; d'où la borne `<0.2`.
- Correctifs : `0.1.1`, `0.1.2` — sans changement de contrat ni de schéma.
- Toute migration SQL du socle est **additive** (nouvelles tables, colonnes avec défaut) ; jamais de
  suppression ni de renommage en `0.x`. Elle s'applique automatiquement à l'ouverture de chaque Mentor.

## Faire évoluer le socle

1. Le besoin est noté dans le `docs/journal.md` d'un Mentor, rubrique « Pour le socle ».
2. Vérifier la règle de `01-perimetre.md` (au moins deux Mentor, rien de disciplinaire, testable sans modèle).
3. Coder dans `mentor-socle` avec ses tests ; mettre à jour `CHANGELOG.md` et la doc du contrat.
4. Lancer les tests du socle **et** ceux de chaque Mentor installé (`/compat` dans Claude Code).
5. Taguer (`git tag v0.1.1`), puis monter la version dans chaque Mentor un par un.
