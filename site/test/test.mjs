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

const env = { DB: faireD1() };
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

console.log(`\n${ok} réussis, ${ko} échoués`);
process.exit(ko ? 1 : 0);
