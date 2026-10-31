// Anti-triche : le JavaScript du serveur donne EXACTEMENT les mêmes tirages que le PC et l'appli.
// Lancer :  node --no-warnings test/tirage.mjs
import { readFileSync } from "node:fs";
import { Hasard, tirer, differences, stadePlausible, xpPourGrandir, attirancePlausible, FAMILLES, glitchDe, gardienPlausible, GARDIENS } from "../src/tirage.js";

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

console.log("Le glitch (tirage 13, à part : compteur + 2^20)");
verifier(V.glitchs.every((x) => glitchDe(x.valeur, x.n, x.gardien) === x.glitch) && V.glitchs.filter((x) => x.glitch).length > 10,
  `${V.glitchs.length} tirages du glitch identiques au Python`);
verifier(Object.keys(GARDIENS).join() === "enumeration,droits,secrets" && GARDIENS.secrets === "Crânard", "les gardiens des 3 boîtes codées");
verifier(gardienPlausible(undefined, "Ricanombre") === false && gardienPlausible("enumeration", "Ricanombre") === true
  && gardienPlausible("enumeration", "Crânard") === undefined && gardienPlausible("hangar", "Ombrachne") === undefined,
  "« gardien » : seulement l'espèce gardienne d'une boîte codée");
{
  const t1 = { ...V.tirages[0].attendu, glitch: false };
  verifier(differences({ ...V.tirages[0].attendu, glitch: true }, t1).join() === "glitch", "faux glitch repéré");
  verifier(differences({ ...V.tirages[0].attendu }, { ...t1, glitch: true }).length === 0,
    "une capture d'avant le glitch (sans le champ) reste conforme");
}
{
  const VG = JSON.parse(readFileSync(new URL("../../donnees/glitch/vecteurs.json", import.meta.url), "utf8"));
  const G = await import("../src/glitch.js");
  const { createHash } = await import("node:crypto");
  verifier(VG.fnv.every((f) => G.fnv(f.texte).toString() === f.h), "glitch.js : fnv1a-64 identique");
  const agrandir = (w, h, px, s) => { const o = []; for (let y = 0; y < h * s; y++) for (let x = 0; x < w * s; x++) o.push(px[Math.floor(y / s) * w + Math.floor(x / s)]); return o; };
  const ratesG = VG.cas.filter((c) => {
    const im = VG.images[c.image];
    const o = G.appliquer(im.w * c.s, im.h * c.s, agrandir(im.w, im.h, im.px.map((x) => parseInt(x, 16)), c.s), c.graine, c.style, c.phase, c.s);
    return createHash("sha256").update(o.map((p) => p.toString(16).padStart(8, "0")).join("")).digest("hex") !== c.empreinte;
  });
  verifier(ratesG.length === 0, `glitch.js : ${VG.cas.length - ratesG.length}/${VG.cas.length} images identiques au Python`);
  verifier(VG.eclairs.every((x) => JSON.stringify(G.etat(x.graine, x.t)) === JSON.stringify(x.etat)), `glitch.js : ${VG.eclairs.length} instants, mêmes éclairs`);
  let ok2 = true;
  try { new Function(G.SCRIPT_GLITCH); } catch { ok2 = false; }
  verifier(ok2 && G.SCRIPT_GLITCH.includes("data-glitch") && !G.SCRIPT_GLITCH.includes("export "), "le script des pages se lit (navigateur)");
}

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
  verifier(VE.echelons.every((m) => E.echelonDe(m.n, m.or, m.diamant, m.tous) === m.echelon), "grades identiques (Giga : 1 médaille d'or ; Téra 3, Péta 6, Exa 10 de diamant ; Exa : chaque exercice)");
  verifier(VE.echelons.every((m) => E.etoilesDe(m.n, m.echelon) === m.etoiles), "étoiles identiques (à l'Exa : 600 / 800 / 1000)");
  const { createHash } = await import("node:crypto");
  const empreinteDessin = (g) => createHash("sha256").update(g.map((l) => l.map((c) => c || "").join(",")).join("/")).digest("hex");
  verifier(VE.ecussons.every((m) => empreinteDessin(E.ecusson(m.famille, m.echelon, m.etoiles)) === m.empreinte),
    `${VE.ecussons.length} badges complets identiques au pixel près (galons, étoiles)`);
  const px = E.ECHELONS.map((e) => E.galons(e).flat().filter(Boolean).length);
  verifier(px.every((n, i) => i === 0 || n > px[i - 1]), `les galons grandissent à chaque grade (${px.join(", ")})`);
  const tout = { familles: { cuisinier: { n: 400, or: 0, diamant: 10 } }, records: {} };
  const avant = E.echelon(tout, "cuisinier");
  for (const typ of Object.keys(E.TYPES)) if (E.TYPES[typ][0] === "cuisinier") tout.records[typ] = { t: 9.9 };
  verifier(avant === 6 && E.echelon(tout, "cuisinier") === 7, "Exa : seulement quand chaque exercice de la famille est réussi (sinon Péta)");
  verifier(VE.semaines.every((m) => E.semaine(m.t * 1000) === m.semaine), "semaines ISO identiques");
  verifier(E.commandesConnues("plo_tuyau", ["grep", "wc"]) && !E.commandesConnues("plo_tuyau", ["grep"]), "commandes déjà tapées : vérifiées");
  verifier(E.svgBadge("explorateur", "giga").includes('fill="#ffffff"') && E.svgBadge(null, null).includes("#3a3a44"),
    "badges en SVG (étincelle du Giga, « ??? » gris)");
}

console.log("Récompenses par monde (donnees/recompenses/vecteurs.json) : le serveur accepte les créatures favorisées");
{
  // Une faveur d'exploit (pc/tg/recompenses.py) choisit seulement QUEL compteur garder parmi quelques-uns : la créature
  // gardée doit être exactement le tirage du serveur pour ce (graine, compteur), sinon elle serait refusée.
  const VR = JSON.parse(readFileSync(new URL("../../donnees/recompenses/vecteurs.json", import.meta.url), "utf8"));
  let bons = 0;
  const mauvais = [];
  for (const c of VR.cas) {
    const { champs } = tirer(c.valeur, c.attendu.n, false, null);
    if (differences(c.attendu.champs, champs).length === 0 && JSON.stringify(champs) === JSON.stringify(c.attendu.champs)) bons++;
    else mauvais.push(`${c.exploit} n=${c.attendu.n}`);
  }
  verifier(bons === VR.cas.length, `${bons}/${VR.cas.length} créatures favorisées identiques au tirage du serveur ${mauvais.slice(0, 2).join(", ")}`);
  verifier(VR.cas.every((c) => c.attendu.n >= c.n0 && c.attendu.n < c.n0 + VR.conf["essais_" + c.genre]),
    "le compteur gardé reste dans la fenêtre d'essais (jamais au-delà, jamais deux fois le même)");
}

console.log(`\n${ok} réussis, ${ko} échoués`);
if (ko) process.exit(1);
