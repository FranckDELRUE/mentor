# 7. Plan de développement en 12 lots

Principe : **les tests sont la spécification**. Chaque lot a son fichier `tests/test_lotNN_*.py`, déjà écrit.
Un lot est terminé quand ses tests passent **et** que ceux des lots précédents passent encore
(`uv run pytest`). Les tests des lots suivants échouent tant qu'ils ne sont pas réalisés : c'est normal.
Un lot = un commit (`lot NN : titre`).

Tous les modules sont sous `src/mentor_socle/`. Les signatures ci-dessous sont celles que les tests
utilisent ; tout ce qui n'y figure pas est libre. Les fichiers de `assets/` sont à **recopier tels quels**
(SQL, bibliothèque Typst, pages web) : ne pas les réécrire.

Avant chaque lot : lire `docs/08-pieges.md` (erreurs déjà rencontrées, avec leur correction).

| Lot | Contenu | Tests |
|---|---|---|
| 0 | Squelette du paquet | `test_lot00_squelette.py` |
| 1 | Configuration commune, mode hors ligne | `test_lot01_config.py` |
| 2 | Verrou GPU, registre des Mentor | `test_lot02_machine.py` |
| 3 | Base SQLite et migrations | `test_lot03_base.py` |
| 4 | Contrat Discipline, Contexte, modèles, prompts, `appel_structure`, `FauxLLM` | `test_lot04_modeles.py` |
| 5 | File de tâches, travailleur, validations | `test_lot05_taches.py` |
| 6 | QR, images, feuilles, portes, rendu PDF Typst | `test_lot06_impression.py` |
| 7 | Inbox, renvoi entre Mentor, transcription | `test_lot07_scans.py` |
| 8 | Répétition espacée, compétences, erreurs, planificateur | `test_lot08_pedagogie.py` |
| 9 | Corpus, sauvegarde, vérification du kit, gestionnaires complets | `test_lot09_corpus_sauvegarde_kit.py` |
| 10 | Interface parent | `test_lot10_web.py` |
| 11 | CLI, squelette de nouveau Mentor | `test_lot11_cli_gabarit.py` |

---

## Lot 0 — Squelette
`src/mentor_socle/__init__.py` avec `__version__ = "0.1.0"` (identique à `pyproject.toml`) ;
`chemins.py` : `dossier_commun() -> Path` (variable `MENTOR_COMMUN` prioritaire ; sinon
`%LOCALAPPDATA%/mentor` sous Windows, `$XDG_STATE_HOME/mentor` ou `~/.local/state/mentor` ailleurs ; le
dossier est créé). `uv sync --extra dev`.
**Fin** : `pytest tests/test_lot00_squelette.py`.

## Lot 1 — Configuration et mode hors ligne
`config.py` (Pydantic v2, `extra="forbid"` partout) :
`AppConfig(host="127.0.0.1", port 1024–65535, strict_offline=True)`, `CheminsConfig(data, inbox, sauvegardes)` avec
`.resolus(racine)`, `EleveConfig(prenom, classe, etablissement, annee_scolaire="2026-2027")`, `ParentConfig(pin_hash)`,
`SauvegardeConfig(automatique: aucune|quotidienne|hebdomadaire, conserver=30)`, `ChargeConfig(hebdo_min=90,
seance_max_min=25, coefficient_vacances=1.5)`, `Periode(nom, debut, fin)` (fin ≥ début), `Evaluation(date, type,
chapitres, coefficient, libelle)`, `CalendrierConfig(zone A|B|C="B", vacances, evaluations).en_vacances(jour)`,
`OllamaConfig(url, timeout_s)`, `SocleSettings` (racine, extensible), `charger_settings(chemin, modele=SocleSettings)`.
La racine du projet est le parent du dossier `config/` ; `inbox` et `sauvegardes` valent par défaut `data/inbox` et
`data/sauvegardes`.
`offline.py` : `est_local(hote)`, `activer()`, `desactiver()` (tests), `ConnexionInterdite(ConnectionRefusedError)`.
Remplacer `socket.socket.connect` et `connect_ex` ; autoriser loopback et sockets non IP.
**Fin** : `test_lot01_config.py`.

## Lot 2 — Machine : verrou GPU et registre
`gpu.py` : `verrou(app, tache, attente_s=3600)` — gestionnaire de contexte qui rend le **détenteur précédent**
(`dict | None`) ; fichier de verrou `gpu.lock` (bibliothèque `filelock`) + `gpu.detenteur.json` dans `dossier_commun()` ;
**réentrant dans un processus** (RLock + compteur de profondeur) ; `etat() -> dict | None` ; `GpuOccupe(TimeoutError)`
avec `.detenteur`. Le détenteur écrit contient `app, tache, pid, depuis` ; à la sortie, il est copié dans
`gpu.detenteur.precedent.json`.
`registre.py` : `CODES_CONNUS` (LET 8765, MAT 8766, HIS 8767, SVT 8768, PHC 8769, PHI 8770, LVA 8771, avec leurs noms),
`EntreeRegistre`, `lire()`, `enregistrer(code, nom, port, racine, inbox, version_socle) -> list[str]` (liste des conflits
de port ; écriture protégée par un verrou de fichier) dans `apps.json`.
**Fin** : `test_lot02_machine.py` (un test lance un second processus Python).

## Lot 3 — Base et migrations
`db/__init__.py` : `connecter(chemin)` (WAL, `foreign_keys=ON`, `busy_timeout`, `isolation_level=None`,
`row_factory=sqlite3.Row`, `check_same_thread=False`), `migrer(cx, espace=None, dossier=None) -> list[str]` (noms
« espace/fichier » appliqués ; **socle d'abord** puis la discipline ; table `schema_migrations(espace, version, …)` ;
chaque migration dans une transaction **annulée en cas d'erreur** ; découpage des instructions avec
`sqlite3.complete_statement`), `js(valeur)` (JSON, accents conservés), `dejs(texte, defaut=None)`.
Recopier `assets/sql/0001_socle.sql` dans `src/mentor_socle/db/sql/` (inclus dans le paquet : `importlib.resources`).
**Fin** : `test_lot03_base.py`.

## Lot 4 — Contrat, contexte, modèles
- `referentiel.py` (première partie) : `Anomalie(niveau, fichier, message)` (`__str__` → `[ALERTE] f : m`), `charger_yaml`,
  `nombre` (accepte `"6.4e9"` et `"1/4"` : voir pièges), `ids_uniques`, `references_connues`.
- `llm/modeles.py` : `Role(modele, options, keep_alive="5m", verrou_gpu=True, description)`, `RegistreModeles.role(nom)`
  (`KeyError` explicite), `charger_modeles(dossier_config)` (lit `modeles.yaml`, sinon `models.yaml`, sinon les `.example`).
- `llm/ollama.py` : protocole `ClientLLM` (`chat, embed, modeles_charges, decharger`), `ClientOllama` (httpx, `/api/chat`
  avec `format` = schéma JSON, `/api/embed`, `/api/ps`, `/api/tags`, `/api/version`, `keep_alive=0` pour décharger ;
  `trust_env=False`), `image_b64`.
- `llm/prompts.py` : `lire_prompt(chemin) -> Prompt(nom, role, version, systeme, utilisateur, meta)`, `.rendre(**vars)`
  → liste de messages ; en-tête YAML obligatoire avec `role` ; titres `# Système` / `# Utilisateur` ; Jinja
  **`StrictUndefined`** ; filtre `tojson` ; `BibliothequePrompts(dossier)[nom]` (`KeyError` clair) et `.tous()`.
- `llm/structure.py` : `appel_structure(ctx, prompt, Schema, *, images=None, tache_id=None, **variables)` —
  voir `docs/03-contrat-discipline.md` §3.4. Étapes : rendre ; joindre les images en base64 au dernier message
  utilisateur ; appeler avec `format=Schema.model_json_schema()` ; extraire le JSON (gérer les blocs ``` ) ; valider ;
  **une** relance de réparation (message d'erreur renvoyé au modèle) ; `SortieInvalide` sinon ; journaliser **chaque**
  appel dans `llm_appels` ; prendre `gpu.verrou(ctx.discipline.nom, prompt)` et décharger les autres modèles chargés
  quand `role.verrou_gpu` ; `embeddings(ctx, textes, role="embeddings")`. Si `ctx.llm` a un attribut
  `prompt_courant`, y écrire le nom du prompt (c'est ainsi que `FauxLLM` choisit sa réponse).
- `discipline.py` : classe abstraite `Discipline` (voir §3.1 ; `code` validé par `^[A-Z]{3}$`) avec propriétés
  `dossier_config, dossier_referentiel, dossier_prompts, dossier_gabarits (templates), dossier_migrations,
  fichier_taxonomie`.
- `contexte.py` : `Contexte` (dataclass) et `Contexte.ouvrir(discipline, *, llm=None, fichier_settings=None)` :
  lire les settings (`FileNotFoundError` qui cite `settings.example.yaml`), activer le mode hors ligne si demandé, créer
  `data/`, `inbox/`, `sauvegardes/`, ouvrir `data/mentor-<code>.sqlite3`, migrer.
- `testing.py` : `FauxLLM(reponses=None, file=None, vecteur=None)` (réponse choisie par nom de prompt ; une liste est
  consommée dans l'ordre, la dernière est répétée ; attributs `appels, decharges, charges, prompt_courant, reponses`),
  `contexte_de_test(cls, dossier, *, llm=None, racine_kit=None, settings=None)` (copie `referentiel/ prompts/ templates/
  migrations/` du kit, écrit settings et modèles de test, fixe `MENTOR_COMMUN`).
**Fin** : `test_lot04_modeles.py`.

## Lot 5 — Tâches
`taches.py` : `ajouter(cx, type_, payload=None, *, priorite=5, max_essais=2)`, `prendre(cx)` (atomique : `UPDATE … RETURNING`),
`reprendre_orphelines(cx)`, `ouvrir_validation(cx, objet_type, objet_id, motif, details=None)`, `AValider(motif, resultat)`,
`executer_une(ctx, gestionnaires) -> bool`, `Travailleur(ctx, gestionnaires, attente_s)` (thread démon, `.arreter()`).
Règles : un type sans gestionnaire échoue **immédiatement** (pas de nouvel essai) ; une autre exception remet en file
jusqu'à `max_essais` puis « echec » avec la trace ; `AValider` → « a_valider » + validation ouverte.
**Fin** : `test_lot05_taches.py`.

## Lot 6 — QR, images, impression
- `scan/qr.py` : format `MENTOR1|<APP>|<APP>-<AA>-<NNNN>|<page>/<total>` ; `InfoQR`, `encoder` (`ValueError` si invalide),
  `decoder`, `svg(texte)` (correction d'erreur **H**, bibliothèque `segno`), `lire(image)` (zxing-cpp, repli OpenCV).
- `scan/image.py` : `pages(fichier, dpi=200)` (PDF via PyMuPDF, images via `np.fromfile` + `cv2.imdecode` pour les chemins
  accentués), `angle_inclinaison`, `redresser -> (image, angle)`, `ameliorer` (CLAHE), `pour_vision(img, cote_max)`, `enregistrer`.
- `impression/portes.py` : `ResultatPorte(porte, ok, bloquante=True, messages)`, `porte_sources` (`seg:<code>` existant dans
  `segments`, ou `ref:<id>` via `discipline.reference_existe`), `porte_charge` (non bloquante), `passer(ctx, feuille_id)` :
  statut « prete » ou « a_valider » + validation ouverte.
- `impression/feuilles.py` : `nouveau_code` (`TST-26-0001` : code, année de rentrée sur 2 chiffres, numéro), `creer(...)`,
  `verifier`, `imprimer` (`FeuilleNonPrete` si statut ≠ prete/imprimee).
- `impression/typst_rendu.py` : `rendre_pdf(ctx, feuille, sortie) -> nb_pages` avec le paquet `typst` ; **deux passes**
  (compter les pages, puis imprimer le bon QR « page n / total ») ; dossier temporaire contenant `mentor.typ`,
  `principal.typ`, `donnees.json`, `qr-1.svg … qr-12.svg` et les fichiers de `templates/` de la discipline ; gabarit :
  `templates/<type>.typ` > `templates/feuille.typ` > celui du socle.
  Recopier `assets/typst/mentor.typ` et `feuille.typ` dans `src/mentor_socle/impression/gabarits/`.
**Fin** : `test_lot06_impression.py` — un test **relit le QR du PDF rendu**. Ouvrir aussi un PDF et le regarder.

## Lot 7 — Inbox et transcription
- `scan/inbox.py` : `sha256`, `ingerer_fichier(ctx, fichier, type_document=None, date_document=None) -> (statut, valeur)`
  avec statut `recu` (id), `doublon`, `renvoye` (code de l'application) ; `scanner(ctx) -> BilanInbox(recus, doublons,
  renvoyes, illisibles)`. Comportement : dédoublonnage par empreinte (fichier déplacé dans `inbox/_doublons`) ; pages
  redressées dans `data/scans/<id>/page-NN.png` ; original déplacé dans `data/scans/<id>/original/` ; feuille « rendue » ;
  QR d'un autre Mentor → fichier déplacé dans **sa** boîte (registre) ; sans QR → type `a_classer` + validation ; fichier
  illisible → `inbox/_illisibles`.
- `scan/transcription.py` : `ZoneLue`, `PageLue`, `transcrire_document(ctx, payload, tache_id)` : une page à la fois via
  `appel_structure(ctx, "transcription", PageLue, images=[…], type_document, numero_page, lexique)` ; lexique =
  `discipline.lexique_ocr(chapitre)` ; zones enregistrées ; **confiance < 0,75 → document « a_valider »** et validation.
- `gestionnaires.py` : `tous(ctx)` = gestionnaires du socle **puis** ceux de la discipline (qui peuvent les remplacer).
  Pour l'instant : `transcrire_document` seulement.
**Fin** : `test_lot07_scans.py`.

## Lot 8 — Pédagogie
`pedagogie/srs.py` (Leitner : intervalles 1, 3, 7, 16, 35, 80 jours ; réussite = boîte +1, échec = boîte 1),
`competences.py` (maîtrise et incertitude : voir les formules ci-dessous), `erreurs.py` (`Taxonomie`, `charger`,
`enregistrer` — refuse un code hors taxonomie —, `recurrentes` avec tendance), `planificateur.py`
(`budget_semaine`, `planifier` → `ElementPlan(type, cible, duree_min, raison, priorite)`).
- Compétences : observation de score `s ∈ [0,1]`, poids `w`. Défaut : maîtrise 0,5, incertitude 0,35. Bruit
  `b = 0,25 / √max(w, 0,05)` ; gain `g = u² / (u² + b²)` ; `m ← m + g·(s − m)` ; `u ← max(0,05, √(1−g)·u)`.
  Avant l'observation, l'incertitude dérive : `u ← min(0,35, √(u² + 0,004²·jours·10))`.
  Priorité d'une compétence : `(1 − maîtrise) + 0,5·incertitude`.
- Erreurs récurrentes : fenêtre 42 jours, seuil 3 ; tendance « recul » si les erreurs de la moitié récente ×2 ≤ celles
  de la moitié ancienne, « hausse » si plus nombreuses, « stable » sinon.
- Planificateur : budget = `hebdo_min` (× `coefficient_vacances` si ≥ 4 jours de vacances dans la semaine) ; séances de
  5 à `seance_max_min` minutes ; ordre : préparation d'évaluation à ≤ 14 jours > remédiation des erreurs non « recul » >
  4 compétences prioritaires (15 min) > cartes à revoir (5 à 15 min) > approfondissement jusqu'à épuisement du budget.
**Fin** : `test_lot08_pedagogie.py`.

## Lot 9 — Corpus, sauvegarde, vérification du kit
`corpus.py` (`ajouter_segment` — upsert qui remet `embedding` à NULL —, `indexer`, `rechercher` : vecteurs NumPy
normalisés float32 en BLOB), `sauvegarde.py` (`sauvegarder` avec `Connection.backup`, nom
`mentor-<code>-AAAAMMJJ-HHMMSS.sqlite3`, `tourner`, `derniere`, `due`, `gestionnaire_sauvegarde`),
`referentiel.verifier_kit(discipline, afficher=True) -> 0|1` (YAML valides, rôles des prompts présents dans
`modeles.yaml`, taxonomie à identifiants uniques, puis `discipline.verifier_referentiel`), `journal.py`
(`configurer(dossier)` : fichier tournant). Compléter `gestionnaires.py` : ajouter `sauvegarde` et `indexer_corpus`.
**Fin** : `test_lot09_corpus_sauvegarde_kit.py`.

## Lot 10 — Interface parent
`web/app.py` : `creer_app(ctx) -> FastAPI`, `web/auth.py` : `hacher_pin` (scrypt, 4 à 12 chiffres), `verifier_pin`,
`serialiseur`, `jeton_valide`. Recopier `assets/web/templates/` et `assets/web/static/` dans `src/mentor_socle/web/`.
Routes : `/`, `/connexion`, `/deconnexion`, `/depot` (GET/POST), `/inbox/scanner`, `/validations` (+ POST),
`/taches` (+ relancer), `/sauvegarde`, `/feuilles` (+ vérifier, imprimer), `/pdf/{code}`. Sans PIN défini : accès libre
avec bandeau d'alerte ; avec PIN : redirection vers `/connexion` (cookie signé 12 h, `httponly`, `samesite=strict`).
Gabarits de la discipline : `templates/web/` d'abord. Upload : extensions autorisées seulement (400 sinon).
**Fin** : `test_lot10_web.py`.

## Lot 11 — CLI et squelette de Mentor
`cli.py` : `main(cls, racine, argv)` avec `check, serve, worker, inbox, migrate, backup, kit, plan, gpu, parent set-pin` ;
`main_socle(argv)` avec `nouveau, registre, gpu`. `serve` : enregistre l'application dans le registre, lance le
travailleur, une veille (inbox toutes les 30 s + sauvegarde automatique) et uvicorn sur `127.0.0.1`.
`gabarit.py` : `creer_projet(code, nom, dossier, port=None)` copie `assets/gabarit_app/` (à placer dans
`src/mentor_socle/gabarit_app/`, inclus dans le paquet) en remplaçant `__PROJET__ __PAQUET__ __CLASSE__ __NOM__ __CODE__
__code__ __PORT__ __VERSION_MIN__ __VERSION_MAX__`, y compris dans les noms de fichiers.
**Fin** : `test_lot11_cli_gabarit.py`, puis `uv run mentor-socle nouveau PHC "Mentor Physique-Chimie" ../essai` et
`uv run mentor check` dans le projet créé.

---

## Après le socle : adapter les quatre Mentor
Voir `docs/05-migration-des-mentor.md`. Un Mentor à la fois, en commençant par **Mentor Maths** (le plus petit
écart avec le gabarit). Pour chacun, tag du socle (`git tag v0.1.0`) puis dépendance figée.
