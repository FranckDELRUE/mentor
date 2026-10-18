"""Lot 3 — base SQLite et migrations par espace."""

from mentor_socle import db

TABLES_SOCLE = {"documents", "pages", "zones", "segments", "feuilles", "copies", "notes_reelles", "erreurs",
                "competences", "cartes", "validations", "taches", "llm_appels"}


def test_connexion_wal_et_cles_etrangeres(tmp_path):
    cx = db.connecter(tmp_path / "x" / "base.sqlite3")
    assert cx.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert cx.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_migrations_socle_puis_discipline_idempotentes(tmp_path):
    migr = tmp_path / "migrations"
    migr.mkdir()
    (migr / "0001_tst.sql").write_text(
        "-- référence une table du socle\nCREATE TABLE tst_extra (id INTEGER PRIMARY KEY,"
        " feuille_id INTEGER REFERENCES feuilles(id));\n", encoding="utf-8")
    cx = db.connecter(tmp_path / "base.sqlite3")
    appliques = db.migrer(cx, "TST", migr)
    assert appliques[0].startswith("socle/0001") and appliques[-1] == "TST/0001_tst.sql"
    tables = {r[0] for r in cx.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert TABLES_SOCLE | {"tst_extra", "schema_migrations"} <= tables
    assert db.migrer(cx, "TST", migr) == []
    (migr / "0002_tst.sql").write_text("ALTER TABLE tst_extra ADD COLUMN note REAL;", encoding="utf-8")
    assert db.migrer(cx, "TST", migr) == ["TST/0002_tst.sql"]


def test_migration_en_erreur_annulee(tmp_path):
    migr = tmp_path / "m"
    migr.mkdir()
    (migr / "0001_tst.sql").write_text("CREATE TABLE a (x);\nCREATE TABLE feuilles (y);\n", encoding="utf-8")
    cx = db.connecter(tmp_path / "b.sqlite3")
    try:
        db.migrer(cx, "TST", migr)
    except Exception:
        pass
    assert not cx.execute("SELECT 1 FROM sqlite_master WHERE name='a'").fetchone()
    assert not cx.execute("SELECT 1 FROM schema_migrations WHERE espace='TST'").fetchone()


def test_json_aller_retour():
    assert db.dejs(db.js({"é": [1, "à"]})) == {"é": [1, "à"]}
    assert "é" in db.js("é") and db.dejs(None, []) == []
