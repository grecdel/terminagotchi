/**
 * La salle d'entraînement côté site : le serveur refait le tirage d'un exercice à partir de (graine, compteur) pour
 * vérifier un temps. Même spécification que pc/tg/entrainement.py et app/…/Entrainement.kt ; vecteurs communs :
 * donnees/entrainement/vecteurs.json (vérifiés par test/tirage.mjs). Les badges (écusson 14 × 14, ou complet 18 × 28 avec
 * les galons du grade et les étoiles ; mêmes dessins et couleurs que pc/tg/badges.py et Badges.kt) sont dessinés en SVG.
 */
import { Hasard } from "./tirage.js";

export const BASE = 1_000_000;
export const MAX_PAR_GRAINE = 100;
export const FAMILLES = ["explorateur", "batisseur", "demenageur", "nettoyeur", "lecteur", "detective", "plombier", "cuisinier"];
/** Les grades (des tailles d'informatique), leurs seuils, et les étoiles vers le grade suivant (★, ★★, ★★★). */
export const ECHELONS = ["bit", "octet", "kilo", "mega", "giga", "tera", "peta", "exa"];
export const SEUILS = [1, 5, 15, 30, 50, 100, 200, 400];
/** Médailles de diamant demandées par grade (Téra 3, Péta 6, Exa 10) ; l'Exa demande aussi chaque exercice de la famille. */
export const DIAMANTS = [0, 0, 0, 0, 0, 3, 6, 10];
export const ETOILES = [[2, 3, 4], [8, 10, 13], [19, 23, 27], [35, 40, 45], [63, 75, 88], [125, 150, 175], [250, 300, 350], [600, 800, 1000]];
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

/** Le grade atteint (0…7, ou -1) : n réussites, pour le Giga une médaille d'or (ou de diamant), puis des médailles de
 * diamant (DIAMANTS), et pour l'Exa chaque exercice de la famille réussi au moins une fois. On monte dans l'ordre. */
export function echelonDe(n, ors = 0, diamants = 0, tousTypes = false) {
  let k = -1;
  for (const [i, s] of SEUILS.entries()) {
    if (n >= s && (i < 4 || ors >= 1) && diamants >= DIAMANTS[i] && (i < 7 || tousTypes)) k = i;
    else break;
  }
  return k;
}

/** L'enfant a-t-il déjà tapé les commandes de cet exercice ? */
export function commandesConnues(typ, vus) {
  const s = vus instanceof Set ? vus : new Set(Array.isArray(vus) ? vus : []);
  return TYPES[typ][1].every((c) => CMD[c].some((x) => s.has(x)));
}

// ---------------------------------------------------------------- les badges (mêmes dessins que le jeu)
export const COULEURS = {
  bit: ["#0d3b1e", "#2f9e4f", "#86e89a", "#eaffe9", "#17602f"],
  octet: ["#08404d", "#22b0c6", "#a6f3ff", "#062f3a", "#127688"],
  kilo: ["#152a78", "#4072f0", "#b1c8ff", "#f0f4ff", "#2240b0"],
  mega: ["#3d0f60", "#a050e6", "#e2b8ff", "#fff0ff", "#5e1f92"],
  giga: ["#6b4700", "#e8b71c", "#fff27a", "#4f3300", "#a36f00"],
  tera: ["#4b3a8c", "#dfe9ff", "#ffffff", "#4b3a8c", "#ff6fd8"],
  peta: ["#4a0a18", "#e8344e", "#ff9aa8", "#fff0f0", "#8a1028"],
  exa: ["#0b0626", "#3a1f9e", "#9f8bff", "#ffe36e", "#ff7ad9"],
  cache: ["#3a3a44", "#5a5a66", "#6e6e7a", "#8a8a96", "#4a4a55"],
};
const FIXES = { d: "#4a3000", e: "#d9a41a", g: "#fff27a", q: "#0b3f55", r: "#3fd6ff", s: "#fff6c8", z: "#0c0c10", y: "#4a4a5e", x: "#262630", p: "#d8d8e0", "1": "#ff5a6e", "2": "#ffa63d", "3": "#ffe94a", "4": "#5cff86", "5": "#4ad8ff", "6": "#b46cff", n: "#1a0d33", v: "#ffffff", w: "#ffffff", u: "#8ff7ff", o: "#cfd8ff", L: "#fff3b0", P: "#ff9f43", "~": "#14214f", ":": "#5a2470", "*": "#ffffff", "+": "#7f9cff", S: "#ffd84a", W: "#ffffff" };
const ETOILE_ON = "#ffd84a", ETOILE_OFF = "#3c3c4a";
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
/** Les galons de chaque grade : [première ligne, lignes de 18 pixels], derrière l'écusson (voir pc/tg/badges.py). */
const GALONS = {
  bit: [16, [
    ".......aaa........",
    ".....aabbbaa......",
    "...aabbcccbbaa....",
    "..abbccaaaccbba...",
    ".abccaa...aaccba..",
    ".acaa.......aaca..",
    "..a...........a...",
  ]],
  octet: [16, [
    ".......aaa........",
    ".....aabbbaa......",
    "...aabbcccbbaa....",
    "..abbccaaaccbba...",
    ".abccaabbbaaccba..",
    ".acaabbcccbbaaca..",
    "..abbccaaaccbba...",
    ".abccaa...aaccba..",
    ".acaa.......aaca..",
    "..a...........a...",
  ]],
  kilo: [16, [
    ".......aaa........",
    ".....aabbbaa......",
    "...aabbcccbbaa....",
    "..abbccaaaccbba...",
    ".abccaabbbaaccba..",
    ".acaabbcccbbaaca..",
    "..abbccaaaccbba...",
    ".abccaabbbaaccba..",
    ".acaabbcccbbaaca..",
    "..abbccaaaccbba...",
    ".abccaa...aaccba..",
    ".acaa.......aaca..",
  ]],
  mega: [7, [
    "d................d",
    "gd..............dg",
    "ed..............de",
    "egd............dge",
    "ed..............de",
    "egd............dge",
    "ed..............de",
    "egd............dge",
    "ed..............de",
    "ded....aaa.....ded",
    ".ded.aabbbaa..ded.",
    "..daabbcccbbaaed..",
    "..abbccaaaccbba...",
    ".abccaabbbaaccba..",
    ".acaabbcccbbaaca..",
    "..abbccaaaccbba...",
    ".abccaabbbaaccba..",
    ".acaabbcccbbaaca..",
    "..abbccaaaccbba...",
    ".abccaa...aaccba..",
    ".acaa.......aaca..",
  ]],
  giga: [4, [
    "q................q",
    "sq..............qs",
    "rsq............qsr",
    "rrq............qrr",
    "rsq............qsr",
    "rrq............qrr",
    "rsq............qsr",
    "rrq............qrr",
    "rsq............qsr",
    "rrq............qrr",
    "rsq............qsr",
    "rrq............qrr",
    "qrrq...aaa....qrrq",
    ".qrrqaabbbaa.qrrq.",
    "..qaabpcpcpbaarq..",
    "..abbzyyyyyzbba...",
    ".abcczxsxxxzccba..",
    ".acaazxxxxxzaaca..",
    "..abbcpapapcbba...",
    ".abccaabbbaaccba..",
    ".acaabbcccbbaaca..",
    "..abbccaaaccbba...",
    ".abccaa...aaccba..",
    ".acaa.......aaca..",
  ]],
  tera: [4, [
    "1111n........n1111",
    "1v1n..........n1v1",
    "1vn............nv1",
    "22n............n22",
    "2vn............nv2",
    "33n............n33",
    "3vn............nv3",
    "33n............n33",
    "4vn............nv4",
    "44n............n44",
    "5vn............nv5",
    "55n............n55",
    "n55n...aaa....n55n",
    ".n66naabbbaa.n66n.",
    "..naabpcpcpbaa6n..",
    "..abbzyyyyyzbba...",
    ".abcczxuwuxzccba..",
    ".acaazxuuuxzaaca..",
    "..abbcpapapcbba...",
    ".abccaabbbaaccba..",
    ".acaabbcccbbaaca..",
    "..abbccaaaccbba...",
    ".abccaanwnaaccba..",
    ".acaa.nuwun.aaca..",
  ]],
  peta: [4, [
    "1111n........n1111",
    "1v1n..........n1v1",
    "1vn............nv1",
    "22n............n22",
    "2vn............nv2",
    "33n............n33",
    "3vn............nv3",
    "33n............n33",
    "4vn............nv4",
    "44n............n44",
    "5vn............nv5",
    "55n............n55",
    "n55n...aaa....n55n",
    ".n66naabbbaa.n66n.",
    "o.naabpcpcpbaa6n.o",
    "..abbzyyyyyzbba...",
    "oabcczxuwuxzccba.o",
    "LPcaazxuuuxzaaca..",
    "PPabbcpapapcbba..o",
    "oabccaabbbaaccba.o",
    "oacaabbcccbbaacaLP",
    "..abbccaaaccbba.PP",
    "oabccaanwnaaccbaoo",
    ".acaa.nuwun.aaca..",
  ]],
  exa: [0, [
    "..:~~*~~:~~*~:~~..",
    ".~~:~~:~~:~:~~:~+.",
    "~+~~:~~:~:~*:~~:~~",
    "*~:~~:~:~~:~~:~~:~",
    "1111n:~~:~~:~n1111",
    "1v1n~~:~~:~~:~n1v1",
    "1vn~:~~:~~:~:~~nv1",
    "22n~~:~~:~:~~:~n22",
    "2vn:~~:~:~~:~~:nv2",
    "33n~:~:~~:~~:~~n33",
    "3vn~:~~:~~:~~:~nv3",
    "33n~~:~~:~~:~:~n33",
    "4vn:~~:~~:~:~~:nv4",
    "44n~:~~:~:~~:~~n44",
    "5vn~~:~:~~:~~:*nv5",
    "55n:~:~~:~~:~~:n55",
    "n55n~~:aaa~~:*n55n",
    "~n66naabbbaa:n66n~",
    "o~naabpcpcpbaa6n:o",
    ":~abbzyyyyyzbba~~:",
    "oabcczxuwuxzccba~o",
    "LPcaazxuuuxzaaca~~",
    "PPabbcpapapcbba~:o",
    "oabccaabbbaaccba~o",
    "oacaabbcccbbaacaLP",
    "~~abbccaaaccbba~PP",
    "oabccaanwnaaccbaoo",
    ".acaa~nuwun~aaca..",
  ]],
};
/** Par-dessus l'écusson (Péta, Exa) : l'étoile posée. */
const DEVANT = {
  peta: [3, [
    "........s.........",
    "........S.........",
    "......sSWSs.......",
    "........S.........",
  ]],
  exa: [3, [
    "........s.........",
    "........S.........",
    "......sSWSs.......",
    "........S.........",
  ]],
};
const ETOILE = ["..x..", ".xxx.", "xxxxx", ".x.x."];

export function grille(famille, echelon) {
  const cache = !famille || !ECHELONS.includes(echelon) || !ICONES[famille];
  const c = COULEURS[cache ? "cache" : echelon];
  const pal = { o: c[0], f: c[1], h: c[2], i: c[3], k: c[4], K: c[4] };
  const g = FORME.map((l) => [...l].map((x) => pal[x] || null));
  ICONES[cache ? "cache" : famille].forEach((l, y) => [...l].forEach((x, xx) => { if (x !== ".") g[3 + y][3 + xx] = pal[x]; }));
  if (ECHELONS.indexOf(echelon) >= 4 && !cache) for (const [y, x] of ETINCELLES) g[y][x] = "#ffffff";
  return g;
}

function couche(g, echelon, motifs) {
  if (!motifs[echelon]) return g;
  const c = COULEURS[echelon];
  const pal = { ...FIXES, a: c[0], b: c[2], c: c[1] };
  const [y0, lignes] = motifs[echelon];
  lignes.forEach((l, y) => [...l].forEach((x, xx) => { if (x !== ".") g[y0 + y][xx] = pal[x]; }));
  return g;
}

/** Le grade seul : grille 18 × 28 (null = transparent), avec ce qui passe devant l'écusson. */
export function galons(echelon, devant = true) {
  const g = Array.from({ length: 28 }, () => Array(18).fill(null));
  if (!ECHELONS.includes(echelon)) return g;
  couche(g, echelon, GALONS);
  return devant ? couche(g, echelon, DEVANT) : g;
}

/** Le badge complet 18 × 28 : galons, écusson en (2, 4), 3 étoiles au-dessus (0 à 3 allumées). « ??? » : l'écusson gris seul. */
export function ecusson(famille, echelon, etoiles = 0) {
  const cache = !famille || !ECHELONS.includes(echelon) || !ICONES[famille];
  const g = galons(cache ? null : echelon, false);
  grille(famille, echelon).forEach((l, y) => l.forEach((c, x) => { if (c) g[4 + y][2 + x] = c; }));
  if (!cache) couche(g, echelon, DEVANT);
  if (!cache) [0, 6, 12].forEach((x0, i) => ETOILE.forEach((l, y) => [...l].forEach((x, xx) => {
    if (x === "x") g[y][x0 + xx] = i < etoiles ? ETOILE_ON : ETOILE_OFF;
  })));
  return g;
}

/** Les étoiles (0…3) dans le grade k avec n réussites. */
export const etoilesDe = (n, k) => (k < 0 ? 0 : ETOILES[k].filter((s) => n >= s).length);

/** Le badge en SVG (pixels nets) : l'écusson seul, ou complet (galons, étoiles) quand `etoiles` est un nombre. */
export function svgBadge(famille, echelon, taille = 4, etiquette = "", etoiles = null) {
  const g = Number.isInteger(etoiles) ? ecusson(famille, echelon, etoiles) : grille(famille, echelon);
  const w = g[0].length, h = g.length;
  const parCouleur = new Map();
  g.forEach((l, y) => l.forEach((c, x) => { if (c) parCouleur.set(c, (parCouleur.get(c) || "") + `M${x} ${y}h1v1h-1z`); }));
  const rects = [...parCouleur].map(([c, d]) => `<path fill="${c}" d="${d}"/>`).join("");
  const role = etiquette ? `role="img" aria-label="${etiquette.replace(/"/g, "&quot;")}"` : `aria-hidden="true"`;
  return `<svg class="badge-px" viewBox="0 0 ${w} ${h}" width="${w * taille}" height="${h * taille}" shape-rendering="crispEdges" ${role}>${rects}</svg>`;
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

/** Pour l'Exa : chaque exercice de la famille a-t-il été réussi au moins une fois (il a un record) ? */
export function tousTypes(e, f) {
  const recs = e.records && typeof e.records === "object" ? e.records : {};
  return Object.keys(TYPES).filter((typ) => TYPES[typ][0] === f).every((typ) => Object.hasOwn(recs, typ));
}

export function echelon(e, f) {
  const x = fam(e, f);
  return echelonDe(x.n, x.or + x.diamant, x.diamant, tousTypes(e, f));
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
