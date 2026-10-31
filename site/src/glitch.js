/**
 * L'effet « glitch » d'une créature (même spécification que pc/tg/glitch.py et app/…/Glitch.kt ; vecteurs communs :
 * donnees/glitch/vecteurs.json). Pixels : entiers ARGB 0xAARRGGBB (non signés), transparents si A = 0.
 * Au repos le style A (léger), toutes les quelques secondes un éclair du style C (fort) : voir etat().
 * Ce fichier sert au serveur (tests) ET au navigateur : SCRIPT_GLITCH (en bas) est la version posée dans les pages.
 */
const M64 = (1n << 64n) - 1n;
const ROSE = 0xff2878, CYAN = 0x28e6ff, JAUNE = 0xf0ff50, BLANC = 0xffffff;
const MORTS = [ROSE, CYAN, JAUNE, BLANC];
export const ECLAIR_MS = 260;
export const REPERE = "▚";

export function fnv(texte) {
  let h = 0xcbf29ce484222325n;
  for (const o of new TextEncoder().encode(texte)) h = ((h ^ BigInt(o)) * 0x100000001b3n) & M64;
  return h;
}

class Hasard {
  constructor(texte) { this.etat = fnv(texte); }
  suivant() {
    this.etat = (this.etat + 0x9e3779b97f4a7c15n) & M64;
    let z = this.etat;
    z = ((z ^ (z >> 30n)) * 0xbf58476d1ce4e5b9n) & M64;
    z = ((z ^ (z >> 27n)) * 0x94d049bb133111ebn) & M64;
    return z ^ (z >> 31n);
  }
  n(k) { return Number(this.suivant() % BigInt(k)); }
}

const plein = (p) => (p >>> 24) !== 0;

/** Les pixels transparents reliés au bord de l'image (4 voisins). */
function exterieur(w, h, pl) {
  const dehors = new Uint8Array(w * h);
  const pile = [];
  for (let i = 0; i < w * h; i++) {
    const x = i % w;
    if (!pl[i] && (i < w || i >= w * (h - 1) || x === 0 || x === w - 1)) { dehors[i] = 1; pile.push(i); }
  }
  while (pile.length) {
    const i = pile.pop();
    const x = i % w;
    for (const j of [i >= w ? i - w : -1, i + w < w * h ? i + w : -1, x > 0 ? i - 1 : -1, x < w - 1 ? i + 1 : -1]) {
      if (j >= 0 && !pl[j] && !dehors[j]) { dehors[j] = 1; pile.push(j); }
    }
  }
  return dehors;
}

/** Les pixels (tableau d'entiers ARGB, w × h) avec l'effet : un NOUVEAU tableau (Array de nombres non signés). */
export function appliquer(w, h, px, graine, style = "A", phase = 0, s = 1) {
  s = Math.max(1, s | 0);
  const w0 = Math.max(1, Math.floor(w / s)), h0 = Math.max(1, Math.floor(h / s));
  const r = new Hasard(`${graine}:${style}:${phase}`);
  const fort = style === "C";
  const pl = Array.from(px, plein);
  let out = Array.from(px, (p) => p >>> 0);
  if (fort) {
    for (let i = 0; i < out.length; i++) {
      if (!pl[i]) continue;
      const p = out[i];
      let rr = (p >>> 16) & 255, gg = (p >>> 8) & 255, bb = p & 255;
      const m = Math.floor((rr + gg + bb) / 3);
      rr = Math.floor((55 * rr + 45 * m) / 100); gg = Math.floor((55 * gg + 45 * m) / 100); bb = Math.floor((55 * bb + 45 * m) / 100);
      rr = Math.min(255, Math.floor(rr * 105 / 100) + 18); bb = Math.min(255, Math.floor(bb * 110 / 100) + 28);
      out[i] = ((p & 0xff000000) | (rr << 16) | (gg << 8) | bb) >>> 0;
    }
  }
  const d = s * (fort ? Math.max(2, Math.floor(w0 / 12)) : Math.max(1, Math.floor(w0 / 24)));
  const dehors = fort ? null : exterieur(w, h, pl);
  for (let y = 0; y < h; y++) {
    const b = y * w;
    for (let x = 0; x < w; x++) {
      if (pl[b + x] || (dehors && !dehors[b + x])) continue;
      if (x + d < w && pl[b + x + d]) out[b + x] = (0xff000000 | CYAN) >>> 0;
      else if (x - d >= 0 && pl[b + x - d]) out[b + x] = (0xff000000 | ROSE) >>> 0;
    }
  }
  for (let k = 0; k < (fort ? 7 : 2); k++) {
    const y0 = r.n(h0);
    const hh = 1 + r.n(Math.max(1, Math.floor(h0 / (fort ? 7 : 10))));
    const sens = r.n(2) ? 1 : -1;
    const dx = sens * (1 + r.n(fort ? Math.max(3, Math.floor(w0 / 5)) : Math.max(2, Math.floor(w0 / 12)))) * s;
    for (let y = y0 * s; y < Math.min(h, (y0 + hh) * s); y++) {
      const ligne = out.slice(y * w, (y + 1) * w);
      for (let x = 0; x < w; x++) out[y * w + x] = ligne[(((x - dx) % w) + w) % w];
    }
  }
  if (fort) {
    for (let y = 0; y < h; y++) {
      if (Math.floor(y / s) % 3 !== 0) continue;
      for (let i = y * w; i < (y + 1) * w; i++) {
        const p = out[i];
        if (!plein(p)) continue;
        out[i] = ((p & 0xff000000) | (Math.floor(((p >>> 16) & 255) * 78 / 100) << 16)
          | (Math.floor(((p >>> 8) & 255) * 78 / 100) << 8) | Math.floor((p & 255) * 78 / 100)) >>> 0;
      }
    }
    const nb = Math.max(1, Math.floor(w0 * h0 / 250));
    for (let k = 0; k < nb; k++) {
      const yu = r.n(h0), xu = r.n(w0), c = MORTS[r.n(4)];
      if (yu * s < h && xu * s < w && plein(out[yu * s * w + xu * s])) {
        for (let y = yu * s; y < Math.min(h, yu * s + s); y++) {
          for (let x = xu * s; x < Math.min(w, xu * s + s); x++) out[y * w + x] = (0xff000000 | c) >>> 0;
        }
      }
    }
    const x0 = Math.floor(w0 / 4) + r.n(Math.max(1, Math.floor(w0 / 2)));
    const ww = 2 + r.n(2);
    const lum = (p) => ((p >>> 16) & 255) + ((p >>> 8) & 255) + (p & 255);
    for (let x = x0 * s; x < Math.min(w, (x0 + ww) * s); x++) {
      const ys = [];
      for (let y = 0; y < h; y++) if (plein(out[y * w + x])) ys.push(y);
      const vals = ys.map((y) => out[y * w + x]).sort((a, b) => lum(a) - lum(b));
      ys.forEach((y, k) => { out[y * w + x] = vals[k]; });
    }
  }
  return out;
}

/** [style, phase] à l'instant t (ms) : ["A", 0] au repos, ["C", phase] pendant un éclair. */
export function etat(graine, t = Date.now()) {
  const hh = fnv(`${graine}:eclair`);
  const periode = 3000n + hh % 2500n;
  const t2 = BigInt(Math.floor(t)) + (hh >> 20n) % periode;
  const u = t2 % periode;
  if (u < BigInt(ECLAIR_MS)) return ["C", Number((t2 / periode) % 4n) * 2 + (u >= BigInt(ECLAIR_MS / 2) ? 1 : 0)];
  return ["A", 0];
}

/**
 * Le script posé dans les pages (bestiaire, profil, galerie) : chaque <img data-glitch="graine"> (portrait d'une
 * capture glitch) est redessiné dans un <canvas> à sa place, teinte shiny d'abord (data-teinte, en degrés), puis
 * l'effet : style A au repos, un éclair C de temps en temps. La taille d'un « pixel de créature » : largeur / 48.
 */
export const SCRIPT_GLITCH = `(()=>{const M=(1n<<64n)-1n;${fnv.toString()}${Hasard.toString()}const ROSE=${ROSE},CYAN=${CYAN},MORTS=${JSON.stringify(MORTS)},ECLAIR_MS=${ECLAIR_MS},M64=M,plein=${plein.toString()};${exterieur.toString()}${appliquer.toString()}${etat.toString()}
const reduit=matchMedia("(prefers-reduced-motion: reduce)").matches;const fx=[];function prendre(im){const W=im.naturalWidth,H=im.naturalHeight;if(!W||!H)return;const cv=document.createElement("canvas");cv.width=W;cv.height=H;cv.className=im.className;cv.setAttribute("role","img");cv.setAttribute("aria-label",im.alt||"");cv.style.cssText=im.getAttribute("style")||"";cv.style.filter="";cv.style.imageRendering="pixelated";cv.style.width=(im.width||W)+"px";cv.style.height=(im.height||H)+"px";const c=cv.getContext("2d");const t=+im.dataset.teinte||0;if(t&&"filter" in c)c.filter="hue-rotate("+t+"deg)";else if(t)cv.style.filter="hue-rotate("+t+"deg)";c.drawImage(im,0,0);c.filter="none";const d=c.getImageData(0,0,W,H).data;const px=new Array(W*H);for(let i=0;i<W*H;i++)px[i]=((d[4*i+3]<<24)|(d[4*i]<<16)|(d[4*i+1]<<8)|d[4*i+2])>>>0;im.replaceWith(cv);fx.push({c,W,H,px,g:im.dataset.glitch,s:Math.max(1,Math.round(W/48)),vu:{},cle:""});}
function dessiner(f){const[st,ph]=reduit?["A",0]:etat(f.g);const cle=st+ph;if(cle===f.cle)return;f.cle=cle;let im=f.vu[cle];if(!im){const o=appliquer(f.W,f.H,f.px,f.g,st,ph,f.s);im=f.c.createImageData(f.W,f.H);for(let i=0;i<o.length;i++){const p=o[i];im.data[4*i]=(p>>>16)&255;im.data[4*i+1]=(p>>>8)&255;im.data[4*i+2]=p&255;im.data[4*i+3]=p>>>24;}f.vu[cle]=im;}f.c.putImageData(im,0,0);}
for(const im of document.querySelectorAll("img[data-glitch]")){if(im.complete)prendre(im);else im.addEventListener("load",()=>prendre(im),{once:true});}
setInterval(()=>{for(const f of fx)dessiner(f);},reduit?1000:65);})();`;
