# 5. Adapter les Mentor existants au socle

Les quatre kits ont été conçus « sans code partagé » : leurs plans en lots prévoient chacun de
réécrire l'infrastructure. Avec le socle, ces lots disparaissent ou se réduisent à du branchement.
Comme aucun code n'a encore été écrit lot par lot, l'adaptation porte surtout sur les documents.

## 5.1 Étapes communes (par Mentor, une seule fois)

1. Placer le Mentor à côté de `mentor-socle/`.
2. `pyproject.toml` : ajouter la dépendance et la source (voir `06-versionnement.md`) ; retirer les
   dépendances désormais apportées par le socle (FastAPI, Pydantic, httpx, OpenCV, zxing, Typst, PyMuPDF…).
3. Créer `src/mentor_xxx/discipline.py` et `__main__.py` (copier depuis un projet créé par
   `mentor-socle nouveau`), et déclarer `mentor = "mentor_xxx.__main__:run"`.
4. Renommer si besoin `config/models.yaml` en `config/modeles.yaml` (l'ancien nom reste lu) et vérifier
   que chaque rôle cité dans les prompts y figure.
5. Ajouter l'en-tête YAML (`role`, `version`) à chaque prompt et, si besoin, les titres `# Système` / `# Utilisateur`.
6. Mettre `referentiel/taxonomie_erreurs.yaml` au format commun (`erreurs: [{code, libelle, famille, gravite}]`) ;
   les champs propres (confusions de notions, remédiations) restent permis.
7. Réécrire `scripts/verifier_kit.py` en appel à `verifier_kit` + contrôles propres dans `verifier_referentiel()`.
8. Remplacer dans `CLAUDE.md` la section « Pile » et les règles d'infrastructure par le bloc « Règle n°1 :
   ne pas réécrire le socle » du gabarit ; ajouter le passage par `../mentor-socle/docs/03-contrat-discipline.md`
   dans la commande `/lot`.
9. Réviser `docs/0x-plan-lots` selon le tableau du Mentor ci-dessous, puis `uv run mentor check`.

## 5.2 Lots remplacés par le socle

Les noms de lots varient d'un kit à l'autre ; ce sont les contenus qui comptent.

| Contenu de lot dans les kits | Devient |
|---|---|
| Squelette du projet, configuration, CLI `check/serve` | Fourni (lot 0 réduit à : discipline.py, settings propres) |
| Verrou GPU, registre des modèles, client Ollama, `structured_call` | Fourni (`appel_structure`) |
| Base SQLite, migrations, tables communes | Fourni ; seules les tables propres restent |
| File de tâches et travailleur | Fourni |
| Inbox, dédoublonnage, redressement, QR, routage | Fourni |
| Transcription page par page, relecture parent | Fourni ; la discipline écrit le prompt et le lexique (ou remplace le gestionnaire) |
| Rendu PDF Typst, QR par page, zones de réponse | Fourni ; la discipline écrit ses gabarits propres |
| Portes avant impression (mécanique), porte « sources » | Fourni ; la discipline écrit ses portes |
| Répétition espacée, modèle de l'élève, erreurs récurrentes, planificateur | Fourni ; la discipline transforme le plan en feuilles |
| Corpus et recherche | Fourni ; la discipline découpe et nomme les segments |
| Interface parent (cadre, PIN, dépôt, validations, tâches) | Fourni ; la discipline ajoute ses pages |
| Sauvegarde | Fourni |

## 5.3 Par Mentor : ce qui reste propre

**Mentor Lettres (LET, 8765)** — correction critère par critère du commentaire et de la dissertation
(deux passes, troisième si écart), grilles et niveaux d'exigence, LanguageTool comme vérification de la
langue (porte et outil de correction), oral (lecture, explication, entretien), contraction et pastiche,
dictée et analyse logique au niveau Excellence. Section `pedagogie` (œuvres de la classe, œuvre de
l'entretien) et section `correction` dans `SettingsLET`. Prompt `transcription` attentif à
l'orthographe exacte (ne rien corriger).

**Mentor Maths (MAT, 8766)** — vérification SymPy obligatoire comme **porte bloquante** sur énoncés et
corrigés, et dans la correction des copies ; transcription remplacée par une version qui sépare texte et
calculs (LaTeX) ; automatismes de l'EAM ; niveau Prépa et Olympiades ; saisie des rangs et appréciations
des bulletins (table propre ou `notes_reelles.rang`).

**Mentor Histoire (HIS, 8767)** — porte « faits » (chaque date, nom, chiffre confronté au cours scanné
et aux repères du référentiel) ; cartographie (GeoPandas/Shapely, fonds SVG dans `templates/`) et
croquis ; frise (`his_frise_evenement`) ; profil du professeur (`his_profil_prof`) ; EMC : neutralité,
jamais d'évaluation d'opinion, sujets sensibles en validation parent (porte propre). Lexique OCR des
noms propres par chapitre via `lexique_ocr()`.

**Mentor SVT (SVT, 8768)** — porte « faits » scientifique ; porte `hors_programme` (aucun exercice
n'exige une limite du BO) ; calculs SymPy des 19 types (`calculs.yaml`), porte bloquante comme en
Maths ; données simulées étiquetées comme telles ; porte « santé » (maladies génétiques, cancer,
vaccination, antibiotiques) toujours en validation parent ; schémas-bilans (fonds SVG, lecture
spécialisée). Tables propres : `svt_lacunes`, `svt_divergences`, `svt_progression`. Rappel : contrôle
continu, coefficient 8 — chaque DS compte, ce que le planificateur reçoit par `calendrier.evaluations`.

## 5.4 Deux portes à faire remonter au socle plus tard

Maths et SVT écrivent chacun une porte SymPy ; Histoire et SVT chacun une porte « faits ». Quand les
deux versions existent, les comparer et remonter la partie commune dans `mentor_socle.impression`
(socle 0.2), en gardant dans chaque discipline ce qui lui est propre (types de calculs, nature des faits).
