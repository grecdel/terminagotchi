-- Salle d'entraînement : exercices vérifiés et « Star de la semaine ». Ré-exécutable ; le déploiement applique schema.sql, qui contient les mêmes lignes.
-- Chaque exercice réussi envoyé par le jeu, vérifié ou non : le serveur refait le tirage à partir de (graine, n)
-- (voir src/entrainement.js) ; une même (graine, n) ne sert qu'une fois.
CREATE TABLE IF NOT EXISTS exercices (
  id TEXT PRIMARY KEY,
  joueur TEXT NOT NULL,
  partie TEXT NOT NULL,
  famille TEXT NOT NULL,
  type TEXT NOT NULL,
  temps REAL NOT NULL,
  medaille TEXT NOT NULL,
  date INTEGER NOT NULL,
  semaine TEXT NOT NULL,
  graine TEXT,
  n INTEGER,
  verifie INTEGER NOT NULL DEFAULT 0,
  UNIQUE (graine, n)
);
CREATE INDEX IF NOT EXISTS exercices_record ON exercices (type, verifie, temps);
CREATE INDEX IF NOT EXISTS exercices_semaine ON exercices (semaine, famille, verifie);
CREATE INDEX IF NOT EXISTS exercices_joueur ON exercices (joueur);

-- « Star de la semaine » : la partie qui a réussi le plus d'exercices vérifiés dans une famille pendant une semaine
-- (ISO, UTC). Elle porte le titre la semaine suivante ; le site compte combien de fois chacun l'a eu.
CREATE TABLE IF NOT EXISTS titres_hebdo (
  semaine TEXT NOT NULL,
  famille TEXT NOT NULL,
  joueur TEXT NOT NULL,
  partie TEXT NOT NULL,
  n INTEGER NOT NULL,
  PRIMARY KEY (semaine, famille)
);
CREATE INDEX IF NOT EXISTS titres_hebdo_joueur ON titres_hebdo (joueur);
