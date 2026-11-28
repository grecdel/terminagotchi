package fr.terminagotchi

/**
 * Exemples prêts à taper, et aide quand il manque quelque chose après une commande
 * (portage de pc/tg/exemples.py : mêmes exemples, mêmes règles, mêmes textes « lex.ex* » et « aide.manque.* »).
 *
 * 1) Le lexique montre, sous chaque commande qui a besoin de quelque chose après elle, un exemple prêt à
 *    taper : « ↳ exemple : mkdir cabane ». Les exemples se tapent depuis le terrain de jeu
 *    (~/terrain_terminagotchi) et n'utilisent que ce qui y existe (nid/, nid/repas.txt écrit pendant la
 *    leçon « J'inspecte ») ou ce qu'un exemple précédent du lexique crée (mkdir cabane, touch lettre.txt,
 *    cp … copie.txt). tests/jvm/RetoursEnfants.kt les lance tous pour de vrai.
 *
 * 2) Quand l'enfant tape une commande connue sans ce qu'il lui faut (mkdir tout seul, cp avec un seul nom…),
 *    la créature dit dans une bulle ce qui manque et la commande corrigée à taper. Si la leçon en cours
 *    demande justement cette commande, c'est la commande de la leçon qui est proposée (mkdir nid).
 *    Le terminal passe par Shell.kt : on voit aussi la sortie (« missing operand », « usage: »…), ce qui
 *    attrape les cas que la ligne seule ne montre pas. Une commande absente du téléphone (« not found »)
 *    ne reçoit pas d'aide : le terminal dit déjà qu'il ne la connaît pas.
 */
object Exemples {
    /** {commande du lexique : exemple} */
    val LEXIQUE: Map<String, String> = mapOf(
        "cd" to "cd nid · cd .. · cd ~",
        "mkdir" to "mkdir cabane",
        "touch" to "touch lettre.txt",
        "echo" to "echo coucou > mot.txt",
        "cp" to "cp nid/repas.txt copie.txt",
        "mv" to "mv copie.txt nid/",
        "rm" to "rm lettre.txt",
        "rmdir" to "rmdir cabane",
        "chmod" to "chmod 444 nid/repas.txt",
        "rev" to "rev nid/repas.txt",
        "cat" to "cat nid/repas.txt",
        "head" to "head -n 3 nid/repas.txt",
        "tail" to "tail -n 3 nid/repas.txt",
        "grep" to "grep pomme nid/repas.txt",
        "find" to "find . -name \"*.txt\"",
        "wc" to "wc nid/repas.txt",
        "sort" to "sort nid/repas.txt",
        "stat" to "stat nid/repas.txt",
        "du" to "du -sh nid",
        "ping" to "ping -c 3 example.com",
        // le téléphone
        "ouvre" to "ouvre whatsapp",
        "web" to "web wikipedia.org",
        "carte" to "carte tour eiffel",
        "appelle" to "appelle 0612345678",
        "sms" to "sms 0612345678 {salut}",
        "partage" to "partage {salut}",
        "lampe" to "lampe on",
        "vibre" to "vibre 500",
        "dis" to "dis {salut}",
        "reglages" to "reglages wifi",
        // la créature et les jeux
        "joue" to "joue pierre",
        "devine" to "devine 10",
        "renomme" to "renomme Pixel",
        "cherche" to "cherche grep",
        "equipe" to "equipe epee_rouillee",
        "bois" to "bois potion_de_soin",
        "drapeau" to "drapeau TG{…}",
        "indice" to "indice 1",
        "edite" to "edite notes.txt",
        "langue" to "langue en",
        "notifs" to "notifs on",
        "notif" to "notif on",
        "site" to "site bestiaire",
        "bestiaire" to "bestiaire Glitchou",
        "anime" to "anime abyssor attaque",
        "aile" to "aile grenier",
        "explique" to "explique rm",
    )

    /** Les mots à remplacer d'un exemple, dans la langue courante (NUMÉRO, NOM@ADRESSE, coucou). */
    fun remplir(ex: String): String =
        ex.replace("{numero}", t("lex.ex.numero")).replace("{ssh}", t("lex.ex.ssh")).replace("{salut}", t("lex.ex.salut"))

    /** L'exemple prêt à taper d'une commande du lexique, ou null (commandes du PC : 🔒 ; « carte » seul = le plan). */
    fun lexique(m: Mot): String? {
        if (m.pc || (m.cmd == "carte" && m.sectionCle == "lex.ch.maison")) return null
        return LEXIQUE[m.cmd]?.let { remplir(it) }
    }

    // ---------------------------------------------------------------- « il manque quelque chose »
    /** cle : le texte « aide.manque.<cle> » ; besoin : noms nécessaires après la commande ;
     *  avecValeur : les options suivies d'une valeur (head -n 3 : « 3 » n'est pas un nom de fichier). */
    class Regle(val cle: String, val ex: String, val besoin: Int, val avecValeur: Set<String> = emptySet())

    val REGLES: Map<String, Regle> = mapOf(
        "mkdir" to Regle("mkdir", "mkdir cabane", 1),
        "rmdir" to Regle("rmdir", "rmdir cabane", 1),
        "touch" to Regle("touch", "touch lettre.txt", 1),
        "cat" to Regle("lire", "cat nid/repas.txt", 1),
        "less" to Regle("lire", "less nid/repas.txt", 1),
        "head" to Regle("lire", "head -n 3 nid/repas.txt", 1, setOf("-n", "-c")),
        "tail" to Regle("lire", "tail -n 3 nid/repas.txt", 1, setOf("-n", "-c")),
        "wc" to Regle("lire", "wc nid/repas.txt", 1),
        "sort" to Regle("lire", "sort nid/repas.txt", 1, setOf("-k", "-t", "-o")),
        "rev" to Regle("lire", "rev nid/repas.txt", 1),
        "stat" to Regle("lire", "stat nid/repas.txt", 1, setOf("-c")),
        "cp" to Regle("deux", "cp nid/repas.txt copie.txt", 2),
        "mv" to Regle("deux", "mv copie.txt nid/", 2),
        "rm" to Regle("rm", "rm lettre.txt", 1),
        "grep" to Regle("grep", "grep pomme nid/repas.txt", 2, setOf("-e", "-m", "-A", "-B", "-C")),
        "chmod" to Regle("chmod", "chmod 444 nid/repas.txt", 2),
        "find" to Regle("find", "find . -name \"*.txt\"", 1),
        "kill" to Regle("kill", "kill {numero}", 1, setOf("-s")),
        "ping" to Regle("reseau", "ping -c 3 example.com", 1, setOf("-c", "-i", "-W", "-s", "-w")),
        "curl" to Regle("reseau", "curl -I https://example.com", 1, setOf("-o", "-H", "-X", "-d", "-A", "-u", "-e")),
        "nslookup" to Regle("reseau", "nslookup example.com", 1),
        "ssh" to Regle("ssh", "ssh {ssh}", 1, setOf("-p", "-i", "-l")),
        "nano" to Regle("nano", "nano lettre.txt", 1),
        "git" to Regle("git", "git init carnet", 1, setOf("-C", "-c")),
    )

    /** tuyau, redirection, plusieurs commandes : on ne devine pas */
    private val SPECIAL = Regex("[|<>;&`\$()]")
    private val SANS_NOM = setOf("-name", "-iname", "-type")
    private val SORTIES = listOf("missing operand", "missing file operand", "missing destination", "usage:",
        "requires an argument", "need 1 argument", "needs 1 argument", "need 2 arguments", "needs 2 arguments")

    /** La commande si la ligne est une commande connue SANS ce qu'il lui faut après elle, sinon null. */
    fun manque(ligne: String): String? {
        if (ligne.isBlank() || SPECIAL.containsMatchIn(ligne)) return null
        val mots = ligne.trim().split(Regex("\\s+"))
        val cmd = Regles.premierMot(ligne)
        val r = REGLES[cmd] ?: return null
        if (cmd == "find") return if (mots.size == 1 || mots.last() in SANS_NOM) cmd else null
        var saute = false
        var noms = 0
        for (m in mots.drop(1)) {
            if (saute) { saute = false; continue }
            if (m.startsWith("-") && m.length > 1) { saute = m in r.avecValeur; continue }
            noms++
        }
        return if (noms < r.besoin) cmd else null
    }

    /** La sortie de la commande dit qu'il manque quelque chose (« missing operand », « usage: »…). */
    fun sortieManque(sortie: String): Boolean {
        val s = sortie.lowercase()
        return SORTIES.any { it in s }
    }

    /** La commande de la leçon en cours si elle commence par la même commande (mkdir nid plutôt que mkdir cabane). */
    private fun exempleLecon(jeu: Jeu, cmd: String): String? {
        val c = Histoire.leconCourante(jeu) ?: return null
        val modele = c.etapes.getOrNull(jeu.etape)?.cmd?.split("    ")?.get(0)?.trim() ?: return null
        return if (modele.isNotEmpty() && Regles.premierMot(modele) == cmd && manque(modele) == null) modele else null
    }

    /** Le texte de la bulle d'aide pour cette ligne (et sa sortie, si on la connaît), ou null. */
    fun texte(jeu: Jeu, ligne: String, sortie: String? = null): String? {
        var cmd = manque(ligne)
        if (sortie != null) {
            if ("not found" in sortie.lowercase()) return null          // absente du téléphone : déjà expliqué
            if (cmd == null && sortieManque(sortie) && !SPECIAL.containsMatchIn(ligne))
                cmd = Regles.premierMot(ligne).takeIf { it in REGLES }
        }
        val r = REGLES[cmd ?: return null] ?: return null
        val ex = remplir(exempleLecon(jeu, cmd) ?: r.ex)
        val valeurs = Mots.termes(Mots.palier(jeu)) + mapOf("cmd" to Regles.premierMot(ligne), "ex" to ex)
        return t("aide.manque." + r.cle, *valeurs.toList().toTypedArray())
    }

    /** Après une commande du terminal : la bulle (et la ligne du journal) avec la commande à taper. Renvoie le texte. */
    fun apres(jeu: Jeu, ligne: String, sortie: String? = null): String? {
        if (Regles.estColle(ligne)) return null
        val x = texte(jeu, ligne, sortie) ?: return null
        jeu.dire(x, 14)
        jeu.log(x)
        jeu.animer("confus")
        return x
    }
}
