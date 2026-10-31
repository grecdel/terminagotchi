package fr.terminagotchi

import java.io.File

class Branche(
    val cle: String,
    private val nomCle: String,
    val icone: String,
    val stat: String,
    private val descCle: String,
    val lecons: List<Lecon>,
) {
    val nom: String get() = t(nomCle)
    val desc: String get() = t(descCle)
}

/**
 * Les leçons propres au téléphone (les anciennes branches de l'arbre : téléphone, système, tuyaux, scripts,
 * créateur). La Maison endormie (Histoire.kt) les range dans ses chapitres : le jardin du téléphone, la salle des
 * machines, la bibliothèque, l'atelier… La commande « arbre » montre maintenant les ailes de la maison.
 */
object Arbre {
    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)

    /** le lieu de la liste de courses (chapitre 5, la bibliothèque) et son fichier */
    const val BIBLIO = "bibliotheque"
    /** le dossier du Doom-like (carte.txt, reglages.txt) dans la zone d'aventure */
    const val JEU = "jeu"
    const val COURSES = "$BIBLIO/courses.txt"

    /** ~/.tgrc (avec le point : le fichier que le shell charge) contient la fonction miam */
    fun tgrcMiam(jeu: Jeu): Boolean =
        try { Regex("miam\\s*\\(\\)").containsMatchIn(File(jeu.home, ".tgrc").readText()) } catch (e: Exception) { false }

    /** Cherche un fichier par son nom n'importe où dans la maison (sur 5 niveaux). */
    fun trouve(jeu: Jeu, nom: String): File? =
        jeu.home.walkTopDown().maxDepth(5).firstOrNull { it.isFile && it.name == nom }

    fun creer(jeu: Jeu): Map<String, Branche> {
        val dossierJeu = File(jeu.terrain, "jeu")
        return linkedMapOf(
            "telephone" to Branche("telephone", "arbre.telephone.nom", "📱", "Agilité", "arbre.telephone.desc", listOf(
                Lecon("lec.android0.titre", "Télécommande", 1, listOf(
                    Etape("arbre.telephone0.0.dit", "lampe on",
                        "arbre.telephone0.0.bravo",
                        re = r("^lampe\\s+on")),
                    Etape("lec.android0.3.dit", "lampe off",
                        "arbre.telephone0.1.bravo",
                        re = r("^lampe\\s+off")),
                    Etape("arbre.telephone0.2.dit", "vibre 300",
                        "arbre.telephone0.2.bravo", re = r("^vibre\\b")),
                    Etape("arbre.telephone0.3.dit", "batterie",
                        "arbre.telephone0.3.bravo", re = r("^batterie\\b")),
                )),
                Lecon("lec.android1.titre", "Portier", 1, listOf(
                    Etape("arbre.telephone1.0.dit", "applis",
                        "arbre.telephone1.0.bravo",
                        re = r("^applis\\b")),
                    Etape("arbre.telephone1.1.dit", "ouvre parametres",
                        "arbre.telephone1.1.bravo",
                        re = r("^ouvre\\s+\\S+"), astuceCle = "arbre.telephone1.1.astuce"),
                    Etape("arbre.telephone1.2.dit", "web wikipedia.org",
                        "arbre.telephone1.2.bravo",
                        re = r("^web\\s+\\S+")),
                    Etape("lec.android1.1.dit", "carte tour eiffel",
                        "arbre.telephone1.3.bravo",
                        re = r("^carte\\s+\\S+")),
                )),
                Lecon("arbre.telephone2.titre", "Messager", 1, listOf(
                    Etape("arbre.telephone2.0.dit", "dis bonjour",
                        "arbre.telephone2.0.bravo", re = r("^dis\\s+\\S+")),
                    Etape("arbre.telephone2.1.dit", "partage coucou",
                        "arbre.telephone2.1.bravo",
                        re = r("^partage\\s+\\S+")),
                    Etape("arbre.telephone2.2.dit", "sms 0612345678 coucou",
                        "arbre.telephone2.2.bravo", re = r("^sms\\s+\\S+")),
                )),
            )),
            "systeme" to Branche("systeme", "branche.Système", "⚙", "Force", "arbre.systeme.desc", listOf(
                Lecon("lec.systeme0.titre", "Vigie", 1, listOf(
                    Etape("arbre.systeme0.0.dit", "whoami",
                        "arbre.systeme0.0.bravo",
                        re = r("^(whoami|id(\\s+-un?)?(\\s|$))")),
                    Etape("arbre.systeme0.1.dit", "id",
                        "arbre.systeme0.1.bravo", re = r("^id\\b")),
                    Etape("lec.systeme0.1.dit", "ps",
                        "lec.systeme0.1.bravo",
                        re = r("^ps\\b")),
                )),
                Lecon("lec.systeme1.titre", "Intendant", 1, listOf(
                    Etape("lec.systeme1.0.dit", "df -h",
                        "lec.systeme1.0.bravo", re = r("^df\\b")),
                    Etape("lec.systeme1.1.dit", "du -sh ~/terrain_terminagotchi",
                        "lec.systeme1.1.bravo", re = r("^du\\b"),
                        astuceCle = "arbre.systeme1.1.astuce"),
                    Etape("arbre.systeme1.2.dit", "uptime",
                        "arbre.systeme1.2.bravo", re = r("^uptime\\b")),
                )),
                Lecon("arbre.systeme2.titre", "Détective", 1, listOf(
                    Etape("arbre.systeme2.0.dit", "uname -a",
                        "arbre.systeme2.0.bravo",
                        re = r("^uname\\b")),
                    Etape("arbre.systeme2.1.dit", "getprop ro.product.model",
                        "arbre.systeme2.1.bravo", re = r("^getprop\\b")),
                )),
            )),
            "tuyaux" to Branche("tuyaux", "arbre.tuyaux.nom", "🔧", "Endurance", "arbre.tuyaux.desc", listOf(
                Lecon("arbre.tuyaux0.titre", "Plombier", 1, listOf(
                    Etape("arbre.tuyaux0.0.dit", "ls | wc -l",
                        "arbre.tuyaux0.0.bravo", re = r("\\|\\s*wc\\b"),
                        astuceCle = "arbre.tuyaux0.0.astuce"),
                    // C3 : la liste de courses se fait dans la bibliothèque (« 📁 » sur chaque étape) ; un dressage qui
                    // emmène l'enfant ailleurs ne valide plus les étapes dans un autre lieu
                    Etape("arbre.tuyaux0.1.dit", "echo banane > courses.txt",
                        "arbre.tuyaux0.1.bravo",
                        fs = { File(it.terrain, COURSES).isFile }, ou = BIBLIO),
                    Etape("arbre.tuyaux0.2.dit", "echo pomme >> courses.txt",
                        "arbre.tuyaux0.2.bravo",
                        re = r("pomme.*>>\\s*courses"), ou = BIBLIO),
                    Etape("arbre.tuyaux0.3.dit", "echo cerise >> courses.txt",
                        "arbre.tuyaux0.3.bravo", re = r("cerise.*>>\\s*courses"), ou = BIBLIO),
                    Etape("arbre.tuyaux0.4.dit", "sort courses.txt",
                        "arbre.tuyaux0.4.bravo", re = r("^sort\\b"), ou = BIBLIO),
                )),
                Lecon("arbre.tuyaux1.titre", "Tamiseur", 1, listOf(
                    Etape("arbre.tuyaux1.0.dit", "cat courses.txt | grep pomme",
                        "arbre.tuyaux1.0.bravo",
                        re = r("\\|\\s*grep\\b"), ou = BIBLIO),
                    Etape("arbre.tuyaux1.1.dit", "sort courses.txt > triee.txt",
                        "arbre.tuyaux1.1.bravo", fs = { File(it.terrain, "$BIBLIO/triee.txt").isFile }, ou = BIBLIO),
                    Etape("arbre.tuyaux1.2.dit", "cat triee.txt",
                        "arbre.tuyaux1.2.bravo",
                        re = r("^cat\\b.*triee"), ou = BIBLIO),
                )),
            )),
            "scripts" to Branche("scripts", "branche.Scripts", "🧪", "Intelligence", "lec.scripts.desc", listOf(
                Lecon("lec.scripts0.titre", "Cuistot", 1, listOf(
                    Etape("arbre.scripts0.0.dit", "echo 'echo \"Miam !\"' > miam.sh",
                        "lec.scripts0.0.bravo", fs = { trouve(it, "miam.sh") != null }),
                    Etape("arbre.scripts0.1.dit", "cat miam.sh",
                        "arbre.scripts0.1.bravo", re = r("^cat\\b.*miam")),
                    Etape("lec.scripts0.1.dit", "sh miam.sh",
                        "arbre.scripts0.2.bravo",
                        re = r("^sh\\s+\\S*miam")),
                )),
                Lecon("lec.scripts1.titre", "Inventeur", 1, listOf(
                    Etape("arbre.scripts1.0.dit", "echo 'miam() { echo \"Miam !\"; }' >> ~/.tgrc",
                        "arbre.scripts1.0.bravo",
                        // C4 : `~/tgrc` (sans le point) n'est pas le fichier chargé par le shell : la fonction doit
                        // vraiment arriver dans ~/.tgrc
                        re = r("miam\\s*\\(\\).*>>\\s*(~/|\\\$HOME/|\\\$\\{HOME\\}/|/home/explorateur/)\\.tgrc(\\s|$|;|&)"),
                        fs = { tgrcMiam(it) }),
                    Etape("lec.scripts1.2.dit", "miam",
                        "arbre.scripts1.1.bravo",
                        re = r("^miam\\s*$")),
                )),
                Lecon("arbre.scripts2.titre", "Créateur", 1, listOf(
                    Etape("arbre.scripts2.0.dit", "for i in 1 2 3; do echo \"Miam \$i\"; done",
                        "arbre.scripts2.0.bravo", re = r("^for\\b")),
                    Etape("arbre.scripts2.1.dit", "if [ -f miam.sh ]; then echo oui; else echo non; fi",
                        "arbre.scripts2.1.bravo", re = r("^if\\b"),
                        astuceCle = "arbre.scripts2.1.astuce"),
                )),
            )),
            "createur" to Branche("createur", "arbre.createur.nom", "🎮", "Intelligence", "arbre.createur.desc", listOf(
                Lecon("arbre.createur0.titre", "Apprenti", 1, listOf(
                    Etape("arbre.createur0.0.dit", "doom",
                        "arbre.createur0.0.bravo",
                        fs = { File(dossierJeu, "carte.txt").isFile }),
                    Etape("arbre.createur0.1.dit", "cd ~/terrain_terminagotchi/jeu",
                        "arbre.createur0.1.bravo",
                        re = r("^cd\\s+.*jeu\\s*$")),
                    Etape("arbre.createur0.2.dit", "cat carte.txt",
                        "arbre.createur0.2.bravo",
                        re = r("^cat\\b.*carte"), ou = JEU),
                )),
                Lecon("arbre.createur1.titre", "Architecte", 1, listOf(
                    // v3 (C5) : le lieu « jeu » : tapée ailleurs (un dressage emmène dans un repaire), `edite carte.txt`
                    // ouvrirait un fichier vide et l'étape ne passerait jamais
                    Etape("arbre.createur1.0.dit", "edite carte.txt",
                        "arbre.createur1.0.bravo",
                        fs = { Doom.carteModifiee(dossierJeu) }, ou = JEU),
                    Etape("arbre.createur1.1.dit", "doom",
                        "arbre.createur1.1.bravo",
                        re = r("^doom\\b")),
                )),
                Lecon("arbre.createur2.titre", "Ingénieur", 1, listOf(
                    Etape("arbre.createur2.0.dit", "edite reglages.txt",
                        "arbre.createur2.0.bravo",
                        fs = { Doom.reglagesModifies(dossierJeu) }, ou = JEU),
                    Etape("arbre.createur2.1.dit", "doom",
                        "arbre.createur2.1.bravo",
                        re = r("^doom\\b")),
                )),
            )),
        )
    }
}
