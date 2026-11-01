/**
 * Terminagotchi — les badges de la Guilde des Bâtisseurs Libres sur le site, et le PSEUDO coloré (décision du
 * 1er novembre : la couleur du badge choisi comme titre va sur le pseudo de l'enfant, jamais sur le nom de la créature).
 *
 * Même règle que le jeu (pc/tg/guilde.py, Guilde.kt), mêmes données (guilde_donnees.js, fabriqué depuis
 * donnees/guilde.json par donnees/guilde/outils/fiches_guilde.py). Le serveur ne croit que ce qu'il peut vérifier :
 *  - « Artisan » : recalculé ici à partir de la progression synchronisée (leçons de la Guilde réussies, contribution
 *    d'entraînement prête), comme les grades de la salle d'entraînement ; un grade envoyé par le jeu est ignoré ;
 *  - « Contributeur » : SEULEMENT la liste des crédits du dépôt (copiée dans guilde_donnees.js au déploiement),
 *    cherchée avec le pseudo du compte ; jamais une déclaration du jeu.
 * Le jeu n'envoie que l'identifiant du titre qu'il montre (« artisan:kilo ») : le pseudo n'est coloré que si le
 * serveur a lui-même vérifié ce badge.
 */
import DONNEES from "./guilde_donnees.js";

export const BADGES = ["artisan", "contributeur"];
export const CREDITS = DONNEES.credits;           // (un tableau : les tests y ajoutent des contributeurs)
const P = (b) => DONNEES.badges[b].paliers;
export const LECONS = DONNEES.badges.artisan.lecons;

/** Couleurs du pseudo : lisibles sur les fonds sombres du site (contraste vérifié par les tests). */
export const COULEUR = Object.fromEntries(BADGES.map((b) => [b, DONNEES.badges[b].couleur]));

export function palierArtisan(lecons, contribution) {
  let k = -1;
  for (const [i, p] of P("artisan").entries()) {
    if (lecons >= p.lecons && (contribution || !p.contribution)) k = i;
    else break;
  }
  return k;
}

export function palierContributeur(n) {
  let k = -1;
  for (const [i, p] of P("contributeur").entries()) {
    if (n >= p.n) k = i;
    else break;
  }
  return k;
}

/** Le nombre de contributions acceptées d'un pseudo dans les crédits (sans tenir compte des majuscules), ou 0. */
export function contributionsDe(pseudo, contributeurs = CREDITS) {
  const p = String(pseudo || "").trim().toLowerCase();
  if (!p) return 0;
  for (const x of Array.isArray(contributeurs) ? contributeurs : []) {
    if (x && typeof x === "object" && String(x.pseudo || "").trim().toLowerCase() === p) return Math.max(0, Math.floor(Number(x.contributions) || 0));
  }
  return 0;
}

/** Fusionne la progression de la Guilde envoyée par un appareil (les leçons ne se « défont » pas). */
export function fusionner(avant, envoi) {
  const a = avant && typeof avant === "object" ? avant : {};
  const e = envoi && typeof envoi === "object" ? envoi : {};
  const lecons = new Set((Array.isArray(a.lecons) ? a.lecons : []).filter((l) => LECONS.includes(l)));
  for (const l of Array.isArray(e.lecons) ? e.lecons : []) if (LECONS.includes(l)) lecons.add(l);
  return { lecons: LECONS.filter((l) => lecons.has(l)), contribution: a.contribution === true || e.contribution === true };
}

/** L'échelon du badge « Artisan » d'un état de partie (etat.guilde), ou null. */
export function echelonArtisan(g) {
  const x = fusionner(g, null);
  const k = palierArtisan(x.lecons.length, x.contribution);
  return k >= 0 ? P("artisan")[k].echelon : null;
}

/** L'échelon du badge « Contributeur » d'un pseudo (d'après les crédits seulement), ou null. */
export function echelonContributeur(pseudo, contributeurs = CREDITS) {
  const k = palierContributeur(contributionsDe(pseudo, contributeurs));
  return k >= 0 ? P("contributeur")[k].echelon : null;
}

/** Le badge du titre montré par le jeu (« artisan:kilo » → « artisan »), ou "" : seul le nom du badge est gardé. */
export function badgeDuTitre(titre) {
  const b = typeof titre === "string" ? titre.split(":")[0] : "";
  return BADGES.includes(b) ? b : "";
}

/**
 * Ce que montre le site pour un joueur : { artisan, contributeur } (échelons vérifiés ou null) et `titre`
 * ({ badge, echelon, couleur } quand le titre choisi dans le jeu est un badge de la Guilde que le serveur a vérifié).
 */
export function vitrine(pseudo, titreBadge, echelonA) {
  const ech = { artisan: echelonA || null, contributeur: echelonContributeur(pseudo) };
  const b = BADGES.includes(titreBadge) ? titreBadge : "";
  return { ...ech, titre: b && ech[b] ? { badge: b, echelon: ech[b], couleur: COULEUR[b] } : null };
}

export const textes = (lang) => DONNEES.textes[lang] || DONNEES.textes.fr;
