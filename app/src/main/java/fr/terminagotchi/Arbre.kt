package fr.terminagotchi

import java.io.File

class Branche(
    val cle: String,
    val nom: String,
    val icone: String,
    val stat: String,
    val desc: String,
    val lecons: List<Lecon>,
)

/** L'arbre de compétences du téléphone, ouvert après le tronc commun. */
object Arbre {
    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)

    /** Cherche un fichier par son nom n'importe où dans la maison (sur 5 niveaux). */
    fun trouve(jeu: Jeu, nom: String): File? =
        jeu.home.walkTopDown().maxDepth(5).firstOrNull { it.isFile && it.name == nom }

    val ORDRE = listOf("telephone", "systeme", "tuyaux", "port", "scripts", "createur")

    fun creer(jeu: Jeu): Map<String, Branche> {
        val dossierJeu = File(jeu.terrain, "jeu")
        return linkedMapOf(
            "telephone" to Branche("telephone", "Téléphone", "📱", "Agilité", "piloter ton téléphone au clavier", listOf(
                Lecon("Les petits pouvoirs", "Télécommande", 1, listOf(
                    Etape("Allume la lampe torche !", "lampe on", "Lumière ! Une commande, une action.",
                        re = r("^lampe\\s+on")),
                    Etape("… et éteins-la.", "lampe off", "Un argument (on/off) change le comportement.",
                        re = r("^lampe\\s+off")),
                    Etape("Fais-moi vibrer.", "vibre 300", "300 = la durée en millisecondes.", re = r("^vibre\\b")),
                    Etape("Comment va la batterie ?", "batterie", "Pratique avant de partir !", re = r("^batterie\\b")),
                )),
                Lecon("Ouvrir le monde", "Portier", 1, listOf(
                    Etape("Quelles applis as-tu ?", "applis", "Chaque appli a un nom visible… et un nom secret (paquet).",
                        re = r("^applis\\b")),
                    Etape("Lance une appli de ton choix.", "ouvre parametres", "Tu lances tes applis au clavier !",
                        re = r("^ouvre\\s+\\S+"), astuce = "Remplace « parametres » par n'importe quelle appli de la liste."),
                    Etape("Ouvre un site.", "web wikipedia.org", "Android choisit l'appli qui sait ouvrir les liens.",
                        re = r("^web\\s+\\S+")),
                    Etape("Cherche un lieu.", "carte tour eiffel", "Les cartes s'ouvrent directement sur le lieu.",
                        re = r("^carte\\s+\\S+")),
                )),
                Lecon("Le messager", "Messager", 1, listOf(
                    Etape("Fais parler le téléphone.", "dis bonjour", "J'ai une voix !", re = r("^dis\\s+\\S+")),
                    Etape("Prépare un message à partager.", "partage coucou", "Tu choisis l'appli : WhatsApp, mail…",
                        re = r("^partage\\s+\\S+")),
                    Etape("Prépare un SMS (rien ne part sans toi).", "sms 0612345678 coucou",
                        "Commande + numéro + message : trois morceaux, comme une phrase.", re = r("^sms\\s+\\S+")),
                )),
            )),
            "systeme" to Branche("systeme", "Système", "⚙", "Force", "comprendre la machine", listOf(
                Lecon("La vigie", "Vigie", 1, listOf(
                    Etape("Qui suis-je pour Android ?", "whoami", "Chaque appli a son propre utilisateur : c'est le bac à sable.",
                        re = r("^whoami\\b")),
                    Etape("Et mes groupes ?", "id", "uid = numéro d'utilisateur, gid = groupe.", re = r("^id\\b")),
                    Etape("Qui tourne en ce moment ?", "ps", "Chaque ligne est un programme vivant, avec son PID.",
                        re = r("^ps\\b")),
                )),
                Lecon("L'intendant", "Intendant", 1, listOf(
                    Etape("Reste-t-il de la place ?", "df -h", "-h = « human » : des tailles lisibles.", re = r("^df\\b")),
                    Etape("Combien pèse notre terrain ?", "du -sh terrain_terminagotchi",
                        "du = « disk usage ». Pratique pour trouver ce qui remplit la mémoire.", re = r("^du\\b"),
                        astuce = "Depuis ton dossier perso (cd ~)."),
                    Etape("Depuis quand le téléphone est allumé ?", "uptime", "« up » = allumé depuis…", re = r("^uptime\\b")),
                )),
                Lecon("Le détective", "Détective", 1, listOf(
                    Etape("Quel est ce système ?", "uname -a", "C'est un noyau Linux ! Android est construit dessus.",
                        re = r("^uname\\b")),
                    Etape("Quel est le modèle du téléphone ?", "getprop ro.product.model",
                        "getprop lit les réglages internes d'Android.", re = r("^getprop\\b")),
                )),
            )),
            "tuyaux" to Branche("tuyaux", "Tuyaux", "🔧", "Endurance", "brancher les commandes entre elles", listOf(
                Lecon("Le tuyau", "Plombier", 1, listOf(
                    Etape("Compte les éléments du dossier.", "ls | wc -l",
                        "« | » envoie le résultat de ls dans wc, qui compte les lignes.", re = r("\\|\\s*wc\\b"),
                        astuce = "Le | est dans la rangée de touches au-dessus du clavier."),
                    Etape("Commence une liste de courses.", "echo banane > courses.txt", "Le fichier est créé.",
                        fs = { trouve(it, "courses.txt") != null }),
                    Etape("Ajoute une ligne.", "echo pomme >> courses.txt", "« >> » ajoute sans effacer.",
                        re = r(">>\\s*courses")),
                    Etape("Encore une !", "echo cerise >> courses.txt", "Trois fruits.", re = r("cerise.*>>\\s*courses")),
                    Etape("Trie la liste.", "sort courses.txt", "Par ordre alphabétique !", re = r("^sort\\b")),
                )),
                Lecon("Le tamis", "Tamiseur", 1, listOf(
                    Etape("Filtre la liste.", "cat courses.txt | grep pomme", "grep ne garde que les lignes qui contiennent le mot.",
                        re = r("\\|\\s*grep\\b")),
                    Etape("Trie et range dans un nouveau fichier.", "sort courses.txt > triee.txt",
                        "On combine : trier, puis écrire le résultat.", fs = { trouve(it, "triee.txt") != null }),
                    Etape("Vérifie le résultat.", "cat triee.txt", "Bravo, tu enchaînes les outils comme un pro.",
                        re = r("^cat\\b.*triee")),
                )),
            )),
            "port" to Branche("port", "Le Port", "⚓", "Agilité", "les réseaux : adresses, ports, TCP/UDP, routage, box, HTTPS", listOf(
                Lecon("Les quais", "Capitaine", 1, listOf(
                    Etape("Sur internet, chaque machine a une adresse (IP) et des quais numérotés : les ports. Regarde l'annuaire des quais.",
                        "ports", "443 = le web chiffré, 22 = SSH, 53 = le DNS. Un service attend toujours sur le même quai.",
                        re = r("^(ports|ss|netstat)\\b")),
                    Etape("Demande à l'annuaire d'internet (le DNS) l'adresse d'un site.", "nslookup example.com",
                        "Le DNS traduit un nom en adresse IP, comme un annuaire traduit un nom en numéro.",
                        re = r("^(nslookup|dig|host)\\s+\\S+")),
                )),
                Lecon("Le facteur", "Facteur", 1, listOf(
                    Etape("Frappe à la porte d'un site, sans entrer.", "curl -I https://example.com",
                        "200 = « entrez ! », 301 = « c'est à côté », 404 = introuvable, 500 = le site est malade.",
                        re = r("^curl\\b.*-I")),
                    Etape("Rapporte-moi un colis : la page entière, rangée dans un fichier.", "curl -o colis.html https://example.com",
                        "-o = « output » : la réponse va dans un fichier au lieu de l'écran.", fs = { trouve(it, "colis.html") != null }),
                    Etape("Ouvre le colis : les 5 premières lignes.", "head -n 5 colis.html", "Du HTML : le langage des pages web !",
                        re = r("^(head|cat)\\b.*colis")),
                )),
                Lecon("TCP et UDP", "Aiguilleur", 1, listOf(
                    Etape("Regarde une connexion se faire, en mode bavard.", "curl -v https://example.com",
                        "« Connected to … port 443 » : TCP fait d'abord une poignée de main (SYN, SYN-ACK, ACK), puis on parle. Fiable, dans l'ordre.",
                        re = r("^curl\\b.*-v")),
                    Etape("Le DNS, lui, envoie une simple carte postale (UDP). Demande un autre site.", "nslookup wikipedia.org",
                        "UDP : pas de poignée de main, plus rapide, mais sans garantie. Parfait pour une petite question.",
                        re = r("^(nslookup|dig|host)\\s+\\S+")),
                )),
                Lecon("Le phare", "Gardien du phare", 1, listOf(
                    Etape("Par où sortent nos paquets ? Regarde les routes.", "route",
                        "« default via … » : la passerelle, la sortie vers internet. Chez toi, c'est la box (ou le partage de connexion).",
                        re = r("^(route|ip\\s+r)")),
                    Etape("Envoie un signal à la passerelle (l'adresse après « via »).", "ping -c 2 192.168.1.1",
                        "Si elle répond en 1 ou 2 ms, c'est qu'elle est tout près : c'est le premier relais de chaque paquet.",
                        re = r("^ping\\b"), astuce = "Remplace 192.168.1.1 par l'adresse vue avec « route »."),
                )),
                Lecon("La box et le cadenas", "Coffre-fort", 1, listOf(
                    Etape("Quelle est ton adresse vue d'internet ?", "curl https://api.ipify.org",
                        "Elle est différente de ton adresse locale : la box traduit (NAT) toutes les adresses de la maison en une seule.",
                        re = r("^curl\\b.*(ipify|ifconfig\\.me|icanhazip)")),
                    Etape("Regarde le cadenas d'un site : son certificat.", "curl -v https://wikipedia.org",
                        "Le certificat prouve qui est le site ; ensuite tout est chiffré (TLS). C'est le « s » de https.",
                        re = r("^curl\\b.*-v.*https://")),
                    Etape("Compare avec un site en http (sans s).", "curl -v http://example.com",
                        "En http://, tout passe en clair : chaque relais du trajet peut lire. Le cadenas, ça compte !",
                        re = r("^curl\\b.*http://")),
                )),
            )),
            "scripts" to Branche("scripts", "Scripts", "🧪", "Intelligence", "automatiser et créer TES commandes", listOf(
                Lecon("Ma première recette", "Cuistot", 1, listOf(
                    Etape("Écris une recette (un script).", "echo 'echo \"Miam !\"' > miam.sh",
                        "Un script = des commandes rangées dans un fichier.", fs = { trouve(it, "miam.sh") != null }),
                    Etape("Lis-la.", "cat miam.sh", "Elle contient une commande.", re = r("^cat\\b.*miam")),
                    Etape("Cuisine-la !", "sh miam.sh", "sh lit le fichier et exécute ses commandes. Tu viens de programmer !",
                        re = r("^sh\\s+\\S*miam")),
                )),
                Lecon("Ma propre commande", "Inventeur", 1, listOf(
                    Etape("Invente la commande « miam » pour toujours.", "echo 'miam() { echo \"Miam !\"; }' >> ~/.tgrc",
                        "~/.tgrc est lu avant chaque commande : tout ce qu'il contient existe partout.",
                        re = r("miam\\s*\\(\\).*>>\\s*~?/?\\S*tgrc")),
                    Etape("Essaie-la !", "miam", "Une commande qui n'existait pas… et qui est à toi.",
                        re = r("^miam\\s*$")),
                )),
                Lecon("La boucle", "Créateur", 1, listOf(
                    Etape("Répète une action trois fois.", "for i in 1 2 3; do echo \"Miam \$i\"; done",
                        "Une boucle : la base de tous les programmes (et des jeux !).", re = r("^for\\b")),
                    Etape("Une condition !", "if [ -f miam.sh ]; then echo oui; else echo non; fi",
                        "if = « si ». [ -f fichier ] teste si le fichier existe.", re = r("^if\\b"),
                        astuce = "Les [ et ] sont dans les symboles du clavier."),
                )),
            )),
            "createur" to Branche("createur", "Créateur de jeu", "🎮", "Intelligence", "dessiner et régler ton propre Doom-like", listOf(
                Lecon("L'atelier", "Apprenti", 1, listOf(
                    Etape("Prépare l'atelier du jeu.", "doom", "Le jeu crée ses fichiers dans terrain_terminagotchi/jeu. Joue un peu !",
                        fs = { File(dossierJeu, "carte.txt").isFile }),
                    Etape("Va dans l'atelier.", "cd ~/terrain_terminagotchi/jeu", "Voici les fichiers du jeu.",
                        re = r("^cd\\s+.*jeu\\s*$")),
                    Etape("Regarde le niveau.", "cat carte.txt", "# = mur, C = départ, B = bestiole, X = sortie.",
                        re = r("^cat\\b.*carte")),
                )),
                Lecon("Mon premier niveau", "Architecte", 1, listOf(
                    Etape("Ouvre l'éditeur sur la carte.", "edite carte.txt",
                        "Modifie le dessin, puis Enregistrer. Garde des murs # tout autour !",
                        fs = { Doom.carteModifiee(dossierJeu) }),
                    Etape("Teste ton niveau !", "doom", "C'est TON niveau. Les vrais level designers font pareil.",
                        re = r("^doom\\b")),
                )),
                Lecon("Les réglages", "Ingénieur", 1, listOf(
                    Etape("Ouvre les réglages du jeu.", "edite reglages.txt",
                        "Change une valeur (vitesse, vie, couleurs), puis Enregistrer.",
                        fs = { Doom.reglagesModifies(dossierJeu) }),
                    Etape("Teste le changement.", "doom", "Ce sont des variables : un nom, une valeur. La base du code !",
                        re = r("^doom\\b")),
                )),
            )),
        )
    }

    fun texte(jeu: Jeu): String {
        val sb = StringBuilder("🌳 Arbre de compétences\n")
        if (!jeu.troncFini) {
            sb.append("Termine d'abord le tronc commun (${jeu.lecon}/${jeu.lecons.size} leçons).\n")
        }
        for (cle in ORDRE) {
            val b = jeu.branches[cle] ?: continue
            val fait = jeu.progresBranche(cle)
            val etat = when {
                fait >= b.lecons.size -> "✔ maîtrisée"
                jeu.brancheActive() == cle -> "◀ en cours"
                else -> ""
            }
            sb.append("\n${b.icone} ${b.nom} ($fait/${b.lecons.size}) $etat\n   ${b.desc} · nourrit ${b.stat}\n")
            b.lecons.forEachIndexed { i, l -> sb.append("   ${if (i < fait) "■" else "□"} ${l.titre} → ${l.skill}\n") }
        }
        sb.append("\nPour suivre une branche :  arbre ${ORDRE.joinToString(" | ")}")
        return sb.toString()
    }
}
