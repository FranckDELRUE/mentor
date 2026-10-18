"""Lecture et prétraitement des scans (chemins accentués inclus : pas de ``cv2.imread``)."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pymupdf

EXTENSIONS_IMAGE = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


def _lire_image(fichier: Path) -> np.ndarray:
    donnees = np.fromfile(str(fichier), dtype=np.uint8)
    img = cv2.imdecode(donnees, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"image illisible : {fichier}")
    return img


def pages(fichier: Path | str, dpi: int = 200) -> list[np.ndarray]:
    """Pages d'un PDF (rendues à ``dpi``) ou image unique, en BGR."""
    fichier = Path(fichier)
    if fichier.suffix.lower() != ".pdf":
        return [_lire_image(fichier)]
    resultat: list[np.ndarray] = []
    with pymupdf.open(fichier) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False)
            rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
            resultat.append(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    return resultat


def _gris(img: np.ndarray) -> np.ndarray:
    return img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def angle_inclinaison(img: np.ndarray) -> float:
    """Inclinaison (degrés) des lignes d'écriture ; positive si le côté droit descend. 0 si indécidable."""
    gris = _gris(img)
    w = gris.shape[1]
    bords = cv2.Canny(cv2.GaussianBlur(gris, (3, 3), 0), 50, 150)
    lignes = cv2.HoughLinesP(bords, 1, np.pi / 720, threshold=80, minLineLength=int(w * 0.3), maxLineGap=20)
    if lignes is None:
        return 0.0
    angles = []
    for x1, y1, x2, y2 in np.asarray(lignes).reshape(-1, 4):  # la forme change selon la version d'OpenCV
        a = float(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if abs(a) <= 15:
            angles.append(a)
    return float(np.median(angles)) if angles else 0.0


def redresser(img: np.ndarray) -> tuple[np.ndarray, float]:
    """Redresse l'image ; rend ``(image, angle_corrige)``. Fond blanc ajouté dans les coins."""
    angle = angle_inclinaison(img)
    if abs(angle) < 0.2:
        return img, 0.0
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    fond = 255 if img.ndim == 2 else (255, 255, 255)
    return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_CUBIC, borderValue=fond), angle


def ameliorer(img: np.ndarray) -> np.ndarray:
    """Niveaux de gris avec égalisation locale du contraste (CLAHE)."""
    return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(_gris(img))


def pour_vision(img: np.ndarray, cote_max: int) -> np.ndarray:
    """Réduit l'image pour que son plus grand côté ne dépasse pas ``cote_max``."""
    h, w = img.shape[:2]
    plus_grand = max(h, w)
    if plus_grand <= cote_max:
        return img
    f = cote_max / plus_grand
    return cv2.resize(img, (max(1, round(w * f)), max(1, round(h * f))), interpolation=cv2.INTER_AREA)


def enregistrer(img: np.ndarray, chemin: Path | str) -> Path:
    """Écrit l'image (format choisi par l'extension) ; crée les dossiers ; rend le chemin."""
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    ok, tampon = cv2.imencode(chemin.suffix or ".png", img)
    if not ok:
        raise ValueError(f"encodage impossible : {chemin}")
    tampon.tofile(str(chemin))
    return chemin
