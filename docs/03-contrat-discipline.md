# 3. Contrat entre le socle et une discipline

Un Mentor = une sous-classe de `mentor_socle.discipline.Discipline` + des fichiers rangés selon les
conventions ci-dessous. Le socle appelle la discipline à des points précis ; la discipline ne touche
pas aux internes du socle.

## 3.1 La classe

```python
class MentorMaths(Discipline):
    code = "MAT"                       # 3 majuscules, écrit dans chaque QR
    nom = "Mentor Maths"
    port_defaut = 8766
    settings_modele = SettingsMAT      # sous-classe de SocleSettings (sections propres)
    version = "0.4.0"

    def charger_referentiel(self): ...                 # obligatoire
    def verifier_referentiel(self, ref) -> list[Anomalie]: ...
    def reference_existe(self, identifiant) -> bool: ...   # pour la porte « sources »
    def gestionnaires(self) -> dict[str, Gestionnaire]: ... # tâches de fond propres
    def portes(self) -> list[Porte]: ...                    # vérifications avant impression
    def routeurs(self) -> list[APIRouter]: ...              # pages web propres
    def liens_menu(self) -> list[tuple[str, str]]: ...
    def lexique_ocr(self, chapitre) -> list[str]: ...       # aide à la transcription
    def contexte_feuille(self, feuille) -> dict: ...        # variables pour les gabarits Typst
    def verifications_demarrage(self, ctx) -> list[tuple[str, bool, str]]: ...  # pour `mentor check`
```

Tout est facultatif sauf `charger_referentiel`. Les signatures exactes sont dans `discipline.py`.

## 3.2 Arborescence d'un Mentor

```
mentor-xxx/
├── pyproject.toml            dépend de mentor-socle (version épinglée)
├── CLAUDE.md                 règles (dont : ne pas réécrire le socle)
├── config/                   settings.example.yaml · modeles.example.yaml  (les vrais : non versionnés)
├── referentiel/              YAML ; taxonomie_erreurs.yaml au format commun
├── prompts/                  un .md par tâche ; transcription.md attendu
├── templates/                gabarits Typst (<type>.typ, feuille.typ) + fonds ; templates/web/ pour l'interface
├── migrations/               0001_xxx.sql… (tables préfixées par le code en minuscules)
├── src/mentor_xxx/           discipline.py, __main__.py, correcteurs, générateurs, portes
├── tests/                    avec mentor_socle.testing
├── scripts/verifier_kit.py   3 lignes : appelle mentor_socle.referentiel.verifier_kit
└── docs/                     cahier des charges, plan en lots, journal
```

`mentor-socle nouveau <CODE> "<Nom>" <dossier>` crée exactement cette arborescence, prête à tester.

## 3.3 Contexte

Les gestionnaires, portes et pages reçoivent un `Contexte` :

| Attribut | Contenu |
|---|---|
| `ctx.discipline` | l'instance de la discipline (chemins, code, nom) |
| `ctx.settings` | settings validés (classe de la discipline) |
| `ctx.cx` | connexion SQLite (autocommit ; `BEGIN`/`COMMIT` explicites si besoin) |
| `ctx.modeles` / `ctx.prompts` | registre des rôles / bibliothèque de prompts |
| `ctx.llm` | client (Ollama en vrai, `FauxLLM` en test) |
| `ctx.referentiel` | référentiel chargé à la première utilisation |
| `ctx.data` | dossier `data/` résolu |

## 3.4 Appeler un modèle

Un seul chemin : `appel_structure(ctx, "<prompt>", Schema, images=[...], tache_id=tid, **variables)`.
Il rend une instance Pydantic valide ou lève `SortieInvalide`. Ne jamais appeler `ctx.llm.chat`
directement : on perdrait le verrou GPU, la réparation et le journal.

Format d'un prompt (`prompts/correction_commentaire.md`) :

```markdown
---
role: correcteur
version: 3
description: Correction critère par critère
---
# Système
Tu es un professeur… Grille : {{ grille | tojson }}
# Utilisateur
Copie transcrite : {{ copie }}
```

Jinja en mode strict : une variable oubliée lève une erreur. Le champ `version` est journalisé dans
`llm_appels`, ce qui permet de relier une dérive de notation à un changement de prompt.

## 3.5 Tâches de fond

```python
def corriger_copie(ctx, payload: dict, tache_id: int) -> dict:
    ...                                   # rend un résultat JSON
    raise AValider("Écart de notation > 2 points entre deux passes", {"ecart": 2.5})   # → parent
```

Déclarer dans `gestionnaires()`. Le socle fournit `transcrire_document`, `sauvegarde`,
`indexer_corpus` ; une discipline peut remplacer l'un d'eux en déclarant le même nom (ex. Maths remplace
la transcription pour séparer texte et calculs LaTeX). Mettre en file : `taches.ajouter(ctx.cx, "type", payload)`.

## 3.6 Feuilles, portes et impression

```python
fid = feuilles.creer(ctx, type_="remediation", titre="Dérivation — signe", contenu=contenu,
                     sources=["seg:C04-012", "ref:MAT-1-DERIV-03"], chapitres=["C04"], duree_min=20)
resultats = feuilles.verifier(ctx, fid)   # portes du socle + portes de la discipline
pdf = feuilles.imprimer(ctx, fid)         # refuse si la feuille n'est pas « prete »
```

- **Sources** : `seg:<code de segment>` (cours scanné) ou `ref:<identifiant du référentiel>`. Une
  feuille sans source valide ne s'imprime pas.
- **Porte** : fonction `(ctx, feuille) -> ResultatPorte(porte, ok, bloquante, messages)`.
- **Gabarit** : `templates/<type>.typ`, sinon `templates/feuille.typ`, sinon celui du socle. Un gabarit
  commence par `#import "mentor.typ": *` puis `#show: mentor-page`, et lit `donnees.contenu`. La
  bibliothèque fournit `zone-reponse(type: "lignes"|"carreaux"|"cadre", hauteur_cm:)`, `consigne`,
  `encadre`, `exercice`. Tout fichier de `templates/` (fonds SVG de cartes, schémas) est copié à côté.
- Le QR (en-tête, chaque page) : `MENTOR1|<code>|<feuille>|<page>/<total>`.

## 3.7 Modèle de l'élève et planification

- Après chaque correction : `erreurs.enregistrer(ctx.cx, copie_id, erreurs, taxonomie)` (codes vérifiés)
  et `competences.observer(ctx.cx, code, score, poids=…)` (1 pour un DS, 0,5 pour un entraînement).
- Le modèle ne doit jamais sortir de code hors taxonomie : dans le schéma de sortie de la correction, déclarer les
  erreurs avec `taxonomie.modele_erreur()` (le champ `code` y est une énumération des codes permis, transmise à
  Ollama et revalidée), et insérer `taxonomie.pour_prompt()` dans le prompt. `enregistrer` reste le dernier
  filet : un code inconnu y lève `ValueError` et rien n'est écrit.
- Les notes du professeur vont dans `notes_reelles` : c'est la vérité terrain pour calibrer.
- `planificateur.planifier(ctx)` rend des `ElementPlan` motivés ; la discipline les transforme en feuilles.

## 3.8 Interface parent

- Routeurs FastAPI propres via `routeurs()`, entrées de menu via `liens_menu()`.
- Gabarits : `templates/web/<nom>.html` surcharge celui du socle ; tous héritent de `base.html`
  (`{% extends "base.html" %}{% block contenu %}…{% endblock %}`).

## 3.9 Tests

```python
from mentor_socle.testing import FauxLLM, contexte_de_test

def test_correction(tmp_path):
    llm = FauxLLM({"correction_commentaire": {"note": 13.5, "criteres": [...]}})
    ctx = contexte_de_test(MentorLettres, tmp_path, llm=llm, racine_kit=RACINE)
```

`FauxLLM` répond selon le nom du prompt appelé (transmis par `appel_structure`) ; une liste de
réponses est consommée dans l'ordre (utile pour tester la réparation) ; `llm.appels` garde les messages
envoyés pour vérifier ce que le modèle a reçu. `contexte_de_test` isole aussi le verrou GPU et le registre.
