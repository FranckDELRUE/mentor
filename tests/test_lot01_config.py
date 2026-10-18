"""Lot 1 — configuration commune et mode hors ligne."""

import datetime as dt
import socket

import pytest
import yaml
from pydantic import ValidationError

from mentor_socle import offline
from mentor_socle.config import Evaluation, Periode, SocleSettings, charger_settings


def test_settings_valides_et_chemins_resolus(tmp_path):
    (tmp_path / "config").mkdir()
    f = tmp_path / "config" / "settings.yaml"
    f.write_text(yaml.safe_dump({
        "app": {"port": 8767},
        "calendrier": {"vacances": [{"nom": "Toussaint", "debut": "2026-10-17", "fin": "2026-11-02"}]},
    }), encoding="utf-8")
    s = charger_settings(f)
    assert s.app.host == "127.0.0.1" and s.app.strict_offline is True
    assert s.chemins.data == (tmp_path / "data").resolve()
    assert s.chemins.inbox == s.chemins.data / "inbox"
    assert s.chemins.sauvegardes == s.chemins.data / "sauvegardes"
    assert s.calendrier.zone == "B"
    assert s.calendrier.en_vacances(dt.date(2026, 10, 20))
    assert not s.calendrier.en_vacances(dt.date(2026, 11, 3))
    assert s.charge.hebdo_min == 90 and s.charge.seance_max_min == 25 and s.charge.coefficient_vacances == 1.5
    assert s.eleve.annee_scolaire == "2026-2027"


def test_settings_refuse_cle_inconnue_port_invalide_et_periode_inversee():
    with pytest.raises(ValidationError):
        SocleSettings.model_validate({"app": {"port": 80}})
    with pytest.raises(ValidationError):
        SocleSettings.model_validate({"app": {"port": 8765}, "inconnue": 1})
    with pytest.raises(ValidationError):
        Periode(nom="x", debut=dt.date(2026, 2, 1), fin=dt.date(2026, 1, 1))
    assert Evaluation(date=dt.date(2026, 11, 20), type="ds").coefficient == 1.0


def test_une_discipline_ajoute_sa_section(tmp_path):
    from pydantic import BaseModel

    class Pedagogie(BaseModel):
        niveau_exigence: int = 2

    class SettingsX(SocleSettings):
        pedagogie: Pedagogie = Pedagogie()

    (tmp_path / "config").mkdir()
    f = tmp_path / "config" / "settings.yaml"
    f.write_text("app: {port: 8770}\npedagogie: {niveau_exigence: 3}\n", encoding="utf-8")
    assert charger_settings(f, SettingsX).pedagogie.niveau_exigence == 3


def test_mode_hors_ligne():
    assert offline.est_local("127.0.0.1") and offline.est_local("::1") and offline.est_local("localhost")
    assert not offline.est_local("ollama.com") and not offline.est_local("8.8.8.8")
    offline.activer()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with pytest.raises(offline.ConnexionInterdite):
            s.connect(("93.184.216.34", 80))
        s.close()
        serveur = socket.socket()
        serveur.bind(("127.0.0.1", 0))
        serveur.listen(1)
        client = socket.socket()
        client.connect(serveur.getsockname())  # local : autorisé
        client.close()
        serveur.close()
    finally:
        offline.desactiver()
