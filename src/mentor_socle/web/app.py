"""Interface parent : tableau de bord, dépôt de scans, validations, tâches, feuilles."""

from __future__ import annotations

import datetime as dt
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import ChoiceLoader, Environment, FileSystemLoader, select_autoescape

from mentor_socle import __version__, gpu, registre
from mentor_socle.db import dejs
from mentor_socle.impression import feuilles
from mentor_socle.pedagogie import competences, erreurs, planificateur
from mentor_socle.scan import inbox
from mentor_socle.taches import ajouter
from mentor_socle.web.auth import DUREE_SESSION_S, jeton_valide, serialiseur, verifier_pin

if TYPE_CHECKING:
    from mentor_socle.contexte import Contexte

DOSSIER_WEB = Path(__file__).parent
EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp"}
TAILLE_MAX = 200 * 1024 * 1024
COOKIE = "mentor_session"
ECHECS_MAX, BLOCAGE_S = 5, 60
STATUTS_VALIDATION = {"acceptee", "refusee"}


def _environnement(ctx: Contexte) -> Environment:
    """Gabarits de la discipline (``templates/web/``) d'abord, puis ceux du socle."""
    env = Environment(
        loader=ChoiceLoader([
            FileSystemLoader(str(ctx.discipline.dossier_gabarits / "web")),
            FileSystemLoader(str(DOSSIER_WEB / "templates")),
        ]),
        autoescape=select_autoescape(["html"]),
    )
    env.policies["json.dumps_kwargs"] = {"sort_keys": True, "ensure_ascii": False}
    env.filters["dejs"] = dejs
    return env


def creer_app(ctx: Contexte) -> FastAPI:
    """Construit l'application FastAPI de l'interface parent pour ``ctx``."""
    app = FastAPI(title=ctx.discipline.nom, docs_url=None, redoc_url=None, openapi_url=None)
    env = _environnement(ctx)
    app.mount("/static", StaticFiles(directory=str(DOSSIER_WEB / "static")), name="static")
    echecs: list[float] = []

    def pin_hash() -> str:
        return ctx.settings.parent.pin_hash

    def signeur():
        return serialiseur(pin_hash())

    def page(nom: str, request: Request, statut: int = 200, **variables: Any) -> HTMLResponse:
        nb = ctx.cx.execute("SELECT COUNT(*) FROM validations WHERE statut = 'ouverte'").fetchone()[0]
        autres = {c: e for c, e in registre.lire().items() if c != ctx.discipline.code}
        contexte = {
            "ctx": ctx, "app_nom": ctx.discipline.nom, "version_socle": __version__,
            "pin_defini": bool(pin_hash()), "nb_validations": nb, "gpu": gpu.etat(),
            "autres_mentor": autres, "menu_discipline": ctx.discipline.liens_menu(), **variables,
        }
        return HTMLResponse(env.get_template(nom).render(**contexte), status_code=statut)

    @app.middleware("http")
    async def exiger_pin(request: Request, appel):
        libre = request.url.path in ("/connexion", "/deconnexion") or request.url.path.startswith("/static/")
        if pin_hash() and not libre and not jeton_valide(signeur(), request.cookies.get(COOKIE)):
            return RedirectResponse("/connexion", status_code=303)
        return await appel(request)

    # --- accès ------------------------------------------------------------------------------
    @app.get("/connexion")
    def connexion(request: Request, erreur: int = 0):
        return page("connexion.html", request, erreur=bool(erreur))

    @app.post("/connexion")
    def connecter(pin: str = Form("")):
        maintenant = time.monotonic()
        echecs[:] = [t for t in echecs if maintenant - t < BLOCAGE_S]
        if len(echecs) >= ECHECS_MAX:
            raise HTTPException(429, "Trop d'essais : patienter une minute.")
        if not pin_hash() or not verifier_pin(pin, pin_hash()):
            echecs.append(maintenant)
            return RedirectResponse("/connexion?erreur=1", status_code=303)
        reponse = RedirectResponse("/", status_code=303)
        reponse.set_cookie(COOKIE, signeur().dumps("parent"), max_age=DUREE_SESSION_S,
                           httponly=True, samesite="strict")
        return reponse

    @app.get("/deconnexion")
    def deconnexion():
        reponse = RedirectResponse("/connexion", status_code=303)
        reponse.delete_cookie(COOKIE)
        return reponse

    # --- tableau de bord ----------------------------------------------------------------------
    @app.get("/")
    def tableau(request: Request):
        aujourdhui = dt.date.today()
        prochaines = sorted((e for e in ctx.settings.calendrier.evaluations if e.date >= aujourdhui),
                            key=lambda e: e.date)[:5]
        notes = [dict(n) for n in ctx.cx.execute("SELECT * FROM notes_reelles ORDER BY date DESC LIMIT 6")]
        etats = {r[0]: r[1] for r in ctx.cx.execute("SELECT statut, COUNT(*) FROM taches GROUP BY statut")}
        return page(
            "tableau.html", request,
            plan=planificateur.planifier(ctx), prochaines=prochaines, notes=notes, etats=etats,
            recurrentes=[{**r, "occurrences": r["nb"]} for r in erreurs.recurrentes(ctx.cx)],
            priorites=competences.priorites(ctx.cx, limite=5),
        )

    # --- dépôt de scans -----------------------------------------------------------------------
    @app.get("/depot")
    def depot(request: Request):
        return page("depot.html", request, message="")

    @app.post("/depot")
    def deposer(request: Request, fichier: UploadFile, type_document: str = Form(""),
                date_document: str = Form("")):
        extension = Path(fichier.filename or "").suffix.lower()
        if extension not in EXTENSIONS:
            raise HTTPException(400, f"Extension non acceptée : {extension or '(aucune)'}.")
        if date_document:
            try:
                dt.date.fromisoformat(date_document)
            except ValueError:
                raise HTTPException(400, "Date invalide.") from None
        dossier = ctx.data / "_depot"
        dossier.mkdir(parents=True, exist_ok=True)
        temporaire = dossier / f"{uuid.uuid4().hex}{extension}"
        taille = 0
        with temporaire.open("wb") as sortie:
            while bloc := fichier.file.read(1024 * 1024):
                taille += len(bloc)
                if taille > TAILLE_MAX:
                    sortie.close()
                    temporaire.unlink(missing_ok=True)
                    raise HTTPException(413, "Fichier trop volumineux.")
                sortie.write(bloc)
        statut, valeur = inbox.ingerer_fichier(ctx, temporaire, type_document or None, date_document or None)
        message = {
            "recu": f"Document n°{valeur} reçu : la transcription est en file d'attente.",
            "doublon": f"Déjà reçu (document n°{valeur}).",
            "renvoye": f"Feuille d'un autre Mentor ({valeur}) : transmise à sa boîte de dépôt.",
            "illisible": f"Fichier illisible : {valeur}",
        }[statut]
        return page("depot.html", request, message=message)

    @app.post("/inbox/scanner")
    def relever(request: Request):
        bilan = inbox.scanner(ctx)
        message = (f"Relevé : {len(bilan.recus)} reçu(s), {len(bilan.doublons)} doublon(s), "
                   f"{len(bilan.renvoyes)} renvoyé(s), {len(bilan.illisibles)} illisible(s).")
        return page("depot.html", request, message=message)

    # --- validations --------------------------------------------------------------------------
    @app.get("/validations")
    def validations(request: Request):
        lignes = ctx.cx.execute("SELECT * FROM validations WHERE statut = 'ouverte' ORDER BY id").fetchall()
        return page("validations.html", request, validations=[dict(v) for v in lignes])

    @app.post("/validations/{vid}")
    def decider(vid: int, statut: str = Form(""), decision: str = Form("")):
        if statut not in STATUTS_VALIDATION:
            raise HTTPException(400, "Statut inconnu.")
        cur = ctx.cx.execute(
            "UPDATE validations SET statut = ?, decision = ?, "
            "decide_le = strftime('%Y-%m-%dT%H:%M:%S','now','localtime') WHERE id = ? AND statut = 'ouverte'",
            (statut, decision, vid))
        if cur.rowcount == 0:
            raise HTTPException(404, "Validation introuvable ou déjà décidée.")
        return RedirectResponse("/validations", status_code=303)

    # --- tâches -------------------------------------------------------------------------------
    @app.get("/taches")
    def liste_taches(request: Request):
        lignes = ctx.cx.execute("SELECT * FROM taches ORDER BY id DESC LIMIT 100").fetchall()
        return page("taches.html", request, taches=[dict(t) for t in lignes])

    @app.post("/taches/{tid}/relancer")
    def relancer(tid: int):
        cur = ctx.cx.execute(
            "UPDATE taches SET statut = 'en_attente', essais = 0, erreur = NULL, debut_le = NULL, "
            "fin_le = NULL WHERE id = ? AND statut = 'echec'", (tid,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Aucune tâche en échec avec ce numéro.")
        return RedirectResponse("/taches", status_code=303)

    @app.post("/sauvegarde")
    def sauvegarder():
        ajouter(ctx.cx, "sauvegarde")
        return RedirectResponse("/taches", status_code=303)

    # --- feuilles -----------------------------------------------------------------------------
    @app.get("/feuilles")
    def liste_feuilles(request: Request):
        lignes = ctx.cx.execute("SELECT * FROM feuilles ORDER BY id DESC LIMIT 200").fetchall()
        return page("feuilles.html", request, feuilles=[dict(f) for f in lignes])

    @app.post("/feuilles/{fid}/verifier")
    def verifier_feuille(fid: int):
        if not ctx.cx.execute("SELECT 1 FROM feuilles WHERE id = ?", (fid,)).fetchone():
            raise HTTPException(404, "Feuille inconnue.")
        feuilles.verifier(ctx, fid)
        return RedirectResponse("/feuilles", status_code=303)

    @app.post("/feuilles/{fid}/imprimer")
    def imprimer_feuille(request: Request, fid: int):
        try:
            feuilles.imprimer(ctx, fid)
        except KeyError:
            raise HTTPException(404, "Feuille inconnue.") from None
        except feuilles.FeuilleNonPrete as e:
            raise HTTPException(409, str(e)) from None
        lignes = ctx.cx.execute("SELECT * FROM feuilles ORDER BY id DESC LIMIT 200").fetchall()
        return page("feuilles.html", request, feuilles=[dict(f) for f in lignes])

    @app.get("/pdf/{code}")
    def pdf(code: str) -> Response:
        ligne = ctx.cx.execute("SELECT pdf FROM feuilles WHERE code = ?", (code,)).fetchone()
        if not ligne or not ligne["pdf"] or not Path(ligne["pdf"]).is_file():
            raise HTTPException(404, "PDF introuvable.")
        return FileResponse(ligne["pdf"], media_type="application/pdf", filename=f"{code}.pdf")

    for routeur in ctx.discipline.routeurs():
        app.include_router(routeur)
    return app
