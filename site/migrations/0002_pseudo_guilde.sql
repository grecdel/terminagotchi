-- Pseudo coloré par les badges de la Guilde (1er novembre). Ré-exécutable ; le déploiement applique schema.sql, qui contient les mêmes lignes.
-- Pour la vitrine de chaque joueur (sa meilleure partie) : le badge de la Guilde choisi comme titre dans le jeu
-- (« artisan », « contributeur » ou vide) et l'échelon « Artisan » recalculé par le serveur à partir des leçons de la
-- Guilde synchronisées. L'échelon « Contributeur » n'est jamais stocké : il vient des crédits du dépôt (src/guilde_donnees.js).
CREATE TABLE IF NOT EXISTS pseudos_guilde (
  joueur TEXT PRIMARY KEY,
  titre TEXT NOT NULL DEFAULT '',
  artisan TEXT,
  maj INTEGER NOT NULL
);
