# 8. Pièges connus (déjà rencontrés pendant la mise au point du socle)

À relire avant chaque lot. Chaque entrée dit le symptôme et la correction.

| # | Lot | Symptôme | Cause et correction |
|---|---|---|---|
| 1 | 0 | `uv sync` échoue : « Readme file does not exist » | `pyproject.toml` déclare `readme = "README.md"` : le fichier doit exister (il existe dans le kit). |
| 2 | 1 | `6.4e9` lu comme **chaîne** dans un YAML | PyYAML suit YAML 1.1 : la notation scientifique sans point-signe n'est pas un flottant. `referentiel.nombre()` convertit `int/float/"6.4e9"/"1/4"` ; l'utiliser pour tout nombre venant d'un référentiel. |
| 3 | 2 | Le verrou GPU se bloque lui-même dans une tâche qui enchaîne deux modèles | Deux `FileLock` dans le même processus s'excluent. Le verrou doit être **réentrant** : `threading.RLock` + compteur de profondeur, un seul `FileLock` pris au niveau 0. |
| 4 | 3 | Une migration à moitié appliquée reste en base | `executescript` valide implicitement la transaction. Découper avec `sqlite3.complete_statement`, exécuter instruction par instruction entre `BEGIN` et `COMMIT`, `ROLLBACK` sur erreur (la connexion est en `isolation_level=None`). |
| 5 | 4 | Un prompt avec une variable oubliée produit un texte « troué » sans erreur | Jinja doit être en **`StrictUndefined`**. |
| 6 | 4 | La réponse du modèle est entourée de ```` ```json ```` | `_extraire_json` : retirer les clôtures, puis prendre du premier `{` au dernier `}`. |
| 7 | 4 | Le test de réparation reçoit le JSON entre guillemets | `FauxLLM` : une `str` est renvoyée telle quelle ; un `dict` est sérialisé en JSON. Une **liste** est convertie en `deque` consommé dans l'ordre (la dernière réponse est répétée). |
| 8 | 4 | Le modèle 24 B ne tient pas avec le modèle de vision en VRAM (12 Go) | Avant chaque appel, décharger (`keep_alive=0`) tous les modèles chargés **autres** que celui du rôle. |
| 9 | 5 | `TypeError: 'Event' object is not callable` à `join()` | Un attribut `self._stop` écrase la méthode interne `Thread._stop`. Nommer l'événement autrement (`self._arret`). |
| 10 | 5 | Deux travailleurs prennent la même tâche | `prendre` doit être **une seule instruction** : `UPDATE … WHERE id = (SELECT … LIMIT 1) RETURNING *`. |
| 11 | 6 | QR illisible une fois le PDF scanné, ou **coupé** en haut de page | Marge haute de 3,5 cm + `header-ascent: 0.5cm` ; QR de 2,1 cm minimum, correction d'erreur **H**, bordure blanche de 2 modules. Le test relit le QR du PDF rendu : ne pas le contourner. |
| 12 | 6 | Le QR de la page 2 dit « page 1/1 » | Rendre **deux fois** : première passe pour compter les pages (QR provisoires), seconde passe avec le bon total. |
| 13 | 6 | `TypeError: cannot unpack non-iterable numpy.int32` dans `redresser` | OpenCV 5 : `HoughLinesP` renvoie un tableau dont la forme change. Utiliser `np.asarray(lignes).reshape(-1, 4)`. |
| 14 | 6 | Image introuvable avec un chemin accentué sous Windows | `cv2.imread` ne gère pas l'Unicode : lire avec `np.fromfile` + `cv2.imdecode`, écrire avec `cv2.imencode` + `tofile`. |
| 15 | 6 | Contenu des exercices injecté dans Typst | Le contenu (écrit par un modèle) est évalué en mode « markup » : compiler avec `root=` le dossier temporaire pour qu'aucun fichier extérieur ne soit lisible. Ne jamais passer de contenu élève non nettoyé dans `eval`. |
| 16 | 6 | `sqlite3.Row` refusé par les portes | Les portes reçoivent un **`dict`** (`dict(row)`). |
| 17 | 7 | Le test de doublon ne détecte rien | Deux rendus PDF du même scan diffèrent. Le test **recopie le même fichier** ; le code compare le SHA-256 du fichier reçu. |
| 18 | 7 | Un fichier est déplacé dans la boîte d'un autre Mentor, mais ce Mentor n'est pas enregistré | Si le code QR n'est pas dans le registre, ne pas déplacer le fichier : le traiter comme un scan sans feuille reconnue (type `a_classer` + validation « Type de document à préciser »). |
| 19 | 9 | La sauvegarde est corrompue si l'application écrit en même temps | Utiliser `Connection.backup()`, jamais une copie du fichier `.sqlite3` (le mode WAL a des fichiers annexes). |
| 20 | 10 | Avertissement de dépréciation httpx dans les tests web | Sans conséquence ; les tests tournent avec `-p no:warnings` si besoin. |
| 21 | 11 | Le test de `nouveau` importe deux fois le même nom de paquet | Retirer le paquet de `sys.modules` et de `sys.path` en fin de test (déjà fait dans les tests fournis). |

## Conventions de code attendues
- Python 3.12, types partout, fonctions courtes, docstrings en français, pas de dépendance POSIX (`pathlib`).
- Aucune ressource réseau à l'exécution : pas de CDN, pas de police distante, pas de télémétrie.
- Les noms du domaine sont en français (`feuille`, `copie`, `porte`, `taches`) ; les identifiants techniques peuvent être en anglais.
- Un lot ne touche pas aux fichiers de `tests/` : si un test paraît faux, s'arrêter et le signaler dans `docs/journal.md`.
