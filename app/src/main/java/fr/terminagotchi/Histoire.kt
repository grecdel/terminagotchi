package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * « L'éveil du Terminaworld » (titre provisoire, une seule clé : lex.ch.maison) : le fil conducteur du
 * Terminagotchi, en 10 chapitres (portage de pc/tg/histoire.py). Ancien nom : « La Maison endormie ».
 *
 * Le monde à explorer : terrain_terminagotchi = le Terminaworld (sa racine = le carrefour), ~ = le camp de base,
 * dossier = un lieu, fichier = un objet, texte = un parchemin, dossier caché = un passage secret, tree = la carte
 * du monde. Les lieux gardent les vieux noms écrits sur leurs panneaux (les vrais dossiers ne changent pas) :
 * vestibule (l'entrée du monde), grenier (une forêt), cave (une caverne), bibliotheque (engloutie), etc.
 * L'enfant trouve un œuf à l'entrée du monde endormi : le téléphone. Les monstres de 10 familles se sont installés
 * chacun dans un lieu. Avec sa créature, il réveille le monde lieu par lieu. Chaque chapitre a un vrai problème à
 * résoudre ; les commandes sont les outils pour le résoudre.
 *
 *    1 reveil        Le réveil                 pwd, ls, cd, puis cd / (l'œuf, puis le voyage jusqu'à la Racine)
 *    2 nid           Le nid                    mkdir, touch, rmdir, rm -r, >, cat   (un nid, un lieu en trop, un repas)
 *    3 grenier       La forêt du Grenier       ls -R, mv, cp, rm        (des lianes ont tout mélangé)
 *    4 cave          La caverne des Démons     whoami, id, chmod, puis les lieux du gardien (/etc, /bin, /var/log)
 *    5 bibliotheque  La bibliothèque engloutie find, cat, grep, head, wc, et les tuyaux | sort
 *    6 machines      La salle des machines du volcan  free, du, rm, df, uptime, uname, getprop
 *    7 dortoir       Le dortoir des brumes     ps, ps | wc, date        (des fantômes refusent de dormir)
 *    8 atelier       L'atelier des Constructs  scripts (sh, ~/.tgrc, for, if), puis le Doom à construire
 *    9 tour          La tour des nuages        ping, ifconfig, hostname, web
 *   10 coeur         Le cœur du monde          rev, ls -a, find, cat >, grep | wc, puis Abyssor
 *   (+ telephone : le jardin du téléphone, ouvre, lampe, sms… hors compte des ailes)
 *
 * Le Terminaworld, c'est TOUT le système de fichiers, simulé par Racine.kt (/, /home, ~ = /home/explorateur, /etc, /bin,
 * /tmp, /var/log, /dev, /proc) : « Voyage jusqu'à la Racine » (fin du chapitre 1) et « Les lieux du gardien » (fin du
 * chapitre 4) y emmènent, en lecture seule. Une étape dont « ou » ou « ici » commence par / attend un lieu du
 * Terminaworld hors de la zone d'aventure (« / », « /home/explorateur »). Chaque étape a sa version « pour les grands »
 * (clé <étape>.adulte, Etape.adulte, G-32).
 *
 * Mêmes règles que sur PC : après le chapitre 2, les ailes 3 à 9 se réveillent dans l'ordre qu'on veut. On choisit
 * une aile en y entrant (cd grenier) ou avec « aile <nom> ». On peut changer d'aile en cours de route : l'étape
 * atteinte est gardée (« pas »). Le chapitre 10 s'ouvre quand au moins 5 ailes sont réveillées. Le niveau demandé
 * suit le nombre d'ailes déjà réveillées, et les étapes « expert » n'apparaissent qu'à partir du niveau 10.
 * Pendant un chapitre, sa famille de monstres est attirée (même champ « attire » que l'attirance par commande,
 * vérifiable par le serveur : la commande de la famille doit avoir été goûtée ; git pour les Constructs n'existe
 * pas sur le téléphone, ils ne sont donc attirés que si git a été goûtée ailleurs… ou tapée pour rien).
 *
 * Différences avec le PC (les commandes qui n'existent pas sur le téléphone) : pas de tree (ls -R), pas de sudo
 * (id), pas de less (cat), pas de sleep &, jobs ni kill (le dortoir compte et fait dormir les fantômes avec ps | wc
 * et date, la même limite que la famille Processus), pas de git (l'atelier fabrique le Doom), pas de curl, nslookup
 * ni ssh (la tour : hostname et web). Les leçons des branches d'avant (téléphone, système, tuyaux, scripts, créateur)
 * sont rangées dans les chapitres. Les textes propres au téléphone sont les clés « hista.* » (elles remplacent les
 * clés « hist.* » du même nom, voir cle()).
 *
 * Sauvegarde : module « histoire » = {chap, faits (leçons finies), ailes (chapitres finis), pas (étape gardée par
 * leçon), ouverts (chapitres annoncés), carnet ({commande: chapitre}), meubles, suggere, annonce, born, v}.
 * Les anciennes sauvegardes (lecon / etape / arbre) sont rangées dans les bons chapitres (migrer) ; v 1 → 2 : la
 * leçon « Une pièce en trop » (debarras) est insérée dans le chapitre 2 sans casser les parties en cours (versionV2).
 */
object Histoire {
    const val NIVEAU_EXPERT = 10
    const val AILES_POUR_LE_COEUR = 5

    class Chapitre(
        val id: String, val n: Int, val piece: String, val famille: String?, val lecons: List<String>,
        val niveaux: List<Int>? = null, val objet: String? = null, val titre: String? = null,
    )

    val CHAPITRES = listOf(
        Chapitre("reveil", 1, "vestibule", null, listOf("t0", "reveil1", "racine"), listOf(2, 2, 2), "veilleuse"),
        Chapitre("nid", 2, "nid", null, listOf("nid0", "debarras", "nid1", "secrets"), listOf(3, 3, 4, 4), "coussin"),
        Chapitre("grenier", 3, "grenier", "Sylvestres", listOf("grenier0", "t4"), null, "plante", "jardinier"),
        Chapitre("cave", 4, "cave", "Démons", listOf("cave0", "t3", "gardien"), null, "cadenas_dore", "gardien_des_cles"),
        Chapitre("bibliotheque", 5, "bibliotheque", "Abyssaux", listOf("biblio0", "biblio1", "tuyaux0", "tuyaux1"), null,
            "marque_page", "bibliothecaire"),
        Chapitre("machines", 6, "salle_des_machines", "Élémentaires", listOf("machines0", "systeme1", "systeme2"), null,
            "ventilateur", "mecanicien"),
        Chapitre("dortoir", 7, "dortoir", "Morts-vivants", listOf("dortoir0", "dortoir1"), null, "boite_a_musique", "veilleur"),
        Chapitre("atelier", 8, "atelier", "Constructs",
            listOf("atelier0", "scripts0", "scripts1", "scripts2", "createur0", "createur1", "createur2"), null, "robot_jouet", "inventeur"),
        Chapitre("tour", 9, "tour", "Célestes", listOf("tour0", "tour1"), null, "telescope", "astronome"),
        Chapitre("coeur", 10, "coeur", "Aberrations", listOf("coeur0", "coeur1", "coeur2"), listOf(10, 11, 12), "couronne", "heros"),
        // le jardin du téléphone (les leçons propres à Android), hors compte des ailes
        Chapitre("telephone", 0, "jardin", null, listOf("telephone0", "telephone1", "telephone2"), null, "antenne"),
    )
    val PAR_CHAP = CHAPITRES.associateBy { it.id }
    val AILES = CHAPITRES.filter { it.n in 3..9 }.map { it.id }

    fun chapitreDeLecon(lid: String) = CHAPITRES.firstOrNull { lid in it.lecons }
    fun chapitreDePiece(p: String) = CHAPITRES.firstOrNull { it.piece == p }

    // ---------------------------------------------------------------- textes
    /** Le palier de vocabulaire de la partie en cours (mis à jour par leconCourante, comme lecons.PALIER sur PC). */
    @Volatile var palier = 0

    /** La clé propre au téléphone si elle existe (hista.x pour hist.x, qua.x pour qu.x, cartea.x pour carte.x). */
    fun cle(k: String): String {
        val i = k.indexOf('.')
        if (i <= 0) return k
        val a = k.substring(0, i) + "a" + k.substring(i)
        return if (k.substring(0, i) in setOf("hist", "qu", "carte") && Langue.existe(a)) a else k
    }

    /** Un texte de leçon ou de l'histoire, avec le jargon du palier ({dossier}, {processus}…) et le nom des pièces ({piece}). */
    fun tx(c: String?, params: Map<String, String> = emptyMap(), p: Int = palier): String {
        if (c.isNullOrEmpty()) return ""
        val d = HashMap(Mots.termes(p))
        for ((k, v) in params) d[k] = if (k == "piece") Maison.nomPiece(v) else v
        return Langue.remplir(Langue.modele(cle(c)), d)
    }

    fun dire(jeu: Jeu, c: String, vararg p: Pair<String, Any?>): String =
        tx(c, p.associate { it.first to (it.second?.toString() ?: "") }, Mots.palier(jeu))

    fun nomChapitre(cid: String) = t(cle("hist.$cid.titre"))

    // ---------------------------------------------------------------- les leçons de l'histoire
    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)
    private const val LS = "^(ls|dir|gci|get-childitem)\\b"
    private const val LIRE = "^(cat|type|gc|get-content|less|more|head|tail)\\b"

    /** Une étape nouvelle : textes hist.<leçon>.<i>.dit / .bravo. */
    private fun n(lid: String, i: Int, cmd: String, re: String? = null, fs: ((Jeu) -> Boolean)? = null, ou: String? = null,
                  ici: String? = null, exact: Boolean = false, expert: Boolean = false, astuce: String? = null, cree: String? = null,
                  params: Map<String, String> = emptyMap()) =
        Etape("hist.$lid.$i.dit", cmd, "hist.$lid.$i.bravo", re?.let { r(it) }, fs, astuce, cree, ou, ici, exact, expert, params)

    /** Une étape propre au téléphone : textes hista.<leçon>.<i>.dit / .bravo. */
    private fun a(lid: String, i: Int, cmd: String, re: String) = Etape("hista.$lid.$i.dit", cmd, "hista.$lid.$i.bravo", r(re))

    private fun entree(piece: String) = Etape("hist.entree.dit", "cd ~/terrain_terminagotchi/$piece", "hist.entree.bravo",
        ici = piece, params = mapOf("piece" to piece))

    private val FRAGMENTS = listOf("coeur/.porte_secrete/fragment_1.txt", "grenier/fragment_2.txt", "tour/fragment_3.txt")

    /** Toutes les leçons (catalogue du téléphone + celles de l'histoire), par identifiant. */
    fun catalogue(jeu: Jeu): Map<String, Lecon> {
        val base = LinkedHashMap<String, Lecon>()
        jeu.lecons.forEachIndexed { i, l -> base["t$i"] = l }
        for ((b, br) in jeu.branches) br.lecons.forEachIndexed { i, l -> base["$b$i"] = l }
        fun ref(lid: String, i: Int) = base[lid]!!.etapes[i]
        val nouvelles = linkedMapOf(
            "reveil1" to Lecon("hist.reveil1.titre", null, 1, listOf(
                n("reveil1", 0, "cd terrain_terminagotchi", ici = ""),
                n("reveil1", 1, "ls", re = LS, ou = ""),
                n("reveil1", 2, "cd vestibule", ici = "vestibule"),
                n("reveil1", 3, "ls", re = LS, ou = "vestibule"),
            )),
            // « Voyage jusqu'à la Racine » (G-33) : le Terminaworld est tout le système de fichiers (simulé, Racine.kt)
            "racine" to Lecon("hist.racine.titre", null, 1, listOf(
                n("racine", 0, "cd /", ici = "/"),
                n("racine", 1, "ls", re = LS, ou = "/"),
                n("racine", 2, "pwd", re = "^(pwd|get-location|gl)\\b", ou = "/"),
                n("racine", 3, "cd ~", ici = Racine.HOME, params = mapOf("chemin" to Racine.HOME)),
                n("racine", 4, "cd ${Racine.HOME}/terrain_terminagotchi/vestibule", ici = "vestibule"),
            )),
            "nid0" to Lecon("lec.t1.titre", "Bâtisseur", 1, listOf(
                n("nid0", 0, "cd ..", ici = "", exact = true),
                ref("t1", 2),
                n("nid0", 2, "touch nid/lit.txt", fs = { File(it.terrain, "nid/lit.txt").isFile }, cree = "nid/lit.txt"),
            )),
            // une pièce en trop : démolir une pièce vide (rmdir), puis la broyeuse pour une pièce pleine (rm -r)
            "debarras" to Lecon("hist.debarras.titre", null, 1, listOf(
                n("debarras", 0, "mkdir debarras", fs = { debarras(it) != null }, cree = "debarras"),
                n("debarras", 1, "rmdir debarras", fs = { debarras(it) == null }),
                n("debarras", 2, "rm -r vieille_cabane", fs = { !File(it.terrain, "vieille_cabane").exists() && it.terrain.isDirectory }),
            )),
            "nid1" to Lecon("lec.t2.titre", null, 1, listOf(ref("t2", 0), ref("t2", 1))),
            // mini-leçon « pont » (G-05) : les passages secrets (ls -a) juste avant l'ouverture de l'exploration
            "secrets" to Lecon("hist.secrets.titre", null, 1, listOf(
                n("secrets", 0, "ls -a", re = "^(ls\\s+-\\w*[aA]|dir\\s+(-force|/a)|gci\\s+-force|get-childitem\\s+-force)", ou = ""),
                n("secrets", 1, "cat .mot_secret.txt", re = "$LIRE.*\\.mot_secret", ou = ""),
            )),
            // pas de tree sur le téléphone : ls -R montre le plan
            "grenier0" to Lecon("hist.grenier0.titre", "Explorateur", 1, listOf(
                entree("grenier"),
                n("grenier0", 1, "ls -R", re = "^(tree|ls\\s+-\\w*R)\\b"),
                n("grenier0", 2, "mv fouillis/ours_en_peluche.txt ../nid/", fs = { File(it.terrain, "nid/ours_en_peluche.txt").isFile },
                    cree = "nid/ours_en_peluche.txt"),
            )),
            // pas de sudo sur le téléphone : id montre les clubs (les groupes) de l'utilisateur
            "cave0" to Lecon("hist.cave0.titre", null, 1, listOf(entree("cave"), ref("systeme0", 0), ref("systeme0", 1))),
            // « Les lieux du gardien » (G-33) : la salle des règles, l'armurerie, les archives, en lecture seule
            "gardien" to Lecon("hist.gardien.titre", null, 1, listOf(
                n("gardien", 0, "cat /etc/hostname", re = "^(cat|head|tail|more|less)\\b.*/etc/hostname"),
                n("gardien", 1, "ls /bin", re = "^ls\\b.*/(usr/)?s?bin\\b"),
                n("gardien", 2, "ls /var/log", re = "^ls\\b.*/var/log"),
                Etape("hist.gardien.3.dit", "ls -l /etc/hostname", "hista.gardien.3.bravo", r("^(ls\\s+-\\w*l|stat)\\b.*/etc/"),
                    adulteCle = "hista.gardien.3.adulte"),
            )),
            "biblio0" to Lecon("hist.biblio0.titre", null, 1, listOf(
                entree("bibliotheque"),
                n("biblio0", 1, "find . -name \"*abysses*\"", re = "^(find|get-childitem|gci|dir)\\b.*abyss"),
                n("biblio0", 2, "cat etagere_c/coin_poussiereux/livre_des_abysses.txt",
                    re = "^(less|more|cat|type|gc|get-content|head|tail)\\b.*abysses"),
            )),
            "biblio1" to Lecon("hist.biblio1.titre", "Inspecteur", 1, listOf(
                ref("t2", 2),
                n("biblio1", 1, "head -n 3 etagere_c/coin_poussiereux/livre_des_abysses.txt", re = "^(head|get-content|gc)\\b.*abysses"),
                n("biblio1", 2, "wc -l etagere_c/coin_poussiereux/livre_des_abysses.txt", re = "^(wc\\b|get-content.*measure-object|gc.*measure)"),
                n("biblio1", 3, "grep -rn TRESOR .", re = "^(grep\\s+-\\w*r|select-string|sls)\\b.*tresor", expert = true),
            )),
            "machines0" to Lecon("hist.machines0.titre", null, 1, listOf(
                entree("salle_des_machines"),
                n("machines0", 1, "free -h", re = "^free\\b"),
                n("machines0", 2, "du -sh *", re = "^(du|get-childitem|gci|dir)\\b", ou = "salle_des_machines"),
                n("machines0", 3, "rm vieux_carton.bin", fs = {
                    !File(it.terrain, "salle_des_machines/vieux_carton.bin").exists() && File(it.terrain, "salle_des_machines").isDirectory }),
            )),
            "dortoir0" to Lecon("hist.dortoir0.titre", "Vigie", 1, listOf(entree("dortoir"), ref("systeme0", 2))),
            // pas de sleep &, jobs ni kill sur le téléphone (même limite que la famille Processus : ps et date)
            "dortoir1" to Lecon("hista.dortoir1.titre", "Chasseur", 1, listOf(
                a("dortoir1", 0, "ps -A | wc -l", "^(ps|top)\\b.*\\|\\s*wc\\b"),
                a("dortoir1", 1, "date", "^date\\b"),
            )),
            "atelier0" to Lecon("hist.atelier0.titre", null, 1, listOf(
                entree("atelier"),
                n("atelier0", 1, "cat plan_de_travail.txt", re = "$LIRE.*plan_de_travail"),
            )),
            "tour0" to Lecon("lec.reseau0.titre", "Radar", 1, listOf(
                entree("tour"),
                Etape("lec.reseau0.0.dit", "ping -c 3 example.com", "lec.reseau0.0.bravo", r("^ping\\b")),
                Etape("lec.reseau0.1.dit", "ifconfig", "lec.reseau0.1.bravo", r("^(ip|ifconfig|ipconfig)\\b")),
            )),
            // pas de curl, nslookup ni ssh sur le téléphone : le nom de la maison, puis le navigateur comme facteur
            "tour1" to Lecon("lec.reseau1.titre", "Facteur", 1, listOf(
                a("tour1", 0, "hostname", "^hostname\\b"),
                a("tour1", 1, "web example.com", "^web\\s+\\S+"),
            )),
            "coeur0" to Lecon("hist.coeur0.titre", null, 1, listOf(
                entree("coeur"),
                n("coeur0", 1, "rev message_brouille.txt", re = "(^|\\s)rev\\b.*message"),
                n("coeur0", 2, "ls -a", re = "^(ls\\s+-\\w*a|dir\\s+-force|gci\\s+-force|get-childitem\\s+-force)", ou = "coeur"),
                n("coeur0", 3, "cd .porte_secrete", ici = "coeur/.porte_secrete"),
            )),
            "coeur1" to Lecon("hist.coeur1.titre", null, 1, listOf(
                n("coeur1", 0, "find ~/terrain_terminagotchi -name \"fragment*\"", re = "^(find|get-childitem|gci|dir)\\b.*fragment"),
                n("coeur1", 1, "cat coeur/.porte_secrete/fragment_1.txt grenier/fragment_2.txt tour/fragment_3.txt > coeur/coeur_repare.txt",
                    fs = { repare(it) }, cree = "coeur/coeur_repare.txt"),
                n("coeur1", 2, "chmod 444 coeur/coeur_repare.txt", fs = { repare(it) && protege(File(it.terrain, "coeur/coeur_repare.txt")) }),
            )),
            "coeur2" to Lecon("hist.coeur2.titre", "Héros", 1, listOf(
                n("coeur2", 0, "cat coeur/.porte_secrete/abyssor_dort.txt", re = "$LIRE.*abyssor"),
                n("coeur2", 1, "grep -rl ABYSSOR ~/terrain_terminagotchi | wc -l", re = "(grep|select-string|sls)\\b.*abyssor"),
                n("coeur2", 2, "echo ? > coeur/reponse.txt", fs = { reponse(it) }),
            )),
        )
        // les étapes en plus pour les experts (niveau 10 et plus) dans les leçons reprises telles quelles
        val expert = mapOf("t4" to listOf(n("t4", 3, "cp -r grenier/fouillis grenier/fouillis_secours",
            fs = { File(it.terrain, "grenier/fouillis_secours").isDirectory }, expert = true)))
        val tout = LinkedHashMap<String, Lecon>()
        for ((k, l) in base) tout[k] = expert[k]?.let { Lecon(l.titreCle, l.skill, l.niveau, l.etapes + it) } ?: l
        tout.putAll(nouvelles)
        return tout
    }

    fun lecon(jeu: Jeu, lid: String): Lecon? = jeu.catalogue[lid]

    /** Le débarras de la leçon « Une pièce en trop » (dans la grande salle ou dans le nid), ou null. */
    fun debarras(jeu: Jeu): File? =
        listOf(File(jeu.terrain, "debarras"), File(jeu.terrain, "nid/debarras")).firstOrNull { it.isDirectory }

    // ---------------------------------------------------------------- l'état
    private fun liste(o: JSONObject, k: String) = Quetes.liste(o, k)
    private fun mettre(o: JSONObject, k: String, l: List<String>) { o.put(k, JSONArray(l)) }
    private fun ajouter(o: JSONObject, k: String, v: String) { val l = liste(o, k); if (v !in l) { l.add(v); mettre(o, k, l) } }

    fun h(jeu: Jeu): JSONObject {
        val o = jeu.extra.optJSONObject("histoire")
        if (o == null || !o.has("v")) migrer(jeu)
        val h = jeu.module("histoire")
        if (!h.has("chap")) h.put("chap", "reveil")
        for (k in listOf("faits", "ailes", "ouverts", "meubles", "suggere")) if (!h.has(k)) h.put(k, JSONArray())
        for (k in listOf("pas", "carnet")) if (!h.has(k)) h.put(k, JSONObject())
        if (!h.has("born")) h.put("born", System.currentTimeMillis() / 1000)
        if (h.optInt("v", 1) < 2) versionV2(jeu, h)
        if (h.optInt("v", 1) < 3) versionV3(h)
        if (h.optInt("v", 1) < 4) versionV4(h)
        return h
    }

    /** Sauvegarde v3 → v4 : « Voyage jusqu'à la Racine » finit le chapitre 1, « Les lieux du gardien » le chapitre 4. Un
     *  chapitre déjà fini les compte comme faites ; une partie en plein chapitre les fera à la fin. */
    private fun versionV4(h: JSONObject) {
        h.put("v", 4)
        if ("reveil" in liste(h, "ailes")) ajouter(h, "faits", "racine")
        if ("cave" in liste(h, "ailes")) ajouter(h, "faits", "gardien")
    }

    /** Sauvegarde v2 → v3 : la mini-leçon « passages secrets » (secrets) finit le chapitre 2. Un chapitre 2 déjà fini
     *  la compte comme faite ; une partie en plein chapitre 2 la fera à la fin. */
    private fun versionV3(h: JSONObject) {
        h.put("v", 3)
        if ("nid" in liste(h, "ailes")) ajouter(h, "faits", "secrets")
    }

    /**
     * Sauvegarde v1 → v2 : la leçon « Une pièce en trop » (debarras) arrive entre le nid (nid0) et le garde-manger
     * (nid1). Le chapitre 2 déjà fini la compte comme faite ; une partie en plein garde-manger le garde (son étape
     * est rangée pour après le débarras) ; une partie en plein nid0 continue nid0 à la même étape.
     */
    private fun versionV2(jeu: Jeu, h: JSONObject) {
        h.put("v", 2)
        val f = liste(h, "faits")
        if ("debarras" in f) return
        if ("nid1" in f || "nid" in liste(h, "ailes")) { ajouter(h, "faits", "debarras"); return }
        if ("nid0" in f && h.optString("chap") == "nid") {
            if (jeu.etape > 0) h.getJSONObject("pas").put("nid1", jeu.etape)
            jeu.etape = 0
        }
    }

    fun faits(jeu: Jeu) = liste(h(jeu), "faits")
    fun ailes(jeu: Jeu) = liste(h(jeu), "ailes")
    fun chap(jeu: Jeu): String? = h(jeu).let { if (it.isNull("chap")) null else it.optString("chap").ifEmpty { null } }
    private fun mettreChap(jeu: Jeu, c: String?) { h(jeu).put("chap", c ?: JSONObject.NULL) }

    /** La graine des meubles et des quêtes de cette partie (comme f"{partie}:{born}" sur PC). */
    fun graine(jeu: Jeu) = "${jeu.partie.ifEmpty { "1" }}:${h(jeu).optLong("born")}"

    fun fini(jeu: Jeu, cid: String) = cid in ailes(jeu)
    fun nbAiles(jeu: Jeu) = ailes(jeu).count { it in AILES }

    /** Le chapitre peut être joué (ou rejoué) maintenant. */
    fun ouvert(jeu: Jeu, cid: String): Boolean = when (cid) {
        !in PAR_CHAP -> false
        "reveil" -> true
        "nid" -> fini(jeu, "reveil")
        "coeur" -> nbAiles(jeu) >= AILES_POUR_LE_COEUR
        else -> fini(jeu, "nid")
    }

    /** La pièce existe dans la maison de cette partie (sa porte a été posée). */
    fun pieceOuverte(jeu: Jeu, p: String): Boolean {
        if (p == "vestibule") return fini(jeu, "reveil") || (chap(jeu) == "reveil" && "t0" in faits(jeu))
        val c = chapitreDePiece(p) ?: return false
        if (p == "nid") return fini(jeu, "reveil")
        return ouvert(jeu, c.id)
    }

    /** XP qu'une leçon finie a donnée au moins (20 à la fin, + 5 par étape avant la dernière), et un chapitre fini. */
    const val XP_LECON_SURE = 20
    const val XP_CHAPITRE_SUR = 30

    /** L'XP que l'apprentissage seul a forcément donnée : leçons et chapitres finis (jamais la répétition). */
    fun xpAppris(jeu: Jeu) = XP_LECON_SURE * faits(jeu).size + XP_CHAPITRE_SUR * ailes(jeu).size

    /** Le niveau demandé pour voir la leçon. G-04 : jamais plus que le niveau que les leçons et chapitres déjà finis
     *  ont donné ; un enfant qui suit le parcours n'a jamais à « remplir » (seul l'œuf du réveil attend ses premières
     *  commandes). */
    fun niveauRequis(jeu: Jeu, c: Chapitre, i: Int): Int {
        val n = c.niveaux?.let { it[minOf(i, it.size - 1)] }
            ?: minOf(12, 5 + nbAiles(jeu) + i)               // les ailes : la difficulté suit le nombre d'ailes réveillées
        if (c.id == "reveil") return n
        return maxOf(1, minOf(n, Regles.niveau(xpAppris(jeu))))
    }

    fun etapes(jeu: Jeu, lid: String): List<Etape> =
        lecon(jeu, lid)?.etapes?.filter { !it.expert || jeu.niveau >= NIVEAU_EXPERT } ?: emptyList()

    fun chapitreCourant(jeu: Jeu): Chapitre? {
        val c = PAR_CHAP[chap(jeu)] ?: return null
        return if (ouvert(jeu, c.id) && !fini(jeu, c.id)) c else null
    }

    fun leconId(jeu: Jeu): String? {
        val c = chapitreCourant(jeu) ?: return null
        val f = faits(jeu)
        return c.lecons.firstOrNull { it !in f }
    }

    /** La leçon en cours : son chapitre, ses étapes (filtrées), le niveau demandé, l'étiquette « Leçon 1/2 ». */
    class Courante(val id: String, val chap: Chapitre, val lecon: Lecon, val etapes: List<Etape>, val niveau: Int, val etiquette: String) {
        val titre: String get() = lecon.titre
        val skill: String? get() = lecon.skill
    }

    fun leconCourante(jeu: Jeu): Courante? {
        val lid = leconId(jeu) ?: return null
        val c = chapitreCourant(jeu)!!
        val i = c.lecons.indexOf(lid)
        val l = lecon(jeu, lid) ?: return null
        val st = etapes(jeu, lid)
        if (st.isEmpty()) return null
        if (jeu.etape >= st.size) {
            // filet de sécurité : toutes les étapes sont faites (sauvegarde d'une autre version…) → la leçon se termine
            finirLecon(jeu, Courante(lid, c, l, st, niveauRequis(jeu, c, i), ""))
            return leconCourante(jeu)
        }
        jeu.etape = jeu.etape.coerceIn(0, st.size - 1)
        palier = Mots.palier(jeu)
        return Courante(lid, c, l, st, niveauRequis(jeu, c, i), t("hist.etiquette", "i" to i + 1, "total" to c.lecons.size))
    }

    // ---------------------------------------------------------------- fichiers du terrain
    /** Écrit dans le terrain (jamais ailleurs). Un texte reçoit un retour à la ligne final. */
    fun ecrire(jeu: Jeu, rel: String, contenu: Any, finLigne: Boolean = true): Boolean {
        val f = File(jeu.terrain, rel)
        if (!f.canonicalPath.startsWith(jeu.terrain.canonicalPath + "/")) return false
        return try {
            f.parentFile?.mkdirs()
            if (contenu is ByteArray) f.writeBytes(contenu)
            else { val s = contenu.toString(); f.writeText(if (!finLigne || s.endsWith("\n")) s else s + "\n") }
            true
        } catch (e: Exception) { false }
    }

    fun lire(jeu: Jeu, rel: String): String? {
        val b = try { File(jeu.terrain, rel).readBytes() } catch (e: Exception) { return null }
        if (b.size >= 2 && ((b[0] == 0xFF.toByte() && b[1] == 0xFE.toByte()) || (b[0] == 0xFE.toByte() && b[1] == 0xFF.toByte())))
            return String(b, Charsets.UTF_16)
        return String(b, Charsets.UTF_8)
    }

    /** Personne ne peut plus écrire dans ce fichier (aucun droit w, comme _protected sur PC). */
    fun protege(f: File): Boolean = try {
        f.exists() && java.nio.file.Files.getPosixFilePermissions(f.toPath()).none { it.name.endsWith("_WRITE") }
    } catch (e: Exception) { f.exists() && !f.canWrite() }

    private fun repare(jeu: Jeu): Boolean {
        val txt = lire(jeu, "coeur/coeur_repare.txt") ?: return false
        if (txt.isEmpty()) return false
        return FRAGMENTS.all { f -> val x = (lire(jeu, f) ?: "").trim(); x.isNotEmpty() && x in txt }
    }

    /** Le nombre de fichiers de la maison qui contiennent le mot ABYSSOR (la réponse de l'énigme). */
    fun tracesAbyssor(jeu: Jeu): Int {
        val T = jeu.terrain
        if (!T.isDirectory) return 0
        val mot = "ABYSSOR".toByteArray()
        return T.walkTopDown().onEnter { it.name != ".git" }.count { f ->
            f.isFile && !(f.name == "reponse.txt" && f.parentFile?.name == "coeur") && f.length() < 200000 &&
                try { contientOctets(f.readBytes(), mot) } catch (e: Exception) { false }
        }
    }

    private fun contientOctets(b: ByteArray, m: ByteArray): Boolean {
        outer@ for (i in 0..b.size - m.size) {
            for (j in m.indices) if (b[i + j] != m[j]) continue@outer
            return true
        }
        return false
    }

    private fun reponse(jeu: Jeu): Boolean {
        val x = (lire(jeu, "coeur/reponse.txt") ?: "").trim()
        return x.isNotEmpty() && x.all { it.isDigit() } && x.toBigInteger() == tracesAbyssor(jeu).toBigInteger()
    }

    // ---------------------------------------------------------------- les meubles de la maison
    private fun inverse(l: String): String {
        val cps = l.codePoints().toArray()
        cps.reverse()
        return String(cps, 0, cps.size)
    }

    /** Ce que le jeu pose dans une pièce quand sa porte s'ouvre : {chemin: texte (ou octets)}. */
    fun meubles(jeu: Jeu, p: String): Map<String, Any> = when (p) {
        "vestibule" -> mapOf("vestibule/oeuf_tout_chaud.txt" to dire(jeu, "hist.meuble.oeuf"))
        "grenier" -> linkedMapOf("grenier/fouillis/ours_en_peluche.txt" to dire(jeu, "hist.meuble.ours"),
            "grenier/fouillis/malle/vieille_robe.txt" to dire(jeu, "hist.meuble.robe"),
            "grenier/fouillis/carton/jouet_casse.txt" to dire(jeu, "hist.meuble.jouet"))
        "bibliotheque" -> linkedMapOf("bibliotheque/etagere_a/livre_des_recettes.txt" to dire(jeu, "hist.meuble.recettes"),
            "bibliotheque/etagere_b/livre_des_etoiles.txt" to dire(jeu, "hist.meuble.etoiles"),
            "bibliotheque/etagere_c/coin_poussiereux/livre_des_abysses.txt" to Langue.liste("hist.meuble.abysses").joinToString("\n"))
        "salle_des_machines" -> mapOf("salle_des_machines/vieux_carton.bin" to ByteArray(300000))
        "atelier" -> mapOf("atelier/plan_de_travail.txt" to dire(jeu, "hist.meuble.plan"))
        // la vieille cabane pleine de planches de la leçon « Une pièce en trop » (seulement par BESOINS)
        "nid" -> linkedMapOf("vieille_cabane/planche_1.txt" to dire(jeu, "hist.meuble.planche"),
            "vieille_cabane/planche_2.txt" to dire(jeu, "hist.meuble.planche"),
            ".mot_secret.txt" to dire(jeu, "hist.meuble.mot_secret", "nom" to jeu.nom))
        "coeur" -> {
            val m = linkedMapOf<String, Any>(
                "coeur/message_brouille.txt" to dire(jeu, "hist.meuble.message").split("\n").joinToString("\n") { inverse(it) },
                "coeur/.porte_secrete/abyssor_dort.txt" to dire(jeu, "hist.meuble.abyssor"))
            FRAGMENTS.forEachIndexed { i, f -> m[f] = t("hist.meuble.fragment.${i + 1}") }
            val r = Quetes.rnd(jeu, "abyssor")
            val lieux = listOf("grenier/griffure.txt", "cave/griffure.txt", "bibliotheque/etagere_a/griffure.txt",
                "dortoir/griffure.txt", "atelier/griffure.txt", "tour/griffure.txt", "vestibule/griffure.txt")
            val nb = r.randint(3, 6)
            for (f in r.echantillon(lieux, nb)) m[f] = t("hist.meuble.griffure")
            m
        }
        else -> emptyMap()
    }

    /** fichiers dont une leçon a besoin : remis s'ils disparaissent (tant que l'étape n'est pas passée) */
    private val BESOINS: Map<String, List<Pair<String, Int?>>> = mapOf(
        "reveil1" to listOf("vestibule/oeuf_tout_chaud.txt" to null),
        "debarras" to listOf("vieille_cabane/planche_1.txt" to 2, "vieille_cabane/planche_2.txt" to 2),
        "secrets" to listOf(".mot_secret.txt" to null),
        "grenier0" to listOf("grenier/fouillis/ours_en_peluche.txt" to 2),
        "biblio0" to listOf("bibliotheque/etagere_c/coin_poussiereux/livre_des_abysses.txt" to null),
        "biblio1" to listOf("bibliotheque/etagere_c/coin_poussiereux/livre_des_abysses.txt" to null),
        "machines0" to listOf("salle_des_machines/vieux_carton.bin" to 3),
        "atelier0" to listOf("atelier/plan_de_travail.txt" to null),
        "coeur0" to listOf("coeur/message_brouille.txt" to null, "coeur/.porte_secrete/abyssor_dort.txt" to null),
        "coeur1" to FRAGMENTS.map { it to 1 },
        "coeur2" to listOf("coeur/.porte_secrete/abyssor_dort.txt" to null),
    )

    /** Pose les portes des pièces ouvertes et leurs meubles (une fois). Jamais hors du terrain.
     *  Si le terrain a disparu après sa construction, rien n'est fait (Terrain.kt aide à le refaire). */
    fun meubler(jeu: Jeu): List<String> {
        val h = h(jeu)
        val lid = leconId(jeu)
        val T = jeu.terrain
        if (!T.isDirectory) {
            if (lid != "reveil1") return emptyList()
            if (!T.mkdirs() && !T.isDirectory) return emptyList()
        }
        val poses = mutableListOf<String>()
        for (p in Maison.PIECES + "jardin") {
            if (p == "nid" || (!pieceOuverte(jeu, p) && !(p == "vestibule" && lid == "reveil1"))) continue
            val d = File(T, p)
            val cle = "piece:$p"
            if (!d.isDirectory) {
                if (!d.mkdirs() && !d.isDirectory) continue
                // la pièce avait disparu (terrain effacé) : ses meubles et ses quêtes pas finies reviennent
                val m = liste(h, "meubles")
                if (m.remove(cle)) mettre(h, "meubles", m)
                val q = Quetes.q(jeu)
                val finies = Quetes.liste(q, "finies")
                q.put("poses", JSONArray(Quetes.liste(q, "poses").filter { it in finies || Quetes.PAR_ID[it]?.piece != p }))
            }
            if (cle !in liste(h, "meubles")) {
                ajouter(h, "meubles", cle)
                for ((rel, contenu) in meubles(jeu, p)) {
                    if (!File(T, rel).exists()) { ecrire(jeu, rel, contenu); poses.add(rel) }
                }
            }
        }
        // les fichiers dont la leçon en cours a besoin
        val besoins = BESOINS[lid]
        if (lid != null && besoins != null) {
            val step = jeu.etape
            val piece = chapitreCourant(jeu)!!.piece
            val tous = HashMap<String, Any>()
            for (p in listOf(piece, "coeur", "grenier", "tour", "vestibule")) if (pieceOuverte(jeu, p) || p == piece) tous.putAll(meubles(jeu, p))
            for ((rel, jusque) in besoins) {
                if ((jusque == null || step < jusque) && !File(T, rel).exists() && rel in tous) {
                    if (lid == "grenier0" && File(T, "nid/ours_en_peluche.txt").exists()) continue
                    ecrire(jeu, rel, tous[rel]!!)
                    poses.add(rel)
                }
            }
        }
        return poses
    }

    // ---------------------------------------------------------------- choisir une aile
    /** Commence (ou reprend) un chapitre. Renvoie le message à afficher. */
    fun choisir(jeu: Jeu, cid: String, dit: Boolean = true): String {
        if (cid !in PAR_CHAP) return t("hist.aile.inconnue", "nom" to cid)
        if (fini(jeu, cid)) return t("hist.aile.deja", "chapitre" to nomChapitre(cid))
        if (!ouvert(jeu, cid)) {
            if (cid == "coeur") return t("hist.coeur.ferme", "n" to nbAiles(jeu), "total" to AILES_POUR_LE_COEUR)
            return t("hist.aile.fermee", "chapitre" to nomChapitre(cid))
        }
        val h = h(jeu)
        if (chap(jeu) == cid && chapitreCourant(jeu) != null) return t("hist.aile.en_cours", "chapitre" to nomChapitre(cid))
        leconId(jeu)?.let { h.getJSONObject("pas").put(it, jeu.etape) }          // l'étape atteinte est gardée
        mettreChap(jeu, cid)
        val nouv = leconId(jeu)
        jeu.etape = if (nouv != null) prendrePas(jeu, nouv) else 0
        h.remove("annonce")
        jeu.indiceLecon = null
        val msg = t("hist.aile.choisie", "chapitre" to nomChapitre(cid))
        if (dit) jeu.dire(msg, 8)
        return msg
    }

    private fun prendrePas(jeu: Jeu, lid: String): Int {
        val pas = h(jeu).getJSONObject("pas")
        val s = pas.optInt(lid, 0)
        pas.remove(lid)
        return s
    }

    /** « grenier », « 3 », « Le grenier… » → l'identifiant du chapitre (ou null). Les anciennes branches aussi. */
    fun chercherChapitre(nom: String?): String? {
        val n = (nom ?: "").trim().lowercase()
        if (n.isEmpty()) return null
        ANCIENNES[Bestiaire.simple(n)]?.let { return it }
        for (c in CHAPITRES) {
            if (n == c.id || n == c.piece || n == c.n.toString() || (n.length >= 3 && n in nomChapitre(c.id).lowercase())) return c.id
        }
        return null
    }

    /** les branches de l'arbre d'avant (arbre scripts…) → leur chapitre */
    private val ANCIENNES = mapOf("telephone" to "telephone", "systeme" to "machines", "tuyaux" to "bibliotheque",
        "scripts" to "atelier", "createur" to "atelier")

    /** Entrer dans une aile pas encore réveillée la choisit (s'il n'y a pas de chapitre en cours). */
    private fun visiteAile(jeu: Jeu, cwds: List<String?>) {
        if (!fini(jeu, "nid")) return
        val h = h(jeu)
        for (cwd in cwds) {
            val p = Maison.rel(jeu, cwd) ?: continue
            val c = chapitreDePiece(p.split("/")[0]) ?: continue
            if (fini(jeu, c.id) || !ouvert(jeu, c.id) || chap(jeu) == c.id) continue
            if (chapitreCourant(jeu) == null) choisir(jeu, c.id)
            else if (c.id !in liste(h, "suggere")) {
                ajouter(h, "suggere", c.id)
                jeu.dire(t(cle("hist.aile.autre"), "chapitre" to nomChapitre(c.id), "id" to c.id), 10)
            }
        }
    }

    // ---------------------------------------------------------------- avancer
    private fun finirChapitre(jeu: Jeu, c: Chapitre) {
        val h = h(jeu)
        ajouter(h, "ailes", c.id)
        jeu.log(t("hist.chapitre.fini.log", "chapitre" to nomChapitre(c.id)))
        jeu.dire(dire(jeu, "hist.${c.id}.fin"), 16)
        jeu.animer("victoire")
        jeu.ajouterXp(30)
        Quetes.recompenser(jeu, objet = c.objet, titre = c.titre, souvenir = listOf("chap", c.id))
        mettreChap(jeu, null)
        when {
            c.id == "reveil" -> mettreChap(jeu, "nid")
            c.id == "nid" -> jeu.dire(dire(jeu, "hist.libre.dit"), 16)
            c.id == "coeur" -> jeu.dire(dire(jeu, "hist.fin.dit"), 16)
            c.id in AILES -> if (nbAiles(jeu) == AILES_POUR_LE_COEUR) {
                jeu.log(t("hist.coeur.ouvert.log"))
                jeu.dire(dire(jeu, "hist.coeur.ouvert.dit"), 16)
            } else jeu.dire(t(cle("hist.aile.suite"), "n" to nbAiles(jeu)), 12)
        }
        h.remove("annonce")
    }

    /** Une étape réussie. Renvoie true s'il reste des étapes dans la leçon. */
    private fun avancer(jeu: Jeu, les: Courante): Boolean {
        val e = les.etapes[jeu.etape]
        jeu.log("✔ ${e.cmd}")
        jeu.dire(e.bravo, 12)
        Explique.apresReussite(jeu, e.cmd)          // -r, >>, 444… : expliqués une fois (Explique.kt)
        jeu.etape++
        jeu.animer("content")
        if (jeu.etape < les.etapes.size) {
            jeu.ajouterXp(5)
            return true
        }
        finirLecon(jeu, les)
        return false
    }

    private val STAT = mapOf("tour" to "Agilité", "atelier" to "Intelligence", "dortoir" to "Force", "machines" to "Force",
        "cave" to "Force", "bibliotheque" to "Endurance", "telephone" to "Agilité")

    private fun finirLecon(jeu: Jeu, les: Courante) {
        val h = h(jeu)
        jeu.etape = 0
        ajouter(h, "faits", les.id)
        val sk = les.skill
        if (sk != null && sk !in jeu.skills) jeu.skills.add(sk)
        val c = les.chap
        if (sk != null) {
            jeu.log(t("lec.finie.log", "titre" to les.titre, "skill" to Regles.nomSkill(sk)))
            jeu.dire(t("lec.finie.dit", "skill" to Regles.nomSkill(sk)), 14)
        } else {
            jeu.log(t("hist.lecon.finie.log", "titre" to les.titre))
            jeu.dire(t("hist.lecon.finie.dit"), 12)
        }
        STAT[c.id]?.let { jeu.stats[it] = (jeu.stats[it] ?: 0) + 5 }
        jeu.ajouterXp(20)
        h.remove("annonce")
        val f = faits(jeu)
        if (c.lecons.all { it in f }) finirChapitre(jeu, c)
        else jeu.etape = leconId(jeu)?.let { prendrePas(jeu, it) } ?: 0
    }

    /** Un lieu du Terminaworld hors de la zone d'aventure (« / », « /home/explorateur ») : le chemin virtuel exact. */
    private fun absOk(jeu: Jeu, cwd: String?, lieu: String) = cwd != null && Racine.virtuel(jeu.home, cwd) == lieu

    private fun ouOk(jeu: Jeu, e: Etape, cwd: String?): Boolean = when {
        e.ou == null -> true
        e.ou.startsWith("/") -> absOk(jeu, cwd, e.ou)
        else -> Maison.dans(jeu, cwd, e.ou)
    }

    private fun iciOk(jeu: Jeu, e: Etape, cwd: String?): Boolean {
        val ici = e.ici ?: return false
        if (cwd == null) return false
        if (ici.startsWith("/")) return absOk(jeu, cwd, ici)
        return if (e.exact) Maison.rel(jeu, cwd) == ici else Maison.dans(jeu, cwd, ici)
    }

    private fun tickLecon(jeu: Jeu, tapees: List<Pair<String, String?>>) {
        // filet de sécurité : un chapitre dont toutes les leçons sont faites se termine (le suivant démarre)
        chapitreCourant(jeu)?.let { c -> if (c.lecons.all { it in faits(jeu) }) finirChapitre(jeu, c) }
        val les = leconCourante(jeu) ?: return
        if (jeu.niveau < les.niveau) return
        val h = h(jeu)
        if (h.optString("annonce") != les.id) {
            h.put("annonce", les.id)
            if (les.chap.id !in liste(h, "ouverts")) {
                ajouter(h, "ouverts", les.chap.id)
                jeu.log(t("hist.chapitre.log", "n" to les.chap.n, "chapitre" to nomChapitre(les.chap.id)))
                jeu.dire(dire(jeu, "hist.${les.chap.id}.debut"), 18)
            } else jeu.dire(t("lec.annonce"), 10)
            jeu.animer("parle")
        }
        val avant = les.id to jeu.etape
        for ((ligne, cwd) in tapees) {
            val e = les.etapes[jeu.etape]
            val ok = e.re?.containsMatchIn(ligne) == true && ouOk(jeu, e, cwd)
            if (ok || iciOk(jeu, e, cwd)) {
                if (!avancer(jeu, les)) { jeu.indiceLecon = null; return }
            }
        }
        // les étapes déjà faites (fichiers, dossier courant) passent toutes, jusqu'à la fin de la leçon s'il le faut
        for (k in les.etapes.indices) {
            val e = les.etapes[jeu.etape]
            if (e.fs?.invoke(jeu) != true && !iciOk(jeu, e, Maison.ici(jeu))) break
            if (!avancer(jeu, les)) { jeu.indiceLecon = null; return }
        }
        if (avant != (les.id to jeu.etape)) jeu.indiceLecon = null
        else if (tapees.isNotEmpty()) {
            val conseil = indice(jeu, les.etapes[jeu.etape], tapees)
            if (conseil != null && conseil != jeu.indiceLecon) {
                jeu.indiceLecon = conseil
                jeu.dire("💡 $conseil", 12)
            }
        }
    }

    /** Un indice quand c'est presque ça (mauvais endroit, faute de frappe, mauvais nombre…). */
    fun indice(jeu: Jeu, e: Etape, tapees: List<Pair<String, String?>>): String? {
        if (e.bravoCle == "hist.coeur2.2.bravo" && File(jeu.terrain, "coeur/reponse.txt").isFile) return t("hist.indice.nombre")
        if (e.ou != null && e.ou.startsWith("/") && e.re != null) {
            for ((l, cwd) in tapees) if (e.re.containsMatchIn(l) && !ouOk(jeu, e, cwd)) return t("hist.indice.racine", "cmd" to "cd /")
        }
        if (e.ou != null && !e.ou.startsWith("/") && e.re != null) {
            for ((l, cwd) in tapees) if (e.re.containsMatchIn(l) && !Maison.dans(jeu, cwd, e.ou)) {
                return t("hist.indice.piece", "piece" to Maison.nomPiece(if (e.ou.isNotEmpty()) e.ou else "grande_salle"),
                    "cmd" to "cd ~/${jeu.terrain.name}/${e.ou}".trimEnd('/'))
            }
        }
        if (e.ici != null) return null
        val lignes = tapees.map { it.first }
        indiceRm(jeu, e, tapees)?.let { return it }
        if (Indices.fauteDeFrappe(lignes, e.cmd, chiffres = true) == null) indiceChemin(jeu, e, tapees)?.let { return it }
        return Indices.lecon(jeu, e, lignes)
    }

    private val RECURSIF = Regex("^-\\w*[rR]")

    /** Le dossier visé par un mot tapé (relatif au dossier courant, ou ~/…). */
    private fun cible(jeu: Jeu, cwd: String?, mot: String): File = when {
        mot.startsWith("~/") -> File(jeu.home, mot.substring(2))
        mot.startsWith("/") -> File(mot)
        else -> File(cwd ?: jeu.home.path, mot)
    }

    /** rm sur une pièce (« rm debarras » échoue) ; rmdir sur une pièce pleine (« rmdir vieille_cabane » refuse). */
    private fun indiceRm(jeu: Jeu, e: Etape, tapees: List<Pair<String, String?>>): String? {
        for ((l, cwd) in tapees) {
            val mots = l.trim().split(Regex("\\s+"))
            val cmd = mots[0].lowercase()
            val args = mots.drop(1).filter { !it.startsWith("-") }
            if (cmd == "rm" && mots.drop(1).none { RECURSIF.containsMatchIn(it) }) {
                args.firstOrNull { cible(jeu, cwd, it).isDirectory }?.let { return t("hist.indice.rmdir", "nom" to it.trimEnd('/')) }
            }
            if (cmd == "rmdir" && e.cmd.startsWith("rm -r")) {
                args.firstOrNull { cible(jeu, cwd, it).list()?.isNotEmpty() == true }
                    ?.let { return t("hist.indice.plein", "nom" to it.trimEnd('/'), "cmd" to e.cmd) }
            }
        }
        return null
    }

    /**
     * Le fichier de l'étape n'est pas arrivé au bon endroit DANS le terrain (sinon Indices.lecon dit d'y aller) :
     * c'est devenu un dossier (mkdir nid/lit.txt), ou la commande a été tapée sans son chemin (touch lit.txt dans la
     * grande salle), ou depuis une autre pièce (touch nid/lit.txt dans le nid).
     */
    private fun indiceChemin(jeu: Jeu, e: Etape, tapees: List<Pair<String, String?>>): String? {
        val rel = e.cree ?: return null
        if ('/' !in rel || rel !in e.cmd || e.fs?.invoke(jeu) == true) return null
        val f = File(jeu.terrain, rel)
        if (f.isDirectory) return t("hist.indice.dossier", "nom" to f.name, "rel" to rel, "cmd" to e.cmd)
        val premier = e.cmd.split(" ")[0].lowercase()
        for ((l, cwd) in tapees) {
            if (l.trim().split(Regex("\\s+"))[0].lowercase() != premier) continue
            val r = Maison.rel(jeu, cwd) ?: continue
            return if (r.isEmpty()) t("hist.indice.chemin", "cmd" to e.cmd)
            else t("hist.indice.depuis", "terrain" to "cd ~/${jeu.terrain.name}", "cmd" to e.cmd)
        }
        return null
    }

    // ---------------------------------------------------------------- attirance du chapitre
    /** La famille du chapitre en cours, si sa commande a déjà été goûtée (sinon le serveur refuserait). */
    fun familleAttiree(jeu: Jeu): String? {
        val fam = chapitreCourant(jeu)?.famille ?: return null
        return if (Bestiaire.familles()[fam] in jeu.vus) fam else null
    }

    // ---------------------------------------------------------------- le carnet d'aventure
    /** Chaque nouvelle commande goûtée est rangée avec le moment de l'histoire où on l'a apprise. */
    fun noter(jeu: Jeu) {
        val carnet = h(jeu).getJSONObject("carnet")
        val c = chapitreCourant(jeu)
        val ou = c?.id ?: if (fini(jeu, "nid")) "libre" else "reveil"
        for (cmd in jeu.vus) if (!carnet.has(cmd)) carnet.put(cmd, ou)
    }

    /** Le moment de l'histoire où la commande a été apprise (carnet d'aventure), ou « ». */
    fun quand(jeu: Jeu, mot: String): String {
        val ou = jeu.extra.optJSONObject("histoire")?.optJSONObject("carnet")?.optString(mot)?.ifEmpty { null } ?: return ""
        if (ou == "avant" || ou == "libre") return t("hist.carnet.$ou")
        return t(cle("hist.$ou.court"))
    }

    /** Les souvenirs du carnet : chapitres réveillés, quêtes finies, titres, objets. */
    fun souvenirs(jeu: Jeu): List<String> {
        val q = Quetes.q(jeu)
        val out = mutableListOf("", t("lex.souvenirs"))
        val a = ailes(jeu)
        for (cid in a) out.add("  ✓ " + nomChapitre(cid))
        if (a.isEmpty()) out.add("  " + t("lex.souvenirs.aucun"))
        out.add("  " + t("lex.souvenirs.quetes", "n" to Quetes.liste(q, "finies").size))
        val titres = Quetes.liste(q, "titres")
        if (titres.isNotEmpty()) out.add("  " + t("lex.souvenirs.titres", "liste" to titres.joinToString(", ") { t("qu.titre.$it") }))
        val objets = Quetes.liste(q, "objets")
        if (objets.isNotEmpty()) out.add("  " + t("lex.souvenirs.objets", "liste" to objets.takeLast(12).joinToString(", ") { t("qu.objet.$it") }))
        return out
    }

    // ---------------------------------------------------------------- migration des anciennes sauvegardes
    /** les leçons d'avant que d'autres leçons de l'histoire remplacent */
    private val COUVRE = mapOf("systeme0" to listOf("cave0", "dortoir0"))
    private val BRANCHES = listOf("telephone", "systeme", "tuyaux", "scripts", "createur")

    /** Range la progression d'avant (tronc commun + arbre du téléphone) dans les chapitres, sans rien perdre. */
    fun migrer(jeu: Jeu) {
        val ancien = jeu.extra.optJSONObject("histoire")
        if (ancien != null && ancien.has("v")) return
        val L = jeu.lecon
        val s = jeu.etape
        val faits = mutableListOf<String>()
        val pas = JSONObject()
        fun fait(vararg ids: String) { for (x in ids) if (x !in faits) faits.add(x) }
        if (L >= 1) fait("t0")
        if (L >= 2) fait("reveil1", "nid0", "debarras")
        if (L >= 3) fait("nid1")
        if (L >= 4) fait("t3")
        if (L >= 5) fait("t4")
        var courant: String? = null
        when (L) {
            0 -> pas.put("t0", s)
            2 -> if (s <= 1) pas.put("nid1", s) else { fait("nid1"); pas.put("biblio1", 0) }   // le grep est la 1re étape de biblio1
            3 -> { pas.put("t3", s); courant = "cave" }
            4 -> { pas.put("t4", s); courant = "grenier" }
        }
        val arbre = jeu.extra.optJSONObject("arbre")
        val progres = arbre?.optJSONObject("progres")
        for (b in BRANCHES) {
            val n = progres?.optInt(b) ?: 0
            for (i in 0 until n) { val lid = "$b$i"; fait(*(COUVRE[lid] ?: listOf(lid)).toTypedArray()) }
        }
        val b = arbre?.optString("active")?.ifEmpty { null }
        if (b != null && b in BRANCHES && L >= 5) {
            val lid = "$b${progres?.optInt(b) ?: 0}"
            if (lid == "systeme0") {                              // whoami, id → la cave ; ps → le dortoir
                if (s >= 2) { fait("cave0"); pas.put("dortoir0", 1); courant = "dortoir" }
                else { if (s > 0) pas.put("cave0", s + 1); courant = "cave" }
            } else if (jeu.catalogue.containsKey(lid)) {
                if (s > 0) pas.put(lid, s)
                courant = chapitreDeLecon(lid)?.id ?: courant
            }
        }
        if ("nid1" in faits) fait("secrets")       // le tronc commun fini : l'exploration était déjà ouverte (v3)
        if ("reveil1" in faits) fait("racine")     // le chapitre 1 était fini (v4)
        if ("t3" in faits && "cave0" in faits) fait("gardien")
        val h = JSONObject().put("v", 2).put("chap", "reveil").put("faits", JSONArray(faits)).put("ailes", JSONArray())
            .put("pas", pas).put("ouverts", JSONArray()).put("carnet", JSONObject()).put("meubles", JSONArray())
            .put("suggere", JSONArray()).put("born", System.currentTimeMillis() / 1000)
        jeu.extra.put("histoire", h)
        val a = CHAPITRES.filter { c -> c.lecons.all { it in faits } }.map { it.id }
        h.put("ailes", JSONArray(a))
        mettreChap(jeu, when {
            !fini(jeu, "reveil") -> "reveil"
            !fini(jeu, "nid") -> "nid"
            courant != null && !fini(jeu, courant) -> courant
            else -> null
        })
        h.put("ouverts", JSONArray(a))
        jeu.etape = leconId(jeu)?.let { prendrePas(jeu, it) } ?: 0
        if (L >= 2 && !jeu.extra.has("maison")) jeu.extra.put("maison", JSONObject().put("visites", JSONArray(listOf("", "nid"))))
        val carnet = h.getJSONObject("carnet")
        for (cmd in jeu.vus) carnet.put(cmd, "avant")
    }

    // ---------------------------------------------------------------- à chaque tour de jeu
    /** Après une commande tapée (ligne), ou de temps en temps (ligne = null) ; cwd : le dossier courant du terminal. */
    fun tick(jeu: Jeu, ligne: String?, colle: Boolean, cwd: File? = null) {
        h(jeu)
        val tapees = Maison.suivre(jeu, ligne, colle, cwd)
        meubler(jeu)
        visiteAile(jeu, tapees.map { it.second } + Maison.ici(jeu))
        tickLecon(jeu, tapees)
        meubler(jeu)
        Quetes.tick(jeu, tapees)
        noter(jeu)
    }

    // ---------------------------------------------------------------- écrans
    /** Le menu des chapitres (aile, arbre). */
    fun lignesAiles(jeu: Jeu): List<String> {
        val out = mutableListOf("── 🏚 " + t("hist.menu.titre") + " ──", "")
        val f = faits(jeu)
        for (c in CHAPITRES) {
            val etat = when {
                fini(jeu, c.id) -> "✓ " + t("hist.menu.reveillee")
                chap(jeu) == c.id -> "▶ " + t("hist.menu.en_cours")
                ouvert(jeu, c.id) -> t("hist.menu.libre")
                c.id == "coeur" -> t("hist.coeur.ferme", "n" to nbAiles(jeu), "total" to AILES_POUR_LE_COEUR)
                else -> t("hist.menu.fermee")
            }
            val num = if (c.n > 0) "%2d".format(c.n) else " +"
            out.add("$num. ${Maison.ICONES[c.piece] ?: ""} ${nomChapitre(c.id)} (${c.lecons.count { it in f }}/${c.lecons.size} · ${c.piece}/)  $etat")
        }
        out.add("")
        out.add(t(cle("hist.menu.aide")))
        out.add(t("app.arbre.competences", "liste" to (if (jeu.skills.isEmpty()) t("app.arbre.aucune") else jeu.skills.joinToString(", ") { Regles.nomSkill(it) })))
        return out
    }

    /** Ce que l'écran principal montre quand il n'y a pas de leçon : (titre, texte) ou null. */
    fun bandeau(jeu: Jeu): Pair<String, String>? {
        if (chapitreCourant(jeu) != null) return null
        if (fini(jeu, "coeur")) return t("hist.fin.titre") to t(cle("hist.fin.suite"))
        if (fini(jeu, "nid")) return t("hist.choisir.titre") to t(cle("hist.choisir.aide"), "n" to nbAiles(jeu))
        return null
    }
}
