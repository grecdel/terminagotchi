/**
 * Terminagotchi — le site de recensement.
 * Un seul programme Cloudflare Worker : l'API (comptes, synchro, classement, CTF, badges)
 * et les pages du site. Données dans Cloudflare D1 (SQLite).
 */

import BESTIAIRE from "./bestiaire.js";
import { tirer, differences, stadePlausible, attirancePlausible, MAX_APPARITIONS, PAR_NOM_T, TIRAGE } from "./tirage.js";
import { LANGUES, NOMS_LANGUES, LOCALES, RTL, choisirLangue, cookieLangue, textes, libelle } from "./i18n.js";
import { confidentialiteFr, mentionsFr } from "./legal_fr.js";
import * as ENT from "./entrainement.js";
import { barreTerminal, planSite, CSS_TERMINAL } from "./terminal.js";

// ====================================================================== réglages à remplir

const DEPOT = "https://github.com/grecdel/terminagotchi";
const CONTACT = "contact@terminagotchi.com";
/** Liens de dons (page /soutenir). Une plateforme n'est affichée que si son lien est rempli. */
const DONS = { liberapay: "", kofi: "", github: "" };
/**
 * Éditeur du site (page /mentions-legales). Particulier non professionnel :
 *  - anonyme: true  → nom et adresse NON publiés (il faut les avoir donnés à l'hébergeur, Cloudflare) ;
 *  - anonyme: false → remplir nom (et adresse si on veut la publier).
 * directeur : directeur de la publication (vide = l'éditeur lui-même).
 */
const EDITEUR = { anonyme: true, nom: "", adresse: "", directeur: "" };
/** Licence du code source (ex. « GPL-3.0-or-later », « MIT ») : vide tant que le dépôt n'a pas de fichier LICENSE. */
const LICENCE = "";
/**
 * Durées de conservation, annoncées sur /confidentialite ET appliquées par la purge quotidienne (scheduled) :
 * compte effacé après `inactifMois` sans synchronisation ; adresses IP et compteurs anti-abus après `ipHeures`.
 */
const CONSERVATION = { inactifMois: 36, ipHeures: 24, sessionJours: 30 };
const STATS = ["Intelligence", "Agilité", "Force", "Endurance"];
const COULEUR = { Intelligence: 39, "Agilité": 78, Force: 203, Endurance: 221 };
const STADES = ["Œuf", "Bébé", "Ado", "Adulte"];
const PAR_NOM = Object.fromEntries(BESTIAIRE.especes.map((e) => [e.nom, e]));
const PAR_ID = Object.fromEntries(BESTIAIRE.especes.map((e) => [e.id, e]));
// anciennes espèces (bestiaire v1) : leur nom mène à la nouvelle espèce de même numéro (vieilles captures, collections)
const ANCIENS = Object.fromEntries(Object.entries(BESTIAIRE.anciens || {}).map(([nom, id]) => [nom, PAR_ID[id]]).filter(([, e]) => e));
/** L'espèce d'un nom envoyé par le jeu : nom du nouveau bestiaire d'abord, sinon ancien nom. */
const especeDe = (nom) => PAR_NOM[nom] || ANCIENS[nom] || null;
const ESPECES = [...new Set([...Object.keys(PAR_NOM), ...Object.keys(ANCIENS)])];
const PUBLIQUES = BESTIAIRE.especes.filter((e) => !e.secrete).sort((a, b) => a.numero - b.numero);
// espèces qui ont un dessin complet animé (bandes d'images dans public/anim/<id>/<stade>/<animation>.webp)
const ANIMEES = new Set(["abyssor"]);
const STADES_B = ["enfant", "ado", "adulte", "finale"];
const MARQUES = new Set(BESTIAIRE.marques);
const HUMEURS = new Set(BESTIAIRE.humeurs);
const COULEUR_RARETE = { commune: "#b9c7be", "peu commune": "#5cff95", rare: "#5cb8ff", "épique": "#c58cff", "légendaire": "#ffb84d",
  mythique: "#ff7aa8" };
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

// ====================================================================== salle d'entraînement

/*
 * Le jeu envoie (etat.entrainement côté jeu, voir pc/tg/entrainement.py) :
 *   deltas  : les compteurs gagnés depuis la dernière synchro, par famille (n, bronze, argent, or, diamant) ;
 *   runs    : les exercices réussis à vérifier { id, type, g (graine), n (compteur), t (secondes), d (date), e (empreinte) } ;
 *   records : son meilleur temps par exercice { t, g, n, d }.
 * Un exercice est vérifié si la graine est bien celle d'un appareil du joueur, si (graine, n) n'a jamais servi, si
 * l'enfant avait déjà tapé ses commandes, si l'empreinte est celle du tirage refait ici, si le temps est plausible
 * (ENT.tempsMinimum, par type), si sa date tombe le jour de sa graine, s'il ne chevauche aucun autre exercice
 * vérifié et s'il en reste moins de ENT.MAX_VERIFIES_JOUR ce jour-là. La réponse d'un exercice se calcule depuis
 * la graine (il le faut pour jouer hors ligne) : ces contrôles jugent donc le rythme, pas la réponse.
 * Les deltas ne servent qu'au jeu (sa progression locale) : grades, titres, badges du profil, records publics et
 * Star de la semaine ne comptent que les exercices vérifiés (verifiesDe, recomptés ici).
 * Un record est « vérifié » quand il correspond à un exercice vérifié ; sinon il est gardé, marqué non vérifié.
 */
async function posteDuJoueur(env, joueur, poste, cache) {
  if (!cache.has(poste)) {
    const r = await env.DB.prepare("SELECT 1 AS ok FROM cles WHERE joueur = ? AND substr(empreinte, 1, 12) = ?").bind(joueur.id, poste).first();
    cache.set(poste, !!r);
  }
  return cache.get(poste);
}

async function synchroEntrainement(env, joueur, partie, avant, envoi, vus) {
  const e = { ...ENT.etatVide(), ...(avant && typeof avant === "object" ? avant : {}) };
  e.familles = { ...(e.familles || {}) };
  e.records = { ...(e.records || {}) };
  const verdicts = {};
  for (const f of ENT.FAMILLES) ENT.fam(e, f);
  if (!envoi || typeof envoi !== "object") return { etat: e, verdicts };
  const entier = (x, max) => Math.max(0, Math.min(max, Math.floor(Number(x) || 0)));
  for (const f of ENT.FAMILLES) {
    const x = ENT.fam(e, f);
    for (const k of ["n", ...ENT.MEDAILLES]) x[k] += entier(envoi.deltas?.[f]?.[k], 500);
  }
  const garder = (typ, cand) => {
    const a = e.records[typ];
    if (!a || (cand.v && !a.v) || (cand.v === !!a.v && cand.t < a.t)) e.records[typ] = cand;
  };
  const vusSet = new Set(vus);
  const maintenant = Date.now();
  const postes = new Map();
  for (const run of (Array.isArray(envoi.runs) ? envoi.runs : []).slice(-200)) {
    if (!run || typeof run.id !== "string" || !/^[0-9a-f]{6,24}$/.test(run.id) || !Object.hasOwn(ENT.TYPES, run.type)) continue;
    const t = Math.round(Number(run.t) * 10) / 10;
    if (!(t > 0 && t < 3600)) continue;
    const deja = await env.DB.prepare("SELECT verifie FROM exercices WHERE id = ?").bind(run.id).first();
    if (deja) { verdicts[run.id] = deja.verifie === 1; continue; }
    const m = typeof run.g === "string" && run.g.match(/^(\d{4}-\d{2}-\d{2})\.([0-9a-f]{12})$/);
    let raison = null;
    if (!run.g) raison = "sans graine";
    else if (!env.SECRET_GRAINES) raison = "vérification indisponible";
    else if (!m || !Number.isInteger(run.n) || run.n < 0 || run.n >= ENT.MAX_PAR_GRAINE) raison = "graine ou compteur invalide";
    else if (!(Date.parse(m[1] + "T00:00:00Z") <= maintenant + JOUR_MS)) raison = "graine d'un jour futur";
    else if (!(await posteDuJoueur(env, joueur, m[2], postes))) raison = "graine d'un autre joueur";
    else if (!ENT.commandesConnues(run.type, vusSet)) raison = "commandes pas encore tapées";
    else if (ENT.empreinte(run.type, ENT.generer(run.type, await valeurGraine(env, joueur.id, m[2], m[1]), run.n)) !== run.e) raison = "ne correspond pas au tirage";
    else if (t < ENT.tempsMinimum(run.type)) raison = "temps impossible";
    const date = Math.min(maintenant, Math.max(Number(run.d) || 0, maintenant - 8 * JOUR_MS));
    if (!raison) {
      // la date annoncée doit tomber le jour de la graine (fuseaux horaires compris), jamais dans le futur
      const jourG = Date.parse(m[1] + "T00:00:00Z");
      const d = Number(run.d);
      if (!(d >= jourG - 14 * 3_600_000 && d <= jourG + JOUR_MS + 14 * 3_600_000 && d <= maintenant + 60_000)) raison = "date hors du jour de la graine";
    }
    if (!raison) {
      // un enfant fait un exercice à la fois : pas de chevauchement avec un autre exercice vérifié (0,5 s de marge)
      const chev = await env.DB.prepare("SELECT 1 AS ok FROM exercices WHERE joueur = ? AND verifie = 1 AND date > ? AND date - temps * 1000 < ?")
        .bind(joueur.id, date - t * 1000 + 500, date - 500).first();
      if (chev) raison = "en même temps qu'un autre exercice";
    }
    if (!raison) {
      const j0 = Math.floor(date / JOUR_MS) * JOUR_MS;
      const nb = await env.DB.prepare("SELECT COUNT(*) AS c FROM exercices WHERE joueur = ? AND verifie = 1 AND date >= ? AND date < ?")
        .bind(joueur.id, j0, j0 + JOUR_MS).first();
      if ((nb?.c ?? 0) >= ENT.MAX_VERIFIES_JOUR) raison = "trop d'exercices ce jour-là";
    }
    const ligne = [run.id, joueur.id, partie, ENT.TYPES[run.type][0], run.type, t, ENT.medaille(run.type, t), date, ENT.semaine(date)];
    const sql = "INSERT OR IGNORE INTO exercices (id, joueur, partie, famille, type, temps, medaille, date, semaine, graine, n, verifie) "
      + "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)";
    if (!raison) {
      const r = await env.DB.prepare(sql).bind(...ligne, run.g, run.n, 1).run();
      if ((r.meta?.changes ?? 0) === 0) raison = "graine déjà utilisée";
    }
    if (raison) await env.DB.prepare(sql).bind(...ligne, null, null, 0).run();
    verdicts[run.id] = !raison;
    if (!raison) garder(run.type, { t, v: true, d: date });
  }
  for (const [typ, r] of Object.entries(envoi.records && typeof envoi.records === "object" ? envoi.records : {})) {
    if (!Object.hasOwn(ENT.TYPES, typ) || !r || typeof r !== "object") continue;
    const t = Math.round(Number(r.t) * 10) / 10;
    if (!(t >= 1 && t < 3600)) continue;
    const v = typeof r.g === "string" && r.g && Number.isInteger(r.n)
      ? !!(await env.DB.prepare("SELECT 1 AS ok FROM exercices WHERE joueur = ? AND graine = ? AND n = ? AND verifie = 1 AND ABS(temps - ?) < 0.05")
        .bind(joueur.id, r.g, r.n, t).first())
      : false;
    garder(typ, { t, v, d: entier(r.d, 4e12) });
  }
  // les grades, titres et badges publics ne comptent QUE les exercices vérifiés (recomptés ici, jamais envoyés par le
  // jeu) ; e.familles garde les compteurs du jeu (sa progression locale, sur tous ses appareils), « non vérifiés »
  e.verifies = await verifiesDe(env, joueur.id, partie);
  return { etat: e, verdicts };
}

/** Les compteurs (réussites, médailles) des seuls exercices vérifiés d'une partie, par famille. */
async function verifiesDe(env, joueurId, partie) {
  const v = Object.fromEntries(ENT.FAMILLES.map((f) => [f, Object.fromEntries(["n", ...ENT.MEDAILLES].map((k) => [k, 0]))]));
  const r = await env.DB.prepare("SELECT famille, medaille, COUNT(*) AS c FROM exercices WHERE joueur = ? AND partie = ? AND verifie = 1 "
    + "GROUP BY famille, medaille").bind(joueurId, partie).all();
  for (const x of r.results) {
    if (!v[x.famille]) continue;
    v[x.famille].n += x.c;
    if (Object.hasOwn(v[x.famille], x.medaille)) v[x.famille][x.medaille] += x.c;
  }
  return v;
}

/** Donne la « Star de la semaine » de la semaine passée dans chaque famille (une fois par semaine). Renvoie cette semaine-là. */
async function semainesAttribuees(env, maintenant = Date.now()) {
  const s = ENT.semainePrecedente(maintenant);
  const fait = await env.DB.prepare("SELECT valeur FROM config WHERE cle = 'hebdo'").first();
  if (fait?.valeur === s) return s;
  for (const f of ENT.FAMILLES) {
    await env.DB.prepare(
      "INSERT OR IGNORE INTO titres_hebdo (semaine, famille, joueur, partie, n) SELECT ?, famille, joueur, partie, COUNT(*) AS c "
      + "FROM exercices WHERE semaine = ? AND famille = ? AND verifie = 1 GROUP BY joueur, partie ORDER BY c DESC, SUM(temps) ASC, MIN(date) ASC LIMIT 1",
    ).bind(s, s, f).run();
  }
  await env.DB.prepare("INSERT INTO config (cle, valeur) VALUES ('hebdo', ?) ON CONFLICT (cle) DO UPDATE SET valeur = excluded.valeur").bind(s).run();
  return s;
}

/** Les Stars de la semaine d'un joueur : celles qu'il porte cette semaine (par partie) et combien de fois en tout. */
async function starsDe(env, joueurId, partie = null) {
  const s = await semainesAttribuees(env);
  const ici = partie === null ? "" : " AND partie = ?";
  const lier = (q, ...p) => env.DB.prepare(q).bind(...p, ...(partie === null ? [] : [partie]));
  const maintenant = await lier("SELECT famille FROM titres_hebdo WHERE semaine = ? AND joueur = ?" + ici, s, joueurId).all();
  const compte = await lier("SELECT famille, COUNT(*) AS n FROM titres_hebdo WHERE joueur = ?" + ici + " GROUP BY famille", joueurId).all();
  return { semaine: s, familles: maintenant.results.map((x) => x.famille), compte: Object.fromEntries(compte.results.map((x) => [x.famille, x.n])) };
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
      && (especeDe(c.espece) || PAR_NOM_T[c.espece]) && MARQUES.has(c.marque) && HUMEURS.has(c.humeur);
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
      stade: STADES_B.includes(c.stade) || TIRAGE.stades.includes(c.stade) ? c.stade : "enfant",
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
    } else if (STADES_B.includes(c.stade) && STADES_B.indexOf(c.stade) > STADES_B.indexOf(ancienne.stade || "enfant")) ancienne.stade = c.stade;
    else if (TIRAGE.stades.indexOf(c.stade) > TIRAGE.stades.indexOf(ancienne.stade)) ancienne.stade = c.stade;
  }
  if (envoi.partage && typeof envoi.partage === "object" && (Number(envoi.partage.date) || 0) >= (e.partage?.date || 0)) {
    e.partage = { actif: envoi.partage.actif === true, date: Number(envoi.partage.date) || 0 };
  }
  const v = envoi.valeurs || {};
  if (e.shiny === undefined && typeof v.shiny === "boolean") e.shiny = v.shiny;
  // le nom : celui du compte reste, sauf renommage plus récent (un appareil fraîchement relié ne l'écrase pas)
  if (typeof v.nom === "string" && v.nom.trim() && (!e.nom || (Number(v.nomDate) || 0) > e.nomDate)) {
    // sans caractères de contrôle ni de mise en forme (ESC, NUL, RLO…) : le nom est montré à d'autres joueurs
    e.nom = v.nom.replace(/[\p{Cc}\p{Cf}]/gu, "").trim().slice(0, 16) || e.nom || "?";
    e.nomDate = Number(v.nomDate) || 0;
  }
  if (!e.trait && typeof v.trait === "string") e.trait = v.trait.slice(0, 20);
  if (!e.forme && STATS.includes(v.forme)) e.forme = v.forme;
  // le thème (apparence) : le plus récent gagne, un nom court en minuscules seulement
  if (typeof v.theme === "string" && /^[a-z]{2,12}$/.test(v.theme) && (Number(v.themeDate) || 0) > (e.themeDate || 0)) {
    e.theme = v.theme;
    e.themeDate = Number(v.themeDate) || 0;
  }
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
const SESSION_JOURS = CONSERVATION.sessionJours;

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
  const ent = await synchroEntrainement(env, joueur, partie, avant.entrainement, b.entrainement, e.vus);
  e.entrainement = ent.etat;
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
  const st = await starsDe(env, joueur.id, partie);
  return json({ etat: e, partie, badges: nouveaux, graines: await graines(env, joueur),
    entrainement: { hebdo: { semaine: st.semaine, familles: st.familles }, compte: st.compte, verdicts: ent.verdicts } });
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

  // le plan du site pour le mini-terminal des pages (ls, cd, Tab…) : ne change qu'avec une nouvelle version
  if (chemin === "/api/plan" && m === "GET") {
    return json(planSite(new URL(requete.url).searchParams.get("lang")), 200, { "cache-control": "public, max-age=3600" });
  }

  if (chemin === "/api/records" && m === "GET") {
    return json(await donneesRecords(env));
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

  if (chemin === "/api/compte" && m === "DELETE") {
    // suppression définitive du compte et de TOUTES ses données ; le pseudo doit être recopié (pas de suppression par erreur)
    const b = await corps(requete);
    if (String(b?.confirmer || "").trim().toLowerCase() !== joueur.pseudo.toLowerCase()) {
      return erreur("Pour supprimer le compte, recopie le pseudo dans « confirmer ».", 400);
    }
    await supprimerCompte(env, joueur.id);
    return json({ ok: true, supprime: joueur.pseudo });
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

// ====================================================================== suppression et durées de conservation

/** Efface un compte et tout ce qui s'y rattache (toutes les tables qui ont une colonne « joueur »). */
async function supprimerCompte(env, id) {
  for (const table of ["cles", "codes", "badges", "apparitions", "parties", "secours", "sessions", "exercices", "titres_hebdo"]) {
    await env.DB.prepare(`DELETE FROM ${table} WHERE joueur = ?`).bind(id).run();
  }
  // compteurs anti-abus par compte (« sync:<id> », « drapeau:<id> »…)
  await env.DB.prepare("DELETE FROM essais WHERE sujet LIKE ?").bind("%:" + id).run();
  await env.DB.prepare("DELETE FROM joueurs WHERE id = ?").bind(id).run();
}

/**
 * Applique les durées annoncées sur /confidentialite (lancée chaque jour par le déclencheur « crons » de wrangler.toml) :
 * comptes sans synchronisation depuis CONSERVATION.inactifMois, compteurs anti-abus (adresses IP) de plus de
 * CONSERVATION.ipHeures, jetons et sessions expirés. Renvoie le nombre de comptes effacés.
 */
async function purger(env, maintenant = Date.now()) {
  await env.DB.prepare("DELETE FROM essais WHERE minute < ?").bind(Math.floor(maintenant / 60000) - CONSERVATION.ipHeures * 60).run();
  await env.DB.prepare("DELETE FROM codes WHERE expire < ?").bind(maintenant).run();
  await env.DB.prepare("DELETE FROM sessions WHERE expire < ?").bind(maintenant).run();
  const limite = maintenant - CONSERVATION.inactifMois * 30.44 * 86_400_000;
  const vieux = await env.DB.prepare("SELECT id FROM joueurs WHERE maj < ? LIMIT 200").bind(Math.round(limite)).all();
  for (const j of vieux.results) await supprimerCompte(env, j.id);
  return vieux.results.length;
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
    entrainement: await entrainementPublic(env, j.id, e.entrainement),
  };
}

/** Badges, titre, records et Stars de la semaine d'un joueur (sa meilleure partie, ses Stars sur toutes ses parties). */
async function entrainementPublic(env, joueurId, ent) {
  const brut = { ...ENT.etatVide(), ...(ent && typeof ent === "object" ? ent : {}) };
  const st = await starsDe(env, joueurId);
  // grades et titres : seulement les exercices vérifiés (e.verifies, recomptés par le serveur) et les records vérifiés
  const recordsTous = Object.entries(brut.records || {}).filter(([typ, r]) => Object.hasOwn(ENT.TYPES, typ) && r && Number(r.t) > 0);
  const e = { familles: { ...(brut.verifies && typeof brut.verifies === "object" ? brut.verifies : {}) },
    records: Object.fromEntries(recordsTous.filter(([, r]) => r.v === true)) };
  const local = { familles: { ...(brut.familles || {}) } };
  const familles = Object.fromEntries(ENT.FAMILLES.map((f) => {
    const x = ENT.fam(e, f);
    const k = ENT.echelon(e, f);
    return [f, { n: x.n, or: x.or + x.diamant, echelon: k >= 0 ? ENT.ECHELONS[k] : null, etoiles: ENT.etoilesDe(x.n, k),
      nonVerifies: Math.max(0, ENT.fam(local, f).n - x.n) }];
  }));
  const records = Object.fromEntries(recordsTous.map(([typ, r]) => [typ, { t: Number(r.t), v: r.v === true }]));
  return { familles, titre: ENT.titres(e, st.familles)[0] || null, records, stars: st.compte };
}

/** Les records vérifiés (10 meilleurs joueurs par exercice), les Stars de la semaine, la tête de la semaine en cours. */
async function donneesRecords(env) {
  const semaine = await semainesAttribuees(env);
  const cette = ENT.semaine();
  const tops = await env.DB.prepare(
    "SELECT e.type, j.pseudo, MIN(e.temps) AS t FROM exercices e JOIN joueurs j ON j.id = e.joueur WHERE e.verifie = 1 "
    + "GROUP BY e.type, e.joueur ORDER BY e.type, t ASC, MIN(e.date) ASC",
  ).all();
  const records = {};
  for (const r of tops.results) {
    const l = (records[r.type] ??= []);
    if (l.length < 10) l.push({ pseudo: r.pseudo, t: r.t, medaille: ENT.medaille(r.type, r.t) });
  }
  const stars = (await env.DB.prepare(
    "SELECT h.famille, h.n, j.pseudo FROM titres_hebdo h JOIN joueurs j ON j.id = h.joueur WHERE h.semaine = ?",
  ).bind(semaine).all()).results;
  const enTete = {};
  const t = (await env.DB.prepare(
    "SELECT x.famille, j.pseudo, x.c FROM (SELECT famille, joueur, COUNT(*) AS c, SUM(temps) AS st FROM exercices "
    + "WHERE semaine = ? AND verifie = 1 GROUP BY famille, joueur) x JOIN joueurs j ON j.id = x.joueur ORDER BY x.famille, x.c DESC, x.st ASC",
  ).bind(cette).all()).results;
  for (const r of t) enTete[r.famille] ??= { pseudo: r.pseudo, n: r.c };
  const palmares = (await env.DB.prepare(
    "SELECT j.pseudo, COUNT(*) AS n FROM titres_hebdo h JOIN joueurs j ON j.id = h.joueur GROUP BY h.joueur ORDER BY n DESC, MIN(h.semaine) ASC LIMIT 10",
  ).all()).results;
  return { semaine, cetteSemaine: cette, records, stars: Object.fromEntries(stars.map((x) => [x.famille, { pseudo: x.pseudo, n: x.n }])),
    enTete, palmares };
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
// polices pixel, hébergées ici (public/polices, fichiers woff2 du projet Fontsource, licence SIL OFL 1.1) :
// aucune requête vers Google Fonts, donc aucune adresse IP envoyée à Google.
// « Press Start 2P » pour les titres et les boutons, « VT323 » pour le texte.
// Elles ne couvrent que l'alphabet latin (et le cyrillique pour Press Start 2P) : les autres écritures gardent
// leurs polices lisibles, en taille normale (VT323 est petite, la même taille rendrait le reste énorme).
const UNICODE = {
  latin: "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD",
  "latin-ext": "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF",
  cyrillic: "U+0301,U+0400-045F,U+0490-0491,U+04B0-04B1,U+2116",
  "cyrillic-ext": "U+0460-052F,U+1C80-1C8A,U+20B4,U+2DE0-2DFF,U+A640-A69F,U+FE2E-FE2F",
};
const FONTES = [["Press Start 2P", "press-start-2p", ["latin", "latin-ext", "cyrillic", "cyrillic-ext"]], ["VT323", "vt323", ["latin", "latin-ext"]]]
  .flatMap(([famille, fichier, sousEnsembles]) => sousEnsembles.map((u) => `@font-face{font-family:"${famille}";font-style:normal;font-weight:400;font-display:swap;`
    + `src:url(/polices/${fichier}-${u}-400-normal.woff2) format("woff2");unicode-range:${UNICODE[u]}}`)).join("\n");
const PIXEL = `"Press Start 2P",${MONO},monospace`;
const VT = `"VT323",${MONO},monospace`;

// un cadre en escalier (coins crantés) : quatre ombres décalées, sans image
const cran = (c, p = 4) => `0 -${p}px 0 ${c},0 ${p}px 0 ${c},-${p}px 0 0 ${c},${p}px 0 0 ${c}`;

const CSS = `
${FONTES}
:root{--fond:#08100c;--panneau:#0f1a14;--ecran:#050b08;--bord:#2b4d38;--bord-vif:#4c8c63;--texte:#dcf7e6;--doux:#9cc4aa;
--vert:#5cff95;--vert-fonce:#139a4c;--ambre:#ffb84d;--ambre-fonce:#a86400;--encre:#04170b;
--pixel:${PIXEL};--police:${VT};--titre:${PIXEL};--corps:22px;--interligne:1.3;--petit:19px;--mini:11px;--bouton:13px;--graisse:400;--h1:28px;--h2:16px}
html:lang(ru){--police:${MONO},monospace;--corps:17px;--interligne:1.55;--petit:15px}
${["zh", "ja", "hi", "bn", "ar", "ur"].map((l) => `html:lang(${l}){--police:${POLICES[l]};--titre:${POLICES[l]};--corps:17px;--petit:15px;--mini:13px;--bouton:17px;--graisse:700;--h1:30px;--h2:21px;--interligne:1.65}`).join("\n")}
html:lang(ar){--interligne:1.85}html:lang(ur){--interligne:2.15}
*{box-sizing:border-box}
html{background:var(--fond)}
body{margin:0;min-height:100vh;color:var(--texte);font:var(--corps)/var(--interligne) var(--police);
 background:radial-gradient(ellipse 120% 60% at 50% -10%,#123322 0,rgba(8,16,12,0) 60%),var(--fond)}
body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:50;
 background:repeating-linear-gradient(to bottom,rgba(0,0,0,0) 0 2px,rgba(0,0,0,.13) 2px 3px)}
@media (prefers-reduced-motion:reduce){body::after{display:none}}
a{color:var(--vert);text-underline-offset:3px}
a:hover{color:var(--ambre)}
:focus-visible{outline:3px solid var(--ambre);outline-offset:6px}
h1,h2,h3{font-family:var(--titre);font-weight:var(--graisse)}
h1{font-size:var(--h1);line-height:1.45;margin:10px 0 14px;color:var(--vert);text-shadow:0 0 14px rgba(92,255,149,.35)}
h2{font-size:var(--h2);line-height:1.5;margin:44px 0 18px;color:var(--ambre)}
h2 .petit{display:block;margin-top:6px;font:var(--petit)/1.3 var(--police)}
h2::before{content:"";display:inline-block;vertical-align:.1em;margin-inline-end:12px;width:10px;height:10px;background:var(--ambre);box-shadow:${cran("var(--ambre-fonce)", 2)}}
p{margin:0 0 14px}
.doux{color:var(--doux)}
.petit{font-size:var(--petit)}
.pixel{font-family:var(--pixel)}
/* ---- en-tête : une fenêtre de terminal */
.entete{max-width:1040px;margin:18px auto 0;padding:0 16px}
.barre{display:flex;align-items:center;gap:14px;flex-wrap:wrap;background:var(--bord);padding:8px 14px;box-shadow:${cran("var(--bord)")};margin:4px 4px 0}
.points{display:flex;gap:8px}.points i{width:12px;height:12px;background:#ff6b6b}.points i+i{background:var(--ambre)}.points i+i+i{background:var(--vert)}
.logo{display:flex;align-items:center;gap:10px;color:var(--texte);text-decoration:none;font:13px/1 var(--pixel);letter-spacing:1px}
.logo img{image-rendering:pixelated}
.menu{display:flex;flex-wrap:wrap;gap:4px 22px;align-items:center;background:var(--panneau);padding:10px 18px;margin:0 4px;box-shadow:${cran("var(--bord)")}}
.menu a{color:var(--texte);text-decoration:none;font-family:var(--police);white-space:nowrap;padding:2px 0}
.menu a .invite{color:var(--vert);margin-inline-end:6px}
.menu a:hover{color:var(--vert)}
.menu a[aria-current]{color:var(--ambre)}.menu a[aria-current] .invite{color:var(--ambre)}
.curseur{color:var(--vert);animation:clignote 1.1s steps(1) infinite}
.menu .curseur{color:var(--ambre);margin-inline-start:4px}
@keyframes clignote{50%{opacity:0}}
.langues{margin-inline-start:auto;display:flex;gap:6px;align-items:center}
.langues select{background:var(--ecran);color:var(--texte);border:0;box-shadow:${cran("var(--bord-vif)", 2)};padding:4px 8px;font:16px ${MONO};max-width:11em}
.langues button{font-size:11px;padding:6px 10px;margin:0}
main{max-width:1040px;margin:0 auto;padding:30px 20px 80px}
/* ---- panneaux et fenêtres */
.carte{background:var(--panneau);padding:18px 20px;margin:4px;box-shadow:${cran("var(--bord)")}}
.fenetre{background:var(--panneau);margin:4px;box-shadow:${cran("var(--bord)")}}
.fenetre>.titre-fen{display:flex;align-items:center;gap:12px;background:var(--bord);padding:6px 14px;color:var(--texte);font:18px/1.2 ${VT}}
.fenetre>.titre-fen .points i{width:10px;height:10px}
.fenetre>.contenu{padding:16px 20px}
.grille{display:grid;gap:24px;grid-template-columns:repeat(auto-fit,minmax(250px,1fr))}
.ecran{background-color:var(--ecran);background-image:linear-gradient(rgba(92,255,149,.06) 1px,transparent 1px),linear-gradient(90deg,rgba(92,255,149,.06) 1px,transparent 1px);
 background-size:8px 8px;box-shadow:inset 0 0 0 2px #000,inset 0 0 24px rgba(92,255,149,.08)}
/* ---- boutons pixel */
.btn,button{display:inline-flex;align-items:center;justify-content:center;gap:10px;font:var(--bouton)/1.6 var(--titre);font-weight:var(--graisse);color:var(--encre);
 background:var(--vert);border:0;padding:12px 18px;margin-block:10px;margin-inline:4px 14px;text-decoration:none;cursor:pointer;
 box-shadow:inset 0 -5px 0 var(--vert-fonce),${cran("var(--vert)")}}
.btn:hover,button:hover{color:var(--encre);filter:brightness(1.08)}
.btn:active,button:active{transform:translateY(2px);box-shadow:inset 0 -2px 0 var(--vert-fonce),${cran("var(--vert)")}}
.btn.ambre{background:var(--ambre);box-shadow:inset 0 -5px 0 var(--ambre-fonce),${cran("var(--ambre)")}}
.btn.grand{font-size:calc(var(--bouton) + 3px);padding:18px 24px}
.btn .fichier{font:12px/1.6 var(--pixel)}
.btn.large{display:flex;width:calc(100% - 8px);margin-inline:4px;padding:16px 10px}
.fleche{flex:none}
/* ---- accueil */
.hero{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,.75fr);gap:32px;align-items:center}
.invite-ligne{font:20px ${VT};color:var(--doux);margin:0}
.invite-ligne b{color:var(--vert);font-weight:normal}
.hero h1{font-size:calc(var(--h1) + 4px)}
.scene{display:grid;place-items:center;padding:30px 10px 18px;margin:4px;box-shadow:${cran("var(--bord)")}}
.mascotte{width:min(250px,100%);height:auto;image-rendering:pixelated;animation:flotte 2.6s steps(6) infinite alternate;filter:drop-shadow(0 0 18px rgba(92,255,149,.25))}
.sol{width:46%;height:10px;margin-top:10px;background:rgba(92,255,149,.18);animation:sol 2.6s steps(6) infinite alternate}
@keyframes flotte{to{transform:translateY(-14px)}}
@keyframes sol{to{transform:scaleX(.8);opacity:.6}}
.mascotte.mange{aspect-ratio:240/400;background:url(/mascotte_mange.png) 0 0/900% 100% no-repeat;cursor:pointer}
.mascotte.croque{animation:flotte 2.6s steps(6) infinite alternate,croque 4.51s step-end 1}
@keyframes croque{0.0%{background-position-x:0.0%}15.5%{background-position-x:12.5%}19.3%{background-position-x:25.0%}23.7%{background-position-x:37.5%}27.5%{background-position-x:50.0%}30.8%{background-position-x:37.5%}33.9%{background-position-x:62.5%}37.3%{background-position-x:50.0%}40.6%{background-position-x:37.5%}43.7%{background-position-x:62.5%}47.0%{background-position-x:37.5%}51.0%{background-position-x:75.0%}56.8%{background-position-x:87.5%}70.1%{background-position-x:100.0%}80.0%{background-position-x:0.0%}100%{background-position-x:0}}
@media (prefers-reduced-motion:reduce){.mascotte,.sol,.curseur{animation:none}}
.apercu{display:grid;gap:14px;grid-template-columns:repeat(auto-fill,minmax(96px,1fr));margin:18px 0}
.apercu a{display:grid;place-items:center;aspect-ratio:1;margin:2px;position:relative}
/* ---- tableaux */
table{width:100%;border-collapse:collapse}
td,th{padding:8px 6px;border-bottom:2px dashed var(--bord);text-align:start}
tr:last-child td{border-bottom:0}
th{color:var(--doux);font-weight:normal;font-size:var(--petit)}
td.num{text-align:end;white-space:nowrap}
td.rang{font:12px var(--pixel);color:var(--ambre);width:3em}
/* ---- badges, puces, jauges */
.badge{display:inline-flex;gap:8px;align-items:center;background:var(--ecran);padding:4px 12px;margin-block:8px;margin-inline:4px 12px;text-decoration:none;color:var(--texte);box-shadow:${cran("var(--bord)", 3)}}
.badge.verifie{box-shadow:${cran("var(--vert-fonce)", 3)}}
.barre-xp{height:16px;background:var(--ecran);margin:10px 3px;box-shadow:${cran("var(--bord)", 3)}}
.barre-xp>i,.jauge>i{display:block;height:100%;background:repeating-linear-gradient(90deg,var(--vert) 0 8px,transparent 8px 10px)}
code,pre{background:var(--ecran);font-family:${MONO},monospace;font-size:.82em;direction:ltr;unicode-bidi:isolate;color:var(--vert)}
code{padding:2px 6px;line-height:1.5;overflow-wrap:anywhere}
pre{padding:12px;overflow-x:auto;text-align:left}
.ltr{direction:ltr;unicode-bidi:isolate}
.creature{image-rendering:pixelated;max-width:100%;height:auto}
.rgb{background:linear-gradient(90deg,#ff6b6b,#ffd75f,#5cff95,#5fd7ff,#c58cff,#ff7aa8,#ff6b6b);background-size:200% auto;
 -webkit-background-clip:text;background-clip:text;color:transparent;animation:rgb 4s linear infinite}
@keyframes rgb{to{background-position:200% center}}
@media (prefers-reduced-motion:reduce){.rgb{animation:none}}
/* ---- rareté */
.rar{display:inline-block;font:var(--mini)/1.5 var(--titre);font-weight:var(--graisse);color:var(--encre);background:var(--r);padding:4px 8px;margin:4px 3px;box-shadow:${cran("var(--r)", 2)};white-space:nowrap}
.legende{display:flex;flex-wrap:wrap;gap:6px 8px;margin:6px 0 12px}
.pastille{display:inline-block;width:12px;height:12px;background:var(--r);box-shadow:${cran("var(--r)", 2)};margin:0 4px}
/* ---- filtres */
.filtres{display:flex;flex-wrap:wrap;align-items:center;gap:8px 4px}
.filtres+.filtres{margin-top:10px}
.filtres .etiquette{color:var(--doux);margin-inline-end:8px}
.puce{display:inline-flex;align-items:center;gap:6px;background:var(--ecran);color:var(--texte);text-decoration:none;padding:3px 10px;margin:3px 5px;box-shadow:${cran("var(--bord)", 2)}}
.puce:hover{color:var(--vert)}
.puce[aria-current]{background:var(--ambre);color:var(--encre);box-shadow:${cran("var(--ambre)", 2)}}
/* ---- cartes de bestioles (façon Pokédex) */
.grille-b{display:grid;gap:22px;grid-template-columns:repeat(auto-fill,minmax(172px,1fr))}
.bestiole{display:flex;flex-direction:column;align-items:center;gap:8px;padding:10px 12px 14px;margin:4px;background:var(--panneau);color:var(--texte);text-decoration:none;
 box-shadow:inset 0 4px 0 var(--r,var(--bord)),${cran("var(--bord)")}}
a.bestiole:hover{color:var(--texte);box-shadow:inset 0 4px 0 var(--r,var(--bord)),${cran("var(--bord-vif)")}}
.bestiole .haut{display:flex;justify-content:space-between;align-items:center;width:100%;font:10px/1 var(--pixel);color:var(--doux)}
.bestiole .haut .fam{font:22px/1 sans-serif}
.bestiole .ecran{width:100%;aspect-ratio:1;display:grid;place-items:center;position:relative}
.bestiole .ecran img,.portrait img,.apercu img{position:absolute;inset:8%;width:84%;height:84%;object-fit:contain;image-rendering:pixelated}
.bestiole code{display:block;font-size:13px;text-align:center;overflow-wrap:anywhere;padding:2px 4px;width:100%}
.bestiole .ecran svg{width:70%;height:auto}
.nom-b{font:11px/1.5 var(--pixel);text-align:center;overflow-wrap:anywhere}
.nom-v{font:var(--mini)/1.5 var(--titre);font-weight:var(--graisse)}
.capture{align-items:stretch;text-align:start}
.capture .nom-b,.capture .rar-l{text-align:center}
.capture.shiny{box-shadow:inset 0 4px 0 var(--r,var(--bord)),${cran("#ffd75f")},0 0 22px rgba(255,215,95,.25)}
.capture .marque{font-size:var(--petit);margin:2px 0}
.capture .infos{font-size:var(--petit);color:var(--doux);line-height:1.25}
.anime{direction:ltr;background-size:auto 100%;background-repeat:no-repeat;image-rendering:pixelated;animation:anime 1.2s steps(12) infinite}
@keyframes anime{from{background-position:0 0}to{background-position:calc(var(--px) * -12) 0}}
@media (prefers-reduced-motion:reduce){.anime{animation:none}}
/* ---- fiche d'espèce */
.fiche{display:grid;grid-template-columns:minmax(0,.9fr) minmax(0,1.1fr);gap:32px;align-items:start}
.portrait{aspect-ratio:1;display:grid;place-items:center;position:relative;margin:4px;box-shadow:inset 0 6px 0 var(--r),${cran("var(--bord)")}}
.portrait svg{width:70%;height:auto}
.numero{font:14px var(--pixel);color:var(--doux)}
.stats-b{display:grid;gap:8px;margin-top:16px}
.stat{display:grid;grid-template-columns:5.5em 1fr 2.4em;gap:12px;align-items:center}
.stat b{font:12px var(--pixel);text-align:end}
.jauge{height:14px;background:var(--ecran);box-shadow:${cran("var(--bord)", 2)}}
.stades{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:16px;align-items:end}
.stades figure{margin:0;text-align:center}
.stades .ecran{aspect-ratio:1;display:flex;align-items:flex-end;justify-content:center;padding-bottom:6%;margin:3px;box-shadow:inset 0 0 0 2px #000,${cran("var(--bord)", 3)}}
.stades img{object-fit:contain;image-rendering:pixelated;height:var(--h);width:auto;max-width:94%}
.stades figcaption{margin-top:10px;font-size:var(--petit);color:var(--doux)}
.variante.pas-dessinee .ecran img{filter:grayscale(1) brightness(.55)}
.voisins{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-top:36px}
/* ---- salle d'entraînement (badges en pixels, records, Stars de la semaine) */
.badge-px{image-rendering:pixelated;flex:none}
.echelle{display:flex;flex-wrap:wrap;gap:18px 26px;align-items:flex-end;margin:10px 4px 14px}
.ech{margin:0;text-align:center;font-size:var(--petit);max-width:9em}
.ech figcaption{margin-top:6px}
.stars .star{display:flex;gap:14px;align-items:center}
h2.avec-badge{display:flex;align-items:center;gap:12px}
h2.avec-badge::before{display:none}
/* ---- pied de page */
.pied{max-width:1040px;margin:0 auto;padding:22px 20px 36px;border-top:2px dashed var(--bord);color:var(--doux);font-size:var(--petit);text-align:center}
.pied .liens{display:flex;flex-wrap:wrap;justify-content:center;gap:4px 26px}
.pied a{color:var(--doux);text-decoration:none;white-space:nowrap;padding:2px 0}
.pied a:hover{color:var(--vert)}
.pied p{margin:10px 0 0;font-size:calc(var(--petit) - 2px);opacity:.8}
/* ---- pages pour les adultes (parents, soutenir, textes légaux) */
.texte-long{max-width:780px}
.texte-long ul{padding-inline-start:26px;margin:0 0 14px}
.texte-long li{margin:0 0 8px}
.texte-long li::marker{color:var(--ambre)}
.bandeau{display:flex;gap:14px;align-items:flex-start;background:var(--ecran);padding:14px 18px;margin:4px 4px 22px;box-shadow:${cran("var(--ambre-fonce)")}}
.bandeau .icone{font:20px/1 var(--pixel);color:var(--ambre);flex:none}
.bandeau p{margin:0}
.enfants{box-shadow:inset 0 4px 0 var(--vert),${cran("var(--bord)")}}
.enfants li{margin-bottom:10px}
.avertissement{box-shadow:${cran("var(--ambre-fonce)")}}
.avertissement p:last-child,.carte>p:last-child{margin-bottom:0}
.dons{display:flex;flex-wrap:wrap;gap:6px}
html:not([lang="fr"]) section[lang="fr"]{border-top:2px dashed var(--bord);margin-top:36px;padding-top:6px}
.defile{overflow-x:auto;margin:0 0 14px}
.tableau-legal{font-size:var(--petit);min-width:640px}
.tableau-legal td{vertical-align:top}
.tableau-legal td:first-child{width:38%}
@media (max-width:760px){
 .pied{padding:20px 16px 30px}
 .tableau-legal{min-width:0}
 .tableau-legal,.tableau-legal tbody,.tableau-legal tr,.tableau-legal td{display:block;width:auto}
 .tableau-legal .entetes{display:none}
 .tableau-legal tr{padding:12px 0;border-bottom:2px dashed var(--bord)}
 .tableau-legal td,.tableau-legal td:first-child{width:auto;border:0;padding:3px 0}
 .tableau-legal td[data-t]::before{content:attr(data-t) " : ";color:var(--ambre)}
 .bandeau{padding:12px 14px}
 .hero,.fiche{grid-template-columns:1fr;gap:18px}
 .hero .scene{order:-1}
 .mascotte{width:min(170px,46vw)}
 .scene{padding:18px 10px 12px}
 :root{--h1:20px;--h2:14px;--corps:21px}
 ${["zh", "ja", "hi", "bn", "ar", "ur"].map((l) => `html:lang(${l})`).join(",")}{--h1:24px;--h2:19px;--corps:16px}
 html:lang(ru){--corps:16px}
 .hero h1{font-size:calc(var(--h1) + 2px)}
 main{padding:22px 16px 64px}
 .entete{padding:0 12px;margin-top:12px}
 .menu{gap:2px 16px;padding:8px 14px}
 .langues{margin-inline-start:0}
 .grille-b{grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
 .nom-b{font-size:10px}
 .stades{grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
 .stades .ecran{margin:2px}
 td,th{padding:6px 3px}
 .btn.grand{padding:16px 18px}
}
${CSS_TERMINAL}`;

/** Le contexte de langue d'une requête : langue, textes, sens d'écriture, format des dates. */
function contexteLangue(requete, url) {
  const { lang, demandee } = choisirLangue(requete, url);
  return { lang, demandee, t: textes(lang), url, dir: RTL.has(lang) ? "rtl" : "ltr", locale: LOCALES[lang] };
}

/** Un nom venu des données ou d'un joueur (bestiole, pseudo…) : isolé pour ne pas se mélanger au sens d'écriture. */
const bdi = (s) => `<bdi>${echapper(s)}</bdi>`;
const numero = (e) => `<bdi>#${String(e.numero).padStart(3, "0")}</bdi>`;
const lib = (L, table, cle) => libelle(L.t[table], cle);
/** Une flèche « télécharger » en gros pixels (les polices pixel n'ont pas de flèche). */
const FLECHE = `<svg class="fleche" viewBox="0 0 7 8" width="14" height="16" aria-hidden="true" shape-rendering="crispEdges"><path fill="currentColor" d="M2 0h3v4h2v1H6v1H5v1H4v1H3V7H2V6H1V5H0V4h2z"/></svg>`;
const points = `<span class="points" aria-hidden="true"><i></i><i></i><i></i></span>`;
/** Une fenêtre de terminal : barre de titre (3 points + chemin) et contenu. */
const fenetre = (titre, contenu) => `<div class="fenetre"><div class="titre-fen">${points}<bdi class="ltr">${titre}</bdi></div><div class="contenu">${contenu}</div></div>`;

function selecteurLangue(L) {
  const caches = [...L.url.searchParams].filter(([k]) => k !== "lang")
    .map(([k, v]) => `<input type="hidden" name="${echapper(k)}" value="${echapper(v)}">`).join("");
  const options = LANGUES.map((l) => `<option value="${l}" lang="${l}" dir="${RTL.has(l) ? "rtl" : "ltr"}"${l === L.lang ? " selected" : ""}>${NOMS_LANGUES[l]}</option>`).join("");
  return `<form class="langues" method="get" action="${echapper(L.url.pathname)}">${caches}<span aria-hidden="true">🌐</span>`
    + `<select name="lang" aria-label="${echapper(L.t.nav.langue)}" onchange="this.form.submit()">${options}</select>`
    + `<noscript><button type="submit">OK</button></noscript></form>`;
}

function menu(L) {
  const n = L.t.nav;
  const ici = L.url.pathname.replace(/\/+$/, "") || "/";
  const liens = [["/classement", n.classement], ["/records", L.t.navRecords], ["/bestiaire", n.bestiaire], ["/captures", n.captures], ["/ctf", n.ctf],
    ["/#telecharger", n.telecharger], ["/compte", n.compte]];
  return liens.map(([href, t]) => {
    const actif = href !== "/#telecharger" && (ici === href || ici.startsWith(href + "/"));
    return `<a href="${href}"${actif ? ' aria-current="page"' : ""}><span class="invite" aria-hidden="true">&gt;</span>${t}${actif ? '<span class="curseur" aria-hidden="true">█</span>' : ""}</a>`;
  }).join("");
}

/** Le pied de page : liens discrets vers le code, le contact et les pages pour les adultes. */
function piedDePage(L) {
  const P = L.t.pied;
  const liens = [[DEPOT, P.source], [`mailto:${CONTACT}`, P.contact], ["/soutenir", P.soutenir], ["/parents", P.parents],
    ["/mentions-legales", P.mentions], ["/confidentialite", P.confidentialite]];
  return `<footer class="pied"><div class="liens">`
    + liens.map(([href, t]) => `<a href="${echapper(href)}">${echapper(t)}</a>`).join("")
    + `</div><p>Terminagotchi · <bdi>terminagotchi.com</bdi></p></footer>`;
}

function page(L, titre, contenu, description = L.t.description, statut = 200) {
  return new Response(`<!doctype html><html lang="${L.lang}" dir="${L.dir}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${echapper(titre)} · Terminagotchi</title><meta name="description" content="${echapper(description)}">
<meta name="theme-color" content="#08100c">
<link rel="icon" type="image/png" href="/favicon.png"><link rel="apple-touch-icon" href="/icone.png">
<link rel="preload" href="/polices/press-start-2p-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/polices/vt323-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<style>${CSS}</style></head><body>
<header class="entete"><div class="barre">${points}<a class="logo" href="/"><img src="/icone.png" alt="" width="28" height="28"><bdi>TERMINAGOTCHI</bdi></a>${selecteurLangue(L)}</div>
<nav class="menu">${menu(L)}</nav></header>
<main>${contenu}</main>
${piedDePage(L)}
${barreTerminal(L)}</body></html>`, {
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
  return `<tr><td class="rang"><bdi>${i + 1}</bdi></td><td><a href="/joueur/${encodeURIComponent(j.pseudo)}">${bdi(j.pseudo)}</a></td>
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
  // la première espèce de chaque famille, en portrait
  const apercu = BESTIAIRE.familles.map((f) => PUBLIQUES.find((e) => e.famille === f.nom && e.portrait)).filter(Boolean)
    .map((e) => `<a class="ecran" href="/bestiaire/${e.id}" title="${echapper(e.nom)}">${imgPortrait(e, "classique", "adulte", e.nom)}</a>`).join("");
  return page(L, A.titre, `
<section class="hero">
  <div>
    <p class="invite-ligne ltr" aria-hidden="true"><b>~$</b> ./terminagotchi<span class="curseur">█</span></p>
    <h1>${A.heroTitre}</h1>
    <p>${A.heroTexte}</p>
    <p><a class="btn grand" href="#telecharger">${FLECHE}${A.telecharger}</a><a class="btn ambre" href="/bestiaire">${A.voirBestiaire}</a></p>
    <p class="doux petit">${A.recensees(n)}</p>
  </div>
  <div class="scene ecran"><div class="mascotte mange" role="img" aria-label="Terminagotchi"></div><div class="sol" aria-hidden="true"></div></div><script>(function(){var m=document.querySelector(".mascotte.mange");if(!m||matchMedia("(prefers-reduced-motion:reduce)").matches)return;function c(){m.classList.remove("croque");void m.offsetWidth;m.classList.add("croque")}m.addEventListener("animationend",function(e){if(e.animationName==="croque")m.classList.remove("croque")});m.addEventListener("click",c);function t(){setTimeout(function(){c();t()},12000+Math.random()*18000)}setTimeout(c,2500);t()})()</script>
</section>
<h2 id="telecharger">${A.telecharger}</h2>
<div class="grille">
  <div class="carte"><b>📱 Android</b><p class="doux">${A.android}</p>
    <a class="btn large" href="${DEPOT}/releases/latest/download/terminagotchi.apk">${FLECHE}<bdi class="fichier">terminagotchi.apk</bdi></a></div>
  <div class="carte"><b>💻 ${A.pcTitre}</b><p class="doux">${A.pc}</p>
    <a class="btn large ambre" href="${DEPOT}/releases/latest/download/terminagotchi.pyz">${FLECHE}<bdi class="fichier">terminagotchi.pyz</bdi></a>
    <p class="doux">${A.puis} <code>python3 terminagotchi.pyz</code></p></div>
  <div class="carte"><b>🔗 ${A.partoutTitre}</b><p class="doux">${A.partout}</p></div>
</div>
<h2>${A.bestioles}</h2>
<p>${A.bestiolesTexte}</p>
<div class="apercu">${apercu}</div>
<h2>${A.classement}</h2>
${fenetre("~/classement", `${lignes ? tableClassement(L, lignes) : `<p class="doux">${A.personne}</p>`}
<p style="margin:12px 0 0"><a href="/classement">${A.voirTout}</a></p>`)}
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
${fenetre("~/classement --top 100", lignes ? tableClassement(L, lignes) : `<p class="doux">${C.personne}</p>`)}`);
}

async function pageJoueur(env, L, pseudo) {
  const J = L.t.joueur;
  const p = await profilPublic(env, pseudo);
  if (!p) return page(L, J.inconnuTitre, `<h1>${J.inconnu}</h1><p><a href="/classement">${J.retour}</a></p>`);
  const lo = 10 * (p.niveau - 1) ** 2;
  const hi = 10 * p.niveau ** 2;
  const pct = Math.round((100 * (p.xp - lo)) / Math.max(1, hi - lo));
  const stats = STATS.map((s) => `<span class="badge" title="${echapper(lib(L, "stats", s))}">${echapper(L.t.court[s])} <b class="pixel" style="font-size:12px">${p.stats[s]}</b></span>`).join("");
  const badges = p.badges.map((b) => `<a class="badge verifie" href="${b.lien}">✔ ${echapper(titreBadge(L, b))}</a>`).join("")
    || `<span class="doux">${J.aucunBadge}</span>`;
  // collection : les anciens noms (bestiaire v1) comptent pour la nouvelle espèce de même numéro
  const parEspece = new Map();
  for (const [nom, n] of Object.entries(p.collection)) {
    const e = especeDe(nom);
    if (e && n) parEspece.set(e, (parEspece.get(e) || 0) + n);
  }
  const coll = [...parEspece].sort((a, b) => a[0].numero - b[0].numero).map(([e, n]) =>
    `<a class="bestiole" style="--r:${COULEUR_RARETE[e.rarete]}" href="${e.secrete ? `/captures?joueur=${encodeURIComponent(p.pseudo)}` : `/bestiaire/${e.id}`}">
     <div class="haut"><span>${numero(e)}</span><span class="fam" title="${echapper(lib(L, "familles", e.famille))}">${e.icone}</span></div>
     <div class="ecran">${visuel(L, e)}</div><div class="nom-b">${bdi(e.nom)} <bdi>×${n}</bdi></div></a>`).join("");
  const collHtml = coll ? `<p class="doux">${J.nbEspeces(parEspece.size)}</p><div class="grille-b">${coll}</div>`
    : `<span class="doux">${J.aucuneBestiole}</span>`;
  const comp = p.competences.map((c) => `<span class="badge">◇ ${bdi(c)}</span>`).join("")
    || `<span class="doux">${J.aucune}</span>`;
  const forme = p.forme && p.niveau >= 5 ? lib(L, "formes", p.forme) : "";
  const appareils = p.appareils.map((a) => (a === "android" ? J.telephone : J.pc)).join(" + ") || "—";
  const stade = L.t.stades[stadeDe(p.niveau)];
  return page(L, p.pseudo, `
<section class="hero">
  <div>
    <h1>${p.shiny ? `<span class="rgb">${bdi(p.nom)} ✨</span>` : bdi(p.nom)}</h1>
    <p class="doux">${J.ligneCreature(bdi(p.pseudo), echapper(stade), echapper(forme), bdi(p.trait || "?"))}</p>
    <p>${J.ligneNiveau(p.niveau, p.xp, p.rang)}</p>
    <div class="barre-xp"><i style="width:${pct}%"></i></div>
    <div style="margin-top:10px">${stats}</div>
    <p class="doux">${J.ligneActivite(p.commandes, p.gouts, appareils)}</p>
  </div>
  <div class="scene ecran">${svgCreature(p.niveau, p.forme, p.stats, 12, p.shiny, L.t.creature)}</div>
</section>
<h2>${J.badges}</h2><div>${badges}</div>
${sectionEntrainement(L, p.entrainement)}
<h2>${J.competences} <span class="doux petit">${J.declarees}</span></h2><div>${comp}</div>
<h2>${J.collection}</h2>${collHtml}
${p.partage ? `<p style="margin-top:20px"><a href="/captures?joueur=${encodeURIComponent(p.pseudo)}">${J.voirCaptures}</a></p>` : ""}
<p class="doux petit" style="margin-top:32px">${J.inscrit(new Date(p.inscrit).toLocaleDateString(L.locale))} ·
<a href="/api/profil/${encodeURIComponent(p.pseudo)}">${J.json}</a></p>`, J.description(p.nom, p.pseudo, p.niveau));
}

/** Le texte d'un titre de la salle d'entraînement, dans sa couleur (arc-en-ciel pour la Légende). */
function titreEnt(L, x) {
  if (!x) return "";
  const E = L.t.ent;
  const texte = x.id === "legende" ? E.titreLegende : x.id === "touche" ? E.titreTouche : x.id === "apprenti" ? E.titreApprenti
    : x.id === "star" ? E.titreStar(E.familles[x.famille]) : E.titreFamille(E.familles[x.famille], E.echelonsNoms[x.echelon]);
  return x.couleur === "arc" ? `<span class="rgb">« ${echapper(texte)} »</span>` : `<span style="color:${x.couleur}">« ${echapper(texte)} »</span>`;
}

const MEDAILLE_ICONE = ENT.ICONE_MEDAILLE;

async function pageRecords(env, L) {
  const E = L.t.ent;
  const d = await donneesRecords(env);
  const lienJ = (p) => `<a href="/joueur/${encodeURIComponent(p)}">${bdi(p)}</a>`;
  const echelle = ENT.ECHELONS.map((e, k) => `<figure class="ech">${ENT.svgBadge("explorateur", e, 3, E.echelonsNoms[e], 0)}<figcaption><b>${echapper(E.echelonsNoms[e])}</b> · <bdi>${ENT.SEUILS[k]}</bdi><br><span class="doux">${echapper(E.gradesSens[e])}</span></figcaption></figure>`).join("");
  const stars = ENT.FAMILLES.map((f) => {
    const s = d.stars[f];
    const t = d.enTete[f];
    return `<div class="carte star">${ENT.svgBadge(f, s ? "giga" : null, 3, E.familles[f])}<div><b>${echapper(E.familles[f])}</b>
<div>${s ? `🏆 ${lienJ(s.pseudo)} <span class="doux">${echapper(E.reussis(s.n))}</span>` : `<span class="doux">—</span>`}</div>
<div class="doux petit">${echapper(E.enTete)} : ${t ? `${lienJ(t.pseudo)} (${echapper(E.reussis(t.n))})` : "—"}</div></div></div>`;
  }).join("");
  const palmares = d.palmares.map((x, i) => `<tr><td class="rang"><bdi>${i + 1}</bdi></td><td>${lienJ(x.pseudo)}</td><td class="num">${echapper(E.fois(x.n))}</td></tr>`).join("");
  let familles = "";
  for (const f of ENT.FAMILLES) {
    const types = Object.keys(ENT.TYPES).filter((typ) => ENT.TYPES[typ][0] === f && d.records[typ]?.length);
    if (!types.length) continue;
    familles += `<h2 class="avec-badge">${ENT.svgBadge(f, "giga", 2)}${echapper(E.familles[f])}</h2><div class="grille">`
      + types.map((typ) => fenetre(`~/records/${typ}`, `<p><b>${echapper(E.types[typ])}</b></p><table><tr><th>#</th><th>${L.t.thJoueur}</th><th>${echapper(E.thTemps)}</th></tr>`
        + d.records[typ].map((r, i) => `<tr><td class="rang"><bdi>${i + 1}</bdi></td><td>${lienJ(r.pseudo)}</td><td class="num"><bdi>${r.t.toFixed(1)} s</bdi> ${MEDAILLE_ICONE[r.medaille]}</td></tr>`).join("")
        + "</table>")).join("") + "</div>";
  }
  return page(L, E.titre, `<h1>${E.h1}</h1><p>${E.intro}</p>
<h2>${echapper(E.echelons)}</h2><p>${echapper(E.gradesIntro)}</p><div class="echelle">${echelle}</div><p class="doux petit">${echapper(E.echelle)}</p>
<h2>${echapper(E.stars)}</h2><p class="doux">${echapper(E.starsSous)}</p>
${Object.keys(d.stars).length || Object.keys(d.enTete).length ? `<div class="grille stars">${stars}</div>` : `<p class="doux">${echapper(E.aucuneStar)}</p>`}
${palmares ? `<h2>${echapper(E.palmares)}</h2>${fenetre("~/stars", `<table>${palmares}</table>`)}` : ""}
${familles || `<h2>${echapper(E.records)}</h2><p class="doux">${echapper(E.aucun)}</p>`}`, E.description);
}

/** La partie « salle d'entraînement » du profil : badges, titre, Stars, records. */
function sectionEntrainement(L, ent) {
  const E = L.t.ent;
  if (!ent) return "";
  const badges = ENT.FAMILLES.filter((f) => ent.familles[f]?.echelon).map((f) => {
    const x = ent.familles[f];
    const et = "★".repeat(x.etoiles || 0) + "☆".repeat(3 - (x.etoiles || 0));
    const nom = `${E.familles[f]} · ${E.echelonsNoms[x.echelon]} ${et}`;
    return `<figure class="ech" title="${echapper(nom)}">${ENT.svgBadge(f, x.echelon, 3, nom, x.etoiles || 0)}<figcaption>${echapper(E.familles[f])}<br><span class="doux">${echapper(E.echelonsNoms[x.echelon])} ${et} · ${echapper(E.reussis(x.n))}</span></figcaption></figure>`;
  }).join("");
  const nonV = ENT.FAMILLES.reduce((a, f) => a + (ent.familles[f]?.nonVerifies || 0), 0);
  const stars = Object.entries(ent.stars || {}).filter(([f]) => E.familles[f])
    .map(([f, n]) => `<span class="badge" style="color:#ffaf00">${echapper(E.starCompte(E.familles[f], n))}</span>`).join("");
  const recs = Object.keys(ENT.TYPES).filter((typ) => ent.records[typ]).map((typ) => {
    const r = ent.records[typ];
    return `<tr><td>${echapper(E.types[typ])}</td><td class="num"><bdi>${r.t.toFixed(1)} s</bdi> ${MEDAILLE_ICONE[ENT.medaille(typ, r.t)]}</td>
<td>${r.v ? `<span style="color:var(--vert)">${echapper(E.verifie)}</span>` : `<span class="doux">${echapper(E.nonVerifie)}</span>`}</td></tr>`;
  }).join("");
  return `<h2>${echapper(E.profil)}</h2>
${ent.titre ? `<p>${E.titreLigne(titreEnt(L, ent.titre))}</p>` : ""}
${badges ? `<div class="echelle">${badges}</div>` : `<p class="doux">${echapper(E.aucunBadge)}</p>`}
${nonV ? `<p class="doux">${echapper(E.nonVerifies(nonV))}</p>` : ""}
${stars ? `<div>${stars}</div>` : ""}
${recs ? `<h2>${echapper(E.records)} <a class="petit" href="/records">/records</a></h2>${fenetre("~/records", `<table>${recs}</table>`)}` : ""}`;
}

async function pageBadge(env, L, id) {
  const B = L.t.badge;
  const b = await env.DB.prepare("SELECT b.*, j.pseudo FROM badges b JOIN joueurs j ON j.id = b.joueur WHERE b.id = ?").bind(id).first();
  if (!b) return page(L, B.inconnuTitre, `<h1>${B.inconnuTitre}</h1><p class="doux">${B.faux}</p>`);
  const date = new Date(b.date).toLocaleString(L.locale, { timeZone: "Europe/Paris" });
  const titre = titreBadge(L, b);
  return page(L, titre, `<div class="carte" style="max-width:600px;margin:24px auto;text-align:center">
<div style="font-size:56px">🏅</div><h1>${echapper(titre)}</h1>
<p>${B.delivre(`<a href="/joueur/${encodeURIComponent(b.pseudo)}"><b>${bdi(b.pseudo)}</b></a>`, `<bdi>${echapper(date)}</bdi>`)}</p>
<p style="color:var(--vert)">${B.verifie}</p>
<p class="doux">${B.identifiant} : <code>${echapper(b.id)}</code> · <a href="/api/badge/${echapper(b.id)}">${B.preuve}</a></p></div>`,
  B.description(titre, b.pseudo));
}

// ---------------------------------------------------------------- bestioles
/** Un portrait (public/portraits/<id>/<variante>_<stade>.webp). */
function imgPortrait(e, vid, stade, alt, extra = "") {
  return `<img src="/portraits/${e.id}/${encodeURIComponent(vid)}_${stade}.webp" alt="${echapper(alt)}" loading="lazy" decoding="async"${extra}>`;
}

/** La variante dessinée la plus proche (sinon la forme classique). */
const varianteDessinee = (e, vid) => (e.variantes.some((v) => v.id === vid && v.dessinee) ? vid : "classique");
/** Le stade d'une capture : nouveaux stades, ou anciens (enfant…finale) ramenés aux nouveaux. */
const stadePortrait = (s) => (TIRAGE.stades.includes(s) ? s : s === "finale" ? "ancien" : STADES_B.includes(s) ? s : "adulte");

/** Le dessin d'une bestiole : son portrait (variante, stade, teinte shiny), l'animation d'Abyssor, sinon le petit sprite. */
function visuel(L, e, c = {}, anim = "statique") {
  const filtre = c.shiny ? ` style="filter:hue-rotate(${Math.round((c.teinte || 0.5) * 360)}deg)"` : "";
  if (e.portrait) {
    const stade = stadePortrait(c.stade);
    return imgPortrait(e, varianteDessinee(e, c.variante), stade, `${e.nom} (${lib(L, "stadesB", stade)})`, filtre);
  }
  if (!ANIMEES.has(e.id)) return svgBestiole(e, c.shiny, 6);
  const stade = STADES_B.includes(c.stade) ? c.stade : "adulte";
  const px = 112;
  const teinte = c.shiny ? `filter:hue-rotate(${Math.round((c.teinte || 0.5) * 360)}deg);` : "";
  return `<div class="anime" role="img" aria-label="${echapper(e.nom)} (${echapper(lib(L, "stadesB", stade))})"
    style="width:${px}px;height:${px}px;background-image:url(/anim/${e.id}/${stade}/${anim}.webp);--px:${px}px;${teinte}"></div>`;
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
  return `<span class="rar" style="--r:${COULEUR_RARETE[r]}">${echapper(lib(L, "raretes", r))}</span>`;
}

/** Une carte façon Pokédex : numéro, icône de famille, grand portrait, nom, rareté. */
function carteEspece(L, e) {
  return `<a class="bestiole" style="--r:${COULEUR_RARETE[e.rarete]}" href="/bestiaire/${e.id}">
  <div class="haut"><span>${numero(e)}</span><span class="fam" title="${echapper(lib(L, "familles", e.famille))}" aria-label="${echapper(lib(L, "familles", e.famille))}">${e.icone}</span></div>
  <div class="ecran">${e.portrait ? imgPortrait(e, "classique", "adulte", e.nom) : svgBestiole(e)}</div>
  <div class="nom-b">${bdi(e.nom)}</div>${etiquetteRarete(L, e.rarete)}</a>`;
}

/** Le bestiaire : les 150 espèces dans leur forme classique, adulte. */
function pageBestiaire(L, url) {
  const B = L.t.bestiaire;
  const famille = url.searchParams.get("famille") || "";
  const rarete = url.searchParams.get("rarete") || "";
  const liste = PUBLIQUES.filter((e) => (!famille || e.famille === famille) && (!rarete || e.rarete === rarete));
  const lien = (k, v, t) => {
    const p = new URLSearchParams({ famille, rarete, [k]: v });
    for (const [a, b] of [...p]) if (!b) p.delete(a);
    const actif = (k === "famille" ? famille : rarete) === v;
    return `<a class="puce" href="/bestiaire${p.toString() ? "?" + p : ""}"${actif ? ' aria-current="true"' : ""}>${t}</a>`;
  };
  const raretes = BESTIAIRE.raretes.filter((r) => PUBLIQUES.some((e) => e.rarete === r));
  const filtresF = [lien("famille", "", B.toutes), ...BESTIAIRE.familles.map((f) => lien("famille", f.nom, `<span aria-hidden="true">${f.icone}</span> ${echapper(lib(L, "familles", f.nom))}`))].join("");
  const filtresR = [lien("rarete", "", B.toutes), ...raretes.map((r) => lien("rarete", r, `<i class="pastille" style="--r:${COULEUR_RARETE[r]}"></i> ${echapper(lib(L, "raretes", r))}`))].join("");
  return page(L, B.titre, `<h1>${B.h1}</h1>
<p>${B.intro}</p>
<div class="carte"><div class="filtres"><span class="etiquette">${B.famille}</span>${filtresF}</div>
<div class="filtres"><span class="etiquette">${B.rarete}</span>${filtresR}</div></div>
<h2>${B.raretesTitre}</h2>
<div class="legende">${BESTIAIRE.raretes.map((r) => etiquetteRarete(L, r)).join("")}</div>
<p class="doux">${B.raretesTexte}</p>
<p class="doux" style="margin-top:28px">${B.nb(liste.length)}</p>
<div class="grille-b">${liste.map((e) => carteEspece(L, e)).join("")}</div>`, B.description);
}

// la plus haute stat de base, pour la longueur des jauges
const STAT_MAX = Math.max(...PUBLIQUES.flatMap((e) => Object.values(e.stats)));
// hauteur des portraits selon le stade : on la voit grandir
const HAUTEUR_STADE = { bebe: 46, enfant: 60, ado: 72, adulte: 86, ancien: 96 };

function pageEspece(L, id) {
  const E = L.t.espece;
  const e = PAR_ID[id];
  if (!e || e.secrete) return page(L, E.inconnueTitre, `<h1>${E.inconnue}</h1><p><a href="/bestiaire">${E.retour}</a></p>`, undefined, 404);
  const i = PUBLIQUES.indexOf(e);
  const prec = PUBLIQUES[(i + PUBLIQUES.length - 1) % PUBLIQUES.length];
  const suiv = PUBLIQUES[(i + 1) % PUBLIQUES.length];
  const [fp, fs] = L.t.fleches;
  const stats = Object.entries(e.stats).map(([k, v]) => `<div class="stat"><span class="doux">${echapper(lib(L, "statsB", k))}</span>`
    + `<span class="jauge" aria-hidden="true"><i style="width:${Math.round((100 * v) / STAT_MAX)}%"></i></span><b>${v}</b></div>`).join("");
  const fam = lib(L, "familles", e.famille);
  const rar = lib(L, "raretes", e.rarete);
  const couleur = COULEUR_RARETE[e.rarete];
  const stades = BESTIAIRE.stades.map((s) => `<figure><div class="ecran">${e.portrait ? imgPortrait(e, "classique", s, `${e.nom} (${lib(L, "stadesB", s)})`, ` style="--h:${HAUTEUR_STADE[s]}%"`) : svgBestiole(e)}</div>
    <figcaption>${echapper(lib(L, "stadesB", s))}</figcaption></figure>`).join("");
  const variantes = e.variantes.map((v) => {
    const nom = v.id === "classique" ? E.classique : lib(L, "habitats", v.zone);
    return `<div class="bestiole variante${v.dessinee ? "" : " pas-dessinee"}" style="--r:${couleur}">
    <div class="ecran">${e.portrait ? imgPortrait(e, v.dessinee ? v.id : "classique", "adulte", `${e.nom} (${nom})`) : svgBestiole(e)}</div>
    <div class="nom-b nom-v">${echapper(nom)}</div>
    <div class="doux petit" style="text-align:center">${echapper(E.chance(v.chance))}</div>
    ${v.dessinee ? "" : `<div class="doux petit" style="text-align:center">${E.pasDessinee}</div>`}
    <code>~/terrain_terminagotchi/${echapper(v.zone)}</code></div>`;
  }).join("");
  return page(L, e.nom, `<p><a href="/bestiaire">${E.retourCourt}</a></p>
<section class="fiche">
  <div class="portrait ecran" style="--r:${couleur}">${e.portrait ? imgPortrait(e, "classique", "adulte", e.nom) : svgBestiole(e, false, 14)}</div>
  <div>
    <p class="numero">${numero(e)}</p>
    <h1>${e.rarete === "légendaire" ? `<span class="rgb">${bdi(e.nom)}</span>` : bdi(e.nom)}</h1>
    <p><span class="puce"><span aria-hidden="true">${e.icone}</span> ${echapper(E.famille(fam))}</span> ${etiquetteRarete(L, e.rarete)}</p>
    <p lang="fr" dir="ltr">${echapper(e.description)}</p>
    <p class="doux" lang="fr" dir="ltr">${echapper(e.comportement)}</p>
    <div class="stats-b" aria-label="${echapper(E.statsTitre)}">${stats}</div>
  </div>
</section>
<h2>${E.stades}</h2>
<div class="stades">${stades}</div>
<h2>${E.fiche}</h2>
${fenetre(`~/bestiaire/${e.id}`, `<table>
<tr><td class="doux">${E.frequence}</td><td>${etiquetteRarete(L, e.rarete)} ${echapper(lib(L, "frequences", e.frequence))} · ${echapper(E.unSur(e.un_sur))}</td></tr>
<tr><td class="doux">${E.apparition}</td><td>${E.attiree(`<code>${echapper(e.attiree_par)}</code>`)}</td></tr>
<tr><td class="doux">${E.habitat}</td><td>${echapper(lib(L, "habitats", e.habitat))} · <code>~/terrain_terminagotchi/${echapper(e.zone)}</code></td></tr>
<tr><td class="doux">${E.capacite}</td><td><bdi lang="fr">${echapper(e.capacite)}</bdi></td></tr>
<tr><td class="doux">${E.statFavorite}</td><td>${echapper(lib(L, "stats", e.stat))}</td></tr>
<tr><td class="doux">${E.taillePoids}</td><td><bdi>~${e.taille_cm} cm · ~${e.poids_ko} ${E.ko}</bdi></td></tr>
</table>`)}
<h2>${E.variantes}</h2>
<p class="doux">${E.variantesTexte}</p>
<div class="grille-b">${variantes}</div>
<nav class="voisins"><a class="puce" href="/bestiaire/${prec.id}">${fp} ${numero(prec)} ${bdi(prec.nom)}</a>
<a class="puce" href="/bestiaire/${suiv.id}">${numero(suiv)} ${bdi(suiv.nom)} ${fs}</a></nav>`,
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
  // l'espèce d'une capture : tirage vérifié, nouveau nom, ou ancien nom (bestiaire v1)
  const especeCapture = (c) => (c.verifie === true && PAR_NOM_T[c.espece] ? PAR_ID[PAR_NOM_T[c.espece].id] : null) || especeDe(c.espece);
  caps = caps.filter((c) => especeCapture(c) && (!shinySeul || c.shiny) && (!rarete || c.rarete === rarete));
  caps.sort((a, b) => (b.shiny - a.shiny) || ((b.verifie === true) - (a.verifie === true)) || (b.date - a.date));
  const total = caps.length;
  caps = caps.slice(0, 120);
  const cartes = caps.map((c) => {
    const e = especeCapture(c);
    const date = new Date(c.date).toLocaleDateString(L.locale);
    // anti-triche : seules les bestioles dont le serveur a refait le tirage sont « vérifiées »
    const verif = `<div class="petit">${c.verifie === true ? `<span style="color:var(--vert)">✔ ${K.verifiee}</span>` : `<span class="doux">${K.nonVerifiee}</span>`}</div>`;
    // rareté : celle de l'individu (nouveau bestiaire) ; les anciennes captures n'en ont pas
    const rar = COULEUR_RARETE[c.rarete] ? c.rarete : null;
    const brille = c.shiny || ["légendaire", "mythique"].includes(rar);
    const nom = brille ? `<span class="rgb">${bdi(e.nom)}${c.shiny ? " ✨" : ""}</span>` : bdi(e.nom);
    const stade = e.portrait ? stadePortrait(c.stade) : STADES_B.includes(c.stade) ? c.stade : "adulte";
    const vid = e.portrait ? varianteDessinee(e, c.variante) : "classique";
    const variante = c.variante && c.variante !== "classique" ? e.variantes.find((v) => v.id === c.variante) : null;
    return `<div class="bestiole capture${c.shiny ? " shiny" : ""}"${rar ? ` style="--r:${COULEUR_RARETE[rar]}"` : ""}>
      <div class="haut"><span>${numero(e)}</span><span class="fam" title="${echapper(lib(L, "familles", e.famille))}">${e.icone}</span></div>
      <div class="ecran">${visuel(L, e, { ...c, stade, variante: vid })}</div>
      <div class="nom-b">${nom}</div>
      ${rar ? `<div class="rar-l">${etiquetteRarete(L, rar)}</div>` : ""}
      <div class="infos">${echapper(lib(L, "stadesB", stade))}${variante ? ` · ${echapper(lib(L, "habitats", variante.zone))}` : ""}</div>
      <div class="marque" lang="fr" dir="ltr">« <span class="rgb">${echapper(c.marque)}</span> »</div>
      <div class="infos">${echapper(K.humeur(lib(L, "humeurs", c.humeur)))} · <bdi>${c.taille} cm</bdi><br>${K.potentiel} <b style="color:var(--vert)"><bdi>${c.potentiel} %</bdi></b></div>
      ${verif}
      <div class="infos">${K.par(`<a href="/joueur/${encodeURIComponent(c.pseudo)}">${bdi(c.pseudo)}</a>`, `<bdi>${echapper(date)}</bdi>`)}</div>
    </div>`;
  }).join("");
  const lienR = (v, t) => `<a class="puce" href="/captures?${new URLSearchParams({ ...(filtre && { joueur: filtre }), ...(shinySeul && { shiny: "1" }), ...(v && { rarete: v }) })}"${rarete === v ? ' aria-current="true"' : ""}>${t}</a>`;
  return page(L, K.titre, `<h1>${K.h1}</h1>
<p>${K.intro}
${filtre ? `${K.de(bdi(filtre))} <a href="/captures">${K.voirTous}</a>` : ""}</p>
<div class="carte"><div class="filtres">${lienR("", K.toutes)}${BESTIAIRE.raretes.map((x) => lienR(x, `<i class="pastille" style="--r:${COULEUR_RARETE[x]}"></i> ${echapper(lib(L, "raretes", x))}`)).join("")}
<a class="puce" href="/captures?${new URLSearchParams({ ...(filtre && { joueur: filtre }), ...(!shinySeul && { shiny: "1" }) })}"${shinySeul ? ' aria-current="true"' : ""}>${shinySeul ? K.pasQueShiny : `<span class="rgb">${K.shinySeul}</span>`}</a></div></div>
<p class="doux">${K.resume(total, joueurs, total > 120)}</p>
${cartes ? `<div class="grille-b" style="grid-template-columns:repeat(auto-fill,minmax(210px,1fr))">${cartes}</div>`
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
${fenetre("~/ctf", `<ol style="padding-inline-start:24px;margin:0">${liste}</ol>`)}
<h2>${C.valider}</h2>
<div class="carte"><p>${C.validerTexte}</p>
<p class="doux">${C.curl}</p></div>
<h2>${C.pourquoi}</h2>
<div class="carte"><p class="doux">${C.pourquoiTexte}</p></div>`);
}

// ====================================================================== pages pour les adultes

const lienMail = `<a href="mailto:${CONTACT}">${CONTACT}</a>`;
const liste = (items) => `<ul>${items.map((x) => `<li>${x}</li>`).join("")}</ul>`;
const NOMS_DONS = { liberapay: "Liberapay", kofi: "Ko-fi", github: "GitHub Sponsors" };

function pageSoutenir(L) {
  const S = L.t.soutenir;
  const dons = Object.entries(DONS).filter(([, lien]) => /^https:\/\//.test(lien || ""));
  const boutons = dons.length
    ? `<div class="dons">${dons.map(([k, lien], i) => `<a class="btn${i % 2 ? " ambre" : ""}" href="${echapper(lien)}" rel="noopener">${echapper(NOMS_DONS[k] || k)}</a>`).join("")}</div>`
    : `<p class="doux"><span class="curseur" aria-hidden="true">█</span> ${S.bientot}</p>`;
  return page(L, S.titre, `<div class="texte-long">
<h1>${S.h1}</h1>
<div class="bandeau"><span class="icone" aria-hidden="true">!</span><p>${S.pourQui}</p></div>
<h2>${S.gratuitTitre}</h2>
<p>${S.gratuit}</p>
<p class="doux">${S.cout}</p>
<h2>${S.donsTitre}</h2>
<div class="carte"><p>${S.donsTexte}</p>${boutons}</div>
<h2>${S.autresTitre}</h2>
${liste(S.autres.map((x, i) => (i === 1 ? `${x} <a href="${DEPOT}/issues">GitHub</a>` : x)))}
<p>${S.ecrire(lienMail)}</p>
<p class="pixel" style="color:var(--vert);font-size:14px;margin-top:28px">${S.merci}</p>
</div>`, S.gratuit);
}

function pageParents(L) {
  const P = L.t.parents;
  return page(L, P.titre, `<div class="texte-long">
<h1>${P.h1}</h1>
<p>${P.intro}</p>
<h2>${P.apprendTitre}</h2>
<p>${P.apprend}</p>
<p>${P.histoire}</p>
<h2>${P.sansTitre}</h2>
<div class="carte">${liste(P.sans)}</div>
<h2>${P.horsLigneTitre}</h2>
<p>${P.horsLigne}</p>
<p class="doux">${P.public}</p>
<h2>${P.ordiTitre}</h2>
${liste(P.ordi)}
<h2>${P.supprimerTitre}</h2>
<p>${P.supprimer(lienMail)}</p>
<p><a href="/confidentialite">${P.plus}</a></p>
<p><a class="btn ambre" href="/soutenir">${P.soutenir}</a></p>
</div>`, P.intro);
}

/** Le texte complet en français (qui fait foi), isolé pour garder sa langue et son sens d'écriture. */
const texteFr = (L, html, note = L.t.confidentialite.versionFr) => `${L.lang === "fr" || !note ? "" : `<p class="doux">${note}</p>`}<section lang="fr" dir="ltr">${html}</section>`;

function pageConfidentialite(L) {
  const C = L.t.confidentialite;
  const complet = confidentialiteFr({ contact: CONTACT, depot: DEPOT, conservation: CONSERVATION });
  return page(L, C.titre, `<div class="texte-long">
<h1>${C.h1}</h1>
<div class="carte enfants"><h2 style="margin-top:6px">${C.enfantsTitre}</h2>${liste(C.enfants)}</div>
<h2>${C.resumeTitre}</h2>
${liste([...C.resume, C.duree(Math.round(CONSERVATION.inactifMois / 12)), C.droits(lienMail)])}
${L.lang === "fr" ? "" : `<div class="bandeau"><span class="icone" aria-hidden="true">!</span><p>${C.modele}</p></div>`}
<h2>${C.complete}</h2>
${texteFr(L, complet)}
</div>`, C.enfants[0]);
}

function pageMentions(L) {
  const M = L.t.mentions;
  const complet = mentionsFr({ contact: CONTACT, depot: DEPOT, editeur: EDITEUR, licence: LICENCE });
  return page(L, M.titre, `<div class="texte-long">
<h1>${M.h1}</h1>
${L.lang === "fr" ? "" : `<div class="bandeau"><span class="icone" aria-hidden="true">!</span><p>${M.enFrancais} ${L.t.confidentialite.modele}</p></div>`}
${texteFr(L, complet, "")}
</div>`, M.titre);
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
  const parties = (await listeParties(env, j)).map((p) => `<li>${bdi(p.nom || "?")} · ${echapper(lib(L, "formes", p.forme) || "")} ${echapper(L.t.niv(p.niveau))}</li>`).join("");
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
  if (chemin === "/records") return pageRecords(env, L);
  if (chemin === "/ctf") return pageCtf(L, url.origin);
  if (chemin === "/bestiaire") return pageBestiaire(L, url);
  if (chemin === "/captures") return pageCaptures(env, L, url);
  if (chemin === "/soutenir") return pageSoutenir(L);
  if (chemin === "/parents") return pageParents(L);
  if (chemin === "/confidentialite") return pageConfidentialite(L);
  if (chemin === "/mentions-legales") return pageMentions(L);
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
        return new Response(null, { headers: { "access-control-allow-origin": "*", "access-control-allow-headers": "authorization, content-type", "access-control-allow-methods": "GET, POST, DELETE" } });
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
  // chaque jour (wrangler.toml, [triggers]) : on efface ce qui a dépassé sa durée de conservation
  async scheduled(evenement, env, ctx) {
    ctx.waitUntil(purger(env).then(() => semainesAttribuees(env)));
  },
};

// pour les tests
export { fusionner, niveauDe, drapeauDe, EPREUVES, normaliserJeton, purger, CONSERVATION };
