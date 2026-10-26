/**
 * Terminagotchi — les textes juridiques complets, en français (la version qui fait foi).
 *
 * Les autres langues montrent un résumé traduit (i18n_pages.js) puis ce texte, marqué lang="fr".
 * Tout ce qui est écrit ici doit correspondre à ce que fait VRAIMENT le serveur (schema.sql, routes /api/
 * de worker.js) : on ne dit jamais qu'on collecte moins que la réalité.
 *
 * ⚠ Ces textes sont un MODÈLE : ils doivent être relus par une personne compétente avant de faire foi.
 */

const e = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/** Hébergeur (vérifié le 26 octobre 2026 : rapport annuel 10-K 2025 de Cloudflare, page de garde). */
export const HEBERGEUR = {
  nom: "Cloudflare, Inc.",
  adresse: "101 Townsend Street, San Francisco, CA 94107, États-Unis",
  telephone: "+1 888 993 5273",
  site: "https://www.cloudflare.com",
};

const MISE_A_JOUR = "26 octobre 2026";

const AVERTISSEMENT = `<div class="carte avertissement"><p><b>⚠ Modèle à faire vérifier.</b> Ce texte a été rédigé
comme point de départ par l'auteur du jeu. Il n'a pas encore été relu par un juriste : il doit être vérifié avant de faire foi.</p></div>`;

/** Ligne d'un tableau « donnée | pourquoi | base légale | durée ». */
const ligne = (donnee, pourquoi, base, duree) => `<tr><td>${donnee}</td><td data-t="Pourquoi">${pourquoi}</td>`
  + `<td data-t="Base légale">${base}</td><td data-t="Durée">${duree}</td></tr>`;

/**
 * La politique de confidentialité complète.
 * @param {{ contact: string, depot: string, conservation: { inactifMois: number, ipHeures: number, sessionJours: number } }} c
 */
export function confidentialiteFr(c) {
  const mail = `<a href="mailto:${e(c.contact)}">${e(c.contact)}</a>`;
  const ans = c.conservation.inactifMois % 12 === 0 ? `${c.conservation.inactifMois / 12} ans` : `${c.conservation.inactifMois} mois`;
  const compte = `tant que le compte existe ; effacé avec lui (sur demande, ou automatiquement après ${ans} sans aucune synchronisation)`;
  const contrat = "fourniture du service demandé (art. 6.1.b du RGPD)";
  const interet = "intérêt légitime (art. 6.1.f du RGPD)";
  return `${AVERTISSEMENT}
<p class="doux">Dernière mise à jour : ${MISE_A_JOUR}.</p>

<h2>1. Qui est responsable ?</h2>
<p>Le responsable du traitement est l'éditeur du site terminagotchi.com, un particulier qui publie le jeu à titre non professionnel
(voir les <a href="/mentions-legales">mentions légales</a>). Pour toute question : ${mail}.</p>

<h2>2. Quand des données sont-elles collectées ?</h2>
<p><b>Le jeu fonctionne entièrement sans compte et hors ligne.</b> Sans compte, le jeu n'envoie rien à notre serveur :
la partie reste sur l'appareil.</p>
<p>Des données ne sont envoyées que si le joueur crée un compte (commande <code>compte creer</code>, appelée « recensement »)
ou relie un appareil à un compte existant. Le compte est <b>facultatif</b> : il sert à sauvegarder la progression, à la retrouver
sur un autre appareil, à figurer au classement et à recevoir des badges.</p>

<h2>3. Les données, leur but, leur base légale et leur durée</h2>
<div class="defile"><table class="tableau-legal">
<tr class="entetes"><th>Donnée</th><th>Pourquoi</th><th>Base légale</th><th>Durée de conservation</th></tr>
${ligne("<b>Pseudo</b> (3 à 20 caractères, choisi par le joueur), identifiant interne tiré au hasard, date d'inscription et date de la dernière synchronisation",
    "identifier le compte ; l'afficher au classement et sur le profil public", contrat, compte)}
${ligne("<b>Clé d'appareil</b> : seule son empreinte (SHA-256) est stockée, avec le type d'appareil (« android » ou « pc ») et sa date de création",
    "reconnaître les appareils du joueur, sans mot de passe ni e-mail", contrat,
    "jusqu'à la déconnexion de cet appareil (<code>compte deconnexion</code>) ou la suppression du compte")}
${ligne("<b>Code de secours</b> : seule son empreinte (HMAC) est stockée, avec sa date",
    "rendre le compte si l'appareil est perdu", contrat, "remplacée à chaque nouveau code ; effacée avec le compte")}
${ligne("<b>Jetons temporaires</b> : jetons TG-… pour relier un appareil, liens de connexion au site (empreinte seulement)",
    "relier un appareil ; ouvrir une session sur le site", contrat, "10 minutes ; effacés au plus tard 24 heures après")}
${ligne("<b>Session sur le site</b> : empreinte du jeton de session (cookie <code>tg_session</code>)",
    "rester connecté à la page « Mon compte »", contrat, `${c.conservation.sessionJours} jours, ou jusqu'à la déconnexion`)}
${ligne(`<b>Progression synchronisée</b>, pour chaque partie (jusqu'à 30 par compte) : nom donné à la créature, caractère, forme,
    XP, niveau, statistiques, faim, nombre de commandes tapées, <b>noms</b> des commandes déjà essayées (par exemple <code>ls</code> ou <code>cd</code>,
    jamais le reste de la ligne tapée), compétences, collection, records de temps, captures (espèce, variante, marque, humeur, taille,
    statistiques, rareté, stade, date, dossier du terrain où elle a eu lieu), types d'appareils utilisés et date de leur dernière synchronisation,
    choix de partage de la galerie`,
    "sauvegarder la partie, la synchroniser entre appareils, calculer le classement", contrat, compte)}
${ligne("<b>Badges</b> (type, titre, date)", "prouver une réussite par un lien public vérifiable", contrat, compte)}
${ligne(`<b>Anti-triche</b> : registre des apparitions déjà utilisées (identifiant de « graine » = date du jour et début de l'empreinte de la clé
    d'appareil, numéro d'apparition, identifiant de la capture, date). Les graines elles-mêmes ne sont pas stockées : elles sont recalculées.`,
    "vérifier que les captures n'ont pas été inventées et qu'une apparition ne sert qu'une fois", `${interet} : un classement équitable`, compte)}
${ligne("<b>Adresse IP</b>, dans un compteur d'essais, seulement lors de l'inscription, de la liaison d'un appareil ou de l'utilisation d'un code de secours",
    "limiter les abus (essais en masse)", `${interet} : la sécurité du service`, `au plus ${c.conservation.ipHeures} heures`)}
${ligne("<b>Compteurs d'essais</b> par compte (synchronisations, drapeaux du CTF, nouveaux codes de secours)",
    "limiter les abus", `${interet} : la sécurité du service`, `au plus ${c.conservation.ipHeures} heures`)}
</table></div>

<h2>4. Ce qui est public</h2>
<p>Le site montre à tous, pour chaque compte : le pseudo, le nom de la créature, son niveau, son XP, son rang, son stade, sa forme, son caractère,
ses statistiques, le nombre de commandes tapées et de commandes différentes, les compétences, la collection, les records, les types d'appareils
(téléphone, PC), la date d'inscription, les badges et le nombre de captures (page <code>/joueur/pseudo</code>, classement, et la même chose au
format JSON). Les <b>captures</b> détaillées ne sont montrées dans la galerie que si le joueur l'a demandé (<code>compte partage on</code>) ;
il peut les retirer à tout moment (<code>compte partage off</code>).</p>
<p>C'est pourquoi nous conseillons de <b>ne pas utiliser son vrai nom</b> comme pseudo ni comme nom de créature.</p>

<h2>5. Ce que nous ne collectons pas</h2>
<p>Pas de nom réel, pas d'adresse e-mail, pas de mot de passe, pas d'âge, pas de numéro de téléphone, pas de localisation, pas de contacts,
pas de photo. Pas de publicité, pas de mesure d'audience, pas de traceur, pas de messagerie entre joueurs. Le contenu des commandes tapées
n'est jamais envoyé : seulement leur nom. Les données ne sont jamais vendues ni cédées.</p>
<p>Les polices de caractères sont hébergées sur le site lui-même : afficher une page n'envoie aucune requête à Google ni à un autre tiers.</p>
<p>Si vous nous écrivez à ${mail}, votre message et votre adresse e-mail sont gardés le temps de traiter la demande, puis au plus un an.</p>

<h2>6. Qui reçoit les données ?</h2>
<p>Personne d'autre que l'éditeur, à part notre <b>hébergeur</b>, ${HEBERGEUR.nom} (${HEBERGEUR.adresse}), qui fait tourner le site
(Cloudflare Workers) et sa base de données (Cloudflare D1) en tant que sous-traitant. Pour acheminer les pages et protéger le site contre
les attaques, Cloudflare traite aussi techniquement l'adresse IP des visiteurs, selon sa propre
<a href="https://www.cloudflare.com/privacypolicy/">politique de confidentialité</a>.</p>
<p>Le code source et les fichiers à télécharger (l'appli Android et le jeu PC) sont hébergés sur <b>GitHub</b> (GitHub, Inc., États-Unis) :
quand vous les téléchargez, c'est GitHub qui reçoit la demande, selon sa propre politique de confidentialité. De même, quand un compte
est utilisé, le jeu lit un petit fichier sur GitHub pour connaître l'adresse du serveur : GitHub voit alors l'adresse IP, mais rien d'autre.</p>

<h2>7. Transfert hors de l'Union européenne</h2>
<p>Cloudflare, Inc. est une société américaine : les données peuvent être stockées et traitées aux États-Unis ou ailleurs dans son réseau.
Ce transfert est encadré par le <b>Data Privacy Framework</b> UE–États-Unis (décision d'adéquation de la Commission européenne du
10 juillet 2023), auquel Cloudflare est certifié, et par les clauses contractuelles types de son accord de traitement des données.</p>

<h2>8. Cookies</h2>
<p>Le site n'utilise <b>aucun cookie de publicité ni de mesure d'audience</b>. Il peut poser trois petits cookies, tous nécessaires à ce que
vous demandez, et donc dispensés de consentement (article 82 de la loi Informatique et Libertés) :</p>
<ul>
<li><code>lang</code> : la langue choisie dans le menu (1 an). Il n'est posé que si vous changez de langue.</li>
<li><code>tg_session</code> : la connexion à la page « Mon compte », seulement après avoir ouvert le lien donné par <code>compte site</code>
(${c.conservation.sessionJours} jours, ou jusqu'à la déconnexion).</li>
<li><code>role</code> : un cookie d'exercice de l'épreuve 4 du CTF web (« Le cookie de confiance »), posé seulement quand on ouvre cette
épreuve ; il s'efface à la fermeture du navigateur.</li>
</ul>

<h2>9. Les enfants</h2>
<p>Terminagotchi est fait pour les enfants dès 7 ans. Il est conçu pour collecter le minimum : un pseudo et la progression du jeu,
sans aucune donnée qui permette d'identifier ou de contacter l'enfant. Aucun traitement ne repose sur le consentement de l'enfant.</p>
<p>Pour un enfant de moins de 15 ans, nous recommandons que le compte soit créé <b>avec un parent</b>, qui peut exercer tous les droits
ci-dessous en son nom. Un parent qui découvre qu'un compte a été créé sans son accord peut demander sa suppression à ${mail}.</p>

<h2>10. Sécurité</h2>
<p>Il n'y a pas de mot de passe à voler. Les clés d'appareil, les codes de secours, les jetons et les sessions ne sont stockés que sous forme
d'empreintes : même en lisant la base de données, on ne peut pas les retrouver. Les échanges passent par HTTPS.</p>

<h2>11. Vos droits</h2>
<p>Vous avez le droit d'<b>accéder</b> à vos données, de les <b>rectifier</b>, de les <b>effacer</b>, d'en <b>limiter</b> l'utilisation,
de vous y <b>opposer</b> et d'en recevoir une <b>copie</b> dans un format lisible (JSON). Pour cela, écrivez à ${mail} en indiquant le pseudo.
Pour vérifier que le compte est bien le vôtre, nous pourrons vous demander une information que seul le jeu peut afficher.
Nous répondons dans un délai d'un mois.</p>
<p>Le jeu peut aussi supprimer lui-même le compte et toutes ses données, sans passer par nous (fonction de l'API <code>DELETE /api/compte</code>,
bientôt accessible depuis le jeu).</p>
<p>Si vous estimez que vos droits ne sont pas respectés, vous pouvez adresser une réclamation à la <b>CNIL</b>
(<a href="https://www.cnil.fr/fr/plaintes">www.cnil.fr/fr/plaintes</a>, 3 place de Fontenoy, TSA 80715, 75334 Paris Cedex 07).</p>

<h2>12. Modifications</h2>
<p>Cette politique peut évoluer avec le jeu. La date de mise à jour est indiquée en haut. Le code du site, et donc ce qui est vraiment
stocké, peut être vérifié par tous sur <a href="${e(c.depot)}">GitHub</a>.</p>`;
}

/**
 * Les mentions légales (article 1-1 de la LCEN).
 * @param {{ contact: string, depot: string, editeur: { anonyme: boolean, nom: string, adresse: string, directeur: string }, licence: string }} c
 */
export function mentionsFr(c) {
  const mail = `<a href="mailto:${e(c.contact)}">${e(c.contact)}</a>`;
  const ed = c.editeur;
  const anonyme = ed.anonyme || !ed.nom;
  const editeur = anonyme
    ? `<p>Le site terminagotchi.com est édité par un <b>particulier, à titre non professionnel</b>.</p>
<p>Conformément à l'article 1-1, II de la loi n° 2004-575 du 21 juin 2004 pour la confiance dans l'économie numérique (LCEN),
l'éditeur a choisi de ne pas rendre public son nom ni son adresse : ces éléments d'identification ont été communiqués à l'hébergeur
mentionné ci-dessous.</p>`
    : `<p>Le site terminagotchi.com est édité par <b>${e(ed.nom)}</b>, particulier, à titre non professionnel.</p>
${ed.adresse ? `<p>Adresse : ${e(ed.adresse)}</p>` : ""}`;
  const directeur = ed.directeur ? e(ed.directeur) : anonyme ? "l'éditeur du site (voir ci-dessus)" : e(ed.nom);
  const licence = c.licence
    ? `<p>Le code source du jeu et du site est publié sur <a href="${e(c.depot)}">GitHub</a> sous la licence <b>${e(c.licence)}</b>
(voir le fichier LICENSE du dépôt).</p>`
    : `<p>Le code source du jeu et du site est consultable sur <a href="${e(c.depot)}">GitHub</a>. Aucune licence libre n'a encore été
choisie : tant qu'aucune licence n'est indiquée, le code reste protégé par le droit d'auteur (tous droits réservés).</p>`;
  return `${AVERTISSEMENT}
<h2>L'éditeur du site</h2>
${editeur}
<p>Contact : ${mail}</p>
<p>Directeur de la publication : ${directeur}.</p>

<h2>Hébergeur</h2>
<p><b>${HEBERGEUR.nom}</b><br>${HEBERGEUR.adresse}<br>Téléphone : ${HEBERGEUR.telephone}<br>
<a href="${HEBERGEUR.site}">${HEBERGEUR.site.replace("https://", "")}</a></p>
<p>Le site fonctionne sur Cloudflare Workers et sa base de données sur Cloudflare D1.</p>

<h2>Propriété intellectuelle</h2>
<p>Le jeu Terminagotchi, ses textes, ses bestioles, leurs dessins et leurs noms sont l'œuvre de l'éditeur, sauf mention contraire.
Toute reproduction au-delà de ce que permettent la loi ou la licence indiquée ci-dessous demande son accord.</p>
${licence}

<h2>Crédits</h2>
<ul>
<li>Police <b>Press Start 2P</b>, de CodeMan38 — Copyright 2012 The Press Start 2P Project Authors.</li>
<li>Police <b>VT323</b>, de Peter Hull — Copyright 2011 The VT323 Project Authors.</li>
</ul>
<p>Ces deux polices sont distribuées sous la licence libre <b>SIL Open Font License 1.1</b> (textes complets :
<a href="/polices/OFL-PressStart2P.txt">Press Start 2P</a>, <a href="/polices/OFL-VT323.txt">VT323</a>).
Elles sont hébergées sur ce site (fichiers du projet Fontsource), sans appel à Google Fonts.</p>

<h2>Données personnelles</h2>
<p>Voir la <a href="/confidentialite">politique de confidentialité</a>.</p>

<h2>Signaler un contenu</h2>
<p>Pour signaler un pseudo ou un nom de créature inapproprié, ou tout contenu illicite, écrivez à ${mail} en indiquant l'adresse de la page.</p>`;
}
