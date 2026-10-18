"""QR des feuilles : ``MENTOR1|<APP>|<APP>-<AA>-<NNNN>|<page>/<total>``."""

from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import cv2
import numpy as np
import segno
import zxingcpp

PREFIXE = "MENTOR1"
_APP = re.compile(r"[A-Z]{3}")
_FORMAT = re.compile(r"MENTOR1\|([A-Z]{3})\|([^|\s]+)\|(\d+)/(\d+)")


@dataclass(frozen=True)
class InfoQR:
    """Contenu décodé d'un QR de feuille."""

    app: str
    feuille: str
    page: int
    total: int


def encoder(app: str, feuille: str, page: int, total: int) -> str:
    """Texte du QR ; ``ValueError`` si l'un des champs est invalide."""
    if not _APP.fullmatch(app):
        raise ValueError(f"code d'application invalide : {app!r} (trois majuscules attendues)")
    if not feuille or "|" in feuille or any(c.isspace() for c in feuille):
        raise ValueError(f"code de feuille invalide : {feuille!r}")
    if not 1 <= page <= total:
        raise ValueError(f"pagination invalide : {page}/{total}")
    return f"{PREFIXE}|{app}|{feuille}|{page}/{total}"


def decoder(texte: str) -> InfoQR | None:
    """Rend l'``InfoQR`` d'un texte de QR, ou ``None`` si ce n'est pas un QR Mentor."""
    m = _FORMAT.fullmatch(texte.strip())
    if not m:
        return None
    page, total = int(m.group(3)), int(m.group(4))
    if not 1 <= page <= total:
        return None
    return InfoQR(m.group(1), m.group(2), page, total)


def svg(texte: str) -> str:
    """QR en SVG autonome, avec correction d'erreur H et bordure blanche de 2 modules."""
    tampon = BytesIO()
    segno.make(texte, error="h", micro=False).save(
        tampon, kind="svg", scale=10, border=2, xmldecl=False, nl=False)
    return tampon.getvalue().decode("utf-8")


def lire(image: np.ndarray) -> list[InfoQR]:
    """QR Mentor présents dans l'image (zxing-cpp, repli OpenCV), sans doublon."""
    textes = [c.text for c in zxingcpp.read_barcodes(image)]
    if not any(decoder(t) for t in textes):
        textes += _lire_opencv(image)
    trouves: list[InfoQR] = []
    for t in textes:
        info = decoder(t)
        if info and info not in trouves:
            trouves.append(info)
    return trouves


def _lire_opencv(image: np.ndarray) -> list[str]:
    detecteur: Any = cv2.QRCodeDetector()
    try:
        ok, decodes, _, _ = detecteur.detectAndDecodeMulti(image)
    except cv2.error:
        return []
    return [t for t in decodes if t] if ok else []
