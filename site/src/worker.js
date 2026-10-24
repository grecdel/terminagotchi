/**
 * Terminagotchi — le site de recensement.
 * Un seul programme Cloudflare Worker : l'API (comptes, synchro, classement, CTF, badges)
 * et les pages du site. Données dans Cloudflare D1 (SQLite).
 */

import BESTIAIRE from "./bestiaire.js";

const DEPOT = "https://github.com/grecdel/terminagotchi-android";
const STATS = ["Intelligence", "Agilité", "Force", "Endurance"];
const COURT = { Intelligence: "INT", "Agilité": "AGI", Force: "FOR", Endurance: "END" };
const COULEUR = { Intelligence: 39, "Agilité": 78, Force: 203, Endurance: 221 };
const STADES = ["Œuf", "Bébé", "Ado", "Adulte"];
const FORMES = { Intelligence: "Hacker", Force: "Titan", "Agilité": "Éclair", Endurance: "Carapace" };
const ESPECES = BESTIAIRE.especes.map((e) => e.nom);
const PAR_NOM = Object.fromEntries(BESTIAIRE.especes.map((e) => [e.nom, e]));
const PAR_ID = Object.fromEntries(BESTIAIRE.especes.map((e) => [e.id, e]));
const MARQUES = new Set(BESTIAIRE.marques);
const HUMEURS = new Set(BESTIAIRE.humeurs);
const COULEUR_RARETE = { commune: "#b0b0c0", "peu commune": "#5fd787", rare: "#5fafff", "légendaire": "#ffaf00" };
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
    "SELECT j.* FROM cles c JOIN joueurs j ON j.id = c.joueur WHERE c.empreinte = ?",
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

// ====================================================================== synchro

/**
 * Fusionne ce qu'envoie un appareil dans l'état commun de la créature.
 *  - compteurs (xp, stats…) : on AJOUTE ce que l'appareil a gagné depuis sa dernière synchro
 *  - ensembles (commandes goûtées, compétences) : union
 *  - collection : maximum par espèce · records : meilleur temps
 *  - nom, faim : la valeur la plus récente gagne · caractère, forme : la première gagne
 */
function fusionner(etat, envoi, appareil) {
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
      && PAR_NOM[c.espece] && MARQUES.has(c.marque) && HUMEURS.has(c.humeur);
    if (!ok) continue;
    const st = {};
    for (const k of ["PV", "ATK", "DEF", "VIT", "INT"]) st[k] = entier(c.stats?.[k], 200);
    e.captures.push({
      id: c.id, espece: c.espece, shiny: c.shiny === true, date: entier(c.date, 4e12), marque: c.marque,
      humeur: c.humeur, taille: Math.max(0, Math.min(1000, Number(c.taille) || 0)), potentiel: entier(c.potentiel, 100),
      stats: st, zone: typeof c.zone === "string" && /^[a-z/]{0,60}$/.test(c.zone) ? c.zone : "",
    });
    connues.add(c.id);
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
    return json({ pseudo, cle, profil: "/joueur/" + pseudo });
  }

  if (chemin === "/api/lier" && m === "POST") {
    if (!(await limite(env, "lier:" + ip, 10))) return erreur("Trop d'essais, réessaie dans une minute.", 429);
    const b = await corps(requete);
    const code = String(b?.code || "").trim().toUpperCase();
    const appareil = APPAREILS.includes(b?.appareil) ? b.appareil : "pc";
    const c = await env.DB.prepare("SELECT * FROM codes WHERE code = ?").bind(code).first();
    if (!c || c.expire < Date.now()) return erreur("Code invalide ou expiré (il dure 10 minutes).", 404);
    await env.DB.prepare("DELETE FROM codes WHERE code = ?").bind(code).run();
    const j = await env.DB.prepare("SELECT pseudo FROM joueurs WHERE id = ?").bind(c.joueur).first();
    const cle = await nouvelleCle(env, c.joueur, appareil);
    return json({ pseudo: j.pseudo, cle });
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
    const alphabet = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";
    const b = new Uint8Array(6);
    crypto.getRandomValues(b);
    const code = [...b].map((x) => alphabet[x % alphabet.length]).join("");
    await env.DB.prepare("DELETE FROM codes WHERE expire < ?").bind(Date.now()).run();
    await env.DB.prepare("INSERT INTO codes (code, joueur, expire) VALUES (?, ?, ?)")
      .bind(code, joueur.id, Date.now() + 10 * 60_000).run();
    return json({ code, expire: 600 });
  }

  if (chemin === "/api/sync" && m === "POST") {
    if (!(await limite(env, "sync:" + joueur.id, 30))) return erreur("Trop de synchros, doucement !", 429);
    const b = await corps(requete);
    if (!b) return erreur("Données illisibles.");
    const appareil = APPAREILS.includes(b.appareil) ? b.appareil : "pc";
    const e = fusionner(lireEtat(joueur), b, appareil);
    await env.DB.prepare("UPDATE joueurs SET etat = ?, xp = ?, niveau = ?, maj = ? WHERE id = ?")
      .bind(JSON.stringify(e), e.xp, niveauDe(e.xp), Date.now(), joueur.id).run();
    const nouveaux = [];
    if (Object.keys(e.appareils).length >= 2) {
      const bd = await donnerBadge(env, joueur.id, "multi", "Multi-plateforme : PC + téléphone");
      if (bd) nouveaux.push(bd);
    }
    return json({ etat: e, badges: nouveaux });
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
    shiny: e.shiny === true, captures: (e.captures || []).length, partage: e.partage?.actif === true,
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

async function ctf(requete, env, pseudo, n, suite) {
  const j = await env.DB.prepare("SELECT id, pseudo FROM joueurs WHERE pseudo = ?").bind(pseudo).first();
  if (!j) return texte("Joueur inconnu. Inscris-toi d'abord depuis l'appli ou le jeu PC (commande : compte creer).\n", 404);
  const secret = await secretServeur(env);
  const f = await drapeauDe(secret, j.id, n);
  const base = `/ctf/${j.pseudo}`;
  const valider = `\nQuand tu l'as : drapeau ${"TG{…}"}  (dans le jeu, sur PC ou téléphone)\n`;
  switch (n) {
    case 1:
      return texte(`🚩 Épreuve 1 : L'en-tête caché\nLe drapeau n'est PAS dans cette page.\nUne réponse web contient aussi des « en-têtes » invisibles…\nIndice : curl -I <adresse de cette page>\n${valider}`,
        200, { "x-drapeau": f });
    case 2:
      if (suite === "cachette") return texte(`Bien joué, petit robot ! Ton drapeau : ${f}\n`);
      return texte(`🚩 Épreuve 2 : Le fichier des robots\nLes sites disent aux robots où ils n'ont PAS le droit d'aller.\nCe fichier s'appelle toujours robots.txt, à la racine du site.\nIndice : curl <adresse du site>/robots.txt\n${valider}`);
    case 3:
      if (requete.method === "POST") {
        const t = await requete.text();
        const mot = new URLSearchParams(t).get("mot");
        if (mot && mot.toLowerCase() === "terminal") return texte(`Le guichet s'ouvre ! Ton drapeau : ${f}\n`);
        return texte("Le guichet reste fermé : mauvais mot.\n", 403);
      }
      return texte(`🚩 Épreuve 3 : Le guichet\nCe guichet n'accepte pas les visites : il faut lui ENVOYER (POST) le bon mot.\nLe mot est écrit à l'envers : lanimret\nIndice : curl -d "mot=..." <adresse de cette page>\n${valider}`);
    case 4: {
      const cookie = requete.headers.get("cookie") || "";
      if (/(^|;\s*)role=admin(\s*;|$)/.test(cookie)) return texte(`Bienvenue, « admin »… (le serveur t'a cru !) Ton drapeau : ${f}\n`);
      return texte(`🚩 Épreuve 4 : Le cookie de confiance\nTu es un simple « visiteur » : regarde le cookie que je t'envoie (curl -i).\nSeuls les « admin » voient le drapeau…\nIndice : curl -b "role=..." <adresse de cette page>\n${valider}`,
        200, { "set-cookie": "role=visiteur; Path=" + base + "/4" });
    }
    case 5:
      return json({
        epreuve: "5 : La boîte JSON",
        aide: "Le drapeau est rangé quelque part là-dedans. Astuce sur PC : curl <adresse> | python3 -m json.tool",
        tiroirs: { haut: { vide: true }, milieu: { chaussettes: 12, boite: { couvercle: "rouge", contenu: { secret: f } } }, bas: [] },
      });
    default:
      return texte("Il n'y a que 5 épreuves.\n", 404);
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

function svgCreature(niveau, forme, stats, taille = 8, shiny = false) {
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
  return `<svg class="creature" viewBox="0 0 ${w} ${rows.length}" width="${w * taille}" height="${rows.length * taille}" shape-rendering="crispEdges" role="img" aria-label="créature">${rects}</svg>`;
}

const CSS = `
:root{--fond:#14141f;--carte:#1e1e2e;--bord:#3a3a55;--texte:#e6e6e6;--doux:#9a9ab0;--vert:#5fd787;--rose:#ff87ff;--jaune:#ffd75f;--bleu:#87afff}
*{box-sizing:border-box}
body{margin:0;background:var(--fond);color:var(--texte);font:16px/1.5 ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}
a{color:var(--bleu)}
header{border-bottom:1px solid var(--bord);background:#181826}
nav{max-width:960px;margin:0 auto;padding:12px 16px;display:flex;gap:18px;align-items:center;flex-wrap:wrap}
nav .logo{color:var(--rose);font-weight:bold;text-decoration:none;font-size:18px}
nav a{text-decoration:none}
main{max-width:960px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:28px;margin:8px 0 4px}h2{font-size:20px;margin:32px 0 12px;color:var(--jaune)}
.doux{color:var(--doux)}
.carte{background:var(--carte);border:1px solid var(--bord);border-radius:16px;padding:18px}
.grille{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr))}
.hero{display:flex;gap:24px;align-items:center;flex-wrap:wrap}
.btn{display:inline-block;background:#5f5fd7;color:#fff;text-decoration:none;padding:10px 16px;border-radius:12px;margin:6px 8px 6px 0}
.btn.vert{background:#2f7d50}
table{width:100%;border-collapse:collapse}
td,th{padding:8px 6px;border-bottom:1px solid var(--bord);text-align:left}
th{color:var(--doux);font-weight:normal;font-size:13px}
td.num{text-align:right}
.badge{display:inline-flex;gap:8px;align-items:center;background:#26263a;border:1px solid var(--bord);border-radius:999px;padding:6px 12px;margin:4px 6px 4px 0;text-decoration:none;color:var(--texte)}
.badge.verifie{border-color:#2f7d50}
.barre{height:8px;background:#33334a;border-radius:4px;overflow:hidden}.barre>i{display:block;height:100%;background:var(--vert)}
code,pre{background:#11111b;border-radius:8px}
code{padding:2px 6px}
pre{padding:12px;overflow-x:auto}
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
.capture{text-align:left}
.capture.shiny{border-color:#ffd75f;box-shadow:0 0 18px #ffd75f44}
.capture .marque{font-size:14px;margin:6px 0}
.filtres a{margin-right:10px;font-size:14px}
.stats-b{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;text-align:center}
.stats-b div{background:#26263a;border-radius:8px;padding:6px 0}
@media (max-width:600px){h1{font-size:22px}td,th{padding:6px 3px;font-size:14px}}
`;

function page(titre, contenu, description = "Terminagotchi : la créature qui se nourrit de tes commandes et t'apprend le terminal.", statut = 200) {
  return new Response(`<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${echapper(titre)} · Terminagotchi</title><meta name="description" content="${echapper(description)}">
<style>${CSS}</style></head><body>
<header><nav><a class="logo" href="/">▞ Terminagotchi</a><a href="/classement">Classement</a><a href="/bestiaire">Bestiaire</a><a href="/captures">Captures</a><a href="/ctf">CTF web</a><a href="/#telecharger">Télécharger</a></nav></header>
<main>${contenu}</main></body></html>`, { status: statut, headers: { "content-type": "text/html; charset=utf-8" } });
}

function ligneClassement(j, i) {
  const forme = j.forme ? FORMES[j.forme] : "";
  return `<tr><td>${i + 1}</td><td><a href="/joueur/${encodeURIComponent(j.pseudo)}">${echapper(j.pseudo)}</a></td>
<td>${echapper(j.nom)} <span class="doux">${echapper(STADES[stadeDe(j.niveau)])} ${echapper(forme)}</span></td>
<td class="num">niv. ${j.niveau}</td><td class="num">${j.xp} XP</td></tr>`;
}

async function pageAccueil(env) {
  const top = await env.DB.prepare("SELECT pseudo, etat, xp, niveau FROM joueurs ORDER BY xp DESC, cree ASC LIMIT 10").all();
  const n = (await env.DB.prepare("SELECT COUNT(*) AS n FROM joueurs").first()).n;
  const lignes = top.results.map((j, i) => {
    const e = lireEtat(j);
    return ligneClassement({ pseudo: j.pseudo, nom: e.nom || j.pseudo, niveau: j.niveau, xp: j.xp, forme: e.forme }, i);
  }).join("");
  return page("Accueil", `
<section class="hero">
  <div>${svgCreature(12, "Agilité", {}, 10)}</div>
  <div style="flex:1;min-width:260px">
    <h1>La créature qui mange tes commandes</h1>
    <p>Chaque commande tapée dans le terminal la nourrit. En grandissant, elle t'apprend à naviguer, créer, protéger…
    puis à explorer des donjons, jouer au hacker et coder ton propre jeu.</p>
    <p class="doux">${n} créature${n > 1 ? "s" : ""} recensée${n > 1 ? "s" : ""}.</p>
  </div>
</section>
<h2 id="telecharger">Télécharger</h2>
<div class="grille">
  <div class="carte"><b>📱 Android</b><p class="doux">Widget + terminal intégré, donjon, CTF, Doom-like.</p>
    <a class="btn vert" href="${DEPOT}/releases/latest/download/terminagotchi.apk">terminagotchi.apk</a></div>
  <div class="carte"><b>💻 PC (Linux, Mac, Windows)</b><p class="doux">Vit dans ton vrai terminal. Il faut Python 3.</p>
    <a class="btn" href="${DEPOT}/releases/latest/download/terminagotchi.pyz">terminagotchi.pyz</a>
    <p class="doux">Puis : <code>python3 terminagotchi.pyz</code></p></div>
  <div class="carte"><b>🔗 La même créature partout</b><p class="doux">Dans le jeu : <code>compte creer TonPseudo</code>,
    puis <code>compte code</code> pour obtenir un code, et sur l'autre appareil <code>compte lier CODE</code>.</p></div>
</div>
<h2>Classement</h2>
<div class="carte">${lignes ? `<table><tr><th>#</th><th>Joueur</th><th>Créature</th><th></th><th></th></tr>${lignes}</table>`
    : `<p class="doux">Personne pour l'instant… sois la première créature recensée !</p>`}
<p><a href="/classement">Voir tout le classement →</a></p></div>
<h2>Des preuves, pas des promesses</h2>
<div class="carte"><p>Les badges marqués <b>✔ vérifié</b> sont délivrés par le serveur lui-même : par exemple, chaque
drapeau du <a href="/ctf">CTF web</a> est personnel et contrôlé ici. Chaque badge a sa page publique, que tu peux partager.</p>
<p class="doux">Le reste du profil (niveau, compétences…) est déclaré par l'appli et affiché comme tel.</p></div>`);
}

async function pageClassement(env) {
  const r = await env.DB.prepare("SELECT pseudo, etat, xp, niveau FROM joueurs ORDER BY xp DESC, cree ASC LIMIT 100").all();
  const lignes = r.results.map((j, i) => {
    const e = lireEtat(j);
    return ligneClassement({ pseudo: j.pseudo, nom: e.nom || j.pseudo, niveau: j.niveau, xp: j.xp, forme: e.forme }, i);
  }).join("");
  return page("Classement", `<h1>🏆 Classement</h1><p class="doux">Les 100 créatures les plus expérimentées.</p>
<div class="carte">${lignes ? `<table><tr><th>#</th><th>Joueur</th><th>Créature</th><th></th><th></th></tr>${lignes}</table>`
    : `<p class="doux">Personne pour l'instant.</p>`}</div>`);
}

async function pageJoueur(env, pseudo) {
  const p = await profilPublic(env, pseudo);
  if (!p) return page("Inconnu", `<h1>Joueur inconnu</h1><p><a href="/classement">Retour au classement</a></p>`);
  const lo = 10 * (p.niveau - 1) ** 2;
  const hi = 10 * p.niveau ** 2;
  const pct = Math.round((100 * (p.xp - lo)) / Math.max(1, hi - lo));
  const stats = STATS.map((s) => `<div>${COURT[s]} <b>${p.stats[s]}</b></div>`).join("");
  const badges = p.badges.map((b) => `<a class="badge verifie" href="${b.lien}">✔ ${echapper(b.titre)}</a>`).join("")
    || `<span class="doux">Aucun badge vérifié pour l'instant.</span>`;
  const coll = BESTIAIRE.especes.filter((e) => p.collection[e.nom]).map((e) =>
    `<a class="bestiole" href="/bestiaire/${e.id}">${svgBestiole(e)}<div class="num">#${String(e.numero).padStart(3, "0")}</div>
     <div>${echapper(e.nom)} ×${p.collection[e.nom]}</div></a>`).join("");
  const collHtml = coll ? `<p class="doux">${Object.keys(p.collection).filter((k) => p.collection[k]).length}/150 espèces</p><div class="grille-b">${coll}</div>`
    : `<span class="doux">Aucune bestiole capturée.</span>`;
  const comp = p.competences.map((c) => `<span class="badge">◇ ${echapper(c)}</span>`).join("")
    || `<span class="doux">Aucune.</span>`;
  const forme = p.forme && p.niveau >= 5 ? FORMES[p.forme] : "";
  const appareils = p.appareils.map((a) => (a === "android" ? "📱 téléphone" : "💻 PC")).join(" + ") || "—";
  return page(p.pseudo, `
<section class="hero">
  <div class="carte">${svgCreature(p.niveau, p.forme, p.stats, 10, p.shiny)}</div>
  <div style="flex:1;min-width:260px">
    <h1>${p.shiny ? `<span class="rgb">${echapper(p.nom)} ✨</span>` : echapper(p.nom)}</h1>
    <p class="doux">créature de <b>${echapper(p.pseudo)}</b> · ${echapper(p.stade)} ${echapper(forme)} · caractère ${echapper(p.trait || "?")}</p>
    <p>Niveau <b>${p.niveau}</b> · ${p.xp} XP · <b>#${p.rang}</b> au classement</p>
    <div class="barre"><i style="width:${pct}%"></i></div>
    <div class="grille" style="grid-template-columns:repeat(4,1fr);margin-top:12px">${stats}</div>
    <p class="doux">${p.commandes} commandes mangées · ${p.gouts} goûts découverts · joue sur ${appareils}</p>
  </div>
</section>
<h2>Badges vérifiés par le serveur</h2><div>${badges}</div>
<h2>Compétences <span class="doux" style="font-size:14px">(déclarées par l'appli)</span></h2><div>${comp}</div>
<h2>Collection</h2>${collHtml}
${p.partage ? `<p><a href="/captures?joueur=${encodeURIComponent(p.pseudo)}">Voir ses captures uniques →</a></p>` : ""}
<p class="doux" style="margin-top:32px">Inscrit le ${new Date(p.inscrit).toLocaleDateString("fr-FR")} ·
<a href="/api/profil/${encodeURIComponent(p.pseudo)}">données publiques (JSON)</a></p>`, `La créature ${p.nom} de ${p.pseudo}, niveau ${p.niveau}.`);
}

async function pageBadge(env, id) {
  const b = await env.DB.prepare("SELECT b.*, j.pseudo FROM badges b JOIN joueurs j ON j.id = b.joueur WHERE b.id = ?").bind(id).first();
  if (!b) return page("Badge inconnu", `<h1>Badge inconnu</h1><p class="doux">Ce badge n'existe pas : il est peut-être faux.</p>`);
  const date = new Date(b.date).toLocaleString("fr-FR", { timeZone: "Europe/Paris" });
  return page(b.titre, `<div class="carte" style="max-width:560px;margin:24px auto;text-align:center">
<div style="font-size:56px">🏅</div><h1>${echapper(b.titre)}</h1>
<p>délivré à <a href="/joueur/${encodeURIComponent(b.pseudo)}"><b>${echapper(b.pseudo)}</b></a> le ${echapper(date)}</p>
<p style="color:var(--vert)">✔ Vérifié : ce badge est enregistré par le serveur du recensement Terminagotchi.</p>
<p class="doux">Identifiant : <code>${echapper(b.id)}</code> · <a href="/api/badge/${echapper(b.id)}">preuve (JSON)</a></p></div>`,
  `Badge « ${b.titre} » de ${b.pseudo}.`);
}

// ---------------------------------------------------------------- bestioles
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

function etiquetteRarete(r) {
  return `<span class="rar" style="color:${COULEUR_RARETE[r]}">${echapper(r)}</span>`;
}

/** Le glossaire classique des 150 espèces (apparence normale, sans variantes ni shiny). */
function pageBestiaire(url) {
  const famille = url.searchParams.get("famille") || "";
  const rarete = url.searchParams.get("rarete") || "";
  const liste = BESTIAIRE.especes.filter((e) => (!famille || e.famille === famille) && (!rarete || e.rarete === rarete));
  const lien = (k, v, t) => {
    const p = new URLSearchParams({ famille, rarete, [k]: v });
    for (const [a, b] of [...p]) if (!b) p.delete(a);
    const actif = (k === "famille" ? famille : rarete) === v;
    return `<a href="/bestiaire${p.toString() ? "?" + p : ""}"${actif ? ' style="color:var(--jaune)"' : ""}>${t}</a>`;
  };
  const filtresF = [lien("famille", "", "toutes"), ...BESTIAIRE.familles.map((f) => lien("famille", f.nom, f.icone + " " + f.nom))].join(" ");
  const filtresR = [lien("rarete", "", "toutes"), ...BESTIAIRE.raretes.map((r) => lien("rarete", r, r))].join(" ");
  const cartes = liste.map((e) => `<a class="bestiole" href="/bestiaire/${e.id}">${svgBestiole(e)}
    <div class="num">#${String(e.numero).padStart(3, "0")} · ${e.icone} ${echapper(e.famille)}</div>
    <div><b>${echapper(e.nom)}</b></div>${etiquetteRarete(e.rarete)}</a>`).join("");
  return page("Bestiaire", `<h1>📖 Bestiaire</h1>
<p>Les 150 espèces de bestioles qui se cachent dans le terrain de jeu : 75 communes, 45 peu communes, 20 rares et 10 légendaires,
réparties en 15 familles. Plus une bestiole est rare, plus elle se cache profond (recoin → cachette → sanctuaire).</p>
<div class="carte filtres"><div><span class="doux">Famille :</span> ${filtresF}</div><div style="margin-top:6px"><span class="doux">Rareté :</span> ${filtresR}</div></div>
<p class="doux">${liste.length} espèce${liste.length > 1 ? "s" : ""}</p>
<div class="grille-b">${cartes}</div>`, "Le bestiaire des 150 bestioles de Terminagotchi.");
}

function pageEspece(id) {
  const e = PAR_ID[id];
  if (!e) return page("Inconnue", `<h1>Espèce inconnue</h1><p><a href="/bestiaire">Retour au bestiaire</a></p>`, undefined, 404);
  const i = e.numero - 1;
  const prec = BESTIAIRE.especes[(i + 149) % 150];
  const suiv = BESTIAIRE.especes[(i + 1) % 150];
  const stats = Object.entries(e.stats).map(([k, v]) => `<div><div class="doux" style="font-size:12px">${k}</div><b>${v}</b></div>`).join("");
  return page(e.nom, `<p><a href="/bestiaire">← Bestiaire</a></p>
<section class="hero">
  <div class="carte">${svgBestiole(e, false, 14)}</div>
  <div style="flex:1;min-width:260px">
    <p class="doux">#${String(e.numero).padStart(3, "0")} · ${e.icone} famille ${echapper(e.famille)}</p>
    <h1>${e.rarete === "légendaire" ? `<span class="rgb">${echapper(e.nom)}</span>` : echapper(e.nom)}</h1>
    ${etiquetteRarete(e.rarete)}
    <p>${echapper(e.description)}</p>
    <p class="doux">${echapper(e.comportement)}</p>
    <div class="stats-b">${stats}</div>
  </div>
</section>
<h2>Fiche</h2>
<div class="carte"><table>
<tr><td class="doux">Capacité</td><td>${echapper(e.capacite)}</td></tr>
<tr><td class="doux">Stat favorite</td><td>${echapper(e.stat)}</td></tr>
<tr><td class="doux">Taille / poids</td><td>~${e.taille_cm} cm · ~${e.poids_ko} Ko</td></tr>
<tr><td class="doux">Habitat</td><td><code>~/terrain_terminagotchi/${echapper(e.zone)}</code></td></tr>
<tr><td class="doux">Apparition</td><td>${echapper(e.frequence)} · attirée par la commande <code>${echapper(e.attiree_par)}</code></td></tr>
</table></div>
<p style="margin-top:24px"><a href="/bestiaire/${prec.id}">← #${String(prec.numero).padStart(3, "0")} ${echapper(prec.nom)}</a>
 · <a href="/bestiaire/${suiv.id}">#${String(suiv.numero).padStart(3, "0")} ${echapper(suiv.nom)} →</a></p>`,
  `${e.nom}, bestiole ${e.rarete} de la famille ${e.famille}.`);
}

/** La galerie des captures : seulement les joueurs qui ont dit oui (compte partage on). */
async function pageCaptures(env, url) {
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
  caps = caps.filter((c) => PAR_NOM[c.espece] && (!shinySeul || c.shiny) && (!rarete || PAR_NOM[c.espece].rarete === rarete));
  caps.sort((a, b) => (b.shiny - a.shiny) || (b.date - a.date));
  const total = caps.length;
  caps = caps.slice(0, 120);
  const cartes = caps.map((c) => {
    const e = PAR_NOM[c.espece];
    const date = new Date(c.date).toLocaleDateString("fr-FR");
    const nom = c.shiny || e.rarete === "légendaire" ? `<span class="rgb">${echapper(e.nom)}${c.shiny ? " ✨" : ""}</span>` : `<b>${echapper(e.nom)}</b>`;
    return `<div class="bestiole capture${c.shiny ? " shiny" : ""}">
      <div style="text-align:center">${svgBestiole(e, c.shiny)}</div>
      <div>${nom} <span class="num">#${String(e.numero).padStart(3, "0")}</span></div>
      ${etiquetteRarete(e.rarete)}
      <div class="marque">« <span class="rgb">${echapper(c.marque)}</span> »</div>
      <div class="doux" style="font-size:13px">humeur ${echapper(c.humeur)} · ${c.taille} cm<br>potentiel <b style="color:var(--vert)">${c.potentiel} %</b></div>
      <div class="doux" style="font-size:12px;margin-top:6px">par <a href="/joueur/${encodeURIComponent(c.pseudo)}">${echapper(c.pseudo)}</a> · ${date}</div>
    </div>`;
  }).join("");
  const lienR = (v, t) => `<a href="/captures?${new URLSearchParams({ ...(filtre && { joueur: filtre }), ...(shinySeul && { shiny: "1" }), ...(v && { rarete: v }) })}">${t}</a>`;
  return page("Captures", `<h1>✨ Les captures</h1>
<p>Chaque bestiole capturée est <b>unique</b> : sa marque, son humeur, sa taille et son potentiel sont tirés au sort au moment de la capture.
${filtre ? `Captures de <b>${echapper(filtre)}</b>. <a href="/captures">Voir tout le monde</a>` : ""}</p>
<div class="carte filtres">${lienR("", "toutes")} ${BESTIAIRE.raretes.map((x) => lienR(x, x)).join(" ")}
 · <a href="/captures?${new URLSearchParams({ ...(filtre && { joueur: filtre }), ...(!shinySeul && { shiny: "1" }) })}">${shinySeul ? "toutes (pas que les shiny)" : "<span class=\"rgb\">shiny seulement</span>"}</a></div>
<p class="doux">${total} capture${total > 1 ? "s" : ""} partagée${total > 1 ? "s" : ""} par ${joueurs} joueur${joueurs > 1 ? "s" : ""}${total > 120 ? " (les 120 plus récentes)" : ""}.</p>
${cartes ? `<div class="grille-b" style="grid-template-columns:repeat(auto-fill,minmax(220px,1fr))">${cartes}</div>`
    : `<div class="carte"><p class="doux">Aucune capture partagée pour l'instant.</p></div>`}
<h2>Apparaître dans la galerie</h2>
<div class="carte"><p>La galerie ne montre que les joueurs qui l'ont <b>accepté</b>. Pour y montrer tes bestioles, tape dans le jeu :
<code>compte partage on</code> (sur PC : <code>tg compte partage on</code>). Pour les retirer : <code>compte partage off</code>.</p>
<p class="doux">Les captures sont déclarées par l'appli ; seuls les badges marqués ✔ sont vérifiés par le serveur.</p></div>`,
  "La galerie des bestioles capturées par les joueurs de Terminagotchi.");
}

function pageCtf(origine) {
  const liste = EPREUVES.map((e) => `<li><b>${e.n}. ${echapper(e.titre)}</b> — <code>curl ${origine}/ctf/TonPseudo/${e.n}</code></li>`).join("");
  return page("CTF web", `<h1>🚩 Capture the flag — édition web</h1>
<p>5 épreuves qui apprennent comment fonctionne le web, avec la commande <code>curl</code>.
Chaque drapeau est <b>personnel</b> : remplace <code>TonPseudo</code> par ton pseudo de recensement.</p>
<div class="carte"><ol style="padding-left:20px">${liste}</ol></div>
<h2>Comment valider</h2>
<div class="carte"><p>Dans le jeu (PC ou téléphone) : <code>drapeau TG{…}</code>. Le serveur vérifie et te délivre un badge vérifié.</p>
<p class="doux">Sur PC, <code>curl</code> est déjà installé (Linux, Mac, Windows 10+). Sur Android, utilise Termux
(<code>pkg install curl</code>).</p></div>
<h2>Pourquoi c'est légal et éthique</h2>
<div class="carte"><p class="doux">Ces épreuves sont faites pour être « attaquées ». S'entraîner sur des systèmes dont
on n'a pas l'autorisation est illégal : les vrais hackers éthiques ne testent que ce qu'on leur permet de tester.</p></div>`);
}

// ====================================================================== aiguillage

export default {
  async fetch(requete, env) {
    const url = new URL(requete.url);
    const chemin = url.pathname.replace(/\/+$/, "") || "/";
    try {
      if (requete.method === "OPTIONS") {
        return new Response(null, { headers: { "access-control-allow-origin": "*", "access-control-allow-headers": "authorization, content-type", "access-control-allow-methods": "GET, POST" } });
      }
      if (chemin.startsWith("/api/")) return await api(requete, env, chemin);
      if (chemin === "/") return await pageAccueil(env);
      if (chemin === "/classement") return await pageClassement(env);
      if (chemin === "/ctf") return pageCtf(url.origin);
      if (chemin === "/bestiaire") return pageBestiaire(url);
      if (chemin === "/captures") return await pageCaptures(env, url);
      const mb = chemin.match(/^\/bestiaire\/([a-z0-9]+)$/);
      if (mb) return pageEspece(mb[1]);
      if (chemin === "/robots.txt") {
        return texte("User-agent: *\n# Les robots ne doivent pas fouiller les cachettes du CTF…\nDisallow: /ctf/*/2/cachette\n");
      }
      let m = chemin.match(/^\/joueur\/([^/]+)$/);
      if (m) return await pageJoueur(env, decodeURIComponent(m[1]));
      m = chemin.match(/^\/badge\/([0-9a-f]{16})$/);
      if (m) return await pageBadge(env, m[1]);
      m = chemin.match(/^\/ctf\/([^/]+)\/(\d)(?:\/(\w+))?$/);
      if (m) return await ctf(requete, env, decodeURIComponent(m[1]), Number(m[2]), m[3]);
      return page("Introuvable", `<h1>404</h1><p>Cette page n'existe pas. <a href="/">Retour à l'accueil</a></p>`, undefined, 404);
    } catch (e) {
      console.error(e);
      return chemin.startsWith("/api/") ? erreur("Erreur du serveur : " + e.message, 500) : texte("Erreur du serveur.\n", 500);
    }
  },
};

// pour les tests
export { fusionner, niveauDe, drapeauDe, EPREUVES };
