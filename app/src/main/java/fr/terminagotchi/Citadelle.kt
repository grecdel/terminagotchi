package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.nio.file.Files
import java.nio.file.attribute.PosixFilePermissions
import java.security.MessageDigest
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.PBEKeySpec
import javax.crypto.spec.SecretKeySpec
import kotlin.math.ln

/**
 * 🛡 La Citadelle — cybersécurité DÉFENSIVE (docs/programme.md § 2.11 et § 7.5), portage de pc/tg/citadelle.py.
 *
 * Mêmes règles que sur PC (journal du gardien, chmod et umask, drapeaux des boîtes, faux facteur, force des phrases de
 * passe, inspecteur, tableau de garde) : vecteurs communs donnees/citadelle/vecteurs.json, vérifiés par
 * tests/jvm/Citadelle.kt. Toutes les attaques sont FAUSSES et restent dans terrain_terminagotchi/citadelle/.
 *
 * Sur le téléphone, le shell (toybox) fait le vrai travail (chmod, find, grep, cut, sort, uniq, sha256sum, tar), et
 * des commandes intégrées (Commandes.kt) remplacent ce qui manque, sans jamais sortir du terrain :
 *  - `openssl enc -aes-256-cbc -pbkdf2 [-d] -in … [-out …] -pass pass:…` : le même format que le vrai openssl
 *    (« Salted__ », sel de 8 octets, PBKDF2-HMAC-SHA256 10 000 tours, AES-256-CBC) ;
 *  - `diff a b` (format normal de diff), `shuf -n N fichier` ;
 *  - les processus fantômes sont SIMULÉS (le shell du téléphone arrête tout ce qu'une commande lance) : `citadelle ps`
 *    les montre, `kill PID` les arrête (seulement eux : un autre numéro part au vrai shell) ;
 *  - `citadelle …` : cadenas, chown simulé, masque, tableau, facteur, force, phrase, boîtes, drapeau, inspecteur,
 *    rotation, vague.
 */
object Citadelle {
    @Volatile var chargeur: (() -> String?)? = null
    private var d: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("citadelle.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun donnees(): JSONObject = d ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() }).also { d = it }

    private fun liste(o: JSONObject?, k: String): List<String> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.get(it).toString() } } ?: emptyList()
    private fun objets(o: JSONObject?, k: String): List<JSONObject> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.getJSONObject(it) } } ?: emptyList()

    // ---------------------------------------------------------------- la spécification pure (vecteurs communs)
    /** Le registre du gardien (journaux/acces.log), comme journal() sur PC. */
    fun journal(): List<String> {
        val j = donnees().optJSONObject("journal") ?: return emptyList()
        val (h, m, s) = j.optString("debut", "06:00:00").split(":").map { it.toInt() }
        val t0 = h * 3600 + m * 60 + s
        val vis = liste(j, "visiteurs"); val noms = liste(j, "noms"); val portes = liste(j, "portes")
        val inoms = liste(j, "intrus_noms"); val err = liste(j, "erreurs_visiteurs").map { it.toInt() }
        val de = j.optInt("intrus_de"); val a = j.optInt("intrus_a")
        return (0 until j.optInt("lignes")).map { i ->
            val ts = t0 + i * j.optInt("pas_secondes")
            val heure = "%02d:%02d:%02d".format(ts / 3600, ts % 3600 / 60, ts % 60)
            val (res, adr, porte, nom) = when {
                i in de until a -> listOf("ECHEC", j.optString("intrus"), j.optString("intrus_porte"), inoms[i % inoms.size])
                i == a -> listOf("OK", j.optString("intrus"), j.optString("intrus_porte"), "invite")
                else -> { val k = i % vis.size; listOf(if (i in err) "ECHEC" else "OK", vis[k], portes[k], noms[k]) }
            }
            "${j.optString("date")} $heure $res $adr $porte $nom"
        }
    }

    fun echecs(): Map<String, Int> {
        val c = LinkedHashMap<String, Int>()
        for (l in journal()) { val m = l.split(" "); if (m[2] == "ECHEC") c[m[3]] = (c[m[3]] ?: 0) + 1 }
        return c
    }

    fun intrus() = donnees().optJSONObject("journal")?.optString("intrus") ?: ""

    fun modeTexte(mode: Int): String = buildString {
        for (dec in listOf(6, 3, 0)) {
            val b = (mode shr dec) and 7
            append(if (b and 4 != 0) 'r' else '-'); append(if (b and 2 != 0) 'w' else '-'); append(if (b and 1 != 0) 'x' else '-')
        }
    }

    /** Le mode après `chmod spec` (octal ou symbolique, comme GNU chmod), ou null. */
    fun chmodMode(spec0: String, actuel: Int, masque: Int = "022".toInt(8)): Int? {
        val spec = spec0.trim()
        if (Regex("[0-7]{1,4}").matches(spec)) return spec.toInt(8) and "777".toInt(8)
        var mode = actuel and "777".toInt(8)
        for (clause in spec.split(",")) {
            val m = Regex("([ugoa]*)((?:[-+=][rwx]*)+)").matchEntire(clause) ?: return null
            var qui = m.groupValues[1]
            val filtre: Int
            if (qui.isEmpty()) { filtre = "777".toInt(8) and masque.inv(); qui = "a" } else filtre = "777".toInt(8)
            var cibles = 0
            for (q in qui) cibles = cibles or when (q) { 'u' -> "700".toInt(8); 'g' -> "070".toInt(8); 'o' -> "007".toInt(8); else -> "777".toInt(8) }
            for (op in Regex("([-+=])([rwx]*)").findAll(m.groupValues[2])) {
                var bits = 0
                for (p in op.groupValues[2]) bits = bits or when (p) { 'r' -> "444".toInt(8); 'w' -> "222".toInt(8); else -> "111".toInt(8) }
                bits = bits and cibles and filtre
                mode = when (op.groupValues[1]) {
                    "+" -> mode or bits
                    "-" -> mode and bits.inv()
                    else -> (mode and (cibles and filtre).inv()) or bits
                }
            }
        }
        return mode and "777".toInt(8)
    }

    fun umaskMode(masque: Int, dossier: Boolean = false) = (if (dossier) "777".toInt(8) else "666".toInt(8)) and masque.inv() and "777".toInt(8)

    private fun hex(b: ByteArray) = b.joinToString("") { "%02x".format(it) }
    fun sha(s: String) = hex(MessageDigest.getInstance("SHA-256").digest(s.toByteArray(Charsets.UTF_8)))

    fun drapeau(graine: String, boite: String, genre: String) = "TG{$boite-$genre-${sha("$graine:$boite:$genre").substring(0, 8)}}"

    /** Les 6 affirmations sur la lettre du faux facteur, mélangées comme random.Random(f"facteur:{graine}").shuffle. */
    fun facteur(graine: String): List<Triple<Int, String, Boolean>> {
        val l = objets(donnees(), "facteur").toMutableList()
        PyHasard("facteur:$graine").melanger(l)
        return l.mapIndexed { i, x -> Triple(i + 1, x.optString("id"), x.optBoolean("vrai")) }
    }

    fun bonsIndices(graine: String) = facteur(graine).filter { it.third }.map { it.first }.sorted()

    fun bits(f: JSONObject): Double = if (f.has("bits")) f.optDouble("bits") else f.optInt("mots") * ln(f.optDouble("liste")) / ln(2.0)

    fun dureeEssais(b: Double, parSeconde: Double? = null): Double =
        Math.pow(2.0, b) / 2 / (parSeconde ?: donnees().optDouble("essais_par_seconde", 1e9))

    private fun entier(v: Double) = "%,.0f".format(java.util.Locale.ROOT, v).replace(",", " ")

    fun dureeTexte(s: Double): String {
        if (s < 1) return t("cit.duree.instant")
        for ((u, n) in listOf("an" to 365.25 * 86400, "jour" to 86400.0, "heure" to 3600.0, "minute" to 60.0, "seconde" to 1.0)) {
            if (s >= n) {
                val v = s / n
                if (u == "an" && v >= 1e6) return t("cit.duree.millions", "n" to entier(v / 1e6))
                return t("cit.duree.$u", "n" to entier(v))
            }
        }
        return t("cit.duree.instant")
    }

    /** La manche Rempart d'une boîte : (règle, ok), d'après modes (chemin → mode, ou null si absent). */
    fun inspecter(b: JSONObject, modes: Map<String, Int?>, rotation: Boolean = false): List<Pair<String, Boolean>> =
        objets(b, "rempart").map { r ->
            when {
                r.optBoolean("rotation") -> "rotation" to rotation
                r.optBoolean("absent") -> "absent:${r.optString("chemin")}" to (modes[r.optString("chemin")] == null)
                else -> {
                    val m = modes[r.optString("chemin")]
                    var ok = true
                    for ((qui, dec) in listOf("fermer_groupe" to 3, "fermer_autres" to 0))
                        for (p in r.optString(qui)) {
                            val bit = (when (p) { 'r' -> 4; 'w' -> 2; else -> 1 }) shl dec
                            if (m != null && m and bit != 0) ok = false
                        }
                    "droits:${r.optString("chemin")}" to ok
                }
            }
        }

    fun boite(id: String?) = objets(donnees(), "boites").firstOrNull { it.optString("id") == id }
    fun boites() = objets(donnees(), "boites")

    fun tableau(glitchs: Int, processus: Int, secrets: Int) =
        listOf(Triple("glitchs", glitchs, glitchs == 0), Triple("processus", processus, processus == 0), Triple("secrets", secrets, secrets == 0))

    fun mots(): List<String> = liste(donnees(), "mots").take(donnees().optInt("mots_nb", 128))

    // ---------------------------------------------------------------- l'état, le terrain, le carnet de garde
    fun etat(jeu: Jeu): JSONObject {
        val c = jeu.module("citadelle")
        for (k in listOf("faits", "rotation", "fictifs")) if (c.optJSONArray(k) == null) c.put(k, JSONArray())
        if (c.optJSONObject("proprietaires") == null) c.put("proprietaires", JSONObject())
        return c
    }

    private fun faits(jeu: Jeu) = liste(etat(jeu), "faits")
    private fun fait(jeu: Jeu, cle: String): Boolean {
        if (cle in faits(jeu)) return true
        etat(jeu).getJSONArray("faits").put(cle)
        return false
    }

    const val CARNET = "carnet_de_garde.txt"
    fun dossier(jeu: Jeu) = File(jeu.terrain, "citadelle")

    fun noter(jeu: Jeu, etiquette: String, texte: String) {
        try { dossier(jeu).mkdirs(); File(dossier(jeu), CARNET).appendText("[$etiquette] $texte\n") } catch (e: Exception) { }
    }

    fun carnet(jeu: Jeu): String = try { File(dossier(jeu), CARNET).readText() } catch (e: Exception) { "" }
    fun dansCarnet(jeu: Jeu, etiquette: String, mot: String = "ok", sujet: String? = null): Boolean {
        val debut = if (sujet != null) "^\\[$etiquette] ${Regex.escape(sujet)}\\b" else "^\\[$etiquette]"
        return Regex("$debut.*\\($mot\\)\\s*$", RegexOption.MULTILINE).containsMatchIn(carnet(jeu))
    }

    fun lire(jeu: Jeu, rel: String) = Histoire.lire(jeu, "citadelle/$rel") ?: ""

    fun mode(f: File): Int? = try {
        if (!f.exists()) null else {
            val p = Files.getPosixFilePermissions(f.toPath())
            var m = 0
            for (x in p) m = m or (1 shl (8 - x.ordinal))
            m
        }
    } catch (e: Exception) { null }

    fun chmod(f: File, mode: Int): Boolean = try {
        Files.setPosixFilePermissions(f.toPath(), PosixFilePermissions.fromString(modeTexte(mode))); true
    } catch (e: Exception) { false }

    val HABITANTS = listOf("gardien:x:1000:1000:Gardien:/citadelle:/bin/sh", "sentinelle:x:1001:2001:Sentinelle:/citadelle/tours:/bin/sh",
        "forgeron:x:1002:1002:Forgeron:/citadelle/cuisines:/bin/sh", "visiteur:x:1003:1003:Visiteur:/citadelle/cour:/bin/false")
    val GROUPES = listOf("gardiens:x:1000:gardien", "veilleurs:x:2001:gardien,sentinelle", "cuisine:x:1002:forgeron",
        "visiteurs:x:1003:visiteur")
    private val ICONES_TRESOR = mapOf("carte" to "🗺", "couronne" to "👑", "epee" to "⚔")

    fun tresor(): Map<String, String> = liste(donnees(), "tresor").associate { f ->
        val n = f.substringBeforeLast('.')
        "tresor/$f" to t("cit.tresor", "icone" to (ICONES_TRESOR[n] ?: "✨"), "nom" to n) + "\n"
    }

    fun parchemins(): Map<String, String> = liste(donnees(), "parchemins").withIndex().associate { (i, f) ->
        "parchemins/$f" to t("cit.parchemin", "n" to i + 1, "nom" to f.substringBeforeLast('.')) + "\n"
    }

    /** Ce que le jeu pose dans la Citadelle quand elle s'ouvre (mêmes fichiers que sur PC). */
    fun meubles(jeu: Jeu): Map<String, Any> {
        val m = linkedMapOf<String, Any>(
            "citadelle/regle_d_or.txt" to t("cit.meuble.regle", "nom" to jeu.nom),
            "citadelle/$CARNET" to t("cit.meuble.carnet") + "\n",
            "citadelle/coffre.txt" to t("cit.meuble.coffre"),
            "citadelle/ronde.sh" to "#!/bin/sh\necho \"" + t("cit.meuble.ronde") + "\"\n",
            "citadelle/habitants.txt" to HABITANTS.joinToString("\n") + "\n",
            "citadelle/groupes.txt" to GROUPES.joinToString("\n") + "\n",
            "citadelle/tour_de_guet.txt" to t("cit.meuble.tour"),
            "citadelle/journaux/acces.log" to journal().joinToString("\n") + "\n",
            "citadelle/cadeau.sh" to "#!/bin/sh\n# " + t("cit.meuble.cadeau1") + "\ncd \"\$(dirname \"\$0\")\" || exit 1\n" +
                "echo \"🎁 !\"\nrm -f bac_a_sable/tresor_*.txt   # " + t("cit.meuble.cadeau3") + "\n",
            "citadelle/bac_a_sable/tresor_1.txt" to t("cit.meuble.bac"),
            "citadelle/bac_a_sable/tresor_2.txt" to t("cit.meuble.bac"),
            "citadelle/lettre.txt" to t("cit.meuble.lettre", "nom" to jeu.nom),
            "citadelle/vraie_lettre.txt" to t("cit.meuble.vraie_lettre"),
            "citadelle/lettre_du_facteur.txt" to t("cit.meuble.fausse_lettre", "lien" to donnees().optString("lien_faux")),
            "citadelle/mots.txt" to mots().joinToString("\n") + "\n")
        for (f in liste(donnees(), "decor")) m["citadelle/$f"] = t("cit.decor", "lieu" to f.substringBeforeLast('/'))
        for ((r, x) in tresor()) m["citadelle/$r"] = x
        m["citadelle/empreintes_tresor.sha256"] = tresor().entries.joinToString("") { "${sha(it.value)}  ${it.key}\n" }
        for ((r, x) in parchemins()) m["citadelle/$r"] = x
        m["citadelle/parchemins.sha256"] = parchemins().entries.joinToString("") { "${sha(it.value)}  ${it.key}\n" }
        return m
    }

    val BESOINS = mapOf("cit0" to listOf("regle_d_or.txt"), "cit1" to listOf("coffre.txt", "ronde.sh"),
        "cit2" to listOf("groupes.txt", "tour_de_guet.txt"), "cit4" to listOf("journaux/acces.log"),
        "cit6" to listOf("cadeau.sh", "bac_a_sable/tresor_1.txt", "bac_a_sable/tresor_2.txt"),
        "cit8" to listOf("empreintes_tresor.sha256", "tresor/carte.txt", "tresor/epee.txt"),
        "cit10" to listOf("lettre.txt"), "cit11" to listOf("vraie_lettre.txt", "lettre_du_facteur.txt"), "cit12" to listOf("mots.txt"))

    private fun ecrire(jeu: Jeu, rel: String, texte: String, mode: Int? = null, mtime: Long? = null): Boolean {
        val f = File(jeu.terrain, "citadelle/$rel")
        if (f.exists() && mode != null) chmod(f, "600".toInt(8))
        if (!Histoire.ecrire(jeu, "citadelle/$rel", texte, finLigne = false)) return false
        if (mode != null) chmod(f, mode)
        if (mtime != null) f.setLastModified(mtime)
        return true
    }

    fun glitchs(jeu: Jeu): List<String> {
        val d = dossier(jeu)
        if (!d.isDirectory) return emptyList()
        return d.walkTopDown().filter { it.isFile && it.name.endsWith(".glitch") }.map { it.relativeTo(d).path }.sorted().toList()
    }

    /** Appelé par Histoire.meubler pendant une leçon de la Citadelle (comme meubler sur PC). */
    fun meubler(jeu: Jeu, lid: String?) {
        val d = dossier(jeu)
        if (!d.isDirectory || lid == null) return
        val step = jeu.etape
        val tous = meubles(jeu)
        if (!fait(jeu, "modes")) for ((r, m) in listOf("coffre.txt" to "644", "ronde.sh" to "644", "cadeau.sh" to "755")) chmod(File(d, r), m.toInt(8))
        for (r in BESOINS[lid] ?: emptyList()) if (!File(d, r).exists()) tous["citadelle/$r"]?.let { ecrire(jeu, r, it.toString(), if (r == "cadeau.sh") "755".toInt(8) else null) }
        val maintenant = System.currentTimeMillis()
        if (lid == "cit5") {
            if (!fait(jeu, "glitchs")) {
                d.walkTopDown().filter { it.isFile }.forEach { it.setLastModified(maintenant - 3_600_000) }
                ecrire(jeu, "repere.txt", t("cit.meuble.repere"), mtime = maintenant - 1000)
                for (g in liste(donnees(), "glitchs")) ecrire(jeu, g, t("cit.meuble.glitch"))
            }
            liste(donnees(), "ver").forEachIndexed { i, g ->
                if (step >= i + 1 && !fait(jeu, "ver${i + 1}")) {
                    ecrire(jeu, g, t("cit.meuble.glitch"))
                    jeu.dire(t("cit.ver.copie", "lieu" to g.substringBeforeLast('/')), 12)
                }
            }
        }
        if (lid == "cit6" && (1..2).any { !File(d, "bac_a_sable/tresor_$it.txt").exists() }) {
            for (i in 1..2) if (!File(d, "bac_a_sable/tresor_$i.txt").exists()) ecrire(jeu, "bac_a_sable/tresor_$i.txt", t("cit.meuble.bac"))
            jeu.dire(t("cit.cadeau.lance"), 16)
        }
        if (lid == "cit7" && step < 1 && fictifsVivants(jeu).isEmpty()) lancerFictifs(jeu, liste(donnees(), "processus"))
        if (lid == "cit8" && !fait(jeu, "altere")) ecrire(jeu, "tresor/" + donnees().optString("tresor_altere"), t("cit.tresor.altere"))
        if (lid == "cit9" && step >= 1 && !fait(jeu, "verrou")) { frapper(jeu); jeu.dire(t("cit.verrou.frappe"), 16) }
        if (lid == "cit9" && step == 0) for ((r, x) in parchemins()) if (!File(d, r).exists()) ecrire(jeu, r, x)
        if (lid == "cit10" || lid == "cit11") Phare.allumer(Port.portPhare(), Phare.Genre.PHARE, jeu)   // le pont curl
        boites().forEachIndexed { i, b -> if (lid == "cit${13 + i}" && !fait(jeu, "boite:" + b.optString("id"))) fabriquerBoite(jeu, b) }
    }

    const val MARQUE_VERROU = "journaux/verrouilleur.log"

    /** Le Verrouilleur frappe une seule fois, juste après la sauvegarde (le journal le note). Vrai s'il vient de frapper. */
    fun frapper(jeu: Jeu): Boolean {
        if (File(dossier(jeu), MARQUE_VERROU).exists()) return false
        verrouiller(jeu)
        ecrire(jeu, MARQUE_VERROU, t("cit.verrou.frappe") + "\n")
        return true
    }

    fun verrouiller(jeu: Jeu) {
        val p = File(dossier(jeu), "parchemins")
        for (f in liste(donnees(), "parchemins")) {
            val src = File(p, f)
            if (!src.isFile) continue
            try {
                val dst = File(p, f.substringBeforeLast('.') + ".verrou")
                dst.writeText(java.util.Base64.getEncoder().encodeToString(src.readBytes()) + "\n")
                chmod(dst, 0)
                src.delete()
            } catch (e: Exception) { }
        }
    }

    fun fabriquerBoite(jeu: Jeu, b: JSONObject) {
        val base = "boites/${b.optString("id")}/"
        val gr = Histoire.graine(jeu)
        for (f in objets(b, "fichiers")) {
            val dr = if (f.has("drapeau")) drapeau(gr, b.optString("id"), f.optString("drapeau")) else ""
            var txt = t(f.optString("texte"), "drapeau" to dr)
            if (f.optBoolean("script")) txt = "#!/bin/sh\n" + txt.split("\n").joinToString("\n") { "# $it" } + "\necho \"" + t("cit.meuble.ronde") + "\"\n"
            ecrire(jeu, base + f.optString("chemin"), if (txt.endsWith("\n")) txt else txt + "\n", f.optString("mode").toInt(8))
        }
        val ds = b.optJSONObject("dossiers") ?: JSONObject()
        for (k in ds.keys()) chmod(File(dossier(jeu), base + k), ds.getString(k).toInt(8))
    }

    fun modesBoite(jeu: Jeu, id: String): Map<String, Int?> {
        val base = File(dossier(jeu), "boites/$id")
        return objets(boite(id), "rempart").filter { it.has("chemin") }.associate { it.optString("chemin") to mode(File(base, it.optString("chemin"))) }
    }

    // ---------------------------------------------------------------- les processus fantômes (simulés sur le téléphone)
    fun fictifsVivants(jeu: Jeu): List<Pair<Int, String>> = objets(etat(jeu), "fictifs").filter { it.optBoolean("vivant") }
        .map { it.optInt("pid") to it.optString("nom") }

    fun lancerFictifs(jeu: Jeu, noms: List<String>) {
        val a = etat(jeu).getJSONArray("fictifs")
        var pid = donnees().optInt("pid_fictif", 4242) + a.length() * 7
        for (n in noms) { a.put(JSONObject().put("pid", pid).put("nom", n).put("vivant", true)); pid += 7 }
    }

    /** kill PID : un processus fantôme est arrêté (rien n'est affiché, comme le vrai kill) ; sinon null (le vrai shell). */
    fun kill(jeu: Jeu, reste: String): String? {
        val pids = reste.split(Regex("\\s+")).filter { !it.startsWith("-") }.mapNotNull { it.toIntOrNull() }
        if (pids.isEmpty()) return null
        val a = etat(jeu).getJSONArray("fictifs")
        val miens = (0 until a.length()).map { a.getJSONObject(it) }.filter { it.optInt("pid") in pids && it.optBoolean("vivant") }
        if (miens.isEmpty()) return null
        miens.forEach { it.put("vivant", false) }
        return ""
    }

    // ---------------------------------------------------------------- les leçons
    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)
    private const val LS = "^(ls|dir)\\b"
    private const val LIRE = "^(cat|less|more|head|tail)\\b"
    private const val CIT = "^(tg\\s+)?citadelle\\s+"
    private const val CURL = "^(curl|curl\\.exe)\\b"
    val PASSE: String get() = donnees().optString("mot_de_passe_exemple", "licorne-violette-exemple")
    val MAUVAISE: String get() = donnees().optString("mauvaise_cle_exemple", "mauvaise-cle")
    private const val OPENSSL_D = "^openssl\\s+enc\\b(?=.*\\s-d\\b)(?=.*-aes-256-cbc\\b)(?=.*-pbkdf2\\b)(?=.*-in\\s+\\S*lettre\\.enc\\b)"

    private fun n(lid: String, i: Int, cmd: String, re: String? = null, fs: ((Jeu) -> Boolean)? = null, ou: String? = null,
                  cree: String? = null, exploit: String? = null, echoue: Boolean = false) =
        Etape("hist.$lid.$i.dit", cmd, "hist.$lid.$i.bravo", re?.let { r(it) }, fs, null, cree, ou, exploit = exploit, echoue = echoue)

    private fun m(j: Jeu, rel: String) = mode(File(j.terrain, "citadelle/$rel"))

    private fun restaure(j: Jeu) = File(dossier(j), MARQUE_VERROU).exists() && parchemins().all { (rel, x) -> lire(j, rel).replace("\r\n", "\n") == x }

    private fun sauvegarde(j: Jeu): Boolean {
        for (nom in listOf("coffre_de_secours.tar.gz", "coffre_de_secours.tgz", "coffre_de_secours.tar")) {
            val f = File(dossier(j), nom)
            if (!f.isFile) continue
            val noms = membresTar(f)
            if (liste(donnees(), "parchemins").all { "parchemins/$it" in noms }) { frapper(j); return true }
        }
        return false
    }

    /** Les noms d'une archive tar (éventuellement gzip), lue à la main (en-têtes de 512 octets). */
    fun membresTar(f: File): Set<String> = try {
        val brut = f.readBytes()
        val b = if (brut.size > 2 && brut[0] == 0x1f.toByte() && brut[1] == 0x8b.toByte())
            java.util.zip.GZIPInputStream(brut.inputStream()).readBytes() else brut
        val out = mutableSetOf<String>()
        var i = 0
        while (i + 512 <= b.size) {
            val nom = String(b, i, 100, Charsets.UTF_8).substringBefore('\u0000')
            if (nom.isEmpty()) break
            val prefixe = String(b, i + 345, 155, Charsets.UTF_8).substringBefore('\u0000')
            val taille = String(b, i + 124, 12, Charsets.US_ASCII).trim('\u0000', ' ').ifEmpty { "0" }.toLong(8)
            out.add((if (prefixe.isNotEmpty()) "$prefixe/$nom" else nom).removePrefix("./"))
            i += 512 + ((taille + 511) / 512 * 512).toInt()
        }
        out
    } catch (e: Exception) { emptySet() }

    val IDS = (0..16).map { "cit$it" }

    fun lecons(jeu: Jeu): Map<String, Lecon> {
        val inspecte = { id: String -> { j: Jeu -> dansCarnet(j, "inspecteur", sujet = id) } }
        val drapeaux = { id: String -> { j: Jeu -> dansCarnet(j, "drapeaux", sujet = id) } }
        val rempart = { id: String -> { j: Jeu -> inspecter(boite(id)!!, modesBoite(j, id)).all { it.second } } }
        return linkedMapOf(
            "cit0" to Lecon("hist.cit0.titre", null, 1, listOf(
                Etape("hist.entree.dit", "cd ~/terrain_terminagotchi/citadelle", "hist.entree.bravo", ici = "citadelle", params = mapOf("piece" to "citadelle")),
                n("cit0", 1, "ls", re = LS, ou = "citadelle"),
                n("cit0", 2, "cat regle_d_or.txt", re = "$LIRE.*regle_d_or"),
            )),
            "cit1" to Lecon("hist.cit1.titre", null, 1, listOf(
                n("cit1", 0, "ls -l coffre.txt", re = "^(ls\\s+(-\\w*l\\w*\\s+)+.*coffre|(tg\\s+)?citadelle\\s+cadenas\\b.*coffre)", ou = "citadelle"),
                n("cit1", 1, "chmod 600 coffre.txt", fs = { j -> m(j, "coffre.txt")?.let { it and "077".toInt(8) == 0 && it and "600".toInt(8) == "600".toInt(8) } == true }),
                n("cit1", 2, "chmod u+x ronde.sh", fs = { j -> m(j, "ronde.sh")?.let { it and "100".toInt(8) != 0 } == true }),
            )),
            "cit2" to Lecon("hist.cit2.titre", null, 1, listOf(
                n("cit2", 0, "id", re = "^(id|whoami|groups)\\b"),
                n("cit2", 1, "grep veilleurs groupes.txt", re = "^grep\\b.*veilleurs.*groupes"),
                n("cit2", 2, "citadelle chown sentinelle:veilleurs tour_de_guet.txt", fs = { j -> dansCarnet(j, "chown") }),
            )),
            "cit3" to Lecon("hist.cit3.titre", null, 1, listOf(
                n("cit3", 0, "umask", re = "^umask\\s*$"),
                n("cit3", 1, "(umask 077; touch carnet_secret.txt)", fs = { j -> m(j, "carnet_secret.txt")?.let { it and "077".toInt(8) == 0 } == true },
                    cree = "citadelle/carnet_secret.txt", ou = "citadelle"),
                n("cit3", 2, "citadelle masque 077", re = "${CIT}masque\\b"),
            )),
            "cit4" to Lecon("hist.cit4.titre", null, 1, listOf(
                n("cit4", 0, "tail -n 5 journaux/acces.log", re = "^tail\\b.*acces\\.log"),
                n("cit4", 1, "grep -c ECHEC journaux/acces.log", re = "^grep\\s+(-\\w*c\\w*\\s+)+.*ECHEC.*acces\\.log|^grep\\b.*ECHEC.*acces\\.log\\s*\\|\\s*wc\\s+-l\\b"),
                n("cit4", 2, "grep ECHEC journaux/acces.log | cut -d \" \" -f 4 | sort | uniq -c | sort -n",
                    re = "^grep\\b.*ECHEC.*\\|\\s*cut\\b.*\\|\\s*sort\\b.*\\|\\s*uniq\\s+-c"),
                n("cit4", 3, "echo ? > intrus.txt", fs = { j -> intrus() in lire(j, "intrus.txt") }, cree = "citadelle/intrus.txt", ou = "citadelle"),
            )),
            "cit5" to Lecon("hist.cit5.titre", null, 1, listOf(
                n("cit5", 0, "find . -name \"*.glitch\"", re = "^find\\b.*-name\\s+[\"']?\\*\\.glitch", ou = "citadelle"),
                n("cit5", 1, "find . -newer repere.txt", re = "^find\\b.*-newer\\s+\\S*repere"),
                n("cit5", 2, "find . -name \"*.glitch\" -delete", fs = { j -> dossier(j).isDirectory && glitchs(j).isEmpty() }),
            )),
            "cit6" to Lecon("hist.cit6.titre", null, 1, listOf(
                n("cit6", 0, "cat cadeau.sh", re = "$LIRE.*cadeau\\.sh", ou = "citadelle"),
                n("cit6", 1, "grep rm cadeau.sh", re = "^grep\\b.*\\brm\\b.*cadeau"),
                n("cit6", 2, "chmod -x cadeau.sh", fs = { j -> m(j, "cadeau.sh")?.let { it and "111".toInt(8) == 0 } == true &&
                    (1..2).all { File(dossier(j), "bac_a_sable/tresor_$it.txt").isFile } }),
            )),
            // le shell du téléphone arrête tout ce qu'une commande lance : les processus fantômes sont simulés
            "cit7" to Lecon("hist.cit7.titre", null, 1, listOf(
                n("cit7", 0, "citadelle ps", re = "(${CIT}ps\\b|^ps\\b.*\\|\\s*grep\\b.*fictif)"),
                n("cit7", 1, "kill ?", fs = { j -> fictifsVivants(j).isEmpty() }),
                n("cit7", 2, "citadelle tableau", re = "${CIT}tableau\\b"),
            )),
            "cit8" to Lecon("hist.cit8.titre", null, 1, listOf(
                n("cit8", 0, "sha256sum tresor/carte.txt", re = "^sha256sum\\b.*tresor", ou = "citadelle"),
                n("cit8", 1, "sha256sum -c empreintes_tresor.sha256", re = "^sha256sum\\s+(-c|--check)\\b.*empreintes_tresor", echoue = true),
                n("cit8", 2, "echo ? > altere.txt", fs = { j -> donnees().optString("tresor_altere").substringBeforeLast('.') in lire(j, "altere.txt") },
                    cree = "citadelle/altere.txt", ou = "citadelle"),
            )),
            // toybox tar sans gzip sur certains téléphones : une archive .tar simple
            "cit9" to Lecon("hist.cit9.titre", null, 1, listOf(
                n("cit9", 0, "tar cf coffre_de_secours.tar parchemins", fs = { j -> sauvegarde(j) }, ou = "citadelle"),
                n("cit9", 1, "tar xf coffre_de_secours.tar", fs = { j -> restaure(j) }),
                n("cit9", 2, "rm -f parchemins/*.verrou", fs = { j -> File(dossier(j), "parchemins").let { p -> File(dossier(j), MARQUE_VERROU).exists() && p.isDirectory && p.listFiles()!!.none { it.name.endsWith(".verrou") } } }),
                n("cit9", 3, "sha256sum -c parchemins.sha256", re = "^sha256sum\\s+(-c|--check)\\b.*parchemins\\.sha256"),
            )),
            "cit10" to Lecon("hist.cit10.titre", null, 1, listOf(
                n("cit10", 0, "cat lettre.txt", re = "$LIRE.*lettre\\.txt", ou = "citadelle"),
                n("cit10", 1, "openssl enc -aes-256-cbc -pbkdf2 -in lettre.txt -out lettre.enc -pass pass:$PASSE",
                    fs = { j -> try { File(dossier(j), "lettre.enc").readBytes().let { b -> b.copyOf(8).contentEquals("Salted__".toByteArray()) &&
                        chiffrer(b, PASSE, true).isNotEmpty() } } catch (e: Exception) { false } },   // la clé d'EXEMPLE (sinon l'étape suivante est impossible)
                    cree = "citadelle/lettre.enc"),
                n("cit10", 2, "openssl enc -d -aes-256-cbc -pbkdf2 -in lettre.enc -pass pass:$MAUVAISE",
                    re = OPENSSL_D + "(?!.*pass:" + Regex.escape(PASSE) + "\\b)", echoue = true),
                n("cit10", 3, "openssl enc -d -aes-256-cbc -pbkdf2 -in lettre.enc -pass pass:$PASSE", re = OPENSSL_D + "(?=.*pass:" + Regex.escape(PASSE) + "\\b)"),
            )),
            "cit11" to Lecon("hist.cit11.titre", null, 1, listOf(
                n("cit11", 0, "diff vraie_lettre.txt lettre_du_facteur.txt", re = "^diff\\b.*(vraie_lettre.*lettre_du_facteur|lettre_du_facteur.*vraie_lettre)",
                    echoue = true, ou = "citadelle"),
                n("cit11", 1, "curl -s http://localhost:8042/courrier", re = "$CURL.*(localhost|127\\.0\\.0\\.1):8042/courrier\\b"),
                n("cit11", 2, "citadelle facteur", re = "${CIT}facteur\\s*$"),
                n("cit11", 3, "citadelle facteur ? ? ?", fs = { j -> dansCarnet(j, "facteur") }),
            )),
            "cit12" to Lecon("hist.cit12.titre", null, 1, listOf(
                n("cit12", 0, "wc -l mots.txt", re = "^wc\\s+-l\\b.*mots", ou = "citadelle"),
                n("cit12", 1, "shuf -n 4 mots.txt", re = "^shuf\\b.*-n\\s*4\\b.*mots"),
                n("cit12", 2, "citadelle force", re = "${CIT}force\\b"),
            )),
            "cit13" to Lecon("hist.cit13.titre", null, 1, listOf(
                n("cit13", 0, "citadelle boites", re = "${CIT}bo[iî]tes?\\s*$", ou = "citadelle"),
                n("cit13", 1, "ls -la boites/enumeration", re = "^ls\\b.*-\\w*a.*enumeration|^ls\\b.*enumeration.*-\\w*a"),
                n("cit13", 2, "grep -r \"TG{\" boites/enumeration", re = "^grep\\s+(-\\w*r\\w*\\s+)+.*TG.*enumeration"),
                n("cit13", 3, "citadelle drapeau ?", fs = drapeaux("enumeration")),
                n("cit13", 4, "chmod o-rwx boites/enumeration/.cave_oubliee", fs = rempart("enumeration")),
                n("cit13", 5, "citadelle inspecteur enumeration", fs = inspecte("enumeration"), exploit = "citadelle.boite"),
            )),
            "cit14" to Lecon("hist.cit14.titre", null, 1, listOf(
                n("cit14", 0, "ls -l boites/droits", re = "^ls\\s+(-\\w*l\\w*\\s+)+.*droits", ou = "citadelle"),
                n("cit14", 1, "find boites/droits -perm -o+w", re = "^find\\b.*droits.*-perm\\s+(\\S*o\\+?w|-?0?002\\b|/0?002\\b)"),
                n("cit14", 2, "grep -r \"TG{\" boites/droits", re = "^grep\\s+(-\\w*r\\w*\\s+)+.*TG.*droits"),
                n("cit14", 3, "citadelle drapeau ?", fs = drapeaux("droits")),
                n("cit14", 4, "chmod o-rwx boites/droits/*", fs = rempart("droits")),
                n("cit14", 5, "citadelle inspecteur droits", fs = inspecte("droits"), exploit = "citadelle.boite.droits"),
            )),
            "cit15" to Lecon("hist.cit15.titre", null, 1, listOf(
                n("cit15", 0, "ls -la boites/secrets", re = "^ls\\b.*-\\w*a.*secrets|^ls\\b.*secrets.*-\\w*a", ou = "citadelle"),
                n("cit15", 1, "grep -r mot_de_passe boites/secrets", re = "^grep\\s+(-\\w*r\\w*\\s+)+.*mot_de_passe.*secrets"),
                n("cit15", 2, "citadelle drapeau ?", fs = drapeaux("secrets")),
                n("cit15", 3, "rm boites/secrets/.historique_fictif", fs = { j -> !File(dossier(j), "boites/secrets/.historique_fictif").exists() }),
                n("cit15", 4, "citadelle rotation secrets", fs = { j -> dansCarnet(j, "rotation") }),
                n("cit15", 5, "citadelle inspecteur secrets", fs = inspecte("secrets"), exploit = "citadelle.boite.secrets"),
            )),
            "cit16" to Lecon("hist.cit16.titre", null, 1, listOf(
                n("cit16", 0, "ss -tln", re = "^(ss\\s+-\\w*l|netstat\\b)"),
                n("cit16", 1, "citadelle vague", re = "${CIT}vague\\b"),
                n("cit16", 2, "citadelle tableau", fs = { j -> dansCarnet(j, "vague", "repoussee") }, exploit = "citadelle.vague"),
            )),
        )
    }

    // ---------------------------------------------------------------- l'arbre du Carrefour
    private fun besoin(): List<String> {
        val P = Programme.donnees()
        val ms = P.optJSONArray("mondes") ?: JSONArray()
        val m = (0 until ms.length()).map { ms.getJSONObject(it) }.firstOrNull { it.optString("id") == "citadelle" } ?: return emptyList()
        val tronc = P.optJSONObject("tronc") ?: JSONObject()
        return liste(m, "requis").flatMap { liste(tronc, it) }.distinct()
    }

    fun ouvert(jeu: Jeu) = besoin().all { Histoire.fini(jeu, it) }
    fun manque(jeu: Jeu) = besoin().filter { !Histoire.fini(jeu, it) }.map { Histoire.nomChapitre(it) }

    fun annonce(jeu: Jeu): Boolean {
        val h = Histoire.h(jeu)
        val deja = h.optJSONArray("mondes_annonces") ?: JSONArray().also { h.put("mondes_annonces", it) }
        if ((0 until deja.length()).any { deja.getString(it) == "citadelle" } || Histoire.fini(jeu, "citadelle") || !ouvert(jeu)) return false
        deja.put("citadelle")
        jeu.log(t("cit.ouvert.log"))
        jeu.dire(Histoire.dire(jeu, "cit.ouvert.dit"), 18)
        return true
    }

    /** Un indice de la Citadelle (Histoire.indice), comme citadelle.indice sur PC. */
    fun indice(jeu: Jeu, e: Etape, tapees: List<Pair<String, String?>>): String? {
        if (Histoire.leconCourante(jeu)?.id !in IDS) return null
        val lignes = tapees.map { it.first.trim() }
        if (lignes.any { Regex("^sudo\\b").containsMatchIn(it) }) return t("cit.indice.sudo")
        if ("?" in e.cmd.split(" ") && lignes.any { Regex("(^|\\s)\\?(\\s|$)|…|<").containsMatchIn(it) }) return t("cit.indice.trou")
        if (e.cmd == "kill ?" && lignes.isNotEmpty() && fictifsVivants(jeu).isNotEmpty()) return t("cit.indice.kill")
        val c = carnet(jeu).lines()
        fun der(et: String) = c.lastOrNull { it.startsWith("[$et]") }
        if (e.cmd.startsWith("citadelle drapeau")) {
            val x = der("drapeau")
            if (x != null && x.endsWith("(faux)")) return t("cit.indice.drapeau")
            if (x != null && x.endsWith("(perime)")) return t("cit.drapeau.perime")
            if (x != null && x.endsWith("(ok)")) return t("cit.drapeau.encore")   // un drapeau sur deux
            return null
        }
        if (e.cmd == "citadelle tableau" && e.exploit == "citadelle.vague")            // la vague : réparer, puis le tableau
            return if (lignes.lastOrNull()?.let { Regex("${CIT}tableau\\b").containsMatchIn(it) } == true) t("cit.vague.encore") else t("hist.cit16.2.dit")
        if (e.cmd.startsWith("citadelle facteur ?") && lignes.lastOrNull()?.let { Regex("${CIT}facteur\\s*$").matches(it) } == true)
            return t("cit.facteur.aide")
        if ((e.cmd.startsWith("citadelle inspecteur") || e.cmd.startsWith("chmod o-rwx boites/")) && der("inspecteur")?.endsWith("(refus)") == true) return t("cit.indice.rempart")
        if (e.cmd.startsWith("citadelle facteur ?") && der("facteur")?.endsWith("(faux)") == true) return t("cit.indice.facteur")
        if (e.cmd.startsWith("openssl") && lignes.any { "pass:" in it && PASSE !in it && "-d" !in it.split(Regex("\\s+")) }) return t("cit.indice.cle")
        if ("glitch" in e.cmd && glitchs(jeu).isNotEmpty()) return t("cit.indice.glitch", "n" to glitchs(jeu).size)
        return null
    }

    // ---------------------------------------------------------------- les commandes du jeu : citadelle …
    val QUI = listOf("moi", "club", "autres")

    /** Les trois cadenas (r w x) pour moi, mon club, les autres ; un cadenas qui change est entre crochets. */
    fun grille(mode: Int, avant: Int? = null): List<String> = QUI.mapIndexed { k, q ->
        val dec = 6 - 3 * k
        val cases = "rwx".mapIndexed { j, p ->
            val on = (mode shr dec) and (4 shr j) != 0
            val change = avant != null && ((avant shr dec) and (4 shr j) != 0) != on
            (if (change) "[" else " ") + (if (on) p else '·') + (if (change) "]" else " ")
        }.joinToString("")
        "  ${listOf("🙂", "👥", "🌍")[k]} ${t("cit.qui.$q").padEnd(12)} $cases"
    }

    fun cadenas(jeu: Jeu, nom: String, dossier: File): List<String> {
        val f = File(dossier, nom).let { if (it.exists()) it else File(dossier(jeu), nom) }
        val m = mode(f) ?: return listOf(t("cit.inconnu", "nom" to nom))
        return listOf("🔒 " + t("cit.cadenas.titre", "nom" to f.name), "  ${modeTexte(m)}  (${"%03o".format(m)})") + grille(m) + listOf("  " + t("cit.cadenas.aide"))
    }

    fun masque(jeu: Jeu, arg: String?): List<String> {
        val actuel = "077".toInt(8)                 // le masque des applis Android
        val m = (arg ?: "").toIntOrNull(8) ?: if (arg.isNullOrEmpty()) actuel else return listOf(t("cit.masque.aide"))
        val o = { x: Int -> "%03o".format(x) }
        val out = mutableListOf("🎭 " + t("cit.masque.titre", "masque" to o(m)),
            "  " + t("cit.masque.calcul", "masque" to o(m), "mode" to o(umaskMode(m)), "texte" to modeTexte(umaskMode(m))))
        out += grille(umaskMode(m), "666".toInt(8))
        out.add("  " + t("cit.masque.dossier", "mode" to o(umaskMode(m, true)), "texte" to modeTexte(umaskMode(m, true))))
        out.add("  " + t("cit.masque.actuel", "masque" to "0" + o(actuel)))
        mode(File(dossier(jeu), "carnet_secret.txt"))?.let { out.add("  " + t("cit.masque.carnet", "texte" to modeTexte(it))) }
        noter(jeu, "masque", "${o(m)} → ${o(umaskMode(m))} (ok)")
        return out
    }

    fun chown(jeu: Jeu, args: List<String>): List<String> {
        if (args.size < 2) return listOf(t("cit.chown.aide"))
        val (user, groupe0) = args[0].split(":", limit = 2).let { it[0] to it.getOrElse(1) { "" } }
        val fichier = args.last()
        val users = HABITANTS.map { it.substringBefore(':') }
        val groupes = GROUPES.map { it.substringBefore(':') }
        if (user !in users) return listOf(t("cit.chown.inconnu", "nom" to user, "liste" to users.joinToString(", ")))
        if (groupe0.isNotEmpty() && groupe0 !in groupes) return listOf(t("cit.chown.groupe_inconnu", "nom" to groupe0, "liste" to groupes.joinToString(", ")))
        val f = File(dossier(jeu), fichier)
        if (!f.isFile) return listOf(t("cit.inconnu", "nom" to fichier))
        val p = etat(jeu).getJSONObject("proprietaires")
        val ancien = p.optString(fichier, "gardien:gardiens")
        val groupe = groupe0.ifEmpty { ancien.substringAfter(':') }
        p.put(fichier, "$user:$groupe")
        val m = mode(f) ?: "644".toInt(8)
        noter(jeu, "chown", "$fichier $user:$groupe (ok)")
        return listOf("🏰 " + t("cit.chown.titre"),
            "  ${t("cit.chown.avant")} -${modeTexte(m)} 1 ${ancien.replace(':', ' ')} ${f.length()} $fichier",
            "  ${t("cit.chown.apres")} -${modeTexte(m)} 1 $user $groupe ${f.length()} $fichier", "", "  " + t("cit.chown.simule"))
    }

    fun lignesPs(jeu: Jeu): List<String> {
        val v = fictifsVivants(jeu)
        val out = mutableListOf("USER          PID  %CPU  COMMAND")
        for ((pid, nom) in v) out.add("explorateur ${pid.toString().padStart(5)}   0.0  $nom ${donnees().optInt("processus_secondes", 900)}")
        if (v.isEmpty()) out.add("  " + t("cit.ps.aucun"))
        return out
    }

    fun lignesTableau(jeu: Jeu): List<String> {
        val g = glitchs(jeu).size
        val p = fictifsVivants(jeu).size
        val sec = mode(File(dossier(jeu), donnees().optJSONObject("vague")?.optString("secret") ?: ""))
        val ouverts = if (sec != null && sec and "077".toInt(8) != 0) 1 else 0
        val out = mutableListOf("🛡 " + t("cit.tableau.titre"), "")
        for ((ind, v, vert) in tableau(g, p, ouverts)) out.add("  ${if (vert) "✔" else "✖"} ${t("cit.tableau.$ind").padEnd(34)} $v")
        if ("vague" in faits(jeu)) {
            if (g == 0 && p == 0 && ouverts == 0) {
                if (!dansCarnet(jeu, "vague", "repoussee")) noter(jeu, "vague", t("cit.vague.repoussee") + " (repoussee)")
                out += listOf("", "  " + t("cit.vague.gagne"))
            } else out += listOf("", "  " + t("cit.vague.encore"))
        }
        return out
    }

    fun vague(jeu: Jeu): List<String> {
        val v = donnees().optJSONObject("vague") ?: JSONObject()
        for (g in liste(v, "glitchs")) ecrire(jeu, g, t("cit.meuble.glitch"))
        ecrire(jeu, v.optString("secret"), t("cit.meuble.secret_vague", "exemple" to PASSE), "644".toInt(8))
        if (fictifsVivants(jeu).none { it.second == v.optString("processus") }) lancerFictifs(jeu, listOf(v.optString("processus")))
        if ("vague" !in faits(jeu)) etat(jeu).getJSONArray("faits").put("vague")
        noter(jeu, "vague", "lancee")
        return listOf("🌊 " + t("cit.vague.titre"), "", "  " + t("cit.vague.texte"), "") + lignesTableau(jeu)
    }

    fun lignesFacteur(jeu: Jeu, choix: List<String>): List<String> {
        val gr = Histoire.graine(jeu)
        val f = facteur(gr)
        if (choix.isEmpty()) return listOf("✉ " + t("cit.facteur.titre"), "") + f.map { "  ${it.first}. " + t("cit.facteur.${it.second}") } +
            listOf("", "  " + t("cit.facteur.aide"))
        val nums = choix.mapNotNull { it.toIntOrNull() }.toSortedSet().toList()
        if (nums.size != choix.size) return listOf(t("cit.facteur.aide"))
        if (nums == bonsIndices(gr)) {
            noter(jeu, "facteur", nums.joinToString(" ") + " (ok)")
            return listOf("✔ " + t("cit.facteur.ok"))
        }
        noter(jeu, "facteur", nums.joinToString(" ") + " (faux)")
        return listOf("✖ " + t("cit.facteur.faux", "n" to nums.count { it in bonsIndices(gr) }))
    }

    fun lignesForce(jeu: Jeu): List<String> {
        val out = mutableListOf("🔑 " + t("cit.force.titre"), "")
        for (f in objets(donnees(), "force")) {
            val b = bits(f)
            out.add("  " + t("cit.force.${f.optString("id")}", "exemple" to f.optString("exemple")))
            val calc = if (f.has("mots")) "${f.optInt("liste")}^${f.optInt("mots")} ≈ 2^${Math.round(b)}" else "≈ 2^${Math.round(b)}"
            out.add("     $calc → " + t("cit.force.temps", "duree" to dureeTexte(dureeEssais(b))))
        }
        out += listOf("", "  " + t("cit.force.morale"), "  " + t("cit.force.jamais"))
        noter(jeu, "force", "exemples (ok)")
        return out
    }

    fun lignesBoites(jeu: Jeu): List<String> {
        val out = mutableListOf("📦 " + t("cit.boites.titre"), "", "  " + t("cit.boites.regle"), "")
        for (b in boites()) {
            val id = b.optString("id")
            val etat = when {
                dansCarnet(jeu, "inspecteur", sujet = id) -> t("cit.boites.maitrisee")
                dansCarnet(jeu, "drapeaux", sujet = id) -> t("cit.boites.rempart")
                else -> t("cit.boites.enquete")
            }
            out.add("  📦 ${t("cit.boite.$id")} (${t("cit.niveau." + b.optString("niveau"))}) — $etat")
        }
        for (a in liste(donnees(), "a_venir")) out.add("  📦 ${t("cit.boite.$a")} — ${t("cit.boites.bientot")}")
        out += listOf("", "  " + t("cit.boites.loi"))
        return out
    }

    fun lignesDrapeau(jeu: Jeu, valeur: String?): List<String> {
        if (valeur.isNullOrBlank()) return listOf(t("cit.drapeau.aide"))
        val gr = Histoire.graine(jeu)
        val v = valeur.trim()
        for (b in boites()) {
            val id = b.optString("id")
            for (genre in listOf("entree", "donjon")) {
                if (v != drapeau(gr, id, genre)) continue
                if (id == "secrets" && genre == "donjon" && id in liste(etat(jeu), "rotation")) {
                    noter(jeu, "drapeau", "$id $genre (perime)")
                    return listOf(t("cit.drapeau.perime"))
                }
                noter(jeu, "drapeau", "$id $genre (ok)")
                val out = mutableListOf("🚩 " + t("cit.drapeau.ok", "boite" to t("cit.boite.$id"), "genre" to t("cit.genre.$genre")))
                val faits = Regex("^\\[drapeau] $id (\\w+) \\(ok\\)", RegexOption.MULTILINE).findAll(carnet(jeu)).map { it.groupValues[1] }.toSet()
                if (faits.containsAll(listOf("entree", "donjon"))) {
                    if (!dansCarnet(jeu, "drapeaux", sujet = id)) noter(jeu, "drapeaux", "$id (ok)")
                    out.add("  " + t("cit.drapeau.deux", "boite" to t("cit.boite.$id")))
                } else out.add("  " + t("cit.drapeau.encore"))
                return out
            }
        }
        noter(jeu, "drapeau", v.take(40) + " (faux)")
        return listOf("✖ " + t("cit.drapeau.faux"))
    }

    fun lignesInspecteur(jeu: Jeu, id: String?): List<String> {
        val b = boite(id) ?: return listOf(t("cit.inspecteur.aide"))
        if (!dansCarnet(jeu, "drapeaux", sujet = id)) return listOf(t("cit.inspecteur.enquete"))
        val regles = inspecter(b, modesBoite(jeu, id!!), id in liste(etat(jeu), "rotation"))
        val out = mutableListOf("🕵 " + t("cit.inspecteur.titre", "boite" to t("cit.boite.$id")), "")
        for ((r, ok) in regles) {
            val genre = r.substringBefore(':')
            out.add("  ${if (ok) "✔" else "✖"} " + t("cit.inspecteur.$genre" + if (ok) ".ok" else ".ko", "chemin" to r.substringAfter(':', "")))
        }
        if (regles.all { it.second }) {
            if (!dansCarnet(jeu, "inspecteur", sujet = id)) noter(jeu, "inspecteur", "$id (ok)")
            out += listOf("", "  " + t("cit.inspecteur.maitrisee", "boite" to t("cit.boite.$id")))
        } else {
            noter(jeu, "inspecteur", "$id (refus)")
            out += listOf("", "  " + t("cit.inspecteur.encore"))
        }
        return out
    }

    fun rotation(jeu: Jeu, id: String?): List<String> {
        if (id != "secrets") return listOf(t("cit.rotation.aide"))
        val r = etat(jeu).getJSONArray("rotation")
        if (id !in liste(etat(jeu), "rotation")) r.put(id)
        val nouveau = "exemple-" + sha("${Histoire.graine(jeu)}:rotation").substring(0, 6)
        if (File(dossier(jeu), "boites/secrets/config.ini").exists())
            ecrire(jeu, "boites/secrets/config.ini", t("cit.boite.config_neuf", "exemple" to nouveau), "600".toInt(8))
        noter(jeu, "rotation", "$id (ok)")
        return listOf("🔄 " + t("cit.rotation.ok"))
    }

    fun phrase(): List<String> {
        val r = SecureRandom()
        val l = mots().toMutableList()
        val p = (0 until 4).map { l.removeAt(r.nextInt(l.size)) }
        return listOf(" " + p.joinToString("-"), "  " + t("cit.force.jamais"))
    }

    /** L'entrée de la Citadelle en caractères : le REPLI de l'illustration B3 (le dessin graphique est
     *  CitadelleDessin.forteresse) tant que l'image n'existe pas. Même dessin que citadelle.FORTERESSE sur PC. */
    val FORTERESSE = listOf("      ▲                        ▲", "     ▟█▙   ▗▄ ▗▄ ▗▄ ▗▄ ▗▄    ▟█▙", "     █▓█▄▄▄█████████████▄▄▄▄█▓█", "     █▓██████▀▀▀🛡▀▀▀███████▓█", "  ░░░████████▌     ▐████████░░░", "  👾 ░░░░░░░░▌     ▐░░░░░░░░ 👾")

    /** citadelle [regle|cadenas|chown|masque|ps|tableau|facteur|force|phrase|boites|drapeau|inspecteur|rotation|vague|stop] */
    fun commande(jeu: Jeu, reste: String, ici: File): String {
        val m = reste.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        val sous = (m.getOrNull(0) ?: "aide").lowercase().replace('î', 'i')
        val a = m.drop(1)
        val l = when (sous) {
            "regle" -> FORTERESSE + t("cit.meuble.regle", "nom" to jeu.nom).split("\n")
            "cadenas" -> if (a.isEmpty()) listOf(t("cit.cadenas.aide")) else cadenas(jeu, a[0], ici)
            "chown" -> chown(jeu, a)
            "masque" -> masque(jeu, a.getOrNull(0))
            "ps" -> lignesPs(jeu)
            "tableau" -> lignesTableau(jeu)
            "facteur" -> lignesFacteur(jeu, a.filter { it != "?" && it != "…" })
            "force" -> lignesForce(jeu)
            "phrase" -> phrase()
            "boites", "boite" -> lignesBoites(jeu)
            "drapeau" -> lignesDrapeau(jeu, if (a.isEmpty() || a == listOf("?")) null else a.joinToString(" "))
            "inspecteur" -> lignesInspecteur(jeu, a.getOrNull(0))
            "rotation" -> rotation(jeu, a.getOrNull(0))
            "vague" -> vague(jeu)
            "stop" -> { etat(jeu).put("fictifs", JSONArray()); listOf(t("cit.stop")) }
            else -> FORTERESSE + listOf("🛡 " + t("cit.aide.titre")) + t("cit.aide.liste").split("\n").map { "  $it" }
        }
        return l.joinToString("\n")
    }

    // ---------------------------------------------------------------- les commandes intégrées (téléphone)
    private fun dans(jeu: Jeu, f: File) = f.canonicalPath.startsWith(jeu.terrain.canonicalPath + "/")

    /** openssl enc -aes-256-cbc -pbkdf2 [-d] -in F [-out G] -pass pass:… (même format que le vrai openssl 3). */
    fun openssl(jeu: Jeu, ligne: String, ici: File): String {
        val m = ligne.trim().split(Regex("\\s+"))
        if (m.getOrNull(1) != "enc") return t("cit.tel.openssl.usage")
        var dech = false; var entree: String? = null; var sortie: String? = null; var pass: String? = null; var algo = false; var pbkdf2 = false
        var i = 2
        while (i < m.size) {
            when (m[i]) {
                "-d" -> dech = true
                "-e" -> dech = false
                "-in" -> { entree = m.getOrNull(i + 1); i++ }
                "-out" -> { sortie = m.getOrNull(i + 1); i++ }
                "-pass" -> { pass = m.getOrNull(i + 1)?.removePrefix("pass:"); i++ }
                "-aes-256-cbc" -> algo = true
                "-pbkdf2" -> pbkdf2 = true
                "-salt" -> {}
                else -> return t("cit.tel.openssl.usage")
            }
            i++
        }
        if (!algo || !pbkdf2 || entree == null || pass == null) return t("cit.tel.openssl.usage")
        val fin = File(ici, entree)
        if (!dans(jeu, fin) || !fin.isFile) return t("cit.inconnu", "nom" to entree)
        val res = try { chiffrer(fin.readBytes(), pass, dech) } catch (e: Exception) { null }
            ?: return "bad decrypt\n" + t("cit.tel.openssl.mauvaise")
        if (sortie != null) {
            val fo = File(ici, sortie)
            if (!dans(jeu, fo)) return t("port.tel.curl.dehors")
            fo.writeBytes(res)
            return ""
        }
        return String(res, Charsets.UTF_8)
    }

    /** AES-256-CBC, clé et vecteur dérivés par PBKDF2-HMAC-SHA256 (10 000 tours) ; en-tête « Salted__ » + sel. */
    fun chiffrer(donnees: ByteArray, pass: String, dechiffrer: Boolean, sel0: ByteArray? = null): ByteArray {
        val sel: ByteArray
        val corps: ByteArray
        if (dechiffrer) {
            require(donnees.size >= 16 && String(donnees, 0, 8, Charsets.US_ASCII) == "Salted__")
            sel = donnees.copyOfRange(8, 16); corps = donnees.copyOfRange(16, donnees.size)
        } else { sel = sel0 ?: ByteArray(8).also { SecureRandom().nextBytes(it) }; corps = donnees }
        val kf = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
        val ki = kf.generateSecret(PBEKeySpec(pass.toCharArray(), sel, 10000, 48 * 8)).encoded
        val c = Cipher.getInstance("AES/CBC/PKCS5Padding")
        c.init(if (dechiffrer) Cipher.DECRYPT_MODE else Cipher.ENCRYPT_MODE, SecretKeySpec(ki.copyOfRange(0, 32), "AES"), IvParameterSpec(ki.copyOfRange(32, 48)))
        val r = c.doFinal(corps)
        return if (dechiffrer) r else "Salted__".toByteArray(Charsets.US_ASCII) + sel + r
    }

    /** diff a b : le format normal (« 2c2 », « < », « --- », « > ») ; « » si les fichiers sont pareils. */
    fun diff(jeu: Jeu, ligne: String, ici: File): Pair<String, Int> {
        val m = ligne.trim().split(Regex("\\s+")).drop(1).filter { !it.startsWith("-") }
        if (m.size != 2) return t("cit.tel.diff.usage") to 2
        val fa = File(ici, m[0]); val fb = File(ici, m[1])
        if (!dans(jeu, fa) || !fa.isFile) return t("cit.inconnu", "nom" to m[0]) to 2
        if (!dans(jeu, fb) || !fb.isFile) return t("cit.inconnu", "nom" to m[1]) to 2
        val a = fa.readText().removeSuffix("\n").split("\n"); val b = fb.readText().removeSuffix("\n").split("\n")
        val texte = diffLignes(a, b)
        return texte to (if (texte.isEmpty()) 0 else 1)
    }

    /** Le diff « normal » de deux listes de lignes (plus longue sous-suite commune, comme GNU diff sur ces cas). */
    fun diffLignes(a: List<String>, b: List<String>): String {
        val n = a.size; val m = b.size
        val L = Array(n + 1) { IntArray(m + 1) }
        for (i in n - 1 downTo 0) for (j in m - 1 downTo 0) L[i][j] = if (a[i] == b[j]) L[i + 1][j + 1] + 1 else maxOf(L[i + 1][j], L[i][j + 1])
        val out = StringBuilder()
        var i = 0; var j = 0
        fun plage(x: Int, y: Int) = if (y - x <= 1) "${x + 1}".let { if (y == x) "$x" else it } else "${x + 1},$y"
        while (i < n || j < m) {
            if (i < n && j < m && a[i] == b[j]) { i++; j++; continue }
            val i0 = i; val j0 = j
            while (i < n || j < m) {
                if (i < n && j < m && a[i] == b[j]) break
                if (j >= m || (i < n && L[i + 1][j] >= L[i][j + 1])) i++ else j++
            }
            when {
                i0 == i -> out.append("${i0}a${plage(j0, j)}\n").append(b.subList(j0, j).joinToString("") { "> $it\n" })
                j0 == j -> out.append("${plage(i0, i)}d${j0}\n").append(a.subList(i0, i).joinToString("") { "< $it\n" })
                else -> out.append("${plage(i0, i)}c${plage(j0, j)}\n").append(a.subList(i0, i).joinToString("") { "< $it\n" })
                    .append("---\n").append(b.subList(j0, j).joinToString("") { "> $it\n" })
            }
        }
        return out.toString().removeSuffix("\n")
    }

    /** shuf -n N fichier : N lignes au hasard (vrai hasard du téléphone), seulement dans le terrain. */
    fun shuf(jeu: Jeu, ligne: String, ici: File): String {
        val m = ligne.trim().split(Regex("\\s+")).drop(1)
        var n = Int.MAX_VALUE; var f: String? = null
        var i = 0
        while (i < m.size) {
            when {
                m[i] == "-n" -> { n = m.getOrNull(i + 1)?.toIntOrNull() ?: return t("cit.tel.shuf.usage"); i++ }
                m[i].startsWith("-n") -> n = m[i].substring(2).toIntOrNull() ?: return t("cit.tel.shuf.usage")
                else -> f = m[i]
            }
            i++
        }
        val fi = File(ici, f ?: return t("cit.tel.shuf.usage"))
        if (!dans(jeu, fi) || !fi.isFile) return t("cit.inconnu", "nom" to (f ?: ""))
        val l = fi.readText().removeSuffix("\n").split("\n").toMutableList()
        val r = SecureRandom()
        val out = mutableListOf<String>()
        while (out.size < n && l.isNotEmpty()) out.add(l.removeAt(r.nextInt(l.size)))
        return out.joinToString("\n")
    }

}
