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

    val ORDRE = listOf("telephone", "systeme", "tuyaux", "scripts", "createur")

    fun creer(jeu: Jeu): Map<String, Branche> {
        val dossierJeu = File(jeu.terrain, "jeu")
        return linkedMapOf(
            "telephone" to Branche("telephone", "Téléphone", "📱", "Agilité", "piloter ton téléphone au clavier", listOf(
                Lecon("Les petits pouvoirs", "Télécommande", 1, listOf(
                    Etape("Appuie sur l'interrupteur de la lampe de poche !", "lampe on", "Lumière ! Une commande, une action.",
                        re = r("^lampe\\s+on")),
                    Etape("… et éteins-la.", "lampe off", "Le petit mot après la commande (on/off) change ce qu'elle fait : les grands disent « un argument ».",
                        re = r("^lampe\\s+off")),
                    Etape("Fais frissonner le téléphone.", "vibre 300", "300 = la durée, en millisecondes.", re = r("^vibre\\b")),
                    Etape("Il reste combien à manger dans le ventre du téléphone ?", "batterie", "Pratique avant de partir ! Les grands disent « la batterie ».", re = r("^batterie\\b")),
                )),
                Lecon("Ouvrir le monde", "Portier", 1, listOf(
                    Etape("Quelles applis habitent dans ton téléphone ?", "applis", "Chaque appli a un nom visible… et un nom secret : son paquet.",
                        re = r("^applis\\b")),
                    Etape("Allume une appli de ton choix.", "ouvre parametres", "Tu lances tes applis au clavier !",
                        re = r("^ouvre\\s+\\S+"), astuce = "Remplace « parametres » par n'importe quelle appli de la liste."),
                    Etape("Ouvre la fenêtre sur un site.", "web wikipedia.org", "Android choisit l'appli qui sait ouvrir les liens.",
                        re = r("^web\\s+\\S+")),
                    Etape("Déplie la carte pour trouver un lieu.", "carte tour eiffel", "La carte s'ouvre directement au bon endroit.",
                        re = r("^carte\\s+\\S+")),
                )),
                Lecon("Le messager", "Messager", 1, listOf(
                    Etape("Fais lire une phrase à voix haute au téléphone.", "dis bonjour", "J'ai une voix ! Les grands disent « synthèse vocale ».", re = r("^dis\\s+\\S+")),
                    Etape("Glisse un message dans la boîte aux lettres de ton choix.", "partage coucou", "C'est toi qui choisis l'appli : WhatsApp, mail…",
                        re = r("^partage\\s+\\S+")),
                    Etape("Écris un petit mot SMS (rien ne part sans toi).", "sms 0612345678 coucou",
                        "Commande + numéro + message : trois morceaux, comme une phrase.", re = r("^sms\\s+\\S+")),
                )),
            )),
            "systeme" to Branche("systeme", "Système", "⚙", "Force", "comprendre la maison et ses habitants (le système)", listOf(
                Lecon("La vigie", "Vigie", 1, listOf(
                    Etape("Qui suis-je pour la maison Android ?", "whoami",
                        "Chaque appli a sa propre chambre fermée, avec son propre utilisateur : les grands disent « le bac à sable ».",
                        re = r("^whoami\\b")),
                    Etape("Et à quels clubs j'appartiens (mes groupes) ?", "id", "uid = numéro d'utilisateur, gid = numéro de groupe.", re = r("^id\\b")),
                    Etape("Qui est réveillé dans la maison ? Liste les processus.", "ps",
                        "Chaque ligne est un processus (un programme réveillé), avec son numéro : le PID.",
                        re = r("^ps\\b")),
                )),
                Lecon("L'intendant", "Intendant", 1, listOf(
                    Etape("Reste-t-il de la place sur le disque (les placards) ?", "df -h", "-h = « human » : des tailles lisibles (Go, Mo).", re = r("^df\\b")),
                    Etape("Combien pèse le dossier du terrain ?", "du -sh terrain_terminagotchi",
                        "du = « disk usage ». Pratique pour trouver ce qui remplit le disque.", re = r("^du\\b"),
                        astuce = "Depuis ton dossier perso, ta chambre (cd ~)."),
                    Etape("Depuis quand le système est allumé ?", "uptime", "« up » = allumé depuis… : le temps de fonctionnement.", re = r("^uptime\\b")),
                )),
                Lecon("Le détective", "Détective", 1, listOf(
                    Etape("Quel est ce système ? Affiche le nom du noyau.", "uname -a", "C'est un noyau Linux ! Android est construit dessus.",
                        re = r("^uname\\b")),
                    Etape("Quel est le modèle du téléphone ?", "getprop ro.product.model",
                        "getprop lit les propriétés système d'Android (ses étiquettes cachées).", re = r("^getprop\\b")),
                )),
            )),
            "tuyaux" to Branche("tuyaux", "Tuyaux", "🔧", "Endurance", "brancher les commandes entre elles, comme des tuyaux", listOf(
                Lecon("Le tuyau", "Plombier", 1, listOf(
                    Etape("Compte tout ce qu'il y a dans la pièce.", "ls | wc -l",
                        "« | » est un tuyau : ce que ls dit coule dans wc, qui compte les lignes. Les grands disent « un pipe ».", re = r("\\|\\s*wc\\b"),
                        astuce = "Le | est dans la rangée de touches au-dessus du clavier."),
                    Etape("Commence une liste de courses avec l'entonnoir >.", "echo banane > courses.txt", "Le fichier courses.txt est né.",
                        fs = { trouve(it, "courses.txt") != null }),
                    Etape("Ajoute une ligne à la fin.", "echo pomme >> courses.txt", "« >> » ajoute au fond sans effacer.",
                        re = r(">>\\s*courses")),
                    Etape("Encore une !", "echo cerise >> courses.txt", "Trois fruits.", re = r("cerise.*>>\\s*courses")),
                    Etape("Trie la liste.", "sort courses.txt", "Par ordre alphabétique, comme un dictionnaire !", re = r("^sort\\b")),
                )),
                Lecon("Le tamis", "Tamiseur", 1, listOf(
                    Etape("Filtre la liste avec un pipe et grep.", "cat courses.txt | grep pomme", "grep, la loupe, ne garde que les lignes qui contiennent le mot.",
                        re = r("\\|\\s*grep\\b")),
                    Etape("Trie et redirige le résultat dans un nouveau fichier.", "sort courses.txt > triee.txt",
                        "On combine : trier, puis rediriger la sortie avec >.", fs = { trouve(it, "triee.txt") != null }),
                    Etape("Vérifie le résultat.", "cat triee.txt", "Bravo, tu branches les outils comme un pro.",
                        re = r("^cat\\b.*triee")),
                )),
            )),
            "scripts" to Branche("scripts", "Scripts", "🧪", "Intelligence", "des recettes que la maison suit toute seule, et TES commandes", listOf(
                Lecon("Ma première recette", "Cuistot", 1, listOf(
                    Etape("Écris une recette (une liste de commandes) sur une feuille.", "echo 'echo \"Miam !\"' > miam.sh",
                        "Une recette rangée dans un fichier : les grands disent « un script ».", fs = { trouve(it, "miam.sh") != null }),
                    Etape("Lis-la à voix haute.", "cat miam.sh", "Elle contient une commande.", re = r("^cat\\b.*miam")),
                    Etape("Demande à la maison de suivre la recette !", "sh miam.sh",
                        "sh lit le script et exécute ses commandes, toute seule. Tu viens de programmer !",
                        re = r("^sh\\s+\\S*miam")),
                )),
                Lecon("Ma propre commande", "Inventeur", 1, listOf(
                    Etape("Écris la fonction « miam » dans ~/.tgrc (le carnet de la maison), pour toujours.",
                        "echo 'miam() { echo \"Miam !\"; }' >> ~/.tgrc",
                        "~/.tgrc est relu avant chaque commande : ta fonction existe partout.",
                        re = r("miam\\s*\\(\\).*>>\\s*~?/?\\S*tgrc")),
                    Etape("Essaie-la !", "miam", "Une commande qui n'existait pas… et qui est à toi.",
                        re = r("^miam\\s*$")),
                )),
                Lecon("La boucle", "Créateur", 1, listOf(
                    Etape("Fais tourner une boucle for trois fois.", "for i in 1 2 3; do echo \"Miam \$i\"; done",
                        "Une boucle for : la base de tous les programmes (et des jeux !).", re = r("^for\\b")),
                    Etape("Une condition : le script existe-t-il ?", "if [ -f miam.sh ]; then echo oui; else echo non; fi",
                        "if = « si ». [ -f fichier ] teste si le fichier existe.", re = r("^if\\b"),
                        astuce = "Les [ et ] sont dans les symboles du clavier."),
                )),
            )),
            "createur" to Branche("createur", "Créateur de jeu", "🎮", "Intelligence", "dessiner et régler ton propre Doom-like", listOf(
                Lecon("L'atelier", "Apprenti", 1, listOf(
                    Etape("Prépare l'atelier du jeu.", "doom", "Le jeu a rangé ses fichiers dans terrain_terminagotchi/jeu. Joue un peu !",
                        fs = { File(dossierJeu, "carte.txt").isFile }),
                    Etape("Passe la porte de l'atelier.", "cd ~/terrain_terminagotchi/jeu", "Voici les fichiers du jeu.",
                        re = r("^cd\\s+.*jeu\\s*$")),
                    Etape("Lis le plan du niveau.", "cat carte.txt", "# = mur, C = départ, B = bestiole, X = sortie.",
                        re = r("^cat\\b.*carte")),
                )),
                Lecon("Mon premier niveau", "Architecte", 1, listOf(
                    Etape("Ouvre l'éditeur sur la carte, change le dessin, puis Enregistrer. Garde des murs # tout autour !", "edite carte.txt",
                        "Ta carte est enregistrée !",
                        fs = { Doom.carteModifiee(dossierJeu) }),
                    Etape("Teste ton niveau !", "doom", "C'est TON niveau. Les vrais level designers font pareil.",
                        re = r("^doom\\b")),
                )),
                Lecon("Les réglages", "Ingénieur", 1, listOf(
                    Etape("Ouvre les réglages du jeu, change une valeur (vitesse, vie, couleurs), puis Enregistrer.", "edite reglages.txt",
                        "Réglage enregistré !",
                        fs = { Doom.reglagesModifies(dossierJeu) }),
                    Etape("Teste le changement.", "doom", "Ce sont des variables : une boîte avec un nom et une valeur. La base du code !",
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
