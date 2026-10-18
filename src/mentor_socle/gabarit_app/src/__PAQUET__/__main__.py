from pathlib import Path

from mentor_socle.cli import main

from .discipline import __CLASSE__


def run() -> None:
    main(__CLASSE__, racine=Path(__file__).resolve().parents[2])


if __name__ == "__main__":
    run()
