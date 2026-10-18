# 1. Périmètre : socle ou discipline ?

## Décision

Jusqu'ici les Mentor étaient **séparés sans code partagé** (seulement des conventions et le verrou GPU).
Ce socle change la moitié de cette règle :

- **toujours séparés** : une application, une base, un dossier `data/`, un port, un référentiel, des
  prompts et une interface par discipline. Arrêter, casser ou réinstaller un Mentor n'affecte pas les autres ;
- **désormais partagé** : le code d'infrastructure, sous forme d'un paquet Python versionné
  (`mentor-socle`) dont chaque Mentor dépend, avec une version épinglée.

Aucune donnée n'est partagée entre Mentor. Les deux seuls fichiers communs à la machine sont le verrou
GPU et le registre des applications (`%LOCALAPPDATA%\mentor\`), qui ne contiennent aucune donnée d'élève.

## La règle pour trancher

Une fonctionnalité va dans le socle si **les trois** conditions sont réunies :

1. elle sert (ou servira) à au moins deux Mentor ;
2. elle ne dépend d'aucun contenu disciplinaire (programme, grille, notion, notation) — ce contenu
   peut lui être *passé* (fichier YAML, prompt, lexique, porte) ;
3. son comportement peut être testé avec des données fictives sans modèle réel.

Sinon elle reste dans la discipline. En cas de doute : on commence dans la discipline, et on remonte
dans le socle au deuxième Mentor qui en a besoin.

## Répartition

| Sujet | Socle | Discipline |
|---|---|---|
| Configuration | Sections communes de `settings.yaml`, validation, chemins | Section `pedagogie` et autres sections propres (sous-classe de `SocleSettings`) |
| Modèles | Registre par rôle, client Ollama, `appel_structure`, verrou GPU, journal | Choix des modèles (`modeles.yaml`), schémas Pydantic des sorties |
| Prompts | Format (en-tête YAML, `# Système` / `# Utilisateur`), rendu Jinja strict | Le texte de chaque prompt |
| Base | Schéma commun, migrations, connexion | Tables propres (`migrations/`, préfixe du code : `mat_`, `his_`…) |
| Scans | Inbox, dédoublonnage, pages, redressement, QR, renvoi entre Mentor, transcription générique | Prompt `transcription`, lexique OCR par chapitre, lecture spécialisée (schémas SVT, cartes d'histoire, calculs) |
| Impression | Codes de feuille, bibliothèque Typst `mentor.typ`, QR par page, portes communes (sources, charge) | Gabarits propres (dissertation, frise, fond de carte, schéma-bilan), portes propres |
| Vérification | Porte « sources » (`seg:` / `ref:`), porte « charge » | SymPy (Maths, SVT, Physique), faits (Histoire, SVT), neutralité EMC, sujets de santé, LanguageTool (Lettres) |
| Correction | Rien de disciplinaire ; seulement le stockage (copies, erreurs) et l'appel structuré | Correcteurs, grilles, barèmes, calibrage sur les notes du professeur |
| Pédagogie | Leitner, modèle de l'élève, tendance des erreurs, planificateur générique | Taxonomie d'erreurs, compétences, types d'exercices, niveaux d'exigence, transformation du plan en feuilles |
| Corpus | Segments sourcés, embeddings, recherche | Découpage par nature (définition, mécanisme, repère, démonstration…), récapitulatifs |
| Interface parent | Cadre, PIN, tableau de bord, dépôt, validations, tâches, feuilles, liens entre Mentor | Pages propres (oral, frise, bulletins, olympiades…), surcharge des gabarits |
| Exploitation | CLI, sauvegardes, registre, journaux | Commandes propres (`mentor eval …`) |

## Hors périmètre du socle (volontairement)

- Une application « Mentor tout-en-un » : non. Le socle n'agrège pas les disciplines.
- Un modèle de l'élève transversal (par exemple la rédaction, commune au français et à l'histoire) : pas
  maintenant. Si le besoin se confirme, ce sera un export en lecture seule, pas une base commune.
- Le choix des modèles : chaque Mentor garde le sien, parce que les évaluations sont par discipline.
