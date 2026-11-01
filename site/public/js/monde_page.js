// Le monde des biomes sur le site (page /monde) : portée du prototype « Monde Terminagotchi » v4 et de pc/tg/monde.py.
// Le relief vient de monde_gen.js (même règle que le jeu), les effets de effets.js (même règle que le jeu) ; ici un
// petit terrain d'essai EN MÉMOIRE (rien n'est envoyé ni enregistré) et un mini-terminal pour s'entraîner.
// La fiche d'une créature s'affiche À LA PLACE de la liste (« ← Mes créatures ») ; un clic à côté ou Échap la referme ;
// sur un téléphone, le panneau monte du bas. La mascotte du site n'apparaît pas dans le monde.
import * as G from "./monde_gen.js";
import * as E from "./effets.js";

const T = (window.TG_MONDE && window.TG_MONDE.t) || {};
const tr = (k, p = {}) => String(T[k] ?? k).replace(/\{(\w+)\}/g, (_, x) => p[x] ?? "");
const $ = (s) => document.querySelector(s);
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const ease = (p) => (p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2);
const easeBack = (p) => { const c = 1.7; return 1 + (c + 1) * Math.pow(p - 1, 3) + c * Math.pow(p - 1, 2); };
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const { HR, HH, HZ } = G;
const EMOJI = { feu: "🔥", eau: "💧", glace: "🧊", plante: "🌿", roche: "🗻", ciel: "⚡", ombre: "🌙", machine: "🔩", poison: "🧪" };
const COUL = { feu: "#e8562a", eau: "#2f7fc4", glace: "#9fd8f2", plante: "#5aa63a", roche: "#c9a26a", ciel: "#dfe9ff", ombre: "#4b3a6b", machine: "#8a96a3", poison: "#6a8f2a" };
const STADE_H = { bebe: 30, enfant: 36 };

// ------------------------------------------------------------------ les pixels (comme pc/tg/monde_dessin.py)
const KINDS = {
  herbe: [["#5aa63a", "#4f9634", "#66b843"], "#6b4a2c", "grass"], fleurs: [["#5aa63a", "#4f9634", "#66b843"], "#6b4a2c", "grass flowers"],
  sombre: [["#2f6b2c", "#2a6027", "#367a31"], "#5e3f25", "grass"], chemin: [["#c9a26a", "#b88f58", "#d4b07a"], "#7b5534", ""],
  escalier: [["#c9a26a", "#b88f58", "#d4b07a"], "#7b5534", "steps"], pont: [["#a8743f", "#9a6a3a", "#b5804a"], "#5a381e", "planks"],
  sable: [["#e6cf8a", "#d9bf78", "#efdb9c"], "#b8945a", ""], eau: [["#2f7fc4", "#2a72b2", "#3a8fd6"], "#1d4a73", "water"],
  neige: [["#eef6ff", "#dbeaf8", "#f8fcff"], "#8fa9c2", ""], glace: [["#a8e1f5", "#94d4ec", "#bdeafa"], "#5f9ab8", "ice"],
  basalte: [["#4a3f4f", "#3f3544", "#554959"], "#2e2531", "strata"], cone: [["#5e4646", "#553f40", "#684e4e"], "#4a2c2a", "strata embers"],
  cendre: [["#6d6670", "#625b66", "#7a7380"], "#2e2531", "embers strata"], lave: [["#ff7a1a", "#f25c0f", "#ff9a33"], "#2e2531", "lava strata"],
  pierre: [["#8d929a", "#7d828a", "#9ba0a8"], "#5d6168", "strata"], gres: [["#d08a4e", "#c27a40", "#dc9a5e"], "#9a5a2e", "strata"],
  nuage: [["#e6defc", "#d9cff7", "#f1ecff"], "#a99be0", "cloud"], orage: [["#8f86b8", "#8178ab", "#9d95c4"], "#5f5690", "cloud bolt"],
  dalle: [["#4b3a6b", "#43345f", "#544276"], "#251c38", "flag"], violette: [["#3d2f52", "#352947", "#47375e"], "#251c38", ""],
  crypte: [["#2a2040", "#241b38", "#30254a"], "#1b142a", "flag"], fleche: [["#3a2d55", "#33284b", "#43345f"], "#2a2140", "spire"],
  metal: [["#8a96a3", "#7f8b98", "#96a2ae"], "#4a525c", "plate"], grille: [["#5d6670", "#535b64", "#68717b"], "#3a4149", "grid"],
  rouille: [["#a3562a", "#8f4a24", "#b86a38"], "#5e3018", ""], vase: [["#55702a", "#4b6424", "#617d30"], "#3b4a1c", ""],
  toxique: [["#8fe03a", "#7fd02c", "#a6f04a"], "#3b4a1c", "toxic"],
};
const hexa = (c) => { if (c.startsWith("h")) { const h = +c.slice(1) / 360, l = 0.62, s = 0.85, q = l + s - l * s, p = 2 * l - q;
  const f = (t) => { t = (t + 1) % 1; return t < 1 / 6 ? p + (q - p) * 6 * t : t < 0.5 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p; };
  return [f(h + 1 / 3) * 255 | 0, f(h) * 255 | 0, f(h - 1 / 3) * 255 | 0]; }
  const n = parseInt(c.slice(1, 7), 16); return [n >> 16, (n >> 8) & 255, n & 255]; };
const shade = (c, a) => c.map((v) => clamp(v + (a | 0), 0, 255));
const hexInside = (dx, dy) => Math.abs(dy) <= HH && Math.abs(dx) <= HR - Math.abs(dy) * (HR / 2) / HH;
const hexBottom = (dx) => (Math.abs(dx) <= HR / 2 ? HH : HH * (HR - Math.abs(dx)) / (HR / 2));
function toile(w, h) { const c = document.createElement("canvas"); c.width = w; c.height = h; const g = c.getContext("2d"); const im = g.createImageData(w, h);
  return { c, w, h, im, px(x, y, col, ww = 1, hh = 1) { const [r, gg, b] = typeof col === "string" ? hexa(col) : col; x = Math.floor(x); y = Math.floor(y);
    for (let yy = Math.max(0, y); yy < Math.min(h, y + hh); yy++) for (let xx = Math.max(0, x); xx < Math.min(w, x + ww); xx++) { const k = 4 * (yy * w + xx); im.data[k] = r; im.data[k + 1] = gg; im.data[k + 2] = b; im.data[k + 3] = 255; } },
    ombre(x, y) { if (x >= 0 && y >= 0 && x < w && y < h) { const k = 4 * (y * w + x); if (!im.data[k + 3]) { im.data[k] = 20; im.data[k + 1] = 30; im.data[k + 2] = 15; im.data[k + 3] = 140; } } },
    fin() { g.putImageData(im, 0, 0); return c; } }; }
function blob(g, cx, cy, rx, ry, cols, r) {
  cols = cols.map(hexa);
  for (let y = -ry; y <= ry; y++) for (let x = -rx; x <= rx; x++) { const d = x * x / (rx * rx) + y * y / (ry * ry); if (d > 1) continue;
    let c = cols[1]; const l = (x / rx) * 0.7 + y / ry; if (l > 0.55) c = cols[0]; else if (l < -0.6) c = cols[2]; if (d > 0.82 && l > 0) c = cols[0]; if (r() < 0.08) c = cols[r() < 0.5 ? 0 : 2]; g.px(cx + x, cy + y, c); }
  for (let y = -ry - 1; y <= ry + 1; y++) for (let x = -rx - 1; x <= rx + 1; x++) { const d = x * x / (rx * rx) + y * y / (ry * ry), d2 = x * x / ((rx + 1) * (rx + 1)) + y * y / ((ry + 1) * (ry + 1)); if (d > 1 && d2 <= 1) g.ombre(cx + x, cy + y); }
}
const mod = (a, b) => a % b;
const SPR = {};
function sprite(kind, v, mur, pil) {
  const cle = kind + "|" + v + "|" + mur + "|" + pil; if (SPR[cle]) return SPR[cle];
  const [tp, wl, fs] = KINDS[kind] || KINDS.herbe; const top = tp.map(hexa), wall = hexa(wl), f = new Set(fs.split(" "));
  const cx = HR + 1.5, cy = HH + 1; const g = toile(HR * 2 + 3, Math.ceil(HH * 2 + mur + pil + 3)); const r = G.hasard(G.hachage(cle + "|1"));
  const fl = ["#ffffff", "#ffd84a", "#ff6fa8", "#b48cff"].map(hexa);
  for (let sy = 0; sy < g.h; sy++) for (let sx = 0; sx < g.w; sx++) {
    const x = sx, y = sy, dx = sx + 0.5 - cx, dy = sy + 0.5 - cy; let col = null;
    if (hexInside(dx, dy)) { const n = r(); col = top[0]; if (n < 0.3) col = top[1]; else if (n < 0.42) col = top[2];
      if (f.has("water")) { const b = mod(x + y * 2 + v * 3, 9); col = b < 2 ? top[2] : b < 5 ? top[0] : top[1]; }
      if (f.has("lava")) { const b = mod(x * 2 - y + v * 5, 8); col = b < 2 ? [255, 211, 107] : b < 4 ? top[2] : n < 0.5 ? top[0] : top[1]; if (n < 0.05) col = [58, 42, 42]; }
      if (f.has("toxic")) { const b = mod(x * 2 + y + v * 4, 9); col = b < 2 ? [217, 255, 138] : b < 5 ? top[0] : top[1]; }
      if (f.has("ice") && mod(x - y * 2 + 40, 11) < 2) col = [255, 255, 255];
      if (f.has("planks")) col = x % 4 === 0 ? [90, 56, 30] : Math.floor(x / 4) % 2 ? top[0] : top[2];
      if (f.has("steps") && Math.floor(dy + HH + 0.5) % 4 === 0) col = [138, 106, 64];
      if (f.has("flag") && (mod(x + 2 * y, 10) === 0 || mod(x - 2 * y + 60, 10) === 0)) col = shade(top[0], -22);
      if (f.has("grid") && (mod(x + 2 * y, 5) === 0 || mod(x - 2 * y + 60, 5) === 0)) col = [54, 61, 69];
      if (f.has("plate") && mod(x + 2 * y, 13) === 0) col = [95, 106, 117];
      if (f.has("cloud") && Math.hypot(dx / HR, dy / HH) > 0.7 && n < 0.55) col = [255, 255, 255];
      if (f.has("bolt")) { const rx = Math.floor(dx + 0.5); if ((rx === -1 && dy > -5 && dy < 0) || (rx === 0 && dy >= -1 && dy < 1) || (rx === 1 && dy >= 0 && dy < 4)) col = [255, 225, 74]; }
      if (f.has("flowers") && n > 0.93) col = fl[Math.floor(r() * 4)];
      if (f.has("embers") && n > 0.95) col = n > 0.975 ? [255, 122, 26] : [255, 179, 71];
      if (f.has("spire")) col = shade(col, Math.floor(-dy * 2 + 0.5));
      if (kind === "neige" && n > 0.9) col = [198, 220, 240]; if (kind === "rouille" && n > 0.9) col = [110, 52, 24]; if (kind === "violette" && n > 0.97) col = [125, 255, 207];
      if (!hexInside(dx + 1.2 * (dx >= 0 ? 1 : -1), dy) || !hexInside(dx, dy + (dy < 0 ? -1.1 : 1.1))) col = shade(col, dy < 0 ? 30 : -24);
    } else if (Math.abs(dx) <= HR && dy > hexBottom(dx) && dy <= hexBottom(dx) + mur) {
      const face = dx < -HR / 2 ? 0 : dx > HR / 2 ? 2 : 1, depth = dy - hexBottom(dx);
      col = shade(wall, [14, 0, -26][face] - Math.min(30, depth * 0.35)); if (depth < 1.2) col = shade(wall, [40, 26, 6][face]);
      if (f.has("strata") && Math.floor(depth + 0.5) % HZ === 0 && depth > 2) col = shade(col, -18);
      if (f.has("cloud") && depth > mur - 3) col = [255, 255, 255];
      if (f.has("lava") && mod(Math.floor(dx + 0.5) + Math.floor(depth * 0.35 + 0.5) + v, 5) === 0) col = depth < mur * 0.7 ? [255, 122, 26] : [194, 65, 12];
      if (r() < 0.06) col = shade(col, -12);
    } else if (pil && Math.abs(dx) <= 3 && dy > HH + mur && dy <= HH + mur + pil) col = dx < -1 ? [93, 102, 112] : dx > 1 ? [44, 50, 56] : [58, 65, 73];
    if (col) g.px(sx, sy, col);
  }
  return (SPR[cle] = { c: g.fin(), ax: cx, ay: cy });
}
const DEC = {};
function decor(k) {
  if (DEC[k]) return DEC[k];
  const r = G.hasard(G.hachage(k)); let g;
  const S = (w, h) => (g = toile(w, h));
  if (k === "chene" || k === "cerisier") { S(30, 38); g.px(13, 22, "#6b4426", 4, 14); g.px(13, 22, "#8a5a33", 1, 14); g.px(12, 35, "#5a381e", 6, 2);
    const cols = k === "cerisier" ? ["#d9659a", "#f28bbb", "#ffc2dc"] : ["#2f7a2a", "#3f9a35", "#6cc24e"]; blob(g, 15, 14, 12, 11, cols, r); blob(g, 9, 18, 6, 5, cols, r); blob(g, 21, 18, 6, 5, cols, r);
    if (k === "cerisier") for (let i = 0; i < 8; i++) g.px(5 + Math.floor(r() * 20), 6 + Math.floor(r() * 14), "#ffffff");
  } else if (k === "sapin" || k === "sapin_neige") { S(24, 40); g.px(10, 30, "#6b4426", 4, 9);
    for (let L = 0; L < 4; L++) { const top = 2 + L * 7, hgt = 12, wb = 4 + L * 2; for (let y = 0; y < hgt; y++) { const w = Math.floor((y / hgt) * wb + 0.5) + 1;
      for (let x = -w; x <= w; x++) { let col = x < -w / 3 ? "#1f5a2a" : x > w / 3 ? "#14421f" : "#2a7035"; if (y === hgt - 1) col = "#123a1b"; if (r() < 0.07) col = "#3f8a45";
        if (k === "sapin_neige" && (y < 3 || (y === hgt - 2 && r() < 0.6))) col = x < 0 ? "#ffffff" : "#dbeaf8"; g.px(12 + x, top + y, col); } } }
  } else if (k === "bouleau") { S(26, 40); g.px(11, 18, "#eeeeea", 4, 21); for (let i = 0; i < 6; i++) g.px(11 + Math.floor(r() * 3), 20 + Math.floor(r() * 18), "#2a2a2a", 2, 1); g.px(10, 38, "#5a381e", 6, 2); blob(g, 13, 12, 10, 10, ["#5c9a2a", "#80c03c", "#b5e46a"], r);
  } else if (k.startsWith("fleur:")) { const col = k.slice(6); S(20, 16);
    for (const [x, y] of [[5, 8], [11, 5], [15, 10], [9, 11]]) { g.px(x, y + 1, "#2f7a2a", 1, 4); g.px(x + 1, y + 3, "#3f9a35"); for (const [a, b] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) g.px(x + a, y + b, col); g.px(x, y, "#ffe066"); }
  } else if (k === "rocher" || k === "rocher_volc") { S(26, 20); if (k === "rocher") { blob(g, 13, 11, 11, 7, ["#5d6168", "#8d929a", "#c3c7cc"], r); g.px(8, 9, "#4a4d52", 3, 1); }
    else { blob(g, 13, 11, 11, 7, ["#211a24", "#3f3544", "#5c4f62"], r); g.px(8, 9, "#ff7a1a", 3, 1); g.px(15, 12, "#ffb347", 4, 1); }
  } else if (k === "galet") { S(22, 12); blob(g, 6, 7, 4, 3, ["#6d7178", "#9ba0a8", "#d0d3d7"], r); blob(g, 14, 6, 5, 3, ["#6d7178", "#a7abb2", "#d8dbdf"], r);
  } else if (k === "cristal") { S(22, 30); for (const [x, y, w, h] of [[11, 2, 4, 26], [6, 10, 3, 18], [16, 8, 3, 20]]) for (let i = 0; i < h; i++) { const ww = Math.min(w, Math.ceil(i / 2) + 1); g.px(x - ww + 1, y + i, "#3fb8e8", ww, 1); g.px(x + 1, y + i, "#1f7fb0", ww, 1); g.px(x, y + i, "#c9f4ff"); }
  } else if (k.startsWith("champi")) { S(18, 18); g.px(7, 10, "#f3e7d0", 4, 7); blob(g, 9, 8, 7, 4, k === "champignon" ? ["#a3141e", "#e0303a", "#ff6a6a"] : k === "champi_lum" ? ["#1f8f8a", "#3fe0d0", "#b9fff4"] : ["#5a1f80", "#8a3fc0", "#c48aff"], r); g.px(10, 5, "#ffffff", 2, 2);
  } else if (k === "geyser") { S(24, 26); blob(g, 12, 20, 10, 5, ["#211a24", "#3f3544", "#5c4f62"], r); g.px(9, 15, "#3f3544", 7, 3); g.px(10, 14, "#ff7a1a", 5, 2); g.px(11, 13, "#ffd36b", 3, 1);
  } else if (k === "braises") { S(20, 12); blob(g, 10, 7, 8, 3, ["#211a24", "#3f3544", "#554959"], r); for (let i = 0; i < 7; i++) g.px(4 + Math.floor(r() * 12), 5 + Math.floor(r() * 4), r() < 0.5 ? "#ff7a1a" : "#ffd36b");
  } else if (k === "corail") { S(22, 24); const cc = ["#ff6f91", "#ff8fab", "#ffb3c6"]; for (const [x, h] of [[6, 14], [11, 20], [16, 12]]) for (let y = 0; y < h; y++) g.px(x + Math.round(Math.sin(y / 3)), 23 - y, cc[y % 3], 2, 1);
  } else if (k === "algues") { S(18, 24); for (const [x, h, c2] of [[4, 18, "#2f9a5a"], [9, 22, "#3fbf6a"], [14, 15, "#2a7a4a"]]) for (let y = 0; y < h; y++) g.px(x + Math.round(Math.sin(y / 3 + x) * 1.5), 23 - y, c2, 2, 1);
  } else if (k === "tombe") { S(18, 24); g.px(3, 8, "#7d828a", 12, 15); g.px(5, 5, "#7d828a", 8, 3); g.px(8, 10, "#4a4d52", 2, 8); g.px(6, 12, "#4a4d52", 6, 2);
  } else if (k === "engrenage") { S(26, 26); for (let i = 0; i < 8; i++) { const a = i * Math.PI / 4; g.px(13 + Math.cos(a) * 10 - 2, 13 + Math.sin(a) * 10 - 2, "#4a525c", 4, 4); } blob(g, 13, 13, 9, 9, ["#4a525c", "#8a96a3", "#c9d2db"], r);
  } else if (k === "tuyau") { S(26, 28); g.px(4, 8, "#b86a38", 5, 18); g.px(4, 6, "#8f4a24", 16, 5); g.px(17, 6, "#b86a38", 5, 14); g.px(10, 7, "#3df2ff", 2, 2);
  } else if (k === "roseau") { S(18, 26); for (const [x, h] of [[4, 18], [8, 22], [12, 16], [15, 20]]) { g.px(x, 25 - h, "#6a8f2a", 1, h); g.px(x - 1, 25 - h, "#7a4f28", 3, 4); }
  } else if (k === "caisse") { S(22, 18); g.px(2, 4, "#8a5a33", 18, 13); g.px(2, 4, "#b5804a", 18, 2); for (const x of [2, 10, 18]) g.px(x, 4, "#5a381e", 2, 13);
  } else if (k === "parchemin" || k === "parchemin_machine") { S(20, 22); g.px(4, 4, "#f3e2b8", 12, 15); g.px(3, 2, "#d9bf8a", 14, 3); g.px(3, 18, "#d9bf8a", 14, 3); for (let i = 0; i < 4; i++) g.px(6, 7 + i * 3, "#7b5534", 8 - (i % 2) * 3, 1); if (k !== "parchemin") g.px(12, 12, "#4a525c", 6, 6);
  } else { S(20, 24); g.px(9, 10, "#6b4426", 2, 14); g.px(2, 3, "#8a5a33", 16, 9); g.px(2, 3, "#a8743f", 16, 1); g.px(5, 6, "#3a2414", 10, 1); }
  return (DEC[k] = { c: g.fin(), w: g.w, h: g.h });
}

// ------------------------------------------------------------------ le terrain d'essai, en mémoire (rien n'est envoyé)
const FS = new Map(); let horloge = 1000;
const ajoute = (c, g, txt = "") => FS.set(c, { g, contenu: txt, date: horloge++, droits: g === "d" ? 0o755 : 0o644 });
for (const d of ["biome", "biome/feu", "biome/feu/parcelle_1", "biome/feu/parcelle_2", "biome/plante", "biome/plante/parcelle_1", "biome/plante/parcelle_2", "biome/eau", "biome/eau/parcelle_1", "biome/glace", "biome/glace/parcelle_1"]) ajoute(d, "d");
ajoute("biome/feu/parcelle_1/geyser.pierre", "f"); ajoute("biome/plante/parcelle_1/chene.arbre", "f"); ajoute("biome/plante/parcelle_1/rose.fleur", "f");
ajoute("biome/plante/parcelle_1/mot.txt", "f", "Bonjour le monde\n"); ajoute("biome/eau/parcelle_1/corail.plante", "f"); ajoute("biome/plante/parcelle_1/.secret", "f", "chut\n");
let cwd = "biome";
const photo = () => { const f = {}; for (const [c, e] of FS) f[c] = [e.g, e.g === "d" ? 0 : e.contenu.length, e.date, e.droits]; return { cwd, f }; };
const parentDe = (c) => (c.includes("/") ? c.slice(0, c.lastIndexOf("/")) : "");
const nomDe = (c) => c.slice(c.lastIndexOf("/") + 1);
function chemin(arg) {
  const parts = arg.startsWith("~") || arg.startsWith("/") ? [] : cwd ? cwd.split("/") : [];
  for (const p of arg.replace(/^~\/?(terrain_terminagotchi\/?)?/, "").split("/")) { if (!p || p === ".") continue; if (p === "..") { if (!parts.length) return null; parts.pop(); } else parts.push(p); }
  return parts.join("/");
}
const ecrivable = (c) => { const p = FS.get(parentDe(c)); return !p || (p.droits & 0o200); };
function jokers(args) { const out = []; for (const a of args) { if (/[*?[]/.test(a)) { const base = chemin(a.includes("/") ? parentDe(a) : ".");
  const m = [...FS.keys()].filter((c) => parentDe(c) === base && E.correspond(nomDe(c), nomDe(a)) && !nomDe(c).startsWith(".")).sort(); if (m.length) { out.push(...m.map((c) => (cwd ? c.slice(cwd.length + 1) : c))); continue; } } out.push(a); } return out; }
function lancer(ligne) {
  // un tout petit shell : mkdir, rmdir, rm, touch, mv, cp, cd, pwd, ls, cat, echo > / >>, chmod, find (le terrain d'essai seulement)
  let sortie = [], code = 0;
  const err = (m) => { sortie.push(m); code = 1; };
  for (const seg of ligne.split("&&")) {
    let s = seg.trim(); let redir = null; const m = s.match(/(>>?)\s*(\S+)\s*$/); if (m) { redir = [m[1], m[2]]; s = s.slice(0, m.index).trim(); }
    let [cmd, ...args] = s.match(/"[^"]*"|'[^']*'|\S+/g) || [""]; args = args.map((a) => a.replace(/^["']|["']$/g, ""));
    cmd = E.canon(cmd); const opts = args.filter((a) => a.startsWith("-")).join(""); args = jokers(args.filter((a) => !a.startsWith("-")));
    if (cmd === "mkdir") for (const a of args) { const c = chemin(a); if (c === null) { err("mkdir: " + a + ": Permission denied"); continue; }
      if (FS.has(c)) { err(`mkdir: cannot create directory '${a}': File exists`); continue; }
      if (!opts.includes("p") && !FS.has(parentDe(c)) && parentDe(c)) { err(`mkdir: cannot create directory '${a}': No such file or directory`); continue; }
      if (!ecrivable(c)) { err(`mkdir: cannot create directory '${a}': Permission denied`); continue; }
      const ps = c.split("/"); for (let i = 1; i <= ps.length; i++) { const x = ps.slice(0, i).join("/"); if (!FS.has(x)) ajoute(x, "d"); } }
    else if (cmd === "touch") for (const a of args) { const c = chemin(a); if (c === null || !FS.has(parentDe(c)) && parentDe(c)) { err(`touch: cannot touch '${a}': No such file or directory`); continue; }
      if (!ecrivable(c)) { err(`touch: cannot touch '${a}': Permission denied`); continue; } if (FS.has(c)) FS.get(c).date = horloge++; else ajoute(c, "f"); }
    else if (cmd === "rm" || cmd === "rmdir") for (const a of args) { const c = chemin(a); const e = FS.get(c);
      if (!e) { err(`${cmd}: cannot remove '${a}': No such file or directory`); continue; }
      if (!ecrivable(c)) { err(`${cmd}: cannot remove '${a}': Permission denied`); continue; }
      const sousE = [...FS.keys()].filter((x) => x.startsWith(c + "/"));
      if (e.g === "d" && cmd === "rm" && !opts.includes("r")) { err(`rm: cannot remove '${a}': Is a directory`); continue; }
      if (e.g === "d" && cmd === "rmdir" && sousE.length) { err(`rmdir: failed to remove '${a}': Directory not empty`); continue; }
      for (const x of [c, ...sousE]) FS.delete(x); }
    else if (cmd === "mv" || cmd === "cp") { if (args.length < 2) { err(cmd + ": missing file operand"); continue; }
      let dest = chemin(args[args.length - 1]);
      for (const a of args.slice(0, -1)) { const c = chemin(a); const e = FS.get(c); if (!e) { err(`${cmd}: cannot stat '${a}': No such file or directory`); continue; }
        let d = dest; if (FS.get(d)?.g === "d") d = d + "/" + nomDe(c);
        if (!ecrivable(d)) { err(`${cmd}: cannot create '${args[args.length - 1]}': Permission denied`); continue; }
        if (e.g === "d" && cmd === "cp" && !opts.includes("r")) { err(`cp: -r not specified; omitting directory '${a}'`); continue; }
        for (const x of [c, ...[...FS.keys()].filter((y) => y.startsWith(c + "/"))]) { const n = d + x.slice(c.length); FS.set(n, { ...FS.get(x), date: cmd === "cp" ? horloge++ : FS.get(x).date }); if (cmd === "mv") FS.delete(x); } } }
    else if (cmd === "cd") { const c = args.length ? chemin(args[0]) : ""; if (c === null || (c && FS.get(c)?.g !== "d")) err(`bash: cd: ${args[0]}: No such file or directory`); else cwd = c; }
    else if (cmd === "pwd") sortie.push("/home/toi/terrain_terminagotchi" + (cwd ? "/" + cwd : ""));
    else if (cmd === "ls") { const c = args.length ? chemin(args[0]) : cwd; if (c === null || (c && !FS.has(c))) { err(`ls: cannot access '${args[0]}': No such file or directory`); continue; }
      sortie.push([...FS.keys()].filter((x) => parentDe(x) === c && (opts.includes("a") || !nomDe(x).startsWith("."))).map((x) => nomDe(x) + (FS.get(x).g === "d" ? "/" : "")).sort().join("  ")); }
    else if (cmd === "cat") for (const a of args) { const e = FS.get(chemin(a)); if (!e) err(`cat: ${a}: No such file or directory`); else if (e.g === "d") err(`cat: ${a}: Is a directory`); else sortie.push(e.contenu.replace(/\n$/, "")); }
    else if (cmd === "echo") { const txt = args.join(" ") + "\n";
      if (redir) { const c = chemin(redir[1]); if (c === null || !ecrivable(c)) { err(`bash: ${redir[1]}: Permission denied`); continue; }
        if (FS.has(c)) { const e = FS.get(c); e.contenu = redir[0] === ">>" ? e.contenu + txt : txt; e.date = horloge++; } else ajoute(c, "f", txt); }
      else sortie.push(txt.trim()); }
    else if (cmd === "chmod") { const mode = (s.match(/chmod\s+(\S+)/) || [])[1] || ""; for (const a of args.slice(1)) { const e = FS.get(chemin(a)); if (!e) { err(`chmod: cannot access '${a}': No such file or directory`); continue; }
      if (/^[0-7]{3}$/.test(mode)) e.droits = parseInt(mode, 8);
      else { const mm = mode.match(/^([ugoa]*)([+-])([rwx]+)$/); if (!mm) { err("chmod: invalid mode: '" + mode + "'"); continue; }
        let bits = 0; const qui = mm[1] || "a"; for (const p of mm[3]) for (const q of qui === "a" ? "ugo" : qui) bits |= { r: 4, w: 2, x: 1 }[p] << { u: 6, g: 3, o: 0 }[q];
        e.droits = mm[2] === "+" ? e.droits | bits : e.droits & ~bits; } } }
    else if (cmd === "find") { const motif = (s.match(/-name\s+(\S+)/) || [])[1]?.replace(/["']/g, ""); const base = chemin(args[0] && !args[0].startsWith("*") ? args[0] : ".");
      sortie.push(...[...FS.keys()].filter((x) => (base === "" || x.startsWith(base + "/")) && (!motif || E.correspond(nomDe(x), motif))).sort().map((x) => "./" + (base ? x.slice(base.length + 1) : x))); }
    else if (cmd === "clear" || cmd === "") { }
    else err(cmd + ": command not found (" + tr("site.essai_seulement") + ")");
    if (code) break;
  }
  return { code, sortie: sortie.join("\n") };
}

// ------------------------------------------------------------------ la vue
const cv = $("#scene"), ctx = cv.getContext("2d");
let W = 0, H = 0, dpr = 1, cam = { x: 0, y: 0, z: 2 }, but = null, manuel = false, retour = null;
let carte = null, ordre = [], maison = {}, refuge = [], sel = null, iso = null, now = 0;
const EQUIPE = [["braisillon", "feu"], ["glandouille", "plante"], ["gouttelin", "eau"], ["givrichon", "glace"], ["fumerole", "feu"], ["zapiot", "ciel"], ["etincelot", "feu"]]
  .map(([id, ty], i) => ({ id, nom: id[0].toUpperCase() + id.slice(1), type: ty, stade: i % 3 ? "bebe" : "enfant", guide: i === 0 }));
const imgs = {}; for (const e of EQUIPE) { const im = new Image(); im.src = `/portraits/${e.id}/classique_${e.stade}.webp`; imgs[e.id] = im; }
const creas = {}; const effets = [], parts = [];
function terrainDe() { const out = {}; for (const ty of G.TYPES) { const r = "biome/" + ty; if (!FS.has(r)) continue;
  out[ty] = [...FS.keys()].filter((c) => parentDe(c) === r && FS.get(c).g === "d").sort((a, b) => (parseInt(a.match(/\d+$/)) || 0) - (parseInt(b.match(/\d+$/)) || 0) || a.localeCompare(b)).slice(0, 8)
    .map((p) => ({ nom: nomDe(p), objets: [...FS.keys()].filter((c) => parentDe(c) === p && FS.get(c).g === "f" && !nomDe(c).startsWith(".")).map(nomDe).sort() })); } return out; }
const morph = {}; const fantomes = [];
function sommet(h) { let [x, y] = G.solXY(h.q, h.r); y -= h.h * HZ; const m = morph[h.cle];
  if (m) { const k = clamp((now - m[2]) / 0.8, 0, 1); if (k >= 1) delete morph[h.cle]; else { const e = ease(k); x = m[0] + (x - m[0]) * e; y = m[1] + (y - m[1]) * e; } } return [x, y]; }
function reconstruire() {
  const ancien = carte; const anc = {}; if (ancien) for (const h of ancien.hex.values()) anc[h.cle] = sommet(h);
  carte = G.construire(terrainDe()); carte.parCle = new Map([...carte.hex.values()].map((h) => [h.cle, h]));
  ordre = [...carte.hex.values()].sort((a, b) => G.solXY(a.q, a.r)[1] - G.solXY(b.q, b.r)[1] || a.q - b.q);
  for (const h of carte.hex.values()) { const o = anc[h.cle]; if (o) { const n = sommet(h); if (Math.abs(o[0] - n[0]) > 0.5 || Math.abs(o[1] - n[1]) > 0.5) morph[h.cle] = [o[0], o[1], now]; } }
  if (ancien) for (const h of ancien.hex.values()) if (!carte.parCle.has(h.cle)) fantomes.push({ h, x: anc[h.cle][0], y: anc[h.cle][1], t0: now + h.d * 0.07 });
  const avant = { ...maison }; const r = G.placeCreatures(carte, EQUIPE.map((e) => [e.id, e.type])); maison = r.maison; refuge = r.refuge;
  for (const e of EQUIPE) { const cr = (creas[e.id] ||= { info: e, at: null, seg: null, chemin: [], etat: "idle", jusqu: 0, face: 1, ph: Math.random() * 6, vol: null });
    if (maison[e.id]) { if (avant[e.id] !== maison[e.id] || !carte.parCle.has(cr.at)) poser(cr, !!ancien); } else cr.at = null; }
  if (!ancien) toutVoir(false);
  panneau();
}
const peut = (cr, h) => h && h.region === cr.info.type && !h.block;
function poser(cr, arrivee) { const p = carte.par[maison[cr.info.id]]; const hs = G.FLOWER.map(([a, b]) => carte.at(p.centre[0] + a, p.centre[1] + b)).filter((h) => peut(cr, h)).sort((a, b) => a.d - b.d);
  const h = hs[Math.floor(Math.random() * Math.min(3, hs.length))] || carte.at(...p.centre); cr.at = h.cle; cr.seg = null; cr.chemin = []; cr.etat = "idle"; cr.jusqu = now + 1;
  if (arrivee) { const s = sommet(h); cr.vol = [s[0], s[1] - 170, now + 0.6, 1]; } }
function penser(cr) { const r = Math.random(); if (r < 0.1) { cr.etat = "dort"; cr.jusqu = now + 5; return; } if (r < 0.3) { cr.etat = "idle"; cr.jusqu = now + 2; return; }
  const dep = carte.parCle.get(cr.at); const prev = new Map([[dep.cle, null]]); const file = [[dep, 0]], out = [];
  while (file.length) { const [h, d] = file.shift(); out.push([h, d]); if (d >= 6) continue; for (const [a, b] of G.DIRS) { const n = carte.at(h.q + a, h.r + b); if (!n || prev.has(n.cle) || !peut(cr, n) || Math.abs(n.h - h.h) > 2.9) continue; prev.set(n.cle, h.cle); file.push([n, d + 1]); } }
  const cs = out.filter((o) => o[1] >= 2); if (!cs.length) { cr.etat = "idle"; cr.jusqu = now + 2; return; }
  let b = cs[Math.floor(Math.random() * cs.length)][0].cle; const ch = []; while (prev.get(b)) { ch.unshift(b); b = prev.get(b); } cr.chemin = ch; cr.etat = "marche"; }
function posCrea(cr) { let x, y, d; if (cr.seg) { const [a, b, k] = cr.seg; const ha = carte.parCle.get(a), hb = carte.parCle.get(b) || ha; const pa = sommet(ha), pb = sommet(hb);
  x = pa[0] + (pb[0] - pa[0]) * k; y = pa[1] + (pb[1] - pa[1]) * k * k * (3 - 2 * k); d = Math.max(G.solXY(ha.q, ha.r)[1], G.solXY(hb.q, hb.r)[1]) + 0.5; }
  else { const h = carte.parCle.get(cr.at); [x, y] = sommet(h); d = G.solXY(h.q, h.r)[1] + 0.5; }
  if (cr.vol) { const q = clamp((now - cr.vol[2]) / cr.vol[3], 0, 1); x = cr.vol[0] + (x - cr.vol[0]) * q * q; y = cr.vol[1] + (y - cr.vol[1]) * q * q; d = 1e6; } return [x, y, d]; }
function avancer(cr, dt) { if (!carte.parCle.has(cr.at)) { if (maison[cr.info.id]) poser(cr, false); return; }
  if (cr.vol) { if (now >= cr.vol[2] + cr.vol[3]) { cr.vol = null; eclat(posCrea(cr), "etoile", 10); } else return; }
  if (cr.seg) { cr.seg[2] += dt * 1.3; if (cr.seg[2] >= 1) { cr.at = cr.seg[1]; cr.seg = null; } }
  else if (cr.etat === "marche") { if (!cr.chemin.length) { cr.etat = "idle"; cr.jusqu = now + 1.5; return; } const n = cr.chemin.shift(); const ha = carte.parCle.get(cr.at), hb = carte.parCle.get(n);
    if (!hb || !peut(cr, hb)) { cr.etat = "idle"; cr.chemin = []; return; } const xa = G.solXY(ha.q, ha.r)[0], xb = G.solXY(hb.q, hb.r)[0]; if (Math.abs(xb - xa) > 0.1) cr.face = xb > xa ? 1 : -1; cr.seg = [cr.at, n, 0]; }
  else if (now > cr.jusqu) penser(cr); }
function eclat(p, sorte, n = 14) { const cols = sorte === "confetti" ? ["#ff5f6d", "#ffd54f", "#3ddc84", "#5fafff", "#b284ff"] : sorte === "pouf" ? ["#ffffff", "#e6e6e6", "#cfd8dc"] : ["#ffe066", "#fff6b0", "#ffffff"];
  for (let i = 0; i < n; i++) { const a = Math.random() * Math.PI * 2, s = 10 + Math.random() * 24; parts.push({ x: p[0], y: p[1] - 8, vx: Math.cos(a) * s, vy: Math.sin(a) * s * 0.6 - (sorte === "confetti" ? 30 : 8), v: 0, max: 0.6 + Math.random() * 0.6, c: cols[i % cols.length], g: sorte === "confetti" ? 60 : 0 }); } }

function hexDe(ch) { if (!carte || !ch) return null; const p = ch.split("/"); if (p.length < 2 || p[0] !== "biome") return null;
  if (p.length === 2) { const ps = carte.parcelles.find((x) => x.type === p[1]); return ps ? carte.at(...ps.centre) : null; }
  const par = carte.par[p[1] + "/" + p[2]]; if (!par) return null; if (p.length >= 4 && par.poses[p[3]]) { const o = par.poses[p[3]].off; return carte.at(par.centre[0] + o[0], par.centre[1] + o[1]); } return carte.at(...par.centre); }
const milieu = () => { const hs = [...carte.hex.values()]; return [hs.reduce((s, h) => s + G.solXY(h.q, h.r)[0], 0) / hs.length, hs.reduce((s, h) => s + G.solXY(h.q, h.r)[1], 0) / hs.length - 20]; };
const pointDe = (ch) => { const h = hexDe(ch); return h ? sommet(h) : milieu(); };
const guidePt = () => { const cr = Object.values(creas).find((c) => c.at && c.info.guide) || Object.values(creas).find((c) => c.at); return cr ? posCrea(cr) : milieu(); };
function points(e) {
  if (e._av) return ["deplace", "renomme", "cd"].includes(e.type) ? [e._av[0], pointDe(e.vers)] : e._av;
  if (["jokers", "find", "groupe"].includes(e.type)) return (e.chemins || []).slice(0, 20).map(pointDe);
  if (["deplace", "renomme", "copie", "cd"].includes(e.type)) return [pointDe(e.de), pointDe(e.vers)];
  if (e.type === "messager") { const g = guidePt(); return [g, G.TYPES.includes(e.cible) ? pointDe("biome/" + e.cible) : [g[0] + 120, g[1] - 90]]; }
  if (["lucioles", "photo"].includes(e.type)) return [guidePt()];
  if (e.type === "tuyau") return [pointDe(e.source || "biome/" + e.region)];
  return [pointDe(e.chemin)];
}
const dits = JSON.parse(sessionStorage.getItem("tg_monde_dits") || "{}");
function jouer(ligne) {
  const avant = photo(); const r = lancer(ligne); const apres = photo();
  const evs = E.evenements(ligne, avant, apres, r.code, r.sortie);
  for (const e of evs) if (["objet-", "dossier-", "deplace", "renomme", "cd"].includes(e.type)) e._av = [pointDe(e.chemin || e.de)];
    else if (e.type === "groupe" && String(e.sorte).endsWith("-")) e._av = e.chemins.map(pointDe);
  reconstruire();
  let d = 0, premier = null;
  for (const e of evs.slice(0, 12)) { const pts = points(e); effets.push({ e, t0: now + d, du: e.type === "jokers" ? 1.1 : 1.8, pts }); premier ||= pts[0]; d += e.type === "jokers" ? 0.55 : 0.3;
    if (e.type === "lire") e.lignes = (FS.get(e.chemin)?.contenu || "").split("\n").slice(0, 3); }
  if (premier && !manuel) { retour ||= { ...cam }; but = { x: premier[0], y: premier[1], z: Math.max(cam.z, 1.6 * dpr) }; }
  const k = E.aDire(dits, evs); if (k) { dire(tr(k)); dits[k] = (dits[k] || 0) + 1; sessionStorage.setItem("tg_monde_dits", JSON.stringify(dits)); }
  return r;
}
let bulle = null; function dire(txt) { const cr = Object.values(creas).find((c) => c.at && c.info.guide) || Object.values(creas).find((c) => c.at); bulle = { cr, txt, fin: now + 5 }; }

function resize() { dpr = Math.max(1, Math.min(3, window.devicePixelRatio || 1)); const cw = $("#cwrap").clientWidth; const ch = Math.round(clamp(cw * (cw < 600 ? 1.05 : 0.62), 340, 600));
  cv.style.height = ch + "px"; W = Math.round(cw * dpr); H = Math.round(ch * dpr); cv.width = W; cv.height = H; if (!manuel) toutVoir(false); }
function ajuster(hs, doux, zmax) { let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9; for (const h of hs) { const [x, y] = G.solXY(h.q, h.r); x0 = Math.min(x0, x - HR); x1 = Math.max(x1, x + HR); y0 = Math.min(y0, y - h.h * HZ - HH - (h.scen ? 30 : 0)); y1 = Math.max(y1, y - h.base * HZ + HH + h.pilier); }
  const z = clamp(Math.min(W / (x1 - x0 + 16), H / (y1 - y0 + 36)) * 0.95, 0.5, zmax * dpr); const g = { x: (x0 + x1) / 2, y: (y0 + y1 - 20) / 2, z }; if (doux) but = g; else { cam = g; but = null; } }
function toutVoir(doux = true) { manuel = false; if (carte) ajuster([...carte.hex.values()], doux, 3.2); }
const ex = (x) => (x - cam.x) * cam.z + W / 2, ey = (y) => (y - cam.y) * cam.z + H / 2;
const mx = (x) => (x - W / 2) / cam.z + cam.x, my = (y) => (y - H / 2) / cam.z + cam.y;
const alphaIso = (r, b) => (!iso || r === iso || (b && b.includes(iso)) ? 1 : 0.32);

function dessiner() {
  const z = cam.z; ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.imageSmoothingEnabled = false;
  const gr = ctx.createLinearGradient(0, 0, 0, H); gr.addColorStop(0, "#7cc6f0"); gr.addColorStop(1, "#bfe7ff"); ctx.fillStyle = gr; ctx.fillRect(0, 0, W, H);
  if (!carte || !carte.parcelles.length) { ctx.fillStyle = "#2b2416"; ctx.font = 16 * dpr + "px sans-serif"; ctx.textAlign = "center"; ctx.fillText(tr("monde.vide"), W / 2, H / 2); ctx.textAlign = "left"; return; }
  const tombe = {}, caches = new Set();
  for (const ef of effets) { const age = now - ef.t0; if (ef.e.type === "dossier+" && age < 1.4) for (const c of ef.e.parcelles?.length ? ef.e.parcelles : [ef.e.chemin]) { const p = c.split("/"); if (p.length >= 3) tombe[p[1] + "/" + p[2]] = age; }
    if (["objet+", "copie", "deplace", "renomme"].includes(ef.e.type) && age < 0.9) caches.add(ef.e.vers || ef.e.chemin); }
  const mobs = [];
  for (const p of carte.parcelles) for (const [nom, v] of Object.entries(p.poses)) { const h = carte.at(p.centre[0] + v.off[0], p.centre[1] + v.off[1]); mobs.push({ d: G.solXY(h.q, h.r)[1] + 0.4, p, nom, v, h }); }
  for (const cr of Object.values(creas)) if (cr.at && carte.parCle.has(cr.at)) mobs.push({ d: posCrea(cr)[2], cr });
  mobs.sort((a, b) => a.d - b.d); let j = 0;
  const dessineMob = (m) => {
    if (m.cr) { const cr = m.cr, im = imgs[cr.info.id], [x, y] = posCrea(cr), h0 = STADE_H[cr.info.stade], a = alphaIso(cr.info.type); ctx.globalAlpha = a * 0.3; ctx.fillStyle = "#000"; ctx.beginPath(); ctx.ellipse(ex(x), ey(y) + z, h0 * 0.36 * z, h0 * 0.13 * z, 0, 0, 7); ctx.fill(); ctx.globalAlpha = a;
      const bob = cr.seg ? Math.abs(Math.sin(now * 9 + cr.ph)) * 2 : 0;
      if (sel === cr.info.id) { ctx.strokeStyle = "#ffe066"; ctx.lineWidth = 2 * dpr; ctx.beginPath(); ctx.ellipse(ex(x), ey(y) + z, (h0 * 0.5 + 5) * z, (h0 * 0.2 + 3) * z, 0, 0, 7); ctx.stroke(); }
      if (im.complete && im.naturalWidth) { const k = h0 * z / im.naturalHeight, w = im.naturalWidth * k; ctx.save(); ctx.translate(ex(x), ey(y) - bob * z); ctx.scale(cr.face, cr.etat === "dort" ? 0.95 : 1 + Math.sin(now * 2.2 + cr.ph) * 0.018); ctx.imageSmoothingEnabled = true; ctx.drawImage(im, -w / 2, -h0 * z, w, h0 * z); ctx.restore(); ctx.imageSmoothingEnabled = false; }
      ctx.globalAlpha = 1; zones.push({ x: ex(x) - h0 * 0.5 * z - 6, y: ey(y) - h0 * z - 6, w: h0 * z + 12, h: h0 * z + 12, a: "crea:" + cr.info.id }); return; }
    const ch = "biome/" + m.p.id + "/" + m.nom; if (caches.has(ch)) return; const [x, y] = sommet(m.h), im = decor(m.v.k), a = alphaIso(m.p.type);
    let rot = 0; for (const ef of effets) { const age = now - ef.t0; if (age >= 0 && age < ef.du && (ef.e.chemin === ch || (ef.e.chemins || []).includes(ch))) { rot = Math.sin(age * 30) * 0.1 * Math.max(0, 1 - age / 1.2);
      if (["jokers", "find"].includes(ef.e.type)) { ctx.fillStyle = `rgba(255,236,128,${0.6 * (1 - age / ef.du)})`; ctx.beginPath(); ctx.arc(ex(x), ey(y) - im.h * z / 2, 26 * z, 0, 7); ctx.fill(); } } }
    ctx.globalAlpha = a * 0.28; ctx.fillStyle = "#000"; ctx.beginPath(); ctx.ellipse(ex(x), ey(y) + z, im.w * 0.32 * z, im.w * 0.12 * z, 0, 0, 7); ctx.fill(); ctx.globalAlpha = a;
    ctx.save(); ctx.translate(ex(x), ey(y) + 2 * z); ctx.rotate(rot); ctx.drawImage(im.c, -im.w / 2 * z, -im.h * z, im.w * z, im.h * z); ctx.restore(); ctx.globalAlpha = 1; };
  for (const h of ordre) { const dh = G.solXY(h.q, h.r)[1]; while (j < mobs.length && mobs[j].d < dh) dessineMob(mobs[j++]);
    const [x, y] = sommet(h); let oy = 0, a = alphaIso(h.region, h.between); const ch = tombe[h.parcelle];
    if (ch !== undefined) { const k = clamp((ch - h.d * 0.12) / 0.5, 0, 1); if (k <= 0) continue; oy = (1 - easeBack(k)) * -60; a = Math.min(a, k); }
    const s = sprite(h.kind, h.v, h.mur, h.pilier), sc = h.float ? 0.84 : 1, fy = h.float ? Math.sin(now * 1.1 + h.q * 0.7 + h.r) * 1.2 : 0;
    ctx.globalAlpha = a; ctx.drawImage(s.c, Math.round(ex(x) - s.ax * z * sc), Math.round(ey(y + oy + fy) - s.ay * z * sc), Math.round(s.c.width * z * sc), Math.round(s.c.height * z * sc));
    if (h.kind === "lave") { ctx.globalAlpha = a * (0.22 + 0.22 * Math.sin(now * 3 - (h.flow || 0) * 1.4)); ctx.fillStyle = "#ffe28a"; ctx.beginPath(); ctx.ellipse(ex(x), ey(y + oy), HR * 0.8 * z, HR * 0.5 * z, 0, 0, 7); ctx.fill(); }
    if (h.scen) { const im = decor(h.scen.k); ctx.globalAlpha = a; ctx.drawImage(im.c, ex(x) - im.w / 2 * z * h.scen.s, ey(y + oy) + 2 * z - im.h * z * h.scen.s, im.w * z * h.scen.s, im.h * z * h.scen.s); }
    ctx.globalAlpha = 1; }
  while (j < mobs.length) dessineMob(mobs[j++]);
  for (const f of fantomes) { const age = Math.max(0, now - f.t0); if (age > 1) continue; const s = sprite(f.h.kind, f.h.v, f.h.mur, f.h.pilier); ctx.globalAlpha = Math.max(0, 1 - age); ctx.drawImage(s.c, ex(f.x) - s.ax * z, ey(f.y + age * age * 160) - s.ay * z, s.c.width * z, s.c.height * z); ctx.globalAlpha = 1; }
  // les contours : là où l'on est (vert), les parcelles libres (pointillés pâles)
  const occ = new Set(Object.values(maison)); const ici = cwd.startsWith("biome/") ? (cwd.split("/").length >= 3 ? [cwd.split("/").slice(1, 3).join("/")] : carte.parcelles.filter((p) => p.type === cwd.split("/")[1]).map((p) => p.id)) : [];
  for (const p of carte.parcelles) { const vert = ici.includes(p.id); if (!vert && occ.has(p.id)) continue; ctx.strokeStyle = vert ? "#3dff7c" : "rgba(255,248,220,.6)"; ctx.lineWidth = (vert ? 2 : 1.4) * dpr; ctx.setLineDash(vert ? [6 * dpr, 4 * dpr] : [2 * dpr, 3 * dpr]); ctx.lineDashOffset = -now * 20; ctx.beginPath();
    for (const [a, b] of G.FLOWER) { const h = carte.at(p.centre[0] + a, p.centre[1] + b); const [x, y] = sommet(h); G.DIRS.forEach(([da, db], i) => { const n = carte.at(h.q + da, h.r + db); if (n && n.parcelle === p.id) return; const [k1, k2] = G.DIR_EDGE[i];
      ctx.moveTo(ex(x) + Math.cos(k1 * Math.PI / 3) * HR * z, ey(y) + Math.sin(k1 * Math.PI / 3) * HR * G.TILT * z); ctx.lineTo(ex(x) + Math.cos(k2 * Math.PI / 3) * HR * z, ey(y) + Math.sin(k2 * Math.PI / 3) * HR * G.TILT * z); }); }
    ctx.stroke(); } ctx.setLineDash([]);
  for (const p of parts) { ctx.globalAlpha = 1 - p.v / p.max; ctx.fillStyle = p.c; ctx.fillRect(ex(p.x), ey(p.y), 2 * z, 2 * z); } ctx.globalAlpha = 1;
  for (const ef of effets) if (now >= ef.t0) effet(ef, now - ef.t0);
  // les étiquettes des régions
  ctx.font = `bold ${12 * dpr}px sans-serif`; ctx.textBaseline = "middle";
  for (const ty of G.TYPES) { const ps = carte.parcelles.filter((p) => p.type === ty); if (!ps.length || (iso && iso !== ty)) continue;
    const hs = ps.flatMap((p) => G.FLOWER.map(([a, b]) => carte.at(p.centre[0] + a, p.centre[1] + b))); const top = hs.reduce((m, h) => (G.solXY(h.q, h.r)[1] < G.solXY(m.q, m.r)[1] ? h : m));
    const xw = G.solXY(top.q, top.r)[0], yw = Math.min(...hs.filter((h) => Math.abs(G.solXY(h.q, h.r)[0] - xw) < HR * 4).map((h) => sommet(h)[1] - (h.scen ? 24 : 0))) - 10;
    const n = Object.values(maison).filter((v) => v.startsWith(ty + "/")).length, att = EQUIPE.filter((e) => e.type === ty && refuge.includes(e.id)).length;
    const txt = `${EMOJI[ty]} ${ty}/ ${n}/${ps.length}` + (att ? `  +${att}` : ""), tw = ctx.measureText(txt).width + 18 * dpr; const actif = cwd.startsWith("biome/" + ty);
    ctx.fillStyle = actif ? "rgba(5,20,10,.92)" : "rgba(5,10,15,.78)"; ctx.fillRect(ex(xw) - tw / 2, ey(yw) - 22 * dpr, tw, 22 * dpr); ctx.strokeStyle = actif ? "#3dff7c" : COUL[ty]; ctx.lineWidth = dpr; ctx.strokeRect(ex(xw) - tw / 2, ey(yw) - 22 * dpr, tw, 22 * dpr);
    ctx.fillStyle = actif ? "#3dff7c" : "#e6f0ff"; ctx.fillText(txt, ex(xw) - tw / 2 + 9 * dpr, ey(yw) - 11 * dpr); zones.push({ x: ex(xw) - tw / 2, y: ey(yw) - 22 * dpr, w: tw, h: 22 * dpr, a: "region:" + ty }); }
  if (bulle && now < bulle.fin) { const p = bulle.cr ? posCrea(bulle.cr) : [cam.x, cam.y]; ctx.font = `${13 * dpr}px sans-serif`; const ls = []; let l = ""; for (const m of bulle.txt.split(" ")) { if (ctx.measureText(l + " " + m).width > 240 * dpr && l) { ls.push(l); l = m; } else l = l ? l + " " + m : m; } ls.push(l);
    const tw = Math.max(...ls.map((x) => ctx.measureText(x).width)) + 20 * dpr, bh = ls.length * 17 * dpr + 12 * dpr, bx = clamp(ex(p[0]) - tw / 2, 6, W - tw - 6), by = clamp(ey(p[1]) - 50 * cam.z - bh, 6, H - bh - 6);
    ctx.fillStyle = "#000"; ctx.fillRect(bx - 2, by - 2, tw + 4, bh + 4); ctx.fillStyle = "#fffbe8"; ctx.fillRect(bx, by, tw, bh); ctx.fillStyle = "#2b2416"; ls.forEach((x, i) => ctx.fillText(x, bx + 10 * dpr, by + 14 * dpr + i * 17 * dpr)); }
}
let zones = [];
function etiquette(txt, x, y, c, fin) { ctx.font = `bold ${12.5 * dpr}px sans-serif`; const tw = ctx.measureText(txt).width + 16 * dpr; ctx.globalAlpha = fin; ctx.fillStyle = "rgba(5,10,15,.86)"; ctx.fillRect(x - tw / 2, y - 11 * dpr, tw, 22 * dpr); ctx.strokeStyle = c; ctx.strokeRect(x - tw / 2, y - 11 * dpr, tw, 22 * dpr); ctx.fillStyle = c; ctx.textAlign = "center"; ctx.fillText(txt, x, y); ctx.textAlign = "left"; ctx.globalAlpha = 1; }
function effet(ef, age) {
  const e = ef.e, z = cam.z, k = clamp(age / ef.du, 0, 1), fin = 1 - k, pts = ef.pts.map(([x, y]) => [ex(x), ey(y)]), p0 = pts[0];
  if (!p0) return;
  switch (e.type) {
    case "jokers": for (const [x, y] of pts) { ctx.strokeStyle = `rgba(255,224,102,${fin})`; ctx.lineWidth = 2 * dpr; ctx.beginPath(); ctx.arc(x, y - 10 * z, (12 + 6 * k) * z, 0, 7); ctx.stroke(); } etiquette("✱ " + e.n, p0[0], p0[1] - 40 * z, "#ffd54f", fin); break;
    case "dossier+": if (age < 0.05) for (const p of ef.pts) eclat([p[0], p[1] - 40], "pouf", 16); etiquette("+ " + nomDe(e.chemin) + "/", p0[0], p0[1] - 30 * z - age * 26, "#3ddc84", fin); break;
    case "dossier-": if (age < 0.05) eclat(ef.pts[0], "pouf", 20); etiquette("− " + nomDe(e.chemin) + "/", p0[0], p0[1] - 30 * z - age * 26, "#ff5f6d", fin); break;
    case "objet+": { const im = decor(G.deco(nomDe(e.chemin), e.region || "plante")[0]); const q = clamp(age / 0.8, 0, 1);
      if (e.via === "touch" || e.via === "autre") { ctx.fillStyle = `rgba(255,246,176,${0.45 * Math.sin(Math.min(1, age / 0.6) * Math.PI)})`; ctx.fillRect(p0[0] - 5 * z, p0[1] - 140 * z, 10 * z, 140 * z); }
      if (e.via === "ecrire") for (let i = 0; i < 3; i++) { const qq = clamp(q * 1.3 - i * 0.12, 0, 1); ctx.fillStyle = `rgba(95,175,255,${1 - qq * 0.7})`; ctx.fillRect(20 + (p0[0] - 20) * ease(qq), 20 + (p0[1] - 50) * ease(qq), 8 * z, 2 * z); }
      const yy = p0[1] - (1 - easeBack(q)) * 70 * z; ctx.drawImage(im.c, p0[0] - im.w / 2 * z, yy + 2 * z - im.h * z, im.w * z, im.h * z); if (age > 0.8) etiquette(tr("efx.nouveau"), p0[0], p0[1] - (im.h + 8) * z, "#3ddc84", fin); break; }
    case "objet-": if (age < 0.05) eclat([ef.pts[0][0], ef.pts[0][1] - 8], "confetti", 26); etiquette(tr("efx.pas_corbeille"), p0[0], p0[1] - 30 * z - age * 26, "#ff5f6d", fin); break;
    case "touche": case "modifie": etiquette("🕒 " + tr("efx.heure"), p0[0], p0[1] - 34 * z, "#4dd0e1", fin); break;
    case "deplace": case "renomme": case "copie": { const [x1, y1] = pts[1]; const q = clamp(age, 0, 1); ctx.strokeStyle = `rgba(255,213,79,${fin})`; ctx.setLineDash([4 * dpr, 4 * dpr]); ctx.beginPath(); ctx.moveTo(p0[0], p0[1]); ctx.quadraticCurveTo((p0[0] + x1) / 2, Math.min(p0[1], y1) - 80 * z, x1, y1); ctx.stroke(); ctx.setLineDash([]);
      const im = decor(G.deco(nomDe(e.vers), e.vers.split("/")[1] || "plante")[0]); const bx = p0[0] + (x1 - p0[0]) * ease(q), by = p0[1] + (y1 - p0[1]) * ease(q) - Math.sin(q * Math.PI) * 50 * z;
      if (e.type === "copie") { ctx.fillStyle = `rgba(255,255,255,${Math.max(0, 1 - age * 3)})`; ctx.beginPath(); ctx.arc(p0[0], p0[1] - 10 * z, 40 * z, 0, 7); ctx.fill(); ctx.drawImage(im.c, p0[0] - im.w / 2 * z, p0[1] + 2 * z - im.h * z, im.w * z, im.h * z); }
      if (q < 1 || e.type !== "copie") ctx.drawImage(im.c, bx - im.w / 2 * z, by + 2 * z - im.h * z, im.w * z, im.h * z);
      if (e.type === "renomme") etiquette(nomDe(e.de) + " → " + nomDe(e.vers), x1, y1 - 34 * z, "#ffd54f", fin); break; }
    case "ecrit": if (e.mode === ">" && age < 0.6) { ctx.fillStyle = `rgba(255,95,109,${1 - age / 0.6})`; for (let i = 0; i < 3; i++) ctx.fillRect(p0[0] - 8 * z + i * 3, p0[1] - 20 * z - age * 120 - i * 10, 8 * z, 1.6 * z); }
      etiquette(e.mode === ">>" ? "» " + tr("efx.ajoute") : "> " + tr("efx.efface"), p0[0], p0[1] - 40 * z, e.mode === ">>" ? "#5fafff" : "#ff5f6d", fin); break;
    case "droits": { ctx.strokeStyle = `rgba(220,240,255,${fin})`; ctx.lineWidth = 1.5 * dpr; ctx.beginPath(); ctx.ellipse(p0[0], p0[1] - 16 * z - (1 - easeBack(clamp(age / 0.5, 0, 1))) * 40 * z, 30 * z, 34 * z, 0, 0, 7); ctx.stroke();
      [0o200, 0o020, 0o002].forEach((bit, i) => { const ouvert = ((age > 0.7 ? e.apres : e.avant) & bit) !== 0; ctx.fillStyle = ouvert ? "#3ddc84" : "#ff5f6d"; ctx.fillRect(p0[0] + (i - 1) * 22 * z - 6 * z, p0[1] - 58 * z, 12 * z, 9 * z); ctx.strokeStyle = ctx.fillStyle; ctx.beginPath(); ctx.arc(p0[0] + (i - 1) * 22 * z + (ouvert ? 3 * z : 0), p0[1] - 60 * z, 4 * z, Math.PI, 0); ctx.stroke(); }); break; }
    case "refus": { const b = Math.abs(Math.sin(age * 9)) * 14 * z * fin; if (e.raison === "droits") { ctx.fillStyle = `rgba(255,95,109,${fin})`; ctx.fillRect(p0[0] - 8 * z, p0[1] - 30 * z - b, 16 * z, 12 * z); }
      else if (e.raison === "pas_vide") etiquette(tr("efx.pas_vide"), p0[0] + Math.sin(age * 40) * 4 * fin, p0[1] - 30 * z, "#ffd54f", fin);
      else if (e.raison === "existe") etiquette(tr("efx.existe"), p0[0], p0[1] - 34 * z, "#ffd54f", fin);
      else { ctx.fillStyle = `rgba(255,95,109,${fin})`; ctx.font = `bold ${26 * dpr}px sans-serif`; ctx.textAlign = "center"; ctx.fillText("?", p0[0], p0[1] - 30 * z - b); ctx.textAlign = "left"; } break; }
    case "cd": { const [x1, y1] = pts[1]; const q = ease(clamp(age / 0.9, 0, 1)); const bx = p0[0] + (x1 - p0[0]) * q, by = p0[1] + (y1 - p0[1]) * q - Math.sin(q * Math.PI) * 60 * z;
      ctx.fillStyle = "#ffd54f"; ctx.beginPath(); ctx.arc(bx, by, 5 * z, 0, 7); ctx.fill(); ctx.strokeStyle = "#ffd54f"; ctx.beginPath(); ctx.arc(bx, by, (11 + 3 * Math.sin(age * 8)) * z, 0, 7); ctx.stroke(); if (age > 0.9) etiquette("◉ " + tr("efx.ici"), x1, y1 - 28 * z, "#ffd54f", fin); break; }
    case "pwd": etiquette(["~", "terrain_terminagotchi", ...(e.chemin || "").split("/").filter(Boolean)].slice(-4).join(" / "), p0[0], p0[1] - 60 * z, "#4dd0e1", fin); break;
    case "ls": if (e.caches) etiquette("👁 " + tr("efx.caches"), p0[0], p0[1] - 70 * z, "#b284ff", fin); else etiquette("ls · " + e.n, p0[0], p0[1] - 40 * z, "#fffad2", fin); break;
    case "find": ctx.strokeStyle = `rgba(77,208,225,${fin})`; ctx.lineWidth = 2 * dpr; ctx.beginPath(); ctx.arc(p0[0], p0[1], 260 * z * k + 5, 0, 7); ctx.stroke(); etiquette(e.n ? tr("efx.trouves", { n: e.n }) : tr("efx.rien_trouve"), p0[0], p0[1] - 50 * z, "#4dd0e1", fin); break;
    case "lire": { const q = clamp(age / 0.6, 0, 1), w = 150 * dpr, h = (18 + 52 * ease(q)) * dpr; ctx.globalAlpha = fin; ctx.fillStyle = "#f3e2b8"; ctx.fillRect(p0[0] - w / 2, p0[1] - 50 * z - h, w, h); ctx.fillStyle = "#3b2414"; ctx.font = `${11 * dpr}px monospace`;
      (e.lignes || []).forEach((l, i) => { if ((18 + i * 16) * dpr < h) ctx.fillText(l.slice(0, 22), p0[0] - w / 2 + 8 * dpr, p0[1] - 50 * z - h + (14 + i * 16) * dpr); }); ctx.globalAlpha = 1; break; }
    case "groupe": etiquette((String(e.sorte).endsWith("-") ? "− " : "+ ") + e.n, p0[0], p0[1] - 40 * z, String(e.sorte).endsWith("-") ? "#ff5f6d" : "#3ddc84", fin); break;
    case "tuyau": etiquette((e.etapes || []).join(" | "), p0[0], p0[1] - 80 * z, "#b284ff", fin); break;
  }
}
// ------------------------------------------------------------------ la liste et la fiche (la fiche À LA PLACE de la liste)
const panel = $("#panel");
function panneau() {
  if (!carte) return;
  let h = "";
  if (sel) { const e = EQUIPE.find((x) => x.id === sel), m = maison[sel];
    h = `<button class="retour" id="retourListe">${esc(tr("monde.retour_liste"))}</button><div class="who"><div class="bigimg"><img class="px" src="${imgs[sel].src}" alt=""></div><div><h3>${esc(e.nom)}</h3><span class="tchip" style="--tc:${COUL[e.type]}">${EMOJI[e.type]} ${esc(tr("type." + e.type))}</span></div></div>
      <div class="hab">${m ? `✓ ${esc(tr("monde.habite"))}<br><code>~/terrain_terminagotchi/biome/${esc(m)}/</code>` : `⏳ ${esc(tr("monde.attend", { region: tr("type." + e.type), n: carte.parcelles.filter((p) => p.type === e.type).length }))}<br><code>${esc(cmdAgrandir(e.type))}</code>`}</div>`;
  } else {
    h = `<h2>${esc(tr("monde.mes_creatures", { n: EQUIPE.length }))}</h2>`;
    const ref = EQUIPE.filter((e) => refuge.includes(e.id));
    if (ref.length) h += `<div class="refuge"><h4>🏠 ${esc(tr("monde.refuge", { n: ref.length }))}</h4>` + ref.map((e) => `<div class="rrow"><img class="px" src="${imgs[e.id].src}" alt=""><span>${esc(e.nom)}</span><code>${esc(cmdAgrandir(e.type))}</code></div>`).join("") + `</div>`;
    for (const ty of G.TYPES) { const es = EQUIPE.filter((e) => e.type === ty), ps = carte.parcelles.filter((p) => p.type === ty).length; if (!es.length && !ps) continue;
      h += `<div class="grp"><h4><button class="tchip" data-region="${ty}" style="--tc:${COUL[ty]}">${EMOJI[ty]} ${esc(tr("type." + ty))}</button><span>${es.filter((e) => maison[e.id]).length}/${ps}</span></h4><div class="roster">` +
        es.map((e) => `<button data-cr="${e.id}" class="${refuge.includes(e.id) ? "wait" : ""}"><img class="px" src="${imgs[e.id].src}" alt=""><span>${esc(e.nom)}</span></button>`).join("") + `</div></div>`; }
    h += `<p class="note">${esc(tr("monde.toucher"))}</p>`;
  }
  panel.innerHTML = h;
  panel.querySelectorAll("[data-cr]").forEach((b) => (b.onclick = () => choisir(b.dataset.cr)));
  panel.querySelectorAll("[data-region]").forEach((b) => (b.onclick = () => isoler(b.dataset.region)));
  const r = $("#retourListe"); if (r) r.onclick = () => choisir(null);
}
const cmdAgrandir = (ty) => { const n = carte.parcelles.filter((p) => p.type === ty).length; return n ? `mkdir biome/${ty}/parcelle_${n + 1}` : `mkdir -p biome/${ty}/parcelle_1`; };
function choisir(id) { sel = id; panneau(); panel.classList.toggle("open", !!id || panel.classList.contains("open")); if (!id && innerWidth < 960) panel.classList.remove("open"); }
function isoler(ty) { const hs = [...carte.hex.values()].filter((h) => h.region === ty); if (!hs.length) return; iso = ty; manuel = true; ajuster(hs, true, 3.4); }
function hexSous(x, y) { const wx = mx(x), wy = my(y); for (let i = ordre.length - 1; i >= 0; i--) { const h = ordre[i], [sx, sy] = sommet(h), dx = wx - sx, dy = wy - sy; if (hexInside(dx, dy) || (Math.abs(dx) <= HR && dy > 0 && dy <= hexBottom(dx) + h.mur)) return h; } return null; }
let pd = null;
cv.addEventListener("pointerdown", (e) => { pd = { x: e.clientX, y: e.clientY, cx: cam.x, cy: cam.y, bouge: false }; try { cv.setPointerCapture(e.pointerId); } catch (_) { /* rien */ } });
cv.addEventListener("pointermove", (e) => { if (!pd) return; const dx = e.clientX - pd.x, dy = e.clientY - pd.y; if (!pd.bouge && Math.hypot(dx, dy) > 7) pd.bouge = true; if (pd.bouge) { manuel = true; but = null; cam.x = pd.cx - dx * dpr / cam.z; cam.y = pd.cy - dy * dpr / cam.z; } });
cv.addEventListener("pointerup", (e) => { const p = pd; pd = null; if (!p || p.bouge) return; const rc = cv.getBoundingClientRect(), x = (e.clientX - rc.left) * dpr, y = (e.clientY - rc.top) * dpr;
  const zn = [...zones].reverse().find((zz) => x >= zz.x && x <= zz.x + zz.w && y >= zz.y && y <= zz.y + zz.h);
  if (zn && zn.a.startsWith("crea:")) { choisir(zn.a.slice(5)); return; }
  if (zn && zn.a.startsWith("region:")) { isoler(zn.a.slice(7)); return; }
  if (sel) { choisir(null); return; }                      // un clic à côté : la liste revient
  if (iso) { iso = null; toutVoir(); return; }
  const h = hexSous(x, y); if (h && h.region) isoler(h.region); });
cv.addEventListener("wheel", (e) => { e.preventDefault(); manuel = true; but = null; cam.z = clamp(cam.z * (e.deltaY < 0 ? 1.3 : 1 / 1.3), 0.5 * dpr, 7 * dpr); }, { passive: false });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") { if (sel) choisir(null); else if (iso) { iso = null; toutVoir(); } } });
$("#voir").onclick = () => { iso = null; toutVoir(); }; $("#plus").onclick = () => { manuel = true; cam.z = Math.min(7 * dpr, cam.z * 1.3); }; $("#moins").onclick = () => { manuel = true; cam.z = Math.max(0.5 * dpr, cam.z / 1.3); };
$("#rosterBtn").onclick = () => panel.classList.toggle("open");
// ------------------------------------------------------------------ le mini-terminal
const out = $("#out");
function ligneTerm(txt, cls) { const d = document.createElement("div"); d.className = cls || ""; d.textContent = txt; out.appendChild(d); out.scrollTop = out.scrollHeight; }
const invite = () => "~/terrain_terminagotchi" + (cwd ? "/" + cwd : "") + " $";
$("#form").addEventListener("submit", (e) => { e.preventDefault(); const l = $("#cmd").value.trim(); if (!l) return; $("#cmd").value = ""; ligneTerm(invite() + " " + l, "cmd");
  const r = jouer(l); if (r.sortie) ligneTerm(r.sortie, r.code ? "err" : ""); $("#prompt").textContent = invite(); });
for (const b of document.querySelectorAll("[data-essai]")) b.onclick = () => { $("#cmd").value = b.dataset.essai; $("#cmd").focus(); };
$("#prompt").textContent = invite();
// ------------------------------------------------------------------ l'horloge (une image par rafraîchissement, au plus 50 ms de pas)
let dernier = performance.now() / 1000;
function image(ts) {
  const t = ts / 1000, dt = Math.min(0.05, t - dernier); dernier = t; now += dt;
  if (but) { const k = Math.min(1, dt * 4); cam.x += (but.x - cam.x) * k; cam.y += (but.y - cam.y) * k; cam.z += (but.z - cam.z) * k; if (Math.abs(but.z - cam.z) < 0.01 && Math.abs(but.x - cam.x) < 0.5) { cam = { ...but }; but = null; } }
  if (carte) for (const cr of Object.values(creas)) if (cr.at) avancer(cr, dt);
  for (const p of parts) { p.v += dt; p.x += p.vx * dt; p.y += p.vy * dt; p.vy += p.g * dt; }
  for (let i = parts.length - 1; i >= 0; i--) if (parts[i].v > parts[i].max) parts.splice(i, 1);
  for (let i = effets.length - 1; i >= 0; i--) if (now - effets[i].t0 > effets[i].du) effets.splice(i, 1);
  for (let i = fantomes.length - 1; i >= 0; i--) if (now - fantomes[i].t0 > 1) fantomes.splice(i, 1);
  if (retour && !effets.length) { if (!manuel) but = retour; retour = null; }
  zones = []; dessiner(); requestAnimationFrame(image);
}
window.addEventListener("resize", resize);
reconstruire(); resize(); requestAnimationFrame(image);
window.TG_MONDE_JOUER = jouer;          // pour les captures automatiques (playwright)
