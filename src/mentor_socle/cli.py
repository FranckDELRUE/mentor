"""Ligne de commande : ``main`` (un Mentor : ``mentor …``) et ``main_socle`` (``mentor-socle …``)."""

from __future__ import annotations

import argparse
import getpass
import re
import sys
import threading
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from mentor_socle import __version__, gpu, registre, sauvegarde
from mentor_socle import journal as journal_app
from mentor_socle.contexte import Contexte
from mentor_socle.discipline import Discipline
from mentor_socle.referentiel import verifier_kit

if TYPE_CHECKING:
    from mentor_socle.config import SocleSettings

INTERVALLE_VEILLE_S = 30.0


# --- utilitaires -------------------------------------------------------------------------------
def _ouvrir(discipline: Discipline) -> Contexte:
    """Contexte du Mentor, avec le journal applicatif branché dans ``<data>/journal``."""
    ctx = Contexte.ouvrir(discipline)
    journal_app.configurer(ctx.data / "journal")
    return ctx


def _afficher_gpu() -> None:
    detenteur = gpu.etat()
    if detenteur is None:
        print("GPU libre.")
    else:
        print(f"GPU occupé par {detenteur.get('app')} ({detenteur.get('tache')}) "
              f"depuis {detenteur.get('depuis')}, processus {detenteur.get('pid')}.")


def _modele_installe(modele: str, installes: Sequence[str]) -> bool:
    return modele in installes or f"{modele}:latest" in installes


# --- commandes d'un Mentor ---------------------------------------------------------------------
def _verifications(discipline: Discipline) -> list[tuple[str, bool, str]]:
    """Contrôles de ``mentor check`` : ``(libellé, réussi, détail)``."""
    from mentor_socle.llm.modeles import charger_modeles
    from mentor_socle.llm.ollama import ClientOllama

    resultats: list[tuple[str, bool, str]] = []
    try:
        ctx = Contexte.ouvrir(discipline)
    except Exception as e:  # noqa: BLE001 — tout échec d'ouverture est un résultat de contrôle
        return [("Settings et base", False, str(e))]
    resultats.append(("Settings et base", True, str(ctx.data)))
    reglages = ctx.settings
    resultats.append(("Code QR", True, f"{discipline.code}, port {reglages.app.port}"))
    autres = [e for e in registre.lire().values() if e.code != discipline.code and e.port == reglages.app.port]
    resultats.append(("Port libre dans le registre", not autres,
                      ", ".join(f"{e.nom} ({e.code})" for e in autres) or "aucun conflit"))
    # Un PIN absent est une alerte, pas un échec : l'accès libre est le comportement documenté.
    resultats.append(("Code PIN parent", True, "défini" if reglages.parent.pin_hash
                      else "ABSENT, accès libre (mentor parent set-pin)"))
    resultats.append(("Kit", verifier_kit(discipline, afficher=False) == 0, "mentor kit pour le détail"))
    try:
        installes = ClientOllama(reglages.ollama.url, reglages.ollama.timeout_s)
        version = installes.version()
        resultats.append(("Ollama", True, f"version {version}"))
        presents = installes.modeles_installes()
        manquants = sorted({r.modele for r in charger_modeles(discipline.dossier_config).roles.values()
                            if not _modele_installe(r.modele, presents)})
        resultats.append(("Modèles installés", not manquants,
                          "tous présents" if not manquants else "manquants : " + ", ".join(manquants)))
    except Exception as e:  # noqa: BLE001 — Ollama absent, injoignable ou modeles.yaml illisible
        resultats.append(("Ollama", False, f"injoignable à {reglages.ollama.url} ({type(e).__name__})"))
    resultats += discipline.verifications_demarrage(ctx)
    return resultats


def _check(discipline: Discipline) -> None:
    echec = False
    for libelle, reussi, detail in _verifications(discipline):
        print(f"[{'OK' if reussi else 'ÉCHEC'}] {libelle} : {detail}")
        echec |= not reussi
    sys.exit(1 if echec else 0)


def _migrer(discipline: Discipline) -> None:
    ctx = _ouvrir(discipline)
    nb = ctx.cx.execute("SELECT count(*) FROM schema_migrations").fetchone()[0]
    print(f"Base à jour ({nb} migrations appliquées) : {ctx.data}")


def _sauvegarder(discipline: Discipline) -> None:
    print(sauvegarde.sauvegarder(_ouvrir(discipline)))


def _inbox(discipline: Discipline) -> None:
    from mentor_socle.scan import inbox

    bilan = inbox.scanner(_ouvrir(discipline))
    print(f"{len(bilan.recus)} reçu(s), {len(bilan.doublons)} doublon(s), "
          f"{len(bilan.renvoyes)} renvoyé(s) à un autre Mentor, {len(bilan.illisibles)} illisible(s).")


def _plan(discipline: Discipline) -> None:
    from mentor_socle.pedagogie import planificateur

    plan = planificateur.planifier(_ouvrir(discipline))
    if not plan:
        print("Rien à planifier.")
    for e in plan:
        print(f"{e.priorite:>2}. {e.type:<22} {e.duree_min:>3} min  {e.cible} — {e.raison}")


def _definir_pin(discipline: Discipline, pin: str | None) -> None:
    """Écrit l'empreinte du PIN dans ``config/settings.yaml`` (le PIN lui-même n'est jamais écrit)."""
    from mentor_socle.web.auth import hacher_pin

    fichier = discipline.dossier_config / "settings.yaml"
    if not fichier.is_file():
        sys.exit(f"Settings introuvables : {fichier}")
    if pin is None:
        pin = getpass.getpass("Nouveau PIN (4 à 12 chiffres) : ")
        if pin != getpass.getpass("Confirmer le PIN : "):
            sys.exit("Les deux saisies diffèrent.")
    try:
        empreinte = hacher_pin(pin)
    except ValueError as e:
        sys.exit(str(e))
    texte = fichier.read_text(encoding="utf-8")
    ligne = re.compile(r"^(\s*)pin_hash:.*$", re.MULTILINE)
    if ligne.search(texte):
        texte = ligne.sub(lambda m: f'{m.group(1)}pin_hash: "{empreinte}"', texte, count=1)
    elif re.search(r"^parent:\s*$", texte, re.MULTILINE):
        texte = re.sub(r"^parent:\s*$", f'parent:\n  pin_hash: "{empreinte}"', texte, count=1, flags=re.MULTILINE)
    else:
        texte = texte.rstrip("\n") + f'\n\nparent:\n  pin_hash: "{empreinte}"\n'
    fichier.write_text(texte, encoding="utf-8", newline="")
    print("PIN enregistré. Redémarrer « mentor serve » pour le prendre en compte.")


def _travailler(ctx: Contexte):
    from mentor_socle.gestionnaires import tous
    from mentor_socle.taches import Travailleur

    travailleur = Travailleur(ctx, tous(ctx))
    travailleur.start()
    return travailleur


def _veille(ctx: Contexte, arret: threading.Event, intervalle_s: float = INTERVALLE_VEILLE_S) -> None:
    """Boîte de dépôt toutes les ``intervalle_s`` secondes et sauvegarde automatique quand elle est due."""
    import logging

    from mentor_socle.scan import inbox
    from mentor_socle.taches import ajouter

    log = logging.getLogger("mentor.veille")
    while not arret.is_set():
        try:
            bilan = inbox.scanner(ctx)
            if bilan.recus or bilan.renvoyes or bilan.illisibles:
                log.info("Boîte de dépôt : %d reçu(s), %d renvoyé(s), %d illisible(s)",
                         len(bilan.recus), len(bilan.renvoyes), len(bilan.illisibles))
            en_file = ctx.cx.execute(
                "SELECT 1 FROM taches WHERE type = 'sauvegarde' AND statut IN ('en_attente', 'en_cours')"
            ).fetchone()
            if not en_file and sauvegarde.due(ctx):
                ajouter(ctx.cx, "sauvegarde")
        except Exception:
            log.exception("Erreur de la veille")
        arret.wait(intervalle_s)


def _servir(discipline: Discipline) -> None:
    import uvicorn

    from mentor_socle.web.app import creer_app

    ctx = _ouvrir(discipline)
    reglages: SocleSettings = ctx.settings
    for conflit in registre.enregistrer(discipline.code, discipline.nom, reglages.app.port, discipline.racine,
                                        reglages.chemins.inbox, __version__):
        print(f"Attention : {conflit}.")
    travailleur = _travailler(ctx)
    arret = threading.Event()
    threading.Thread(target=_veille, args=(ctx, arret), daemon=True, name="mentor-veille").start()
    print(f"{discipline.nom} : http://{reglages.app.host}:{reglages.app.port}")
    try:
        uvicorn.run(creer_app(ctx), host=reglages.app.host, port=reglages.app.port, log_level="info")
    finally:
        arret.set()
        travailleur.arreter()


def _travailleur_seul(discipline: Discipline) -> None:
    travailleur = _travailler(_ouvrir(discipline))
    print("Travailleur démarré (Ctrl+C pour arrêter).")
    try:
        travailleur.join()
    except KeyboardInterrupt:
        travailleur.arreter()
        travailleur.join(timeout=10)


def main(cls: type[Discipline], racine: Path | str, argv: Sequence[str] | None = None) -> None:
    """Point d'entrée de ``mentor`` pour la discipline ``cls`` installée dans ``racine``."""
    parseur = argparse.ArgumentParser(prog="mentor", description=f"{cls.nom} (mentor-socle {__version__})")
    sous = parseur.add_subparsers(dest="commande", required=True)
    for nom, aide in (
        ("check", "vérifier l'installation (Ollama, modèles, kit, port, PIN)"),
        ("serve", "lancer l'interface parent, le travailleur et la veille"),
        ("worker", "lancer seulement le travailleur de tâches"),
        ("inbox", "traiter la boîte de dépôt une fois"),
        ("migrate", "appliquer les migrations de la base"),
        ("backup", "sauvegarder la base maintenant"),
        ("kit", "vérifier la cohérence du kit (référentiel, prompts, modèles)"),
        ("plan", "afficher le plan de travail de la semaine"),
        ("gpu", "dire qui utilise le GPU"),
    ):
        sous.add_parser(nom, help=aide)
    parent = sous.add_parser("parent", help="réglages du parent").add_subparsers(dest="action", required=True)
    pin = parent.add_parser("set-pin", help="définir le code PIN de l'interface parent")
    pin.add_argument("pin", nargs="?", help="PIN (demandé sans écho si omis ; à éviter en ligne de commande)")
    args = parseur.parse_args(None if argv is None else list(argv))

    discipline = cls(racine)
    actions: dict[str, Callable[[], None]] = {
        "check": lambda: _check(discipline),
        "serve": lambda: _servir(discipline),
        "worker": lambda: _travailleur_seul(discipline),
        "inbox": lambda: _inbox(discipline),
        "migrate": lambda: _migrer(discipline),
        "backup": lambda: _sauvegarder(discipline),
        "kit": lambda: sys.exit(verifier_kit(discipline)),
        "plan": lambda: _plan(discipline),
        "gpu": _afficher_gpu,
        "parent": lambda: _definir_pin(discipline, getattr(args, "pin", None)),
    }
    actions[args.commande]()


# --- commandes du socle ------------------------------------------------------------------------
def _afficher_registre() -> None:
    entrees = registre.lire()
    if not entrees:
        print("Aucun Mentor enregistré (ils s'inscrivent au lancement de « mentor serve »).")
    for e in sorted(entrees.values(), key=lambda e: e.port):
        print(f"{e.code}  {e.port}  {e.nom}  (socle {e.version_socle})  {e.racine}")


def main_socle(argv: Sequence[str] | None = None) -> None:
    """Point d'entrée de ``mentor-socle`` : création de Mentor, registre, état du GPU."""
    from mentor_socle.gabarit import creer_projet

    parseur = argparse.ArgumentParser(prog="mentor-socle", description=f"Socle des Mentor {__version__}")
    sous = parseur.add_subparsers(dest="commande", required=True)
    nouveau = sous.add_parser("nouveau", help="créer le projet d'un nouveau Mentor")
    nouveau.add_argument("code", help="trois majuscules, ex. PHC")
    nouveau.add_argument("nom", help="nom affiché, ex. « Mentor Physique-Chimie »")
    nouveau.add_argument("dossier", type=Path, help="dossier à créer")
    nouveau.add_argument("--port", type=int, help="port (par défaut : celui réservé au code)")
    sous.add_parser("registre", help="lister les Mentor installés")
    sous.add_parser("gpu", help="dire qui utilise le GPU")
    args = parseur.parse_args(None if argv is None else list(argv))

    if args.commande == "nouveau":
        try:
            dossier = creer_projet(args.code, args.nom, args.dossier, args.port)
        except (ValueError, FileExistsError) as e:
            sys.exit(str(e))
        print(f"Projet créé : {dossier}\nSuite : cd {dossier} ; uv sync ; copier config/*.example.yaml.")
    elif args.commande == "registre":
        _afficher_registre()
    else:
        _afficher_gpu()
