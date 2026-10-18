"""Cohérence du kit : contrôles génériques du socle + contrôles de la discipline."""

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE / "src"))

from mentor_socle.referentiel import verifier_kit  # noqa: E402

from __PAQUET__.discipline import __CLASSE__  # noqa: E402

raise SystemExit(verifier_kit(__CLASSE__(RACINE)))
