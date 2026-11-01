package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest
import java.text.Normalizer

/**
 * 🛠 La Guilde des Bâtisseurs Libres — l'open source et le DIY (docs/programme.md § 7.12), portage de pc/tg/guilde.py.
 *
 * Mêmes règles que sur PC (les situations des 4 libertés et « libre ou gratuit » mélangées comme random.shuffle de
 * Python, les licences reconnues et le catalogue, le fichier où la créature décide qu'elle a faim, la faute volontaire
 * de la contribution et sa correction, le porte-clé, son trou et son volume, le STL fait par le jeu et ce qu'on lit d'un
 * STL, la fausse image et son empreinte, le lsblk fictif et le bon disque, l'établi de la vue déployée) : vecteurs
 * communs donnees/guilde/vecteurs.json, vérifiés par tests/jvm/Guilde.kt.
 *
 * Tout reste dans le terrain : l'appli n'installe rien, ne pousse rien, ne crée aucun compte, n'écrit JAMAIS sur un
 * vrai disque (dd et sha256sum se pratiquent sur des FICHIERS du terrain). Sur le téléphone, il n'y a ni git, ni gcc, ni
 * OpenSCAD, ni lsblk : ces étapes sont RACONTÉES ; la copie du code du jeu est faite d'EXTRAITS du vrai code (guilde.json,
 * relus dans pc/tg par donnees/guilde/outils/fiches_guilde.py), et la correction se relit avec diff au lieu de git diff.
 */
object Guilde {
    @Volatile var chargeur: (() -> String?)? = null
    private var d: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("guilde.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun donnees(): JSONObject = d ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() }).also { d = it }

    private fun liste(o: JSONObject?, k: String): List<String> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.get(it).toString() } } ?: emptyList()
    private fun objets(o: JSONObject?, k: String): List<JSONObject> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.getJSONObject(it) } } ?: emptyList()
    private fun entiers(o: JSONObject?, k: String): List<Int> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.getInt(it) } } ?: emptyList()
    private fun hex(b: ByteArray) = b.joinToString("") { "%02x".format(it) }
    private fun sha(s: String) = hex(MessageDigest.getInstance("SHA-256").digest(s.toByteArray(Charsets.UTF_8)))
    private fun o(k: String) = donnees().optJSONObject(k) ?: JSONObject()

    // ---------------------------------------------------------------- la spécification pure (vecteurs communs)
    fun asciiBas(texte: String?): String = Normalizer.normalize(texte ?: "", Normalizer.Form.NFKD)
        .filter { Character.getType(it) != Character.NON_SPACING_MARK.toInt() }.lowercase()

    private fun <T> melange(graine: String, sel: String, l: List<T>): List<T> = l.toMutableList().also { PyHasard("$sel:$graine").melanger(it) }
    private fun tire(graine: String, sel: String, n: Int) = (sha("$graine:$sel").substring(0, 8).toLong(16) % n).toInt()

    class Carte(val n: Int, val id: String, val rep: String)

    fun libertesCartes(graine: String): List<Carte> =
        melange(graine, "libertes", objets(o("libertes"), "situations")).mapIndexed { i, x -> Carte(i + 1, x.optString("id"), "${x.optInt("rep")}") }

    fun gratuitCartes(graine: String): List<Carte> {
        val a = donnees().optJSONArray("gratuit") ?: JSONArray()
        return melange(graine, "gratuit", (0 until a.length()).map { a.getJSONObject(it) }).mapIndexed { i, x -> Carte(i + 1, x.optString("id"), x.optString("rep")) }
    }

    /** (réponse bien formée, cartes justes) */
    fun quizJustes(cartes: List<Carte>, rep: List<String>, lettres: String): Pair<Boolean, List<Carte>> {
        val r = rep.map { asciiBas(it).take(1) }
        if (r.size != cartes.size || r.any { it.isEmpty() || it[0] !in lettres }) return false to emptyList()
        return true to cartes.zip(r).filter { it.first.rep == it.second }.map { it.first }
    }

    private val L get() = o("licences")
    fun licenceDeTexte(texte: String?): String? =
        objets(L, "familles").firstOrNull { Regex(it.optString("motif"), RegexOption.IGNORE_CASE).containsMatchIn(texte ?: "") }?.optString("id")
    fun licenceCatalogue(nom: String?): String? = L.optJSONObject("catalogue")?.optString(asciiBas(nom).trim())?.ifEmpty { null }
    fun genreLicence(fam: String?): String? = objets(L, "familles").firstOrNull { it.optString("id") == fam }?.optString("genre")
    fun nomLicence(fam: String): String = objets(L, "familles").firstOrNull { it.optString("id") == fam }?.optString("nom") ?: fam
    fun aTrouver() = L.optInt("a_trouver", 5)

    /** Les fichiers (noms) où la créature décide qu'elle a faim, dans {chemin: texte}. */
    fun faimFichiers(fichiers: Map<String, String>): List<String> {
        for (m in liste(o("faim"), "marques")) {
            val re = Regex(m, RegexOption.MULTILINE)
            val r = fichiers.filter { re.containsMatchIn(it.value) }.keys.map { it.substringAfterLast("/") }.toSortedSet().toList()
            if (r.isNotEmpty()) return r
        }
        return emptyList()
    }

    fun faimOk(reponse: String?, attendus: List<String>): Boolean {
        val r = asciiBas((reponse ?: "").trim()).replace("\\", "/").substringAfterLast("/").substringBefore(":")
        if (r.isEmpty()) return false
        return attendus.any { val a = it.lowercase(); r == a || "$r.py" == a || "$r.kt" == a }
    }

    private val CO get() = o("contribution")
    fun faute(graine: String): JSONObject { val f = objets(CO, "fautes"); return f[tire(graine, "faute", f.size)] }

    fun texteContribution(graine: String, juste: Boolean = false): String {
        val f = faute(graine)
        val lignes = objets(CO, "lignes").mapIndexed { i, x ->
            var txt = x.optString("texte")
            if (i == f.optInt("ligne") && !juste) txt = txt.replaceFirst(f.optString("juste"), f.optString("faux"))
            "${x.optString("cle")} = $txt"
        }
        return (liste(CO, "entete") + lignes).joinToString("\n") + "\n"
    }

    fun correctionOk(texte: String?, graine: String) = (texte ?: "").replace("\r\n", "\n").trimEnd('\n') == texteContribution(graine, true).trimEnd('\n')

    class Piece(val longueur: Int, val largeur: Int, val epaisseur: Int, val trouX: Int, val trouY: Int, val trouD: Int)

    fun piece(graine: String): Piece {
        val p = o("piece")
        val lo = entiers(p, "longueurs"); val la = entiers(p, "largeurs"); val ep = entiers(p, "epaisseurs")
        val l = la[tire(graine, "largeur", la.size)]
        return Piece(lo[tire(graine, "longueur", lo.size)], l, ep[tire(graine, "epaisseur", ep.size)], p.optInt("trou_x", 6), l / 2, p.optInt("trou_d", 5))
    }

    private fun nombre(x: String): Double? = x.trim().replace(",", ".").trimEnd('.').toDoubleOrNull()

    fun trouOk(rep: List<String>, graine: String): Boolean {
        val p = piece(graine)
        val nb = rep.map { it.trim { c -> c in "[](),;" } }.filter { it.isNotEmpty() }.map { nombre(it) }
        return nb.size >= 2 && nb[0] == p.trouX.toDouble() && nb[1] == p.trouY.toDouble()
    }

    fun volume(graine: String): Int { val p = piece(graine); return p.longueur * p.largeur * p.epaisseur }

    fun volumeOk(reponse: String?, graine: String): Boolean {
        val s = asciiBas((reponse ?: "").trim()).replace(" ", "")
        val m = Regex("(\\d+(?:[.,]\\d+)?)(mm3|mm³|cm3|cm³)?").matchEntire(s) ?: return false
        var v = m.groupValues[1].replace(",", ".").toDouble()
        if (m.groupValues[2].startsWith("cm")) v *= 1000
        return Math.abs(v - volume(graine)) < 0.5
    }

    fun scadTexte(graine: String, nom: String): String {
        val p = piece(graine)
        return "// ${t("gu.scad.titre", "nom" to nom)}\n// ${t("gu.scad.mesures")}\n" +
            "longueur = ${p.longueur};\nlargeur = ${p.largeur};\nepaisseur = ${p.epaisseur};\n\n" +
            "difference() {\n    cube([longueur, largeur, epaisseur]);\n    // ${t("gu.scad.trou")}\n" +
            "    translate([${p.trouX}, largeur / 2, -1])\n        cylinder(h = epaisseur + 2, d = ${p.trouD}, \$fn = 32);\n}\n"
    }

    private val FACES = listOf(
        intArrayOf(0, 0, -1) to listOf(intArrayOf(0, 0, 0), intArrayOf(0, 1, 0), intArrayOf(1, 1, 0)), intArrayOf(0, 0, -1) to listOf(intArrayOf(0, 0, 0), intArrayOf(1, 1, 0), intArrayOf(1, 0, 0)),
        intArrayOf(0, 0, 1) to listOf(intArrayOf(0, 0, 1), intArrayOf(1, 0, 1), intArrayOf(1, 1, 1)), intArrayOf(0, 0, 1) to listOf(intArrayOf(0, 0, 1), intArrayOf(1, 1, 1), intArrayOf(0, 1, 1)),
        intArrayOf(0, -1, 0) to listOf(intArrayOf(0, 0, 0), intArrayOf(1, 0, 0), intArrayOf(1, 0, 1)), intArrayOf(0, -1, 0) to listOf(intArrayOf(0, 0, 0), intArrayOf(1, 0, 1), intArrayOf(0, 0, 1)),
        intArrayOf(0, 1, 0) to listOf(intArrayOf(0, 1, 0), intArrayOf(0, 1, 1), intArrayOf(1, 1, 1)), intArrayOf(0, 1, 0) to listOf(intArrayOf(0, 1, 0), intArrayOf(1, 1, 1), intArrayOf(1, 1, 0)),
        intArrayOf(-1, 0, 0) to listOf(intArrayOf(0, 0, 0), intArrayOf(0, 0, 1), intArrayOf(0, 1, 1)), intArrayOf(-1, 0, 0) to listOf(intArrayOf(0, 0, 0), intArrayOf(0, 1, 1), intArrayOf(0, 1, 0)),
        intArrayOf(1, 0, 0) to listOf(intArrayOf(1, 0, 0), intArrayOf(1, 1, 0), intArrayOf(1, 1, 1)), intArrayOf(1, 0, 0) to listOf(intArrayOf(1, 0, 0), intArrayOf(1, 1, 1), intArrayOf(1, 0, 1)))

    /** Un fichier STL texte : la plaque du porte-clé (une boîte, 12 triangles), quand OpenSCAD manque. */
    fun stlBoite(lo: Int, la: Int, h: Int, nom: String = "porte_cle"): String {
        val out = mutableListOf("solid $nom")
        for ((n, tri) in FACES) {
            out.add("  facet normal " + n.joinToString(" ")); out.add("    outer loop")
            for (v in tri) out.add("      vertex ${v[0] * lo} ${v[1] * la} ${v[2] * h}")
            out.add("    endloop"); out.add("  endfacet")
        }
        out.add("endsolid $nom")
        return out.joinToString("\n") + "\n"
    }

    class Stl(val n: Int, val binaire: Boolean, val dims: List<Double>)

    private fun arrondi(x: Double) = Math.round(x * 100) / 100.0

    /** Ce qu'on lit d'un STL (texte ou binaire), ou null s'il est illisible. */
    fun stlInfos(octets: ByteArray): Stl? {
        val pts = mutableListOf<DoubleArray>()
        val debut = String(octets.copyOfRange(0, minOf(5, octets.size)), Charsets.ISO_8859_1).lowercase()
        val tete = debut == "solid" && String(octets.copyOfRange(0, minOf(2000, octets.size)), Charsets.ISO_8859_1).contains("facet")
        val n: Int
        if (tete) {
            val txt = String(octets, Charsets.UTF_8)
            n = Regex("^\\s*facet\\s+normal\\b", RegexOption.MULTILINE).findAll(txt).count()
            for (m in Regex("^\\s*vertex\\s+(\\S+)\\s+(\\S+)\\s+(\\S+)", RegexOption.MULTILINE).findAll(txt)) {
                val v = m.groupValues.drop(1).map { it.toDoubleOrNull() ?: return null }
                pts.add(v.toDoubleArray())
            }
        } else {
            if (octets.size < 84) return null
            val bb = ByteBuffer.wrap(octets).order(ByteOrder.LITTLE_ENDIAN)
            val nl = bb.getInt(80).toLong() and 0xFFFFFFFFL
            if (octets.size < 84 + 50 * nl) return null
            n = nl.toInt()
            for (k in 0 until n) for (s in 1..3) {
                val o = 84 + 50 * k + 12 * s
                pts.add(doubleArrayOf(bb.getFloat(o).toDouble(), bb.getFloat(o + 4).toDouble(), bb.getFloat(o + 8).toDouble()))
            }
        }
        if (pts.isEmpty()) return Stl(n, !tete, listOf(0.0, 0.0, 0.0))
        return Stl(n, !tete, (0..2).map { i -> arrondi(pts.maxOf { it[i] } - pts.minOf { it[i] }) })
    }

    private val IM get() = o("image")
    fun imageOctets(): ByteArray {
        val out = java.io.ByteArrayOutputStream()
        out.write(IM.optString("entete").toByteArray(Charsets.US_ASCII))
        var k = 0
        val md = MessageDigest.getInstance("SHA-256")
        val n = IM.optInt("octets", 65536)
        while (out.size() < n) { out.write(md.digest("guilde-image:$k".toByteArray())); k++ }
        return out.toByteArray().copyOf(n)
    }

    fun imageSha(): String = hex(MessageDigest.getInstance("SHA-256").digest(imageOctets()))

    class Disque(val nom: String, val taille: String, val rm: Int, val type: String, val point: String)

    private val DI get() = o("disques")
    fun disques(graine: String): List<Disque> {
        val noms = melange(graine, "disques", liste(DI, "noms"))
        val cles = objets(DI, "cles")
        val cle = cles[tire(graine, "cle", cles.size)]
        val s = DI.optString("sauvegarde")
        val r = mutableListOf(Disque(noms[0], s, 1, "disk", ""), Disque(noms[0] + "1", s, 1, "part", "/media/SAUVEGARDE"),
            Disque(noms[1], cle.optString("lsblk"), 1, "disk", ""), Disque(noms[1] + "1", cle.optString("lsblk"), 1, "part", ""))
        r.sortBy { it.nom }
        return r + listOf(Disque("nvme0n1", DI.optString("systeme"), 0, "disk", ""), Disque("nvme0n1p1", "600M", 0, "part", "/boot/efi"),
            Disque("nvme0n1p2", DI.optString("systeme_racine"), 0, "part", "/"))
    }

    fun cleDisque(graine: String): Pair<String, Int> {
        val cles = objets(DI, "cles")
        return melange(graine, "disques", liste(DI, "noms"))[1] to cles[tire(graine, "cle", cles.size)].optInt("go")
    }

    private fun sansDev(r: String?) = (r ?: "").trim().lowercase().let { if (it.startsWith("/dev/")) it.substring(5) else it }
    fun disqueOk(reponse: String?, graine: String) = sansDev(reponse) == cleDisque(graine).first

    fun disqueErreur(reponse: String?, graine: String): String {
        val r = sansDev(reponse)
        val rows = disques(graine).associateBy { it.nom }
        val x = rows[r] ?: return "inconnu"
        if (r.startsWith("nvme")) return "systeme"
        return if (x.type == "part") "partition" else "sauvegarde"
    }

    fun majmin(nom: String): String {
        Regex("sd([a-z])(\\d*)").matchEntire(nom)?.let { return "8:${16 * (it.groupValues[1][0] - 'a') + (it.groupValues[2].toIntOrNull() ?: 0)}" }
        val m = Regex("nvme0n1(?:p(\\d+))?").matchEntire(nom)
        return "259:${m?.groupValues?.get(1)?.toIntOrNull() ?: 0}"
    }

    // ---------------------------------------------------------------- l'établi (vue déployée)
    private val SEPARATEURS = Regex("\\|\\||&&|[|;&]")

    fun etabliDe(morceau: String?): Triple<String, String, String>? {
        val m = (morceau ?: "").trim()
        for (r in objets(o("etabli"), "regles")) if (Regex(r.optString("motif")).containsMatchIn(m)) return Triple(r.optString("outil"), r.optString("de"), r.optString("vers"))
        return null
    }

    fun etablisDe(ligne: String?): List<Triple<String, String, String>> = (ligne ?: "").split(SEPARATEURS).mapNotNull { etabliDe(it) }

    // ---------------------------------------------------------------- l'état, le terrain, le carnet de la guilde
    fun etat(jeu: Jeu): JSONObject {
        val c = jeu.module("guilde")
        if (c.optJSONArray("faits") == null) c.put("faits", JSONArray())
        return c
    }

    private fun fait(jeu: Jeu, cle: String): Boolean {
        if (cle in liste(etat(jeu), "faits")) return true
        etat(jeu).getJSONArray("faits").put(cle)
        return false
    }

    const val CARNET = "carnet_de_la_guilde.txt"
    const val IMAGE = "image_linux_exemple.iso"
    const val CLE = "cle_usb.img"
    fun dossier(jeu: Jeu) = File(jeu.terrain, "guilde")
    fun noter(jeu: Jeu, etiquette: String, texte: String) {
        try { dossier(jeu).mkdirs(); File(dossier(jeu), CARNET).appendText("[$etiquette] $texte\n") } catch (e: Exception) { }
    }
    fun carnet(jeu: Jeu): String = try { File(dossier(jeu), CARNET).readText() } catch (e: Exception) { "" }
    fun dansCarnet(jeu: Jeu, etiquette: String, mot: String = "ok") =
        Regex("^\\[$etiquette].*\\($mot\\)\\s*$", RegexOption.MULTILINE).containsMatchIn(carnet(jeu))
    fun licencesTrouvees(jeu: Jeu): List<String> =
        Regex("^\\[licence] (\\S+) .*\\(ok\\)\\s*$", RegexOption.MULTILINE).findAll(carnet(jeu)).map { it.groupValues[1] }.toSortedSet().toList()

    private fun ecrire(jeu: Jeu, rel: String, contenu: Any) = Histoire.ecrire(jeu, "guilde/$rel", contenu, finLigne = false)
    private fun lireOctets(jeu: Jeu, rel: String): ByteArray? = try { File(dossier(jeu), rel).readBytes() } catch (e: Exception) { null }

    fun bonjourC(): String {
        val msg = t("gu.bonjour.message").replace("\\", "\\\\").replace("\"", "\\\"").replace("%", "%%")
        return o("code").optString("bonjour_c").replace("@MESSAGE@", msg)
    }

    fun creditsTexte(): String {
        val a = o("credits").optJSONArray("contributeurs") ?: JSONArray()
        val c = (0 until a.length()).mapNotNull { a.optJSONObject(it) }.filter { it.optString("pseudo").isNotEmpty() }
        return t("gu.meuble.credits") + "\n\n" + (if (c.isNotEmpty()) c.joinToString("") {
            t("gu.credits.ligne", "pseudo" to it.optString("pseudo"), "n" to it.optInt("contributions")) + "\n" } else t("gu.credits.vide") + "\n")
    }

    // ---------------------------------------------------------------- les badges de la Guilde (1er novembre)
    // Pas de créature « contributeur » ni de variante réservée : deux BADGES qui grandissent (écusson et grade de Badges.kt)
    // et un NOM COLORÉ quand l'un d'eux est le titre affiché. Même spécification que guilde.py (vecteurs communs).
    private fun badge(b: String): JSONObject = o("badges").optJSONObject(b) ?: JSONObject()
    private fun paliers(b: String): List<JSONObject> = badge(b).optJSONArray("paliers")?.let { a -> (0 until a.length()).map { a.getJSONObject(it) } } ?: emptyList()

    fun palierArtisan(lecons: Int, contribution: Boolean): Int {
        var k = -1
        for ((i, p) in paliers("artisan").withIndex()) {
            if (lecons >= p.optInt("lecons") && (contribution || !p.optBoolean("contribution"))) k = i else break
        }
        return k
    }

    fun palierContributeur(n: Int): Int {
        var k = -1
        for ((i, p) in paliers("contributeur").withIndex()) if (n >= p.optInt("n")) k = i else break
        return k
    }

    fun contributionsDe(pseudo: String?, contributeurs: JSONArray?): Int {
        val p = (pseudo ?: "").trim().lowercase()
        if (p.isEmpty() || contributeurs == null) return 0
        for (i in 0 until contributeurs.length()) {
            val x = contributeurs.optJSONObject(i) ?: continue
            if (x.optString("pseudo").trim().lowercase() == p) return x.optInt("contributions").coerceAtLeast(0)
        }
        return 0
    }

    fun leconsFaites(jeu: Jeu): Int {
        val f = Histoire.h(jeu).optJSONArray("faits")?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: emptyList()
        return liste(badge("artisan"), "lecons").count { it in f }
    }

    fun contributionPrete(jeu: Jeu) = Recompenses.etat(jeu).getJSONObject("exploits").has("guilde.artisan")

    class Badge(val id: String, val k: Int, val echelon: String?, val n: Int)

    fun artisan(jeu: Jeu): Badge {
        val n = leconsFaites(jeu)
        val k = palierArtisan(n, contributionPrete(jeu))
        return Badge("artisan", k, if (k >= 0) paliers("artisan")[k].optString("echelon") else null, n)
    }

    fun contributeur(jeu: Jeu): Badge {
        val n = contributionsDe(Recensement.compte(jeu).optString("pseudo"), o("credits").optJSONArray("contributeurs"))
        val k = palierContributeur(n)
        return Badge("contributeur", k, if (k >= 0) paliers("contributeur")[k].optString("echelon") else null, n)
    }

    fun couleurBadge(b: String): String = badge(b).optString("couleur", "#ffaf5f")

    /** Les titres des badges de la Guilde (Contributeur d'abord), pour Entrainement.titres. */
    fun titres(jeu: Jeu): List<Entrainement.Titre> = listOf(contributeur(jeu), artisan(jeu)).filter { it.echelon != null }.map {
        Entrainement.Titre("${it.id}:${it.echelon}", t("ent.titre.famille", "badge" to t(badge(it.id).optString("nom")),
            "echelon" to Entrainement.nomEchelon(it.echelon!!)), couleurBadge(it.id))
    }

    fun progresArtisan(jeu: Jeu): String {
        val a = artisan(jeu)
        val P = paliers("artisan")
        if (a.k + 1 >= P.size) return t("gu.badge.artisan.max")
        val p = P[a.k + 1]
        if (a.n >= p.optInt("lecons") && p.optBoolean("contribution") && !contributionPrete(jeu))
            return t("gu.badge.artisan.contribution", "echelon" to Entrainement.nomEchelon(p.optString("echelon")))
        return t("gu.badge.artisan.progres", "n" to a.n, "s" to p.optInt("lecons"), "echelon" to Entrainement.nomEchelon(p.optString("echelon")))
    }

    fun progresContributeur(jeu: Jeu): String {
        val c = contributeur(jeu)
        val P = paliers("contributeur")
        if (c.k < 0) return t("gu.badge.contributeur.aucune")
        if (c.k + 1 >= P.size) return t("gu.badge.contributeur.max")
        return t("gu.badge.contributeur.progres", "n" to c.n, "s" to P[c.k + 1].optInt("n"), "echelon" to Entrainement.nomEchelon(P[c.k + 1].optString("echelon")))
    }

    /** Les deux badges de la Guilde (balises dessinées par le terminal), leur progression, et ce que colore le nom. */
    fun lignesBadges(jeu: Jeu): List<String> {
        val out = mutableListOf("🛠 " + t("gu.badges.titre"))
        for ((b, prog) in listOf(artisan(jeu) to progresArtisan(jeu), contributeur(jeu) to progresContributeur(jeu)))
            out.add(Badges.balise(if (b.echelon != null) b.id else null, b.echelon) + "  " + t(badge(b.id).optString("nom")) + " · " +
                (b.echelon?.let { Entrainement.nomEchelon(it) } ?: "—") + "   " + prog)
        out.add(t("gu.badges.nom", "artisan" to t("gu.badge.artisan"), "contributeur" to t("gu.badge.contributeur"), "cmd" to "`badges titre`"))
        return out
    }

    fun meubles(jeu: Jeu): Map<String, Any> {
        val gr = Histoire.graine(jeu)
        return linkedMapOf(
            "guilde/mur_des_plans.txt" to t("gu.meuble.mur", "nom" to jeu.nom) + "\n",
            "guilde/$CARNET" to t("gu.meuble.carnet") + "\n",
            "guilde/CREDITS.txt" to creditsTexte(),
            "guilde/petit_projet/LICENSE" to o("code").optString("licence_mit"),
            "guilde/petit_projet/LISEZMOI.txt" to t("gu.meuble.projet") + "\n",
            "guilde/atelier/bonjour.c" to bonjourC(),
            "guilde/atelier/etoiles.c" to o("code").optString("etoiles_c"),
            "guilde/fabrique/porte_cle.scad" to scadTexte(gr, jeu.nom),
            "guilde/vieux_pc/LISEZMOI.txt" to t("gu.meuble.vieux_pc") + "\n")
    }

    val BESOINS = mapOf("gu0" to listOf("mur_des_plans.txt"), "gu1" to listOf("petit_projet/LICENSE"),
        "gu3" to listOf("atelier/bonjour.c", "atelier/etoiles.c"), "gu5" to listOf("fabrique/porte_cle.scad"))

    fun meubler(jeu: Jeu, lid: String?) {
        val d = dossier(jeu)
        if (!d.isDirectory || lid == null) return
        val tous = meubles(jeu)
        for (r in BESOINS[lid] ?: emptyList()) if (!File(d, r).exists()) tous["guilde/$r"]?.let { ecrire(jeu, r, it) }
        if (lid == "gu6" && jeu.etape >= 2 && !File(d, "vieux_pc/$IMAGE").exists()) poserCle()(jeu)
        if (lid == "gu2" && File(codeDuJeu(jeu), "pc").isDirectory && !File(codeDuJeu(jeu), "LICENSE").exists()) poserLicences(jeu)
        val e = Programme.donnees().optJSONObject("etapes")?.optJSONObject("$lid.${jeu.etape}")
        if (e != null) for (mid in liste(e, "maths")) {
            if (Maths.noeud(mid) != null && !Maths.sait(jeu, mid) && !fait(jeu, "pont:$mid")) {
                jeu.dire(t("gu.pont", "notion" to Maths.titre(mid), "cmd" to "maths $mid"), 16)
                break
            }
        }
    }

    // ---------------------------------------------------------------- le code du jeu (des extraits), la contribution, la clé
    fun codeDuJeu(jeu: Jeu) = File(dossier(jeu), "code_du_jeu")

    /** La copie du téléphone : des EXTRAITS du vrai code du jeu (guilde.json), dans le terrain. */
    fun poserCopie(jeu: Jeu): Int {
        val ex = o("extraits")
        var n = 0
        for (k in ex.keys()) if (ecrire(jeu, "code_du_jeu/$k", ex.getString(k))) n++
        ecrire(jeu, "code_du_jeu/LISEZMOI_COPIE.txt", t("gu.tel.copie") + "\n")
        poserLicences(jeu)
        return n
    }

    /** Les licences du jeu (LICENSE : la GPL du code ; LICENSE-images.md : CC BY-NC-SA pour les images et le lore) à la
     *  racine de la copie, comme dans le dépôt : seulement celles qui manquent. */
    fun poserLicences(jeu: Jeu) {
        val f = o("licences_du_jeu").optJSONObject("fichiers") ?: return
        for (k in f.keys()) if (!File(codeDuJeu(jeu), k).exists()) ecrire(jeu, "code_du_jeu/$k", f.getString(k))
    }

    fun fichiersDuCode(jeu: Jeu): Map<String, String> {
        val base = codeDuJeu(jeu)
        if (!base.isDirectory) return emptyMap()
        return base.walkTopDown().filter { it.isFile && (it.name.endsWith(".py") || it.name.endsWith(".kt")) }
            .associate { it.relativeTo(base).path to (try { it.readText() } catch (e: Exception) { "" }) }
    }

    const val CONTRIB = "contribution"
    fun poserContribution(jeu: Jeu): Boolean {
        if (File(dossier(jeu), "$CONTRIB/langues/fr.txt").exists()) return true
        val gr = Histoire.graine(jeu)
        ecrire(jeu, "$CONTRIB/.origine/fr.txt", texteContribution(gr))
        ecrire(jeu, "$CONTRIB/LISEZMOI.txt", t("gu.contrib.lisezmoi") + "\n")
        return ecrire(jeu, "$CONTRIB/langues/fr.txt", texteContribution(gr))
    }

    fun corrigee(jeu: Jeu) = correctionOk(Histoire.lire(jeu, "guilde/$CONTRIB/langues/fr.txt"), Histoire.graine(jeu))

    fun poserCle(): (Jeu) -> Unit = { jeu ->
        ecrire(jeu, "vieux_pc/$IMAGE", imageOctets())
        ecrire(jeu, "vieux_pc/$IMAGE.sha256", "${imageSha()}  $IMAGE\n")
        ecrire(jeu, "vieux_pc/$CLE", ByteArray(IM.optInt("cle_octets", 131072)))
    }

    fun cleCopiee(jeu: Jeu): Boolean {
        val b = lireOctets(jeu, "vieux_pc/$CLE") ?: return false
        return hex(MessageDigest.getInstance("SHA-256").digest(b)) == imageSha()
    }

    // ---------------------------------------------------------------- les leçons du téléphone
    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)
    private const val LS = "^(ls|dir)\\b"
    private const val LIRE = "^(cat|less|more|head|tail)\\b"
    private const val GU = "^(tg\\s+)?guilde\\s+"
    private const val A = "guilde/atelier"
    private const val C = "guilde/contribution"
    private const val F = "guilde/fabrique"
    private const val V = "guilde/vieux_pc"

    private fun n(lid: String, i: Any, cmd: String, re: String? = null, fs: ((Jeu) -> Boolean)? = null, ou: String? = null,
                  exploit: String? = null) =
        Etape("hist.$lid.$i.dit", cmd, "hist.$lid.$i.bravo", re?.let { r(it) }, fs, null, null, ou, exploit = exploit)

    val IDS = (0..6).map { "gu$it" }

    /** Les leçons du téléphone : les mêmes paliers ; git, gcc, make, OpenSCAD et lsblk sont racontés ; la copie du code est
     *  faite d'extraits du vrai code ; la correction se relit avec diff. */
    fun lecons(jeu: Jeu): Map<String, Lecon> {
        val carnetOk = { et: String -> { j: Jeu -> dansCarnet(j, et) } }
        return linkedMapOf(
            "gu0" to Lecon("hist.gu0.titre", null, 1, listOf(
                Etape("hist.entree.dit", "cd ~/terrain_terminagotchi/guilde", "hist.entree.bravo", ici = "guilde", params = mapOf("piece" to "guilde")),
                n("gu0", 1, "ls", re = LS, ou = "guilde"),
                n("gu0", 2, "cat mur_des_plans.txt", re = "$LIRE.*mur_des_plans", ou = "guilde"),
            )),
            "gu1" to Lecon("hist.gu1.titre", null, 1, listOf(
                n("gu1", 0, "guilde libertes", re = "${GU}libert[eé]s?\\s*$", ou = "guilde"),
                n("gu1", 1, "guilde libertes ? ? ? ?", fs = carnetOk("libertes")),
                n("gu1", 2, "cat petit_projet/LICENSE", re = "$LIRE.*petit_projet/LICENSE", ou = "guilde"),
                n("gu1", 5, "guilde licence ?", fs = { j -> licencesTrouvees(j).size >= aTrouver() }),
                n("gu1", 6, "guilde gratuit", re = "${GU}gratuits?\\s*$"),
                n("gu1", 7, "guilde gratuit ? ? ? ?", fs = carnetOk("gratuit")),
                n("gu1", 8, "guilde licence terminagotchi", re = "${GU}licen[cs]es?\\s+terminagotchi\\b"),
            )),
            "gu2" to Lecon("hist.gu2.titre", null, 1, listOf(
                n("gu2", 0, "guilde depot", re = "${GU}d[eé]p[oô]t\\b", ou = "guilde"),
                n("gu2", 2, "guilde copie", fs = { j -> File(codeDuJeu(j), "pc").isDirectory }),
                n("gu2", "t3", "ls -R code_du_jeu", re = "^ls\\b.*code_du_jeu", ou = "guilde"),
                n("gu2", 4, "grep -rl \"faim\" code_du_jeu/pc/tg", re = "^grep\\b.*-\\w*r\\w*.*faim.*code_du_jeu", ou = "guilde"),
                n("gu2", 5, "grep -rn \"def etat_de\" code_du_jeu/pc/tg", re = "^grep\\b.*etat_de.*code_du_jeu", ou = "guilde"),
                n("gu2", 6, "guilde faim ?", fs = carnetOk("faim")),
                n("gu2", "t7", "head -40 code_du_jeu/pc/tg/satiete.py", re = "$LIRE.*code_du_jeu.*satiete", ou = "guilde"),
                n("gu2", 8, "head code_du_jeu/LICENSE", re = "$LIRE(?!.*petit_projet).*\\bLICENSE(\\s|$)", ou = "guilde"),
            )),
            "gu3" to Lecon("hist.gu3.titre", null, 1, listOf(
                n("gu3", 0, "guilde compiler", re = "${GU}compil", ou = A),
                n("gu3", 1, "cat bonjour.c", re = "$LIRE.*bonjour\\.c", ou = A),
                n("gu3", 2, "guilde gcc", re = "${GU}gcc\\b", ou = A),
            )),
            "gu4" to Lecon("hist.gu4.titre", null, 1, listOf(
                n("gu4", 0, "guilde contribution", fs = { j -> File(dossier(j), "$CONTRIB/langues/fr.txt").isFile }, ou = "guilde"),
                n("gu4", 3, "cat langues/fr.txt", re = "$LIRE.*fr\\.txt", ou = C),
                n("gu4", 4, "sed -i 's/?/?/' langues/fr.txt", fs = { j -> corrigee(j) }, ou = C),
                n("gu4", "t5", "diff .origine/fr.txt langues/fr.txt", re = "^diff\\b.*fr\\.txt", ou = C),
                n("gu4", 8, "guilde fusion", re = "${GU}fusion\\b", exploit = "guilde.artisan"),
            )),
            "gu5" to Lecon("hist.gu5.titre", null, 1, listOf(
                n("gu5", 0, "guilde piece", re = "${GU}pi[eè]ce\\b", ou = F),
                n("gu5", 1, "cat porte_cle.scad", re = "$LIRE.*porte_cle\\.scad", ou = F),
                n("gu5", 2, "guilde trou ? ?", fs = carnetOk("trou")),
                n("gu5", 3, "guilde volume ?", fs = carnetOk("volume")),
                n("gu5", 5, "guilde stl", fs = carnetOk("stl"), ou = F),
                n("gu5", 6, "head -3 porte_cle.stl", re = "$LIRE.*porte_cle\\.stl", ou = F),
            )),
            "gu6" to Lecon("hist.gu6.titre", null, 1, listOf(
                n("gu6", 0, "guilde sauver", re = "${GU}(sauver|vieux)", ou = V),
                n("gu6", 2, "guilde cle", re = "${GU}cl[eé]\\b", ou = V),
                n("gu6", 3, "sha256sum $IMAGE", re = "^sha256sum\\b.*image_linux", ou = V),
                n("gu6", 4, "sha256sum -c $IMAGE.sha256", re = "^sha256sum\\b.*(-c|--check)\\b", ou = V),
                n("gu6", 5, "guilde disques", re = "${GU}disques\\s*$", ou = V),
                n("gu6", 6, "guilde disque ?", fs = carnetOk("disque")),
                n("gu6", 7, "dd if=$IMAGE of=$CLE bs=64k", fs = { j -> cleCopiee(j) }, ou = V),
                n("gu6", 8, "sha256sum $IMAGE $CLE", re = "^sha256sum\\b.*cle_usb", ou = V),
                n("gu6", 9, "guilde certificat", fs = { j -> File(dossier(j), "vieux_pc/certificat_pc_sauve.txt").isFile }),
            )),
        )
    }

    // ---------------------------------------------------------------- l'arbre du Carrefour
    private fun monde(): JSONObject? {
        val ms = Programme.donnees().optJSONArray("mondes") ?: return null
        return (0 until ms.length()).map { ms.getJSONObject(it) }.firstOrNull { it.optString("id") == "guilde" }
    }

    private fun besoin(): Pair<List<String>, List<String>> {
        val m = monde() ?: return emptyList<String>() to emptyList()
        val tronc = Programme.donnees().optJSONObject("tronc") ?: JSONObject()
        return liste(m, "requis").flatMap { liste(tronc, it) }.distinct() to liste(m, "requis_lecons")
    }

    fun ouvert(jeu: Jeu): Boolean {
        val (chaps, lecs) = besoin()
        if (chaps.isEmpty() && lecs.isEmpty()) return false
        val f = Histoire.h(jeu).optJSONArray("faits")?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: emptyList()
        return chaps.all { Histoire.fini(jeu, it) } && lecs.all { it in f }
    }

    fun manque(jeu: Jeu): List<String> {
        val (chaps, lecs) = besoin()
        val f = Histoire.h(jeu).optJSONArray("faits")?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: emptyList()
        return chaps.filter { !Histoire.fini(jeu, it) }.map { Histoire.nomChapitre(it) } +
            lecs.filter { it !in f }.map { l -> val ch = Histoire.chapitreDeLecon(l)
                Histoire.tx("hist.$l.titre") + " (" + (ch?.let { Histoire.nomChapitre(it.id) } ?: "?") + ")" }
    }

    fun annonce(jeu: Jeu): Boolean {
        val h = Histoire.h(jeu)
        val deja = h.optJSONArray("mondes_annonces") ?: JSONArray().also { h.put("mondes_annonces", it) }
        if ((0 until deja.length()).any { deja.getString(it) == "guilde" } || Histoire.fini(jeu, "guilde") || !ouvert(jeu)) return false
        deja.put("guilde")
        jeu.log(t("gu.ouvert.log"))
        jeu.dire(Histoire.dire(jeu, "gu.ouvert.dit"), 18)
        return true
    }

    // ---------------------------------------------------------------- les indices
    private val REPONSES = mapOf("guilde libertes ? ? ? ?" to "libertes", "guilde gratuit ? ? ? ?" to "gratuit", "guilde licence ?" to "licence",
        "guilde faim ?" to "faim", "guilde trou ? ?" to "trou", "guilde volume ?" to "volume", "guilde disque ?" to "disque")
    private val TROU = Regex("(^|\\s)(\\?|…|<[^>]*>)(\\s|$)")
    val DEV = Regex("(\\bof=/dev/|>\\s*/dev/(sd|nvme|mmcblk|hd|vd|disk)|\\b(cp|cat|tee|dd|mv)\\b.*\\s/dev/(sd|nvme|mmcblk|hd|vd|disk))")

    fun indice(jeu: Jeu, e: Etape, tapees: List<Pair<String, String?>>): String? {
        val les = Histoire.leconCourante(jeu)?.id
        if (les !in IDS) return null
        val lignes = tapees.map { it.first.trim() }
        if (lignes.any { DEV.containsMatchIn(it) }) return t("gu.indice.dev")
        if (lignes.any { Regex("^sudo\\b").containsMatchIn(it) }) return t("gu.indice.sudo")
        if ("?" in e.cmd.split(" ") && lignes.filter { r(GU).containsMatchIn(it) || it.startsWith("sed ") }.any { TROU.containsMatchIn(it) })
            return t("gu.indice.trou")
        REPONSES[e.cmd]?.let { et ->
            val der = carnet(jeu).lines().lastOrNull { it.startsWith("[$et]") }
            if (der != null && !der.trimEnd().endsWith("(ok)")) {
                if (et == "disque") return t("gu.indice.disque." + (Regex("\\((\\w+)\\)\\s*$").find(der)?.groupValues?.get(1) ?: "inconnu"))
                if (et == "licence" && der.trimEnd().endsWith("(inconnu)")) return t("gu.indice.licence")
                return t("gu.indice.rep.$et")
            }
        }
        if (e.cmd.startsWith("sed ") && lignes.any { Regex("^sed\\b(?!.*\\s-i)").containsMatchIn(it) }) return t("gu.indice.sed_i")
        if (e.cmd.startsWith("sed ") && lignes.any { it.startsWith("sed") }) return t("gu.indice.faute")
        if (lignes.any { Regex("^dd\\b.*\\bif=\\S*cle_usb").containsMatchIn(it) }) return t("gu.indice.inverse")
        if (e.cmd.startsWith("dd ") && lignes.any { it.startsWith("dd") || it.startsWith("cp") }) return t("gu.indice.copie")
        return null
    }

    // ---------------------------------------------------------------- les commandes du jeu : guilde …
    private fun gStr(x: Double): String = if (x == Math.floor(x)) "${x.toLong()}" else "$x"

    fun lignesLibertes(jeu: Jeu, rep: List<String>): List<String> {
        val c = libertesCartes(Histoire.graine(jeu))
        if (rep.isEmpty()) return listOf("🗽 " + t("gu.libertes.titre"), "") + (0..3).map { "  $it · " + t("gu.liberte.$it") } + listOf("") +
            c.map { "  ${it.n}. " + t("gu.situation.${it.id}") } + listOf("", "  " + t("gu.libertes.aide"))
        val (bon, justes) = quizJustes(c, rep, "0123")
        if (!bon) return listOf(t("gu.libertes.aide"))
        val out = mutableListOf<String>()
        if (justes.size == c.size) { noter(jeu, "libertes", rep.joinToString(" ") + " (ok)"); out.add("✔ " + t("gu.libertes.ok")) }
        else { noter(jeu, "libertes", rep.joinToString(" ") + " (faux)"); out.add("✖ " + t("gu.quiz.faux", "n" to justes.size, "total" to c.size)) }
        justes.forEach { out.add("  ✔ ${it.n}. " + t("gu.situation.${it.id}.pourquoi")) }
        return out
    }

    fun lignesGratuit(jeu: Jeu, rep: List<String>): List<String> {
        val c = gratuitCartes(Histoire.graine(jeu))
        if (rep.isEmpty()) return listOf("🎁 " + t("gu.gratuit.titre"), "") + c.map { "  ${it.n}. " + t("gu.gratuit.${it.id}") } + listOf("", "  " + t("gu.gratuit.aide"))
        val (bon, justes) = quizJustes(c, rep, "lp")
        if (!bon) return listOf(t("gu.gratuit.aide"))
        val out = mutableListOf<String>()
        if (justes.size == c.size) { noter(jeu, "gratuit", rep.joinToString(" ") + " (ok)"); out += listOf("✔ " + t("gu.gratuit.ok"), "  " + t("gu.gratuit.morale")) }
        else { noter(jeu, "gratuit", rep.joinToString(" ") + " (faux)"); out.add("✖ " + t("gu.quiz.faux", "n" to justes.size, "total" to c.size)) }
        justes.forEach { out.add("  ✔ ${it.n}. " + t("gu.gratuit.${it.id}.pourquoi")) }
        return out
    }

    /** Sur le téléphone : seulement le catalogue de la Guilde (les licences des logiciels de l'appareil ne sont pas lisibles). */
    fun lignesLicence(jeu: Jeu, arg: String?): List<String> {
        if (arg.isNullOrBlank()) return listOf(t("gu.licence.aide", "total" to aTrouver()), t("gu.tel.licences"))
        val nom = asciiBas(arg).replace(Regex("[^a-z0-9.+_-]"), "")
        val fam = licenceCatalogue(nom)
        if (fam == null) { noter(jeu, "licence", "${nom.ifEmpty { "?" }} (inconnu)"); return listOf("? " + t("gu.licence.inconnue", "nom" to nom.ifEmpty { arg })) }
        noter(jeu, "licence", "$nom $fam (ok)")
        val nb = licencesTrouvees(jeu).size
        val jeuLui = if (nom == "terminagotchi") t("gu.licence.jeu").split("\n").map { "  $it" } else emptyList()   // le jeu lui-même
        return listOf("✔ $nom : ${nomLicence(fam)} (" + t("gu.licence.catalogue") + ")", "  " + t("gu.genre." + genreLicence(fam))) + jeuLui +
            listOf("  " + (if (nb < aTrouver()) t("gu.licence.encore", "n" to nb, "total" to aTrouver()) else t("gu.licence.fini", "n" to nb)))
    }

    fun lignesFaim(jeu: Jeu, arg: String?): List<String> {
        if (!codeDuJeu(jeu).isDirectory) return listOf(t("gu.faim.sans_code"))
        if (arg.isNullOrBlank()) return listOf(t("gu.faim.aide"))
        val fichiers = fichiersDuCode(jeu)
        val att = faimFichiers(fichiers)
        if (faimOk(arg, att)) {
            noter(jeu, "faim", "${att[0]} (ok)")
            val txt = fichiers.entries.firstOrNull { it.key.substringAfterLast("/") == att[0] }?.value ?: ""
            val m = Regex(liste(o("faim"), "marques").first() + ".*?(?=^\\S)", setOf(RegexOption.MULTILINE, RegexOption.DOT_MATCHES_ALL)).find(txt)
            return listOf("✔ " + t("gu.faim.ok", "fichier" to att[0])) + (m?.value?.trimEnd()?.split("\n")?.take(8)?.map { "  $it" } ?: emptyList()) +
                ("  " + t("gu.faim.morale"))
        }
        noter(jeu, "faim", "${asciiBas(arg).take(40)} (faux)")
        return listOf("✖ " + t("gu.faim.faux"))
    }

    fun dessinPiece(p: Piece, trou: Boolean = true): List<String> {
        val w = maxOf(6, p.longueur / 2); val h = maxOf(3, p.largeur / 4)
        val tx = p.trouX / 2; val ty = h - 1 - p.trouY / 4
        return listOf("┌" + "─".repeat(w) + "┐") + (0 until h).map { rr ->
            val l = CharArray(w) { '█' }
            if (trou && rr == ty.coerceIn(0, h - 1)) l[minOf(w - 1, tx)] = '○'
            "│" + String(l) + "│"
        } + listOf("└" + "─".repeat(w) + "┘")
    }

    fun lignesTrou(jeu: Jeu, rep: List<String>): List<String> {
        val gr = Histoire.graine(jeu)
        if (rep.size < 2) return listOf(t("gu.trou.aide"))
        val p = piece(gr)
        if (trouOk(rep, gr)) { noter(jeu, "trou", "${p.trouX} ${p.trouY} (ok)"); return listOf("✔ " + t("gu.trou.ok", "x" to p.trouX, "y" to p.trouY), "  " + t("gu.trou.morale")) }
        noter(jeu, "trou", rep.take(2).joinToString(" ") + " (faux)")
        return listOf("✖ " + t("gu.trou.faux"))
    }

    fun lignesVolume(jeu: Jeu, arg: String?): List<String> {
        val gr = Histoire.graine(jeu)
        if (arg.isNullOrBlank()) return listOf(t("gu.volume.aide"))
        if (volumeOk(arg, gr)) { val v = volume(gr); noter(jeu, "volume", "$v (ok)")
            return listOf("✔ " + t("gu.volume.ok", "v" to v, "cm" to gStr(v / 1000.0)), "  " + t("gu.volume.morale")) }
        noter(jeu, "volume", "$arg (faux)")
        return listOf("✖ " + t("gu.volume.faux"))
    }

    fun lignesStl(jeu: Jeu): List<String> {
        val p = piece(Histoire.graine(jeu))
        val f = File(dossier(jeu), "fabrique/porte_cle.stl")
        var parJeu = false
        if (!f.isFile) { ecrire(jeu, "fabrique/porte_cle.stl", stlBoite(p.longueur, p.largeur, p.epaisseur)); parJeu = true }
        val inf = stlInfos(lireOctets(jeu, "fabrique/porte_cle.stl") ?: ByteArray(0))
        if (inf == null) { noter(jeu, "stl", "illisible (faux)"); return listOf("✖ " + t("gu.stl.illisible")) }
        noter(jeu, "stl", (if (parJeu) "jeu" else "openscad") + " ${inf.n} (ok)")
        return listOf("🧊 " + t("gu.stl.titre"), "") + (if (parJeu) listOf("  " + t("gu.stl.par_le_jeu")) else emptyList()) +
            dessinPiece(p, !parJeu).map { "  $it" } +
            listOf("  " + t("gu.stl.infos", "n" to inf.n, "x" to gStr(inf.dims[0]), "y" to gStr(inf.dims[1]), "z" to gStr(inf.dims[2])), "",
                "  " + t("gu.stl.morale"), "  " + t("gu.stl.adulte"))
    }

    fun lignesDisques(jeu: Jeu): List<String> {
        val gr = Histoire.graine(jeu)
        val go = cleDisque(gr).second
        noter(jeu, "disques", "vus (ok)")
        val rows = disques(gr)
        return listOf("🔍 " + t("gu.disques.titre"), "", "  " + t("gu.disques.fictif"), "", "  NAME       RM  SIZE TYPE MOUNT") +
            rows.mapIndexed { k, x ->
                val pref = if (x.type == "part") (if (k + 1 >= rows.size || rows[k + 1].type != "part") "└─" else "├─") else ""
                "  ${(pref + x.nom).padEnd(10)} ${x.rm}  ${x.taille.padStart(6)} ${x.type} ${x.point}" } +
            listOf("", "  " + t("gu.disques.question", "go" to go), "  " + t("gu.disques.aide"))
    }

    fun lignesDisque(jeu: Jeu, arg: String?): List<String> {
        val gr = Histoire.graine(jeu)
        if (arg.isNullOrBlank()) return listOf(t("gu.disque.aide"))
        if (disqueOk(arg, gr)) { val (nom, go) = cleDisque(gr); noter(jeu, "disque", "$nom (ok)")
            return listOf("✔ " + t("gu.disque.ok", "nom" to nom, "go" to go), "  " + t("gu.disque.morale")) }
        val err = disqueErreur(arg, gr)
        noter(jeu, "disque", "${asciiBas(arg).take(20)} ($err)")
        return listOf("✖ " + t("gu.indice.disque.$err"))
    }

    fun lignesCertificat(jeu: Jeu): List<String> {
        if (!cleCopiee(jeu)) return listOf("✖ " + t("gu.certificat.pas_encore"))
        if (!dansCarnet(jeu, "disque")) return listOf("✖ " + t("gu.certificat.disque"))
        val date = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.ROOT).format(java.util.Date())
        val texte = t("gu.certificat.texte", "nom" to jeu.nom, "date" to date, "empreinte" to imageSha().take(16))
        ecrire(jeu, "vieux_pc/certificat_pc_sauve.txt", texte + "\n")
        noter(jeu, "certificat", "pc_sauve (ok)")
        return listOf("🏅 " + t("gu.certificat.titre"), "") + texte.split("\n").map { "  $it" } + listOf("", "  " + t("gu.certificat.morale"))
    }

    private fun bloc(cle: String) = t(cle).split("\n").map { "  $it" }

    /** L'entrée de la Guilde en caractères : le REPLI de l'illustration B13 (le dessin graphique est GuildeDessin.guilde). */
    val GUILDE_DESSIN = listOf("    ┌─┬─┬─┬─┐  ⚙", " ╭──┴─┴─┴─┴─┴──╮", " │ ▤ ▤  🛠  ▤ ▤ │", " │ ▤ ▤ ╭──╮ ▤ ▤ │", "▁│▁▁▁▁▁│▒▒│▁▁▁▁▁│▁")

    /** guilde [plan|libertes|licence|gratuit|depot|copie|faim|compiler|gcc|contribution|fusion|piece|trou|volume|stl|
     *  sauver|cle|disques|disque|certificat] */
    fun commande(jeu: Jeu, reste: String, ici: File): String {
        val m = reste.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        val sous = asciiBas(m.getOrNull(0) ?: "aide").replace("œ", "oe").replace("-", "_")
        val a = m.drop(1).filter { it != "?" && it != "…" }
        etat(jeu)
        val l: List<String> = when (sous) {
            "plan", "mur", "regles" -> GUILDE_DESSIN + t("gu.meuble.mur", "nom" to jeu.nom).split("\n")
            "libertes", "liberte" -> lignesLibertes(jeu, a)
            "licence", "licences", "license" -> lignesLicence(jeu, a.getOrNull(0))
            "gratuit", "gratuits" -> lignesGratuit(jeu, a)
            "depot", "depots" -> { noter(jeu, "depot", "lu (ok)"); listOf("📦 " + t("gu.depot.titre"), "") + bloc("gu.depot.texte") + listOf("", "  " + t("gu.tel.raconte", "outil" to "git")) }
            "copie" -> { val n = poserCopie(jeu); noter(jeu, "copie", "copie $n (ok)"); listOf("✔ " + t("gu.copie.posee", "n" to n), "  " + t("gu.tel.copie")) }
            "faim" -> lignesFaim(jeu, a.getOrNull(0))
            "compiler", "compile", "compilateur" -> { noter(jeu, "compiler", "lu (ok)")
                listOf("⚙ " + t("gu.compiler.titre"), "", "  📄 bonjour.c ─⚙ gcc─▶ 🧩 bonjour", "") + bloc("gu.compiler.texte") }
            "gcc" -> { noter(jeu, "gcc", "raconte (ok)"); listOf("🔧 " + t("gu.gcc.titre"), "", "  " + t("gu.tel.gcc"), "  " + t("gu.tel.raconte", "outil" to "gcc, make")) }
            "contribution", "contribuer" -> { val pret = poserContribution(jeu); noter(jeu, "contribution", "fichiers (ok)")
                listOf("🤝 " + t("gu.contrib.titre"), "") + bloc("gu.contrib.texte") + listOf("", "  " + t(if (pret) "gu.contrib.pret_sans_git" else "gu.contrib.rate"),
                    "  " + t("gu.tel.raconte", "outil" to "git")) }
            "fusion", "credits" -> { val ok = corrigee(jeu); noter(jeu, "fusion", (if (ok) "prete" else "pas_prete") + " (ok)")
                listOf("🔀 " + t("gu.fusion.titre"), "") + bloc("gu.fusion.texte") + listOf("", "  " + t(if (ok) "gu.fusion.prete" else "gu.fusion.pas_prete"), "",
                    "📜 " + t("gu.credits.titre")) + creditsTexte().trimEnd().split("\n").map { "  $it" } + listOf("", "  " + progresContributeur(jeu) + "  (`guilde badges`)") }
            "badges", "badge" -> lignesBadges(jeu)
            "piece", "porte_cle" -> { val p = piece(Histoire.graine(jeu)); noter(jeu, "piece", "vue (ok)")
                listOf("🖨 " + t("gu.piece.titre"), "") + dessinPiece(p).map { "  $it" } + listOf("  " + t("gu.piece.mesures", "L" to p.longueur, "l" to p.largeur, "h" to p.epaisseur), "") + bloc("gu.piece.texte") }
            "trou" -> lignesTrou(jeu, a)
            "volume" -> lignesVolume(jeu, a.joinToString(" ").ifEmpty { null })
            "stl" -> lignesStl(jeu)
            "sauver", "vieux_pc", "vieux", "pc" -> { noter(jeu, "vieux_pc", "lu (ok)"); listOf("💻 " + t("gu.vieux.titre"), "") + bloc("gu.vieux.texte") }
            "cle", "cles" -> { poserCle()(jeu); noter(jeu, "cle", "posee (ok)")
                listOf("💾 " + t("gu.cle.titre"), "", "  📀 $IMAGE (${IM.optInt("octets") / 1024} Kio)", "  📄 $IMAGE.sha256", "  🔑 $CLE (${IM.optInt("cle_octets") / 1024} Kio)", "") + bloc("gu.cle.texte") }
            "disques" -> lignesDisques(jeu)
            "disque" -> lignesDisque(jeu, a.getOrNull(0))
            "certificat" -> lignesCertificat(jeu)
            else -> GUILDE_DESSIN + listOf("🛠 " + t("gu.aide.titre")) + t("gu.aide.liste").split("\n").map { "  $it" }
        }
        return l.joinToString("\n")
    }
}
