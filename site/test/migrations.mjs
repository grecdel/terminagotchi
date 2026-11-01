// Les migrations de la base (migrations/*.sql) : sûres et ré-exécutables.
// Le déploiement applique schema.sql PUIS `wrangler d1 migrations apply` (qui note les migrations faites dans la table
// d1_migrations). Une base déjà en ligne a pu recevoir une table par schema.sql sans que la migration soit notée : chaque
// migration doit donc pouvoir repasser sur une base qui l'a déjà, sans erreur et sans rien perdre.
// Lancer :  node --no-warnings test/migrations.mjs   (Node 22+)
import { DatabaseSync } from "node:sqlite";
import { readFileSync, readdirSync } from "node:fs";

const ici = (f) => new URL("../" + f, import.meta.url);
const SCHEMA = readFileSync(ici("schema.sql"), "utf8");
const fichiers = readdirSync(ici("migrations")).filter((f) => f.endsWith(".sql")).sort();
const MIG = fichiers.map((f) => [f, readFileSync(ici("migrations/" + f), "utf8")]);
let ok = 0;
let ko = 0;
function verifier(cond, msg) {
  if (cond) { ok++; console.log("  ✔", msg); } else { ko++; console.log("  ✖", msg); }
}
const sansCommentaires = (sql) => sql.replace(/--[^\n]*/g, "").replace(/\/\*[\s\S]*?\*\//g, "");
const tablesDe = (sql) => [...sansCommentaires(sql).matchAll(/CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)/gi)].map((m) => m[1]);
const forme = (db) => db.prepare("SELECT type, name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name").all()
  .map((x) => `${x.type} ${x.name} ${String(x.sql).replace(/\s+/g, " ")}`).join("\n");
const comptes = (db) => Object.fromEntries(db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").all()
  .map(({ name }) => [name, db.prepare(`SELECT COUNT(*) AS n FROM "${name}"`).get().n]));

/** Une ligne factice dans chaque table (pour voir qu'aucune donnée ne se perd). */
function remplir(db) {
  for (const { name } of db.prepare("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").all()) {
    const cols = db.prepare(`PRAGMA table_info("${name}")`).all();
    const val = (c) => (/INT/i.test(c.type) ? 7 : /REAL/i.test(c.type) ? 1.5 : `${name}-${c.name}`);
    db.prepare(`INSERT INTO "${name}" (${cols.map((c) => `"${c.name}"`).join(",")}) VALUES (${cols.map(() => "?").join(",")})`)
      .run(...cols.map(val));
  }
}

console.log("Migrations de la base :", fichiers.join(", "));
verifier(fichiers.length > 0 && fichiers.every((f, i) => f.startsWith(String(i + 1).padStart(4, "0") + "_") && /^\d{4}_[a-z0-9_]+\.sql$/.test(f)),
  "noms 0001_…, 0002_…, à la suite (l'ordre où wrangler les applique)");
for (const [f, sql] of MIG) {
  const s = sansCommentaires(sql);
  verifier(!/\b(DROP|DELETE|TRUNCATE|UPDATE|REPLACE\s+INTO|RENAME)\b/i.test(s), `${f} : ne supprime, ne remplace, ne renomme rien`);
  const creations = [...s.matchAll(/CREATE\s+(UNIQUE\s+)?(TABLE|INDEX)\s+(?!IF\s+NOT\s+EXISTS)/gi)];
  verifier(creations.length === 0 && !/\bALTER\b/i.test(s), `${f} : seulement des CREATE … IF NOT EXISTS (ré-exécutable)`);
  verifier(tablesDe(sql).every((t) => tablesDe(SCHEMA).includes(t)), `${f} : ses tables sont aussi dans schema.sql (${tablesDe(sql).join(", ")})`);
}

// 1. base neuve : schema.sql seul, ou schema.sql + migrations (deux fois) donnent la même base
const neuve = new DatabaseSync(":memory:");
neuve.exec(SCHEMA);
const attendu = forme(neuve);
const db = new DatabaseSync(":memory:");
db.exec(SCHEMA);
let erreur = null;
try { for (let k = 0; k < 2; k++) for (const [, sql] of MIG) db.exec(sql); } catch (e) { erreur = e.message; }
verifier(erreur === null && forme(db) === attendu, `base neuve : schema.sql puis les migrations, deux fois, sans erreur, même base ${erreur || ""}`);

// 2. base « en ligne » d'avant chaque migration : ses tables n'existent pas encore, les autres sont pleines
for (const [f, sql] of MIG) {
  const vieille = new DatabaseSync(":memory:");
  vieille.exec(SCHEMA);
  for (const t of tablesDe(sql)) vieille.exec(`DROP TABLE "${t}"`);
  remplir(vieille);
  const avant = comptes(vieille);
  erreur = null;
  try { for (let k = 0; k < 2; k++) { vieille.exec(SCHEMA); for (const [, m] of MIG) vieille.exec(m); } } catch (e) { erreur = e.message; }
  const apres = comptes(vieille);
  verifier(erreur === null && forme(vieille) === attendu && Object.entries(avant).every(([t, n]) => apres[t] >= n),
    `base d'avant ${f} (données dans ${Object.keys(avant).length} tables) : déploiement rejoué deux fois, la table arrive, rien ne se perd ${erreur || ""}`);
}

// 3. base déjà à jour et pleine : le déploiement rejoué ne retire rien (schema.sql peut AJOUTER des lignes : il recopie
//    les anciens comptes dans « parties » avec INSERT OR IGNORE)
remplir(db);
const avant = comptes(db);
try { db.exec(SCHEMA); for (const [, sql] of MIG) db.exec(sql); erreur = null; } catch (e) { erreur = e.message; }
const apres3 = comptes(db);
verifier(erreur === null && Object.entries(avant).every(([t, n]) => apres3[t] >= n) && forme(db) === attendu,
  "base à jour et pleine : rejouer schema.sql et les migrations ne retire aucune ligne et garde la même base");

// 4. le déploiement applique bien les migrations (en local pour le test, puis sur la vraie base)
const wf = readFileSync(new URL("../../.github/workflows/site.yml", import.meta.url), "utf8");
const toml = readFileSync(ici("wrangler.toml"), "utf8");
verifier(/migrations_dir\s*=\s*"migrations"/.test(toml), "wrangler.toml : migrations_dir = \"migrations\"");
verifier(/d1 migrations apply terminagotchi --local/.test(wf) && /d1 migrations apply terminagotchi --remote/.test(wf)
  && wf.indexOf("--remote --file=schema.sql") < wf.indexOf("migrations apply terminagotchi --remote"),
  "site.yml : migrations appliquées en local (test) et en ligne, après schema.sql");

console.log(`\n${ok} réussis, ${ko} échoués`);
process.exit(ko ? 1 : 0);
