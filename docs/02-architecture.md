# 2. Architecture

## Vue d'ensemble

```
                 ┌────────────────────── machine (Windows 11, RTX 4080 Laptop 12 Go) ──────────────────────┐
                 │                                                                                         │
  %LOCALAPPDATA%\mentor\   gpu.lock · gpu.detenteur.json · apps.json   (aucune donnée d'élève)             │
                 │                ▲ verrou            ▲ registre                                           │
                 │   ┌────────────┴───────┬───────────┴────────┬────────────────────┐                      │
                 │   │ mentor-lettres     │ mentor-maths       │ mentor-histoire    │ mentor-svt  …        │
                 │   │ :8765  data/ base  │ :8766  data/ base  │ :8767  data/ base  │ :8768  data/ base    │
                 │   │ referentiel/ …     │ referentiel/ …     │ referentiel/ …     │ referentiel/ …       │
                 │   └─────────┬──────────┴─────────┬──────────┴─────────┬──────────┴──────────┘           │
                 │             └──── dépendent de mentor-socle (paquet Python, version épinglée) ───┘     │
                 │                                    │                                                  │
                 │                         Ollama 127.0.0.1:11434                                          │
                 └─────────────────────────────────────────────────────────────────────────────────────────┘
```

## Modules

```
src/mentor_socle/
├── config.py            SocleSettings et sections communes ; charger_settings()
├── discipline.py        classe abstraite Discipline (le contrat)
├── contexte.py          Contexte : discipline, settings, base, modèles, prompts, client LLM
├── offline.py           refus des connexions non locales
├── gpu.py               verrou GPU inter-applications, réentrant, détenteur visible
├── registre.py          apps.json : codes, ports, inbox des Mentor installés
├── db/                  connexion WAL, migrations par espace, sql/0001_socle.sql
├── llm/                 modeles.py (rôles) · ollama.py (client) · prompts.py · structure.py (appel_structure)
├── taches.py            file SQLite, Travailleur, AValider, validations
├── scan/                image.py (pages, redressement) · qr.py · inbox.py · transcription.py
├── impression/          feuilles.py (cycle de vie) · portes.py · typst_rendu.py · gabarits/mentor.typ
├── pedagogie/           srs.py · competences.py · erreurs.py · planificateur.py
├── corpus.py            segments + recherche sémantique (NumPy)
├── sauvegarde.py        sauvegarde SQLite à chaud + rotation
├── gestionnaires.py     tâches fournies : transcrire_document, sauvegarde, indexer_corpus
├── web/                 app.py (FastAPI) · auth.py (PIN) · templates/ · static/
├── cli.py               commande `mentor` de chaque Mentor + `mentor-socle`
├── testing.py           FauxLLM, contexte_de_test
└── gabarit.py + gabarit_app/   squelette d'un nouveau Mentor
```

Pile : Python 3.12, `uv`, Pydantic v2, FastAPI + Jinja2 (sans JavaScript externe), SQLite WAL, Ollama
(HTTP local via httpx), OpenCV + zxing-cpp (QR), segno (génération QR), Typst (binding Python),
PyMuPDF, NumPy, filelock.

## Le cycle papier, commun à tous les Mentor

```
discipline : générateur ──► feuilles.creer() ──► portes.passer() ──► feuilles.imprimer() ──► PDF + QR
                                                      │ échec bloquant                          │
                                                      ▼                                         ▼
                                              validation parent                    l'élève écrit au crayon
                                                                                                │
   inbox ◄── scan déposé (dossier surveillé ou page « Déposer un scan ») ◄──────────────────────┘
     │ SHA-256 (doublon ?) · pages · QR lu
     ├─ QR d'un autre Mentor ──► déplacé dans la boîte de ce Mentor (registre)
     ├─ sans QR ──► document « à classer » + validation parent
     └─ QR de ce Mentor ──► feuille « rendue », tâche transcrire_document
                                     │ modèle de vision, lexique de la discipline
                                     ▼
                         zones transcrites (confiance) ──► relecture parent si confiance < 0,75
                                     ▼
discipline : correction ──► erreurs (taxonomie) + competences.observer() ──► planificateur ──► feuilles suivantes
```

## Ressources partagées et concurrence

- **GPU** : tout appel de modèle prend `gpu.verrou(app, tâche)` (sauf rôles `verrou_gpu: false`, les
  embeddings). En prenant le verrou, le socle décharge d'Ollama les autres modèles : un 24 B ne cohabite
  pas avec un 8 B de vision sur 12 Go. Le verrou est réentrant dans un processus : une correction peut
  enchaîner vision → correcteur → relecteur sans se bloquer.
- **Travailleur** : un seul par Mentor ; les tâches longues ne bloquent jamais l'interface.
- **Base** : WAL, `busy_timeout` 30 s ; l'interface et le travailleur partagent la connexion.
- **Ports** : réservés dans `registre.CODES_CONNUS` ; `mentor check` signale un conflit.

| Code | Application | Port |
|---|---|---|
| LET | Mentor Lettres | 8765 |
| MAT | Mentor Maths | 8766 |
| HIS | Mentor Histoire | 8767 |
| SVT | Mentor SVT | 8768 |
| PHC | Mentor Physique-Chimie (réservé) | 8769 |
| PHI | Mentor Philosophie (réservé) | 8770 |
| LVA | Mentor Langues (réservé) | 8771 |

## Confidentialité (élève mineur)

- `strict_offline` actif par défaut : connexions non locales refusées au niveau du socket.
- Aucune télémétrie ; journaux dans `data/logs` sans le contenu des copies.
- `data/`, `settings.yaml`, `modeles.yaml` jamais versionnés (`.gitignore` du gabarit).
- Interface liée à `127.0.0.1`, protégée par un PIN parent (scrypt, cookie signé 12 h).
