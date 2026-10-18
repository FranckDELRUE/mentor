# 4. Modèle de données commun

Une base SQLite **par Mentor** : `data/mentor-<code>.sqlite3` (WAL). Le schéma ci-dessous est créé par
`src/mentor_socle/db/sql/0001_socle.sql` ; chaque discipline ajoute ses tables par ses propres
migrations (`migrations/0001_<code>.sql`…), appliquées **après** celles du socle et suivies séparément
dans `schema_migrations(espace, version)`.

Conventions : dates en texte ISO 8601 ; listes et objets en JSON dans des colonnes `TEXT` ; identifiants
du référentiel stockés tels quels (`C05`, `E-RAIS-CAUSE`) — le référentiel reste dans les YAML.
Colonnes `meta` (JSON) : extension libre pour la discipline, sans migration.

| Table | Rôle | Colonnes principales |
|---|---|---|
| `documents` | Tout fichier reçu | `type` (cours, ds_sujet, ds_copie, copie_mentor, photocopie, bulletin, a_classer), `date_document`, `chapitres`, `fichier_source`, `empreinte_sha256` (unique), `statut` (recu → pretraite → transcrit / a_valider → valide) |
| `pages` | Pages redressées | `document_id`, `numero`, `image`, `qr` (JSON app/feuille/page/total), `redressee` |
| `zones` | Transcription | `page_id`, `type` (texte, schema, calcul, carte…), `bbox`, `texte_ocr`, `confiance`, `texte_valide`, `valide_par_parent` |
| `segments` | Corpus du cours (fait foi) | `code` (unique, ex. C05-012), `chapitre`, `document_id`, `zone_ids`, `texte`, `nature`, `embedding` |
| `feuilles` | Tout ce qui s'imprime | `code` (MAT-26-0042), `type`, `titre`, `chapitres`, `competences`, `niveau_exigence`, `contenu`, `corrige`, `sources`, `statut` (brouillon → a_valider / prete → imprimee → rendue → corrigee), `duree_min`, `pdf` |
| `copies` | Réponse de l'élève à une feuille ou un DS | `feuille_id`, `document_id`, `transcription`, `correction`, `note_indicative`, `sur`, `statut`, `pdf_annote` |
| `notes_reelles` | Notes du professeur (saisies) | `evaluation`, `date`, `note`, `sur`, `coefficient`, `appreciation`, `rang` |
| `erreurs` | Erreurs relevées | `copie_id`, `code` (taxonomie), `chapitre`, `competence`, `extrait`, `gravite`, `date` |
| `competences` | Modèle de l'élève | `code`, `chapitre`, `maitrise` (0–1), `incertitude`, `nb_observations`, `maj_le` |
| `cartes` | Répétition espacée | `recto`, `verso`, `source`, `chapitre`, `boite`, `prochaine_revue`, `historique` |
| `validations` | Décisions du parent | `objet_type`, `objet_id`, `motif`, `details`, `statut` (ouverte, acceptee, refusee), `decision` |
| `taches` | File de fond | `type`, `statut`, `priorite`, `payload`, `resultat`, `erreur`, `essais`, `max_essais` |
| `llm_appels` | Journal des modèles | `role`, `modele`, `prompt`, `version_prompt`, `entree_sha256`, `sortie`, `ok`, `reparation`, `duree_ms`, `tache_id` |

## Correspondance avec les schémas des kits existants

Les kits Lettres, Maths, Histoire et SVT avaient chacun leur modèle. Correspondance :

| Kits existants | Socle |
|---|---|
| `document` / `documents` | `documents` |
| `segment` (Histoire), `segments` (SVT), `zones` | `segments`, `zones` |
| `exercice`, `sujet`, feuille imprimée | `feuilles` (`type` distingue) |
| `copie` | `copies` |
| `note_reelle` | `notes_reelles` |
| `erreur` | `erreurs` |
| `competence` | `competences` |
| `carte_srs` | `cartes` |
| `tache` / `taches` | `taches` |
| `llm_call` (Lettres) | `llm_appels` |
| `lacunes`, `divergences` (SVT), `frise_evenement`, `profil_prof` (Histoire), `progression` | restent **dans la discipline** (préfixe `svt_`, `his_`…) ; à remonter au socle si un deuxième Mentor les adopte |
