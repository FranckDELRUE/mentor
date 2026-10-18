"""PIN parent : hachage scrypt et cookie de session signé."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets

from itsdangerous import BadSignature, URLSafeTimedSerializer

_PIN = re.compile(r"\d{4,12}")
_N, _R, _P = 2**14, 8, 1
DUREE_SESSION_S = 12 * 3600


def _scrypt(pin: str, sel: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(pin.encode("utf-8"), salt=sel, n=n, r=r, p=p, dklen=32, maxmem=64 * 1024 * 1024)


def hacher_pin(pin: str) -> str:
    """Empreinte ``scrypt$n$r$p$sel$hash`` d'un PIN de 4 à 12 chiffres (``ValueError`` sinon)."""
    if not _PIN.fullmatch(pin):
        raise ValueError("Le PIN doit comporter de 4 à 12 chiffres.")
    sel = secrets.token_bytes(16)
    return f"scrypt${_N}${_R}${_P}${sel.hex()}${_scrypt(pin, sel, _N, _R, _P).hex()}"


def verifier_pin(pin: str, empreinte: str) -> bool:
    """Compare en temps constant ; une empreinte illisible ou vide n'accepte rien."""
    try:
        algo, n, r, p, sel, attendu = empreinte.split("$")
        if algo != "scrypt":
            return False
        calcule = _scrypt(pin, bytes.fromhex(sel), int(n), int(r), int(p))
        return hmac.compare_digest(calcule, bytes.fromhex(attendu))
    except (ValueError, TypeError):
        return False


def serialiseur(secret: str) -> URLSafeTimedSerializer:
    """Signeur de cookies ; changer de PIN invalide les sessions ouvertes."""
    return URLSafeTimedSerializer(secret, salt="mentor-parent")


def jeton_valide(signeur: URLSafeTimedSerializer, jeton: str | None, duree_s: int = DUREE_SESSION_S) -> bool:
    """Vrai si ``jeton`` est signé, non expiré et émis pour le parent."""
    if not jeton:
        return False
    try:
        return signeur.loads(jeton, max_age=duree_s) == "parent"
    except BadSignature:
        return False
