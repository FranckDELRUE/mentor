"""Mode strictement hors ligne : toute connexion non locale est refusée au niveau du socket."""

from __future__ import annotations

import ipaddress
import socket
from typing import Any


class ConnexionInterdite(ConnectionRefusedError):
    """Tentative de connexion vers une machine non locale."""


_connect_origine = socket.socket.connect
_connect_ex_origine = socket.socket.connect_ex
_actif = False


def est_local(hote: str) -> bool:
    """Vrai pour ``localhost`` et les adresses de bouclage (IPv4 ou IPv6)."""
    hote = hote.strip().strip("[]").split("%", 1)[0].lower()
    if hote in ("localhost", "") or hote.endswith(".localhost"):
        return True
    try:
        return ipaddress.ip_address(hote).is_loopback
    except ValueError:
        return False


def _verifier(adresse: Any) -> None:
    """Refuse les adresses IP/nom non locaux ; les sockets non IP (AF_UNIX…) passent."""
    if isinstance(adresse, tuple) and adresse and isinstance(adresse[0], str) and not est_local(adresse[0]):
        raise ConnexionInterdite(f"mode hors ligne : connexion à {adresse[0]} refusée")


def _connect(self: socket.socket, adresse: Any) -> None:
    _verifier(adresse)
    return _connect_origine(self, adresse)


def _connect_ex(self: socket.socket, adresse: Any) -> int:
    _verifier(adresse)
    return _connect_ex_origine(self, adresse)


def activer() -> None:
    """Interdit les connexions non locales pour tout le processus."""
    global _actif
    socket.socket.connect = _connect  # type: ignore[method-assign]
    socket.socket.connect_ex = _connect_ex  # type: ignore[method-assign]
    _actif = True


def desactiver() -> None:
    """Rétablit le comportement normal (réservé aux tests)."""
    global _actif
    socket.socket.connect = _connect_origine  # type: ignore[method-assign]
    socket.socket.connect_ex = _connect_ex_origine  # type: ignore[method-assign]
    _actif = False


def actif() -> bool:
    return _actif
