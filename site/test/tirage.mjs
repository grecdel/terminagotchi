// Anti-triche : le JavaScript du serveur donne EXACTEMENT les mêmes tirages que le PC et l'appli.
// Lancer :  node --no-warnings test/tirage.mjs
import { readFileSync } from "node:fs";
import { Hasard, tirer, differences, stadePlausible, xpPourGrandir, attirancePlausible, FAMILLES } from "../src/tirage.js";

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
  const { champs } = tirer(t.valeur, t.n, t.abyssor, t.attire ?? null);
  if (JSON.stringify(champs) === JSON.stringify(t.attendu)) pareils++;
  else rates.push(`${t.valeur.slice(0, 8)}#${t.n} : ${JSON.stringify(champs)} ≠ ${JSON.stringify(t.attendu)}`);
}
verifier(pareils === V.tirages.length, `${pareils}/${V.tirages.length} tirages identiques au Python`);
for (const r of rates.slice(0, 3)) console.log("     ", r);
verifier(V.tirages.some((t) => t.attendu.shiny) && V.tirages.some((t) => t.attendu.espece === "Abyssor"),
  "les vecteurs couvrent des shiny et Abyssor");

verifier(V.tirages.some((t) => t.attire), "les vecteurs couvrent l'attirance d'une famille");

console.log("Attirance (la commande tapée attire une famille)");
const fam = Object.keys(FAMILLES);
verifier(fam.length === 10 && Object.values(FAMILLES).includes("chmod"), "10 familles, une commande chacune");
verifier(attirancePlausible(undefined, []) === null, "pas d'attirance déclarée : tirage normal");
verifier(attirancePlausible("Démons", ["ls", "chmod"]) === "Démons", "famille attirée par une commande déjà tapée : acceptée");
verifier(attirancePlausible("Démons", ["ls"]) === undefined, "commande jamais tapée : refusée");
verifier(attirancePlausible("Licornes", ["chmod"]) === undefined, "famille inconnue : refusée");
const N = 4000;
let sans = 0;
let avec = 0;
for (let n = 0; n < N; n++) {
  const g = (n * 2654435761 % 4294967296).toString(16).padStart(16, "0") + "0".repeat(48);
  if (tirer(g, n % 200).e.famille === "Démons") sans++;
  if (tirer(g, n % 200, false, "Démons").e.famille === "Démons") avec++;
}
verifier(avec > 2 * sans, `Démons : ${(100 * sans / N).toFixed(1)} % sans attirance, ${(100 * avec / N).toFixed(1)} % avec`);

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

console.log("Salle d'entraînement (donnees/entrainement/vecteurs.json)");
{
  const E = await import("../src/entrainement.js");
  const VE = JSON.parse(readFileSync(new URL("../../donnees/entrainement/vecteurs.json", import.meta.url), "utf8"));
  const ratesE = [];
  for (const x of VE.exercices) {
    const p = E.generer(x.type, x.valeur, x.k);
    if (E.empreinte(x.type, p) !== x.empreinte || E.reponse(x.type, p) !== x.reponse) ratesE.push(`${x.type}#${x.k} : ${E.empreinte(x.type, p)}`);
  }
  verifier(ratesE.length === 0, `${VE.exercices.length - ratesE.length}/${VE.exercices.length} exercices identiques au Python`);
  for (const r of ratesE.slice(0, 3)) console.log("     ", r);
  verifier(VE.medailles.every((m) => E.medaille(m.type, m.t) === m.medaille), `${VE.medailles.length} médailles identiques`);
  verifier(VE.echelons.every((m) => E.echelonDe(m.n, m.or) === m.echelon), "échelons identiques (Diamant : + une médaille d'or)");
  verifier(VE.semaines.every((m) => E.semaine(m.t * 1000) === m.semaine), "semaines ISO identiques");
  verifier(E.commandesConnues("plo_tuyau", ["grep", "wc"]) && !E.commandesConnues("plo_tuyau", ["grep"]), "commandes déjà tapées : vérifiées");
  verifier(E.svgBadge("explorateur", "diamant").includes('fill="#ffffff"') && E.svgBadge(null, null).includes("#3a3a44"),
    "badges en SVG (étincelle du diamant, « ??? » gris)");
}

console.log(`\n${ok} réussis, ${ko} échoués`);
if (ko) process.exit(1);
