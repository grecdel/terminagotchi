// Le monde des biomes : la GÉNÉRATION COMMUNE, même règle que pc/tg/monde_gen.py et Monde.kt (vecteurs communs
// donnees/monde/vecteurs.json, vérifiés par site/test/test.mjs). Porté du prototype « Monde Terminagotchi » v4.
// Ce module ne touche à rien : il calcule le relief d'un terrain décrit par { type: [{nom, objets}] }.

export const TYPES = ["feu", "eau", "glace", "plante", "roche", "ciel", "ombre", "machine", "poison"];
export const HR = 14, TILT = 0.62, HZ = 5, SQ3 = Math.sqrt(3), HH = HR * Math.sin(Math.PI / 3) * TILT;
export const FLOWER = [];
for (let q = -2; q <= 2; q++) for (let r = -2; r <= 2; r++) if (Math.abs(q) + Math.abs(r) + Math.abs(q + r) <= 4) FLOWER.push([q, r]);
export const DIRS = [[1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1]];
export const DIR_EDGE = [[0, 1], [5, 0], [4, 5], [3, 4], [2, 3], [1, 2]];
export const SCEN_BLOCK = new Set(["chene", "sapin", "sapin_neige", "bouleau", "cerisier", "rocher", "rocher_volc", "tombe", "tuyau", "engrenage", "cristal", "colonne"]);
const LIQUIDES = new Set(["eau", "lave", "toxique"]);
const AQUA_DECO = new Set(["corail", "algues", "bulles", "roseau", "coquillage"]);
const LA = [5, -2], LB = [2, 3];
const MN6 = [[1, 0], [-1, 0], [0, 1], [0, -1], [-1, 1], [1, -1]];
const ANG = { roche: 0, feu: 48, machine: 100, ombre: 150, poison: 192, eau: 236, glace: 282, ciel: 322 };
const ORDRE = ["plante", "roche", "feu", "machine", "ombre", "poison", "eau", "glace", "ciel"];

export function hachage(s) {
  let h = 2166136261;
  s = String(s);
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return h >>> 0;
}
export function hasard(graine) {
  let a = graine >>> 0;
  return () => {
    a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
export const rnd = (s) => hasard(hachage(s))();
export const arrondi = (x, n = 1000) => Math.floor(x * n + 0.5) / n;
export function melanger(xs, r) {
  xs = [...xs];
  for (let i = xs.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [xs[i], xs[j]] = [xs[j], xs[i]]; }
  return xs;
}
const choisir = (xs, r) => xs[Math.floor(r() * xs.length)];
export const anneau = (q, r) => (Math.abs(q) + Math.abs(r) + Math.abs(q + r)) / 2;

export function genParcelle(tid, nom, volcan = false, laveDir = 0) {
  const r = hasard(hachage(tid + ":" + nom)), out = {};
  const pool = r() < 0.6, s1 = r() * 6, s2 = r() * 6;
  const ring2 = [], ring1 = [];
  for (const [q, r_] of FLOWER) {
    const d = anneau(q, r_), k = q + "," + r_;
    let kind = "herbe", h = 2.0, extra = {};
    if (tid === "feu") {
      if (volcan) {
        const [dq, dr] = DIRS[laveDir]; const ch1 = q === dq && r_ === dr, ch2 = q === 2 * dq && r_ === 2 * dr;
        if (d === 0) { kind = "lave"; h = 8.2; extra = { crater: 1, flow: 0 }; }
        else if (d === 1) { kind = ch1 ? "lave" : "cone"; h = ch1 ? 8.4 : 9.8 + ((q * 3 + r_) & 1) * 0.8; if (ch1) extra.flow = 1; }
        else { kind = ch2 ? "lave" : (r() < 0.35 ? "cendre" : "cone"); h = ch2 ? 6.4 : 6.8 + r() * 0.5; if (ch2) extra.flow = 2; }
      } else {
        kind = pool && d === 0 ? "lave" : (r() < 0.25 ? "cendre" : "basalte");
        h = kind === "lave" ? 1.5 : 2.2 + r() * 0.6; if (kind === "lave") extra.flow = 0;
      }
    } else if (tid === "eau") { kind = (!pool && d === 0) ? "sable" : "eau"; h = kind === "sable" ? 1.3 : 0.55; }
    else if (tid === "glace") {
      const cliff = ((q * 2 + r_ * 3 + Math.floor(s1 + 0.5)) % 5 + 5) % 5 === 0 && d > 0;
      kind = pool && d === 0 ? "glace" : (cliff ? "glace" : "neige"); h = pool && d === 0 ? 2.4 : (cliff ? 4.9 : 3 + (d === 1 ? 0.4 : 0));
    } else if (tid === "plante") {
      kind = r() < 0.25 ? "fleurs" : (r() < 0.4 ? "sombre" : "herbe");
      h = 2 + 0.55 * Math.sin(q * 1.3 + s1) + 0.45 * Math.cos(r_ * 1.1 + s2);
    } else if (tid === "roche") {
      const trail = (q === 1 && r_ === 0) || (q === 2 && r_ === -1) || (q === 1 && r_ === -1);
      if (d === 0) { kind = "neige"; h = 9.8; }
      else if (d === 1) { h = trail ? 7.2 : 6.8 + r() * 1.8; kind = h > 7.9 ? "neige" : "pierre"; }
      else { h = trail ? 4.8 : 3.6 + r() * 1.6; kind = h > 4.6 ? "pierre" : (r() < 0.5 ? "gres" : "sable"); }
    } else if (tid === "ciel") {
      let sector = 0;
      if (d !== 0) { const a = Math.atan2(r_ + q / 2, q * SQ3 / 2); sector = 1 + Math.floor(arrondi((a + Math.PI) / (Math.PI * 2), 1e6) * 3) % 3; }
      h = [6.2, 4.4, 7.4, 5.4][sector] + (r() - 0.5) * 0.5; kind = r() < 0.2 ? "orage" : "nuage"; extra.float = 1;
    } else if (tid === "ombre") { kind = d === 0 ? "crypte" : (r() < 0.35 ? "violette" : "dalle"); h = d === 0 ? 0.7 : 2 + (d === 1 ? 0 : 0.3); }
    else if (tid === "machine") { kind = r() < 0.25 ? "grille" : (r() < 0.15 ? "rouille" : "metal"); h = 3 + (d === 1 && r() < 0.35 ? 0.6 : 0); extra.machine = 1; }
    else if (tid === "poison") { const tox = (pool && d === 0) || (d === 1 && r() < 0.25); kind = tox ? "toxique" : "vase"; h = kind === "toxique" ? 0.65 : 1.2 + r() * 0.3; }
    out[k] = { kind, h: arrondi(h), v: Math.floor(r() * 4), d, ...extra };
    if (d === 2) ring2.push(k); if (d === 1) ring1.push(k);
  }
  const scen = (cands, keys, n) => { for (const k of melanger(cands, r).slice(0, n)) out[k].scen = { k: choisir(keys, r), s: arrondi(0.85 + r() * 0.45) }; };
  if (tid === "plante") scen(ring2, ["chene", "sapin", "bouleau", "chene", "cerisier"], 5);
  if (tid === "glace") scen(ring2, ["sapin_neige", "cristal"], 2);
  if (tid === "roche") scen(ring2, ["rocher"], 2);
  if (tid === "machine") scen(ring2, ["tuyau", "engrenage"], 2);
  if (tid === "poison") scen(ring2.filter((k) => out[k].kind === "vase"), ["roseau", "champi_tox"], 3);
  if (tid === "eau") scen(ring1, ["corail", "algues"], 2);
  if (tid === "ombre") {
    for (const k of melanger(ring2, r).slice(0, 2)) { out[k].kind = "fleche"; out[k].h = arrondi(8.5 + r() * 2); out[k].block = 1; }
    scen(ring2.filter((k) => out[k].kind !== "fleche"), ["tombe"], 1);
  }
  if (tid === "feu" && !volcan) scen(ring2, ["braises", "rocher_volc"], 2);
  return out;
}

const FLEURS = { rose: "#ff3d5a", tulipe: "#ff8a3d", tournesol: "#ffd23f", marguerite: "#ffffff", lavande: "#a77bff", bleuet: "#4f8cff", coquelicot: "#ff2a2a", violette: "#8a4fff", lys: "#ffe9f2" };
const MOTS = [["geyser", "geyser", 1], ["braise", "braises", 0], ["corail", "corail", 0], ["coquill", "coquillage", 0], ["algue", "algues", 0], ["bonhomme", "bonhomme", 1], ["colonne", "colonne", 1], ["ruine", "colonne", 1], ["paratonnerre", "paratonnerre", 1], ["etoile", "etoile", 0], ["eolienne", "eolienne", 1], ["tombe", "tombe", 1], ["rune", "rune", 1], ["engrenage", "engrenage", 1], ["rouage", "engrenage", 1], ["tuyau", "tuyau", 1], ["neon", "neon", 1], ["lampe", "neon", 1], ["roseau", "roseau", 0], ["bulle", "bulles", 0], ["cristal", "cristal", 1], ["cactus", "cactus", 1]];
const ACC_DE = "àâäáãåçéèêëíìîïñóòôöõúùûüýÿœæ", ACC_A = "aaaaaaceeeeiiiinooooouuuuyyoa";
const norm = (s) => [...String(s).toLowerCase()].map((c) => { const i = ACC_DE.indexOf(c); return i >= 0 ? ACC_A[i] : c; }).join("");
export function deco(nom, tid) {
  const i = nom.lastIndexOf(".");
  const base = norm(i > 0 ? nom.slice(0, i) : nom), ext = norm(i > 0 ? nom.slice(i + 1) : "");
  const a = (...ms) => ms.some((m) => base.includes(m));
  for (const [m, k, b] of MOTS) if (base.includes(m)) return [k, b];
  if (ext === "arbre") {
    if (a("sapin", "pin")) return [tid === "glace" ? "sapin_neige" : "sapin", 1];
    if (a("bouleau")) return ["bouleau", 1];
    if (a("cerisier", "sakura")) return ["cerisier", 1];
    if (a("palmier", "coco")) return ["palmier", 1];
    return ["chene", 1];
  }
  if (ext === "fleur") { let col = null; for (const k in FLEURS) if (base.includes(k)) col = FLEURS[k]; if (!col) col = "h" + (hachage(base) % 360); return ["fleur:" + col, 0]; }
  if (ext === "pierre" || ext === "rocher") { if (a("galet")) return ["galet", 0]; return [tid === "feu" ? "rocher_volc" : "rocher", 1]; }
  if (ext === "champignon") return [{ ombre: "champi_lum", poison: "champi_tox" }[tid] || "champignon", 0];
  if (ext === "plante" || ext === "buisson") return ["buisson", 0];
  if (["tar", "gz", "tgz", "zip"].includes(ext)) return ["caisse", 0];
  if (["sh", "py", "ps1"].includes(ext)) return ["parchemin_machine", 0];
  if (["txt", "md", "log", "csv"].includes(ext)) return ["parchemin", 0];
  return ["panneau", 0];
}

const plan = (q, r) => [1.5 * q, SQ3 * (r + q / 2)];
export const macro = (m, n) => [m * LA[0] + n * LB[0], m * LA[1] + n * LB[1]];
const angDiff = (a, b) => { const d = Math.abs(a - b) % 360; return d > 180 ? 360 - d : d; };
export function disposition(regions) {
  const occ = new Map(); const K = (x, y) => x + "," + y;
  const P = (m, n) => plan(...macro(m, n));
  const ang = (m, n) => { const [x, y] = P(m, n); return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360; };
  const dist = (m, n) => { const [x, y] = P(m, n); return Math.hypot(x, y) / 5; };
  const frontiere = (cells) => { const o = new Map(); for (const [x, y] of cells) for (const [dx, dy] of MN6) { const k = K(x + dx, y + dy); if (!occ.has(k) && !o.has(k)) o.set(k, [x + dx, y + dy]); } return [...o.values()]; };
  const out = {};
  for (const tid of ORDRE) {
    const n = regions[tid] || 0; if (!n) continue;
    const pref = ANG[tid] ?? 0; const cells = [];
    if (!occ.size) cells.push([0, 0]);
    else {
      let best = null, bs = null;
      for (const [x, y] of frontiere([...occ.values()])) { const s = arrondi(angDiff(ang(x, y), pref) * 0.08 + dist(x, y) * 0.9 + ((x * 7 + y * 13) & 3) * 0.001, 1e6); if (bs === null || s < bs) { bs = s; best = [x, y]; } }
      cells.push(best);
    }
    occ.set(K(...cells[0]), cells[0]);
    while (cells.length < n) {
      let cx = 0, cy = 0; for (const c of cells) cx += P(...c)[0]; for (const c of cells) cy += P(...c)[1]; cx /= cells.length; cy /= cells.length;
      let best = null, bs = null;
      for (const [x, y] of frontiere(cells)) { const [px, py] = P(x, y); const s = arrondi(dist(x, y) * 0.7 + (tid === "plante" ? 0 : angDiff(ang(x, y), pref) * 0.03) + Math.hypot(px - cx, py - cy) / 5 * 1.3 + ((x * 7 + y * 13) & 3) * 0.001, 1e6); if (bs === null || s < bs) { bs = s; best = [x, y]; } }
      if (!best) break; cells.push(best); occ.set(K(...best), best);
    }
    out[tid] = cells;
  }
  return out;
}

export function construire(terrain) {
  const lay = disposition(Object.fromEntries(Object.entries(terrain).map(([k, v]) => [k, v.length])));
  const parcelles = []; let volcanFait = false;
  for (const tid of TYPES) (terrain[tid] || []).forEach((p, i) => {
    const volcan = tid === "feu" && !volcanFait; volcanFait = volcanFait || volcan;
    const L = lay[tid] || []; const m = i < L.length ? L[i] : L[L.length - 1];
    parcelles.push({ type: tid, nom: p.nom, id: tid + "/" + p.nom, m, centre: macro(...m), volcan, gen: genParcelle(tid, p.nom, volcan, 0), objets: [...(p.objets || [])], plus: p.plus || 0, caches: p.caches || 0 });
  });
  const hexs = new Map(); const hk = (q, r) => q + "," + r; const at = (q, r) => hexs.get(hk(q, r));
  for (const p of parcelles) {
    const [cq, cr] = p.centre;
    for (const [dq, dr] of FLOWER) {
      const g = p.gen[dq + "," + dr];
      const h = { q: cq + dq, r: cr + dr, cle: p.id + ":" + dq + "," + dr, off: [dq, dr], parcelle: p.id, region: p.type, kind: g.kind, h: g.h, v: g.v, d: g.d, flow: g.flow ?? null, crater: g.crater || 0, float: g.float || 0, machine: g.machine || 0, block: !!g.block, scen: g.scen || null, between: null, bridge: false };
      if (h.scen && SCEN_BLOCK.has(h.scen.k)) h.block = true;
      hexs.set(hk(h.q, h.r), h);
    }
  }
  const par = Object.fromEntries(parcelles.map((p) => [p.id, p]));
  const vp = parcelles.find((p) => p.volcan);
  if (vp) {
    const [vq, vr] = vp.centre, [dq, dr] = DIRS[0];
    for (const h of hexs.values()) {
      if (h.region !== "feu" || h.parcelle === vp.id) continue;
      const d = anneau(h.q - vq, h.r - vr), pied = arrondi(5.6 - (d - 3) * 1.05);
      if (pied > h.h) { h.h = pied; h.kind = rnd(h.cle) < 0.35 ? "cendre" : "cone"; h.scen = null; h.block = false; }
      for (let k = 3; k < 8; k++) if (h.q === vq + dq * k && h.r === vr + dr * k) { h.kind = "lave"; h.flow = k; h.h = arrondi(Math.max(1.3, h.h - 0.35)); }
    }
  }
  for (const h of hexs.values()) {
    if (h.region !== "eau" || h.kind !== "eau" || h.d < 2) continue;
    if (rnd(h.cle + "s") < 0.5 && DIRS.some(([a, b]) => { const n = at(h.q + a, h.r + b); return !n || n.region !== "eau"; })) { h.kind = "sable"; h.h = 1.35; }
  }
  const cordes = [], fait = new Set();
  const parM = new Map(parcelles.map((p) => [p.m[0] + "," + p.m[1], p]));
  const ph = (p) => FLOWER.map(([a, b]) => at(p.centre[0] + a, p.centre[1] + b));
  const hd = (h, c) => anneau(h.q - c[0], h.r - c[1]);
  for (const p of parcelles) for (const [a, b] of MN6) {
    const o = parM.get((p.m[0] + a) + "," + (p.m[1] + b));
    if (!o || o.type === p.type) continue;
    const cle = [p.id, o.id].sort().join("-"); if (fait.has(cle)) continue; fait.add(cle);
    const oc = o.centre, pc = p.centre;
    const cas = ph(p).filter((h) => h.d === 2).sort((x, y) => hd(x, oc) - hd(y, oc) || Math.abs(x.q - x.r) - Math.abs(y.q - y.r));
    if (!cas.length) continue; const ca = cas[0];
    const cbs = DIRS.map(([x, y]) => at(ca.q + x, ca.r + y)).filter((h) => h && h.parcelle === o.id).sort((x, y) => hd(x, pc) - hd(y, pc));
    if (!cbs.length) continue; const cb = cbs[0];
    const ta = p.type, tb = o.type;
    const pont = ["eau", "ciel"].includes(ta) || ["eau", "ciel"].includes(tb) || LIQUIDES.has(ca.kind) || LIQUIDES.has(cb.kind);
    const interieur = (c, pp, pcen) => {
      if (pp.volcan || pp.type === "eau" || pp.type === "ciel") return null;
      const ns = DIRS.map(([dx, dy]) => at(c.q + dx, c.r + dy)).filter((x) => x && x.parcelle === pp.id && x.d === 1 && x.region && x.kind !== "fleche")
        .sort((x, y) => anneau(x.q - pcen[0], x.r - pcen[1]) - anneau(y.q - pcen[0], y.r - pcen[1]) || Math.abs(x.h - c.h) - Math.abs(y.h - c.h));
      return ns[0] || null;
    };
    const raide = Math.abs(ca.h - cb.h) > 1.4;
    const ia = raide ? interieur(ca, p, oc) : null, ib = raide ? interieur(cb, o, pc) : null;
    const chaine = [ia, ca, cb, ib].filter(Boolean);
    const h0 = (ia || ca).kind === "fleche" ? 2 : (ia || ca).h, h1 = (ib || cb).kind === "fleche" ? 2 : (ib || cb).h;
    const ha = ca.kind === "fleche" ? 2 : ca.h, hb = cb.kind === "fleche" ? 2 : cb.h;
    chaine.forEach((h, i) => {
      h.h = arrondi(h0 + (h1 - h0) * (i + 0.5) / chaine.length);
      h.kind = pont ? "pont" : (Math.abs(ha - hb) > 1.4 ? "escalier" : "chemin");
      if (h === ca || h === cb) h.region = null;
      h.block = false; h.scen = null; if (pont) h.float = 0; h.machine = 0; h.bridge = pont; h.between = [ta, tb];
    });
    if (pont) for (let i = 0; i < chaine.length - 1; i++) cordes.push([chaine[i].cle, chaine[i + 1].cle]);
  }
  for (const h of hexs.values()) {
    h.base = arrondi(h.float ? h.h - 1.1 : (h.machine ? h.h - 0.6 : (h.bridge ? h.h - 0.35 : -1.5)));
    h.mur = Math.max(1, Math.floor((h.h - h.base) * HZ + 0.5));
    h.pilier = h.machine ? Math.floor((h.base + 1.5) * HZ + 0.5) : 0;
  }
  for (const p of parcelles) {
    const pris = new Set(); p.poses = {};
    for (const nom of p.objets) {
      const [k, bloque] = deco(nom, p.type); const cands = [];
      for (const o of FLOWER) {
        const h = at(p.centre[0] + o[0], p.centre[1] + o[1]);
        if (!h.region || h.block || h.scen || pris.has(o.join(",")) || h.crater || (o[0] === 0 && o[1] === 0) || (LIQUIDES.has(h.kind) && !AQUA_DECO.has(k))) continue;
        cands.push(o);
      }
      if (!cands.length) continue;
      const o = choisir(cands, hasard(hachage(p.id + "/" + nom)));
      pris.add(o.join(",")); p.poses[nom] = { off: o, k, bloque: !!bloque };
    }
  }
  return { parcelles, par, hex: hexs, at, cordes };
}

export function placeCreatures(monde, creatures) {
  const libres = {}; for (const p of monde.parcelles) (libres[p.type] ||= []).push(p.id);
  const maison = {}, refuge = [];
  for (const [i, ty] of creatures) { if (libres[ty] && libres[ty].length) maison[i] = libres[ty].shift(); else refuge.push(i); }
  return { maison, refuge };
}
export const solXY = (q, r) => [HR * 1.5 * q, HR * SQ3 * (r + q / 2) * TILT];

export function resume(monde) {
  const hs = [...monde.hex.values()].sort((a, b) => a.q - b.q || a.r - b.r);
  return {
    parcelles: monde.parcelles.map((p) => [p.id, [...p.m], p.volcan, Object.fromEntries(Object.keys(p.poses).sort().map((n) => [n, [[...p.poses[n].off], p.poses[n].k, p.poses[n].bloque]]))]),
    hex: hs.map((h) => [h.q, h.r, h.kind, h.h, h.v, h.region, h.mur, h.pilier, h.scen ? h.scen.k : null, h.block]),
    cordes: monde.cordes.map((c) => [...c]),
  };
}
