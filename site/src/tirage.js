/**
 * Anti-triche : le serveur refait le tirage d'une apparition à partir de (graine, compteur).
 * Même spécification que pc/tg/tirage.py et app/…/Tirage.kt (vecteurs communs :
 * donnees/anti_triche/vecteurs.json). Le générateur travaille en BigInt (entiers 64 bits exacts).
 */
import D from "./tirage_donnees.js";

const M64 = (1n << 64n) - 1n;
export const TIRAGE = D;
export const MAX_APPARITIONS = D.max_apparitions;
export const PAR_NOM_T = Object.fromEntries(D.especes.map((e) => [e.nom, e]));
const PUBLIQUES_T = D.especes.filter((e) => !e.secrete);
const ABYSSOR = D.especes.find((e) => e.id === "abyssor");

export class Hasard {
  constructor(valeur, compteur) {
    this.etat = (BigInt("0x" + valeur.slice(0, 16)) ^ ((BigInt(compteur) + 1n) * 0xD1B54A32D192ED03n & M64)) & M64;
  }
  suivant() {
    this.etat = (this.etat + 0x9E3779B97F4A7C15n) & M64;
    let z = this.etat;
    z = ((z ^ (z >> 30n)) * 0xBF58476D1CE4E5B9n) & M64;
    z = ((z ^ (z >> 27n)) * 0x94D049BB133111EBn) & M64;
    return z ^ (z >> 31n);
  }
  entier(n) {
    return Number(this.suivant() % BigInt(n));
  }
  pondere(poids) {
    const r = this.entier(poids.reduce((a, b) => a + b, 0));
    let cumul = 0;
    for (let i = 0; i < poids.length; i++) {
      cumul += poids[i];
      if (r < cumul) return i;
    }
    return poids.length - 1;
  }
}

/** round() de Python sur des valeurs positives à une ou trois décimales (jamais à égalité ici). */
const arrondi = (x) => Math.round(x);

function variante(e, vid) {
  return e.variantes.find((v) => v.id === vid) || e.variantes[0];
}

export function noteEntiere(e, vid, q, shiny) {
  const p = D.rarete.poids;
  const score = arrondi(variante(e, vid).score * 1000);
  const n = 140 * p.stats * q + 140 * p.variante * score + 10000 * p.puissance * (e.puissance - 1)
    + 140000 * p.bonus_shiny * (shiny ? 1 : 0);
  return Math.min(1000, Math.floor((n + 7000) / 14000));
}

export function rareteEntiere(e, note10) {
  if (D.rarete.speciales[e.id]) return D.rarete.speciales[e.id];
  let nom = "commune";
  for (const [seuil, palier] of D.rarete.paliers) if (note10 >= arrondi(seuil * 10)) nom = palier;
  return nom;
}

/** Le tirage complet : { e, champs } (champs = ce que l'individu doit contenir). */
export function tirer(valeur, compteur, abyssorPermis = false) {
  const h = new Hasard(valeur, compteur);
  let e = PUBLIQUES_T[h.pondere(PUBLIQUES_T.map((x) => D.poids_frequence[x.frequence]))];
  let v = e.variantes[h.pondere(e.variantes.map((x) => arrondi(x.chance * 10)))].id;
  const shiny = h.entier(D.chance_shiny) === 0;
  if (h.entier(15) === 0 && abyssorPermis) {
    e = ABYSSOR;
    v = "classique";
  }
  const q = h.entier(1001);
  const iv = {};
  for (const k of Object.keys(e.stats)) {
    const bruit = h.entier(161) + h.entier(161) + h.entier(161) - 240;
    const x = 31 * (q + bruit);
    iv[k] = x <= 0 ? 0 : Math.min(31, Math.floor((x + 500) / 1000));
  }
  const marque = D.marques[h.entier(D.marques.length)];
  const humeur = D.humeurs[h.entier(D.humeurs.length)];
  const taille10 = Math.floor((arrondi(e.taille_cm * 10) * (800 + h.entier(451)) + 500) / 1000);
  const stade = D.stades[h.pondere(D.poids_stades)];
  const teinte = 150 + h.entier(701);
  const note10 = noteEntiere(e, v, q, shiny);
  const nb = Object.keys(iv).length;
  const somme = Object.values(iv).reduce((a, b) => a + b, 0);
  const champs = {
    espece: e.nom, variante: v, shiny, marque, humeur, taille: taille10 / 10, qualite: q / 1000,
    potentiel: Math.floor((200 * somme + 31 * nb) / (62 * nb)),
    stats: Object.fromEntries(Object.entries(e.stats).map(([k, b]) => [k, b + Math.floor(iv[k] / 2)])),
    note: note10 / 10, rarete: rareteEntiere(e, note10), stade,
  };
  if (shiny) champs.teinte = teinte / 1000;
  return { e, champs };
}

/**
 * Compare une capture envoyée par un appareil au tirage refait par le serveur.
 * Renvoie la liste des champs qui ne correspondent pas (vide = conforme).
 */
export function differences(c, champs) {
  const ecarts = [];
  const pareil = (k, a, b) => { if (a !== b) ecarts.push(k); };
  pareil("espece", c.espece, champs.espece);
  pareil("variante", c.variante ?? "classique", champs.variante);
  pareil("shiny", c.shiny === true, champs.shiny);
  pareil("marque", c.marque, champs.marque);
  pareil("humeur", c.humeur, champs.humeur);
  pareil("taille", Math.round(Number(c.taille) * 10), Math.round(champs.taille * 10));
  pareil("qualite", Math.round(Number(c.qualite) * 1000), Math.round(champs.qualite * 1000));
  pareil("potentiel", Number(c.potentiel), champs.potentiel);
  for (const [k, v] of Object.entries(champs.stats)) pareil("stats." + k, Number(c.stats?.[k]), v);
  if (c.rarete !== undefined) pareil("rarete", c.rarete, champs.rarete);
  if (champs.shiny) pareil("teinte", Math.round(Number(c.teinte) * 1000), Math.round(champs.teinte * 1000));
  return ecarts;
}

// ---------------------------------------------------------------- évolution après la capture
/** XP pour passer au stade suivant (comme pc/tg/equipe.py et Equipe.kt) ; 2 XP par commande tapée. */
export const SEUILS = { bebe: 100, enfant: 250, ado: 600, adulte: 1500 };
export const XP_PAR_SECONDE_MAX = 2;

/** XP qu'il faut au minimum pour aller du stade « de » au stade « a ». */
export function xpPourGrandir(de, a) {
  const i = D.stades.indexOf(de);
  const j = D.stades.indexOf(a);
  if (i < 0 || j < 0) return Infinity;
  let xp = 0;
  for (let k = i; k < j; k++) xp += SEUILS[D.stades[k]];
  return xp;
}

/** Le stade le plus avancé plausible, partant de « de », après `secondes` de jeu. */
export function stadePlausible(de, voulu, secondes) {
  const i = D.stades.indexOf(de);
  const j = D.stades.indexOf(voulu);
  if (i < 0) return de;
  if (j <= i) return de;
  let s = de;
  for (let k = i + 1; k <= j; k++) {
    if (xpPourGrandir(de, D.stades[k]) <= XP_PAR_SECONDE_MAX * Math.max(0, secondes)) s = D.stades[k];
  }
  return s;
}
