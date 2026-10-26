/**
 * Terminagotchi — le site de recensement.
 * Un seul programme Cloudflare Worker : l'API (comptes, synchro, classement, CTF, badges)
 * et les pages du site. Données dans Cloudflare D1 (SQLite).
 */

import BESTIAIRE from "./bestiaire.js";
import { tirer, differences, stadePlausible, attirancePlausible, MAX_APPARITIONS, PAR_NOM_T, TIRAGE } from "./tirage.js";
import { LANGUES, NOMS_LANGUES, LOCALES, RTL, choisirLangue, cookieLangue, textes, libelle } from "./i18n.js";

const DEPOT = "https://github.com/grecdel/terminagotchi-android";
const STATS = ["Intelligence", "Agilité", "Force", "Endurance"];
const COULEUR = { Intelligence: 39, "Agilité": 78, Force: 203, Endurance: 221 };
const STADES = ["Œuf", "Bébé", "Ado", "Adulte"];
const ESPECES = BESTIAIRE.especes.map((e) => e.nom);
const PAR_NOM = Object.fromEntries(BESTIAIRE.especes.map((e) => [e.nom, e]));
const PAR_ID = Object.fromEntries(BESTIAIRE.especes.map((e) => [e.id, e]));
const PUBLIQUES = BESTIAIRE.especes.filter((e) => !e.secrete);
// espèces qui ont un dessin complet animé (bandes d'images dans public/anim/<id>/<stade>/<animation>.webp)
const ANIMEES = new Set(["abyssor"]);
const STADES_B = ["enfant", "ado", "adulte", "finale"];
const MARQUES = new Set(BESTIAIRE.marques);
const HUMEURS = new Set(BESTIAIRE.humeurs);
const COULEUR_RARETE = { commune: "#b0b0c0", "peu commune": "#5fd787", rare: "#5fafff", "épique": "#c77dff", "légendaire": "#ffaf00",
  mythique: "#ff5f87" };
const APPAREILS = ["android", "pc"];

// ====================================================================== outils

const enc = new TextEncoder();

function json(donnees, statut = 200, entetes = {}) {
  return new Response(JSON.stringify(donnees), {
    status: statut,
    headers: { "content-type": "application/json; charset=utf-8", "access-control-allow-origin": "*", ...entetes },
  });
}

function erreur(message, statut = 400) {
  return json({ erreur: message }, statut);
}

function texte(t, statut = 200, entetes = {}) {
  return new Response(t, { status: statut, headers: { "content-type": "text/plain; charset=utf-8", ...entetes } });
}

function hex(buf) {
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function aleatoire(n) {
  const b = new Uint8Array(n);
  crypto.getRandomValues(b);
  return hex(b);
}

async function sha256(t) {
  return hex(await crypto.subtle.digest("SHA-256", enc.encode(t)));
}

async function hmac(secret, message) {
  const k = await crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  return hex(await crypto.subtle.sign("HMAC", k, enc.encode(message)));
}

function echapper(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function niveauDe(xp) {
  return Math.floor(Math.sqrt(Math.max(0, xp) / 10)) + 1;
}

function stadeDe(n) {
  return n < 2 ? 0 : n < 5 ? 1 : n < 10 ? 2 : 3;
}

async function corps(requete) {
  try {
    const t = await requete.text();
    if (t.length > 200_000) return null;
    return t ? JSON.parse(t) : {};
  } catch {
    return null;
  }
}

async function secretServeur(env) {
  const r = await env.DB.prepare("SELECT valeur FROM config WHERE cle = 'secret'").first();
  if (r) return r.valeur;
  const s = aleatoire(32);
  await env.DB.prepare("INSERT OR IGNORE INTO config (cle, valeur) VALUES ('secret', ?)").bind(s).run();
  const r2 = await env.DB.prepare("SELECT valeur FROM config WHERE cle = 'secret'").first();
  return r2.valeur;
}

/** Limite anti-abus : au plus `max` essais par minute pour un sujet. */
async function limite(env, sujet, max) {
  const minute = Math.floor(Date.now() / 60000);
  await env.DB.prepare(
    "INSERT INTO essais (sujet, minute, n) VALUES (?, ?, 1) ON CONFLICT (sujet, minute) DO UPDATE SET n = n + 1",
  ).bind(sujet, minute).run();
  const r = await env.DB.prepare("SELECT n FROM essais WHERE sujet = ? AND minute = ?").bind(sujet, minute).first();
  if (Math.random() < 0.02) await env.DB.prepare("DELETE FROM essais WHERE minute < ?").bind(minute - 60).run();
  return r.n <= max;
}

async function authentifier(requete, env) {
  const a = requete.headers.get("authorization") || "";
  const cle = a.startsWith("Bearer ") ? a.slice(7).trim() : "";
  if (!/^[0-9a-f]{64}$/.test(cle)) return null;
  const empreinte = await sha256(cle);
  return env.DB.prepare(
    "SELECT j.*, c.empreinte AS empreinte_cle FROM cles c JOIN joueurs j ON j.id = c.joueur WHERE c.empreinte = ?",
  ).bind(empreinte).first();
}

async function nouvelleCle(env, joueur, appareil) {
  const cle = aleatoire(32);
  await env.DB.prepare("INSERT INTO cles (empreinte, joueur, appareil, cree) VALUES (?, ?, ?, ?)")
    .bind(await sha256(cle), joueur, appareil, Date.now()).run();
  return cle;
}

function lireEtat(joueur) {
  try {
    return JSON.parse(joueur.etat || "{}");
  } catch {
    return {};
  }
}

async function donnerBadge(env, joueur, type, titre) {
  const id = aleatoire(8);
  const r = await env.DB.prepare(
    "INSERT OR IGNORE INTO badges (id, joueur, type, titre, date) VALUES (?, ?, ?, ?, ?)",
  ).bind(id, joueur, type, titre, Date.now()).run();
  return (r.meta?.changes ?? 0) > 0 ? { id, type, titre } : null;
}

// ====================================================================== anti-triche : graines

/*
 * Chaque appareil (chaque clé) reçoit une graine par jour, signée avec le secret SECRET_GRAINES
 * (wrangler secret put SECRET_GRAINES — jamais écrit dans le dépôt ni renvoyé tel quel).
 * Le jeu tire ses apparitions de (graine, compteur) ; le serveur refait le tirage pour vérifier.
 * Identifiant d'une graine : « AAAA-MM-JJ.poste » (poste = 12 premiers caractères de l'empreinte de la clé).
 */
const JOURS_AVANT = 1;
const JOURS_APRES = 6;
const JOUR_MS = 86_400_000;

function jourUTC(t) {
  return new Date(t).toISOString().slice(0, 10);
}

async function valeurGraine(env, joueurId, poste, jour) {
  return hmac(env.SECRET_GRAINES, `graine|${joueurId}|${poste}|${jour}`);
}

/** Les graines de cet appareil, d'hier à dans 6 jours (le jeu les garde pour jouer hors ligne). */
async function graines(env, joueur) {
  if (!env.SECRET_GRAINES || !joueur.empreinte_cle) return [];
  const poste = joueur.empreinte_cle.slice(0, 12);
  const out = [];
  for (let d = -JOURS_AVANT; d <= JOURS_APRES; d++) {
    const jour = jourUTC(Date.now() + d * JOUR_MS);
    out.push({ id: `${jour}.${poste}`, valeur: await valeurGraine(env, joueur.id, poste, jour) });
  }
  return out;
}

/**
 * Vérifie les NOUVELLES captures qui annoncent une graine : refait le tirage, compare, contrôle que
 * (graine, compteur) ne sert qu'une fois et que le stade est plausible. Renvoie Map(id → verdict).
 * Attirance (champ « attire ») : le tirage est refait avec la famille déclarée, acceptée seulement si
 * le joueur a déjà tapé la commande de cette famille (commandes « vus » connues ou envoyées).
 */
async function verifierCaptures(env, joueur, etat, envoyees, vusEnvoyes = []) {
  const verdicts = new Map();
  const vus = new Set([...(Array.isArray(etat.vus) ? etat.vus : []), ...(Array.isArray(vusEnvoyes) ? vusEnvoyes : [])]);
  const connues = new Set((etat.captures || []).map((c) => c.id));
  const postes = new Map();
  const maintenant = Date.now();
  for (const c of Array.isArray(envoyees) ? envoyees : []) {
    if (!c || typeof c.id !== "string" || connues.has(c.id) || verdicts.has(c.id)) continue;
    if (c.graine === undefined && c.n === undefined) continue;          // ancienne capture : non vérifiée
    const non = (raison) => verdicts.set(c.id, { verifie: false, raison });
    const m = typeof c.graine === "string" && c.graine.match(/^(\d{4}-\d{2}-\d{2})\.([0-9a-f]{12})$/);
    const n = c.n;
    if (!env.SECRET_GRAINES) { non("vérification indisponible"); continue; }
    if (!m || !Number.isInteger(n) || n < 0 || n >= MAX_APPARITIONS) { non("graine ou compteur invalide"); continue; }
    const [, jour, poste] = m;
    const debutJour = Date.parse(jour + "T00:00:00Z");
    if (!Number.isFinite(debutJour) || debutJour > maintenant + JOUR_MS) { non("graine d'un jour futur"); continue; }
    if (!postes.has(poste)) {
      const r = await env.DB.prepare("SELECT 1 AS ok FROM cles WHERE joueur = ? AND substr(empreinte, 1, 12) = ?")
        .bind(joueur.id, poste).first();
      postes.set(poste, !!r);
    }
    if (!postes.get(poste)) { non("graine d'un autre joueur"); continue; }
    const attire = attirancePlausible(c.attire, vus);
    if (attire === undefined) { non("attirance impossible"); continue; }
    const { champs } = tirer(await valeurGraine(env, joueur.id, poste, jour), n, c.espece === "Abyssor", attire);
    if (differences(c, champs).length) { non("ne correspond pas au tirage"); continue; }
    const i0 = TIRAGE.stades.indexOf(champs.stade);
    const voulu = TIRAGE.stades.includes(c.stade) ? c.stade : champs.stade;
    if (TIRAGE.stades.indexOf(voulu) < i0) { non("stade impossible"); continue; }
    // l'évolution : bornée par le temps écoulé depuis l'apparition (au plus tôt la veille du jour de la graine)
    const depuis = Math.min(maintenant, Math.max(Number(c.date) || 0, debutJour - JOUR_MS));
    const stade = stadePlausible(champs.stade, voulu, (maintenant - depuis) / 1000);
    const r = await env.DB.prepare(
      "INSERT OR IGNORE INTO apparitions (graine, n, joueur, capture, date) VALUES (?, ?, ?, ?, ?)",
    ).bind(c.graine, n, joueur.id, c.id, maintenant).run();
    if ((r.meta?.changes ?? 0) === 0) { non("graine déjà utilisée"); continue; }
    verdicts.set(c.id, { verifie: true, champs, stade, depuis });
  }
  return verdicts;
}

// ====================================================================== synchro

/**
 * Fusionne ce qu'envoie un appareil dans l'état commun de la créature.
 *  - compteurs (xp, stats…) : on AJOUTE ce que l'appareil a gagné depuis sa dernière synchro
 *  - ensembles (commandes goûtées, compétences) : union
 *  - collection : maximum par espèce · records : meilleur temps
 *  - nom, faim : la valeur la plus récente gagne · caractère, forme : la première gagne
 */
function fusionner(etat, envoi, appareil, verdicts = new Map()) {
  const e = {
    nom: "", nomDate: 0, trait: "", forme: null, xp: 0, total: 0, colles: 0, stats: {}, vus: [], skills: [],
    collection: {}, records: {}, faim: 80, faimDate: 0, appareils: {}, ...etat,
  };
  const entier = (x, max) => Math.max(0, Math.min(max, Math.floor(Number(x) || 0)));
  const d = envoi.deltas || {};
  e.xp += entier(d.xp, 20000);
  e.total += entier(d.total, 20000);
  e.colles += entier(d.colles, 1000);
  for (const s of STATS) e.stats[s] = (e.stats[s] || 0) + entier(d.stats?.[s], 5000);

  const union = (a, b, max) => {
    const s = new Set(Array.isArray(a) ? a : []);
    for (const x of Array.isArray(b) ? b : []) {
      if (typeof x === "string" && x.length > 0 && x.length <= 40 && s.size < max) s.add(x);
    }
    return [...s];
  };
  e.vus = union(e.vus, envoi.vus, 3000);
  e.skills = union(e.skills, envoi.skills, 300);

  for (const esp of ESPECES) {
    const n = entier(envoi.collection?.[esp], 9999);
    if (n > (e.collection[esp] || 0)) e.collection[esp] = n;
  }
  for (const [k, v] of Object.entries(envoi.records || {})) {
    const t = Number(v);
    if (/^[a-z0-9_-]{1,20}$/.test(k) && t > 0 && t < 3600 && (!e.records[k] || t < e.records[k])) {
      e.records[k] = Math.round(t * 10) / 10;
    }
  }
  // captures individuelles : union par identifiant, chaque champ vérifié
  const connues = new Set((e.captures || []).map((c) => c.id));
  e.captures = Array.isArray(e.captures) ? e.captures : [];
  for (const c of Array.isArray(envoi.captures) ? envoi.captures : []) {
    if (e.captures.length >= 3000) break;
    const ok = c && typeof c.id === "string" && /^[0-9a-f]{6,20}$/.test(c.id) && !connues.has(c.id)
      && (PAR_NOM[c.espece] || PAR_NOM_T[c.espece]) && MARQUES.has(c.marque) && HUMEURS.has(c.humeur);
    if (!ok) continue;
    const zone = typeof c.zone === "string" && /^[a-z/_]{0,60}$/.test(c.zone) ? c.zone : "";
    const v = verdicts.get(c.id);
    if (v?.verifie) {
      // tirage refait par le serveur : ce sont SES valeurs qui sont gardées
      const t = v.champs;
      e.captures.push({
        id: c.id, espece: t.espece, variante: t.variante, shiny: t.shiny, date: entier(c.date, 4e12), marque: t.marque,
        humeur: t.humeur, taille: t.taille, qualite: t.qualite, potentiel: t.potentiel, stats: t.stats, note: t.note,
        rarete: t.rarete, zone, stade: v.stade, stade0: t.stade, depuis: v.depuis, teinte: t.teinte ?? 0,
        graine: c.graine, n: c.n, verifie: true, ...(typeof c.attire === "string" && { attire: c.attire }),
      });
      connues.add(c.id);
      continue;
    }
    const st = {};
    for (const k of ["PV", "ATK", "DEF", "VIT", "INT"]) st[k] = entier(c.stats?.[k], 200);
    e.captures.push({
      id: c.id, espece: c.espece, shiny: c.shiny === true, date: entier(c.date, 4e12), marque: c.marque,
      humeur: c.humeur, taille: Math.max(0, Math.min(1000, Number(c.taille) || 0)), potentiel: entier(c.potentiel, 100),
      stats: st, zone,
      stade: STADES_B.includes(c.stade) ? c.stade : "enfant",
      teinte: Math.max(0, Math.min(1, Number(c.teinte) || 0)),
      verifie: false, ...(v?.raison && { raison: v.raison }),
    });
    connues.add(c.id);
  }
  // une bestiole déjà connue a pu grandir depuis : on garde le stade le plus avancé
  const parId = Object.fromEntries(e.captures.map((c) => [c.id, c]));
  for (const c of Array.isArray(envoi.captures) ? envoi.captures : []) {
    const ancienne = c && parId[c.id];
    if (!ancienne) continue;
    if (ancienne.verifie === true) {
      // bestiole vérifiée : elle ne grandit pas plus vite que le temps écoulé ne le permet
      const s = stadePlausible(ancienne.stade0, c.stade, (Date.now() - ancienne.depuis) / 1000);
      if (TIRAGE.stades.indexOf(s) > TIRAGE.stades.indexOf(ancienne.stade)) ancienne.stade = s;
    } else if (STADES_B.indexOf(c.stade) > STADES_B.indexOf(ancienne.stade || "enfant")) ancienne.stade = c.stade;
  }
  if (envoi.partage && typeof envoi.partage === "object" && (Number(envoi.partage.date) || 0) >= (e.partage?.date || 0)) {
    e.partage = { actif: envoi.partage.actif === true, date: Number(envoi.partage.date) || 0 };
  }
  const v = envoi.valeurs || {};
  if (e.shiny === undefined && typeof v.shiny === "boolean") e.shiny = v.shiny;
  // le nom : celui du compte reste, sauf renommage plus récent (un appareil fraîchement relié ne l'écrase pas)
  if (typeof v.nom === "string" && v.nom.trim() && (!e.nom || (Number(v.nomDate) || 0) > e.nomDate)) {
    e.nom = v.nom.trim().slice(0, 16);
    e.nomDate = Number(v.nomDate) || 0;
  }
  if (!e.trait && typeof v.trait === "string") e.trait = v.trait.slice(0, 20);
  if (!e.forme && STATS.includes(v.forme)) e.forme = v.forme;
  if ((Number(v.faimDate) || 0) > e.faimDate) {
    e.faim = Math.max(0, Math.min(100, Number(v.faim) || 0));
    e.faimDate = Number(v.faimDate);
  }
  if (APPAREILS.includes(appareil)) e.appareils[appareil] = Date.now();
  return e;
}

// ====================================================================== comptes : parties, jetons, code de secours

/*
 * Plusieurs parties par compte (table `parties`) : une partie = une créature. L'identifiant « 1 »
 * est la créature d'avant les parties multiples (les anciennes appli synchronisent sur /api/sync
 * sans identifiant = partie 1) ; les autres ont des identifiants au hasard, sur /api/sync/<id>.
 * La ligne `joueurs` garde une copie de la MEILLEURE partie (plus d'XP) : profil, classement, galerie.
 *
 * Connexion sans mot de passe (des enfants) : un jeton court TG-XXXX-XX (10 minutes, une fois) relie
 * un appareil ; `compte site` donne un lien à usage unique qui ouvre une session sur le site ;
 * un code de secours TG-XXXX-XXXX-XXXX, montré UNE fois, rend le compte si l'appareil est perdu
 * (seule son empreinte HMAC est stockée).
 */
const ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";
const RE_PARTIE = /^[A-Za-z0-9_-]{1,24}$/;
const SESSION_JOURS = 30;

function tirerCode(n) {
  const b = new Uint8Array(n);
  crypto.getRandomValues(b);
  return [...b].map((x) => ALPHABET[x % ALPHABET.length]).join("");
}

/** « tg-7kq2 m9 » → « 7KQ2M9 » (le préfixe TG- et les tirets sont facultatifs). */
function normaliserJeton(t, longueur) {
  const c = String(t || "").toUpperCase().replace(/[^A-Z0-9]/g, "");
  return c.length === longueur + 2 && c.startsWith("TG") ? c.slice(2) : c;
}

const jetonLisible = (c) => `TG-${c.slice(0, 4)}-${c.slice(4)}`;
const secoursLisible = (c) => `TG-${c.slice(0, 4)}-${c.slice(4, 8)}-${c.slice(8)}`;

async function nouveauJeton(env, joueurId) {
  const code = tirerCode(6);
  await env.DB.prepare("DELETE FROM codes WHERE expire < ?").bind(Date.now()).run();
  await env.DB.prepare("INSERT INTO codes (code, joueur, expire) VALUES (?, ?, ?)")
    .bind(code, joueurId, Date.now() + 10 * 60_000).run();
  return code;
}

/** Un nouveau code de secours (remplace l'ancien). Renvoyé UNE fois, jamais stocké en clair. */
async function nouveauSecours(env, joueurId) {
  const code = tirerCode(12);
  const empreinte = await hmac(await secretServeur(env), "secours|" + code);
  await env.DB.prepare("DELETE FROM secours WHERE joueur = ?").bind(joueurId).run();
  await env.DB.prepare("INSERT INTO secours (empreinte, joueur, cree) VALUES (?, ?, ?)").bind(empreinte, joueurId, Date.now()).run();
  return secoursLisible(code);
}

/** Migration douce : un compte sans ligne `parties` voit sa créature d'avant devenir la partie 1. */
async function migrerParties(env, joueur) {
  await env.DB.prepare(
    "INSERT OR IGNORE INTO parties (joueur, partie, etat, xp, niveau, cree, maj) SELECT id, '1', etat, xp, niveau, cree, maj "
    + "FROM joueurs WHERE id = ? AND etat <> '{}' AND NOT EXISTS (SELECT 1 FROM parties p WHERE p.joueur = joueurs.id)",
  ).bind(joueur.id).run();
}

async function synchroniser(env, joueur, b, partie) {
  await migrerParties(env, joueur);
  const appareil = APPAREILS.includes(b.appareil) ? b.appareil : "pc";
  const ligne = await env.DB.prepare("SELECT etat FROM parties WHERE joueur = ? AND partie = ?").bind(joueur.id, partie).first();
  const avant = ligne ? lireEtat(ligne) : {};
  const e = fusionner(avant, b, appareil, await verifierCaptures(env, joueur, avant, b.captures, b.vus));
  const maintenant = Date.now();
  await env.DB.prepare(
    "INSERT INTO parties (joueur, partie, etat, xp, niveau, cree, maj) VALUES (?, ?, ?, ?, ?, ?, ?) "
    + "ON CONFLICT (joueur, partie) DO UPDATE SET etat = excluded.etat, xp = excluded.xp, niveau = excluded.niveau, maj = excluded.maj",
  ).bind(joueur.id, partie, JSON.stringify(e), e.xp, niveauDe(e.xp), maintenant, maintenant).run();
  // la vitrine du joueur (profil, classement, galerie) montre sa meilleure créature
  const meilleure = await env.DB.prepare("SELECT etat, xp, niveau FROM parties WHERE joueur = ? ORDER BY xp DESC, maj DESC LIMIT 1")
    .bind(joueur.id).first();
  await env.DB.prepare("UPDATE joueurs SET etat = ?, xp = ?, niveau = ?, maj = ? WHERE id = ?")
    .bind(meilleure.etat, meilleure.xp, meilleure.niveau, maintenant, joueur.id).run();
  const nouveaux = [];
  if (Object.keys(e.appareils).length >= 2) {
    const bd = await donnerBadge(env, joueur.id, "multi", "Multi-plateforme : PC + téléphone");
    if (bd) nouveaux.push(bd);
  }
  return json({ etat: e, partie, badges: nouveaux, graines: await graines(env, joueur) });
}

async function listeParties(env, joueur) {
  await migrerParties(env, joueur);
  const r = await env.DB.prepare("SELECT partie, etat, xp, niveau, maj FROM parties WHERE joueur = ? ORDER BY cree").bind(joueur.id).all();
  return r.results.map((p) => {
    const e = lireEtat(p);
    return { partie: p.partie, nom: e.nom || "", forme: e.forme || null, niveau: p.niveau, xp: p.xp, shiny: !!e.shiny, maj: p.maj };
  });
}

/** Le joueur connecté au site (cookie de session), ou null. */
async function joueurSession(requete, env) {
  const m = String(requete.headers.get("cookie") || "").match(/(?:^|;\s*)tg_session=([0-9a-f]{64})/);
  if (!m) return null;
  return env.DB.prepare("SELECT j.* FROM sessions s JOIN joueurs j ON j.id = s.joueur WHERE s.empreinte = ? AND s.expire > ?")
    .bind(await sha256(m[1]), Date.now()).first();
}

// ====================================================================== API

async function api(requete, env, chemin) {
  const m = requete.method;
  const ip = requete.headers.get("cf-connecting-ip") || "local";

  if (chemin === "/api/inscription" && m === "POST") {
    if (!(await limite(env, "inscription:" + ip, 5))) return erreur("Trop d'inscriptions, réessaie dans une minute.", 429);
    const b = await corps(requete);
    const pseudo = String(b?.pseudo || "").trim();
    const appareil = APPAREILS.includes(b?.appareil) ? b.appareil : "pc";
    if (!/^[A-Za-z0-9_-]{3,20}$/.test(pseudo)) {
      return erreur("Le pseudo doit faire 3 à 20 caractères : lettres sans accent, chiffres, - ou _.");
    }
    const existe = await env.DB.prepare("SELECT 1 FROM joueurs WHERE pseudo = ?").bind(pseudo).first();
    if (existe) return erreur("Ce pseudo est déjà pris, choisis-en un autre.", 409);
    const id = crypto.randomUUID();
    const maintenant = Date.now();
    await env.DB.prepare("INSERT INTO joueurs (id, pseudo, etat, xp, niveau, cree, maj) VALUES (?, ?, '{}', 0, 1, ?, ?)")
      .bind(id, pseudo, maintenant, maintenant).run();
    const cle = await nouvelleCle(env, id, appareil);
    await donnerBadge(env, id, "recense", "Recensé");
    // code de secours : donné UNE seule fois, ici
    return json({ pseudo, cle, profil: "/joueur/" + pseudo, secours: await nouveauSecours(env, id) });
  }

  if (chemin === "/api/lier" && m === "POST") {
    if (!(await limite(env, "lier:" + ip, 10))) return erreur("Trop d'essais, réessaie dans une minute.", 429);
    const b = await corps(requete);
    const code = normaliserJeton(b?.code, 6);       // TG-7KQ2-M9, 7KQ2M9…
    const appareil = APPAREILS.includes(b?.appareil) ? b.appareil : "pc";
    const c = code.length === 6 ? await env.DB.prepare("SELECT * FROM codes WHERE code = ?").bind(code).first() : null;
    if (!c || c.expire < Date.now()) return erreur("Code invalide ou expiré (il dure 10 minutes).", 404);
    await env.DB.prepare("DELETE FROM codes WHERE code = ?").bind(code).run();
    const j = await env.DB.prepare("SELECT pseudo FROM joueurs WHERE id = ?").bind(c.joueur).first();
    const cle = await nouvelleCle(env, c.joueur, appareil);
    return json({ pseudo: j.pseudo, cle });
  }

  if (chemin === "/api/secours/recuperer" && m === "POST") {
    if (!(await limite(env, "secours:" + ip, 5))) return erreur("Trop d'essais, réessaie dans une minute.", 429);
    const b = await corps(requete);
    const code = normaliserJeton(b?.code, 12);
    const appareil = APPAREILS.includes(b?.appareil) ? b.appareil : "pc";
    const s = code.length === 12
      ? await env.DB.prepare("SELECT joueur FROM secours WHERE empreinte = ?").bind(await hmac(await secretServeur(env), "secours|" + code)).first()
      : null;
    if (!s) return erreur("Code de secours inconnu : vérifie chaque caractère.", 404);
    const j = await env.DB.prepare("SELECT pseudo FROM joueurs WHERE id = ?").bind(s.joueur).first();
    return json({ pseudo: j.pseudo, cle: await nouvelleCle(env, s.joueur, appareil) });
  }

  if (chemin === "/api/classement" && m === "GET") {
    const r = await env.DB.prepare("SELECT pseudo, etat, xp, niveau FROM joueurs ORDER BY xp DESC, cree ASC LIMIT 50").all();
    return json(r.results.map((j) => {
      const e = lireEtat(j);
      return { pseudo: j.pseudo, nom: e.nom || j.pseudo, niveau: j.niveau, xp: j.xp, forme: e.forme || null };
    }));
  }

  if (chemin.startsWith("/api/profil/") && m === "GET") {
    const p = await profilPublic(env, decodeURIComponent(chemin.slice(12)));
    return p ? json(p) : erreur("Joueur inconnu.", 404);
  }

  if (chemin.startsWith("/api/badge/") && m === "GET") {
    const b = await env.DB.prepare(
      "SELECT b.*, j.pseudo FROM badges b JOIN joueurs j ON j.id = b.joueur WHERE b.id = ?",
    ).bind(chemin.slice(11)).first();
    if (!b) return erreur("Badge inconnu.", 404);
    return json({ badge: b.titre, type: b.type, joueur: b.pseudo, date: new Date(b.date).toISOString(), verifie: true,
      emetteur: "Terminagotchi — recensement" });
  }

  // ------------------------------------------------ routes réservées aux joueurs connectés
  const joueur = await authentifier(requete, env);
  if (!joueur) return erreur("Clé manquante ou invalide.", 401);

  if (chemin === "/api/moi" && m === "GET") {
    return json({ pseudo: joueur.pseudo, etat: lireEtat(joueur), profil: "/joueur/" + joueur.pseudo });
  }

  if (chemin === "/api/code" && m === "POST") {
    const code = await nouveauJeton(env, joueur.id);
    return json({ code, jeton: jetonLisible(code), expire: 600 });
  }

  if (chemin === "/api/secours" && m === "POST") {
    if (!(await limite(env, "nouveau-secours:" + joueur.id, 5))) return erreur("Trop d'essais, réessaie dans une minute.", 429);
    return json({ secours: await nouveauSecours(env, joueur.id) });
  }

  if (chemin === "/api/lien-site" && m === "POST") {
    // lien à usage unique (10 minutes) qui ouvre une session sur le site ; seule son empreinte est gardée
    const t = aleatoire(16);
    await env.DB.prepare("DELETE FROM codes WHERE expire < ?").bind(Date.now()).run();
    await env.DB.prepare("INSERT INTO codes (code, joueur, expire) VALUES (?, ?, ?)")
      .bind("W" + (await sha256(t)), joueur.id, Date.now() + 10 * 60_000).run();
    return json({ lien: "/connexion?t=" + t, expire: 600 });
  }

  if (chemin === "/api/deconnexion" && m === "POST") {
    await env.DB.prepare("DELETE FROM cles WHERE empreinte = ?").bind(joueur.empreinte_cle).run();
    return json({ ok: true });
  }

  if (chemin === "/api/parties" && m === "GET") {
    return json({ parties: await listeParties(env, joueur) });
  }

  const ms = chemin.match(/^\/api\/sync(?:\/([^/]+))?$/);
  if (ms && m === "POST") {
    if (!(await limite(env, "sync:" + joueur.id, 30))) return erreur("Trop de synchros, doucement !", 429);
    const b = await corps(requete);
    if (!b) return erreur("Données illisibles.");
    // sans identifiant (anciennes versions de l'appli) : la partie 1
    const partie = ms[1] ? decodeURIComponent(ms[1]) : "1";
    if (!RE_PARTIE.test(partie)) return erreur("Identifiant de partie invalide.");
    const n = await env.DB.prepare("SELECT COUNT(*) AS n FROM parties WHERE joueur = ? AND partie <> ?").bind(joueur.id, partie).first();
    if (n.n >= 30) return erreur("Trop de parties sur ce compte.", 409);
    return synchroniser(env, joueur, b, partie);
  }

  if (chemin === "/api/drapeau" && m === "POST") {
    if (!(await limite(env, "drapeau:" + joueur.id, 20))) return erreur("Trop d'essais, respire un peu !", 429);
    const b = await corps(requete);
    const propose = String(b?.drapeau || "").trim();
    const secret = await secretServeur(env);
    for (const ep of EPREUVES) {
      if (propose === (await drapeauDe(secret, joueur.id, ep.n))) {
        const bd = await donnerBadge(env, joueur.id, "ctf_web_" + ep.n, "CTF web : " + ep.titre);
        const n = (await env.DB.prepare("SELECT COUNT(*) AS n FROM badges WHERE joueur = ? AND type LIKE 'ctf_web_%'")
          .bind(joueur.id).first()).n;
        let final = null;
        if (n >= EPREUVES.length) final = await donnerBadge(env, joueur.id, "ctf_web_tout", "Hacker du web (CTF complet)");
        return json({
          ok: true, epreuve: ep.n, titre: ep.titre, nouveau: !!bd, lecon: ep.lecon, score: n, sur: EPREUVES.length,
          badge: bd ? "/badge/" + bd.id : null, badgeFinal: final ? "/badge/" + final.id : null,
        });
      }
    }
    return json({ ok: false, message: "Ce n'est pas un de tes drapeaux. Vérifie chaque caractère !" });
  }

  return erreur("Route inconnue.", 404);
}

async function profilPublic(env, pseudo) {
  const j = await env.DB.prepare("SELECT * FROM joueurs WHERE pseudo = ?").bind(pseudo).first();
  if (!j) return null;
  const e = lireEtat(j);
  const b = await env.DB.prepare("SELECT id, type, titre, date FROM badges WHERE joueur = ? ORDER BY date").bind(j.id).all();
  const rang = (await env.DB.prepare("SELECT COUNT(*) AS n FROM joueurs WHERE xp > ?").bind(j.xp).first()).n + 1;
  return {
    pseudo: j.pseudo, nom: e.nom || j.pseudo, niveau: j.niveau, xp: j.xp, rang,
    stade: STADES[stadeDe(j.niveau)], forme: e.forme || null, trait: e.trait || "",
    stats: Object.fromEntries(STATS.map((s) => [s, e.stats?.[s] || 0])),
    commandes: e.total || 0, gouts: (e.vus || []).length, competences: e.skills || [],
    collection: e.collection || {}, records: e.records || {},
    appareils: Object.keys(e.appareils || {}), inscrit: new Date(j.cree).toISOString(),
    shiny: e.shiny === true, captures: (e.captures || []).length,
    capturesVerifiees: (e.captures || []).filter((c) => c.verifie === true).length, partage: e.partage?.actif === true,
    badges: b.results.map((x) => ({ ...x, lien: "/badge/" + x.id })),
  };
}

// ====================================================================== CTF en ligne
// Chaque joueur a SES drapeaux (calculés avec le secret du serveur) : impossible de les copier sur un ami.

const EPREUVES = [
  { n: 1, titre: "L'en-tête caché", lecon: "Une page web a un corps (ce qu'on voit) et des en-têtes (ce qu'on ne voit pas). curl -I montre les en-têtes." },
  { n: 2, titre: "Le fichier des robots", lecon: "robots.txt dit aux moteurs de recherche où ne pas aller… et donne souvent des idées aux curieux !" },
  { n: 3, titre: "Le guichet", lecon: "GET lit une page, POST envoie des données (comme un formulaire). curl -d fait un POST." },
  { n: 4, titre: "Le cookie de confiance", lecon: "Un cookie est stocké chez le visiteur : il peut le modifier ! Un serveur ne doit jamais lui faire confiance aveuglément." },
  { n: 5, titre: "La boîte JSON", lecon: "JSON est le format des API. On le lit avec des outils (python3 -m json.tool) plutôt qu'à l'œil." },
];

async function drapeauDe(secret, joueurId, n) {
  return "TG{" + (await hmac(secret, joueurId + ":ctf:" + n)).slice(0, 14) + "}";
}

async function ctf(requete, env, pseudo, n, suite, L) {
  const T = L.t.ctfTexte;
  const j = await env.DB.prepare("SELECT id, pseudo FROM joueurs WHERE pseudo = ?").bind(pseudo).first();
  if (!j) return texte(T.inconnu, 404);
  const secret = await secretServeur(env);
  const f = await drapeauDe(secret, j.id, n);
  const base = `/ctf/${j.pseudo}`;
  const titre = (k) => T.epreuve(k, L.t.ctf.epreuves[k - 1]) + "\n";
  switch (n) {
    case 1:
      return texte(titre(1) + T.e1 + T.valider, 200, { "x-drapeau": f });
    case 2:
      if (suite === "cachette") return texte(T.e2ok(f));
      return texte(titre(2) + T.e2 + T.valider);
    case 3:
      if (requete.method === "POST") {
        const t = await requete.text();
        const mot = new URLSearchParams(t).get("mot");
        if (mot && mot.toLowerCase() === "terminal") return texte(T.e3ok(f));
        return texte(T.e3non, 403);
      }
      return texte(titre(3) + T.e3 + T.valider);
    case 4: {
      const cookie = requete.headers.get("cookie") || "";
      if (/(^|;\s*)role=admin(\s*;|$)/.test(cookie)) return texte(T.e4ok(f));
      return texte(titre(4) + T.e4 + T.valider, 200, { "set-cookie": "role=visiteur; Path=" + base + "/4" });
    }
    case 5:
      return json({
        epreuve: T.epreuve(5, L.t.ctf.epreuves[4]),
        aide: T.e5,
        tiroirs: { haut: { vide: true }, milieu: { chaussettes: 12, boite: { couvercle: "rouge", contenu: { secret: f } } }, bas: [] },
      });
    default:
      return texte(T.cinq, 404);
  }
}

// ====================================================================== pages

const SPRITES = {
  oeuf: ["....wwww....", "...wwwwww...", "..wwwswwww..", "..wwwwwwsw..", ".wwswwwwwww.", ".wwwwwwwsww.", ".wwwwswwwww.", ".wwwwwwwwww.", "..wwwwwwww..", "...wwwwww..."],
  bebe: ["............", "....bbbb....", "..bbbbbbbb..", ".bbbbbbbbbb.", ".bbebbbbebb.", ".bbebbbbebb.", "bbkbbmmbbkbb", "bbbbbbbbbbbb", ".bbbbbbbbbb.", "..bb....bb.."],
  ado: ["..bbbbbbbb..", ".bbbbbbbbbb.", ".bbebbbbebb.", ".bbebbbbebb.", "bbkbbbbbbkbb", "bbbbbmmbbbbb", ".bbbbbbbbbb.", ".bbbbbbbbbb.", "..bbb..bbb..", "..bb....bb.."],
  adoTete: { Intelligence: ["......l.....", "......a....."], Force: [".h........h.", ".hh......hh."], "Agilité": ["..h......h..", "..hh....hh.."], Endurance: ["............", "...cccccc..."] },
  adoCorps: { Endurance: { 6: "??c?c??c?c??", 7: "???c?cc?c???" }, Intelligence: { 2: "??l?????l???" } },
  adulte: ["..bbbbbbbbbbbb..", "..bbbbbbbbbbbb..", ".bbbeebbbbeebbb.", ".bbbeebbbbeebbb.", ".bbkbbbbbbbbkbb.", "..bbbbbmmbbbbb..", "..bbbbbbbbbbbb..", "..bbbbbbbbbbbb..", "..bbbbbbbbbbbb..", "...bbbb..bbbb...", "...bbb....bbb..."],
  adulteTete: { Intelligence: [".......ll.......", ".......aa......."], Force: [".hh..........hh.", ".hhh........hhh."], "Agilité": ["...hh......hh...", "...hhh....hhh..."], Endurance: ["................", "....cccccccc...."] },
  adulteCorps: {
    Intelligence: { 2: "???l??llll??l???" }, Force: { 4: "h??????????????h", 5: "hh????????????hh" },
    "Agilité": { 4: "w??????????????w", 5: "ww????????????ww", 6: "ww????????????ww", 7: "w??????????????w" },
    Endurance: { 6: "???c?c?c?c?c????", 7: "????c?c?c?c?c???", 8: "???c?c?c?c?c????" },
  },
};

function x256(n) {
  const base = ["000000", "800000", "008000", "808000", "000080", "800080", "008080", "c0c0c0", "808080", "ff0000", "00ff00", "ffff00", "0000ff", "ff00ff", "00ffff", "ffffff"];
  if (n < 16) return "#" + base[n];
  if (n < 232) {
    const k = n - 16;
    const lv = [0, 95, 135, 175, 215, 255];
    return "#" + [lv[Math.floor(k / 36)], lv[Math.floor(k / 6) % 6], lv[k % 6]].map((v) => v.toString(16).padStart(2, "0")).join("");
  }
  const g = (8 + (n - 232) * 10).toString(16).padStart(2, "0");
  return "#" + g + g + g;
}

const SHINY_JOUEUR = { 39: 220, 78: 51, 203: 129, 221: 255, 141: 219 };

function svgCreature(niveau, forme, stats, taille = 8, shiny = false, etiquette = "créature") {
  const st = stadeDe(niveau);
  const dominant = Object.values(stats || {}).some((v) => v > 0)
    ? Object.entries(stats).sort((a, b) => b[1] - a[1])[0][0] : null;
  const f = forme || dominant || "Endurance";
  const over = (base, o) => base.map((r, i) => (o && o[i] ? [...o[i]].map((m, k) => (m === "?" ? r[k] : m)).join("") : r));
  const rows = st === 0 ? SPRITES.oeuf : st === 1 ? SPRITES.bebe
    : st === 2 ? [...SPRITES.adoTete[f], ...over(SPRITES.ado, SPRITES.adoCorps[f])]
      : [...SPRITES.adulteTete[f], ...over(SPRITES.adulte, SPRITES.adulteCorps[f])];
  let corps = st >= 2 && forme ? COULEUR[forme] : dominant ? COULEUR[dominant] : 141;
  if (shiny) corps = SHINY_JOUEUR[corps] ?? 219;
  const pal = { b: corps, e: 16, k: 211, m: 52, h: 180, w: 230, s: 180, c: 136, a: 250, l: 51 };
  const w = Math.max(...rows.map((r) => r.length));
  let rects = "";
  rows.forEach((r, y) => [...r].forEach((c, x) => {
    if (pal[c] !== undefined) rects += `<rect x="${x}" y="${y}" width="1.02" height="1.02" fill="${x256(pal[c])}"/>`;
  }));
  return `<svg class="creature" viewBox="0 0 ${w} ${rows.length}" width="${w * taille}" height="${rows.length * taille}" shape-rendering="crispEdges" role="img" aria-label="${echapper(etiquette)}">${rects}</svg>`;
}

// polices : la police à chasse fixe d'abord, puis une police de repli par écriture (CJK, devanagari, bengali, arabe, nastaliq)
const MONO = `ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono","DejaVu Sans Mono"`;
const POLICES = {
  zh: `${MONO},"Noto Sans Mono CJK SC","Noto Sans CJK SC","Source Han Sans SC","PingFang SC","Microsoft YaHei","WenQuanYi Micro Hei",sans-serif`,
  ja: `${MONO},"Noto Sans Mono CJK JP","Noto Sans CJK JP","Source Han Sans JP","Hiragino Sans","Hiragino Kaku Gothic ProN","Yu Gothic","Meiryo",sans-serif`,
  // hindi, bengali, arabe, ourdou : la police de l'écriture d'abord (en chasse fixe, ces écritures sont peu lisibles
  // et les espaces trop larges) ; le code et les commandes gardent la chasse fixe (règle code,pre)
  hi: `"Noto Sans Devanagari","Nirmala UI","Mangal","Lohit Devanagari","Kohinoor Devanagari",${MONO},sans-serif`,
  bn: `"Noto Sans Bengali","Nirmala UI","Vrinda","Lohit Bengali","Kohinoor Bangla",${MONO},sans-serif`,
  ar: `"Noto Sans Arabic","Noto Naskh Arabic","Segoe UI","Tahoma","Geeza Pro","DejaVu Sans",${MONO},sans-serif`,
  ur: `"Noto Nastaliq Urdu","Jameel Noori Nastaliq","Urdu Typesetting","Noto Naskh Arabic","Noto Sans Arabic","Segoe UI","Tahoma",${MONO},sans-serif`,
};

const CSS = `
:root{--fond:#14141f;--carte:#1e1e2e;--bord:#3a3a55;--texte:#e6e6e6;--doux:#9a9ab0;--vert:#5fd787;--rose:#ff87ff;--jaune:#ffd75f;--bleu:#87afff}
*{box-sizing:border-box}
body{margin:0;background:var(--fond);color:var(--texte);font:16px/1.5 ${MONO},monospace}
${Object.entries(POLICES).map(([l, p]) => `body:lang(${l}){font-family:${p}}`).join("\n")}
body:lang(ur){line-height:2.1}
body:lang(ar){line-height:1.8}
a{color:var(--bleu)}
header{border-bottom:1px solid var(--bord);background:#181826}
nav{max-width:960px;margin:0 auto;padding:12px 16px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}
nav .logo{color:var(--rose);font-weight:bold;text-decoration:none;font-size:18px}
nav a{text-decoration:none}
.langues{margin-inline-start:auto;display:flex;gap:6px;align-items:center}
.langues select{background:var(--carte);color:var(--texte);border:1px solid var(--bord);border-radius:10px;padding:4px 8px;font:inherit;font-size:14px;max-width:12em}
.langues button{background:#5f5fd7;color:#fff;border:0;border-radius:8px;padding:4px 10px;font:inherit}
main{max-width:960px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:28px;margin:8px 0 4px}h2{font-size:20px;margin:32px 0 12px;color:var(--jaune)}
.doux{color:var(--doux)}
.carte{background:var(--carte);border:1px solid var(--bord);border-radius:16px;padding:18px}
.grille{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
.hero{display:flex;gap:24px;align-items:center;flex-wrap:wrap}
.btn{display:inline-block;background:#5f5fd7;color:#fff;text-decoration:none;padding:10px 16px;border-radius:12px;margin-block:6px;margin-inline:0 8px}
.btn.vert{background:#2f7d50}
table{width:100%;border-collapse:collapse}
td,th{padding:8px 6px;border-bottom:1px solid var(--bord);text-align:start}
th{color:var(--doux);font-weight:normal;font-size:13px}
td.num{text-align:end}
.badge{display:inline-flex;gap:8px;align-items:center;background:#26263a;border:1px solid var(--bord);border-radius:999px;padding:6px 12px;margin-block:4px;margin-inline:0 6px;text-decoration:none;color:var(--texte)}
.badge.verifie{border-color:#2f7d50}
.barre{height:8px;background:#33334a;border-radius:4px;overflow:hidden}.barre>i{display:block;height:100%;background:var(--vert)}
code,pre{background:#11111b;border-radius:8px;font-family:${MONO},monospace;direction:ltr;unicode-bidi:isolate}
code{padding:2px 6px;line-height:1.5}
pre{padding:12px;overflow-x:auto;text-align:left}
.ltr{direction:ltr;unicode-bidi:isolate}
.creature{image-rendering:pixelated;max-width:100%;height:auto}
.rgb{background:linear-gradient(90deg,#ff5f5f,#ffd75f,#5fd787,#5fd7ff,#af87ff,#ff87ff,#ff5f5f);background-size:200% auto;
 -webkit-background-clip:text;background-clip:text;color:transparent;animation:rgb 4s linear infinite;font-weight:bold}
@keyframes rgb{to{background-position:200% center}}
@media (prefers-reduced-motion:reduce){.rgb{animation:none}}
.grille-b{display:grid;gap:10px;grid-template-columns:repeat(auto-fill,minmax(150px,1fr))}
.bestiole{background:var(--carte);border:1px solid var(--bord);border-radius:14px;padding:10px;text-align:center;text-decoration:none;color:var(--texte);display:block}
.bestiole:hover{border-color:#5f5fd7}
.bestiole svg{width:96px;height:96px}
.bestiole .num{color:var(--doux);font-size:12px}
.rar{font-size:12px;border-radius:999px;padding:1px 8px;border:1px solid currentColor;display:inline-block;margin-top:4px}
.capture{text-align:start}
.capture.shiny{border-color:#ffd75f;box-shadow:0 0 18px #ffd75f44}
.anime{direction:ltr;background-size:auto 100%;background-repeat:no-repeat;image-rendering:pixelated;animation:anime 1.2s steps(12) infinite}
@keyframes anime{from{background-position:0 0}to{background-position:calc(var(--px) * -12) 0}}
@media (prefers-reduced-motion:reduce){.anime{animation:none}}
.capture .marque{font-size:14px;margin:6px 0}
.filtres a{margin-inline-end:10px;font-size:14px}
.stats-b{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;text-align:center}
.stats-b div{background:#26263a;border-radius:8px;padding:6px 0}
@media (max-width:600px){h1{font-size:22px}td,th{padding:6px 3px;font-size:14px}.langues{margin-inline-start:0}}
`;

/** Le contexte de langue d'une requête : langue, textes, sens d'écriture, format des dates. */
function contexteLangue(requete, url) {
  const { lang, demandee } = choisirLangue(requete, url);
  return { lang, demandee, t: textes(lang), url, dir: RTL.has(lang) ? "rtl" : "ltr", locale: LOCALES[lang] };
}

/** Un nom venu des données ou d'un joueur (bestiole, pseudo…) : isolé pour ne pas se mélanger au sens d'écriture. */
const bdi = (s) => `<bdi>${echapper(s)}</bdi>`;
const numero = (e) => `<bdi>#${String(e.numero).padStart(3, "0")}</bdi>`;
const lib = (L, table, cle) => libelle(L.t[table], cle);

function selecteurLangue(L) {
  const caches = [...L.url.searchParams].filter(([k]) => k !== "lang")
    .map(([k, v]) => `<input type="hidden" name="${echapper(k)}" value="${echapper(v)}">`).join("");
  const options = LANGUES.map((l) => `<option value="${l}" lang="${l}" dir="${RTL.has(l) ? "rtl" : "ltr"}"${l === L.lang ? " selected" : ""}>${NOMS_LANGUES[l]}</option>`).join("");
  return `<form class="langues" method="get" action="${echapper(L.url.pathname)}">${caches}<span aria-hidden="true">🌐</span>`
    + `<select name="lang" aria-label="${echapper(L.t.nav.langue)}" onchange="this.form.submit()">${options}</select>`
    + `<noscript><button type="submit">OK</button></noscript></form>`;
}

function page(L, titre, contenu, description = L.t.description, statut = 200) {
  const n = L.t.nav;
  return new Response(`<!doctype html><html lang="${L.lang}" dir="${L.dir}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${echapper(titre)} · Terminagotchi</title><meta name="description" content="${echapper(description)}">
<link rel="icon" type="image/png" href="/favicon.png"><link rel="apple-touch-icon" href="/icone.png">
<style>${CSS}</style></head><body>
<header><nav><a class="logo" href="/"><img src="/icone.png" alt="" width="28" height="28" style="vertical-align:middle;image-rendering:pixelated;margin-inline-end:6px"><bdi>Terminagotchi</bdi></a><a href="/classement">${n.classement}</a><a href="/bestiaire">${n.bestiaire}</a><a href="/captures">${n.captures}</a><a href="/ctf">${n.ctf}</a><a href="/#telecharger">${n.telecharger}</a><a href="/compte">${n.compte}</a>${selecteurLangue(L)}</nav></header>
<main>${contenu}</main></body></html>`, {
    status: statut,
    headers: { "content-type": "text/html; charset=utf-8", "content-language": L.lang, vary: "Accept-Language, Cookie" },
  });
}

/** Titre d'un badge dans la langue choisie (le serveur l'enregistre en français). */
function titreBadge(L, b) {
  const T = L.t.badges;
  if (!T) return b.titre;
  if (b.type === "recense") return T.recense;
  if (b.type === "multi") return T.multi;
  if (b.type === "ctf_web_tout") return T.ctfTout;
  const m = /^ctf_web_(\d)$/.exec(b.type || "");
  const ep = m && L.t.ctf.epreuves[Number(m[1]) - 1];
  return ep ? T.ctf(ep) : b.titre;
}

function ligneClassement(L, j, i) {
  const forme = j.forme ? lib(L, "formes", j.forme) : "";
  return `<tr><td>${i + 1}</td><td><a href="/joueur/${encodeURIComponent(j.pseudo)}">${bdi(j.pseudo)}</a></td>
<td>${bdi(j.nom)} <span class="doux">${echapper(L.t.stades[stadeDe(j.niveau)])} ${echapper(forme)}</span></td>
<td class="num">${echapper(L.t.niv(j.niveau))}</td><td class="num"><bdi>${j.xp} XP</bdi></td></tr>`;
}

function tableClassement(L, lignes) {
  return `<table><tr><th>#</th><th>${L.t.thJoueur}</th><th>${L.t.thCreature}</th><th></th><th></th></tr>${lignes}</table>`;
}

async function pageAccueil(env, L) {
  const A = L.t.accueil;
  const top = await env.DB.prepare("SELECT pseudo, etat, xp, niveau FROM joueurs ORDER BY xp DESC, cree ASC LIMIT 10").all();
  const n = (await env.DB.prepare("SELECT COUNT(*) AS n FROM joueurs").first()).n;
  const lignes = top.results.map((j, i) => {
    const e = lireEtat(j);
    return ligneClassement(L, { pseudo: j.pseudo, nom: e.nom || j.pseudo, niveau: j.niveau, xp: j.xp, forme: e.forme }, i);
  }).join("");
  return page(L, A.titre, `
<section class="hero">
  <div><img src="/mascotte.png" alt="Terminagotchi" width="200" style="image-rendering:pixelated;max-width:45vw;height:auto"></div>
  <div style="flex:1;min-width:260px">
    <h1>${A.heroTitre}</h1>
    <p>${A.heroTexte}</p>
    <p class="doux">${A.recensees(n)}</p>
  </div>
</section>
<h2 id="telecharger">${A.telecharger}</h2>
<div class="grille">
  <div class="carte"><b>📱 Android</b><p class="doux">${A.android}</p>
    <a class="btn vert" href="${DEPOT}/releases/latest/download/terminagotchi.apk"><bdi>terminagotchi.apk</bdi></a></div>
  <div class="carte"><b>💻 ${A.pcTitre}</b><p class="doux">${A.pc}</p>
    <a class="btn" href="${DEPOT}/releases/latest/download/terminagotchi.pyz"><bdi>terminagotchi.pyz</bdi></a>
    <p class="doux">${A.puis} <code>python3 terminagotchi.pyz</code></p></div>
  <div class="carte"><b>🔗 ${A.partoutTitre}</b><p class="doux">${A.partout}</p></div>
</div>
<h2>${A.classement}</h2>
<div class="carte">${lignes ? tableClassement(L, lignes) : `<p class="doux">${A.personne}</p>`}
<p><a href="/classement">${A.voirTout}</a></p></div>
<h2>${A.preuvesTitre}</h2>
<div class="carte"><p>${A.preuves}</p>
<p class="doux">${A.preuvesDoux}</p></div>`);
}

async function pageClassement(env, L) {
  const C = L.t.classement;
  const r = await env.DB.prepare("SELECT pseudo, etat, xp, niveau FROM joueurs ORDER BY xp DESC, cree ASC LIMIT 100").all();
  const lignes = r.results.map((j, i) => {
    const e = lireEtat(j);
    return ligneClassement(L, { pseudo: j.pseudo, nom: e.nom || j.pseudo, niveau: j.niveau, xp: j.xp, forme: e.forme }, i);
  }).join("");
  return page(L, C.titre, `<h1>${C.h1}</h1><p class="doux">${C.sous}</p>
<div class="carte">${lignes ? tableClassement(L, lignes) : `<p class="doux">${C.personne}</p>`}</div>`);
}

async function pageJoueur(env, L, pseudo) {
  const J = L.t.joueur;
  const p = await profilPublic(env, pseudo);
  if (!p) return page(L, J.inconnuTitre, `<h1>${J.inconnu}</h1><p><a href="/classement">${J.retour}</a></p>`);
  const lo = 10 * (p.niveau - 1) ** 2;
  const hi = 10 * p.niveau ** 2;
  const pct = Math.round((100 * (p.xp - lo)) / Math.max(1, hi - lo));
  const stats = STATS.map((s) => `<div title="${echapper(lib(L, "stats", s))}">${echapper(L.t.court[s])} <b>${p.stats[s]}</b></div>`).join("");
  const badges = p.badges.map((b) => `<a class="badge verifie" href="${b.lien}">✔ ${echapper(titreBadge(L, b))}</a>`).join("")
    || `<span class="doux">${J.aucunBadge}</span>`;
  const coll = BESTIAIRE.especes.filter((e) => p.collection[e.nom]).map((e) =>
    `<a class="bestiole" href="${e.secrete ? `/captures?joueur=${encodeURIComponent(p.pseudo)}` : `/bestiaire/${e.id}`}"><div style="display:flex;justify-content:center">${visuel(L, e)}</div><div class="num">${numero(e)}</div>
     <div>${bdi(e.nom)} <bdi>×${p.collection[e.nom]}</bdi></div></a>`).join("");
  const collHtml = coll ? `<p class="doux">${J.nbEspeces(Object.keys(p.collection).filter((k) => p.collection[k]).length)}</p><div class="grille-b">${coll}</div>`
    : `<span class="doux">${J.aucuneBestiole}</span>`;
  const comp = p.competences.map((c) => `<span class="badge">◇ ${bdi(c)}</span>`).join("")
    || `<span class="doux">${J.aucune}</span>`;
  const forme = p.forme && p.niveau >= 5 ? lib(L, "formes", p.forme) : "";
  const appareils = p.appareils.map((a) => (a === "android" ? J.telephone : J.pc)).join(" + ") || "—";
  const stade = L.t.stades[stadeDe(p.niveau)];
  return page(L, p.pseudo, `
<section class="hero">
  <div class="carte">${svgCreature(p.niveau, p.forme, p.stats, 10, p.shiny, L.t.creature)}</div>
  <div style="flex:1;min-width:260px">
    <h1>${p.shiny ? `<span class="rgb">${bdi(p.nom)} ✨</span>` : bdi(p.nom)}</h1>
    <p class="doux">${J.ligneCreature(bdi(p.pseudo), echapper(stade), echapper(forme), bdi(p.trait || "?"))}</p>
    <p>${J.ligneNiveau(p.niveau, p.xp, p.rang)}</p>
    <div class="barre"><i style="width:${pct}%"></i></div>
    <div class="grille" style="grid-template-columns:repeat(4,1fr);margin-top:12px">${stats}</div>
    <p class="doux">${J.ligneActivite(p.commandes, p.gouts, appareils)}</p>
  </div>
</section>
<h2>${J.badges}</h2><div>${badges}</div>
<h2>${J.competences} <span class="doux" style="font-size:14px">${J.declarees}</span></h2><div>${comp}</div>
<h2>${J.collection}</h2>${collHtml}
${p.partage ? `<p><a href="/captures?joueur=${encodeURIComponent(p.pseudo)}">${J.voirCaptures}</a></p>` : ""}
<p class="doux" style="margin-top:32px">${J.inscrit(new Date(p.inscrit).toLocaleDateString(L.locale))} ·
<a href="/api/profil/${encodeURIComponent(p.pseudo)}">${J.json}</a></p>`, J.description(p.nom, p.pseudo, p.niveau));
}

async function pageBadge(env, L, id) {
  const B = L.t.badge;
  const b = await env.DB.prepare("SELECT b.*, j.pseudo FROM badges b JOIN joueurs j ON j.id = b.joueur WHERE b.id = ?").bind(id).first();
  if (!b) return page(L, B.inconnuTitre, `<h1>${B.inconnuTitre}</h1><p class="doux">${B.faux}</p>`);
  const date = new Date(b.date).toLocaleString(L.locale, { timeZone: "Europe/Paris" });
  const titre = titreBadge(L, b);
  return page(L, titre, `<div class="carte" style="max-width:560px;margin:24px auto;text-align:center">
<div style="font-size:56px">🏅</div><h1>${echapper(titre)}</h1>
<p>${B.delivre(`<a href="/joueur/${encodeURIComponent(b.pseudo)}"><b>${bdi(b.pseudo)}</b></a>`, `<bdi>${echapper(date)}</bdi>`)}</p>
<p style="color:var(--vert)">${B.verifie}</p>
<p class="doux">${B.identifiant} : <code>${echapper(b.id)}</code> · <a href="/api/badge/${echapper(b.id)}">${B.preuve}</a></p></div>`,
  B.description(titre, b.pseudo));
}

// ---------------------------------------------------------------- bestioles
/** Le dessin d'une bestiole : animé (stade, teinte shiny) si son espèce a un dessin complet, sinon le petit sprite. */
function visuel(L, e, c = {}, taille = 6, anim = "statique") {
  if (!ANIMEES.has(e.id)) return svgBestiole(e, c.shiny, taille);
  const stade = STADES_B.includes(c.stade) ? c.stade : "adulte";
  const px = 16 * taille;
  const filtre = c.shiny ? `filter:hue-rotate(${Math.round((c.teinte || 0.5) * 360)}deg);` : "";
  return `<div class="anime" role="img" aria-label="${echapper(e.nom)} (${echapper(lib(L, "stadesB", stade))})"
    style="width:${px}px;height:${px}px;background-image:url(/anim/${e.id}/${stade}/${anim}.webp);--px:${px}px;${filtre}"></div>`;
}

function svgBestiole(e, shiny = false, taille = 6) {
  const rows = shiny ? e.sprite_shiny : e.sprite;
  const pal = shiny ? e.palette_shiny : e.palette;
  const n = 16;
  const ox = (n - rows[0].length) / 2;
  const oy = (n - rows.length) / 2;
  let r = "";
  rows.forEach((l, y) => [...l].forEach((c, x) => {
    if (pal[c]) r += `<rect x="${x + ox}" y="${y + oy}" width="1.02" height="1.02" fill="${pal[c]}"/>`;
  }));
  return `<svg viewBox="0 0 ${n} ${n}" width="${n * taille}" height="${n * taille}" shape-rendering="crispEdges" role="img" aria-label="${echapper(e.nom)}">${r}</svg>`;
}

function etiquetteRarete(L, r) {
  return `<span class="rar" style="color:${COULEUR_RARETE[r]}">${echapper(lib(L, "raretes", r))}</span>`;
}

/** Le glossaire classique des 150 espèces (apparence normale, sans variantes ni shiny). */
function pageBestiaire(L, url) {
  const B = L.t.bestiaire;
  const famille = url.searchParams.get("famille") || "";
  const rarete = url.searchParams.get("rarete") || "";
  const liste = PUBLIQUES.filter((e) => (!famille || e.famille === famille) && (!rarete || e.rarete === rarete));
  const lien = (k, v, t) => {
    const p = new URLSearchParams({ famille, rarete, [k]: v });
    for (const [a, b] of [...p]) if (!b) p.delete(a);
    const actif = (k === "famille" ? famille : rarete) === v;
    return `<a href="/bestiaire${p.toString() ? "?" + p : ""}"${actif ? ' style="color:var(--jaune)"' : ""}>${t}</a>`;
  };
  const filtresF = [lien("famille", "", B.toutes), ...BESTIAIRE.familles.map((f) => lien("famille", f.nom, f.icone + " " + echapper(lib(L, "familles", f.nom))))].join(" ");
  const filtresR = [lien("rarete", "", B.toutes), ...BESTIAIRE.raretes.map((r) => lien("rarete", r, echapper(lib(L, "raretes", r))))].join(" ");
  const cartes = liste.map((e) => `<a class="bestiole" href="/bestiaire/${e.id}">${svgBestiole(e)}
    <div class="num">${numero(e)} · ${e.icone} ${echapper(lib(L, "familles", e.famille))}</div>
    <div><b>${bdi(e.nom)}</b></div>${etiquetteRarete(L, e.rarete)}</a>`).join("");
  return page(L, B.titre, `<h1>${B.h1}</h1>
<p>${B.intro}</p>
<div class="carte filtres"><div><span class="doux">${B.famille}</span> ${filtresF}</div><div style="margin-top:6px"><span class="doux">${B.rarete}</span> ${filtresR}</div></div>
<p class="doux">${B.nb(liste.length)}</p>
<div class="grille-b">${cartes}</div>`, B.description);
}

function pageEspece(L, id) {
  const E = L.t.espece;
  const e = PAR_ID[id];
  if (!e || e.secrete) return page(L, E.inconnueTitre, `<h1>${E.inconnue}</h1><p><a href="/bestiaire">${E.retour}</a></p>`, undefined, 404);
  const i = e.numero - 1;
  const prec = PUBLIQUES[(i + 149) % 150];
  const suiv = PUBLIQUES[(i + 1) % 150];
  const [fp, fs] = L.t.fleches;
  const stats = Object.entries(e.stats).map(([k, v]) => `<div><div class="doux" style="font-size:12px">${echapper(lib(L, "statsB", k))}</div><b>${v}</b></div>`).join("");
  const fam = lib(L, "familles", e.famille);
  const rar = lib(L, "raretes", e.rarete);
  return page(L, e.nom, `<p><a href="/bestiaire">${E.retourCourt}</a></p>
<section class="hero">
  <div class="carte">${svgBestiole(e, false, 14)}</div>
  <div style="flex:1;min-width:260px">
    <p class="doux">${numero(e)} · ${e.icone} ${echapper(E.famille(fam))}</p>
    <h1>${e.rarete === "légendaire" ? `<span class="rgb">${bdi(e.nom)}</span>` : bdi(e.nom)}</h1>
    ${etiquetteRarete(L, e.rarete)}
    <p lang="fr" dir="ltr">${echapper(e.description)}</p>
    <p class="doux" lang="fr" dir="ltr">${echapper(e.comportement)}</p>
    <div class="stats-b">${stats}</div>
  </div>
</section>
<h2>${E.fiche}</h2>
<div class="carte"><table>
<tr><td class="doux">${E.capacite}</td><td><bdi lang="fr">${echapper(e.capacite)}</bdi></td></tr>
<tr><td class="doux">${E.statFavorite}</td><td>${echapper(lib(L, "stats", e.stat))}</td></tr>
<tr><td class="doux">${E.taillePoids}</td><td><bdi>~${e.taille_cm} cm · ~${e.poids_ko} ${E.ko}</bdi></td></tr>
<tr><td class="doux">${E.habitat}</td><td>${echapper(lib(L, "habitats", e.habitat))} · <code>~/terrain_terminagotchi/${echapper(e.zone)}</code></td></tr>
<tr><td class="doux">${E.apparition}</td><td>${echapper(lib(L, "frequences", e.frequence))} · ${E.attiree(`<code>${echapper(e.attiree_par)}</code>`)}</td></tr>
</table></div>
<p style="margin-top:24px"><a href="/bestiaire/${prec.id}">${fp} ${numero(prec)} ${bdi(prec.nom)}</a>
 · <a href="/bestiaire/${suiv.id}">${numero(suiv)} ${bdi(suiv.nom)} ${fs}</a></p>`,
  E.description(e.nom, rar, fam));
}

/** La galerie des captures : seulement les joueurs qui ont dit oui (compte partage on). */
async function pageCaptures(env, L, url) {
  const K = L.t.captures;
  const filtre = url.searchParams.get("joueur") || "";
  const shinySeul = url.searchParams.get("shiny") === "1";
  const rarete = url.searchParams.get("rarete") || "";
  const r = await env.DB.prepare("SELECT pseudo, etat FROM joueurs ORDER BY maj DESC LIMIT 500").all();
  let caps = [];
  let joueurs = 0;
  for (const j of r.results) {
    const e = lireEtat(j);
    if (e.partage?.actif !== true) continue;
    if (filtre && j.pseudo.toLowerCase() !== filtre.toLowerCase()) continue;
    joueurs++;
    for (const c of e.captures || []) caps.push({ ...c, pseudo: j.pseudo });
  }
  // rareté : celle de l'individu (nouveau bestiaire), sinon celle de l'espèce (ancien)
  const rareteDe = (c) => c.rarete || PAR_NOM[c.espece]?.rarete;
  caps = caps.filter((c) => (PAR_NOM[c.espece] || PAR_NOM_T[c.espece]) && (!shinySeul || c.shiny) && (!rarete || rareteDe(c) === rarete));
  caps.sort((a, b) => (b.shiny - a.shiny) || ((b.verifie === true) - (a.verifie === true)) || (b.date - a.date));
  const total = caps.length;
  caps = caps.slice(0, 120);
  const cartes = caps.map((c) => {
    const date = new Date(c.date).toLocaleDateString(L.locale);
    // anti-triche : seules les bestioles dont le serveur a refait le tirage sont « vérifiées »
    const verif = `<div class="doux" style="font-size:12px">${c.verifie === true ? `<span style="color:var(--vert)">✔ ${K.verifiee}</span>` : K.nonVerifiee}</div>`;
    if (!PAR_NOM[c.espece] || c.verifie === true) {
      const t = PAR_NOM_T[c.espece];
      const stade = TIRAGE.stades.includes(c.stade) ? c.stade : "adulte";
      const vid = t.variantes.some((v) => v.id === c.variante) ? c.variante : "classique";
      const filtre = c.shiny ? ` style="filter:hue-rotate(${Math.round((c.teinte || 0.5) * 360)}deg)"` : "";
      const nom = c.shiny || ["légendaire", "mythique"].includes(c.rarete) ? `<span class="rgb">${bdi(t.nom)}${c.shiny ? " ✨" : ""}</span>` : `<b>${bdi(t.nom)}</b>`;
      return `<div class="bestiole capture${c.shiny ? " shiny" : ""}">
      <div style="text-align:center"><img src="/portraits/${t.id}/${vid}_${stade}.webp" alt="${echapper(t.nom)}" width="96" height="96" loading="lazy"${filtre}></div>
      <div>${nom}</div>
      ${COULEUR_RARETE[c.rarete] ? etiquetteRarete(L, c.rarete) : ""}
      <div class="marque" lang="fr" dir="ltr">« <span class="rgb">${echapper(c.marque)}</span> »</div>
      <div class="doux" style="font-size:13px">${echapper(K.humeur(lib(L, "humeurs", c.humeur)))} · <bdi>${c.taille} cm</bdi><br>${K.potentiel} <b style="color:var(--vert)"><bdi>${c.potentiel} %</bdi></b></div>
      ${verif}
      <div class="doux" style="font-size:12px;margin-top:6px">${K.par(`<a href="/joueur/${encodeURIComponent(c.pseudo)}">${bdi(c.pseudo)}</a>`, `<bdi>${echapper(date)}</bdi>`)}</div>
    </div>`;
    }
    const e = PAR_NOM[c.espece];
    const nom = c.shiny || e.rarete === "légendaire" ? `<span class="rgb">${bdi(e.nom)}${c.shiny ? " ✨" : ""}</span>` : `<b>${bdi(e.nom)}</b>`;
    return `<div class="bestiole capture${c.shiny ? " shiny" : ""}">
      <div style="text-align:center;display:flex;justify-content:center">${visuel(L, e, c)}</div>
      ${ANIMEES.has(e.id) ? `<div class="doux" style="font-size:12px">${echapper(lib(L, "stadesB", c.stade || "enfant"))}</div>` : ""}
      <div>${nom} <span class="num">${numero(e)}</span></div>
      ${etiquetteRarete(L, e.rarete)}
      <div class="marque" lang="fr" dir="ltr">« <span class="rgb">${echapper(c.marque)}</span> »</div>
      <div class="doux" style="font-size:13px">${echapper(K.humeur(lib(L, "humeurs", c.humeur)))} · <bdi>${c.taille} cm</bdi><br>${K.potentiel} <b style="color:var(--vert)"><bdi>${c.potentiel} %</bdi></b></div>
      ${verif}
      <div class="doux" style="font-size:12px;margin-top:6px">${K.par(`<a href="/joueur/${encodeURIComponent(c.pseudo)}">${bdi(c.pseudo)}</a>`, `<bdi>${echapper(date)}</bdi>`)}</div>
    </div>`;
  }).join("");
  const lienR = (v, t) => `<a href="/captures?${new URLSearchParams({ ...(filtre && { joueur: filtre }), ...(shinySeul && { shiny: "1" }), ...(v && { rarete: v }) })}">${t}</a>`;
  return page(L, K.titre, `<h1>${K.h1}</h1>
<p>${K.intro}
${filtre ? `${K.de(bdi(filtre))} <a href="/captures">${K.voirTous}</a>` : ""}</p>
<div class="carte filtres">${lienR("", K.toutes)} ${BESTIAIRE.raretes.map((x) => lienR(x, echapper(lib(L, "raretes", x)))).join(" ")}
 · <a href="/captures?${new URLSearchParams({ ...(filtre && { joueur: filtre }), ...(!shinySeul && { shiny: "1" }) })}">${shinySeul ? K.pasQueShiny : `<span class="rgb">${K.shinySeul}</span>`}</a></div>
<p class="doux">${K.resume(total, joueurs, total > 120)}</p>
${cartes ? `<div class="grille-b" style="grid-template-columns:repeat(auto-fill,minmax(220px,1fr))">${cartes}</div>`
    : `<div class="carte"><p class="doux">${K.aucune}</p></div>`}
<h2>${K.apparaitre}</h2>
<div class="carte"><p>${K.apparaitreTexte}</p>
<p class="doux">${K.declarees}</p></div>`,
  K.description);
}

function pageCtf(L, origine) {
  const C = L.t.ctf;
  const liste = EPREUVES.map((e) => `<li><b>${e.n}. ${echapper(C.epreuves[e.n - 1])}</b> — <code>curl ${origine}/ctf/${C.pseudo}/${e.n}</code></li>`).join("");
  return page(L, C.titre, `<h1>${C.h1}</h1>
<p>${C.intro(C.pseudo)}</p>
<div class="carte"><ol style="padding-inline-start:20px">${liste}</ol></div>
<h2>${C.valider}</h2>
<div class="carte"><p>${C.validerTexte}</p>
<p class="doux">${C.curl}</p></div>
<h2>${C.pourquoi}</h2>
<div class="carte"><p class="doux">${C.pourquoiTexte}</p></div>`);
}

// ====================================================================== aiguillage

// ====================================================================== pages du compte (session par cookie)

function cookieSession(valeur, maxAge) {
  return `tg_session=${valeur}; Path=/; Max-Age=${maxAge}; HttpOnly; Secure; SameSite=Lax`;
}

async function pageConnexion(env, L, url) {
  const t = String(url.searchParams.get("t") || "");
  const cle = /^[0-9a-f]{32}$/.test(t) ? "W" + (await sha256(t)) : "";
  const c = cle ? await env.DB.prepare("SELECT * FROM codes WHERE code = ?").bind(cle).first() : null;
  if (!c || c.expire < Date.now()) {
    return page(L, L.t.compte.titre, `<h1>${L.t.compte.titre}</h1><p>${L.t.compte.perime}</p>`, undefined, 404);
  }
  await env.DB.prepare("DELETE FROM codes WHERE code = ?").bind(cle).run();        // une seule fois
  const s = aleatoire(32);
  await env.DB.prepare("DELETE FROM sessions WHERE expire < ?").bind(Date.now()).run();
  await env.DB.prepare("INSERT INTO sessions (empreinte, joueur, expire) VALUES (?, ?, ?)")
    .bind(await sha256(s), c.joueur, Date.now() + SESSION_JOURS * 86_400_000).run();
  return new Response(null, { status: 303, headers: { location: "/compte", "set-cookie": cookieSession(s, SESSION_JOURS * 86400) } });
}

async function pageCompte(requete, env, L, chemin) {
  const C = L.t.compte;
  const j = await joueurSession(requete, env);
  if (!j) return page(L, C.titre, `<h1>${C.titre}</h1><p>${C.invite}</p>`);
  if (chemin === "/compte/sortir" && requete.method === "POST") {
    const m = String(requete.headers.get("cookie") || "").match(/tg_session=([0-9a-f]{64})/);
    if (m) await env.DB.prepare("DELETE FROM sessions WHERE empreinte = ?").bind(await sha256(m[1])).run();
    return new Response(null, { status: 303, headers: { location: "/", "set-cookie": cookieSession("", 0) } });
  }
  let jeton = "";
  if (chemin === "/compte/jeton" && requete.method === "POST") {
    jeton = `<div class="carte"><p>${C.jeton(jetonLisible(await nouveauJeton(env, j.id)))}</p><p class="doux">${C.jetonAide}</p></div>`;
  }
  const parties = (await listeParties(env, j)).map((p) => `<li>${bdi(p.nom || "?")} · ${echapper(lib(L, "formes", p.forme) || "")} niv. ${p.niveau}</li>`).join("");
  return page(L, C.titre, `<h1>${C.bonjour(bdi(j.pseudo))}</h1>
<p><a href="/joueur/${encodeURIComponent(j.pseudo)}">${C.profil}</a></p>
<h2>${C.lier}</h2>${jeton}<form method="post" action="/compte/jeton"><button>${C.jetonBouton}</button></form>
<h2>${C.parties}</h2>${parties ? `<ul>${parties}</ul>` : `<p class="doux">${C.aucunePartie}</p>`}
<form method="post" action="/compte/sortir"><button>${C.sortir}</button></form>`);
}

async function aiguiller(requete, env, url, chemin, L) {
  if (chemin === "/") return pageAccueil(env, L);
  if (chemin === "/connexion") return pageConnexion(env, L, url);
  if (chemin === "/compte" || chemin === "/compte/jeton" || chemin === "/compte/sortir") return pageCompte(requete, env, L, chemin);
  if (chemin === "/classement") return pageClassement(env, L);
  if (chemin === "/ctf") return pageCtf(L, url.origin);
  if (chemin === "/bestiaire") return pageBestiaire(L, url);
  if (chemin === "/captures") return pageCaptures(env, L, url);
  const mb = chemin.match(/^\/bestiaire\/([a-z0-9]+)$/);
  if (mb) return pageEspece(L, mb[1]);
  if (chemin === "/robots.txt") {
    return texte("User-agent: *\n# Les robots ne doivent pas fouiller les cachettes du CTF…\nDisallow: /ctf/*/2/cachette\n");
  }
  let m = chemin.match(/^\/joueur\/([^/]+)$/);
  if (m) return pageJoueur(env, L, decodeURIComponent(m[1]));
  m = chemin.match(/^\/badge\/([0-9a-f]{16})$/);
  if (m) return pageBadge(env, L, m[1]);
  m = chemin.match(/^\/ctf\/([^/]+)\/(\d)(?:\/(\w+))?$/);
  if (m) return ctf(requete, env, decodeURIComponent(m[1]), Number(m[2]), m[3], L);
  return page(L, L.t.introuvable.titre, `<h1>404</h1><p>${L.t.introuvable.texte}</p>`, undefined, 404);
}

export default {
  async fetch(requete, env) {
    const url = new URL(requete.url);
    const chemin = url.pathname.replace(/\/+$/, "") || "/";
    try {
      if (requete.method === "OPTIONS") {
        return new Response(null, { headers: { "access-control-allow-origin": "*", "access-control-allow-headers": "authorization, content-type", "access-control-allow-methods": "GET, POST" } });
      }
      // l'API reste en français : c'est l'appli et le jeu PC qui la lisent
      if (chemin.startsWith("/api/")) return await api(requete, env, chemin);
      const L = contexteLangue(requete, url);
      const r = await aiguiller(requete, env, url, chemin, L);
      // ?lang=xx : on retient le choix dans un cookie pour les pages suivantes
      if (L.demandee) r.headers.append("set-cookie", cookieLangue(L.demandee));
      if (!r.headers.has("vary")) r.headers.set("vary", "Accept-Language, Cookie");
      return r;
    } catch (e) {
      console.error(e);
      return chemin.startsWith("/api/") ? erreur("Erreur du serveur : " + e.message, 500) : texte("Erreur du serveur.\n", 500);
    }
  },
};

// pour les tests
export { fusionner, niveauDe, drapeauDe, EPREUVES, normaliserJeton };
