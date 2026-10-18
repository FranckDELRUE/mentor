-- Schéma commun à tous les Mentor. Les disciplines ajoutent leurs tables dans leurs propres
-- migrations (espace = code discipline) et peuvent compléter les colonnes `meta` (JSON).
-- Dates : texte ISO 8601. Identifiants du référentiel stockés tels quels (C05, E-RAIS-CAUSE…).

CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,                 -- cours, ds_sujet, ds_copie, copie_mentor, photocopie, bulletin…
    date_document TEXT,
    chapitres TEXT NOT NULL DEFAULT '[]',
    fichier_source TEXT NOT NULL,
    empreinte_sha256 TEXT NOT NULL UNIQUE,
    statut TEXT NOT NULL DEFAULT 'recu', -- recu, pretraite, transcrit, a_valider, valide, rejete
    meta TEXT NOT NULL DEFAULT '{}',
    cree_le TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
    modifie_le TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
);

CREATE TABLE pages (
    id INTEGER PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    numero INTEGER NOT NULL,
    image TEXT NOT NULL,
    qr TEXT,                            -- JSON : {app, feuille, page, total}
    redressee INTEGER NOT NULL DEFAULT 0,
    UNIQUE (document_id, numero)
);

CREATE TABLE zones (
    id INTEGER PRIMARY KEY,
    page_id INTEGER NOT NULL REFERENCES pages(id) ON DELETE CASCADE,
    type TEXT NOT NULL DEFAULT 'texte', -- texte, schema, graphique, calcul, carte, figure
    bbox TEXT,                          -- JSON [x0, y0, x1, y1] en pixels
    texte_ocr TEXT,
    confiance REAL,
    texte_valide TEXT,
    valide_par_parent INTEGER NOT NULL DEFAULT 0,
    meta TEXT NOT NULL DEFAULT '{}'
);

-- Corpus : le cours du professeur, découpé et sourcé. Il fait foi.
CREATE TABLE segments (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,          -- ex. C05-012
    chapitre TEXT NOT NULL,
    document_id INTEGER REFERENCES documents(id) ON DELETE SET NULL,
    zone_ids TEXT NOT NULL DEFAULT '[]',
    texte TEXT NOT NULL,
    nature TEXT NOT NULL DEFAULT 'cours',
    embedding BLOB,                     -- float32, normalisé
    meta TEXT NOT NULL DEFAULT '{}',
    cree_le TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
);
CREATE INDEX idx_segments_chapitre ON segments(chapitre);

-- Feuilles imprimées : exercices, sujets, corrigés, récapitulatifs, cartes. Le QR porte le code.
CREATE TABLE feuilles (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,          -- ex. MAT-26-0042
    type TEXT NOT NULL,                 -- exercice, sujet, corrige, recapitulatif, cartes, remediation…
    titre TEXT NOT NULL DEFAULT '',
    chapitres TEXT NOT NULL DEFAULT '[]',
    competences TEXT NOT NULL DEFAULT '[]',
    niveau_exigence INTEGER,
    contenu TEXT NOT NULL DEFAULT '{}',
    corrige TEXT,
    sources TEXT NOT NULL DEFAULT '[]', -- références de segments / du référentiel
    statut TEXT NOT NULL DEFAULT 'brouillon', -- brouillon, a_valider, prete, imprimee, rendue, corrigee, abandonnee
    duree_min INTEGER,
    pdf TEXT,
    imprime_le TEXT,
    cree_le TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
);

CREATE TABLE copies (
    id INTEGER PRIMARY KEY,
    feuille_id INTEGER REFERENCES feuilles(id),
    document_id INTEGER NOT NULL REFERENCES documents(id),
    transcription TEXT,                 -- JSON validé
    correction TEXT,                    -- JSON validé
    note_indicative REAL,
    sur REAL DEFAULT 20,
    statut TEXT NOT NULL DEFAULT 'a_transcrire', -- a_transcrire, a_valider, a_corriger, corrigee, rendue
    pdf_annote TEXT,
    cree_le TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
);

-- Notes du professeur (saisies par le parent) : la vérité terrain pour calibrer la correction.
CREATE TABLE notes_reelles (
    id INTEGER PRIMARY KEY,
    evaluation TEXT NOT NULL,
    date TEXT NOT NULL,
    note REAL NOT NULL,
    sur REAL NOT NULL DEFAULT 20,
    coefficient REAL NOT NULL DEFAULT 1,
    appreciation TEXT,
    rang TEXT,
    document_id INTEGER REFERENCES documents(id),
    saisi_le TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
);

CREATE TABLE erreurs (
    id INTEGER PRIMARY KEY,
    copie_id INTEGER REFERENCES copies(id) ON DELETE CASCADE,
    code TEXT NOT NULL,                 -- code de la taxonomie d'erreurs de la discipline
    chapitre TEXT,
    competence TEXT,
    extrait TEXT,
    gravite INTEGER NOT NULL DEFAULT 2, -- 1 mineure, 2 notable, 3 grave
    date TEXT NOT NULL
);
CREATE INDEX idx_erreurs_code_date ON erreurs(code, date);

CREATE TABLE competences (
    code TEXT PRIMARY KEY,
    chapitre TEXT,
    maitrise REAL NOT NULL DEFAULT 0.5, -- 0..1
    incertitude REAL NOT NULL DEFAULT 0.35,
    nb_observations INTEGER NOT NULL DEFAULT 0,
    maj_le TEXT
);

CREATE TABLE cartes (
    id INTEGER PRIMARY KEY,
    recto TEXT NOT NULL,
    verso TEXT NOT NULL,
    source TEXT NOT NULL,               -- segment ou entrée du référentiel
    chapitre TEXT,
    boite INTEGER NOT NULL DEFAULT 1,
    prochaine_revue TEXT NOT NULL,
    historique TEXT NOT NULL DEFAULT '[]',
    suspendue INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_cartes_revue ON cartes(prochaine_revue);

-- Tout ce que le parent doit trancher : transcription douteuse, divergence cours/référentiel,
-- sujet sensible, porte de vérification bloquée…
CREATE TABLE validations (
    id INTEGER PRIMARY KEY,
    objet_type TEXT NOT NULL,
    objet_id INTEGER NOT NULL,
    motif TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '{}',
    statut TEXT NOT NULL DEFAULT 'ouverte', -- ouverte, acceptee, refusee
    decision TEXT,
    cree_le TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
    decide_le TEXT
);

CREATE TABLE taches (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,
    statut TEXT NOT NULL DEFAULT 'en_attente', -- en_attente, en_cours, a_valider, faite, echec
    priorite INTEGER NOT NULL DEFAULT 5,       -- 1 la plus urgente
    payload TEXT NOT NULL DEFAULT '{}',
    resultat TEXT,
    erreur TEXT,
    essais INTEGER NOT NULL DEFAULT 0,
    max_essais INTEGER NOT NULL DEFAULT 2,
    cree_le TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
    debut_le TEXT,
    fin_le TEXT
);
CREATE INDEX idx_taches_file ON taches(statut, priorite, id);

CREATE TABLE llm_appels (
    id INTEGER PRIMARY KEY,
    role TEXT NOT NULL,
    modele TEXT NOT NULL,
    prompt TEXT NOT NULL,
    version_prompt TEXT,
    entree_sha256 TEXT,
    sortie TEXT,
    ok INTEGER NOT NULL,
    reparation INTEGER NOT NULL DEFAULT 0,
    erreur TEXT,
    duree_ms INTEGER,
    tache_id INTEGER REFERENCES taches(id) ON DELETE SET NULL,
    cree_le TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
);
