/**
 * La salle d'entraînement côté site : le serveur refait le tirage d'un exercice à partir de (graine, compteur) pour
 * vérifier un temps. Même spécification que pc/tg/entrainement.py et app/…/Entrainement.kt ; vecteurs communs :
 * donnees/entrainement/vecteurs.json (vérifiés par test/tirage.mjs). Les badges (dessins 14 × 14, mêmes couleurs que
 * pc/tg/badges.py et Badges.kt) sont dessinés en SVG.
 */
import { Hasard } from "./tirage.js";

export const BASE = 1_000_000;
export const MAX_PAR_GRAINE = 100;
export const FAMILLES = ["explorateur", "batisseur", "demenageur", "nettoyeur", "lecteur", "detective", "plombier", "cuisinier"];
export const ECHELONS = ["bois", "bronze", "argent", "or", "diamant"];
export const SEUILS = [1, 5, 15, 30, 50];
export const MEDAILLES = ["bronze", "argent", "or", "diamant"];
export const ICONE_MEDAILLE = { bronze: "🥉", argent: "🥈", or: "🥇", diamant: "💎" };

const PIECES = ["cave", "grenier", "cuisine", "salon", "jardin", "atelier", "bureau", "chambre", "garage", "veranda", "bibliotheque", "couloir"];
const COINS = ["coffre", "placard", "tiroir", "armoire", "etagere", "malle", "panier", "boite"];
const OBJETS = ["pomme", "balle", "cle", "lampe", "livre", "carte", "plume", "bougie", "boussole", "flute", "tambour", "etoile", "coquillage",
  "gomme", "crayon", "bille"];
const MOTS = ["licorne", "dragon", "fusee", "volcan", "pirate", "robot", "comete", "tortue", "cactus", "biscuit", "nuage", "sirene"];

/** Chaque commande et ses équivalents (Windows…), pour vérifier que l'enfant l'avait déjà tapée (« vus »). */
export const CMD = {
  cd: ["cd", "set-location", "sl"], ls: ["ls", "dir", "gci", "get-childitem"], pwd: ["pwd", "get-location"],
  mkdir: ["mkdir", "md", "new-item"], touch: ["touch", "new-item", "ni"], cp: ["cp", "copy", "copy-item"],
  mv: ["mv", "move", "move-item"], rm: ["rm", "del", "remove-item"], rmdir: ["rmdir", "rd"], cat: ["cat", "type", "get-content", "gc"],
  head: ["head"], tail: ["tail"], grep: ["grep", "select-string", "sls"], find: ["find"], echo: ["echo", "write-output"],
  wc: ["wc", "measure-object"], sh: ["sh", "bash"], chmod: ["chmod"],
};

/** type : [famille, commandes, par en secondes] */
export const TYPES = {
  exp_chemin: ["explorateur", ["cd"], 15], exp_cle: ["explorateur", ["cd", "ls"], 30],
  bat_pieces: ["batisseur", ["mkdir"], 15], bat_objets: ["batisseur", ["mkdir", "touch"], 25],
  dem_mv: ["demenageur", ["mv"], 20], dem_cp: ["demenageur", ["cp"], 20],
  net_rm: ["nettoyeur", ["rm"], 20], net_rmdir: ["nettoyeur", ["rmdir"], 20], net_rmr: ["nettoyeur", ["rm", "rmdir"], 15],
  lec_cat: ["lecteur", ["cat"], 20], lec_head: ["lecteur", ["head"], 20], lec_tail: ["lecteur", ["tail"], 20],
  det_grep: ["detective", ["grep"], 25], det_find: ["detective", ["find"], 25],
  plo_ecrit: ["plombier", ["echo"], 20], plo_ajout: ["plombier", ["echo"], 20], plo_tuyau: ["plombier", ["grep", "wc"], 30],
  cui_lancer: ["cuisinier", ["sh"], 20], cui_ecrire: ["cuisinier", ["sh", "chmod", "echo"], 40],
};

function choisir(h, liste, n) {
  const a = [...liste];
  for (let i = 0; i < n; i++) {
    const j = i + h.entier(a.length - i);
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a.slice(0, n);
}

/** Les paramètres de l'exercice (graine en hexadécimal, compteur). */
export function generer(typ, valeur, k) {
  const h = new Hasard(valeur, BASE + k);
  const p = {};
  if (["exp_chemin", "exp_cle", "det_find"].includes(typ)) {
    p.pieces = choisir(h, PIECES, 3);
    p.coins = choisir(h, COINS, 2);
    p.i = h.entier(3);
    p.j = h.entier(2);
    if (typ === "det_find") p.objet = choisir(h, OBJETS, 1)[0];
  } else if (typ === "bat_pieces") p.pieces = choisir(h, PIECES, 2);
  else if (typ === "bat_objets") { p.pieces = choisir(h, PIECES, 1); p.objets = choisir(h, OBJETS, 2); }
  else if (typ === "dem_mv" || typ === "dem_cp") { p.pieces = choisir(h, PIECES, 2); p.objets = choisir(h, OBJETS, 1); }
  else if (typ === "net_rm") { p.pieces = choisir(h, PIECES, 1); p.objets = choisir(h, OBJETS, 1); p.n = 2 + h.entier(3); }
  else if (typ === "net_rmdir") { p.pieces = choisir(h, PIECES, 3); p.objets = choisir(h, OBJETS, 1); }
  else if (typ === "net_rmr") { p.pieces = choisir(h, PIECES, 2); p.objets = choisir(h, OBJETS, 3); }
  else if (typ === "lec_cat") { p.mots = choisir(h, MOTS, 1); p.n = 1 + h.entier(3); }
  else if (typ === "lec_head" || typ === "lec_tail") { p.mots = choisir(h, MOTS, 8); p.n = 2 + h.entier(3); }
  else if (typ === "det_grep") { p.objets = choisir(h, OBJETS, 5); p.mots = choisir(h, MOTS, 6); p.i = h.entier(5); }
  else if (["plo_ecrit", "cui_lancer", "cui_ecrire"].includes(typ)) p.mots = choisir(h, MOTS, 1);
  else if (typ === "plo_ajout") p.mots = choisir(h, MOTS, 4);
  else if (typ === "plo_tuyau") {
    p.objets = choisir(h, OBJETS, 4);
    const n = 8 + h.entier(5);
    p.lignes = Array.from({ length: n }, () => h.entier(4));
    if (!p.lignes.includes(0)) p.lignes[0] = 0;
  } else throw new Error("exercice inconnu : " + typ);
  return p;
}

/** « type|clé=valeurs|… » dans l'ordre des clés (comme le PC et l'appli). */
export function empreinte(typ, p) {
  return [typ, ...Object.keys(p).sort().map((k) => k + "=" + (Array.isArray(p[k]) ? p[k].join(",") : String(p[k])))].join("|");
}

export function reponse(typ, p) {
  switch (typ) {
    case "lec_cat": return p.mots[0];
    case "lec_head": return p.mots[p.n - 1];
    case "lec_tail": return p.mots[7];
    case "det_grep": return p.objets[p.i];
    case "det_find": return p.pieces[p.i];
    case "plo_tuyau": return String(p.lignes.filter((x) => x === 0).length);
    case "cui_lancer": return p.mots[0];
    default: return null;
  }
}

export function medaille(typ, s) {
  const par = TYPES[typ][2];
  return s <= par ? "diamant" : s <= 2 * par ? "or" : s <= 4 * par ? "argent" : "bronze";
}

/** Le temps le plus court plausible pour un exercice (en secondes). */
export const tempsMinimum = (typ) => Math.max(2, TYPES[typ][2] / 5);

/** La semaine ISO (UTC) d'un instant en millisecondes : « 2026-W43 ». */
export function semaine(ms = Date.now()) {
  const d = new Date(ms);
  const j = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
  const jour = j.getUTCDay() || 7;
  j.setUTCDate(j.getUTCDate() + 4 - jour);
  const debut = new Date(Date.UTC(j.getUTCFullYear(), 0, 1));
  const n = Math.ceil(((j - debut) / 86_400_000 + 1) / 7);
  return `${j.getUTCFullYear()}-W${String(n).padStart(2, "0")}`;
}
export const semainePrecedente = (ms = Date.now()) => semaine(ms - 7 * 86_400_000);

/** L'échelon atteint (0…4, ou -1) : n réussites, et pour le Diamant une médaille d'or (ou de diamant). */
export function echelonDe(n, ors = 0) {
  let k = -1;
  SEUILS.forEach((s, i) => { if (n >= s && (i < 4 || ors >= 1)) k = i; });
  return k;
}

/** L'enfant a-t-il déjà tapé les commandes de cet exercice ? */
export function commandesConnues(typ, vus) {
  const s = vus instanceof Set ? vus : new Set(Array.isArray(vus) ? vus : []);
  return TYPES[typ][1].every((c) => CMD[c].some((x) => s.has(x)));
}

// ---------------------------------------------------------------- les badges (mêmes dessins que le jeu)
export const COULEURS = {
  bois: ["#3a2a1a", "#76583a", "#987654", "#efe0c4", "#4a3522"],
  bronze: ["#6b3510", "#d0782a", "#f6ad62", "#fff3e0", "#7a3c0c"],
  argent: ["#4a525e", "#aab5c2", "#e6edf4", "#323a47", "#6b7685"],
  or: ["#6b4700", "#e8b71c", "#fff27a", "#4f3300", "#a36f00"],
  diamant: ["#0b4a66", "#3fcfff", "#d2f8ff", "#06324a", "#1a7fae"],
  cache: ["#3a3a44", "#5a5a66", "#6e6e7a", "#8a8a96", "#4a4a55"],
};
const FORME = ["...oooooooo...", "..ohhhhhhhhfo.", ".ohhffffffffo.", "ohhffffffffffo", "ohfffffffffffo", "ohfffffffffffo", "ohfffffffffffo",
  "ohfffffffffffo", "ohfffffffffffo", "offfffffffffo.", ".offfffffffo..", "..offfffffo...", "...offfffo....", ".....ooo......"];
const ICONES = {
  explorateur: ["...ii...", "...ii...", "..ikki..", "iiikkiii", "iiiKKiii", "..iKKi..", "...ii...", "...ii..."],
  batisseur: ["...ii...", "..iiii..", ".iiiiii.", "iiiiiiii", ".iiiiii.", ".iikkii.", ".iikkii.", ".iikkii."],
  demenageur: ["....i...", "....ii..", "iiiiiii.", "iiiiiiii", "iiiiiii.", "....ii..", "....i...", "........"],
  nettoyeur: [".......i", "......i.", ".....i..", "....i...", "..kkkk..", ".iiiiii.", "iiiiiii.", "i.i.i.i."],
  lecteur: ["iii..iii", "iiiiiiii", "ikkiikki", "iiiiiiii", "ikkiikki", "iiiiiiii", "ikkiikki", "iiiiiiii"],
  detective: ["..iiii..", ".i....i.", "i......i", "i......i", ".i....i.", "..iiiik.", "......kk", ".......k"],
  plombier: ["iiiiii..", "kkkkkii.", "iiiiiii.", ".....ii.", ".....ii.", "....iiii", "........", ".....k.."],
  cuisinier: [".i.ii.i.", "iiiiiiii", "iiiiiiii", ".iiiiii.", "..iiii..", "..kkkk..", "..iiii..", "..iiii.."],
  cache: ["..iiii..", ".ii..ii.", ".....ii.", "....ii..", "...ii...", "...ii...", "........", "...ii..."],
};
const ETINCELLES = [[1, 12], [0, 12], [2, 12], [1, 11], [1, 13]];

export function grille(famille, echelon) {
  const cache = !famille || !ECHELONS.includes(echelon) || !ICONES[famille];
  const c = COULEURS[cache ? "cache" : echelon];
  const pal = { o: c[0], f: c[1], h: c[2], i: c[3], k: c[4], K: c[4] };
  const g = FORME.map((l) => [...l].map((x) => pal[x] || null));
  ICONES[cache ? "cache" : famille].forEach((l, y) => [...l].forEach((x, xx) => { if (x !== ".") g[3 + y][3 + xx] = pal[x]; }));
  if (echelon === "diamant" && !cache) for (const [y, x] of ETINCELLES) g[y][x] = "#ffffff";
  return g;
}

/** Le badge en SVG (pixels nets). */
export function svgBadge(famille, echelon, taille = 4, etiquette = "") {
  const g = grille(famille, echelon);
  const parCouleur = new Map();
  g.forEach((l, y) => l.forEach((c, x) => { if (c) parCouleur.set(c, (parCouleur.get(c) || "") + `M${x} ${y}h1v1h-1z`); }));
  const rects = [...parCouleur].map(([c, d]) => `<path fill="${c}" d="${d}"/>`).join("");
  const role = etiquette ? `role="img" aria-label="${etiquette.replace(/"/g, "&quot;")}"` : `aria-hidden="true"`;
  return `<svg class="badge-px" viewBox="0 0 14 14" width="${14 * taille}" height="${14 * taille}" shape-rendering="crispEdges" ${role}>${rects}</svg>`;
}

// ---------------------------------------------------------------- l'état d'une partie (etat.entrainement)
export function etatVide() {
  return { familles: {}, records: {} };
}

export function fam(e, f) {
  const x = (e.familles[f] ??= {});
  for (const k of ["n", ...MEDAILLES]) x[k] = Math.max(0, Math.floor(Number(x[k]) || 0));
  return x;
}

export function echelon(e, f) {
  const x = fam(e, f);
  return echelonDe(x.n, x.or + x.diamant);
}

/** Les titres d'une partie, du plus beau au plus simple : [{ id, famille?, echelon?, couleur }]. */
export function titres(e, stars = []) {
  const out = [];
  const ech = Object.fromEntries(FAMILLES.map((f) => [f, echelon(e, f)]));
  if (FAMILLES.every((f) => ech[f] >= 3)) out.push({ id: "legende", couleur: "arc" });
  for (const f of stars) if (FAMILLES.includes(f)) out.push({ id: "star", famille: f, couleur: "#ffaf00" });
  if (FAMILLES.filter((f) => ech[f] >= 1).length >= 6) out.push({ id: "touche", couleur: "#ff87ff" });
  const ordre = [...FAMILLES].sort((a, b) => (ech[b] - ech[a]) || (fam(e, b).n - fam(e, a).n) || (FAMILLES.indexOf(a) - FAMILLES.indexOf(b)));
  for (const f of ordre) if (ech[f] >= 1) out.push({ id: "famille", famille: f, echelon: ECHELONS[ech[f]], couleur: COULEURS[ECHELONS[ech[f]]][2] });
  if (FAMILLES.some((f) => fam(e, f).n > 0)) out.push({ id: "apprenti", couleur: "#c8b8a0" });
  return out;
}
