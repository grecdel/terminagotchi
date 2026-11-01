/**
 * Terminagotchi — la page « Pour les enseignants et les parents » (/enseignants), en français (la version qui fait foi).
 *
 * Les autres langues montrent un résumé traduit (i18n_pages.js, clé « enseignants ») puis ce texte, marqué lang="fr".
 * Tout ce qui est écrit ici doit correspondre à ce que fait VRAIMENT le jeu (pc/tg/classe.py) : le mode classe est
 * 100 % local, rien n'est envoyé. Le tableau de bord en ligne est REPORTÉ (serveur, décision du propriétaire, avis CNIL).
 *
 * codeSeance() fabrique exactement les mêmes codes que pc/tg/classe.py (vecteurs : donnees/classe/vecteurs.json).
 */

const e = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

export const LETTRES = "ABCDEFGHJKMNPQRSTUVWXYZ";
const OPTIONS = "AGS";

/** Le code de séance : codeSeance(5, "SG") → « 05-GS-K » (même calcul que classe.fabriquer). */
export function codeSeance(n, options = "") {
  const opts = [...OPTIONS].filter((o) => String(options).toUpperCase().includes(o)).join("");
  const nn = String(n).padStart(2, "0");
  const corps = nn + opts;
  let somme = 0;
  for (let i = 0; i < corps.length; i++) somme += (i + 1) * corps.charCodeAt(i);
  const c = LETTRES[somme % LETTRES.length];
  return opts ? `${nn}-${opts}-${c}` : `${nn}-${c}`;
}

/** Les chapitres et les mondes, avec leur numéro dans le jeu (histoire.CHAPITRES). */
export const CHAPITRES = [
  [1, "Le réveil", "pwd, ls, cd, cd /"],
  [2, "Le nid", "mkdir, touch, >, cat, ls -a"],
  [3, "La forêt du Grenier", "tree, mv, cp, rm"],
  [4, "La caverne des Démons", "whoami, chmod, /etc, /bin, /var/log"],
  [5, "La bibliothèque engloutie", "find, less, grep, head, wc"],
  [6, "La salle des machines du volcan", "free, du, df"],
  [7, "Le dortoir des brumes", "ps, &, jobs, kill"],
  [8, "La petite forge des Constructs", "scripts, chmod +x, alias, git"],
  [9, "La tour des nuages", "ping, ip, curl, nslookup"],
  [10, "Le cœur du monde", "révision : find, grep | wc, cat >"],
  [11, "Le Port des messagers", "réseaux, protocoles (simulés)"],
  [12, "La Citadelle des gardiens", "cybersécurité défensive (boîtes simulées)"],
  [13, "La Crypte des Codes", "cryptographie, blockchain expliquée"],
  [14, "La Salle des Rouages", "matériel, systèmes, machine virtuelle"],
  [15, "La Tour des Ondes", "radio, LoRa, réseaux maillés"],
  [16, "La Guilde des Bâtisseurs Libres", "open source, licences, git"],
  [17, "L'Observatoire de l'IA", "comprendre l'IA (aucune vraie IA)"],
  [18, "La Salle des Données", "texte, CSV, SQL sur sa collection"],
  [19, "La Forge", "scripts, boucles, Python, son jeu, son site"],
  [20, "L'Atelier des robots", "robot simulé, capteurs, ET / OU / NON, boucles"],
  [21, "La Bibliothèque du Temps", "git : versions, branches, fusion, empreintes"],
  [23, "Le Sommet", "Expert++ : scripts robustes, regex, débogage"],
];

const ligne = ([n, nom, notions]) => `<tr><td>${n}. ${e(nom)}<br><span class="doux">${e(notions)}</span></td>`
  + `<td data-t="Séance guidée"><code>${codeSeance(n, "GS")}</code></td>`
  + `<td data-t="Sans aide (cran C)"><code>${codeSeance(n, "AGS")}</code></td>`
  + `<td data-t="Sur chaque poste"><code>${codeSeance(n, "S")}</code></td></tr>`;

/**
 * La page complète.
 * @param {{ depot: string }} c
 */
export function enseignantsFr(c) {
  const pdf = `${c.depot}/blob/main/docs/classe/fiches_enseignant.pdf`;
  const fiches = `${c.depot}/blob/main/docs/classe/fiches_enseignant.md`;
  return `<p>Terminagotchi apprend le terminal en élevant une créature : chaque commande tapée la nourrit. Il est gratuit,
sans publicité, sans achat, <b>sans compte</b>, et il fonctionne <b>hors ligne</b>. Cette page dit comment l'utiliser en
classe, ce que les élèves apprennent et ce que le jeu fait (et ne fait pas) des données.</p>

<div class="carte"><p><b>En une phrase :</b> l'enseignant donne un <b>code de séance</b> (il règle seulement le jeu),
chaque élève choisit un <b>pseudonyme</b>, et le bilan de la séance reste <b>sur l'ordinateur de l'élève</b> : il
s'affiche, s'imprime ou s'enregistre en fichier que l'élève remet lui-même. <b>Rien n'est envoyé.</b></p></div>

<h2>1. Lancer le jeu en salle</h2>
<ul>
<li>Sur les postes (Linux, macOS, Windows) : <code>python3 terminagotchi.pyz</code>, sans installation (Python 3 suffit).
Le fichier se trouve dans les versions publiées du <a href="${e(c.depot)}">dépôt du jeu</a>.</li>
<li>Le jeu écrit seulement dans le dossier de l'élève : <code>~/terrain_terminagotchi</code> (le terrain de jeu, le seul
endroit où l'on crée et supprime) et <code>~/.terminagotchi</code> (la sauvegarde).</li>
<li>Au premier lancement, l'élève fait éclore son œuf (5 minutes environ). Prévoyez-le dans la première séance.</li>
<li>Pour projeter au tableau : <code>tg espace classe</code> (grand écran).</li>
</ul>

<h2>2. Le code de séance</h2>
<p>Un code comme <code>05-GS-K</code> contient seulement : le chapitre visé (ici 5), les options, et une lettre de contrôle
qui attrape les fautes de frappe. Options : <b>A</b> sans aide (l'élève voit le but, pas la commande : cran C),
<b>G</b> grand écran, <b>S</b> sans chrono. <code>00</code> = pas de chapitre imposé.</p>
<p>Pour en fabriquer un autre : <code>tg classe creer 5 grand sanschrono</code> (sur n'importe quel poste, hors ligne).</p>
<div class="defile"><table class="tableau-legal">
<tr class="entetes"><td>Chapitre ou monde</td><td>Séance guidée (G S)</td><td>Sans aide (A G S)</td><td>Sur chaque poste (S)</td></tr>
${CHAPITRES.map(ligne).join("\n")}
</table></div>
<p class="doux">Les chapitres 1 et 2 s'enchaînent ; ensuite les chapitres 3 à 9 se font dans l'ordre voulu, le 10 s'ouvre
après 5 d'entre eux. Les mondes 11 à 21 s'ouvrent quand le tronc commun nécessaire est fait, le Sommet (23) quand trois
mondes ont leur palier 3 : si un élève n'y a pas encore accès, le jeu le lui dit et il continue là où il en est.</p>

<h2>3. Pendant la séance</h2>
<ul>
<li>L'élève tape <code>tg classe code 05-GS-K Lynx42</code> : le code, puis son pseudonyme (2 à 16 lettres ou chiffres,
sans espace : un « Prénom Nom » est refusé).</li>
<li>Le jeu va au chapitre visé, met la faim de la créature en pause, coupe les notifications et applique les options.</li>
<li>Aucune synchronisation, aucune requête vers le site : si l'élève avait un compte en ligne, il est mis de côté jusqu'à
la fin de la séance.</li>
<li>Pas de pression de temps : avec l'option S, les dressages de créatures n'ont plus de chrono.</li>
<li>À la fin : <code>tg classe fin</code>. Les réglages d'avant reviennent.</li>
</ul>

<h2>4. Le bilan</h2>
<p><code>tg classe bilan</code> affiche : la durée, le nombre de commandes valides, le chapitre et l'étape atteints, les
étapes réussies par cran, les commandes trouvées seul et les endroits où l'élève a bloqué (3 essais ou plus).</p>
<ul>
<li><b>Cran A</b> : étape réussie avec la commande montrée (découverte).</li>
<li><b>Cran C</b> : étape réussie en mode « sans aide », la commande étant cachée.</li>
<li><b>Cran D</b> : exercice de la salle d'entraînement réussi, résultat vérifié.</li>
<li>Une notion est considérée comme acquise au cran C ou D. Le cran B (« à trous ») n'existe pas encore dans le jeu :
le bilan ne l'invente pas.</li>
</ul>
<p><code>tg classe bilan fichier</code> enregistre le bilan en <code>.txt</code> (à imprimer) et en <code>.csv</code> dans
le dossier personnel de l'élève, qui le remet lui-même (clé USB, dossier partagé de l'établissement, ENT).
Côté enseignant, <code>tg classe rassembler &lt;dossier&gt;</code> réunit les fichiers remis dans un seul tableau
(<code>bilan_de_classe.csv</code>) et montre où la classe bloque. Les bilans sont rangés par date et par pseudonyme :
<b>jamais de classement des élèves</b>.</p>

<h2>5. Données personnelles</h2>
<ul>
<li>Le mode classe ne demande ni nom, ni adresse électronique, ni âge, ni compte. Seul un pseudonyme est saisi.</li>
<li>Rien ne quitte l'ordinateur : ni le pseudonyme, ni le bilan, ni les commandes tapées.</li>
<li>Le bilan est un fichier de l'élève. Ce que l'établissement en fait ensuite (où il est rangé, combien de temps) relève
de l'établissement. Conseil : gardez la correspondance pseudonyme ↔ élève sur papier, pas dans le fichier.</li>
<li>Effacer : <code>tg classe effacer</code> oublie la séance ; supprimer <code>~/.terminagotchi</code> et
<code>~/terrain_terminagotchi</code> efface tout le jeu du poste (en fin d'année par exemple).</li>
<li>Le compte en ligne du jeu (le « recensement ») est facultatif et sans rapport avec la classe : il est coupé pendant
les séances. Voir la <a href="/confidentialite">politique de confidentialité</a>.</li>
</ul>
<div class="carte avertissement"><p><b>Reporté :</b> un tableau de bord enseignant <b>en ligne</b> (classes créées sur le
site, suivi à distance). Il demande un serveur, une décision du propriétaire du projet et un avis CNIL (données de
mineurs). Il n'existe pas aujourd'hui, et rien dans le jeu ne prépare un tel envoi.</p></div>

<h2>6. Les fiches de séance</h2>
<p>Une fiche par chapitre (objectif, durée de 45 ou 55 minutes, prérequis, déroulé, code de séance, questions pour
l'oral, trace écrite à imprimer, activité sans ordinateur) : <a href="${e(pdf)}">fiches enseignant (PDF)</a>
· <a href="${e(fiches)}">version texte</a>.</p>

<h2>7. Correspondance avec les programmes (indicative)</h2>
<p class="doux">À faire valider par des enseignants avant de faire foi.</p>
<ul>
<li><b>Cycle 3 et collège, technologie et sciences numériques</b> : organiser des fichiers et des dossiers, notion de
chemin, premiers programmes (chapitres 1 à 4, 8).</li>
<li><b>SNT (seconde)</b> : Internet et le Web (chapitre 9, le Port), les données (chapitre 5 et monde 18, la Salle des Données),
l'informatique embarquée (monde 15, la Tour des Ondes).</li>
<li><b>NSI (première et terminale)</b> : architecture matérielle et systèmes d'exploitation (chapitres 4, 6, 7, la Salle
des Rouages), réseaux et routage (monde 11, le Port), sécurisation des communications (la Citadelle, la Crypte des Codes).</li>
<li><b>CRCN / Pix</b> : gérer des données, environnements numériques, protection et sécurité.</li>
</ul>

<h2>8. Accessibilité</h2>
<ul>
<li>Aujourd'hui : grand écran pour la projection, séance sans chrono, faim en pause, 14 langues, chaque étape
expliquée pour l'enfant et pour l'adulte.</li>
<li>Prévu, pas encore fait : police adaptée à la dyslexie, palettes pour daltoniens, réglage des sons propre à la classe.</li>
</ul>

<h2>9. Et les parents ?</h2>
<p>Tout ce que le jeu fait sur l'ordinateur est décrit sur la page <a href="/parents">Pour les parents</a>. Questions,
retours de classe, envie d'être classe pilote : écrivez-nous (lien « Contact » en bas de page).</p>`;
}
