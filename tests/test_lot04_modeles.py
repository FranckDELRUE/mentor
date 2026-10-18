"""Lot 4 — contrat Discipline, Contexte, registre de modèles, prompts, appel_structure, FauxLLM."""

import pytest
from jinja2 import UndefinedError
from pydantic import BaseModel

from mentor_socle.llm import SortieInvalide, appel_structure
from mentor_socle.llm.prompts import lire_prompt


class Exo(BaseModel):
    enonce: str
    bareme: int


def test_contexte_ouvre_base_et_migre(ctx):
    tables = {r[0] for r in ctx.cx.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"documents", "feuilles", "taches", "llm_appels", "tst_extra"} <= tables
    assert ctx.settings.chemins.inbox.is_dir() and ctx.data.is_dir()
    assert ctx.referentiel["chapitres"][0]["id"] == "C01"
    assert ctx.modeles.role("vision").modele == "faux-vision"
    with pytest.raises(KeyError):
        ctx.modeles.role("inexistant")


def test_code_discipline_invalide(tmp_path):
    from mentor_socle.discipline import Discipline

    class Mauvaise(Discipline):
        code = "mat"
        nom = "x"
        port_defaut = 9000

        def charger_referentiel(self):
            return {}

    with pytest.raises(ValueError):
        Mauvaise(tmp_path)


def test_settings_absents_message_clair(tmp_path, MentorTest):
    from mentor_socle.contexte import Contexte

    with pytest.raises(FileNotFoundError, match="settings.example.yaml"):
        Contexte.ouvrir(MentorTest(tmp_path))


def test_prompt_systeme_utilisateur_et_variable_manquante(ctx):
    p = ctx.prompts["transcription"]
    assert p.role == "vision" and p.utilisateur is not None
    msgs = p.rendre(numero_page=1, type_document="cours", lexique=["a", "b"])
    assert "Lexique : a, b" in msgs[0]["content"] and msgs[1]["content"] == "Transcris."
    with pytest.raises(UndefinedError):
        p.rendre(numero_page=1)
    assert ctx.prompts["exercice"].utilisateur is None
    with pytest.raises(KeyError):
        ctx.prompts["absent"]


def test_entete_prompt_obligatoire(tmp_path):
    f = tmp_path / "x.md"
    f.write_text("pas d'en-tête", encoding="utf-8")
    with pytest.raises(ValueError):
        lire_prompt(f)
    f.write_text("---\nversion: 1\n---\ntexte", encoding="utf-8")
    with pytest.raises(ValueError, match="role"):
        lire_prompt(f)


def test_appel_structure_valide_journalise_et_vide_la_vram(ctx, llm):
    llm.charges = ["autre-modele-lourd"]
    llm.reponses = {"exercice": {"enonce": "Calculer", "bareme": 4}}
    exo = appel_structure(ctx, "exercice", Exo, chapitre="C01")
    assert exo.bareme == 4
    assert llm.decharges == ["autre-modele-lourd"]
    assert llm.appels[0]["format"]["title"] == "Exo"
    ligne = ctx.cx.execute("SELECT * FROM llm_appels").fetchone()
    assert ligne["ok"] == 1 and ligne["reparation"] == 0 and ligne["version_prompt"] == "2"
    assert ligne["role"] == "generateur" and ligne["modele"] == "faux-generateur"


def test_appel_structure_prend_le_verrou_gpu(ctx, llm):
    from mentor_socle import gpu

    vu = {}
    def repondre(messages):
        vu["detenteur"] = gpu.etat()
        return {"enonce": "x", "bareme": 1}

    llm.reponses = {"exercice": repondre}
    appel_structure(ctx, "exercice", Exo, chapitre="C01")
    assert vu["detenteur"]["app"] == "Mentor Test" and gpu.etat() is None


def test_appel_structure_repare_une_fois(ctx, llm):
    llm.reponses = {"exercice": ["pas du json", '```json\n{"enonce": "x", "bareme": 2}\n```']}
    assert appel_structure(ctx, "exercice", Exo, chapitre="C01").bareme == 2
    assert ctx.cx.execute("SELECT reparation FROM llm_appels").fetchone()[0] == 1
    assert "Erreurs" in llm.appels[1]["messages"][-1]["content"]


def test_appel_structure_echoue_apres_reparation(ctx, llm):
    llm.reponses = {"exercice": [{"enonce": "x"}, {"enonce": "x"}]}
    with pytest.raises(SortieInvalide):
        appel_structure(ctx, "exercice", Exo, chapitre="C01")
    assert ctx.cx.execute("SELECT ok FROM llm_appels").fetchone()[0] == 0


def test_appel_structure_images_en_base64(ctx, llm, tmp_path):
    img = tmp_path / "p.png"
    img.write_bytes(b"\x89PNG fake")
    class Page(BaseModel):
        zones: list = []

    llm.reponses = {"transcription": {"zones": []}}
    appel_structure(ctx, "transcription", Page, images=[img], type_document="cours", numero_page=1, lexique=[])
    assert llm.appels[0]["messages"][-1]["images"] == ["iVBORyBmYWtl"]


def test_role_sans_verrou_gpu_pour_les_embeddings(ctx, llm):
    from mentor_socle import gpu
    from mentor_socle.llm import embeddings

    pris = []
    llm._vecteur = lambda t: pris.append(gpu.etat()) or [1.0, 0.0]
    assert embeddings(ctx, ["a"]) == [[1.0, 0.0]] and pris == [None]
