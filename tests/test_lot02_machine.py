"""Lot 2 — ressources partagées de la machine : verrou GPU et registre des Mentor."""

import subprocess
import sys
import textwrap

from mentor_socle import gpu, registre


def test_verrou_gpu_detenteur_reentrance_et_autre_processus():
    assert gpu.etat() is None
    with gpu.verrou("Mentor Maths", "correction"):
        with gpu.verrou("Mentor Maths", "relecture"):  # réentrant dans le même processus
            pass
        code = textwrap.dedent("""
            from mentor_socle import gpu
            try:
                with gpu.verrou("Mentor SVT", "x", attente_s=0.3):
                    print("PRIS")
            except gpu.GpuOccupe as e:
                print("OCCUPE", e.detenteur["app"])
        """)
        sortie = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60).stdout
        assert sortie.strip() == "OCCUPE Mentor Maths"
        assert gpu.etat()["tache"] == "correction"
    assert gpu.etat() is None


def test_verrou_rend_le_detenteur_precedent():
    with gpu.verrou("Mentor Lettres", "a") as precedent:
        assert precedent is None
    with gpu.verrou("Mentor Maths", "b") as precedent:
        assert precedent["app"] == "Mentor Lettres"


def test_registre_detecte_conflit_de_port(tmp_path):
    assert registre.CODES_CONNUS["LET"][1] == 8765 and registre.CODES_CONNUS["SVT"][1] == 8768
    assert registre.enregistrer("MAT", "Mentor Maths", 8766, tmp_path, tmp_path / "i1", "0.1.0") == []
    conflits = registre.enregistrer("SVT", "Mentor SVT", 8766, tmp_path, tmp_path / "i2", "0.1.0")
    assert conflits and "Mentor Maths" in conflits[0]
    assert set(registre.lire()) == {"MAT", "SVT"}
    assert registre.lire()["SVT"].inbox == str(tmp_path / "i2")
