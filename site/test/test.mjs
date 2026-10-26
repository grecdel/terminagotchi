// Test du site sans compte Cloudflare : le Worker tourne dans Node avec une imitation de D1 (SQLite).
// Lancer :  node --no-warnings test/test.mjs   (Node 22+)
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import worker from "../src/worker.js";

function faireD1() {
  const db = new DatabaseSync(":memory:");
  db.exec(readFileSync(new URL("../schema.sql", import.meta.url), "utf8"));
  const preparer = (sql) => {
    let params = [];
    const st = {
      bind: (...p) => { params = p; return st; },
      first: async () => db.prepare(sql).get(...params) ?? null,
      all: async () => ({ results: db.prepare(sql).all(...params) }),
      run: async () => { const r = db.prepare(sql).run(...params); return { meta: { changes: Number(r.changes) } }; },
    };
    return st;
  };
  return { prepare: preparer };
}

// valeur FACTICE : le vrai secret se règle avec `wrangler secret put SECRET_GRAINES`, jamais dans le dépôt
const SECRET_FACTICE = "secret-factice-des-tests";
const env = { DB: faireD1(), SECRET_GRAINES: SECRET_FACTICE };
const ORIGINE = "https://terminagotchi.exemple.workers.dev";
let ok = 0;
let ko = 0;
function verifier(cond, msg) {
  if (cond) { ok++; console.log("  ✔", msg); } else { ko++; console.log("  ✖", msg); }
}
async function appel(methode, chemin, { corps, cle, entetes = {} } = {}) {
  const h = { ...entetes };
  if (cle) h.authorization = "Bearer " + cle;
  if (corps !== undefined && typeof corps !== "string") h["content-type"] = "application/json";
  const r = await worker.fetch(new Request(ORIGINE + chemin, {
    method: methode, headers: h, body: corps === undefined ? undefined : typeof corps === "string" ? corps : JSON.stringify(corps),
  }), env);
  const t = await r.text();
  let j = null;
  try { j = JSON.parse(t); } catch { /* page HTML ou texte */ }
  return { statut: r.status, j, t, h: r.headers };
}

console.log("Inscription");
let r = await appel("POST", "/api/inscription", { corps: { pseudo: "Grec", appareil: "android" } });
verifier(r.statut === 200 && /^[0-9a-f]{64}$/.test(r.j.cle), "inscription OK, clé reçue");
const cleTel = r.j.cle;
r = await appel("POST", "/api/inscription", { corps: { pseudo: "grec" } });
verifier(r.statut === 409, "pseudo déjà pris (insensible à la casse)");
r = await appel("POST", "/api/inscription", { corps: { pseudo: "é<script>" } });
verifier(r.statut === 400, "pseudo invalide refusé");
r = await appel("GET", "/api/moi", { cle: "0".repeat(64) });
verifier(r.statut === 401, "fausse clé refusée");

console.log("Liaison d'un 2e appareil");
r = await appel("POST", "/api/code", { cle: cleTel });
verifier(/^[A-Z2-9]{6}$/.test(r.j?.code), "code de liaison : " + r.j?.code);
const code = r.j.code;
r = await appel("POST", "/api/lier", { corps: { code: code.toLowerCase(), appareil: "pc" } });
verifier(r.statut === 200 && r.j.pseudo === "Grec", "le PC est relié au même joueur");
const clePc = r.j.cle;
r = await appel("POST", "/api/lier", { corps: { code } });
verifier(r.statut === 404, "un code ne sert qu'une fois");

console.log("Synchro et fusion");
r = await appel("POST", "/api/sync", { cle: cleTel, corps: {
  appareil: "android",
  deltas: { xp: 120, total: 30, stats: { Endurance: 12, "Agilité": 4 } },
  vus: ["ls", "cd", "pwd"], skills: ["Boussole"], collection: { Glitchou: 1 }, records: { pwd: 4.2 },
  valeurs: { nom: "Pixel", nomDate: 1000, trait: "curieux", faim: 70, faimDate: 1000 },
} });
verifier(r.j.etat.xp === 120 && r.j.etat.nom === "Pixel", "1re synchro du téléphone");
r = await appel("POST", "/api/sync", { cle: clePc, corps: {
  appareil: "pc",
  deltas: { xp: 80, total: 20, stats: { Intelligence: 9 } },
  vus: ["git", "ls"], skills: ["Archiviste"], collection: { Glitchou: 0, Octobit: 2 }, records: { pwd: 3.1, ls: 2 },
  valeurs: { nom: "AutreNom", nomDate: 500, trait: "farceur", faim: 90, faimDate: 2000 },
} });
const e = r.j.etat;
const badgesPc = r.j.badges;
verifier(e.xp === 200, "XP additionnée des deux appareils (200)");
verifier(e.stats.Endurance === 12 && e.stats.Intelligence === 9, "stats additionnées");
verifier(["ls", "cd", "pwd", "git"].every((x) => e.vus.includes(x)) && e.vus.length === 4, "commandes goûtées : union");
verifier(e.collection.Glitchou === 1 && e.collection.Octobit === 2, "collection : maximum par espèce");
verifier(e.records.pwd === 3.1 && e.records.ls === 2, "records : meilleur temps");
verifier(e.nom === "Pixel", "nom : un appareil relié n'écrase pas le nom du compte");
r = await appel("POST", "/api/sync", { cle: clePc, corps: { appareil: "pc", valeurs: { nom: "Pixou", nomDate: 3000 } } });
verifier(r.j.etat.nom === "Pixou", "nom : un renommage plus récent gagne");
await appel("POST", "/api/sync", { cle: cleTel, corps: { appareil: "android", valeurs: { nom: "Pixel", nomDate: 4000 } } });
verifier(e.trait === "curieux", "caractère : le premier reste");
verifier(e.faim === 90, "faim : la valeur la plus récente");
verifier(badgesPc.some((b) => b.type === "multi"), "badge Multi-plateforme délivré");
r = await appel("POST", "/api/sync", { cle: clePc, corps: { appareil: "pc", deltas: { xp: -500, total: 1e9 } } });
verifier(r.j.etat.xp === 200 && r.j.etat.total === 20050, "valeurs négatives ignorées, gros nombres plafonnés");

console.log("Classement et profil");
await appel("POST", "/api/inscription", { corps: { pseudo: "Rival" } });
r = await appel("GET", "/api/classement");
verifier(r.j[0].pseudo === "Grec" && r.j.length === 2, "classement trié par XP");
r = await appel("GET", "/api/profil/grec");
verifier(r.j.niveau === 5 && r.j.rang === 1 && r.j.appareils.length === 2, "profil public (niveau 5, #1, 2 appareils)");
verifier(!JSON.stringify(r.j).includes(cleTel), "le profil public ne contient aucune clé");

console.log("CTF web (drapeaux personnels vérifiés par le serveur)");
r = await appel("GET", "/ctf/Grec/1");
const d1 = r.h.get("x-drapeau");
verifier(/^TG\{[0-9a-f]{14}\}$/.test(d1) && !r.t.includes(d1), "épreuve 1 : drapeau seulement dans l'en-tête");
r = await appel("GET", "/robots.txt");
verifier(r.t.includes("/2/cachette"), "robots.txt indique la cachette");
r = await appel("GET", "/ctf/Grec/2/cachette");
const d2 = r.t.match(/TG\{[0-9a-f]+\}/)?.[0];
r = await appel("POST", "/ctf/Grec/3", { corps: "mot=terminal", entetes: { "content-type": "application/x-www-form-urlencoded" } });
const d3 = r.t.match(/TG\{[0-9a-f]+\}/)?.[0];
r = await appel("POST", "/ctf/Grec/3", { corps: "mot=faux", entetes: { "content-type": "application/x-www-form-urlencoded" } });
verifier(r.statut === 403, "épreuve 3 : mauvais mot refusé");
r = await appel("GET", "/ctf/Grec/4");
verifier(!/TG\{[0-9a-f]/.test(r.t) && (r.h.get("set-cookie") || "").includes("role=visiteur"), "épreuve 4 : cookie visiteur, pas de drapeau");
r = await appel("GET", "/ctf/Grec/4", { entetes: { cookie: "role=admin" } });
const d4 = r.t.match(/TG\{[0-9a-f]+\}/)?.[0];
r = await appel("GET", "/ctf/Grec/5");
const d5 = r.j.tiroirs.milieu.boite.contenu.secret;
verifier([d2, d3, d4, d5].every(Boolean), "épreuves 2 à 5 : drapeaux trouvés");
r = await appel("GET", "/ctf/Rival/1");
verifier(r.h.get("x-drapeau") !== d1, "chaque joueur a des drapeaux différents");
r = await appel("POST", "/api/drapeau", { cle: clePc, corps: { drapeau: r.h.get("x-drapeau") } });
verifier(r.j.ok === false, "le drapeau d'un autre joueur est refusé");
let dernier;
for (const d of [d1, d2, d3, d4, d5]) dernier = await appel("POST", "/api/drapeau", { cle: cleTel, corps: { drapeau: d } });
verifier(dernier.j.ok && dernier.j.score === 5 && dernier.j.badgeFinal, "5/5 drapeaux validés, badge final");
r = await appel("POST", "/api/drapeau", { cle: cleTel, corps: { drapeau: d1 } });
verifier(r.j.ok && r.j.nouveau === false, "valider deux fois ne redonne pas de badge");

console.log("Badges et pages");
r = await appel("GET", "/api/profil/Grec");
verifier(r.j.badges.length === 8, "badges : recensé + multi + 5 épreuves + final = 8");
const lienBadge = r.j.badges.find((b) => b.type === "ctf_web_tout").lien;
r = await appel("GET", lienBadge);
verifier(r.statut === 200 && r.t.includes("Vérifié") && r.t.includes("Hacker du web"), "page publique du badge");
r = await appel("GET", "/badge/0123456789abcdef");
verifier(r.t.includes("faux"), "un faux badge est signalé");
for (const p of ["/", "/classement", "/joueur/Grec", "/ctf", "/nimporte"]) {
  r = await appel("GET", p);
  verifier(r.statut === (p === "/nimporte" ? 404 : 200) && r.t.startsWith("<!doctype html>"), "page " + p);
}
r = await appel("GET", "/joueur/Grec");
verifier(r.t.includes("<svg") && r.t.includes("Pixel") && r.t.includes("✔ CTF web"), "profil : créature dessinée + badges");

await appel("POST", "/api/sync", { cle: cleTel, corps: { valeurs: { nom: "<img src=x onerror=alert(1)>", nomDate: 9999 } } });
r = await appel("GET", "/joueur/Grec");
verifier(!r.t.includes("<img src=x") && r.t.includes("&lt;img"), "le nom est échappé (pas d'injection HTML)");

console.log("Bestiaire et galerie des captures");
const capt = (id, extra = {}) => ({ id, espece: "Glitchou", shiny: false, date: 1700000000000, marque: "une étoile sur le front",
  humeur: "joyeuse", taille: 7.5, potentiel: 77, stats: { PV: 40, ATK: 41, DEF: 30, VIT: 35, INT: 33 }, zone: "faille", ...extra });
r = await appel("POST", "/api/sync", { cle: cleTel, corps: { appareil: "android", captures: [
  capt("aaaaaa0001"), capt("aaaaaa0002", { shiny: true, espece: "Rootkitsune" }), capt("aaaaaa0001"),
  capt("bbbbbb0001", { marque: "<script>alert(1)</script>" }), capt("bbbbbb0002", { espece: "Inconnu" }),
], partage: { actif: false, date: 10 } } });
verifier(r.j.etat.captures.length === 2, "captures : doublons et captures invalides refusés (2 gardées)");
r = await appel("GET", "/captures");
verifier(r.statut === 200 && !r.t.includes("une étoile sur le front"), "galerie : rien sans l'accord du joueur");
r = await appel("POST", "/api/sync", { cle: clePc, corps: { appareil: "pc", partage: { actif: true, date: 20 } } });
verifier(r.j.etat.partage.actif === true, "accord de partage enregistré");
r = await appel("GET", "/captures");
verifier(r.t.includes("une étoile sur le front") && r.t.includes("Ricanos") && r.t.includes("class=\"rgb\""), "galerie : captures visibles, écriture RGB");
verifier(r.t.includes("/portraits/runodrake/classique_enfant.webp"), "galerie : une ancienne capture (Glitchou) devient la nouvelle espèce de même numéro (Runodrake), en portrait");
r = await appel("GET", "/captures?shiny=1");
verifier(r.t.includes("Ricanos") && !r.t.includes("Runodrake"), "galerie : filtre shiny");
r = await appel("POST", "/api/sync", { cle: cleTel, corps: { appareil: "android", partage: { actif: false, date: 5 } } });
verifier(r.j.etat.partage.actif === true, "un vieux réglage de partage n'écrase pas le plus récent");
r = await appel("GET", "/bestiaire");
verifier(r.statut === 200 && (r.t.match(/class="bestiole"/g) || []).length === 150, "glossaire : 150 espèces");
verifier(!r.t.includes("hue-rotate") && (r.t.match(/_adulte\.webp/g) || []).length === 150, "glossaire : 150 portraits classiques adultes, aucune variante shiny");
r = await appel("GET", "/bestiaire?rarete=l%C3%A9gendaire");
verifier((r.t.match(/class="bestiole"/g) || []).length === 10, "glossaire : filtre des 10 légendaires");
r = await appel("GET", "/bestiaire/braisillon");
verifier(r.statut === 200 && r.t.includes("Braisillon") && r.t.includes("terrain_terminagotchi/volcan"), "fiche d'espèce");
verifier(["bebe", "enfant", "ado", "adulte", "ancien"].every((s) => r.t.includes(`/portraits/braisillon/classique_${s}.webp`)), "fiche : les 5 stades en portrait");
verifier(r.t.includes("/portraits/braisillon/lave_adulte.webp") && r.t.includes("Démons") && r.t.includes("environ 1 apparition sur"), "fiche : variantes dessinées, famille, fréquence");
r = await appel("GET", "/bestiaire/gargouflamme");
verifier(r.t.includes("pas encore dessinée") && !r.t.includes("/portraits/gargouflamme/canyon_"), "fiche : une variante pas encore dessinée montre la forme classique");
r = await appel("GET", "/bestiaire/zzz");
verifier(r.statut === 404, "espèce inconnue : 404");
r = await appel("GET", "/joueur/Grec");
verifier(r.t.includes("/bestiaire/runodrake") && r.t.includes("Voir ses captures uniques"), "profil : collection dessinée + lien vers ses captures");

console.log("Langues de l'interface");
const { LANGUES, NOMS_LANGUES, DICTIONNAIRES, depuisAcceptLanguage } = await import("../src/i18n.js");
verifier(LANGUES.length === 14, "14 langues : " + LANGUES.join(" "));
const langDe = (t) => t.match(/<html lang="([a-z]+)" dir="(ltr|rtl)">/)?.slice(1).join("/");
r = await appel("GET", "/");
verifier(langDe(r.t) === "fr/ltr" && !r.h.get("set-cookie"), "par défaut : français, sans cookie");
verifier(r.h.get("content-type") === "text/html; charset=utf-8" && r.t.includes('<meta charset="utf-8">'), "UTF-8 annoncé (en-tête + meta)");
r = await appel("GET", "/?lang=en");
verifier(langDe(r.t) === "en/ltr" && r.t.includes("Leaderboard"), "?lang=en : page en anglais");
verifier(/^lang=en; Path=\/;/.test(r.h.get("set-cookie") || ""), "?lang=en pose le cookie lang=en");
r = await appel("GET", "/classement", { entetes: { cookie: "lang=de" } });
verifier(langDe(r.t) === "de/ltr" && r.t.includes("Rangliste"), "cookie lang=de : allemand");
r = await appel("GET", "/classement", { entetes: { "accept-language": "pt-BR,pt;q=0.9,en;q=0.8" } });
verifier(langDe(r.t) === "pt/ltr", "Accept-Language pt-BR : portugais");
r = await appel("GET", "/?lang=it", { entetes: { cookie: "lang=de", "accept-language": "es" } });
verifier(langDe(r.t) === "it/ltr", "priorité : ?lang avant cookie avant Accept-Language");
r = await appel("GET", "/", { entetes: { cookie: "lang=ja", "accept-language": "es" } });
verifier(langDe(r.t) === "ja/ltr", "priorité : cookie avant Accept-Language");
r = await appel("GET", "/?lang=zz", { entetes: { "accept-language": "xx,ru;q=0.5" } });
verifier(langDe(r.t) === "ru/ltr" && !r.h.get("set-cookie"), "langue inconnue ignorée, puis Accept-Language");
verifier(depuisAcceptLanguage("en;q=0,de;q=0.3") === "de" && depuisAcceptLanguage("") === null && depuisAcceptLanguage("zh-CN") === "zh",
  "lecture d'Accept-Language (q=0 ignoré, région ignorée)");
r = await appel("GET", "/?lang=ar");
verifier(langDe(r.t) === "ar/rtl" && r.t.includes("الترتيب"), "arabe : dir=rtl");
r = await appel("GET", "/?lang=ur");
verifier(langDe(r.t) === "ur/rtl", "ourdou : dir=rtl");
verifier(LANGUES.every((l) => r.t.includes(`<option value="${l}"`) && r.t.includes(NOMS_LANGUES[l])) && ["中文", "Русский", "日本語", "العربية", "हिन्दी", "বাংলা", "اردو"].every((n) => r.t.includes(n)),
  "sélecteur : les 14 langues, chacune écrite dans sa langue");
r = await appel("GET", "/bestiaire/braisillon?lang=en");
verifier(r.t.includes("Braisillon") && r.t.includes("terrain_terminagotchi/volcan") && r.t.includes("Bestiary") && r.t.includes("volcano") && r.t.includes("Demons family"),
  "fiche en anglais : interface traduite, habitat traduit, chemin inchangé");
const braisillon = (await import("../src/bestiaire.js")).default.especes.find((e) => e.id === "braisillon");
verifier(r.t.includes(braisillon.description.replace(/'/g, "&#39;")), "les descriptions des bestioles restent en français");
r = await appel("GET", "/bestiaire?rarete=l%C3%A9gendaire&lang=es");
verifier((r.t.match(/class="bestiole"/g) || []).length === 10 && r.t.includes("legendaria"), "filtres : valeurs françaises dans l'URL, libellés traduits");
r = await appel("GET", "/joueur/Grec?lang=en");
verifier(r.t.includes("Web hacker (full CTF)") && r.t.includes("Leaderboard"), "badges : titre traduit selon leur type");
r = await appel("GET", "/ctf/Grec/1?lang=en");
verifier(r.t.includes("Challenge 1") && !r.t.includes(r.h.get("x-drapeau")), "CTF en texte : traduit, drapeau toujours caché dans l'en-tête");
r = await appel("POST", "/api/inscription", { corps: { pseudo: "x" }, entetes: { "accept-language": "en" } });
verifier(r.j?.erreur?.startsWith("Le pseudo"), "l'API reste en français (lue par l'appli)");

// cohérence des dictionnaires : mêmes clés, mêmes paramètres, mêmes balises HTML qu'en français
const fr = DICTIONNAIRES.fr;
const problemes = [];
const balises = (s) => (s.match(/<\/?(code|b|a)(\s[^>]*)?>/g) || []).length;
const comparer = (a, b, ch, l) => {
  for (const [k, x] of Object.entries(a)) {
    const y = b?.[k];
    if (y === undefined) { if (!["fleches"].includes(k) && x !== null && !(typeof x === "object" && !Object.keys(x).length)) problemes.push(`${l} ${ch}${k} manque`); continue; }
    if (typeof x === "function") { if (typeof y !== "function" || y.length !== x.length) problemes.push(`${l} ${ch}${k} paramètres`); }
    else if (Array.isArray(x)) { if (!Array.isArray(y) || y.length !== x.length) problemes.push(`${l} ${ch}${k} longueur`); }
    else if (x && typeof x === "object") comparer(x, y, ch + k + ".", l);
    else if (typeof x === "string" && balises(x) !== balises(y)) problemes.push(`${l} ${ch}${k} balises`);
  }
};
for (const l of LANGUES) if (l !== "fr") comparer(fr, DICTIONNAIRES[l], "", l);
for (const l of LANGUES) if (l !== "fr") {
  for (const t of ["stats", "statsB", "raretes", "familles", "habitats", "frequences", "humeurs", "formes", "stadesB", "court"]) {
    for (const k of Object.keys(DICTIONNAIRES.en[t])) if (!DICTIONNAIRES[l][t]?.[k]) problemes.push(`${l} ${t}.${k} manque`);
  }
}
verifier(problemes.length === 0, "dictionnaires cohérents" + (problemes.length ? " : " + problemes.slice(0, 5).join(", ") : ""));

console.log("Anti-triche : graines et captures vérifiées");
{
  const { tirer } = await import("../src/tirage.js");
  r = await appel("POST", "/api/sync", { cle: cleTel, corps: { appareil: "android" } });
  const gr = r.j.graines || [];
  verifier(gr.length === 8 && gr.every((g) => /^\d{4}-\d{2}-\d{2}\.[0-9a-f]{12}$/.test(g.id) && /^[0-9a-f]{64}$/.test(g.valeur)),
    "la synchro donne 8 graines signées (hier → dans 6 jours)");
  verifier(!r.t.includes(SECRET_FACTICE), "le secret n'apparaît jamais dans la réponse");
  const auj = new Date().toISOString().slice(0, 10);
  const g = gr.find((x) => x.id.startsWith(auj));
  const r2 = await appel("POST", "/api/sync", { cle: clePc, corps: { appareil: "pc" } });
  const gPc = r2.j.graines.find((x) => x.id.startsWith(auj));
  verifier(gPc.id !== g.id && gPc.valeur !== g.valeur, "chaque appareil a sa propre graine");
  const autre = await appel("POST", "/api/inscription", { corps: { pseudo: "Voisin", appareil: "pc" }, entetes: { "cf-connecting-ip": "10.9.8.7" } });
  const gAutre = (await appel("POST", "/api/sync", { cle: autre.j.cle, corps: { appareil: "pc" } })).j.graines.find((x) => x.id.startsWith(auj));
  const maintenant = Date.now();
  const capt2 = (id, n, extra = {}, graine = g) => {
    const t = tirer(graine.valeur, n).champs;
    return { id, ...t, stats: { ...t.stats }, graine: graine.id, n, date: maintenant, zone: "volcan", ...extra };
  };
  const honnete = capt2("dddddd0001", 0);
  const triche = capt2("dddddd0002", 1);
  triche.stats.ATK += 9; triche.shiny = true; triche.rarete = "légendaire";
  const ancienne = (() => { const t = tirer(g.valeur, 5).champs; return { id: "dddddd0003", ...t, date: maintenant, zone: "volcan" }; })();
  r = await appel("POST", "/api/sync", { cle: cleTel, corps: { appareil: "android", captures: [
    honnete, triche, capt2("dddddd0004", 0), capt2("dddddd0005", 999), capt2("dddddd0006", 2, {}, gAutre), ancienne,
    capt2("dddddd0007", 3, { stade: "ancien" }), capt2("dddddd0008", 4, { stade: "ancien", date: maintenant - 3 * 3600_000 }),
  ] } });
  const par = Object.fromEntries(r.j.etat.captures.map((c) => [c.id, c]));
  verifier(par.dddddd0001?.verifie === true && par.dddddd0001.stats.ATK === honnete.stats.ATK, "capture honnête : vérifiée");
  verifier(par.dddddd0002?.verifie === false && par.dddddd0002.raison === "ne correspond pas au tirage", "stats gonflées / faux shiny : non vérifiée");
  verifier(par.dddddd0004?.verifie === false && par.dddddd0004.raison === "graine déjà utilisée", "même (graine, compteur) une 2e fois : non vérifiée");
  verifier(par.dddddd0005?.verifie === false && par.dddddd0005.raison === "graine ou compteur invalide", `compteur ≥ ${200} : non vérifiée`);
  verifier(par.dddddd0006?.verifie === false && par.dddddd0006.raison === "graine d'un autre joueur", "graine d'un autre joueur : non vérifiée");
  verifier(par.dddddd0003?.verifie === false && !par.dddddd0003.raison, "capture sans graine (ancienne sauvegarde) : gardée, non vérifiée");
  const s7 = tirer(g.valeur, 3).champs.stade;
  verifier(par.dddddd0007?.verifie === true && par.dddddd0007.stade === s7, `évolution instantanée refusée (reste ${s7})`);
  verifier(par.dddddd0008?.stade === "ancien", "évolution en 3 h : acceptée");
  r = await appel("POST", "/api/sync", { cle: cleTel, corps: { appareil: "android", captures: [{ ...honnete, stade: "ancien", stats: { ...honnete.stats, PV: 999 } }] } });
  const h2 = r.j.etat.captures.find((c) => c.id === "dddddd0001");
  verifier(h2.stats.PV === honnete.stats.PV && h2.stade === honnete.stade, "une capture vérifiée ne change ni de stats ni de stade trop vite");
  // attirance : la commande d'une famille, tapée par l'enfant, rend cette famille plus probable
  const captA = (id, n, attire) => {
    const t = tirer(g.valeur, n, false, attire).champs;
    return { id, ...t, stats: { ...t.stats }, graine: g.id, n, date: maintenant, zone: "volcan", attire };
  };
  let nFaux = 13;
  while (tirer(g.valeur, nFaux).champs.espece === tirer(g.valeur, nFaux, false, "Constructs").champs.espece) nFaux++;
  const menteur = { ...capt2("dddddd0013", nFaux), attire: "Constructs" };
  r = await appel("POST", "/api/sync", { cle: cleTel, corps: { appareil: "android", captures: [
    captA("dddddd0010", 10, "Constructs"), captA("dddddd0011", 11, "Démons"), menteur,
  ] } });
  let parA = Object.fromEntries(r.j.etat.captures.map((c) => [c.id, c]));
  verifier(parA.dddddd0010?.verifie === true && parA.dddddd0010.attire === "Constructs", "attirance par git (déjà tapée) : vérifiée");
  verifier(parA.dddddd0011?.verifie === false && parA.dddddd0011.raison === "attirance impossible", "attirance par chmod jamais tapée : non vérifiée");
  verifier(parA.dddddd0013?.verifie === false && parA.dddddd0013.raison === "ne correspond pas au tirage", "attirance annoncée après coup : non vérifiée");
  r = await appel("POST", "/api/sync", { cle: cleTel, corps: { appareil: "android", vus: ["chmod"], captures: [captA("dddddd0012", 12, "Démons")] } });
  parA = Object.fromEntries(r.j.etat.captures.map((c) => [c.id, c]));
  verifier(parA.dddddd0012?.verifie === true, "chmod envoyé avec la capture : attirance des Démons vérifiée");
  r = await appel("GET", "/api/profil/Grec");
  verifier(r.j.capturesVerifiees === 5, "profil : 5 captures vérifiées comptées à part");
  r = await appel("GET", "/captures");
  verifier(r.t.includes("✔ vérifiée") && r.t.includes("non vérifiée") && r.t.includes("/portraits/"), "galerie : vérifiées (✔) et non vérifiées affichées");
  const sansSecret = { DB: env.DB };
  const rs = await worker.fetch(new Request(ORIGINE + "/api/sync", { method: "POST", headers: { authorization: "Bearer " + cleTel },
    body: JSON.stringify({ appareil: "android", captures: [capt2("dddddd0009", 7)] }) }), sansSecret);
  const js = await rs.json();
  verifier(js.graines.length === 0 && js.etat.captures.find((c) => c.id === "dddddd0009")?.verifie === false,
    "sans SECRET_GRAINES : aucune graine, rien n'est vérifié");
}

console.log("Salle d'entraînement : exercices vérifiés, records, badges, Star de la semaine");
{
  const E = await import("../src/entrainement.js");
  const auj = new Date().toISOString().slice(0, 10);
  let r = await appel("POST", "/api/sync", { cle: cleTel, corps: { appareil: "android", vus: ["mkdir", "rm", "rmdir"] } });
  const g = r.j.graines.find((x) => x.id.startsWith(auj));
  const run = (id, type, n, t, extra = {}) => ({ id, type, g: g.id, n, t, d: Date.now(), e: E.empreinte(type, E.generer(type, g.valeur, n)), ...extra });
  const runs = [
    run("e00000000001", "bat_pieces", 0, 9.4),                                  // honnête (diamant : ≤ 15 s)
    run("e00000000002", "bat_pieces", 1, 12, { e: "bat_pieces|pieces=cave,salon" }),   // empreinte inventée
    run("e00000000003", "net_rm", 0, 30),                                       // même (graine, n) qu'un autre
    run("e00000000004", "bat_pieces", 2, 0.5),                                  // trop rapide pour un enfant
    run("e00000000005", "plo_tuyau", 3, 40),                                    // commandes jamais tapées (grep, wc)
    { id: "e00000000006", type: "net_rmdir", g: "", n: 0, t: 18, d: Date.now(), e: "x" },   // sans graine (hors ligne)
    run("e00000000007", "net_rmr", 4, 14),
  ];
  r = await appel("POST", "/api/sync", { cle: cleTel, corps: { appareil: "android", entrainement: {
    deltas: { batisseur: { n: 4, diamant: 1, or: 1, bronze: 2 }, nettoyeur: { n: 3, argent: 3 } },
    runs, records: { bat_pieces: { t: 9.4, g: g.id, n: 0 }, net_rmdir: { t: 18, g: "", n: 0 }, exp_cle: { t: 0.2 } },
  } } });
  const v = r.j.entrainement?.verdicts || {};
  verifier(v.e00000000001 === true && v.e00000000007 === true, "exercices honnêtes : vérifiés");
  verifier(v.e00000000002 === false, "empreinte inventée : non vérifié");
  verifier(v.e00000000003 === false, "(graine, compteur) déjà utilisé : non vérifié");
  verifier(v.e00000000004 === false, "temps impossible (0,5 s) : non vérifié");
  verifier(v.e00000000005 === false, "commandes jamais tapées : non vérifié");
  verifier(v.e00000000006 === false, "sans graine : gardé, non vérifié");
  const ent = r.j.etat.entrainement;
  verifier(ent.familles.batisseur.n === 4 && ent.familles.nettoyeur.n === 3, "les compteurs s'additionnent (badges de la partie)");
  verifier(ent.records.bat_pieces.v === true && ent.records.bat_pieces.t === 9.4, "record vérifié par le tirage refait");
  verifier(ent.records.net_rmdir.v === false && !ent.records.exp_cle, "record sans graine : « non vérifié » ; record impossible : refusé");
  r = await appel("POST", "/api/sync", { cle: cleTel, corps: { appareil: "android", entrainement: { runs: [runs[0]], deltas: {} } } });
  verifier(r.j.entrainement.verdicts.e00000000001 === true && r.j.etat.entrainement.familles.batisseur.n === 4,
    "un exercice renvoyé deux fois n'est pas compté deux fois");
  // la semaine dernière : une Star par famille (calculée une fois, la semaine suivante)
  const j = await env.DB.prepare("SELECT id FROM joueurs WHERE pseudo = 'Grec'").first();
  const avant = Date.now() - 7 * 86_400_000;
  await env.DB.prepare("INSERT INTO exercices (id, joueur, partie, famille, type, temps, medaille, date, semaine, graine, n, verifie) VALUES ('e0000000000a', ?, '1', 'lecteur', 'lec_cat', 11, 'diamant', ?, ?, NULL, NULL, 1)")
    .bind(j.id, avant, E.semaine(avant)).run();
  await env.DB.prepare("DELETE FROM config WHERE cle = 'hebdo'").run();
  r = await appel("POST", "/api/sync", { cle: cleTel, corps: { appareil: "android" } });
  verifier(r.j.entrainement.hebdo.semaine === E.semainePrecedente() && r.j.entrainement.hebdo.familles.includes("lecteur"),
    "Star de la semaine (Lecteur) : portée cette semaine");
  verifier(r.j.entrainement.compte.lecteur === 1, "le site compte combien de fois on l'a eue");
  r = await appel("GET", "/records");
  verifier(r.statut === 200 && r.t.includes("Records de la salle") && r.t.includes(">Grec<") && r.t.includes("9.4 s") && r.t.includes("💎"),
    "/records : les temps vérifiés, avec leur médaille");
  verifier(!r.t.includes("18.0 s") && r.t.includes("🏆") && r.t.includes("<svg class=\"badge-px\""), "/records : rien de non vérifié, Stars et badges en pixels");
  r = await appel("GET", "/api/records");
  verifier(r.j.records.bat_pieces?.[0]?.pseudo === "Grec" && r.j.stars.lecteur?.pseudo === "Grec", "/api/records (JSON)");
  r = await appel("GET", "/joueur/Grec");
  verifier(r.t.includes("Badges de la salle d&#39;entraînement") && r.t.includes("Bâtisseur") && r.t.includes("non vérifié") && r.t.includes("Star de la semaine en Lecteur : 1 fois"),
    "profil : badges, records (vérifiés ou non) et Stars");
  r = await appel("GET", "/api/profil/Grec");
  verifier(r.j.entrainement?.familles?.batisseur?.echelon === "bit" && r.j.entrainement.familles.batisseur.etoiles === 3
    && r.j.entrainement.stars.lecteur === 1, "profil JSON : grades, étoiles et Stars (4 réussites : Bit ★★★)");
  r = await appel("GET", "/joueur/Grec");
  verifier(r.t.includes("Bit ★★★") && r.t.includes('viewBox="0 0 18 28"'), "profil : le badge complet (galons, étoiles) et son grade");
  r = await appel("GET", "/records");
  verifier(["Bit", "Octet", "Kilo", "Méga", "Giga", "Téra", "8 × Bit", "Téra 100"].every((x) => r.t.includes(x)) && r.t.split('viewBox="0 0 18 28"').length - 1 === 6,
    "/records : les 6 grades, leurs galons et ce qu'ils veulent dire");
  r = await appel("GET", "/records?lang=ja");
  verifier(r.t.includes("トレーニングルーム"), "/records traduit (japonais)");
}

// chaque page dans chaque langue
const pages = ["/", "/classement", "/records", "/bestiaire", "/bestiaire/braisillon", "/captures", "/captures?shiny=1", "/joueur/Grec", "/joueur/Personne", lienBadge, "/badge/0123456789abcdef", "/ctf", "/nimporte", "/compte", "/connexion?t=0",
  "/parents", "/soutenir", "/confidentialite", "/mentions-legales"];
let rendues = 0;
const rates = [];
for (const l of LANGUES) {
  for (const p of pages) {
    r = await appel("GET", p + (p.includes("?") ? "&" : "?") + "lang=" + l);
    const bon = r.t.startsWith("<!doctype html>") && langDe(r.t) === `${l}/${["ar", "ur"].includes(l) ? "rtl" : "ltr"}`
      && !/undefined|\[object |NaN|function \(|=>/.test(r.t.replace(/<style>[\s\S]*?<\/style>/, ""));
    if (bon) rendues++; else rates.push(l + p);
  }
}
verifier(rates.length === 0, `${rendues} pages rendues sans trou (${LANGUES.length} langues × ${pages.length} pages)` + (rates.length ? " ; ratées : " + rates.slice(0, 5).join(", ") : ""));

console.log("Plusieurs parties, jetons TG-…, code de secours, connexion au site");
{
  const ip = { "cf-connecting-ip": "10.7.7.7" };
  r = await appel("POST", "/api/inscription", { corps: { pseudo: "Parties", appareil: "pc" }, entetes: ip });
  const cle = r.j.cle;
  const secours = r.j.secours;
  verifier(/^TG-[A-Z2-9]{4}-[A-Z2-9]{4}-[A-Z2-9]{4}$/.test(secours || ""), "inscription : code de secours donné une fois (" + secours + ")");
  // ancienne appli : /api/sync sans identifiant = partie 1
  await appel("POST", "/api/sync", { cle, corps: { appareil: "pc", deltas: { xp: 100 }, valeurs: { nom: "Pixel" } } });
  r = await appel("POST", "/api/sync/a1b2c3d4", { cle, corps: { appareil: "pc", partie: "a1b2c3d4", deltas: { xp: 30 }, valeurs: { nom: "Bidule" } } });
  verifier(r.j?.partie === "a1b2c3d4" && r.j.etat.xp === 30 && r.j.etat.nom === "Bidule", "une 2e partie ne se mélange pas à la 1re");
  r = await appel("POST", "/api/sync", { cle, corps: { appareil: "android", deltas: { xp: 5 } } });
  verifier(r.j?.partie === "1" && r.j.etat.xp === 105 && r.j.etat.nom === "Pixel", "sync sans identifiant = partie 1 (compatibilité)");
  r = await appel("GET", "/api/parties", { cle });
  verifier(r.j?.parties?.length === 2 && r.j.parties.map((p) => p.nom).join() === "Pixel,Bidule", "/api/parties liste les 2 créatures");
  r = await appel("GET", "/api/profil/Parties");
  verifier(r.j?.xp === 105 && r.j.nom === "Pixel", "le profil montre la meilleure créature");
  r = await appel("POST", "/api/sync/x%20y", { cle, corps: {} });
  verifier(r.statut === 400, "identifiant de partie invalide refusé");
  // migration douce : un compte d'avant (créature dans joueurs.etat, aucune ligne parties)
  const vieux = await appel("POST", "/api/inscription", { corps: { pseudo: "Ancien", appareil: "pc" }, entetes: ip });
  await env.DB.prepare("UPDATE joueurs SET etat = ?, xp = 400, niveau = 7 WHERE pseudo = 'Ancien'").bind(JSON.stringify({ nom: "Vieux", xp: 400 })).run();
  r = await appel("GET", "/api/parties", { cle: vieux.j.cle });
  verifier(r.j?.parties?.length === 1 && r.j.parties[0].partie === "1" && r.j.parties[0].nom === "Vieux", "migration : la créature existante devient la partie 1");
  r = await appel("POST", "/api/sync", { cle: vieux.j.cle, corps: { appareil: "pc", deltas: { xp: 1 } } });
  verifier(r.j?.etat?.xp === 401, "… et la synchro de la partie 1 continue dessus");
  // jeton TG-XXXX-XX
  r = await appel("POST", "/api/code", { cle });
  verifier(/^TG-[A-Z2-9]{4}-[A-Z2-9]{2}$/.test(r.j?.jeton || ""), "jeton lisible : " + r.j?.jeton);
  r = await appel("POST", "/api/lier", { corps: { code: r.j.jeton.toLowerCase(), appareil: "android" }, entetes: ip });
  verifier(r.j?.pseudo === "Parties" && /^[0-9a-f]{64}$/.test(r.j.cle), "compte lier TG-… relie l'appareil");
  const cleTel2 = r.j.cle;
  // code de secours
  r = await appel("POST", "/api/secours/recuperer", { corps: { code: "TG-AAAA-AAAA-AAAA" }, entetes: ip });
  verifier(r.statut === 404, "faux code de secours refusé");
  r = await appel("POST", "/api/secours/recuperer", { corps: { code: secours.toLowerCase().replaceAll("-", " "), appareil: "pc" }, entetes: ip });
  verifier(r.j?.pseudo === "Parties" && /^[0-9a-f]{64}$/.test(r.j.cle), "le code de secours rend le compte");
  const enClair = await env.DB.prepare("SELECT COUNT(*) AS n FROM secours WHERE empreinte LIKE ?").bind("%" + secours.replaceAll("-", "").slice(2) + "%").first();
  verifier(enClair.n === 0, "le code de secours n'est pas stocké en clair");
  r = await appel("POST", "/api/secours", { cle });
  const secours2 = r.j?.secours;
  r = await appel("POST", "/api/secours/recuperer", { corps: { code: secours }, entetes: { "cf-connecting-ip": "10.7.7.8" } });
  verifier(secours2 && r.statut === 404, "un nouveau code de secours remplace l'ancien");
  // déconnexion d'un appareil
  r = await appel("POST", "/api/deconnexion", { cle: cleTel2 });
  r = await appel("GET", "/api/parties", { cle: cleTel2 });
  verifier(r.statut === 401, "après déconnexion, la clé de l'appareil ne marche plus");
  // lien à usage unique vers le site
  r = await appel("POST", "/api/lien-site", { cle });
  const lien = r.j?.lien || "";
  verifier(/^\/connexion\?t=[0-9a-f]{32}$/.test(lien), "compte site : lien à usage unique");
  r = await appel("GET", lien);
  const cookie = (r.h.get("set-cookie") || "").match(/tg_session=[0-9a-f]{64}/)?.[0];
  verifier(r.statut === 303 && r.h.get("location") === "/compte" && cookie && /HttpOnly/.test(r.h.get("set-cookie")), "le lien ouvre une session (cookie HttpOnly)");
  r = await appel("GET", lien);
  verifier(r.statut === 404, "le lien ne marche qu'une fois");
  r = await appel("GET", "/compte", { entetes: { cookie } });
  verifier(r.t.includes("Parties") && r.t.includes("Bidule") && r.t.includes("/compte/jeton"), "page Mon compte : pseudo, créatures, bouton « lier un appareil »");
  r = await appel("POST", "/compte/jeton", { entetes: { cookie } });
  const jeton = r.t.match(/TG-[A-Z2-9]{4}-[A-Z2-9]{2}/)?.[0];
  verifier(!!jeton, "le site affiche un jeton TG-… : " + jeton);
  r = await appel("POST", "/api/lier", { corps: { code: jeton, appareil: "pc" }, entetes: ip });
  verifier(r.j?.pseudo === "Parties", "… qui relie un appareil depuis le terminal");
  r = await appel("GET", "/compte");
  verifier(r.t.includes("compte site") && !r.t.includes("Bidule"), "sans session : la page explique « compte site »");
  r = await appel("POST", "/compte/sortir", { entetes: { cookie } });
  r = await appel("GET", "/compte", { entetes: { cookie } });
  verifier(!r.t.includes("Bidule"), "se déconnecter du site ferme la session");
}

console.log("Pied de page, pages pour les adultes, polices locales");
{
  r = await appel("GET", "/classement");
  verifier(["/parents", "/soutenir", "/confidentialite", "/mentions-legales", "mailto:contact@terminagotchi.com", "github.com/grecdel/terminagotchi-android"]
    .every((x) => r.t.includes(`href="${x.startsWith("/") || x.startsWith("mailto") ? x : "https://" + x}"`)), "pied de page : code, contact, soutenir, parents, mentions, confidentialité");
  verifier(!/googleapis|gstatic/.test(r.t) && r.t.includes("/polices/vt323-latin-400-normal.woff2") && r.t.includes("@font-face"),
    "polices hébergées sur le site : aucun appel à Google Fonts");
  r = await appel("GET", "/soutenir");
  verifier(r.t.includes("parents") && r.t.includes("bientôt") && !/liberapay\.com|ko-fi\.com/.test(r.t), "soutenir : pour les adultes, « bientôt » tant qu'aucun lien n'est rempli");
  r = await appel("GET", "/parents?lang=en");
  verifier(r.t.includes("For parents") && r.t.includes("~/terrain_terminagotchi") && r.t.includes("~/.terminagotchi"), "parents (anglais) : ce que fait le jeu sur l'ordinateur");
  r = await appel("GET", "/confidentialite");
  verifier(r.t.includes("pour les enfants") && r.t.includes("Data Privacy Framework") && r.t.includes("CNIL") && r.t.includes("tg_session")
    && r.t.includes("Adresse IP") && r.t.includes("au plus 24 heures") && r.t.includes("après 3 ans"), "confidentialité : enfants, IP, cookies, durées, CNIL");
  r = await appel("GET", "/confidentialite?lang=ar");
  verifier(/<html lang="ar" dir="rtl">/.test(r.t) && r.t.includes('<section lang="fr" dir="ltr">') && r.t.includes("الخصوصية"), "confidentialité en arabe : résumé traduit + texte français qui fait foi (ltr)");
  r = await appel("GET", "/mentions-legales");
  verifier(r.t.includes("101 Townsend Street") && r.t.includes("non professionnel") && r.t.includes("Modèle à faire vérifier")
    && r.t.includes("SIL Open Font License") && r.t.includes("Aucune licence"), "mentions légales : hébergeur, éditeur, modèle à vérifier, crédits, licence");
}

console.log("Suppression d'un compte et durées de conservation");
{
  const ip = { "cf-connecting-ip": "10.6.6.6" };
  r = await appel("POST", "/api/inscription", { corps: { pseudo: "Efface", appareil: "pc" }, entetes: ip });
  const cle = r.j.cle;
  await appel("POST", "/api/sync", { cle, corps: { appareil: "pc", deltas: { xp: 50 }, valeurs: { nom: "Gomme" } } });
  await appel("POST", "/api/code", { cle });
  r = await appel("DELETE", "/api/compte", { cle, corps: { confirmer: "pas-moi" } });
  verifier(r.statut === 400, "suppression refusée sans recopier le pseudo");
  r = await appel("DELETE", "/api/compte", { cle, corps: { confirmer: "efface" } });
  verifier(r.j?.ok === true && r.j.supprime === "Efface", "DELETE /api/compte avec la clé : compte supprimé");
  const restes = [];
  for (const t of ["cles", "codes", "badges", "apparitions", "parties", "secours", "sessions"]) {
    const n = (await env.DB.prepare(`SELECT COUNT(*) AS n FROM ${t} WHERE joueur NOT IN (SELECT id FROM joueurs)`).first()).n;
    if (n) restes.push(t);
  }
  verifier(restes.length === 0, "aucune donnée orpheline après la suppression" + (restes.length ? " : " + restes.join(", ") : ""));
  r = await appel("GET", "/api/profil/Efface");
  verifier(r.statut === 404, "le profil public a disparu");
  r = await appel("GET", "/api/moi", { cle });
  verifier(r.statut === 401, "la clé ne marche plus");
  r = await appel("OPTIONS", "/api/compte");
  verifier(/DELETE/.test(r.h.get("access-control-allow-methods")), "CORS : DELETE autorisé");
  // purge : un compte inactif depuis plus longtemps que CONSERVATION.inactifMois, des compteurs d'IP anciens
  r = await appel("POST", "/api/inscription", { corps: { pseudo: "Endormi", appareil: "pc" }, entetes: ip });
  const { purger, CONSERVATION } = await import("../src/worker.js");
  const vieux = Date.now() - (CONSERVATION.inactifMois + 1) * 31 * 86_400_000;
  await env.DB.prepare("UPDATE joueurs SET maj = ? WHERE pseudo = 'Endormi'").bind(vieux).run();
  await env.DB.prepare("INSERT INTO essais (sujet, minute, n) VALUES ('inscription:10.1.1.1', ?, 1)").bind(Math.floor(Date.now() / 60000) - CONSERVATION.ipHeures * 60 - 5).run();
  const n = await purger(env);
  const ipRestante = await env.DB.prepare("SELECT 1 AS x FROM essais WHERE sujet = 'inscription:10.1.1.1'").first();
  verifier(n === 1 && (await appel("GET", "/api/profil/Endormi")).statut === 404 && (await appel("GET", "/api/profil/Grec")).statut === 200,
    `purge : compte inactif depuis plus de ${CONSERVATION.inactifMois} mois effacé, les autres gardés`);
  verifier(!ipRestante, `purge : adresses IP de plus de ${CONSERVATION.ipHeures} h effacées`);
}

console.log(`\n${ok} réussis, ${ko} échoués`);
process.exit(ko ? 1 : 0);
