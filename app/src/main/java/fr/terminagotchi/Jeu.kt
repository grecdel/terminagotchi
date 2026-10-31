package fr.terminagotchi

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.sqrt

/**
 * Une étape de leçon : les textes sont des clés de langue (traduits au moment de l'affichage, avec le jargon du
 * palier, voir Histoire.tx). ou : la pièce où la commande doit être tapée ; ici : la pièce où il faut entrer
 * (exact : pas une de ses sous-pièces) ; expert : seulement à partir du niveau 10.
 */
class Etape(
    val ditCle: String,
    val cmd: String,
    val bravoCle: String,
    val re: Regex? = null,
    val fs: ((Jeu) -> Boolean)? = null,
    val astuceCle: String? = null,
    /** ce que crée l'étape (chemin dans le terrain) : pour repérer une bonne commande tapée au mauvais endroit */
    val cree: String? = null,
    val ou: String? = null,
    val ici: String? = null,
    val exact: Boolean = false,
    val expert: Boolean = false,
    val params: Map<String, String> = emptyMap(),
    /** la version « pour les grands » (G-32) ; par défaut la clé <étape>.adulte, à côté de <étape>.dit */
    val adulteCle: String? = null,
    /** l'étape veut voir un refus (le cadenas : `>>` sur un fichier protégé répond « Permission denied ») */
    val echoue: Boolean = false,
    /** le réseau peut manquer (école, avion) : avoir essayé la commande suffit, le jeu explique la réponse */
    val reseau: Boolean = false,
    /** `cd ..` : le lieu d'où l'on remonte jusqu'à « ici » (C1 : depuis le camp, `cd ..` ne mène pas au carrefour) */
    val depuis: String? = null,
) {
    val dit: String get() = Histoire.tx(ditCle, params)
    val bravo: String get() = Histoire.tx(bravoCle, params)
    val astuce: String? get() = astuceCle?.let { Histoire.tx(it, params) }
    /** « Pour les grands : … » (précis et technique, avec le parallèle du vrai terminal), ou null */
    val adulte: String? get() {
        val c = adulteCle ?: if (ditCle.endsWith(".dit")) ditCle.removeSuffix(".dit") + ".adulte" else return null
        if (!Langue.existe(Histoire.cle(c))) return null
        return t("grand.ligne", "texte" to Histoire.tx(c, params))
    }
}

/** Une commande du lexique : son image (la maison), son explication technique, sa section (clés de langue). */
class Mot(val cmd: String, private val imageCle: String, private val techniqueCle: String, val sectionCle: String) {
    val image: String get() = t(imageCle)
    val technique: String get() = t(techniqueCle)
    val section: String get() = t(sectionCle)
    /** commande d'ordinateur, absente du téléphone */
    val pc: Boolean get() = sectionCle == Regles.SECTION_PC
    /** les textes en français (la recherche les comprend toujours) et dans la langue choisie */
    fun textes(code: String) = listOfNotNull(Langue.brut(imageCle, code)?.toString(), Langue.brut(techniqueCle, code)?.toString())
}

class Lecon(val titreCle: String, val skill: String?, val niveau: Int, val etapes: List<Etape>) {
    val titre: String get() = Histoire.tx(titreCle)
}

/** Règles communes : catégories, compétences, textes, piège anti copier-coller. */
object Regles {
    /** identifiants des stats (en français dans la sauvegarde) ; à l'écran : t("stat.<id>") */
    val STATS = listOf("Intelligence", "Agilité", "Force", "Endurance")
    val COULEUR = mapOf("Intelligence" to 39, "Agilité" to 78, "Force" to 203, "Endurance" to 221)

    fun nomStat(s: String) = Langue.ou("stat.$s", s)
    fun court(s: String) = Langue.ou("stat.court.$s", s.take(3).uppercase())
    fun nomSkill(s: String) = Langue.ou("skill.$s", s)
    fun nomTrait(s: String) = Langue.ou("trait.$s", s)
    fun nomStade(n: Int) = t("stade.$n")
    fun nomForme(f: String?) = if (f == null) "" else Langue.ou("forme.$f", f)
    /** « Bébé », « Ado Hacker »… ; un compagnon espèce du bestiaire (especeC, son id) : « Bébé Gouttelin ». */
    fun espece(stade: Int, forme: String?, especeC: String? = null): String {
        val e = if (stade >= 1 && !especeC.isNullOrEmpty()) Bestiaire.espece(especeC) else null
        return if (e != null) t("forme.stade", "stade" to nomStade(stade), "forme" to e.nom)
        else if (stade >= 2 && forme != null) t("forme.stade", "stade" to nomStade(stade), "forme" to nomForme(forme)) else nomStade(stade)
    }

    val CATEGORIES: Map<String, Set<String>> = mapOf(
        "Intelligence" to setOf("git", "python", "python3", "sh", "bash", "alias", "vi", "nano", "awk", "sed"),
        "Agilité" to setOf("ping", "curl", "wget", "ip", "ifconfig", "netstat", "nslookup", "am", "pm",
            "applis", "ouvre", "web", "carte", "appelle", "sms", "partage", "lampe", "vibre", "batterie", "dis",
            "reglages"),
        "Force" to setOf("top", "ps", "kill", "df", "du", "free", "uname", "whoami", "date", "id", "getprop",
            "dumpsys", "uptime"),
        "Endurance" to setOf("ls", "cd", "cp", "mv", "rm", "mkdir", "rmdir", "cat", "touch", "find", "grep",
            "head", "tail", "chmod", "pwd", "echo", "stat", "more", "less", "wc", "sort", "tree"),
    )

    val SKILLS: Map<String, Set<String>> = mapOf(
        "Boussole" to setOf("cd", "ls", "pwd"),
        "Bâtisseur" to setOf("mkdir", "touch", "echo"),
        "Inspecteur" to setOf("cat", "grep", "head", "tail", "find", "more", "less"),
        "Gardien" to setOf("chmod"),
        "Nettoyeur" to setOf("cp", "mv", "rm"),
        "Télécommande" to setOf("lampe", "vibre", "batterie"),
        "Portier" to setOf("ouvre", "applis", "web", "carte"),
        "Messager" to setOf("dis", "partage", "sms", "appelle"),
        "Vigie" to setOf("whoami", "id", "ps"),
        "Intendant" to setOf("df", "du", "uptime"),
        "Détective" to setOf("uname", "getprop", "find"),
        "Plombier" to setOf("wc", "sort"),
        "Tamiseur" to setOf("grep"),
        "Cuistot" to setOf("sh"),
        "Inventeur" to setOf("echo"),
        "Créateur" to setOf("for", "if", "while"),
        "Apprenti" to setOf("doom"),
        "Architecte" to setOf("edite"),
        "Ingénieur" to setOf("doom", "edite"),
        // l'histoire « La Maison endormie » (Histoire.kt)
        "Explorateur" to setOf("tree", "find"),
        "Héros" to setOf("rev", "wc", "sort", "uniq"),
        "Chasseur" to setOf("ps", "date"),
        "Radar" to setOf("ping", "ip", "ifconfig"),
        "Facteur" to setOf("web", "hostname"),
    )

    /** les caractères (identifiants) et la clé de leurs phrases (Langue.liste) */
    val TRAITS = mapOf(
        "curieux" to "trait.curieux.phrases.tel",
        "farceur" to "trait.farceur.phrases",
        "gourmand" to "trait.gourmand.phrases.tel",
        "philosophe" to "trait.philosophe.phrases",
    )
    val FAIM = "core.faim"
    val OEUF = "core.oeuf"
    val COLLE = "core.colle.tel"

    /** Une phrase au hasard d'une liste de la langue choisie. */
    fun auHasard(cle: String) = Langue.liste(cle).random()

    // Lettres cyrilliques identiques à l'œil : une commande affichée puis collée ne fonctionne pas.
    private val HOMO = mapOf('a' to 'а', 'c' to 'с', 'e' to 'е', 'o' to 'о', 'p' to 'р', 'x' to 'х',
        'y' to 'у', 'i' to 'і', 's' to 'ѕ', 'd' to 'ԁ', 'h' to 'һ', 'j' to 'ј')
    private val PIEGES: Set<Char> = HOMO.values.toSet() + '\u00a0'

    fun piege(cmd: String): String {
        val sb = StringBuilder()
        var fait = false
        for (c in cmd) {
            val h = HOMO[c]
            when {
                !fait && h != null -> { sb.append(h); fait = true }
                c == ' ' -> sb.append('\u00a0')
                else -> sb.append(c)
            }
        }
        return sb.toString()
    }

    fun estColle(l: String) = l.any { it in PIEGES }
    fun niveau(xp: Int) = sqrt(xp / 10.0).toInt() + 1
    fun stade(n: Int) = when {
        n < 2 -> 0
        n < 5 -> 1
        n < 10 -> 2
        else -> 3
    }

    fun premierMot(l: String): String =
        l.trim().split(Regex("\\s+")).firstOrNull()?.lowercase()?.substringAfterLast('/') ?: ""

    /**
     * Le lexique : toutes les commandes utiles du terminal Android.
     * Fil rouge : l'ordinateur est un monde à explorer (le Terminaworld). Chaque commande a une image (le monde)
     * et une explication technique ; l'affichage suit le palier de vocabulaire (voir Mots.kt).
     * Les mêmes phrases existent sur PC (pc/tg/lexique.py).
     */
    const val SECTION_PC = "lexa.ch.pc"

    val LEXIQUE: List<Mot> = run {
        val f = "lex.ch.fichiers"
        val l = "lex.ch.lire"
        val y = "lex.ch.systeme"
        val tel = "lexa.ch.telephone"
        val c = "lexa.ch.creature"
        val j = "lexa.ch.jeux"
        val p = "lexa.ch.pc"
        val w = "lex.ch.recensement"
        val m = "lex.ch.maison"
        listOf(
            Mot("pwd", "lex.pwd.i", "lex.pwd.t", f),
            Mot("ls", "lexa.ls.i", "lexa.ls.t", f),
            Mot("cd", "lex.cd.i", "lex.cd.t", f),
            Mot("mkdir", "lex.mkdir.i", "lex.mkdir.t", f),
            Mot("touch", "lex.touch.i", "lex.touch.t", f),
            Mot("echo", "reg.img.echo", "lexa.echo.t", f),
            Mot("cp", "lexa.cp.i", "lexa.cp.t", f),
            Mot("mv", "lex.mv.i", "lex.mv.t", f),
            Mot("rm", "lexa.rm.i", "lexa.rm.t", f),
            Mot("rmdir", "reg.img.rmdir", "lexa.rmdir.t", f),
            Mot("chmod", "lexa.chmod.i", "lexa.chmod.t", f),
            Mot("rev", "lex.rev.i", "lex.rev.t", f),
            Mot("cat", "lex.cat.i", "lex.cat.t", l),
            Mot("head", "lex.head.i", "lex.head.t", l),
            Mot("tail", "reg.img.tail", "lexa.tail.t", l),
            Mot("grep", "lex.grep.i", "lexa.grep.t", l),
            Mot("find", "lexa.find.i", "lexa.find.t", l),
            Mot("wc", "lex.wc.i", "lexa.wc.t", l),
            Mot("sort", "lex.sort.i", "lexa.sort.t", l),
            Mot("stat", "lexa.stat.i", "lexa.stat.t", l),
            Mot("date", "lex.date.i", "lex.date.t", y),
            Mot("whoami", "lexa.whoami.i", "lexa.whoami.t", y),
            Mot("id", "lexa.id.i", "lexa.id.t", y),
            Mot("uptime", "lexa.uptime.i", "lexa.uptime.t", y),
            Mot("free", "lex.free.i", "lex.free.t", y),
            Mot("uname", "lexa.uname.i", "lexa.uname.t", y),
            Mot("df", "lexa.df.i", "lexa.df.t", y),
            Mot("du", "lexa.du.i", "lexa.du.t", y),
            Mot("ps", "lex.ps.i", "lexa.ps.t", y),
            Mot("ping", "lexa.ping.i", "lexa.ping.t", y),
            Mot("clear", "reg.img.clear", "lexa.clear.t", y),
            Mot("applis", "lexa.applis.i", "lexa.applis.t", tel),
            Mot("ouvre", "lex.ouvre.i", "lex.ouvre.t", tel),
            Mot("web", "lexa.web.i", "lexa.web.t", tel),
            Mot("carte", "lexa.carte.i", "lexa.carte.t", tel),
            Mot("appelle", "lexa.appelle.i", "lexa.appelle.t", tel),
            Mot("sms", "lexa.sms.i", "lexa.sms.t", tel),
            Mot("partage", "lexa.partage.i", "lexa.partage.t", tel),
            Mot("lampe", "lexa.lampe.i", "lexa.lampe.t", tel),
            Mot("vibre", "lexa.vibre.i", "lexa.vibre.t", tel),
            Mot("batterie", "reg.img.termux-battery-status", "lexa.batterie.t", tel),
            Mot("dis", "lexa.dis.i", "lexa.dis.t", tel),
            Mot("reglages", "lexa.reglages.i", "lexa.reglages.t", tel),
            Mot("caresse", "lex.caresse.i", "lex.caresse.i", c),
            Mot("danse", "lexa.danse.i", "lexa.danse.t", c),
            Mot("parle", "lexa.parle.i", "lexa.parle.t", c),
            Mot("joue", "lexa.joue.i", "lexa.joue.t", c),
            Mot("devine", "lexa.devine.i", "lexa.devine.t", c),
            Mot("etat", "lexa.etat.i", "lexa.etat.t", c),
            Mot("renomme", "lexa.renomme.i", "lexa.renomme.t", c),
            Mot("envies", "lex.tg_envies.i", "lex.tg_envies.t", c),
            Mot("cherche", "lexa.cherche.i", "lexa.cherche.t", j),
            Mot("collection", "lexa.collection.i", "lexa.collection.t", j),
            Mot("defi", "lexa.defi.i", "lexa.defi.t", j),
            Mot("donjon", "lexa.donjon.i", "lexa.donjon.t", j),
            Mot("plan", "lexa.plan.i", "lexa.plan.t", j),
            Mot("attaque", "lexa.attaque.i", "lexa.attaque.t", j),
            Mot("sac", "lexa.sac.i", "lexa.sac.t", j),
            Mot("equipe", "lexa.equipe.i", "lexa.equipe.t", j),
            Mot("bois", "lexa.bois.i", "lexa.bois.t", j),
            Mot("ctf", "lex.ctf.i", "lexa.ctf.t", j),
            Mot("drapeau", "lexa.drapeau.i", "lexa.drapeau.t", j),
            Mot("indice", "lexa.indice.i", "lexa.indice.t", j),
            Mot("edite", "lexa.edite.i", "lexa.edite.t", j),
            Mot("doom", "lexa.doom.i", "lexa.doom.t", j),
            Mot("langue", "lexa.langue.i", "lex.tg_langue.t", j),
            Mot("notifs", "lexa.notifs.i", "lexa.notifs.t", j),
            Mot("notif", "lexa.notif.i", "lexa.notif.t", j),
            Mot("compte", "lexa.compte.i", "lexa.compte.t", w),
            Mot("sync", "lexa.sync.i", "lexa.sync.t", w),
            Mot("site", "lexa.site.i", "lexa.site.t", w),
            Mot("bestiaire", "lexa.bestiaire.i", "lexa.bestiaire.t", j),
            Mot("troupe", "lexa.troupe.i", "lexa.troupe.t", j),
            Mot("anime", "lexa.anime.i", "lexa.anime.t", j),
            Mot("explique", "lex.explique.i", "lex.explique.t", j),
            Mot("carte", "lexa.maison.carte.i", "lexa.maison.carte.t", m),
            Mot("quetes", "lex.tg_quetes.i", "lex.tg_quetes.t", m),
            Mot("aile", "lexa.aile.i", "lexa.aile.t", m),
            Mot("sudo", "lexa.sudo.i", "lexa.sudo.t", p),
            Mot("apt", "lexa.apt.i", "lexa.apt.t", p),
            Mot("nano", "lexa.nano.i", "lexa.nano.t", p),
            Mot("git", "lexa.git.i", "lexa.git.t", p),
            Mot("python3", "lexa.python3.i", "lexa.python3.t", p),
            Mot("top", "lexa.top.i", "lexa.top.t", p),
            Mot("ssh", "lexa.ssh.i", "lexa.ssh.t", p),
        )
    }

    /** Le texte d'une commande du lexique selon le palier : l'image, puis l'image — la technique, puis la technique (l'image). */
    fun explication(m: Mot, palier: Int): String = when {
        palier <= 0 || m.image == m.technique -> m.image
        palier == 1 -> "${m.image} — ${m.technique}"
        else -> "${m.technique} (${m.image})"
    }

    fun barre(v: Double, max: Double, n: Int): String {
        val k = ((v / max) * n).toInt().coerceIn(0, n)
        return "▰".repeat(k) + "▱".repeat(n - k)
    }
}

/** L'état de la créature, sauvegardé en JSON dans le stockage privé de l'appli. */
class Jeu(ctx: Context) {
    companion object {
        /** langue choisie sur cet appareil (pour une nouvelle partie, qui n'a pas encore de sauvegarde) */
        @Volatile private var DEJA: String? = null

        /** quelle animation l'emporte quand plusieurs arrivent en même temps (comme core.PRIORITE_ANIM sur PC) */
        val PRIORITE_ANIM = mapOf("eclosion" to 10, "oeuf_1" to 3, "oeuf_2" to 3, "oeuf_3" to 3, "evolution" to 9, "victoire" to 8, "ko" to 7, "colere" to 6, "dort" to 6, "content" to 5,
            "confus" to 4, "mange" to 3, "salut" to 2, "parle" to 1)
    }

    init {
        Langue.init(ctx)
        Bestiaire.charger(ctx.applicationContext)
        Animations.init(ctx)
        Guide.init(ctx)
        Programme.init(ctx)
        Intro.init(ctx)
    }

    private val app: Context = ctx.applicationContext ?: ctx

    // chemin « canonique » : /data/user/0 et /data/data désignent le même dossier sur Android
    val home: File = File(ctx.filesDir, "maison").apply { mkdirs() }.canonicalFile
    /** le terrain de la partie ACTIVE (chaque partie a le sien, voir Parties.kt) */
    val terrain: File get() = File(home, "terrain_terminagotchi")

    /** identifiant de la partie (« 1 » = la sauvegarde d'avant les parties multiples, voir Parties.kt) */
    var partie = Parties.active(app)
    /** sans caractères de contrôle ni de mise en forme (ESC, NUL, RLO…), d'où qu'il vienne (saisie, sauvegarde, site) */
    var nom = ""
        set(v) { field = v.filter { c -> Character.getType(c).toByte() != Character.CONTROL && Character.getType(c).toByte() != Character.FORMAT }.trim() }
    var xp = 0
    var faim = 80.0
    var total = 0
    var dernierTick = System.currentTimeMillis()
    val stats = linkedMapOf<String, Int>().apply { Regles.STATS.forEach { put(it, 0) } }
    val vus = mutableSetOf<String>()
    val journal = mutableListOf<String>()
    val skills = mutableListOf<String>()
    var lecon = 0
    var etape = 0
    var forme: String? = null
    var trait = Regles.TRAITS.keys.random()
    var bulle = ""
    var bulleFin = 0L
    /** phrases en attente : la créature ne se coupe jamais la parole (texte, secondes) */
    val bulles = mutableListOf<Pair<String, Int>>()
    /** dernière courte animation demandée pour la créature (nom, date en ms) : l'écran la joue */
    var anim: Pair<String, Long>? = null
    var colles = 0
    /** créature shiny : plus jamais à la naissance (le compagnon n'a pas de rareté) ; gardé pour les anciennes sauvegardes */
    var shiny = false
    /** langue de l'interface (enregistrée dans la sauvegarde ; au premier lancement : celle du téléphone) */
    var langue = Langue.courante
    private val dernierJeu = mutableMapOf<String, Long>()
    val historique = mutableListOf<String>()

    /** Données des modules (arbre, exploration, donjon, ctf, défis…), sauvegardées telles quelles. */
    var extra = JSONObject()

    /** Sous-objet d'un module, créé à la demande. */
    fun module(nom: String): JSONObject = extra.optJSONObject(nom) ?: JSONObject().also { extra.put(nom, it) }

    val branches: Map<String, Branche> by lazy { Arbre.creer(this) }

    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)

    val lecons: List<Lecon> = listOf(
        Lecon("lec.t0.titre", "Boussole", 1, listOf(
            Etape("lec.t0.0.dit", "pwd",
                "lec.t0.0.bravo", re = r("^pwd\\b")),
            Etape("lec.t0.1.dit", "ls",
                "lec.t0.1.bravo", re = r("^ls\\b")),
            Etape("lec.t0.2.dit", "cd ~",
                "lec.t0.2.bravo", re = r("^cd(\\s+~/?)?\\s*$"),
                astuceCle = "leca.t0.2.astuce"),
        )),
        Lecon("lec.t1.titre", "Bâtisseur", 1, listOf(
            Etape("lec.t1.0.dit", "mkdir terrain_terminagotchi",
                "lec.t1.0.bravo", fs = { it.terrain.isDirectory }),
            Etape("lec.t1.1.dit", "cd terrain_terminagotchi",
                "lec.t1.1.bravo",
                re = r("^cd\\s+.*terrain_terminagotchi")),
            Etape("lec.t1.2.dit", "mkdir nid",
                "lec.t1.2.bravo",
                fs = { File(it.terrain, "nid").isDirectory }, cree = "nid"),
        )),
        Lecon("lec.t2.titre", "Inspecteur", 1, listOf(
            Etape("lec.t2.0.dit", "echo pomme > nid/repas.txt",
                "lec.t2.0.bravo",
                fs = { Indices.contient(File(it.terrain, "nid/repas.txt"), "pomme") }, cree = "nid/repas.txt"),
            Etape("lec.t2.1.dit", "cat nid/repas.txt",
                "lec.t2.1.bravo", re = r("^(cat|more|less|head)\\b.*repas")),
            Etape("lec.t2.2.dit", "grep pomme nid/repas.txt",
                "lec.t2.2.bravo", re = r("^grep\\b.*pomme")),
        )),
        Lecon("lec.t3.titre", "Gardien", 1, listOf(
            Etape("lec.t3.0.dit", "ls -l nid",
                "lec.t3.0.bravo", re = r(Verif.LS_L)),
            Etape("lec.t3.1.dit", "chmod 444 nid/repas.txt",
                "lec.t3.1.bravo",
                fs = { val f = File(it.terrain, "nid/repas.txt"); f.isFile && !f.canWrite() }),
            Etape("lec.t3.2.dit", "echo poire >> nid/repas.txt",
                "lec.t3.2.bravo", re = r(Verif.ajoute("repas")), echoue = true),
        )),
        Lecon("lec.t4.titre", "Nettoyeur", 1, listOf(
            Etape("lec.t4.0.dit", "cp nid/repas.txt nid/secours.txt",
                "lec.t4.0.bravo", fs = { File(it.terrain, "nid/secours.txt").isFile }, cree = "nid/secours.txt"),
            Etape("lec.t4.1.dit", "mv nid/secours.txt reserve.txt",
                "lec.t4.1.bravo", fs = { File(it.terrain, "reserve.txt").isFile }, cree = "reserve.txt"),
            Etape("lec.t4.2.dit", "rm reserve.txt",
                "lec.t4.2.bravo",
                fs = { !File(it.terrain, "reserve.txt").exists() }),
        )),
    )

    /** Ce qui s'est passé au chargement (sauvegarde modifiée hors du jeu, abîmée…), dit une fois par la créature. */
    var alerteChargement: String? = null

    init {
        charger()
    }

    val existe: Boolean get() = nom.isNotEmpty()
    /** l'espèce du compagnon (id du bestiaire, tirée avec l'œuf : Oeufs.choisir), null pour une partie d'avant */
    val especeCompagnon: String? get() = extra.optString("espece_compagnon").takeIf { it.isNotEmpty() }
    val niveau: Int get() = Regles.niveau(xp)
    val stade: Int get() = Regles.stade(niveau)

    // ------------------------------------------------------------ sauvegarde
    /**
     * Relit la sauvegarde active (une autre partie de l'appli, comme le Doom, a pu la modifier,
     * ou l'écran d'accueil a changé de partie) : tout repart des valeurs de départ, puis du fichier.
     */
    fun recharger() {
        nom = ""
        xp = 0
        faim = 80.0
        total = 0
        dernierTick = System.currentTimeMillis()
        vus.clear()
        journal.clear()
        skills.clear()
        historique.clear()
        lecon = 0
        etape = 0
        forme = null
        trait = Regles.TRAITS.keys.random()
        bulle = ""
        bulleFin = 0L
        bulles.clear()
        anim = null
        colles = 0
        shiny = false
        dernierJeu.clear()
        extra = JSONObject()
        Regles.STATS.forEach { stats[it] = 0 }
        partie = Parties.active(app)
        langue = Langue.courante
        charger()
    }

    /**
     * La sauvegarde active, vérifiée : son sceau (Garde) doit être bon, sinon (modifiée hors du jeu, abîmée) on prend
     * la copie de secours scellée (sauvegarde.json.bak) ; sans bonne copie, on garde quand même la créature (jamais
     * effacée), et on le dit. Le fichier refusé est rangé à côté (sauvegarde.json.refusee), jamais effacé.
     */
    private fun lireVerifie(fichier: File): JSONObject? {
        val bak = File(fichier.parentFile, fichier.name + ".bak")
        fun essai(f: File): Pair<JSONObject?, Boolean> = try {
            val txt = f.readText()
            val o = JSONObject(txt)
            o to Garde.acceptable(txt)
        } catch (e: Exception) { null to false }
        val (o, bon) = essai(fichier)
        if (o != null && bon) return o
        val (b, bbon) = if (bak.isFile) essai(bak) else (null to false)
        if (b != null && bbon) {
            try { fichier.copyTo(File(fichier.parentFile, fichier.name + ".refusee"), overwrite = true) } catch (e: Exception) {}
            alerteChargement = if (o == null) "garde.illisible" else "garde.sceau"
            return b
        }
        if (o != null) { alerteChargement = "garde.sceau.sans"; return o }
        if (b != null) { alerteChargement = "garde.illisible"; return b }
        if (fichier.exists()) alerteChargement = "garde.perdue"
        return null
    }

    private fun charger() {
        val fichier = Parties.fichierActif(app)
        if (!fichier.exists() && !File(fichier.parentFile, fichier.name + ".bak").isFile) { choisirLangue(null); return }
        try {
            val o = lireVerifie(fichier) ?: throw IllegalStateException("sauvegarde illisible")
            partie = o.optString("partie").ifEmpty { partie }
            nom = o.optString("nom")
            xp = o.optInt("xp")
            faim = o.optDouble("faim", 80.0)
            total = o.optInt("total")
            dernierTick = o.optLong("dernierTick", dernierTick)
            o.optJSONObject("stats")?.let { s -> Regles.STATS.forEach { stats[it] = s.optInt(it) } }
            o.optJSONArray("vus")?.let { a -> for (i in 0 until a.length()) vus.add(a.getString(i)) }
            o.optJSONArray("journal")?.let { a -> for (i in 0 until a.length()) journal.add(a.getString(i)) }
            o.optJSONArray("skills")?.let { a -> for (i in 0 until a.length()) skills.add(a.getString(i)) }
            o.optJSONArray("historique")?.let { a -> for (i in 0 until a.length()) historique.add(a.getString(i)) }
            lecon = o.optInt("lecon")
            etape = o.optInt("etape")
            forme = if (o.has("forme") && !o.isNull("forme")) o.getString("forme") else null
            trait = o.optString("trait", trait)
            bulle = o.optString("bulle")
            bulleFin = o.optLong("bulleFin")
            bulles.clear()
            o.optJSONArray("bulles")?.let { a ->
                for (i in 0 until a.length()) a.optJSONArray(i)?.let { b -> bulles.add(b.optString(0) to b.optInt(1, 8)) }
            }
            anim = o.optJSONArray("anim")?.let { a -> a.optString(0) to a.optLong(1) }
            colles = o.optInt("colles")
            shiny = o.optBoolean("shiny")
            extra = o.optJSONObject("extra") ?: JSONObject()
            Bestiaire.migrer(extra)          // anciennes espèces → nouveau bestiaire, « finale » → « ancien »
            choisirLangue(o.optString("langue").ifEmpty { null })
        } catch (e: Exception) {
            // sauvegarde illisible et sans copie de secours : rangée à côté (jamais effacée), puis on repart de zéro
            try { fichier.copyTo(File(fichier.parentFile, fichier.name + ".refusee"), overwrite = true) } catch (x: Exception) {}
            choisirLangue(null)
        }
        alerteChargement?.let { k ->
            log(t(k))
            dire(t(k), 14)
        }
    }

    /**
     * La langue de cette partie : celle de la sauvegarde ; sinon (premier lancement, nouvelle partie) celle déjà
     * choisie sur l'appareil, sinon celle du téléphone.
     */
    private fun choisirLangue(enregistree: String?) {
        langue = Langue.definir(enregistree ?: dejaChoisie ?: Langue.detecter())
        dejaChoisie = langue
    }

    /** Change la langue (commande « langue xx ») : elle est enregistrée dans la sauvegarde. */
    fun changerLangue(code: String) {
        langue = Langue.definir(code)
        dejaChoisie = langue
        try { app.getSharedPreferences("terminagotchi", Context.MODE_PRIVATE).edit().putString("langue", langue).apply() } catch (e: Exception) { }
    }

    private var dejaChoisie: String?
        get() = DEJA ?: try { app.getSharedPreferences("terminagotchi", Context.MODE_PRIVATE).getString("langue", null) } catch (e: Exception) { null }
        set(v) { DEJA = v }

    fun sauver() {
        val o = JSONObject()
        o.put("langue", langue)
        o.put("nom", nom)
        o.put("xp", xp)
        o.put("faim", faim)
        o.put("total", total)
        o.put("dernierTick", dernierTick)
        o.put("stats", JSONObject(stats.toMap()))
        o.put("vus", JSONArray(vus.toList()))
        o.put("journal", JSONArray(journal))
        o.put("skills", JSONArray(skills))
        o.put("historique", JSONArray(historique))
        o.put("lecon", lecon)
        o.put("etape", etape)
        o.put("forme", forme ?: JSONObject.NULL)
        o.put("trait", trait)
        o.put("bulle", bulle)
        o.put("bulleFin", bulleFin)
        o.put("bulles", JSONArray(bulles.map { JSONArray().put(it.first).put(it.second) }))
        anim?.let { o.put("anim", JSONArray().put(it.first).put(it.second)) }
        o.put("colles", colles)
        o.put("shiny", shiny)
        o.put("extra", extra)
        o.put("partie", partie)
        o.put("maj", System.currentTimeMillis())
        // si l'écran d'accueil a changé de partie entre-temps (rappel en arrière-plan…),
        // cette créature s'enregistre dans SON rangement et n'écrase pas la nouvelle partie active
        val fichier = Parties.fichierDe(app, partie)
        // scellée (Garde : une sauvegarde modifiée hors du jeu est reconnue), avec sa copie de secours scellée
        val texte = Garde.sceller(o)
        Parties.ecrireTexte(fichier, texte)
        if (fichier == Parties.fichierActif(app)) Parties.ecrireTexte(File(fichier.parentFile, fichier.name + ".bak"), texte)
    }

    // ------------------------------------------------------------ vie de la créature
    fun log(msg: String) {
        val heure = SimpleDateFormat("HH:mm", Locale.FRANCE).format(Date())
        journal.add("$heure $msg")
        while (journal.size > 6) journal.removeAt(0)
    }

    /** La créature parle. Si elle parle déjà, la phrase attend son tour (rien n'est écrasé). */
    fun dire(texte: String, secondes: Int = 8) {
        if (System.currentTimeMillis() < bulleFin && bulle.isNotEmpty() && bulle != texte) {
            if (bulles.none { it.first == texte }) {
                bulles.add(texte to secondes)
                while (bulles.size > 4) bulles.removeAt(0)
            }
            return
        }
        bulle = texte
        bulleFin = System.currentTimeMillis() + secondes * 1000L
    }

    /** La phrase à afficher maintenant (passe à la suivante de la file quand la précédente est lue). */
    fun bulleActive(): String {
        val now = System.currentTimeMillis()
        if (now >= bulleFin && bulles.isNotEmpty()) {
            val (t, sec) = bulles.removeAt(0)
            bulle = t
            bulleFin = now + sec * 1000L
        }
        return if (now < bulleFin) bulle else ""
    }

    /** Demande une courte animation de la créature (la plus importante gagne si plusieurs arrivent ensemble). */
    fun animer(nom: String) {
        val now = System.currentTimeMillis()
        val a = anim
        if (a != null && now - a.second < 2000 && (PRIORITE_ANIM[a.first] ?: 0) > (PRIORITE_ANIM[nom] ?: 0)) return
        anim = nom to now
    }

    fun dominant(): String =
        if (stats.values.all { it == 0 }) Regles.STATS.random() else stats.maxByOrNull { it.value }!!.key

    /** la dernière notification de la faim (« j'ai faim », « en veille ») : l'écran la montre une fois */
    var notifFaim: String? = null

    fun tick() {
        // la faim ne baisse que de 7 h à 21 h, 3 fois plus lentement qu'avant, rien en vacances (Satiete.kt) ;
        // l'horloge qui recule (réglage du téléphone) ne nourrit pas : faim entre 0 et 100
        if (existe) Satiete.tick(this)?.let { notifFaim = it } else dernierTick = System.currentTimeMillis()
        Envies.temps(this)                  // les autres envies : usure lente, repos, poussière du terrain
    }

    fun ajouterXp(n: Int) {
        val avant = niveau
        val xpAvant = xp
        xp += n
        if (Intro.retient(this)) xp = minOf(xp, 9)         // l'œuf n'éclot qu'à la fin de sa liste de commandes (Intro.kt)
        if (existe) Satiete.retenir(this, xpAvant)          // grandir demande aussi des jours soignés (l'XP en trop attend)
        val apres = niveau
        if (apres <= avant) return
        animer(if (Regles.stade(apres) > Regles.stade(avant)) "evolution" else "content")
        if (Regles.stade(apres) > Regles.stade(avant)) {
            if (Regles.stade(apres) == 1) {
                log(t("core.eclot.log"))
                dire(t("core.eclot.dit"), 10)
            } else {
                if (forme == null) forme = dominant()
                log(t("core.evolution.log", "forme" to Regles.espece(Regles.stade(apres), forme, especeCompagnon)))
                dire(t("core.evolution.dit"), 10)
            }
        } else {
            log(t("core.niveau.log", "n" to apres))
        }
        val l = Histoire.leconCourante(this)
        if (l != null && l.niveau == apres) { dire(t("lec.annonce"), 10); animer("parle") }
    }

    /** une commande répétée dans les 10 dernières ne donne plus d'XP (anti-remplissage) */
    val FENETRE_REPAS = 10

    /** Mange une commande. Renvoie false si elle a été refusée (collée). */
    fun manger(ligne: String, colle: Boolean, rappel: Boolean = false, code: Int? = null): Boolean {
        if (colle || Regles.estColle(ligne)) {
            colles++
            log(t("core.colle.log"))
            dire(Regles.auHasard(Regles.COLLE), 10)
            animer("colere")
            return false
        }
        val cmd = Regles.premierMot(ligne)
        if (cmd.isEmpty()) return false
        if (rappel) {
            log(t("jeu.mange.rappel", "cmd" to cmd))
            return false
        }
        // v3 : une fonction du jeu « pas encore » ouverte (aura, envies…) ne nourrit pas et ne donne pas d'XP
        if (Intro.bloque(this, cmd, ligne.trim().substringAfter(' ', "").trim()) != null) return false
        if (code != null && code != 0) {        // la commande a échoué : elle nourrit à peine, sans XP ni nouveau goût (G-34)
            Satiete.repas(this, cmd, ratee = true)
            log(t("core.rate.log", "cmd" to cmd))
            animer("confus")
            return false
        }
        total++
        // anti-remplissage (G-04) : une commande déjà goûtée parmi les FENETRE_REPAS dernières nourrit, mais ne donne
        // ni XP ni stat (les niveaux viennent des leçons, des chapitres, des exercices et des commandes nouvelles)
        val repas = module("repas")
        val derniers = repas.optJSONArray("derniers")?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: emptyList()
        repas.put("derniers", org.json.JSONArray((derniers + cmd).takeLast(FENETRE_REPAS)))
        if (cmd in derniers && cmd in vus) {
            Satiete.repas(this, cmd, repetee = true)          // la même commande de suite : elle nourrit à peine
            module("compte").put("repas", System.currentTimeMillis())
            log(t("core.mange", "cmd" to cmd))
            animer("mange")
            return true
        }
        var gain = 1
        var msg = t("core.mange", "cmd" to cmd)
        val stat = Regles.CATEGORIES.entries.firstOrNull { cmd in it.value }?.key
        if (stat != null) {
            stats[stat] = (stats[stat] ?: 0) + 1
            gain += 1
            if (Mots.palier(this) >= 1) msg += " +${Regles.court(stat)}"     // « +END » : du jargon pour un débutant (P2-5)
        }
        if (cmd in Commandes.CREATURE) {
            val maintenant = System.currentTimeMillis()
            if (maintenant - (dernierJeu[cmd] ?: 0L) < 60_000) {
                Satiete.repas(this, cmd, repetee = true)
                log(msg + t("jeu.mange.deja_joue"))
                return true
            }
            dernierJeu[cmd] = maintenant
        }
        val nouvelle = vus.add(cmd)
        if (nouvelle) {
            gain += 5
            msg += t("core.mange.nouveau")
        }
        if (skills.any { Regles.SKILLS[it]?.contains(cmd) == true }) {
            gain *= 2
            msg += " ×2"
        }
        Satiete.repas(this, cmd, nouvelle = nouvelle)      // l'aliment de sa famille (nouveau goût, assiette, veille)
        module("compte").put("repas", System.currentTimeMillis())
        log(msg)
        animer("mange")
        Satiete.gagnerXp(this, gain)                       // +20 % rassasiée, −20 % affamée (Satiete.kt)
        return true
    }

    /** Toutes les leçons (tronc, branches du téléphone, leçons de l'histoire), par identifiant (voir Histoire). */
    val catalogue: Map<String, Lecon> by lazy { Histoire.catalogue(this) }

    /** (compatibilité) les deux premiers chapitres sont finis : la maison est libre. */
    val troncFini: Boolean get() = Histoire.fini(this, "nid")

    /** l'étape à faire maintenant (null s'il n'y a pas de leçon, ou si le niveau n'est pas encore atteint) */
    fun etapeCourante(): Etape? {
        val c = Histoire.leconCourante(this) ?: return null
        return if (niveau >= c.niveau) c.etapes[etape] else null
    }

    /** l'indice « presque ! » de l'étape en cours (affiché sous la leçon), ou null */
    var indiceLecon: String?
        get() = module("lecons").optString("indice").ifEmpty { null }
        set(v) { if (v == null) module("lecons").remove("indice") else module("lecons").put("indice", v) }

    fun parlerSiSilencieux() {
        if (bulleActive().isNotEmpty()) return
        when {
            stade == 0 -> dire(Regles.auHasard(Regles.OEUF))
            // le lien : ses phrases à elle (après quelques jours soignés)
            Satiete.lien(this) >= Satiete.LIEN_PHRASES && kotlin.random.Random.nextDouble() < 0.3 ->
                dire(Langue.auHasard("sat.lien.phrases", "nom" to nom))
            // la faim et les autres envies passent par Envies.kt (rappels espacés)
            else -> dire(Regles.TRAITS[trait]?.let { Regles.auHasard(it) } ?: "…")
        }
    }

    // ------------------------------------------------------------ textes affichés
    /** l'humeur combine les 6 envies (la faim d'abord), voir Envies.humeurCle */
    fun humeur() = t(Envies.humeurCle(this))

    fun titre(): String {
        return "$nom${if (shiny) " ✨" else ""} · " + t("app.forme_niveau", "forme" to Regles.espece(stade, forme, especeCompagnon), "n" to niveau) +
            Entrainement.titreTexte(this).let { if (it.isEmpty()) "" else " $it" }      // le titre de la salle d'entraînement
    }

    fun texteXp(): String {
        val lo = 10 * (niveau - 1) * (niveau - 1)
        val hi = 10 * niveau * niveau
        return Langue.ajuster(t("app.xp"), 5) + "${Regles.barre((xp - lo).toDouble(), (hi - lo).toDouble(), 8)}  $xp/$hi"
    }

    fun texteFaim() = Langue.ajuster(t("app.faim"), 5) + "${Regles.barre(faim, 100.0, 8)}  ${humeur()}"

    fun texteStats() = Regles.STATS.joinToString("  ") { "${Regles.court(it)} ${stats[it]}" }

    /**
     * Le panneau de la leçon (comme l'écran principal du PC) : le chapitre, la leçon et son étape ; sans leçon,
     * le choix de l'aile (ou la fin) ; puis la quête suivie.
     */
    fun texteLecon(): String? {
        val out = mutableListOf<String>()
        val c = Histoire.leconCourante(this)
        if (Placement.actif(this)) out.add("🧩 " + Placement.but(this))          // G-13 : le test « je connais déjà »
        if (c != null) {
            out.add(t("hist.ecran.chapitre", "icone" to (Maison.ICONES[c.chap.piece] ?: "📖"),
                "chapitre" to Histoire.nomChapitre(c.chap.id), "n" to c.chap.n) + " · " + c.etiquette)
            if (Placement.actif(this)) {
                // I2 : pendant le test « je connais déjà », seul le défi est montré (pas la commande de la leçon)
            } else if (niveau < c.niveau) {
                val manque = 10 * (c.niveau - 1) * (c.niveau - 1) - xp
                out.add(t("leca.prochaine", "n" to c.niveau, "xp" to manque))
            } else {
                val e = c.etapes[etape]
                if (c.id == "t0" && etape == 0 && Placement.etat(this).isEmpty()) out.add("🧩 " + t("plac.propose.tel"))
                out.add("${c.titre} (${etape + 1}/${c.etapes.size}) · ${e.dit}\n➜ ${Verif.commandeMontree(this, e)}")
                val cachee = Placement.cache(this, e)                           // I2 : mode sans aide, rien ne la donne
                if (!cachee) {
                    e.adulte?.let { out.add("🧑 $it") }                          // G-32 : la version des grands, toujours là
                    Vrai.ligne(e.cmd)?.let { out.add(it) }                       // G-10 : 💻 et dans un vrai terminal ?
                    for ((montre, cle) in Explique.nouvelles(this, e.cmd))      // 💡 Le -r veut dire… (+ pour les grands)
                        Explique.phrases(this, montre, cle).forEachIndexed { k, p -> out.add("  ".repeat(k) + p) }
                }
                Verif.lieuAttendu(this, e)?.let { lieu ->                      // 📁 d'où la commande marche (calculé, G-34)
                    out.add(t("app.lecon.depuis", "terrain" to (if (lieu.isEmpty()) Mots.terme("terrain", Mots.palier(this))
                        else Maison.nomPiece(lieu.substringBefore('/'))), "cmd" to Verif.cdVers(this, lieu)))
                }
                if (!cachee) e.astuce?.let { out.add(it) }
                indiceLecon?.let { out.add("💡 $it") }
            }
        } else {
            Histoire.bandeau(this)?.let { out.add(it.first + "\n" + it.second) }
        }
        Quetes.ligneSuivie(this)?.let { out.add(it) }
        return out.joinToString("\n").ifEmpty { null }
    }

    fun infoWidget(): String {
        val b = bulleActive()
        if (b.isNotEmpty()) return "« $b »"
        if (Intro.retient(this)) return "🥚 " + Intro.titreListe(this)     // l'œuf : sa liste de commandes
        val e = etapeCourante()
        if (e != null) return t("widget.lecon", "cmd" to Regles.piege(e.cmd))
        if (Intro.ouvert(this, "envies")) Envies.phrase(this)?.let { return "💭 $it" }      // l'envie du moment
        return journal.lastOrNull()?.drop(6) ?: t("widget.nourris")
    }
}
