# mentor-socle — kit de construction avec Claude Code

Ce dossier n'est **pas** le socle : c'est ce qu'il faut à Claude Code pour le construire, lot par lot.
Le socle sert ensuite aux quatre Mentor (Lettres, Maths, Histoire, SVT) et aux suivants.

| Dossier | Rôle |
|---|---|
| `CLAUDE.md` | Règles lues automatiquement par Claude Code |
| `docs/` | Périmètre, architecture, **contrat avec les disciplines**, modèle de données, migration des Mentor, versionnement, **plan en 12 lots**, **pièges connus**, journal |
| `tests/` | 65 tests, un fichier par lot : **la spécification exécutable** (jamais modifiés par Claude Code) |
| `assets/` | Fichiers à recopier tels quels : schéma SQL, bibliothèque Typst, pages web, squelette de Mentor |
| `.claude/commands/` | `/lot N`, `/etat`, `/revue`, `/compat`, `/evolution-socle` |

## Démarrage (Windows 11, PowerShell)

```powershell
winget install Git.Git astral-sh.uv
mkdir C:\Mentor ; cd C:\Mentor
# Décompresser le kit ici sous le nom mentor-socle, puis :
cd mentor-socle
git init ; git add . ; git commit -m "Kit de départ"
claude          # ouvre Claude Code dans ce dossier
```

Dans Claude Code :

```
/lot 0
```

Puis, à chaque lot : `/lot 1`, `/lot 2`… Entre deux lots, `/etat` pour faire le point et `/revue` pour une
relecture critique. Les lots sont courts (un à trois fichiers de code chacun) ; le plus long est le lot 4.

## Ce que vous aurez à regarder vous-même
- **Lot 6** : Claude Code produit un PDF de feuille d'exercices. L'ouvrir : QR en haut à droite non coupé, zones de
  réponse lisibles. Imprimez-le, scannez-le avec votre téléphone, déposez le scan : le test automatique ne remplace pas
  ce test-là.
- **Lot 10** : le socle seul n'a pas d'application à lancer ; l'interface est couverte par les tests. Pour la voir, créez
  l'essai du lot 11 (`uv run mentor-socle nouveau PHC "Mentor Physique-Chimie" ..\essai`), puis dans ce dossier
  `uv run mentor serve` et ouvrez http://127.0.0.1:8769.

## Si Claude Code bloque
Il consigne la question dans `docs/journal.md` (rubrique « Questions ouvertes ») plutôt que d'inventer. Répondez dans
la conversation. Un test qui paraît faux : ne pas le modifier ; demandez-lui d'expliquer, c'est probablement une
consigne du plan qui manque (dans ce cas, corrigez `docs/07-plan-lots.md`).

## Après le lot 11
1. `git tag v0.1.0`.
2. Adapter **Mentor Maths** d'abord (`docs/05-migration-des-mentor.md`), puis les trois autres.
3. Passer chaque Mentor en dépendance figée (`docs/06-versionnement.md`).

Machine de référence : Windows 11, RTX 4080 Laptop 12 Go, 32 Go de RAM. Les tests n'ont besoin ni d'Ollama ni de GPU.
