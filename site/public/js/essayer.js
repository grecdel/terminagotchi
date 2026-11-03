// « Essayer en 2 minutes » (page /essayer) : le début du jeu rejoué dans la page, comme l'intro de pc/tg/intro.py.
// Un faux dossier EN MÉMOIRE (/home/visiteur) ; rien n'est envoyé, rien n'est enregistré (ni cookie, ni stockage) ;
// recharger la page efface tout. L'œuf est tiré au hasard parmi les 9 types, comme dans le jeu ; son nom proposé est
// « Noisette » (traduit). Pas de minuteur : on avance seulement quand l'enfant tape une commande.
// La mascotte du site n'apparaît pas ici (seulement le camp, les œufs et les vrais bébés du jeu).

const D = window.TG_ESSAYER || { t: {}, depart: {}, noms: {} };
const T = D.t;
const tr = (k, p = {}) => String(T[k] ?? k).replace(/\{(\w+)\}/g, (_, x) => (x in p ? p[x] : ""));
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
// `pwd` dans les textes du jeu → <code>pwd</code> ; *l'œuf remue !* → en italique
const riche = (s) => esc(s).replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*([^*]+)\*/g, "<i>$1</i>");
const $ = (id) => document.getElementById(id);

const BUTS = ["pwd", "ls", "echo", "whoami"];
const CHEMIN = "/home/visiteur";
// le faux dossier : un dossier est un objet, un fichier est la clé de son texte
const ARBRE = { "nid": {}, "sac": { "carte.txt": "site.carte" }, "feu.txt": "site.feu", "panneau.txt": "site.panneau" };

let etat;
const out = $("es-out");
const cmd = $("es-cmd");

function ligne(html, cls = "") {
  const d = document.createElement("div");
  if (cls) d.className = cls;
  d.innerHTML = html;
  out.appendChild(d);
  out.scrollTop = out.scrollHeight;
}

function invite() {
  return `visiteur@terminaworld:~${etat.cwd.length ? "/" + etat.cwd.join("/") : ""}$`;
}

function majInvite() {
  $("es-invite").textContent = etat.phase === "nom" ? "?" : invite();
}

function etape(n, texte) {
  $("es-etape").textContent = `${tr("site.etape", { n })} · ${texte}`;
}

function bulle(html) {
  $("es-bulle").innerHTML = html;
}

function scene(eveille) {
  $("es-scene").style.backgroundImage = `url(/essayer/${eveille ? "camp" : "camp_dort"}.jpg)`;
}

function oeuf() {
  const n = etat.faits.length;
  const im = $("es-oeuf");
  im.hidden = n === 0 || etat.ne;
  im.src = `/essayer/oeuf_${etat.type}_${n >= 4 ? "eclosion" : n >= 3 ? "fissure" : "intact"}.png`;
  // l'œuf arrive « en téléchargement » : on en voit un peu plus à chaque commande
  im.style.clipPath = `inset(0 0 ${100 - n * 25}% 0)`;
}

function liste() {
  const n = etat.faits.length;
  const coches = BUTS.map((b) => (etat.faits.includes(b) ? `<span class="ok">✓ ${b}</span>` : `<span class="g">○ ${b}</span>`)).join("  ");
  ligne(`${esc(tr("intro.liste.titre", { n, total: 4 }))}  ${coches}`, "g");
}

function essais() {
  $("es-essais").innerHTML = ["pwd", "ls", "echo bonjour", "whoami"]
    .map((c) => `<button type="button" data-c="${esc(c)}">${esc(c)}</button>`).join("");
}

function demarrer() {
  const types = Object.keys(D.depart);
  const type = types[Math.floor(Math.random() * types.length)] || "plante";
  const choix = D.depart[type] || ["glandouille"];
  etat = { phase: "nom", type, bebe: choix[Math.floor(Math.random() * choix.length)], nom: "", cwd: [], faits: [], hist: [], h: 0, ne: false };
  out.innerHTML = "";
  $("es-fin").hidden = true;
  $("es-bebe").hidden = true;
  $("es-essais").innerHTML = "";
  scene(false);
  oeuf();
  etape(1, tr("site.etape.1"));
  bulle(esc(tr("intro.e.texte.oeuf")));
  ligne(esc(tr("intro.nom.question")), "j");
  cmd.placeholder = tr("site.nom_defaut");
  majInvite();
}

function nommer(texte) {
  // le nom reste dans la page (rien n'est envoyé) ; pas de signes bizarres, 16 lettres au plus
  etat.nom = [...texte.replace(/[<>&"`*{}]/g, "").trim()].slice(0, 16).join("") || tr("site.nom_defaut");
  etat.phase = "jeu";
  ligne(esc(tr("site.nom", { nom: etat.nom })), "g");
  ligne(esc(tr("site.tape")), "g");
  for (const b of BUTS) ligne(riche(tr("intro.l." + b)));
  bulle(esc(tr("intro.camp.dort")));
  cmd.placeholder = tr("site.placeholder");
  essais();
  majInvite();
}

function dossier(chemin) {
  let d = ARBRE;
  for (const p of chemin) {
    d = d && typeof d === "object" ? d[p] : undefined;
  }
  return d && typeof d === "object" ? d : null;
}

/** Un chemin tapé (nid, nid/, .., ~, /home/visiteur/sac…) → la liste des dossiers depuis ~ ; null s'il sort du camp. */
function resoudre(arg) {
  let a = String(arg || "").trim();
  let parts = [...etat.cwd];
  if (a === "" || a === "~") return [];
  if (a.startsWith("~/")) { parts = []; a = a.slice(2); } else if (a.startsWith(CHEMIN)) { parts = []; a = a.slice(CHEMIN.length); }
  for (const p of a.split("/")) {
    if (!p || p === ".") continue;
    if (p === "..") { parts.pop(); continue; }
    parts.push(p);
  }
  return parts;
}

function compte(b) {
  if (etat.faits.includes(b) || etat.ne) return;
  etat.faits.push(b);
  const n = etat.faits.length;
  if (n === 1) {
    scene(true);
    etape(2, tr("site.etape.2"));
    ligne(esc(tr("intro.eveil")), "j");
  }
  oeuf();
  const pct = n * 25;
  bulle(`<span style="color:var(--ambre)">${esc(tr("intro.recoit", { pct }))}</span> · ${esc(tr("intro.type." + etat.type))}`
    + `<div class="es-prog"><i style="width:${pct}%"></i></div>`);
  if (n < 4) {
    ligne(riche(tr("intro.reagit." + n)), "j");
    liste();
    return;
  }
  liste();
  ligne(esc(tr("intro.eclot", { n, total: 4 })), "ok");
  eclore();
}

function eclore() {
  etat.ne = true;
  const fin = () => {
    $("es-oeuf").hidden = true;
    const b = $("es-bebe");
    b.src = `/portraits/${etat.bebe}/classique_bebe.webp`;
    b.alt = D.noms[etat.bebe] || "";
    b.hidden = false;
    const titre = tr("intro.merci.titre", { nom: etat.nom });
    etape(3, titre);
    bulle(`<b style="color:var(--vert)">${esc(titre)}</b><br>${esc(tr("intro.merci", { nom: etat.nom }))}`);
    ligne(esc(tr("site.bravo", { n: 4 })), "g");
    ligne(esc(tr("site.suite")), "g");
    $("es-fin").hidden = false;
  };
  // l'œuf s'ouvre, puis le bébé apparaît (sans attendre si l'enfant préfère moins d'animations)
  if (matchMedia("(prefers-reduced-motion:reduce)").matches) fin(); else setTimeout(fin, 1200);
}

function lancer(texte) {
  const brut = texte.trim();
  ligne(`<span class="p">${esc(invite())}</span> ${esc(brut)}`);
  if (!brut) return;
  etat.hist.push(brut);
  etat.h = etat.hist.length;
  const [c, ...reste] = brut.split(/\s+/);
  const arg = reste.join(" ");
  const nom = c.toLowerCase();
  if (nom === "pwd") {
    ligne(esc(CHEMIN + (etat.cwd.length ? "/" + etat.cwd.join("/") : "")));
    compte("pwd");
  } else if (nom === "ls") {
    const d = dossier(resoudre(arg.replace(/^-\w+\s*/, "")));
    if (!d) { ligne(esc(tr("site.pas_dossier")), "j"); return; }
    const noms = Object.keys(d).sort();
    ligne(noms.length ? noms.map((k) => (typeof d[k] === "object" ? `<span class="d">${esc(k)}/</span>` : esc(k))).join("  ") : esc(tr("site.vide")), noms.length ? "" : "g");
    compte("ls");
  } else if (nom === "echo") {
    ligne(esc(arg.replace(/^(["'])(.*)\1$/, "$2")));
    compte("echo");
  } else if (nom === "whoami") {
    ligne("visiteur");
    compte("whoami");
  } else if (nom === "cd") {
    const p = resoudre(arg);
    if (!dossier(p)) { ligne(esc(tr("site.pas_dossier")), "j"); return; }
    etat.cwd = p;
    majInvite();
  } else if (nom === "cat") {
    const p = resoudre(arg);
    const f = p.pop();
    const d = dossier(p);
    const v = d && f ? d[f] : undefined;
    if (typeof v !== "string") { ligne(esc(tr("site.pas_fichier")), "j"); return; }
    ligne(esc(tr(v)));
  } else if (nom === "clear") {
    out.innerHTML = "";
  } else if (["aide", "help", "?"].includes(nom)) {
    ligne(esc(tr("site.aide")), "g");
  } else {
    ligne(esc(tr("intro.astuce.erreur")), "j");
  }
}

$("es-form").addEventListener("submit", (ev) => {
  ev.preventDefault();
  const v = cmd.value;
  cmd.value = "";
  if (etat.phase === "nom") nommer(v); else lancer(v);
  cmd.focus();
});
cmd.addEventListener("keydown", (ev) => {
  if (etat.phase !== "jeu" || !etat.hist.length) return;
  if (ev.key === "ArrowUp") { etat.h = Math.max(0, etat.h - 1); cmd.value = etat.hist[etat.h]; ev.preventDefault(); }
  if (ev.key === "ArrowDown") { etat.h = Math.min(etat.hist.length, etat.h + 1); cmd.value = etat.hist[etat.h] || ""; ev.preventDefault(); }
});
$("es-essais").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-c]");
  if (!b) return;
  cmd.value = b.dataset.c;
  cmd.focus();
});
$("es-encore").addEventListener("click", () => { demarrer(); cmd.focus(); });
demarrer();
