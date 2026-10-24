// Serveur local de démonstration : node --no-warnings test/serveur.mjs  → http://localhost:8787
import { createServer } from "node:http";
import { DatabaseSync } from "node:sqlite";
import { readFileSync } from "node:fs";
import worker from "../src/worker.js";

const db = new DatabaseSync(":memory:");
db.exec(readFileSync(new URL("../schema.sql", import.meta.url), "utf8"));
const env = { DB: { prepare: (sql) => { let p = []; const s = {
  bind: (...x) => { p = x; return s; },
  first: async () => db.prepare(sql).get(...p) ?? null,
  all: async () => ({ results: db.prepare(sql).all(...p) }),
  run: async () => ({ meta: { changes: Number(db.prepare(sql).run(...p).changes) } }) }; return s; } } };

async function appel(m, chemin, corps, cle) {
  const h = { "content-type": "application/json" };
  if (cle) h.authorization = "Bearer " + cle;
  const r = await worker.fetch(new Request("http://localhost:8787" + chemin, { method: m, headers: h, body: corps && JSON.stringify(corps) }), env);
  return r.headers.get("content-type").includes("json") ? r.json() : r.text();
}
// quelques joueurs de démonstration
const demo = [["Grec", "Pixel", 1250, "Agilité"], ["Lina", "Octave", 640, "Intelligence"], ["Zed", "Brique", 180, "Force"], ["Momo", "Bulle", 35, null]];
for (const [pseudo, nom, xp, forme] of demo) {
  const { cle } = await appel("POST", "/api/inscription", { pseudo, appareil: "android" });
  await appel("POST", "/api/sync", { appareil: "android", deltas: { xp, total: Math.round(xp / 3), stats: { [forme || "Endurance"]: Math.round(xp / 20), Endurance: 8 } },
    vus: ["ls", "cd", "pwd", "mkdir"], skills: ["Boussole", "Bâtisseur", "Inspecteur"], collection: { Glitchou: 2, Kernelou: 1 },
    valeurs: { nom, nomDate: 1, trait: "curieux", forme } }, cle);
  if (pseudo === "Grec") {
    const { code } = await appel("POST", "/api/code", {}, cle);
    const pc = await appel("POST", "/api/lier", { code, appareil: "pc" });
    await appel("POST", "/api/sync", { appareil: "pc", deltas: { xp: 10 } }, pc.cle);
    const t = await worker.fetch(new Request("http://localhost:8787/ctf/Grec/1"), env);
    await appel("POST", "/api/drapeau", { drapeau: t.headers.get("x-drapeau") }, cle);
  }
}
createServer(async (req, res) => {
  const morceaux = [];
  for await (const c of req) morceaux.push(c);
  const corps = morceaux.length ? Buffer.concat(morceaux) : undefined;
  const r = await worker.fetch(new Request("http://localhost:8787" + req.url, { method: req.method, headers: req.headers, body: corps }), env);
  res.writeHead(r.status, Object.fromEntries(r.headers));
  res.end(Buffer.from(await r.arrayBuffer()));
}).listen(8787, () => console.log("http://localhost:8787"));
