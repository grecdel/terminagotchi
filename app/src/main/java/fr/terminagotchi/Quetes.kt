package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.math.BigInteger
import java.security.MessageDigest

/**
 * Le hasard de Python (random.Random(graine texte)) recopié à l'identique : Mersenne Twister, graine
 * « version 2 » (le texte + son SHA-512), choice, randint, randrange, shuffle, sample. Les quêtes générées,
 * les griffures d'Abyssor… sont donc les mêmes que sur PC pour une même graine (partie:naissance:sel).
 */
class PyHasard(graine: String) {
    private val mt = IntArray(624)
    private var mti = 625

    init {
        val o = graine.toByteArray(Charsets.UTF_8)
        var x = BigInteger(1, o + MessageDigest.getInstance("SHA-512").digest(o))
        val cle = mutableListOf<Int>()
        val masque = BigInteger.valueOf(0xFFFFFFFFL)
        if (x.signum() == 0) cle.add(0)
        while (x.signum() > 0) { cle.add(x.and(masque).toLong().toInt()); x = x.shiftRight(32) }
        parTableau(cle)
    }

    private fun initGenrand(s: Int) {
        mt[0] = s
        for (i in 1 until 624) mt[i] = 1812433253 * (mt[i - 1] xor (mt[i - 1] ushr 30)) + i
        mti = 624
    }

    private fun parTableau(cle: List<Int>) {
        initGenrand(19650218)
        var i = 1
        var j = 0
        var k = maxOf(624, cle.size)
        while (k > 0) {
            mt[i] = (mt[i] xor ((mt[i - 1] xor (mt[i - 1] ushr 30)) * 1664525)) + cle[j] + j
            i++; j++
            if (i >= 624) { mt[0] = mt[623]; i = 1 }
            if (j >= cle.size) j = 0
            k--
        }
        k = 623
        while (k > 0) {
            mt[i] = (mt[i] xor ((mt[i - 1] xor (mt[i - 1] ushr 30)) * 1566083941)) - i
            i++
            if (i >= 624) { mt[0] = mt[623]; i = 1 }
            k--
        }
        mt[0] = 0x80000000.toInt()
    }

    private fun suivant(): Int {
        if (mti >= 624) {
            for (kk in 0 until 624) {
                val y = (mt[kk] and 0x80000000.toInt()) or (mt[(kk + 1) % 624] and 0x7fffffff)
                mt[kk] = mt[(kk + 397) % 624] xor (y ushr 1) xor (if (y and 1 != 0) 0x9908b0df.toInt() else 0)
            }
            mti = 0
        }
        var y = mt[mti++]
        y = y xor (y ushr 11)
        y = y xor ((y shl 7) and 0x9d2c5680.toInt())
        y = y xor ((y shl 15) and 0xefc60000.toInt())
        y = y xor (y ushr 18)
        return y
    }

    /** getrandbits(k), k ≤ 32 */
    fun bits(k: Int): Long = if (k == 0) 0L else (suivant().toLong() and 0xFFFFFFFFL) ushr (32 - k)

    /** _randbelow(n) : un entier dans [0, n) */
    fun sous(n: Int): Int {
        val k = 32 - Integer.numberOfLeadingZeros(n)
        var r = bits(k)
        while (r >= n) r = bits(k)
        return r.toInt()
    }

    fun <T> choix(l: List<T>): T = l[sous(l.size)]
    fun randint(a: Int, b: Int): Int = a + sous(b - a + 1)
    fun randrange(n: Int): Int = sous(n)

    fun <T> melanger(l: MutableList<T>) {
        for (i in l.size - 1 downTo 1) {
            val j = sous(i + 1)
            val x = l[i]; l[i] = l[j]; l[j] = x
        }
    }

    fun <T> echantillon(pop: List<T>, k: Int): List<T> {
        val n = pop.size
        var taille = 21
        if (k > 5) taille += Math.pow(4.0, Math.ceil(Math.log(k * 3.0) / Math.log(4.0))).toInt()
        val res = ArrayList<T>()
        if (n <= taille) {
            val pool = pop.toMutableList()
            for (i in 0 until k) {
                val j = sous(n - i)
                res.add(pool[j])
                pool[j] = pool[n - i - 1]
            }
        } else {
            val pris = HashSet<Int>()
            for (i in 0 until k) {
                var j = sous(n)
                while (j in pris) j = sous(n)
                pris.add(j)
                res.add(pop[j])
            }
        }
        return res
    }
}

/**
 * Les quêtes secondaires (portage de pc/tg/quetes.py) : la maison est grande, il s'y passe plein de choses.
 *
 * Quatre sortes de quêtes écrites à la main (44, voir QUETES), posées dans les pièces quand leur porte s'ouvre :
 *   lettre    une lettre à lire (cat lettre_du_jardinier.txt) : la lire accepte la mini-quête ;
 *   habitant  un monstre habitant demande un service (cat habitant_mousseline.txt) ;
 *   cachette  une pièce secrète (dossier qui commence par un point) : y entrer (cd .nid_de_hibou) suffit ;
 *   sauvage   regarder les terres sauvages hors de la maison du jeu (cat /proc/version), en lecture seule.
 * Plus les quêtes GÉNÉRÉES (perdu, construire, copie, compter, protéger, mot secret) : le tableau des annonces
 * du vestibule en propose toujours 3, tirées d'une graine propre à la partie (même hasard que le PC) ;
 * et une QUÊTE DU JOUR (même graine + la date). La difficulté des quêtes générées suit le niveau.
 *
 * Sur le téléphone : la quête git (q37) n'existe pas ; les quêtes des terres sauvages regardent /proc
 * (pas de /etc/hostname ni de /etc/os-release sur Android) ; les textes qui changent sont les clés « qua.* »
 * (elles remplacent « qu.* », voir Histoire.cle).
 *
 * Règle d'or : une quête ne demande JAMAIS d'écrire ou de supprimer hors de ~/terrain_terminagotchi, et le jeu
 * n'écrit lui-même que dans le terrain.
 *
 * Sauvegarde : module « quetes » = {actives, finies, suivie, vu, gen, gen_n, offertes, jour, objets, titres,
 * titre, poses, souvenirs}.
 */
object Quetes {
    class Quete(
        val id: String, val piece: String, val sorte: String, val fichier: String, val but: List<List<Any>>,
        val xp: Int = 15, val objet: String? = null, val titre: String? = null,
        val pose: ((Jeu) -> Map<String, Any>)? = null, val android: Boolean = true,
    )

    const val LIRE = "^(cat|type|gc|get-content|less|more|head|tail|bat|nl)\\b"
    val MOTS_MAGIQUES = listOf("BLOUP", "ZORGLUB", "PLOUF", "SPLASH", "GLOUBI", "SCHLOUK")
    val TUYAUX = listOf("rouge", "bleu", "vert")

    private fun T(jeu: Jeu) = jeu.terrain

    fun rnd(jeu: Jeu, sel: String) = PyHasard(Histoire.graine(jeu) + ":" + sel)

    private fun compte(jeu: Jeu, rel: String, motif: String): Int {
        val r = Regex(motif)
        return File(T(jeu), rel).listFiles()?.count { it.isFile && r.matches(it.name) } ?: 0
    }

    private fun lire(jeu: Jeu, rel: String): String? = Histoire.lire(jeu, rel)

    private fun lignes(jeu: Jeu, rel: String, mots: Boolean = false): Int {
        val x = lire(jeu, rel) ?: return -1
        return if (mots) x.split(Regex("\\s+")).count { it.isNotEmpty() } else x.split("\n").count { it.isNotBlank() }
    }

    // ---------------------------------------------------------------- ce que posent certaines quêtes
    private val poseJournal: (Jeu) -> Map<String, Any> = { mapOf("nid/journal_intime.txt" to t("qu.q10.page")) }
    private val poseChaussettes: (Jeu) -> Map<String, Any> = {
        linkedMapOf("grenier/panier/.vide" to "", "grenier/fouillis/malle/chaussette_rouge.txt" to "🧦",
            "grenier/fouillis/carton/chaussette_verte.txt" to "🧦", "grenier/vieux_coffre/.fond/chaussette_bleue.txt" to "🧦")
    }
    private val poseFeuilles: (Jeu) -> Map<String, Any> = { j ->
        val n = rnd(j, "feuilles").randint(5, 9)
        (0 until n).associate { "grenier/lianes/feuille_${it + 1}.txt" to "🍃" }
    }
    private val posePhotos: (Jeu) -> Map<String, Any> = {
        val m = linkedMapOf<String, Any>("grenier/album/.vide" to "")
        for (x in listOf("plage", "foret", "gateau", "chat")) m["grenier/fouillis/photo_$x.txt"] = "📷 $x"
        m
    }
    private val poseGateau: (Jeu) -> Map<String, Any> = { mapOf("cave/tonneau/.fond/gateau.txt" to "🍰") }
    private val poseInventaire: (Jeu) -> Map<String, Any> = { j ->
        val r = rnd(j, "inventaire")
        val choses = t("qu.q18.choses").split(", ").toMutableList()
        r.melanger(choses)
        mapOf("cave/inventaire.txt" to choses.take(r.randint(6, minOf(12, choses.size))).joinToString("\n"))
    }
    private val poseGlouglou: (Jeu) -> Map<String, Any> = { j ->
        val mot = rnd(j, "mot").choix(MOTS_MAGIQUES)
        mapOf("bibliotheque/etagere_b/journal_de_bord.txt" to t("qu.q20.journal") + "\nMOT MAGIQUE : $mot\n" + t("qu.q20.journal_fin"))
    }
    private val poseTitres: (Jeu) -> Map<String, Any> = { j ->
        val titres = t("qu.q21.titres").split(", ").toMutableList()
        rnd(j, "titres").melanger(titres)
        mapOf("bibliotheque/titres.txt" to titres.joinToString("\n"))
    }
    private val poseGrandLivre: (Jeu) -> Map<String, Any> = {
        mapOf("bibliotheque/grand_livre.txt" to (0 until 40).joinToString("\n") { t("qu.q23.page", "n" to it + 1) })
    }
    private val poseTuyaux: (Jeu) -> Map<String, Any> = { j ->
        val gros = rnd(j, "tuyau").choix(TUYAUX)
        TUYAUX.associate { "salle_des_machines/tuyaux/$it/bouchon.bin" to ByteArray(if (it == gros) 90000 else 6000) }
    }
    private val poseConte: (Jeu) -> Map<String, Any> = {
        mapOf("dortoir/conte_du_soir.txt" to (0 until 30).joinToString("\n\n") { t("qu.q32.conte", "n" to it + 1) })
    }
    private val poseMachine: (Jeu) -> Map<String, Any> = { mapOf("atelier/machine.sh" to "echo \"Vrrr… clic !\"") }

    /** Le nom de l'utilisateur (whoami) : la quête du veilleur. */
    @Volatile private var moi: String? = null
    fun utilisateur(): String {
        moi?.let { return it }
        val u = try {
            val sh = if (File("/system/bin/sh").exists()) "/system/bin/sh" else "sh"
            val p = ProcessBuilder(sh, "-c", "whoami").redirectErrorStream(true).start()
            val s = p.inputStream.bufferedReader().readText().trim()
            p.waitFor()
            s.lines().firstOrNull()?.trim().orEmpty()
        } catch (e: Exception) { "" }
        val r = u.ifEmpty { System.getProperty("user.name") ?: "?" }
        moi = r
        return r
    }

    private fun q(id: String, piece: String, sorte: String, fichier: String, but: List<List<Any>>, xp: Int = 15, objet: String? = null,
                  titre: String? = null, pose: ((Jeu) -> Map<String, Any>)? = null, android: Boolean = true) =
        Quete(id, piece, sorte, fichier, but, xp, objet, titre, pose, android)

    private val compterFeuilles: (Jeu) -> Any = { j -> compte(j, "grenier/lianes", "feuille_.*") }
    private val compterInventaire: (Jeu) -> Any = { j -> lignes(j, "cave/inventaire.txt") }
    private val motGlouglou: (Jeu) -> Any = { j -> rnd(j, "mot").choix(MOTS_MAGIQUES) }
    private val grosTuyau: (Jeu) -> Any = { j -> rnd(j, "tuyau").choix(TUYAUX) }
    private val compterMots: (Jeu) -> Any = { j -> lignes(j, "coeur/message_brouille.txt", mots = true) }
    private val nomVeilleur: (Jeu) -> Any = { utilisateur() }
    private const val SAUVAGE = "^(cat|less|more|head|tail|type)\\s+"

    // ---------------------------------------------------------------- les 44 quêtes écrites à la main
    val QUETES: List<Quete> = listOf(
        // le vestibule
        q("q01", "vestibule", "lettre", "lettre_de_bienvenue.txt", listOf(listOf("visite", "vestibule/.placard_secret")), 15, "paillasson"),
        q("q02", "vestibule", "cachette", ".placard_secret", listOf(), 10, titre = "fouineur"),
        q("q03", "vestibule", "lettre", "mot_du_facteur.txt", listOf(listOf("dossier", "vestibule/boite_aux_lettres")), 15, "timbre"),
        q("q04", "vestibule", "habitant", "habitant_pantoufle.txt", listOf(listOf("fichier", "vestibule/tapis.txt")), 15, "tapis"),
        q("q05", "vestibule", "lettre", "horloge_du_hall.txt", listOf(listOf("plein", "vestibule/heure.txt")), 15, "horloge"),
        // le nid
        q("q06", "nid", "lettre", "liste_de_courses.txt", listOf(listOf("lignes", "nid/courses.txt", 3)), 20, "panier"),
        q("q07", "nid", "habitant", "habitant_grignote.txt", listOf(listOf("fichier", "nid/coussin.txt")), 15, "bougie"),
        q("q08", "nid", "cachette", ".sous_le_lit", listOf(), 10, "doudou"),
        q("q09", "nid", "lettre", "recette_de_mamie.txt", listOf(listOf("fichier", "nid/recette_copie.txt")), 15, "tablier"),
        q("q10", "nid", "lettre", "page_du_journal.txt", listOf(listOf("lignes", "nid/journal_intime.txt", 3)), 15, titre = "ecrivain",
            pose = poseJournal),
        // le grenier des Sylvestres
        q("q11", "grenier", "habitant", "habitant_mousseline.txt", listOf(listOf("nb", "grenier/panier", "chaussette_.*", 3)), 30,
            "pelote", pose = poseChaussettes),
        q("q12", "grenier", "cachette", ".nid_de_hibou", listOf(), 10, "plume"),
        q("q13", "grenier", "lettre", "lettre_du_jardinier.txt", listOf(listOf("reponse", "grenier/reponse_jardinier.txt", compterFeuilles)), 25,
            "arrosoir", pose = poseFeuilles),
        q("q14", "grenier", "habitant", "habitant_ronce.txt", listOf(listOf("nb", "grenier/album", "photo_.*", 4)), 25, "cadre_photo",
            pose = posePhotos),
        // la cave des Démons
        q("q15", "cave", "lettre", "avis_de_vol.txt", listOf(listOf("fichier", "nid/gateau.txt")), 25, "gateau", pose = poseGateau),
        q("q16", "cave", "habitant", "habitant_braise.txt", listOf(listOf("protege", "cave/coffre.txt")), 25, "bougie_rouge"),
        q("q17", "cave", "cachette", ".trappe", listOf(), 10, "cristal"),
        q("q18", "cave", "lettre", "inventaire_a_verifier.txt", listOf(listOf("reponse", "cave/reponse_inventaire.txt", compterInventaire)), 25,
            "sablier", pose = poseInventaire),
        q("q19", "cave", "sauvage", "plan_des_fondations.txt", listOf(listOf("cmd", "^(ls|dir|gci|get-childitem)\\s+([a-z]:)?[\\\\/]\\s*$")),
            20, titre = "explorateur"),
        // la bibliothèque des Abyssaux
        q("q20", "bibliotheque", "habitant", "habitant_glouglou.txt", listOf(listOf("contient", "bibliotheque/mot_magique.txt", motGlouglou)), 25,
            "coquillage", pose = poseGlouglou),
        q("q21", "bibliotheque", "lettre", "fiche_de_pret.txt", listOf(listOf("trie", "bibliotheque/titres_ranges.txt", "bibliotheque/titres.txt")),
            25, "lampe_de_lecture", pose = poseTitres),
        q("q22", "bibliotheque", "cachette", ".salle_des_archives", listOf(), 10, "parchemin"),
        q("q23", "bibliotheque", "lettre", "livre_ouvert.txt", listOf(listOf("cmd", "^(head|get-content|gc)\\b.*grand_livre")), 15, "loupe",
            pose = poseGrandLivre),
        // la salle des machines des Élémentaires
        q("q24", "salle_des_machines", "habitant", "habitant_etincelle.txt",
            listOf(listOf("cmd_ici", "^(df|get-psdrive|gdr)\\b", "salle_des_machines")), 15, "ampoule"),
        q("q25", "salle_des_machines", "lettre", "note_du_chauffagiste.txt",
            listOf(listOf("contient", "salle_des_machines/reponse_tuyau.txt", grosTuyau)), 25, "cle_a_molette", pose = poseTuyaux),
        q("q26", "salle_des_machines", "cachette", ".chaufferie", listOf(), 10, "lanterne"),
        q("q27", "salle_des_machines", "habitant", "habitant_givre.txt", listOf(listOf("fichier", "salle_des_machines/frigo/glacon.txt")),
            15, "boule_a_neige"),
        // (téléphone : pas de /etc/os-release, la plaque est /proc/version)
        q("q28", "salle_des_machines", "sauvage", "plaque_du_constructeur.txt", listOf(listOf("cmd", SAUVAGE + "/proc/version")),
            20, titre = "explorateur"),
        // le dortoir des Morts-vivants
        q("q29", "dortoir", "habitant", "habitant_berceuse.txt",
            listOf(listOf("cmd", "^(ps|get-process|gps|tasklist)\\b.*\\|\\s*(wc|measure-object|measure)")), 20, "attrape_reves"),
        q("q30", "dortoir", "lettre", "journal_du_veilleur.txt", listOf(listOf("contient", "dortoir/veilleur.txt", nomVeilleur)), 20, "bonnet_de_nuit"),
        q("q31", "dortoir", "cachette", ".sous_les_draps", listOf(), 10, "etoile_filante"),
        // (téléphone : pas de less, on lit le conte avec cat)
        q("q32", "dortoir", "lettre", "histoire_du_soir.txt", listOf(listOf("cmd", "^(less|more|cat|head|tail)\\b.*conte")), 15, "livre_de_contes",
            pose = poseConte),
        q("q33", "dortoir", "lettre", "reveil_matin.txt", listOf(listOf("cmd", "^(uptime|get-uptime)\\b")), 15, "reveil"),
        // l'atelier des Constructs
        q("q34", "atelier", "habitant", "habitant_boulon.txt",
            listOf(listOf("fichier", "atelier/bonjour.sh"), listOf("cmd", "^(sh|bash|zsh|\\./|powershell|pwsh|\\.\\\\).*bonjour")), 30, "tournevis"),
        q("q35", "atelier", "lettre", "plan_secret.txt", listOf(listOf("exec", "atelier/machine.sh")), 20, "engrenage", pose = poseMachine),
        q("q36", "atelier", "cachette", ".etabli_cache", listOf(), 10, "boulon_d_or"),
        q("q37", "atelier", "lettre", "carnet_de_bord.txt", listOf(listOf("commits", 2)), 30, "appareil_photo", android = false),
        // la tour des Célestes
        q("q38", "tour", "habitant", "habitant_nuage.txt", listOf(listOf("cmd", "^ping\\b.*(127\\.0\\.0\\.1|localhost)")), 20, "cerf_volant"),
        // (téléphone : pas de /etc/hostname, le nom est dans /proc/sys/kernel/hostname)
        q("q39", "tour", "sauvage", "carte_des_terres_sauvages.txt", listOf(listOf("cmd", SAUVAGE + "/proc/sys/kernel/hostname")), 20,
            titre = "explorateur"),
        q("q40", "tour", "cachette", ".observatoire", listOf(), 10, "longue_vue"),
        q("q41", "tour", "lettre", "telegramme.txt", listOf(listOf("ip", "tour/adresse.txt")), 25, "boussole"),
        // le cœur de la maison
        q("q42", "coeur", "habitant", "habitant_bizarre.txt", listOf(listOf("contient", "coeur/envers.txt", "ihctoganimret")), 25, "miroir"),
        q("q43", "coeur", "cachette", ".chambre_des_echos", listOf(), 10, "coquille"),
        q("q44", "coeur", "lettre", "dernier_message.txt", listOf(listOf("reponse", "coeur/reponse_mots.txt", compterMots)), 25,
            titre = "detective"),
    )
    val PAR_ID = QUETES.associateBy { it.id }

    // ---------------------------------------------------------------- les quêtes générées
    val OBJETS_PERDUS = listOf("bille", "toupie", "crayon", "gomme", "sifflet", "ballon", "bouton", "petite_cle")
    val COINS = listOf("sous_le_tapis", "derriere_le_rideau", "dans_un_tiroir", "sous_une_planche")
    val CONSTRUCTIONS = listOf("cabane", "tipi", "chateau_fort", "igloo", "grotte", "tente")
    val MODELES_FACILES = listOf("perdu", "construire", "copie")
    val MODELES_MOYENS = listOf("compter", "proteger")
    val MODELES_DURS = listOf("mot")
    const val NB_ANNONCES = 3

    /** La difficulté suit le niveau : de plus en plus de sortes de quêtes, et plus cachées. */
    fun modeles(niveau: Int): List<String> {
        val m = MODELES_FACILES.toMutableList()
        if (niveau >= 7) m += MODELES_MOYENS
        if (niveau >= 12) m += MODELES_DURS
        return m
    }

    private fun piecesLibres(jeu: Jeu) =
        Maison.PIECES.filter { it != "nid" && Histoire.pieceOuverte(jeu, it) && File(T(jeu), it).isDirectory }

    /** Une quête générée : {"m": modèle, "p": paramètres} et ce qu'elle pose ({fichier: contenu}). */
    fun generer(jeu: Jeu, sel: String, niveau: Int): Pair<JSONObject, Map<String, Any>> {
        val r = PyHasard(Histoire.graine(jeu) + ":gen:" + sel)
        val pieces = piecesLibres(jeu).ifEmpty { listOf("vestibule") }
        val m = r.choix(modeles(niveau))
        val piece = r.choix(pieces)
        val k = sel.replace(Regex("[^\\p{L}\\p{N}_]"), "").takeLast(6)
        val p = JSONObject().put("piece", piece)
        val pose = linkedMapOf<String, Any>()
        when (m) {
            "perdu" -> {
                val obj = r.choix(OBJETS_PERDUS)
                var coin = r.choix(COINS)
                if (niveau >= 10) coin = ".$coin"                      // plus dur : un coin caché (ls -a, find)
                p.put("objet", obj).put("fichier", "$obj.txt")
                pose["$piece/$coin/$obj.txt"] = "✨ $obj"
            }
            "construire" -> p.put("nom", r.choix(CONSTRUCTIONS) + "_" + k.takeLast(2))
            "copie" -> {
                val obj = r.choix(OBJETS_PERDUS)
                p.put("fichier", "recette_$obj.txt")
                pose["$piece/recette_$obj.txt"] = "1. …\n2. …\n3. ✨"
            }
            "compter" -> {
                val n = r.randint(4, if (niveau < 10) 9 else 15)
                p.put("tas", "tas_$k").put("reponse", "reponse_$k.txt")
                for (i in 0 until n) pose["$piece/tas_$k/caillou_${i + 1}.txt"] = "🪨"
            }
            "proteger" -> {
                p.put("fichier", "tresor_$k.txt")
                pose["$piece/tresor_$k.txt"] = "💎"
            }
            "mot" -> {
                val mot = r.choix(MOTS_MAGIQUES)
                p.put("tas", "pile_$k").put("reponse", "mot_$k.txt").put("mot", mot)
                val n = r.randint(5, 9)
                val bon = r.randrange(n)
                for (i in 0 until n) pose["$piece/pile_$k/papier_${i + 1}.txt"] = if (i == bon) "MOTSECRET : $mot" else "…"
            }
        }
        return JSONObject().put("m", m).put("p", p) to pose
    }

    private fun butGen(g: JSONObject): List<List<Any>> {
        val p = g.getJSONObject("p")
        fun s(k: String) = p.optString(k)
        return when (g.optString("m")) {
            "perdu" -> listOf(listOf("fichier", "nid/${s("fichier")}"))
            "construire" -> listOf(listOf("dossier", "${s("piece")}/${s("nom")}"))
            "copie" -> listOf(listOf("fichier", "nid/copies/${s("fichier")}"))
            "compter" -> {
                val rel = "${s("piece")}/${s("tas")}"
                listOf(listOf("reponse", "nid/${s("reponse")}", { j: Jeu -> compte(j, rel, "caillou_.*") }))
            }
            "proteger" -> listOf(listOf("protege", "${s("piece")}/${s("fichier")}"))
            "mot" -> listOf(listOf("contient", "nid/${s("reponse")}", s("mot")))
            else -> emptyList()
        }
    }

    // ---------------------------------------------------------------- l'état
    fun q(jeu: Jeu): JSONObject {
        val q = jeu.module("quetes")
        for (k in listOf("actives", "finies", "offertes", "objets", "titres", "poses", "souvenirs")) if (!q.has(k)) q.put(k, JSONArray())
        for (k in listOf("vu", "gen")) if (!q.has(k)) q.put(k, JSONObject())
        if (!q.has("gen_n")) q.put("gen_n", 0)
        return q
    }

    fun liste(q: JSONObject, k: String): MutableList<String> =
        q.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.optString(it) }.toMutableList() } ?: mutableListOf()
    private fun mettre(q: JSONObject, k: String, l: List<String>) { q.put(k, JSONArray(l)) }
    private fun ajouter(q: JSONObject, k: String, v: String) { val l = liste(q, k); if (v !in l) { l.add(v); mettre(q, k, l) } }
    private fun retirer(q: JSONObject, k: String, v: String) { val l = liste(q, k); if (l.remove(v)) mettre(q, k, l) }
    private fun suivie(q: JSONObject): String? = if (q.isNull("suivie")) null else q.optString("suivie").ifEmpty { null }
    private fun jourId(q: JSONObject): String? = q.optJSONObject("jour")?.optString("id")?.ifEmpty { null }

    /** La quête existe dans cette partie : sa pièce est ouverte (et le nid construit pour le nid). */
    private fun dispo(jeu: Jeu, quete: Quete): Boolean {
        if (!quete.android) return false
        val p = quete.piece
        if (p == "nid") return "nid0" in Histoire.faits(jeu) && File(T(jeu), "nid").isDirectory
        return Histoire.pieceOuverte(jeu, p) && File(T(jeu), p).isDirectory
    }

    /** Le texte d'une quête (écrite à la main ou générée), avec le jargon du palier. */
    fun texte(jeu: Jeu, qid: String, cle: String = "texte"): String {
        val q = q(jeu)
        val d = HashMap(Mots.termes(Mots.palier(jeu)))
        d["nom"] = jeu.nom
        val g = q.getJSONObject("gen").optJSONObject(qid)
        if (g != null) {
            val p = g.getJSONObject("p")
            for (k in p.keys()) d[k] = p.optString(k)
            if (p.has("piece")) { d["dossier_piece"] = p.optString("piece"); d["piece"] = Maison.nomPiece(p.optString("piece")) }
            if (p.has("objet")) d["objet"] = t("qu.objet." + p.optString("objet"))
            return Langue.remplir(Langue.modele(Histoire.cle("qu.gen.${g.optString("m")}.$cle")), d)
        }
        return Langue.remplir(Langue.modele(Histoire.cle("qu.$qid.$cle")), d)
    }

    fun titre(jeu: Jeu, qid: String) = texte(jeu, qid, "titre")

    private fun ecrire(jeu: Jeu, rel: String, contenu: Any) = Histoire.ecrire(jeu, rel, contenu, finLigne = (contenu as? String)?.isNotEmpty() == true)

    private fun existe(jeu: Jeu, rel: String) = File(T(jeu), rel).exists()

    /** Pose les lettres, habitants, cachettes et objets des quêtes dont la pièce vient de s'ouvrir (une fois). */
    fun poser(jeu: Jeu) {
        val q = q(jeu)
        for (quete in QUETES) {
            if (quete.id in liste(q, "poses") || !dispo(jeu, quete)) continue
            ajouter(q, "poses", quete.id)
            val p = quete.piece
            if (quete.sorte == "cachette") ecrire(jeu, "$p/${quete.fichier}/tresor.txt", texte(jeu, quete.id))
            else if (!existe(jeu, "$p/${quete.fichier}")) ecrire(jeu, "$p/${quete.fichier}", texte(jeu, quete.id))
            quete.pose?.invoke(jeu)?.forEach { (rel, c) -> if (!existe(jeu, rel)) ecrire(jeu, rel, c) }
        }
    }

    // ---------------------------------------------------------------- le tableau des annonces et la quête du jour
    private fun tableau(jeu: Jeu) {
        val q = q(jeu)
        val l = mutableListOf(t("qu.tableau.titre"), "")
        for ((i, gid) in liste(q, "offertes").withIndex()) {
            val etat = if (gid in liste(q, "finies")) " ✔" else if (gid in liste(q, "actives")) " ▶" else ""
            l.add("${i + 1}. ${titre(jeu, gid)}$etat")
            l.add("   " + texte(jeu, gid))
            l.add("")
        }
        l.add(t(Histoire.cle("qu.tableau.pied")))
        ecrire(jeu, "vestibule/tableau_des_annonces.txt", l.joinToString("\n"))
    }

    private fun nouvelleGen(jeu: Jeu, id: String? = null): String {
        val q = q(jeu)
        val gid = id ?: run { q.put("gen_n", q.optInt("gen_n") + 1); "g${q.optInt("gen_n")}" }
        val (g, pose) = generer(jeu, gid, jeu.niveau)
        for ((rel, c) in pose) if (!existe(jeu, rel)) ecrire(jeu, rel, c)
        q.getJSONObject("gen").put(gid, g)
        return gid
    }

    /** Le vestibule propose toujours NB_ANNONCES quêtes générées (dès qu'il existe). */
    fun annonces(jeu: Jeu) {
        if (!Histoire.pieceOuverte(jeu, "vestibule") || !File(T(jeu), "vestibule").isDirectory) return
        val q = q(jeu)
        var change = false
        val finies = liste(q, "finies")
        val off = liste(q, "offertes").filter { it !in finies }.toMutableList()
        mettre(q, "offertes", off)
        while (off.size < NB_ANNONCES) {
            off.add(nouvelleGen(jeu))
            mettre(q, "offertes", off)
            change = true
        }
        if (change || !existe(jeu, "vestibule/tableau_des_annonces.txt")) tableau(jeu)
    }

    fun aujourdhui(): String = java.text.SimpleDateFormat("yyyyMMdd", java.util.Locale.ROOT).format(java.util.Date())

    /** Une quête par jour (graine de la partie + la date). Celle d'hier s'en va si elle n'est pas faite. */
    fun queteDuJour(jeu: Jeu) {
        if ("nid0" !in Histoire.faits(jeu)) return
        val q = q(jeu)
        val jour = aujourdhui()
        if (q.optJSONObject("jour")?.optString("date") == jour) return
        jourId(q)?.let { retirer(q, "actives", it) }
        val gid = nouvelleGen(jeu, "j$jour")
        q.put("jour", JSONObject().put("date", jour).put("id", gid))
        ajouter(q, "actives", gid)
        jeu.log(t("qu.jour.log", "titre" to titre(jeu, gid)))
    }

    // ---------------------------------------------------------------- vérifier
    private fun valeur(jeu: Jeu, x: Any): Any = if (x is Function1<*, *>) {
        @Suppress("UNCHECKED_CAST")
        (x as (Jeu) -> Any)(jeu)
    } else x

    private fun vrai(jeu: Jeu, qid: String, spec: List<Any>): Boolean {
        val k = spec[0] as String
        val f = if (spec.size > 1 && spec[1] is String) File(T(jeu), spec[1] as String) else null
        return when (k) {
            "visite" -> Maison.visitee(jeu, spec[1] as String)
            "fichier" -> f!!.isFile
            "plein" -> (lire(jeu, spec[1] as String) ?: "").isNotBlank()
            "dossier" -> f!!.isDirectory
            "contient" -> valeur(jeu, spec[2]).toString().lowercase() in (lire(jeu, spec[1] as String) ?: "").lowercase()
            "lignes" -> lignes(jeu, spec[1] as String) >= (spec[2] as Int)
            "nb" -> compte(jeu, spec[1] as String, spec[2] as String) >= (spec[3] as Int)
            "reponse" -> {
                val x = (lire(jeu, spec[1] as String) ?: "").trim()
                x.isNotEmpty() && x.all { it.isDigit() } && x.toBigInteger() == valeur(jeu, spec[2]).toString().toBigInteger()
            }
            "trie" -> {
                val la = (lire(jeu, spec[1] as String) ?: "").split("\n").map { it.trim() }.filter { it.isNotEmpty() }
                val lb = (lire(jeu, spec[2] as String) ?: "").split("\n").map { it.trim() }.filter { it.isNotEmpty() }
                la.isNotEmpty() && la == lb.sorted()
            }
            "protege" -> f!!.isFile && Histoire.protege(f)
            "exec" -> f!!.isFile && f.canExecute()
            "commits" -> try { File(T(jeu), "carnet/.git/logs/HEAD").readLines().size >= (spec[1] as Int) } catch (e: Exception) { false }
            "ip" -> Regex("\\b(\\d{1,3}\\.){3}\\d{1,3}\\b|[0-9a-f]{1,4}(:[0-9a-f]{0,4}){2,7}", RegexOption.IGNORE_CASE)
                .containsMatchIn(lire(jeu, spec[1] as String) ?: "")
            "cmd", "cmd_ici" -> q(jeu).getJSONObject("vu").optBoolean(qid)
            else -> false
        }
    }

    fun buts(jeu: Jeu, qid: String): List<List<Any>> {
        val g = q(jeu).getJSONObject("gen").optJSONObject(qid)
        return if (g != null) butGen(g) else PAR_ID[qid]?.but ?: emptyList()
    }

    private fun voirCommandes(jeu: Jeu, qid: String, lignes: List<Pair<String, String?>>) {
        for ((l, cwd) in lignes) for (spec in buts(jeu, qid)) {
            val re = (spec.getOrNull(1) as? String)?.let { Regex(it, RegexOption.IGNORE_CASE) } ?: continue
            if (spec[0] == "cmd" && re.containsMatchIn(l)) q(jeu).getJSONObject("vu").put(qid, true)
            if (spec[0] == "cmd_ici" && re.containsMatchIn(l) && Maison.dans(jeu, cwd, spec[2] as String)) q(jeu).getJSONObject("vu").put(qid, true)
        }
    }

    /** XP, objet (une décoration dans le nid), titre, et un souvenir dans le carnet d'aventure. */
    fun recompenser(jeu: Jeu, xp: Int = 0, objet: String? = null, titre: String? = null, souvenir: List<String>? = null) {
        val q = q(jeu)
        if (xp > 0) jeu.ajouterXp(xp)
        if (objet != null && objet !in liste(q, "objets")) {
            ajouter(q, "objets", objet)
            if (File(T(jeu), "nid").isDirectory) ecrire(jeu, "nid/decorations/$objet.txt", t("qu.deco.fichier", "objet" to t("qu.objet.$objet")))
            jeu.log(t("qu.objet.log", "objet" to t("qu.objet.$objet")))
        }
        if (titre != null && titre !in liste(q, "titres")) {
            ajouter(q, "titres", titre)
            q.put("titre", titre)
            jeu.log(t("qu.titre.log", "titre" to t("qu.titre.$titre")))
        }
        if (souvenir != null) {
            val a = q.getJSONArray("souvenirs")
            a.put(JSONArray(souvenir))
            while (a.length() > 200) a.remove(0)
        }
    }

    fun terminer(jeu: Jeu, qid: String) {
        val q = q(jeu)
        retirer(q, "actives", qid)
        ajouter(q, "finies", qid)
        if (suivie(q) == qid) q.put("suivie", JSONObject.NULL)
        val nom = titre(jeu, qid)
        val gen = q.getJSONObject("gen").has(qid)
        val d = PAR_ID[qid]
        val xp = if (gen) (if (qid.startsWith("j")) 40 else 20) else d!!.xp
        jeu.log(t("qu.finie.log", "titre" to nom))
        jeu.dire(t("qu.finie.dit", "titre" to nom, "xp" to xp), 12)
        jeu.animer("victoire")
        recompenser(jeu, xp, if (gen) null else d!!.objet, if (gen) null else d!!.titre, listOf("quete", qid))
        if (qid in liste(q, "offertes")) {
            annonces(jeu)
            tableau(jeu)
        }
    }

    fun accepter(jeu: Jeu, qid: String) {
        val q = q(jeu)
        if (qid in liste(q, "actives") || qid in liste(q, "finies")) return
        ajouter(q, "actives", qid)
        jeu.log(t("qu.acceptee.log", "titre" to titre(jeu, qid)))
        jeu.dire(t(Histoire.cle("qu.acceptee.dit"), "titre" to titre(jeu, qid)), 10)
    }

    /** Les noms de fichiers lus (cat, less…) dans ces lignes. */
    private fun lues(lignes: List<Pair<String, String?>>): List<String> {
        val re = Regex(LIRE, RegexOption.IGNORE_CASE)
        val out = mutableListOf<String>()
        for ((l, _) in lignes) if (re.containsMatchIn(l)) {
            out += l.trim().split(Regex("\\s+")).drop(1).map { it.trim('\'', '"').trimEnd('/').substringAfterLast('/') }
        }
        return out
    }

    /** À chaque tour de jeu, après les leçons. */
    fun tick(jeu: Jeu, tapees: List<Pair<String, String?>>) {
        if (!T(jeu).isDirectory) return
        if (!Intro.ouvert(jeu, "quetes")) return             // les quêtes arrivent avec leur présentation (Intro.kt)
        val q = q(jeu)
        poser(jeu)
        annonces(jeu)
        queteDuJour(jeu)
        val lus = lues(tapees)
        for (quete in QUETES) {
            val qid = quete.id
            if (qid in liste(q, "finies") || qid !in liste(q, "poses")) continue
            if (quete.sorte == "cachette") {
                if (Maison.visitee(jeu, "${quete.piece}/${quete.fichier}")) {
                    jeu.dire(t("qu.cachette.dit"), 10)
                    terminer(jeu, qid)
                }
            } else if (qid !in liste(q, "actives") && quete.fichier in lus) accepter(jeu, qid)
        }
        if ("tableau_des_annonces.txt" in lus) {
            for (gid in liste(q, "offertes")) accepter(jeu, gid)
            tableau(jeu)
        }
        for (qid in liste(q, "actives")) {
            if (!q.getJSONObject("gen").has(qid) && qid !in PAR_ID) { retirer(q, "actives", qid); continue }
            voirCommandes(jeu, qid, tapees)
            if (buts(jeu, qid).all { vrai(jeu, qid, it) }) terminer(jeu, qid)
        }
    }

    // ---------------------------------------------------------------- pour la carte et l'écran
    /** (pièces secrètes trouvées, pièces secrètes posées) */
    fun secrets(jeu: Jeu): Pair<Int, Int> {
        val q = q(jeu)
        val poses = liste(q, "poses")
        val finies = liste(q, "finies")
        val caches = QUETES.filter { it.sorte == "cachette" && it.id in poses }
        return caches.count { it.id in finies } to caches.size
    }

    fun pieceDeQuete(jeu: Jeu, qid: String): String? {
        val g = q(jeu).getJSONObject("gen").optJSONObject(qid)
        return if (g != null) g.getJSONObject("p").optString("piece").ifEmpty { null } else PAR_ID[qid]?.piece
    }

    /** ★ : une quête à trouver (lettre pas encore lue) ou en cours dans cette pièce. */
    fun etoile(jeu: Jeu, p: String): Boolean {
        val q = q(jeu)
        val poses = liste(q, "poses")
        val finies = liste(q, "finies")
        val actives = liste(q, "actives")
        if (QUETES.any { it.piece == p && it.sorte != "cachette" && it.id in poses && it.id !in finies }) return true
        if (p == "vestibule" && liste(q, "offertes").any { it !in actives }) return true
        return actives.any { pieceDeQuete(jeu, it) == p }
    }

    /** Les quêtes secondaires en cours, dans l'ordre du journal (pour « quetes suivre 3 ») : celle du jour d'abord. */
    fun numerotees(jeu: Jeu): List<String> {
        val q = q(jeu)
        val jour = jourId(q)
        return liste(q, "actives").sortedBy { if (it == jour) 0 else 1 }
    }

    fun suivre(jeu: Jeu, n: String?): String {
        val l = numerotees(jeu)
        val i = n?.trim()?.toIntOrNull() ?: return t("qu.suivre.aide")
        if (i !in 1..l.size) return t("qu.suivre.aucune", "n" to n)
        q(jeu).put("suivie", l[i - 1])
        return t("qu.suivre.ok", "titre" to titre(jeu, l[i - 1]))
    }

    fun ligneSuivie(jeu: Jeu): String? {
        val q = q(jeu)
        val s = suivie(q) ?: return null
        if (s !in liste(q, "actives")) return null
        return t("qu.suivie", "titre" to titre(jeu, s), "piece" to Maison.nomPiece(pieceDeQuete(jeu, s) ?: "vestibule"))
    }

    /** quetes : la quête principale, les secondaires en cours (numérotées) et les terminées. */
    fun journal(jeu: Jeu): List<String> {
        val q = q(jeu)
        val out = mutableListOf("── 📜 " + t("qu.journal.titre", "nom" to jeu.nom) + " ──")
        if (!q.isNull("titre") && q.optString("titre").isNotEmpty()) out.add(t("qu.journal.titre_porte", "titre" to t("qu.titre." + q.optString("titre"))))
        out.add("")
        out.add(t("qu.journal.principale"))
        val c = Histoire.leconCourante(jeu)
        if (c != null) {
            out.add("  ▶ ${c.etiquette} · ${c.titre}")
            out.add("     ➜ `${Regles.piege(c.etapes[jeu.etape].cmd)}`")
        } else {
            out.add("  " + (Histoire.bandeau(jeu)?.second ?: t("qu.journal.rien")))
        }
        out.add("")
        out.add(t("qu.journal.en_cours"))
        val l = numerotees(jeu)
        val jour = jourId(q)
        if (l.isEmpty()) out.add("  " + t("qu.journal.aucune"))
        for ((i, qid) in l.withIndex()) {
            val marque = if (suivie(q) == qid) "👣 " else ""
            val quoi = if (qid == jour) t("qu.journal.du_jour") + " " else ""
            out.add("  ${i + 1}. $marque$quoi${titre(jeu, qid)} (${Maison.nomPiece(pieceDeQuete(jeu, qid) ?: "vestibule")})")
            for (x in texte(jeu, qid).split("\n")) out.add("      $x")
        }
        out.add("")
        val finies = liste(q, "finies")
        val poses = liste(q, "poses")
        val actives = liste(q, "actives")
        val aTrouver = QUETES.count { it.id in poses && it.id !in finies && it.id !in actives && it.sorte != "cachette" }
        out.add(t("qu.journal.terminees", "n" to finies.size))
        for (qid in finies.takeLast(5).reversed()) out.add("  ✔ ${titre(jeu, qid)}")
        val (s, tot) = secrets(jeu)
        out.add("")
        out.add(t("qu.journal.bilan", "lettres" to aTrouver, "secrets" to s, "total" to tot, "objets" to liste(q, "objets").size))
        out.add(t("qu.journal.aide"))
        return out
    }
}
