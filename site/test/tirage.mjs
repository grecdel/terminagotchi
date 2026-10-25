// Anti-triche : le JavaScript du serveur donne EXACTEMENT les mêmes tirages que le PC et l'appli.
// Lancer :  node --no-warnings test/tirage.mjs
import { readFileSync } from "node:fs";
import { Hasard, tirer, differences, stadePlausible, xpPourGrandir } from "../src/tirage.js";

const V = JSON.parse(readFileSync(new URL("../../donnees/anti_triche/vecteurs.json", import.meta.url), "utf8"));
let ok = 0;
let ko = 0;
function verifier(cond, msg) {
  if (cond) { ok++; console.log("  ✔", msg); } else { ko++; console.log("  ✖", msg); }
}

console.log("Vecteurs communs (donnees/anti_triche/vecteurs.json)");
for (const s of V.splitmix) {
  const h = new Hasard(s.valeur, s.n);
  const obtenu = s.sorties.map(() => h.suivant().toString());
  verifier(JSON.stringify(obtenu) === JSON.stringify(s.sorties), `splitmix64 ${s.valeur.slice(0, 16)}…`);
}
let pareils = 0;
const rates = [];
for (const t of V.tirages) {
  const { champs } = tirer(t.valeur, t.n, t.abyssor);
  if (JSON.stringify(champs) === JSON.stringify(t.attendu)) pareils++;
  else rates.push(`${t.valeur.slice(0, 8)}#${t.n} : ${JSON.stringify(champs)} ≠ ${JSON.stringify(t.attendu)}`);
}
verifier(pareils === V.tirages.length, `${pareils}/${V.tirages.length} tirages identiques au Python`);
for (const r of rates.slice(0, 3)) console.log("     ", r);
verifier(V.tirages.some((t) => t.attendu.shiny) && V.tirages.some((t) => t.attendu.espece === "Abyssor"),
  "les vecteurs couvrent des shiny et Abyssor");

console.log("Comparaison d'une capture");
const t0 = V.tirages[0];
const c = { ...t0.attendu, stats: { ...t0.attendu.stats } };
verifier(differences(c, t0.attendu).length === 0, "capture conforme : aucun écart");
c.stats.ATK += 5;
c.shiny = true;
verifier(differences(c, t0.attendu).join() === "shiny,stats.ATK", "stats gonflées et faux shiny repérés");

console.log("Évolution plausible");
verifier(xpPourGrandir("bebe", "ancien") === 2450, "bébé → ancien : 2450 XP");
verifier(stadePlausible("bebe", "ancien", 60) === "enfant", "en 1 minute (120 XP au plus), un bébé devient au mieux enfant");
verifier(stadePlausible("bebe", "ado", 3600) === "ado", "en 1 heure, il peut devenir ado");
verifier(stadePlausible("ado", "enfant", 1e6) === "ado", "on ne rajeunit pas");

console.log(`\n${ok} réussis, ${ko} échoués`);
if (ko) process.exit(1);
