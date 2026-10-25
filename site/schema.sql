-- Base de données du recensement (Cloudflare D1 = SQLite). Ré-exécutable sans risque.
CREATE TABLE IF NOT EXISTS joueurs (
  id TEXT PRIMARY KEY,
  pseudo TEXT NOT NULL UNIQUE COLLATE NOCASE,
  etat TEXT NOT NULL DEFAULT '{}',
  xp INTEGER NOT NULL DEFAULT 0,
  niveau INTEGER NOT NULL DEFAULT 1,
  cree INTEGER NOT NULL,
  maj INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS joueurs_xp ON joueurs (xp DESC);

-- Clés d'accès : une par appareil (téléphone, PC…). Seule leur empreinte est stockée.
CREATE TABLE IF NOT EXISTS cles (
  empreinte TEXT PRIMARY KEY,
  joueur TEXT NOT NULL,
  appareil TEXT NOT NULL,
  cree INTEGER NOT NULL
);

-- Codes à 6 caractères pour relier un nouvel appareil (valables 10 minutes).
CREATE TABLE IF NOT EXISTS codes (
  code TEXT PRIMARY KEY,
  joueur TEXT NOT NULL,
  expire INTEGER NOT NULL
);

-- Badges délivrés et vérifiés par le serveur.
CREATE TABLE IF NOT EXISTS badges (
  id TEXT PRIMARY KEY,
  joueur TEXT NOT NULL,
  type TEXT NOT NULL,
  titre TEXT NOT NULL,
  date INTEGER NOT NULL,
  UNIQUE (joueur, type)
);

-- Limites anti-abus (essais par minute).
CREATE TABLE IF NOT EXISTS essais (
  sujet TEXT NOT NULL,
  minute INTEGER NOT NULL,
  n INTEGER NOT NULL,
  PRIMARY KEY (sujet, minute)
);

-- Réglages internes (secret du serveur, généré au premier lancement).
CREATE TABLE IF NOT EXISTS config (
  cle TEXT PRIMARY KEY,
  valeur TEXT NOT NULL
);

-- Anti-triche : chaque (graine, compteur) ne sert qu'à UNE capture vérifiée.
-- (graine = « AAAA-MM-JJ.poste », voir site/src/tirage.js ; le secret vient de `wrangler secret put SECRET_GRAINES`)
CREATE TABLE IF NOT EXISTS apparitions (
  graine TEXT NOT NULL,
  n INTEGER NOT NULL,
  joueur TEXT NOT NULL,
  capture TEXT NOT NULL,
  date INTEGER NOT NULL,
  PRIMARY KEY (graine, n)
);
CREATE INDEX IF NOT EXISTS apparitions_joueur ON apparitions (joueur);

-- Plusieurs parties (créatures) par compte. Partie « 1 » = la créature d'avant les parties multiples.
-- La ligne `joueurs` garde une copie de la meilleure partie (profil, classement, galerie).
CREATE TABLE IF NOT EXISTS parties (
  joueur TEXT NOT NULL,
  partie TEXT NOT NULL,
  etat TEXT NOT NULL DEFAULT '{}',
  xp INTEGER NOT NULL DEFAULT 0,
  niveau INTEGER NOT NULL DEFAULT 1,
  cree INTEGER NOT NULL,
  maj INTEGER NOT NULL,
  PRIMARY KEY (joueur, partie)
);
-- Migration (ré-exécutable) : la créature existante de chaque compte devient sa partie 1.
INSERT OR IGNORE INTO parties (joueur, partie, etat, xp, niveau, cree, maj)
  SELECT id, '1', etat, xp, niveau, cree, maj FROM joueurs
  WHERE etat <> '{}' AND NOT EXISTS (SELECT 1 FROM parties p WHERE p.joueur = joueurs.id);

-- Code de secours (un par compte) : seule son empreinte HMAC est stockée.
CREATE TABLE IF NOT EXISTS secours (
  empreinte TEXT PRIMARY KEY,
  joueur TEXT NOT NULL UNIQUE,
  cree INTEGER NOT NULL
);

-- Sessions du site, ouvertes par un lien à usage unique (`compte site`). Seule l'empreinte est stockée.
CREATE TABLE IF NOT EXISTS sessions (
  empreinte TEXT PRIMARY KEY,
  joueur TEXT NOT NULL,
  expire INTEGER NOT NULL
);
