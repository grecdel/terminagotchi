// Les commandes qui se voient dans le monde : la SPÉCIFICATION COMMUNE des effets, même règle que pc/tg/effets.py
// et Effets.kt (vecteurs communs donnees/effets/vecteurs.json, vérifiés par site/test/test.mjs).
// evenements(ligne, avant, apres, code, sortie) → [événement] ; avant/apres : {cwd, f: {chemin: [genre, taille, date, droits]}}.
// UN EFFET NE MENT JAMAIS : les fichiers viennent de la comparaison avant/après, jamais du seul texte de la commande.

export const GROUPE = 6;
export const NIVEAUX = ["tous", "essentiels", "aucun"];
const PS = { "get-location": "pwd", gl: "pwd", "set-location": "cd", sl: "cd", chdir: "cd", "push-location": "cd", pushd: "cd", "get-childitem": "ls", gci: "ls", dir: "ls", ll: "ls", la: "ls", "get-content": "cat", gc: "cat", type: "cat", "set-content": "echo", sc: "echo", "add-content": "echo", ac: "echo", "out-file": "tee", "tee-object": "tee", "copy-item": "cp", copy: "cp", cpi: "cp", "move-item": "mv", move: "mv", mi: "mv", "rename-item": "mv", ren: "mv", rni: "mv", "remove-item": "rm", del: "rm", erase: "rm", ri: "rm", rd: "rmdir", "new-item": "touch", ni: "touch", md: "mkdir", "write-output": "echo", "write-host": "echo", write: "echo", "select-string": "grep", "get-process": "ps", gps: "ps", "stop-process": "kill", spps: "kill", "test-connection": "ping", "invoke-webrequest": "curl", iwr: "curl", "invoke-restmethod": "curl", irm: "curl", "get-filehash": "sha256sum", "sort-object": "sort", "measure-object": "wc", "set-acl": "chmod", "get-acl": "ls", "compare-object": "diff", "start-sleep": "sleep" };
const LIRE = new Set(["cat", "head", "tail", "less", "more", "wc", "nl", "bat"]);
const EMPREINTE = new Set(["sha256sum", "sha1sum", "md5sum", "base64", "shasum", "b2sum"]);
const RESEAU = new Set(["ping", "curl", "wget", "nc", "ssh", "scp", "dig", "nslookup", "host", "traceroute"]);
const PROCESSUS = new Set(["ps", "kill", "killall", "pkill", "jobs", "top", "htop", "bg", "fg", "sleep"]);
const CAISSE = new Set(["tar", "zip", "unzip", "gzip", "gunzip"]);
const RIEN = new Set(["clear", "exit", "alias", "export", "env", "source", ".", "unalias", "set", "history", "reset", "cls"]);
const PRIO = { jokers: 3, "dossier+": 3, "dossier-": 3, "objet+": 3, "objet-": 3, touche: 3, deplace: 3, renomme: 3, copie: 3, ecrit: 3, droits: 3, refus: 3, cd: 3, pwd: 3, ls: 3, find: 3, lire: 3, groupe: 3, modifie: 2, lucioles: 2, messager: 2, photo: 2, empreinte: 2, tuyau: 2, caisse: 2 };
const TYPES = ["feu", "eau", "glace", "plante", "roche", "ciel", "ombre", "machine", "poison"];
export const EXTENSIONS = [];

function jetons(seg) {
  const out = []; let cour = "", cite = false, dans = false, q = null, esc = false;
  for (const c of seg) {
    if (esc) { cour += c; esc = false; dans = true; }
    else if (q) { if (c === q) q = null; else if (c === "\\" && q === '"') esc = true; else cour += c; }
    else if (c === '"' || c === "'") { q = c; cite = true; dans = true; }
    else if (c === "\\") esc = true;
    else if (c === " " || c === "\t") { if (dans) out.push([cour, cite]); cour = ""; cite = false; dans = false; }
    else { cour += c; dans = true; }
  }
  if (dans) out.push([cour, cite]);
  return out;
}

export function correspond(nom, motif) {
  let rx = "", i = 0;
  while (i < motif.length) {
    const c = motif[i]; i++;
    if (c === "*") rx += ".*";
    else if (c === "?") rx += ".";
    else if (c === "[") {
      const j = motif.indexOf("]", i < motif.length && "!^".includes(motif[i]) ? i + 1 : i);
      if (j < 0) rx += "\\[";
      else { let cl = motif.slice(i, j); i = j + 1; if (cl[0] === "!" || cl[0] === "^") cl = "^" + cl.slice(1); rx += "[" + cl.replaceAll("\\", "\\\\") + "]"; }
    } else rx += ".^$+{}()|\\".includes(c) ? "\\" + c : c;
  }
  try { return new RegExp("^(?:" + rx + ")$", "s").test(nom); } catch { return false; }
}

export const canon = (cmd) => { const c = (cmd || "").split("/").pop().toLowerCase(); return PS[c] ?? c; };

const RX_REDIR = /(\d?>>?|&>)\s*("[^"]*"|'[^']*'|[^\s<>|;&]+)/g;
export function segments(ligne) {
  const out = []; const texte = ligne.trim();
  const morceaux = []; let cour = "", q = null, i = 0;
  while (i < texte.length) {
    const c = texte[i];
    if (q) { cour += c; if (c === q) q = null; i++; continue; }
    if (c === '"' || c === "'") { q = c; cour += c; i++; continue; }
    const deux = texte.slice(i, i + 2);
    if (deux === "&&" || deux === "||") { morceaux.push([cour, deux]); cour = ""; i += 2; continue; }
    if (";|&".includes(c) && !(c === "&" && texte.slice(i - 1, i) === ">")) { morceaux.push([cour, c]); cour = ""; i++; continue; }
    cour += c; i++;
  }
  morceaux.push([cour, ""]);
  let prec = "";
  for (const [seg, sep] of morceaux) {
    const s = seg.trim();
    if (!s) { prec = sep; continue; }
    const redir = [];
    for (const m of s.matchAll(RX_REDIR)) if (!m[1].startsWith("2")) redir.push([m[1].includes(">>") ? ">>" : ">", m[2].replace(/^["']+|["']+$/g, "")]);
    let s2 = s.replace(RX_REDIR, " ").replace(/<\s*\S+/g, " ");
    let jet = jetons(s2);
    if (!jet.length) { prec = sep; continue; }
    while (jet.length > 1 && ["do", "then", "else", "{", "!", "time"].includes(jet[0][0])) jet = jet.slice(1);
    let cmd = canon(jet[0][0]), args = jet.slice(1);
    if (cmd === "sudo" && args.length) { cmd = canon(args[0][0]); args = args.slice(1); }
    out.push({ cmd, args, redir, fond: sep === "&", tuyau: prec === "|" });
    prec = sep;
  }
  return out;
}

const options = (args) => args.filter(([a, c]) => a.startsWith("-") && !a.startsWith("--") && !c).map(([a]) => a.slice(1)).join("") + args.filter(([a]) => a.startsWith("--")).map(([a]) => a).join(" ");
const chemins = (args) => args.filter(([a, c]) => !(a.startsWith("-") && !c)).map(([a]) => a);
function joindre(cwd, arg) {
  if (cwd === null || cwd === undefined) return null;
  const a = arg.replaceAll("\\", "/");
  if (a.startsWith("/") || a.startsWith("~")) { const m = a.match(/terrain_terminagotchi(?:\/(.*))?$/); return m ? (m[1] || "").replace(/^\/+|\/+$/g, "") : null; }
  const parts = cwd ? cwd.split("/") : [];
  for (const p of a.split("/")) {
    if (p === "" || p === ".") continue;
    if (p === "..") { if (!parts.length) return null; parts.pop(); } else parts.push(p);
  }
  return parts.join("/");
}
const parent = (c) => c.includes("/") ? c.slice(0, c.lastIndexOf("/")) : "";
const nom = (c) => c.slice(c.lastIndexOf("/") + 1);
const joker = (a, cite) => !cite && ["*", "?", "["].some((x) => a.includes(x));
const haut = (xs) => { const s = new Set(xs); return [...s].filter((x) => ![...s].some((y) => y !== x && x.startsWith(y + "/"))).sort(); };
const sous = (xs, d) => xs.filter((x) => x.startsWith(d + "/")).length;
export function region(chemin) {
  const p = (chemin || "").split("/");
  if (p.length >= 2 && p[0] === "biome" && TYPES.includes(p[1])) return [p[1], p.length >= 3 ? p[2] : null];
  return [null, null];
}
const estParcelle = (c) => { const [ty, parc] = region(c); return !!(ty && parc && nom(c) === parc && /^parcelle[_-]?\d*$/.test(parc.toLowerCase())); };
const ev_ = (t, cmd, k = {}) => ({ type: t, cmd, prio: PRIO[t] ?? 2, ...k });
const egal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const cmpKey = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

export function evenements(ligne, avant, apres, code, sortie = "") {
  try { return _evenements(ligne || "", avant || {}, apres || {}, code, sortie || ""); } catch { return []; }
}

function _evenements(ligne, avant, apres, code, sortie) {
  const segs = segments(ligne);
  if (!segs.length) return [];
  const cmds = segs.map((s) => s.cmd);
  const fa = avant.f || {}, fb = apres.f || {};
  const cwd0 = avant.cwd ?? null, cwd1 = apres.cwd ?? null;
  const moinsTout = Object.keys(fa).filter((c) => !(c in fb)), plusTout = Object.keys(fb).filter((c) => !(c in fa));
  const plus = haut(plusTout), moins = haut(moinsTout);
  const changes = Object.keys(fa).filter((c) => c in fb && !egal(fa[c], fb[c]) && fa[c][0] === "f").sort();
  const droits = Object.keys(fa).filter((c) => c in fb && fa[c][3] !== fb[c][3]).sort();
  let ev = [];
  const principal = segs.find((s) => !RIEN.has(s.cmd)) || segs[0];
  const cmd0 = principal.cmd;
  let vises = [];
  for (const s of segs) for (const [a, cite] of s.args) if (joker(a, cite)) {
    const base = joindre(cwd0, a.includes("/") ? parent(a) : ".");
    if (base === null) continue;
    const motif = nom(a);
    vises = vises.concat(Object.keys(fa).filter((c) => parent(c) === base && correspond(nom(c), motif) && (motif.startsWith(".") || !nom(c).startsWith("."))).sort());
  }
  if (vises.length) ev.push(ev_("jokers", cmd0, { chemins: vises.slice(0, 40), n: vises.length }));
  const usesP = new Set(), usesM = new Set();
  if (cmds.includes("mv")) for (const m of moins) {
    const g = fa[m][0], taille = fa[m][1];
    const cands = plus.filter((p) => !usesP.has(p) && fb[p][0] === g && (g === "d" || fb[p][1] === taille))
      .sort((x, y) => (nom(x) !== nom(m)) - (nom(y) !== nom(m)) || cmpKey(x, y));
    if (cands.length) { const p = cands[0]; usesP.add(p); usesM.add(m); ev.push(ev_(parent(p) === parent(m) ? "renomme" : "deplace", "mv", { de: m, vers: p, genre: g, n: sous(moinsTout, m) + 1 })); }
  }
  if (cmds.includes("cp") || cmds.includes("copy")) {
    let sources = [];
    for (const s of segs) if (s.cmd === "cp") {
      const ch = chemins(s.args);
      for (const a of ch.slice(0, -1)) { const r = joindre(cwd0, a); if (r !== null && r in fa) sources.push(r); }
      if (s.args.some(([a, c]) => joker(a, c))) sources = sources.concat(vises);
    }
    for (const p of plus) {
      if (usesP.has(p)) continue;
      const g = fb[p][0];
      const cands = sources.filter((s) => fa[s][0] === g && (g === "d" || fa[s][1] === fb[p][1])).sort((x, y) => (nom(x) !== nom(p)) - (nom(y) !== nom(p)) || cmpKey(x, y));
      if (cands.length) { usesP.add(p); ev.push(ev_("copie", "cp", { de: cands[0], vers: p, genre: g, n: sous(plusTout, p) + 1 })); }
    }
  }
  const redirs = segs.flatMap((s) => s.redir.map(([op, c]) => [op, joindre(cwd0, c)]));
  const has = (set) => cmds.some((c) => set.has(c));
  const via = cmds.includes("touch") ? "touch" : (redirs.length || cmds.includes("tee")) ? "ecrire" : (cmds.includes("curl") || cmds.includes("wget")) ? "messager" : has(CAISSE) ? "caisse" : cmds.includes("git") ? "photo" : cmds.includes("mkdir") ? "mkdir" : "autre";
  for (const p of plus) {
    if (usesP.has(p)) continue;
    if (fb[p][0] === "d") {
      const parcs = [p, ...plusTout.filter((y) => y.startsWith(p + "/"))].filter((x) => fb[x][0] === "d" && estParcelle(x)).sort();
      ev.push(ev_("dossier+", cmd0 !== "cd" ? cmd0 : "mkdir", { chemin: p, n: sous(plusTout, p) + 1, parcelle: parcs.length > 0, parcelles: parcs.slice(0, 8), region: region(p)[0] }));
    } else ev.push(ev_("objet+", cmd0, { chemin: p, via, region: region(p)[0] }));
  }
  for (const m of moins) {
    if (usesM.has(m)) continue;
    if (fa[m][0] === "d") ev.push(ev_("dossier-", cmd0, { chemin: m, n: sous(moinsTout, m) + 1, region: region(m)[0] }));
    else ev.push(ev_("objet-", cmd0, { chemin: m, region: region(m)[0] }));
  }
  for (const c of changes) {
    if (fa[c][1] === fb[c][1] && fa[c][2] === fb[c][2]) continue;
    const r = redirs.find(([, x]) => x === c); const cible = r ? r[0] : null;
    if (cible) ev.push(ev_("ecrit", ["echo", "printf"].includes(cmd0) ? "echo" : cmd0, { chemin: c, mode: cible, avant: fa[c][1], apres: fb[c][1] }));
    else if (cmds.includes("touch") && fa[c][1] === fb[c][1]) ev.push(ev_("touche", "touch", { chemin: c }));
    else if (cmds.includes("tee")) ev.push(ev_("ecrit", "tee", { chemin: c, mode: options(segs.find((s) => s.cmd === "tee").args).includes("a") ? ">>" : ">", avant: fa[c][1], apres: fb[c][1] }));
    else ev.push(ev_("modifie", cmd0, { chemin: c }));
  }
  for (const c of droits) ev.push(ev_("droits", cmds.includes("chmod") ? "chmod" : cmd0, { chemin: c, avant: fa[c][3], apres: fb[c][3], genre: fa[c][0] }));
  if (cwd0 !== cwd1 && (cmds.includes("cd") || cmds.includes("pushd") || cmds.includes("popd"))) ev.push(ev_("cd", "cd", { de: cwd0, vers: cwd1 }));
  const fichiers = ev.filter((e) => e.type !== "jokers");
  const tuyaux = segs.length > 1 && segs.some((s) => s.tuyau);
  if (!fichiers.length && code === 0 && tuyaux) {
    const src = chemins(segs[0].args).map((a) => joindre(cwd1, a)).find((r) => r !== null && r in fb) ?? null;
    ev.push(ev_("tuyau", segs[0].cmd, { etapes: segs.map((s) => s.cmd).slice(0, 6), source: src, region: region(src || cwd1 || "")[0] }));
  } else if (!fichiers.length && code === 0) {
    for (const s of segs) {
      const c = s.cmd, args = s.args, ch = chemins(args);
      if (c === "pwd") ev.push(ev_("pwd", c, { chemin: cwd1 }));
      else if ((c === "ls" || c === "tree") && !s.tuyau) {
        const cible = ch.length && !joker(...args[args.length - 1]) ? joindre(cwd1, ch[0]) : cwd1;
        if (cible !== null && (cible === "" || (cible in fb && fb[cible][0] === "d"))) {
          const o = options(args);
          ev.push(ev_("ls", c, { chemin: cible, caches: o.includes("a") || o.toLowerCase().includes("force"), long: o.includes("l"), n: Object.keys(fb).filter((x) => parent(x) === cible && (o.includes("a") || !nom(x).startsWith("."))).length }));
        }
      } else if (c === "find") {
        const base = ch.length && !ch[0].startsWith("-") ? joindre(cwd1, ch[0]) : cwd1;
        let motif = null;
        args.forEach(([a], i) => { if ((a === "-name" || a === "-iname") && i + 1 < args.length) motif = args[i + 1][0]; });
        if (base === null) continue;
        const ci = args.some(([a]) => a === "-iname");
        const trouves = Object.keys(fb).filter((x) => (base === "" || x.startsWith(base + "/")) && (motif === null || correspond(ci ? nom(x).toLowerCase() : nom(x), ci ? motif.toLowerCase() : motif))).sort();
        ev.push(ev_("find", c, { chemin: base, motif, chemins: trouves.slice(0, 40), n: trouves.length }));
      } else if (LIRE.has(c) && !s.tuyau) {
        for (const a of ch.slice(0, 3)) { const r = joindre(cwd1, a); if (r !== null && r in fb && fb[r][0] === "f") ev.push(ev_("lire", c, { chemin: r, taille: fb[r][1] })); }
      } else if (EMPREINTE.has(c)) {
        for (const a of ch.slice(0, 3)) { const r = joindre(cwd1, a); if (r !== null && r in fb && fb[r][0] === "f") ev.push(ev_("empreinte", c, { chemin: r })); }
      } else if (c === "git" && ch[0] === "commit") ev.push(ev_("photo", "git", { quoi: "commit" }));
      if (RESEAU.has(c)) ev.push(ev_("messager", c, { cible: cibleReseau(args), ok: true }));
      if (PROCESSUS.has(c) || s.fond) ev.push(ev_("lucioles", c, { quoi: s.fond ? "part" : ["kill", "killall", "pkill"].includes(c) ? "eteint" : "voir", ok: true }));
    }
  }
  if (!fichiers.length && code !== 0 && code !== null && code !== undefined) {
    if (RESEAU.has(cmd0)) ev.push(ev_("messager", cmd0, { cible: cibleReseau(principal.args), ok: false }));
    else if (["kill", "killall", "pkill"].includes(cmd0)) ev.push(ev_("lucioles", cmd0, { quoi: "eteint", ok: false }));
    else if (!RIEN.has(cmd0)) ev.push(refus(principal, cwd0, fa, sortie));
  }
  if (EXTENSIONS.length) {
    const ctx = { ligne, cmds, segments: segs, avant, apres, code, sortie, plus, moins, changes, deja: [...ev] };
    for (const f of EXTENSIONS) { try { ev = ev.concat(f(ctx) || []); } catch { /* un effet ne casse jamais le jeu */ } }
  }
  return grouper(ev);
}

function cibleReseau(args) {
  let out = "", saute = false;
  for (const [a] of args) {
    if (saute) { saute = false; continue; }
    if (a.startsWith("-")) { saute = ["-c", "-o", "-O", "-w", "-W", "-i", "-p", "-H", "-d", "-X", "-m", "--output", "-Count"].includes(a); continue; }
    out = a;
  }
  const m = out.match(/^[a-z]+:\/\/([^/:]+)/);
  return m ? m[1] : out;
}

function refus(seg, cwd, fa, sortie) {
  const s = sortie.toLowerCase(); const any = (xs) => xs.some((x) => s.includes(x));
  let raison;
  if (any(["permission", "non accordée", "denied", "refusé", "accès", "unauthorizedaccess", "operation not permitted", "opération non permise"])) raison = "droits";
  else if (any(["not empty", "pas vide", "non vide", "directory not empty"])) raison = "pas_vide";
  else if (any(["file exists", "existe déjà", "already exists", "le fichier existe"])) raison = "existe";
  else if (any(["no such", "aucun fichier", "introuvable", "cannot find", "not found", "n'existe pas", "does not exist", "itemnotfound"])) raison = "introuvable";
  else if (any(["is a directory", "est un dossier", "est un répertoire"])) raison = "dossier";
  else if (any(["command not found", "commande introuvable", "not recognized", "n'est pas reconnu"])) raison = "commande";
  else raison = "autre";
  const ch = chemins(seg.args);
  let cible = ch.length ? joindre(cwd, ch[ch.length - 1]) : null;
  if (raison === "commande") cible = null;
  return ev_("refus", seg.cmd, { raison, chemin: cible, existe: cible !== null && cible in fa });
}

export function grouper(ev) {
  const compte = {}; for (const e of ev) compte[e.type] = (compte[e.type] || 0) + 1;
  const out = [], fait = new Set();
  for (const e of ev) {
    const t = e.type;
    if (compte[t] > GROUPE && t !== "jokers") {
      if (fait.has(t)) continue; fait.add(t);
      const tous = ev.filter((x) => x.type === t);
      const ch = tous.map((x) => x.chemin || x.vers).filter((c) => c !== null && c !== undefined);
      const regs = new Set(tous.map((x) => x.region ?? null));
      out.push({ type: "groupe", cmd: e.cmd, prio: 3, sorte: t, n: tous.length, chemins: ch.slice(0, GROUPE), region: regs.size === 1 ? [...regs][0] : null });
    } else out.push(e);
  }
  return out;
}

export const filtrer = (ev, niveau) => niveau === "aucun" ? [] : niveau === "essentiels" ? ev.filter((e) => (e.prio ?? 2) >= 3) : [...ev];

export const DITS_MAX = 3;
export function cleDit(e) {
  const t = e.type !== "groupe" ? e.type : (e.sorte || "");
  if (t === "refus") return "efx.dit.refus." + (e.raison || "autre");
  if (t === "ecrit") return "efx.dit.ecrit" + (e.mode === ">>" ? ".ajoute" : ".efface");
  if (t === "ls" && e.caches) return "efx.dit.ls_a";
  if (t === "objet+" && ["touch", "ecrire", "messager", "caisse"].includes(e.via)) return "efx.dit.objet." + e.via;
  if (t === "dossier+" && e.parcelle) return "efx.dit.parcelle";
  if (t === "lucioles") return "efx.dit.lucioles." + (e.quoi || "voir");
  if (t === "messager") return "efx.dit.messager" + (e.ok ? "" : ".rate");
  return "efx.dit." + t.replace("+", "_plus").replace("-", "_moins");
}
export function aDire(compteurs, ev) {
  for (const e of ev) { const k = cleDit(e); if (k && (compteurs[k] || 0) < DITS_MAX) return k; }
  return null;
}
