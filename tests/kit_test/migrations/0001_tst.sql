-- table de discipline ; référence une table du socle
CREATE TABLE tst_extra (id INTEGER PRIMARY KEY, feuille_id INTEGER REFERENCES feuilles(id));
