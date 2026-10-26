/**
 * Terminagotchi — le mini-terminal du site : une barre « visiteur@terminagotchi:~/bestiaire$ _ » en bas de chaque page,
 * pour se promener dans le site avec de vraies commandes (ls, cd, cat, find, tree…), comme dans le jeu.
 *
 * Le site est vu comme un dossier personnel :
 *   ~                      → /
 *   ~/bestiaire            → /bestiaire           (dossiers des familles + un fichier par bestiole)
 *   ~/bestiaire/demons     → /bestiaire?famille=Démons
 *   ~/bestiaire/braisillon → /bestiaire/braisillon (un fichier : on l'ouvre avec cat)
 *   ~/joueurs/Grec         → /joueur/Grec         (~/joueurs n'a pas de page : cd y entre sans changer de page)
 *   ~/captures/shiny       → /captures?shiny=1
 *   parents, soutenir, confidentialite, mentions-legales : des fichiers à la racine
 *
 * La page ne contient que son chemin et les textes (petit JSON) ; le plan complet (familles, bestioles) vient de
 * GET /api/plan?lang=xx, chargé seulement quand on ouvre le terminal, puis gardé le temps de la session.
 * La liste des joueurs vient de GET /api/classement, seulement pour ls ou Tab dans ~/joueurs.
 *
 * Le script est écrit « à l'ancienne » (var, function nom(), pas de flèches) : les tests du site interdisent
 * certains mots dans le HTML rendu, et il doit rester petit et lisible.
 */

import BESTIAIRE from "./bestiaire.js";
import { LANGUES, NOMS_LANGUES, textes, libelle } from "./i18n.js";

/** « Bêtes monstrueuses » → « betes-monstrueuses » : un nom de dossier tapable au clavier. */
export function slug(s) {
  return String(s).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

const PUBLIQUES = BESTIAIRE.especes.filter((e) => !e.secrete).sort((a, b) => a.numero - b.numero);
const lienFamille = (nom) => "/bestiaire?" + new URLSearchParams({ famille: nom });

/** Le chemin « ~/… » (sans le ~) qui correspond à une adresse du site. */
export function cheminVirtuel(url) {
  const ch = url.pathname.replace(/\/+$/, "") || "/";
  if (ch === "/") return "";
  if (ch === "/bestiaire") {
    const f = BESTIAIRE.familles.find((x) => x.nom === url.searchParams.get("famille"));
    return f ? "bestiaire/" + slug(f.nom) : "bestiaire";
  }
  if (ch === "/captures" && url.searchParams.get("shiny") === "1") return "captures/shiny";
  const morceaux = ch.slice(1).split("/").map((m) => {
    try { return decodeURIComponent(m).replace(/\//g, "_"); } catch { return m; }
  });
  if (morceaux[0] === "joueur") morceaux[0] = "joueurs";
  return morceaux.join("/");
}

/** Les pages vues comme des fichiers (on les ouvre avec cat) : une bestiole, les textes pour les adultes. */
export function estFichier(url) {
  const ch = url.pathname.replace(/\/+$/, "");
  return /^\/bestiaire\/[a-z0-9]+$/.test(ch) || ["/parents", "/soutenir", "/confidentialite", "/mentions-legales"].includes(ch);
}

/** Le plan du site pour /api/plan : r = racine, s = sous-dossiers, f = familles, e = bestioles. */
export function planSite(lang) {
  const t = textes(lang);
  return {
    r: [["bestiaire", "d", "/bestiaire", t.nav.bestiaire], ["captures", "d", "/captures", t.nav.captures],
      ["classement", "d", "/classement", t.nav.classement], ["records", "d", "/records", t.navRecords],
      ["joueurs", "d", "", t.terminal.joueurs], ["ctf", "d", "/ctf", t.nav.ctf], ["compte", "d", "/compte", t.nav.compte],
      ["parents", "f", "/parents", t.pied.parents], ["soutenir", "f", "/soutenir", t.pied.soutenir],
      ["confidentialite", "f", "/confidentialite", t.pied.confidentialite], ["mentions-legales", "f", "/mentions-legales", t.pied.mentions]],
    s: { captures: [["shiny", "d", "/captures?shiny=1", "✨ " + t.captures.shinySeul]] },
    f: BESTIAIRE.familles.map((f) => [slug(f.nom), libelle(t.familles, f.nom), f.icone, lienFamille(f.nom)]),
    e: PUBLIQUES.map((e) => [e.id, e.nom, slug(e.famille)]),
  };
}

// Le script de la page. Pas de ${…} ni d'accent grave ici (c'est un String.raw).
const SCRIPT = String.raw`(function(){
var D=document,R=D.getElementById("tg"),T;
try{T=JSON.parse(D.getElementById("tg-d").textContent)}catch(e){return}
if(!R||!window.JSON||!D.querySelector)return;
var M=T.s,O=D.getElementById("tg-ouvrir"),PN=D.getElementById("tg-panneau"),S=D.getElementById("tg-sortie"),
F=D.getElementById("tg-form"),I=D.getElementById("tg-saisie"),P=D.getElementById("tg-invite"),X=D.getElementById("tg-fermer");
var PG=T.c?T.c.split("/"):[],cwd=PG.slice(),cwdF=!!T.fi,PL=null,RAC=null,JO=null,attente=[],charge=0,bruit=0;
var CMDS=["ls","cd","pwd","cat","find","grep","tree","history","clear","lang","help","aide","exit","whoami","echo"];
function lire(k,d){try{var v=localStorage.getItem(k);return v?JSON.parse(v):d}catch(e){return d}}
function ecrire(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
function slire(k){try{var v=sessionStorage.getItem(k);return v?JSON.parse(v):null}catch(e){return null}}
function secrire(k,v){try{if(v==null)sessionStorage.removeItem(k);else sessionStorage.setItem(k,JSON.stringify(v))}catch(e){}}
function f(s,x,n){return String(s).split("{x}").join(x==null?"":x).split("{n}").join(n==null?"":String(n))}
function norm(s){return String(s).normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase()}
function ici(){var q=new URLSearchParams(location.search);q.delete("lang");q=q.toString();return location.pathname+(q?"?"+q:"")}
var hist=lire("tg-hist",[]),hi=hist.length,brouillon="",JRN=slire("tg-jrn")||[];
function chem(c){return "~"+(c.length?"/"+c.join("/"):"")}
function invite(){return T.u+"@terminagotchi:"+chem(cwd)+"$"}
function majInvite(){P.textContent="";var u=D.createElement("span");u.className="tg-u";u.textContent=T.u+"@terminagotchi:";
var c=D.createElement("span");c.className="tg-ch";c.textContent=chem(cwd);P.appendChild(u);P.appendChild(c);P.appendChild(D.createTextNode("$"))}
function el(t,c,x){var e=D.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e}
function rendre(e){var d,i,it,a;
if(e.t==="c"){d=el("div","tg-c");d.appendChild(el("span","tg-p",e.p));d.appendChild(D.createTextNode(" "+e.x))}
else if(e.t==="l"){d=el("div","tg-l "+(e.k||""));for(i=0;i<e.x.length;i++){it=e.x[i];var b=el("span","tg-i");
if(it[4])b.appendChild(el("span","tg-a",it[4]));a=el(it[1]?"a":"span",it[2]||"",it[0]);if(it[1])a.href=it[1];b.appendChild(a);
if(it[3]){var n=el("bdi","tg-n",it[3]);b.appendChild(n)}d.appendChild(b)}}
else{d=el("div","tg-m "+(e.k||""),e.x);d.dir="auto"}
S.appendChild(d)}
function ajout(e){JRN.push(e);if(JRN.length>60)JRN=JRN.slice(-60);secrire("tg-jrn",JRN);rendre(e);
while(S.childNodes.length>60)S.removeChild(S.firstChild);S.scrollTop=S.scrollHeight}
function dire(x,k){ajout({t:"m",x:x,k:k})}
function liste(x,k){ajout({t:"l",x:x,k:k})}
function noeud(n,t,u,l){return {n:n,t:t,u:u||"",l:l||"",k:[]}}
function fils(n,nom){var i,b=null;for(i=0;i<n.k.length;i++){if(n.k[i].n===nom)return n.k[i];if(!b&&n.k[i].n.toLowerCase()===String(nom).toLowerCase())b=n.k[i]}return b}
function construire(){RAC=noeud("~","d","/");var i,j,x,y,nd,fam={},B,J;
for(i=0;i<PL.r.length;i++){x=PL.r[i];nd=noeud(x[0],x[1],x[2],x[3]);RAC.k.push(nd);y=PL.s[x[0]]||[];for(j=0;j<y.length;j++)nd.k.push(noeud(y[j][0],y[j][1],y[j][2],y[j][3]))}
B=fils(RAC,"bestiaire");for(i=0;i<PL.f.length;i++){x=PL.f[i];nd=noeud(x[0],"d",x[3],x[2]+" "+x[1]);nd.fam=1;fam[x[0]]=nd;B.k.push(nd)}
for(i=0;i<PL.e.length;i++){x=PL.e[i];B.k.push(noeud(x[0],"f","/bestiaire/"+x[0],x[1]));if(fam[x[2]])fam[x[2]].k.push(noeud(x[0],"f","/bestiaire/"+x[0],x[1]))}
J=fils(RAC,"joueurs");J.dyn=1;if(JO)for(i=0;i<JO.length;i++)J.k.push(noeud(JO[i],"d","/joueur/"+encodeURIComponent(JO[i])))}
function besoin(suite,muet){if(RAC){suite();return}attente.push(suite);var c=slire("tg-plan-"+T.l);if(c){PL=c;pret();return}
if(!muet&&!bruit){bruit=1;dire(M.chargement,"doux")}if(charge)return;charge=1;
fetch("/api/plan?lang="+T.l).then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(p){PL=p;secrire("tg-plan-"+T.l,p);pret()})
.catch(function(){charge=0;attente=[];if(bruit)dire(M.erreurReseau,"err");bruit=0})}
function pret(){construire();var a=attente;attente=[];for(var i=0;i<a.length;i++)a[i]()}
function joueurs(suite){if(JO){suite();return}
fetch("/api/classement").then(function(r){if(!r.ok)throw 0;return r.json()}).then(function(l){JO=[];for(var i=0;i<l.length;i++)JO.push(l[i].pseudo);
if(RAC)construire();suite()}).catch(function(){dire(M.erreurReseau,"err")})}
function segs(ch){ch=String(ch);var base,p,i,s,h="/home/"+T.u;
if(ch.charAt(0)==="~"){base=[];ch=ch.slice(1)}else if(ch.indexOf(h)===0){base=[];ch=ch.slice(h.length)}else if(ch.charAt(0)==="/")base=[];else{base=cwd.slice();if(cwdF&&ch.split("/")[0]!=="..")base.pop()}
p=ch.split("/");for(i=0;i<p.length;i++){s=p[i];if(!s||s===".")continue;if(s==="..")base.pop();else base.push(s)}return base}
function surPage(sg,i){if(PG.length<=i)return false;for(var j=0;j<=i;j++)if(sg[j]!==PG[j])return false;return true}
function trouver(sg){var n=RAC,c,i,vrai=[];for(i=0;i<sg.length;i++){c=fils(n,sg[i]);
if(!c&&n.dyn&&/^[A-Za-z0-9_-]{1,24}$/.test(sg[i]))c=noeud(sg[i],"d","/joueur/"+encodeURIComponent(sg[i]));
if(!c&&surPage(sg,i))c=noeud(sg[i],"d",i===PG.length-1?ici():"");
if(!c||(c.t==="f"&&i<sg.length-1))return null;vrai.push(c.n);n=c}return {n:n,sg:vrai}}
function dist(a,b){var d=[],i,j;for(i=0;i<=a.length;i++){d[i]=[i];for(j=1;j<=b.length;j++)d[i][j]=i?0:j}
for(i=1;i<=a.length;i++)for(j=1;j<=b.length;j++){var c=a[i-1]===b[j-1]?0:1;d[i][j]=Math.min(d[i-1][j]+1,d[i][j-1]+1,d[i-1][j-1]+c);
if(i>1&&j>1&&a[i-1]===b[j-2]&&a[i-2]===b[j-1])d[i][j]=Math.min(d[i][j],d[i-2][j-2]+1)}return d[a.length][b.length]}
function proche(m,l){m=norm(m);var best=null,bd=9,i,x,dd;for(i=0;i<l.length;i++){x=norm(l[i]);
if(m.length>2&&x.indexOf(m)===0)return l[i];dd=dist(m,x);if(dd<bd){bd=dd;best=l[i]}}return bd<=(m.length<4?1:2)?best:null}
function noms(n){var r=[];for(var i=0;i<n.k.length;i++)r.push(n.k[i].n);return r}
function suggerer(cmd,a){var sg=segs(a),der=sg.pop(),r=trouver(sg);if(!r||der==null)return;var s=proche(der,noms(r.n));
if(s){var i=a.lastIndexOf("/");dire(f(M.tuVoulais,cmd+" "+a.slice(0,i+1)+s))}}
function aller(u,nom){if(!u)return;dire(f(M.ouverture,nom),"doux");secrire("tg-suite",1);ecrire("tg-ouvert",1);location.href=u}
function cd(a){var v;if(a==="-"){v=slire("tg-avant");a=v==null?"~":"~/"+v}
besoin(function(){var r=trouver(a?segs(a):[]);if(!r){dire(f(M.pasIci,a),"err");suggerer("cd",a);return}
if(r.n.t==="f"){dire(f(M.estFichier,a),"err");return}
secrire("tg-avant",cwd.join("/"));cwd=r.sg;cwdF=0;majInvite();if(r.n.u&&r.n.u!==ici())aller(r.n.u,chem(r.sg))})}
function exemple(){var r=trouver(segs(".")),i;if(r)for(i=0;i<r.n.k.length;i++)if(r.n.k[i].t==="f")return r.n.k[i].n;return "mentions-legales"}
function cat(a){besoin(function(){if(!a){dire(f(M.usageCat,exemple()));return}var r=trouver(segs(a));
if(!r){dire(f(M.pasIci,a),"err");suggerer("cat",a);return}if(r.n.t==="d"){dire(f(M.estDossier,a),"err");return}aller(r.n.u,a)})}
function article(n,note){return [n.n+(n.t==="d"?"/":""),n.u,n.t==="d"?"tg-d":"tg-f",note?n.l:""]}
function ls(args){var tout=0,cible="",i;for(i=0;i<args.length;i++){if(args[i].charAt(0)==="-"){if(args[i].indexOf("a")>0)tout=1}else cible=args[i]}
besoin(function(){var r=trouver(cible?segs(cible):cwd);if(!r){dire(f(M.pasIci,cible),"err");suggerer("ls",cible);return}
var n=r.n;if(n.t==="f"){liste([article(n)],"g");return}
if(n.dyn&&!JO){joueurs(function(){ls(args)});return}
var d=[],fi=[];for(i=0;i<n.k.length;i++)(n.k[i].t==="d"?d:fi).push(n.k[i]);
if(!d.length&&!fi.length){dire(M.vide,"doux");return}
var col=!n.dyn&&d.length+fi.length<=16,a=[];
for(i=0;i<d.length;i++)a.push(article(d[i],col));
if(fi.length>24&&!tout){if(a.length)liste(a,col?"col":"g");dire(f(M.nbFichiers,"",fi.length),"doux");return}
if(col){for(i=0;i<fi.length;i++)a.push(article(fi[i],1));liste(a,"col");return}
if(a.length)liste(a,"g");a=[];for(i=0;i<fi.length;i++)a.push(article(fi[i]));if(a.length)liste(a,"g")})}
function cherche(args){var m="",i;for(i=0;i<args.length;i++){var x=args[i].replace(/["'*]/g,"");if(x&&x.charAt(0)!=="-"&&x!==".")m=x}
if(!m){dire(f(M.usageFind,"bra"));return}
besoin(function(){var q=norm(m),res=[],x,B=fils(RAC,"bestiaire");
for(i=0;i<RAC.k.length;i++){x=RAC.k[i];if(norm(x.n+" "+x.l).indexOf(q)>=0)res.push(["~/"+x.n+(x.t==="d"?"/":""),x.u,x.t==="d"?"tg-d":"tg-f",x.l])}
for(i=0;i<B.k.length;i++){x=B.k[i];if(x.fam&&norm(x.n+" "+x.l).indexOf(q)>=0)res.push(["~/bestiaire/"+x.n+"/",x.u,"tg-d",x.l])}
for(i=0;i<PL.e.length;i++){x=PL.e[i];if(norm(x[0]+" "+x[1]).indexOf(q)>=0)res.push(["~/bestiaire/"+x[2]+"/"+x[0],"/bestiaire/"+x[0],"tg-f",x[1]===x[0]?"":x[1]])}
if(!res.length){dire(f(M.rien,m),"err");return}dire(f(M.resultats,"",res.length),"doux");liste(res.slice(0,40),"col");if(res.length>40)dire("…","doux")})}
function tree(){besoin(function(){var a=[["~","/","tg-d",""]],i,j,x,y,der,ss,B;
for(i=0;i<RAC.k.length;i++){x=RAC.k[i];der=i===RAC.k.length-1;a.push([x.n+(x.t==="d"?"/":""),x.u,x.t==="d"?"tg-d":"tg-f",x.l,der?"└── ":"├── "]);
ss=[];for(j=0;j<x.k.length;j++)if(x.k[j].t==="d")ss.push(x.k[j]);
for(j=0;j<ss.length;j++){y=ss[j];a.push([y.n+"/",y.u,"tg-d",y.l+(y.fam?" ("+y.k.length+")":""),(der?"    ":"│   ")+(j===ss.length-1?"└── ":"├── ")])}}
liste(a,"col arbre")})}
function lang(a){var u,i,l=[];if(a){a=a.toLowerCase();for(i=0;i<T.ls.length;i++)if(T.ls[i][0]===a){u=new URL(location.href);u.searchParams.set("lang",a);aller(u.pathname+u.search,T.ls[i][1]);return}
dire(f(M.langInconnue,a),"err")}
dire(M.langues);for(i=0;i<T.ls.length;i++){u=new URL(location.href);u.searchParams.set("lang",T.ls[i][0]);l.push([T.ls[i][0],u.pathname+u.search,T.ls[i][0]===T.l?"tg-d":"tg-f",T.ls[i][1]])}liste(l,"col")}
function aide(){var a=[],k;for(k in M.aide)a.push([k,"","tg-k",M.aide[k]]);liste(a,"col");dire(M.astuce,"doux")}
function historique(){if(!hist.length){dire(M.historiqueVide,"doux");return}var a=[],i,d=Math.max(0,hist.length-20);
for(i=d;i<hist.length;i++)a.push([hist[i],"","tg-k","",String(i+1)+"  "]);liste(a,"col")}
function effacer(){JRN=[];secrire("tg-jrn",null);S.textContent=""}
function executer(l){l=l.trim();ajout({t:"c",p:invite(),x:l});if(!l)return;
if(hist[hist.length-1]!==l){hist.push(l);if(hist.length>50)hist=hist.slice(-50);ecrire("tg-hist",hist)}hi=hist.length;brouillon="";
var a=l.split(/\s+/),c=a[0].toLowerCase(),r=a.slice(1),x=r.join(" ");
if(c==="ls"||c==="ll"||c==="dir")ls(r);else if(c==="cd")cd(x);else if(c==="pwd")dire("/home/"+T.u+(cwd.length?"/"+cwd.join("/"):""));
else if(c==="cat"||c==="less"||c==="more"||c==="open")cat(x);else if(c==="find"||c==="grep")cherche(r);else if(c==="tree")tree();
else if(c==="history")historique();else if(c==="clear"||c==="cls")effacer();else if(c==="lang")lang(x);
else if(c==="help"||c==="aide"||c==="man"||c==="?")aide();else if(c==="exit"||c==="quit"||c==="logout")fermer();
else if(c==="whoami")dire(T.u);else if(c==="echo")dire(x);else if(c==="sudo"||c==="su")dire(M.sudo);
else besoin(function(){var r=trouver(segs(".")),n=r&&fils(r.n,a[0]);if(n){dire(f(M.pourAller,(n.t==="d"?"cd ":"cat ")+n.n));return}
dire(f(M.inconnue,a[0]),"err");var s=proche(c,CMDS);dire(s?f(M.tuVoulais,s+(x?" "+x:"")):M.essaieAide)})}
function prefixe(l){var p=l[0]||"",i;for(i=1;i<l.length;i++)while(l[i].toLowerCase().indexOf(p.toLowerCase())!==0)p=p.slice(0,-1);return p}
function completer(){var v=I.value,parts=v.split(" "),der=parts[parts.length-1],c=(parts[0]||"").toLowerCase(),cands=[],i,base="",pre=der;
if(parts.length===1){for(i=0;i<CMDS.length;i++)if(CMDS[i].indexOf(der.toLowerCase())===0)cands.push(CMDS[i]+" ")}
else if(c==="lang"){for(i=0;i<T.ls.length;i++)if(T.ls[i][0].indexOf(der)===0)cands.push(T.ls[i][0])}
else{if(!RAC){besoin(completer);return}var j=der.lastIndexOf("/");base=der.slice(0,j+1);pre=der.slice(j+1);var r=trouver(segs(base||"."));if(!r)return;
if(r.n.dyn&&!JO){joueurs(completer);return}
for(i=0;i<r.n.k.length;i++){var n=r.n.k[i];if(c==="cd"&&n.t!=="d")continue;if(n.n.toLowerCase().indexOf(pre.toLowerCase())===0)cands.push(n.n+(n.t==="d"?"/":" "))}}
if(!cands.length)return;parts.pop();var deb=parts.length?parts.join(" ")+" ":"";
if(cands.length===1){I.value=deb+base+cands[0];return}
var p=prefixe(cands);if(p.length>pre.length){I.value=deb+base+p;return}
ajout({t:"c",p:invite(),x:v});var a=[];for(i=0;i<cands.length&&i<60;i++)a.push([cands[i].trim(),"",cands[i].slice(-1)==="/"?"tg-d":"tg-f",""]);liste(a,"g");if(cands.length>60)dire("…","doux")}
function ouvrir(focus){PN.hidden=false;O.setAttribute("aria-expanded","true");D.documentElement.classList.add("tg-ouvert");ecrire("tg-ouvert",1);
if(!lire("tg-vu",0)){ecrire("tg-vu",1);dire(M.bienvenue);dire(M.astuce,"doux")}besoin(function(){},1);S.scrollTop=S.scrollHeight;if(focus)I.focus()}
function fermer(){PN.hidden=true;O.setAttribute("aria-expanded","false");D.documentElement.classList.remove("tg-ouvert");ecrire("tg-ouvert",0);O.focus()}
O.addEventListener("click",function(){ouvrir(1)});X.addEventListener("click",fermer);
F.addEventListener("submit",function(e){e.preventDefault();var v=I.value;I.value="";executer(v)});
I.addEventListener("keydown",function(e){
if(e.key==="Tab"&&I.value&&!e.shiftKey){e.preventDefault();completer()}
else if(e.key==="Escape"){e.preventDefault();fermer()}
else if(e.key==="ArrowUp"&&hi>0){e.preventDefault();if(hi===hist.length)brouillon=I.value;hi--;I.value=hist[hi]}
else if(e.key==="ArrowDown"&&hi<hist.length){e.preventDefault();hi++;I.value=hi===hist.length?brouillon:hist[hi]}
else if(e.key==="l"&&e.ctrlKey){e.preventDefault();effacer()}});
S.addEventListener("click",function(e){if(e.target===S)I.focus()});
majInvite();for(var i=0;i<JRN.length;i++)rendre(JRN[i]);R.hidden=false;
var suite=slire("tg-suite");secrire("tg-suite",null);var ouv=lire("tg-ouvert",null);
if(suite||ouv===1||(ouv==null&&matchMedia("(min-width:761px)").matches))ouvrir(!!suite);
})()`;

/** La barre du terminal, à mettre à la fin de chaque page. */
export function barreTerminal(L) {
  const M = L.t.terminal;
  const d = { c: cheminVirtuel(L.url), fi: estFichier(L.url) ? 1 : 0, u: M.utilisateur, l: L.lang, s: M, ls: LANGUES.map((l) => [l, NOMS_LANGUES[l]]) };
  const e = (s) => String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
  return `<div id="tg" class="tg" dir="ltr" hidden>`
    + `<button type="button" id="tg-ouvrir" class="tg-ouvrir" aria-expanded="false" aria-controls="tg-panneau" title="${e(M.ouvrir)}"><span aria-hidden="true">&gt;_</span><span class="tg-cache">${e(M.ouvrir)}</span></button>`
    + `<div id="tg-panneau" class="tg-panneau" hidden><div id="tg-sortie" class="tg-sortie" role="log" aria-live="polite"></div>`
    + `<form id="tg-form" class="tg-ligne"><span id="tg-invite" class="tg-invite" aria-hidden="true"></span>`
    + `<input id="tg-saisie" type="text" aria-label="${e(M.saisie)}" placeholder="help" autocomplete="off" autocapitalize="off" autocorrect="off" spellcheck="false" enterkeyhint="go">`
    + `<button type="button" id="tg-fermer" class="tg-fermer" aria-label="${e(M.fermer)}" title="${e(M.fermer)}"><span aria-hidden="true">×</span></button></form></div></div>`
    + `<script type="application/json" id="tg-d">${JSON.stringify(d).replace(/</g, "\\u003c")}</script><script>${SCRIPT}</script>`;
}

/** Le style de la barre (ajouté à la feuille de style du site). */
export const CSS_TERMINAL = `
/* ---- mini-terminal en bas de page */
.tg[hidden],.tg [hidden]{display:none!important}
.tg{position:fixed;inset-inline:0;bottom:0;z-index:40;pointer-events:none;font:18px/1.35 "VT323",ui-monospace,Menlo,Consolas,monospace}
.tg>*{pointer-events:auto}
.tg-ouvrir{position:absolute;bottom:14px;inset-inline-end:14px;margin:0;padding:10px 14px;background:var(--ecran);color:var(--vert);border:0;
 font:14px/1 var(--pixel);cursor:pointer;box-shadow:0 -3px 0 var(--bord-vif),0 3px 0 var(--bord-vif),-3px 0 0 var(--bord-vif),3px 0 0 var(--bord-vif),0 0 18px rgba(92,255,149,.25)}
.tg-ouvrir:hover{color:var(--ambre)}
.tg-ouvert .tg-ouvrir{display:none}
.tg-cache{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.tg-panneau{background:rgba(5,11,8,.97);border-top:3px solid var(--bord-vif);box-shadow:0 -8px 24px rgba(0,0,0,.5)}
.tg-sortie{max-height:min(38vh,320px);overflow-y:auto;padding:8px 16px 2px;color:var(--texte);overflow-wrap:anywhere}
.tg-sortie:empty{display:none}
.tg-c{color:var(--vert)}.tg-p{color:var(--doux)}
.tg-m.doux{color:var(--doux)}.tg-m.err{color:var(--ambre)}
.tg-l{display:flex;flex-wrap:wrap;gap:0 18px}
.tg-l.col{flex-direction:column}
.tg-l.arbre .tg-i{white-space:pre}
.tg-i{display:inline-flex;gap:10px;align-items:baseline}
.tg-a{color:var(--bord-vif)}
.tg-d{color:var(--vert);font-weight:700}.tg-f{color:var(--texte)}.tg-k{color:var(--vert);min-width:4.5em}
.tg-l a{text-decoration:none}.tg-l a:hover{text-decoration:underline;color:var(--ambre)}
.tg-n{color:var(--doux)}
.tg-ligne{display:flex;align-items:center;gap:8px;margin:0;padding:6px 8px 8px 16px}
.tg-invite{color:var(--vert);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:55%;flex:none}
.tg-u{color:var(--doux)}
.tg-ligne input{flex:1;min-width:4em;margin:0;padding:4px 2px;background:transparent;border:0;color:var(--vert);caret-color:var(--vert);font:inherit;font-size:20px}
.tg-ligne input::placeholder{color:var(--bord-vif)}
.tg-ligne input:focus{outline:0}.tg-ligne:focus-within{box-shadow:inset 0 -2px 0 var(--ambre)}
.tg-fermer{margin:0;padding:4px 10px;background:transparent;border:0;color:var(--doux);font:22px/1 var(--police);cursor:pointer}
.tg-fermer:hover{color:var(--ambre)}
.tg-fermer:focus-visible,.tg-ouvrir:focus-visible,.tg-l a:focus-visible{outline:3px solid var(--ambre);outline-offset:2px}
html.tg-ouvert body{padding-bottom:64px}
@media (max-width:760px){.tg-u{display:none}.tg-sortie{max-height:32vh;padding-inline:12px}.tg-ligne{padding-inline-start:12px}.tg-ligne input{font-size:18px}.tg-invite{max-width:48%}}
@media (prefers-reduced-motion:reduce){.tg *{transition:none!important;animation:none!important}}
`;
