package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.text.Normalizer
import java.util.Locale

/**
 * 🔨 La Forge (docs/programme.md § 2.10 et § 7.13 « Ton site web », « L'atelier multimédia »), portage de pc/tg/forge.py.
 *
 * Les scripts de l'enfant s'écrivent et se lancent dans le terrain (terrain_terminagotchi/forge) ; l'appli n'exécute
 * elle-même aucun script de l'enfant. Mêmes paliers que sur PC (fo0 → fo7), avec les variantes du téléphone :
 *  - sh marche ; ./ (le droit x dans les fichiers de l'appli) et read au clavier non : on lance avec sh, et read reçoit
 *    sa réponse par un tuyau (echo Léa | sh question.sh) ; chaque ligne est un nouveau shell (nom=Pixel; echo $nom) ;
 *  - pas de Python : le serpent est raconté (le Traceback que Python écrirait), puis le jeu construit dans l'appli (doom) ;
 *  - le site est servi par l'appli (`forge serveur`, attachée à 127.0.0.1 comme la lanterne du Port), lu avec curl ;
 *  - magick, sox, ffmpeg et exiftool n'existent pas : racontés ; la photo d'exemple (métadonnées INVENTÉES) se lit avec
 *    `forge exif` et se nettoie avec `forge nettoie` (seulement les fichiers du terrain).
 * Exploits « forge.premier_coup » et « forge.sans_indice ». Vecteurs communs donnees/forge/vecteurs.json (tests/jvm/Forge.kt).
 */
object Forge {
    @Volatile var chargeur: (() -> String?)? = null
    private var d: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("forge.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun donnees(): JSONObject = d ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() }).also { d = it }
    private fun liste(o: JSONObject?, k: String): List<String> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.get(it).toString() } } ?: emptyList()
    private fun objets(o: JSONObject?, k: String): List<JSONObject> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.getJSONObject(it) } } ?: emptyList()
    private fun o(k: String) = donnees().optJSONObject(k) ?: JSONObject()

    // ================================================================ la spécification pure (vecteurs communs)
    fun asciiId(texte: String?): String = Normalizer.normalize(texte ?: "", Normalizer.Form.NFKD)
        .filter { Character.getType(it) != Character.NON_SPACING_MARK.toInt() }.lowercase(Locale.ROOT).trim()

    fun octetsGraine(graine: String, sel: String): ByteArray = MessageDigest.getInstance("SHA-256").digest("$graine:$sel".toByteArray(Charsets.UTF_8))

    /** La boucle de la question « combien de tours ? » : for i in $(seq A Z). */
    fun toursQuestion(graine: String): Pair<Int, Int> {
        val b = octetsGraine(graine, "tours")
        val a = 2 + (b[0].toInt() and 0xFF) % 4
        return a to a + 4 + (b[1].toInt() and 0xFF) % 6
    }
    fun toursReponse(a: Int, z: Int) = z - a + 1

    private val SHEBANG = Regex("^#!\\s*/(usr/)?bin/(env\\s+)?(ba|da|k|mk|z)?sh\\b")
    private fun lignesTexte(texte: String): List<String> {
        if (texte.isEmpty()) return emptyList()
        val l = texte.split(Regex("\r\n|\n|\r"))
        return if (l.last().isEmpty()) l.dropLast(1) else l
    }

    /** Ce que la recette de la cabane contient déjà : la première ligne magique, le mkdir, le touch. */
    fun recetteEtat(texte: String?): Map<String, Boolean> {
        val l = lignesTexte(texte ?: "")
        return mapOf("shebang" to (l.isNotEmpty() && SHEBANG.containsMatchIn(l[0].trim()) && SHEBANG.find(l[0].trim())!!.range.first == 0),
            "mkdir" to l.any { Regex("^\\s*mkdir\\b.*\\bcabane\\b").containsMatchIn(it) },
            "touch" to l.any { Regex("^\\s*touch\\b.*\\bcabane/\\S").containsMatchIn(it) })
    }
    fun recetteComplete(texte: String?) = recetteEtat(texte).values.all { it }

    /** Le nom que l'enfant donne à son jeu (pour la carte) : lettres, chiffres, espaces, ' et -, 40 caractères. */
    fun nomDuJeu(texte: String?): String {
        val s = (texte ?: "").filter { it.isLetterOrDigit() || it in " '-’" }.trim()
        return s.replace(Regex("\\s+"), " ").take(40).trim()
    }

    /** Un texte traduit posé dans un script sh entre guillemets doubles : ni guillemet, ni $, ni `, ni \. */
    fun sur(texte: String?) = (texte ?: "").replace("\"", "'").replace("$", "").replace("`", "'").replace("\\", "/")

    // ---------------------------------------------------------------- le JPEG d'exemple et ses métadonnées (EXIF)
    private fun u8(o: ByteArray, i: Int) = o[i].toInt() and 0xFF

    /** [(marqueur, début des données, fin)] des segments d'un JPEG, jusqu'au début de l'image (SOS) ; null sinon. */
    fun segmentsJpeg(o: ByteArray): List<Triple<Int, Int, Int>>? {
        if (o.size < 4 || u8(o, 0) != 0xFF || u8(o, 1) != 0xD8) return null
        val out = mutableListOf<Triple<Int, Int, Int>>()
        var i = 2
        while (i + 4 <= o.size) {
            if (u8(o, i) != 0xFF) return null
            val m = u8(o, i + 1)
            if (m == 0xFF) { i += 1; continue }
            if (m == 0xD8 || m == 0x01 || m in 0xD0..0xD7) { i += 2; continue }
            val n = (u8(o, i + 2) shl 8) or u8(o, i + 3)
            if (n < 2 || i + 2 + n > o.size) return null
            out.add(Triple(m, i + 4, i + 2 + n))
            if (m == 0xDA) break
            i += 2 + n
        }
        return out
    }

    private val EXIF = "Exif\u0000\u0000".toByteArray(Charsets.ISO_8859_1)
    private fun estExif(o: ByteArray, a: Int, b: Int) = b - a >= 6 && (0 until 6).all { o[a + it] == EXIF[it] }
    private fun app1Exif(o: ByteArray): ByteArray? {
        for ((m, a, b) in segmentsJpeg(o) ?: return null) if (m == 0xE1 && estExif(o, a, b)) return o.copyOfRange(a + 6, b)
        return null
    }
    fun aExif(o: ByteArray) = app1Exif(o) != null

    private val TAGS = mapOf(0x010E to "description", 0x010F to "marque", 0x0110 to "modele", 0x0132 to "date", 0x9003 to "date_orig",
        0x0001 to "lat_ref", 0x0002 to "lat", 0x0003 to "lon_ref", 0x0004 to "lon")

    /** Les métadonnées lisibles d'un JPEG : [(nom, valeur)] (marque, modèle, dates, GPS), [] s'il n'y en a pas, null si ce
     *  n'est pas un JPEG. Même lecture que forge.exif_de sur PC (TIFF II ou MM ; IFD0, Exif IFD, GPS IFD). */
    fun exifDe(o: ByteArray): List<Pair<String, String>>? {
        if (segmentsJpeg(o) == null) return null
        val tiff = app1Exif(o) ?: return emptyList()
        if (tiff.size < 8) return emptyList()
        val be = tiff[0] == 'M'.code.toByte() && tiff[1] == 'M'.code.toByte()
        fun u16(p: Int): Int = if (p + 2 > tiff.size) 0 else if (be) (u8(tiff, p) shl 8) or u8(tiff, p + 1) else (u8(tiff, p + 1) shl 8) or u8(tiff, p)
        fun u32(p: Int): Long = if (p + 4 > tiff.size) 0L else if (be) ((u16(p).toLong() shl 16) or u16(p + 2).toLong()) else ((u16(p + 2).toLong() shl 16) or u16(p).toLong())
        val texte = HashMap<String, String>()
        val nombres = HashMap<String, List<Double>>()
        fun ifd(p: Int, gps: Boolean, prof: Int) {
            if (prof > 3 || p + 2 > tiff.size) return
            for (k in 0 until u16(p)) {
                val e = p + 2 + 12 * k
                if (e + 12 > tiff.size) return
                val tag = u16(e); val typ = u16(e + 2); val n = u32(e + 4)
                val taille = (mapOf(1 to 1, 2 to 1, 3 to 2, 4 to 4, 5 to 8, 7 to 1)[typ] ?: 1) * n
                val dp = if (taille <= 4) e + 8 else u32(e + 8).toInt()
                if (!gps && (tag == 0x8769 || tag == 0x8825)) { ifd(u32(e + 8).toInt(), tag == 0x8825, prof + 1); continue }
                if ((tag >= 0x0005 && gps) || (!gps && tag !in setOf(0x010E, 0x010F, 0x0110, 0x0132, 0x9003))) continue
                if (gps && tag !in 1..4) continue
                if (typ == 2) {
                    val fin = minOf(tiff.size, dp + n.toInt()).coerceAtLeast(dp.coerceAtMost(tiff.size))
                    val brut = if (dp in 0..tiff.size) tiff.copyOfRange(dp, fin) else ByteArray(0)
                    val z = brut.indexOf(0).let { if (it < 0) brut.size else it }
                    texte[TAGS.getValue(tag)] = String(brut, 0, z, Charsets.ISO_8859_1).trim()
                } else if (typ == 5 && n == 3L) {
                    nombres[TAGS.getValue(tag)] = (0 until 3).map { j -> u32(dp + 8 * j).toDouble() / maxOf(1L, u32(dp + 8 * j + 4)) }
                }
            }
        }
        ifd(u32(4).toInt(), false, 0)
        val out = mutableListOf<Pair<String, String>>()
        for (k in listOf("marque", "modele", "date", "date_orig", "description")) texte[k]?.let { out.add(k to it) }
        for ((c, ref) in listOf("lat" to "lat_ref", "lon" to "lon_ref")) nombres[c]?.let { (dd, mm, ss) ->
            out.add(c to ("${dd.toInt()}° ${mm.toInt()}' " + String.format(Locale.ROOT, "%.2f", ss) + "\" " + (texte[ref] ?: "")).trim())
        }
        return out
    }

    /** Le même JPEG sans ses segments de métadonnées Exif (APP1) : l'image ne change pas. */
    fun sansExif(o: ByteArray): ByteArray {
        val seg = segmentsJpeg(o) ?: return o
        val out = java.io.ByteArrayOutputStream()
        out.write(o, 0, 2)
        var i = 2
        for ((m, a, b) in seg) {
            val debut = a - 4
            out.write(o, i, debut - i)
            if (!(m == 0xE1 && estExif(o, a, b))) out.write(o, debut, b - debut)
            i = b
        }
        out.write(o, i, o.size - i)
        return out.toByteArray()
    }

    fun photoOctets(): ByteArray = java.util.Base64.getDecoder().decode(o("photo").optString("base64"))

    /** Le nombre d'images d'un GIF (0 si ce n'est pas un GIF lisible). */
    fun imagesGif(o: ByteArray): Int {
        if (o.size < 13) return 0
        val tete = String(o, 0, 6, Charsets.ISO_8859_1)
        if (tete != "GIF87a" && tete != "GIF89a") return 0
        var i = 13 + if (u8(o, 10) and 0x80 != 0) 3 * (1 shl ((u8(o, 10) and 7) + 1)) else 0
        var n = 0
        fun sauter(j0: Int): Int { var j = j0; while (j < o.size && u8(o, j) != 0) j += u8(o, j) + 1; return j + 1 }
        while (i < o.size) {
            when (u8(o, i)) {
                0x3B -> return n
                0x21 -> i = sauter(i + 2)
                0x2C -> {
                    if (i + 10 > o.size) return n
                    val f = u8(o, i + 9)
                    i += 10 + if (f and 0x80 != 0) 3 * (1 shl ((f and 7) + 1)) else 0
                    i = sauter(i + 1)
                    n++
                }
                else -> return n
            }
        }
        return n
    }

    fun wavOk(o: ByteArray) = o.size > 44 && String(o, 0, 4, Charsets.ISO_8859_1) == "RIFF" && String(o, 8, 4, Charsets.ISO_8859_1) == "WAVE"

    // ---------------------------------------------------------------- la vue déployée : l'atelier de la forge
    private val SEPARATEURS = Regex("\\|\\||&&|[|;&]")
    class Atelier(val outil: String, val objet: String, val de: String, val vers: String)
    fun forgeDe(morceau: String?): Atelier? {
        val m = (morceau ?: "").trim()
        for (r in objets(o("atelier"), "regles")) if (Regex(r.optString("motif")).containsMatchIn(m))
            return Atelier(r.optString("outil"), r.optString("objet"), r.optString("de"), r.optString("vers"))
        return null
    }
    fun forgesDe(ligne: String?): List<Atelier> = (ligne ?: "").split(SEPARATEURS).mapNotNull { forgeDe(it) }

    // ---------------------------------------------------------------- ce que le jeu pose dans la forge (mêmes textes que le PC)
    fun serpentPy(): String {
        val salut = sur(t("fo.serpent.salut", "nom" to "{nom}")).replace("'", "’")
        return "# " + t("fo.serpent.com1") + "\n# " + t("fo.serpent.com2") + " python3 serpent.py NOM FOIS\n" +
            "import sys\n\n" +
            "nom = sys.argv[1]          # " + t("fo.serpent.com3") + "\n" +
            "fois = int(sys.argv[2])    # " + t("fo.serpent.com4") + "\n\n" +
            "for i in range(fois):\n" +
            "    print(f\"{i + 1}. " + salut + "\")\n"
    }

    fun devinetteSh(): String = ("#!/bin/sh\n" +
        "# " + sur(t("fo.devinette.com")) + "\n" +
        "secret=\$(( \$(date +%s) % 10 + 1 ))\n" +
        "essais=0\n" +
        "reponse=0\n" +
        "echo \"" + sur(t("fo.devinette.debut")) + "\"\n" +
        "while [ \"\$reponse\" != \"\$secret\" ]; do\n" +
        "  read reponse || exit 1\n" +
        "  essais=\$((essais + 1))\n" +
        "  if [ \"\$reponse\" -lt \"\$secret\" ] 2>/dev/null; then\n" +
        "    echo \"" + sur(t("fo.devinette.plus")) + "\"\n" +
        "  elif [ \"\$reponse\" -gt \"\$secret\" ] 2>/dev/null; then\n" +
        "    echo \"" + sur(t("fo.devinette.moins")) + "\"\n" +
        "  fi\n" +
        "done\n" +
        "echo \"" + sur(t("fo.devinette.bravo", "n" to "@@")) + "\"\n").replace("@@", "\$essais")

    // ================================================================ l'état, le terrain, le carnet de la forge
    fun etat(jeu: Jeu): JSONObject {
        val c = jeu.module("forge")
        if (c.optJSONArray("faits") == null) c.put("faits", JSONArray())
        return c
    }
    private fun faits(jeu: Jeu) = liste(etat(jeu), "faits")
    private fun fait(jeu: Jeu, cle: String): Boolean {
        if (cle in faits(jeu)) return true
        etat(jeu).getJSONArray("faits").put(cle)
        return false
    }

    const val CARNET = "carnet_de_la_forge.txt"
    fun dossier(jeu: Jeu) = File(jeu.terrain, "forge")
    fun noter(jeu: Jeu, etiquette: String, texte: String) { try { dossier(jeu).mkdirs(); File(dossier(jeu), CARNET).appendText("[$etiquette] $texte\n") } catch (e: Exception) { } }
    fun carnet(jeu: Jeu): String = try { File(dossier(jeu), CARNET).readText() } catch (e: Exception) { "" }
    fun dansCarnet(jeu: Jeu, etiquette: String, motCle: String = "ok") = Regex("^\\[$etiquette].*\\($motCle\\)\\s*$", RegexOption.MULTILINE).containsMatchIn(carnet(jeu))
    fun dernier(jeu: Jeu, etiquette: String): String? = carnet(jeu).lines().lastOrNull { it.startsWith("[$etiquette]") }
    private fun ecrire(jeu: Jeu, rel: String, contenu: Any) = Histoire.ecrire(jeu, "forge/$rel", contenu, finLigne = false)
    private fun lire(jeu: Jeu, rel: String): String? = Histoire.lire(jeu, "forge/$rel")
    private fun octets(jeu: Jeu, rel: String): ByteArray? = try { File(dossier(jeu), rel).readBytes() } catch (e: Exception) { null }

    fun meubles(jeu: Jeu): Map<String, Any> = linkedMapOf("forge/enclume.txt" to t("fo.meuble.enclume") + "\n",
        "forge/$CARNET" to t("fo.meuble.carnet") + "\n")

    val SANS_INDICE = setOf("fo1", "fo2", "fo3", "fo4", "fo5", "fo6", "fo7")

    fun meubler(jeu: Jeu, lid: String?) {
        val dd = dossier(jeu)
        if (!dd.isDirectory || lid == null) return
        val step = jeu.etape
        if (lid == "fo0" && !File(dd, "enclume.txt").exists()) ecrire(jeu, "enclume.txt", t("fo.meuble.enclume") + "\n")
        if (lid == "fo4" && !File(dd, "serpent.py").exists()) ecrire(jeu, "serpent.py", serpentPy())
        if (lid == "fo5" && step >= 1 && !File(dd, "mon_jeu/devinette.sh").exists()) ecrire(jeu, "mon_jeu/devinette.sh", devinetteSh())
        if (lid == "fo6" && step >= 1) File(dd, "site").mkdirs()
        if (lid == "fo7" && step >= 2 && step <= 4 && !File(dd, "multimedia/photo_exemple.jpg").exists()) ecrire(jeu, "multimedia/photo_exemple.jpg", photoOctets())
        if (lid in SANS_INDICE && !jeu.indiceLecon.isNullOrEmpty() && "indice:$lid" !in faits(jeu)) etat(jeu).getJSONArray("faits").put("indice:$lid")
        val e = Programme.donnees().optJSONObject("etapes")?.optJSONObject("$lid.$step")
        if (e != null) for (mid in liste(e, "maths")) {
            if (Maths.noeud(mid) != null && !Maths.sait(jeu, mid) && !fait(jeu, "pont:$mid")) {
                jeu.dire(t("fo.pont", "notion" to Maths.titre(mid), "cmd" to "maths $mid"), 16)
                break
            }
        }
    }

    /** Un palier fini sans aucun indice : l'exploit « forge.sans_indice » (une fois). */
    fun leconFinie(jeu: Jeu, lid: String) {
        if (lid !in SANS_INDICE) return
        if ("indice:$lid" in faits(jeu) || !jeu.indiceLecon.isNullOrEmpty()) return
        Recompenses.exploit(jeu, "forge.sans_indice")?.let { m ->
            jeu.log(m)
            jeu.dire("✨ " + t("fo.sans_indice", "palier" to Histoire.tx("hist.$lid.titre")) + " " + m, 18)
        }
    }

    /** La première fois que la recette COMPLÈTE de la cabane est lancée, si la cabane est bâtie : « forge.premier_coup ». */
    fun surveiller(jeu: Jeu, ligne: String?) {
        if ("essai_cabane" in faits(jeu)) return
        val l = (ligne ?: "").trim()
        if (!Regex("^((sh|bash|dash)\\s+(\\./)?|\\./)cabane\\.sh\\b").containsMatchIn(l)) return
        if (!recetteComplete(lire(jeu, "cabane.sh"))) return
        etat(jeu).getJSONArray("faits").put("essai_cabane")
        if (cabaneOk(jeu)) Recompenses.exploit(jeu, "forge.premier_coup")?.let { m ->
            jeu.log(m)
            jeu.dire("🔥 " + t("fo.premier_coup") + " " + m, 18)
        }
    }

    // ---------------------------------------------------------------- les vérifications des étapes
    fun cabaneOk(jeu: Jeu) = File(dossier(jeu), "cabane/porte.txt").isFile && File(dossier(jeu), "cabane/toit.txt").isFile
    private fun contient(jeu: Jeu, rel: String, motif: String) = Regex(motif).containsMatchIn(lire(jeu, rel) ?: "")
    fun villageOk(jeu: Jeu) = (1..10).all { File(dossier(jeu), "village/cabane_$it").isDirectory }
    fun donjonOk(jeu: Jeu) = (1..3).all { File(dossier(jeu), "mon_jeu/donjon/salle_$it").isDirectory }
    fun photoPropre(jeu: Jeu): Boolean { val p = octets(jeu, "multimedia/photo_exemple.jpg") ?: return false; return segmentsJpeg(p) != null && !aExif(p) }
    fun htmlOk(jeu: Jeu) = contient(jeu, "site/index.html", "(?i)<h1[^>]*>.+</h1>")
    fun titreDuSite(jeu: Jeu): String? = Regex("(?is)<h1[^>]*>(.*?)</h1>").find(lire(jeu, "site/index.html") ?: "")?.groupValues?.get(1)?.trim()
    fun portSite() = o("site").optInt("port", 8642)
    fun serveurOk(jeu: Jeu) = dansCarnet(jeu, "serveur") && portSite() in Phare.actifs()
    fun arreteOk(jeu: Jeu) = dansCarnet(jeu, "serveur") && portSite() !in Phare.actifs()

    // ---------------------------------------------------------------- les leçons du téléphone
    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)
    private const val LS = "^(ls|dir)\\b"
    private const val LIRE = "^(cat|less|more|head|tail)\\b"
    private const val FO = "^(tg\\s+)?forge\\s+"
    private const val SH = "^(sh|bash|dash)\\s+"
    private const val O_ = "forge"

    private fun n(lid: String, i: Any, cmd: String, re: String? = null, fs: ((Jeu) -> Boolean)? = null, ou: String? = null,
                  toutCode: Boolean = false) =
        Etape("hist.$lid.$i.dit", cmd, "hist.$lid.$i.bravo", re?.let { r(it) }, fs, null, null, ou, toutCode = toutCode)

    val IDS = (0..7).map { "fo$it" }

    /** Les leçons du téléphone : les mêmes paliers, avec les variantes du téléphone (voir l'en-tête). */
    fun lecons(jeu: Jeu): Map<String, Lecon> {
        val carnetOk = { et: String -> { j: Jeu -> dansCarnet(j, et) } }
        val etatRecette = { j: Jeu -> recetteEtat(lire(j, "cabane.sh")) }
        return linkedMapOf(
            "fo0" to Lecon("hist.fo0.titre", null, 1, listOf(
                Etape("hist.entree.dit", "cd ~/terrain_terminagotchi/forge", "hist.entree.bravo", ici = "forge", params = mapOf("piece" to "forge")),
                n("fo0", 1, "ls", re = LS, ou = O_),
                n("fo0", 2, "cat enclume.txt", re = "$LIRE.*enclume", ou = O_),
            )),
            // ./ et chmod +x : pas dans les fichiers de l'appli (on lance avec sh)
            "fo1" to Lecon("hist.fo1.titre", null, 1, listOf(
                n("fo1", 0, "forge recette", re = "${FO}recettes?\\s*$"),
                n("fo1", 1, "echo '#!/bin/sh' > cabane.sh", fs = { j -> etatRecette(j).getValue("shebang") }, ou = O_),
                n("fo1", 2, "echo 'mkdir -p cabane' >> cabane.sh", fs = { j -> etatRecette(j).let { it.getValue("shebang") && it.getValue("mkdir") } }, ou = O_),
                n("fo1", 3, "echo 'touch cabane/porte.txt cabane/toit.txt' >> cabane.sh", fs = { j -> recetteComplete(lire(j, "cabane.sh")) }, ou = O_),
                n("fo1", 4, "cat cabane.sh", re = "$LIRE.*cabane\\.sh", ou = O_),
                n("fo1", 5, "sh cabane.sh", fs = { j -> cabaneOk(j) }, ou = O_),
            )),
            // chaque ligne est un nouveau shell : la boîte se remplit et s'ouvre sur la même ligne ; read reçoit un tuyau
            "fo2" to Lecon("hist.fo2.titre", null, 1, listOf(
                n("fo2", 0, "forge boites", re = "${FO}bo[iî]tes?\\s*$"),
                n("fo2", 10, "nom=Pixel; echo \"Bonjour \$nom\"", re = "^echo\\b.*\\$\\{?[A-Za-z_]\\w*"),
                n("fo2", 3, "echo 'echo \"Bonjour \$1 !\"' > salut.sh", fs = { j -> contient(j, "salut.sh", "\\$\\{?1\\b") }, ou = O_),
                n("fo2", 4, "sh salut.sh Léa", re = "${SH}salut\\.sh\\s+\\S", ou = O_),
                n("fo2", 5, "echo 'echo \"Tu as donné \$# prénoms.\"' >> salut.sh", fs = { j -> contient(j, "salut.sh", "\\$#") }, ou = O_),
                n("fo2", 6, "sh salut.sh Léa Tom Sam", re = "${SH}salut\\.sh(\\s+\\S+){2,}", ou = O_),
                n("fo2", 7, "echo 'read prenom' > question.sh && echo 'echo \"Salut \$prenom !\"' >> question.sh",
                    fs = { j -> contient(j, "question.sh", "(^|\\s)read\\s+\\w+") }, ou = O_),
                n("fo2", 9, "echo Léa | sh question.sh", re = "\\|\\s*(sh|bash)\\s+question\\.sh", ou = O_),
            )),
            "fo3" to Lecon("hist.fo3.titre", null, 1, listOf(
                n("fo3", 0, "forge aiguillage", re = "${FO}aiguillages?\\s*$"),
                n("fo3", 1, "ls fantome; echo \$?", re = "^echo\\s+[\"']?\\$\\?", ou = O_),
                n("fo3", 2, "forge code ?", fs = carnetOk("code")),
                n("fo3", 3, "if [ -f cabane/porte.txt ]; then echo \"La porte est là !\"; fi", re = "^if\\s+\\[\\s+-[fed]\\b", ou = O_),
                n("fo3", 4, "for i in 1 2 3; do echo \"Tour \$i\"; done", re = "^for\\s+\\w+\\s+in\\b"),
                n("fo3", 5, "for i in \$(seq 1 10); do mkdir -p village/cabane_\$i; done", fs = { j -> villageOk(j) }, ou = O_),
                n("fo3", 6, "ls village | wc -l", re = "^ls\\b.*village.*\\|\\s*wc\\b", ou = O_),
                n("fo3", 7, "n=3; while [ \$n -gt 0 ]; do echo \$n; n=\$((n - 1)); done", re = "^while\\b"),
                n("fo3", 8, "forge tours ?", fs = carnetOk("tours")),
            )),
            // pas de Python : le serpent est raconté, puis le jeu de l'appli (doom)
            "fo4" to Lecon("hist.fo4.titre", null, 1, listOf(
                n("fo4", 0, "forge serpent", re = "${FO}serpents?\\s*$"),
                n("fo4", 4, "cat serpent.py", re = "$LIRE.*serpent\\.py", ou = O_),
                n("fo4", 6, "forge erreur ?", fs = carnetOk("erreur")),
                n("fo4", 8, "doom", re = "^doom\\b"),
            )),
            "fo5" to Lecon("hist.fo5.titre", null, 1, listOf(
                n("fo5", 0, "forge jeu", re = "${FO}jeu\\s*$", ou = O_),
                n("fo5", 1, "cat mon_jeu/devinette.sh", re = "$LIRE.*devinette\\.sh", ou = O_),
                n("fo5", 3, "seq 1 10 | sh mon_jeu/devinette.sh", re = "^seq\\b.*\\|\\s*(sh|bash)\\s+\\S*devinette\\.sh", ou = O_),
                n("fo5", 4, "echo 'for s in 1 2 3; do mkdir -p mon_jeu/donjon/salle_\$s; done' > donjon.sh",
                    fs = { j -> contient(j, "donjon.sh", "(?s)\\bfor\\b.*\\bmkdir\\b.*donjon") }, ou = O_),
                n("fo5", 5, "sh donjon.sh", fs = { j -> donjonOk(j) }, ou = O_),
                n("fo5", 6, "echo \"Le trésor est ici !\" > mon_jeu/donjon/salle_3/tresor.txt",
                    fs = { j -> !lire(j, "mon_jeu/donjon/salle_3/tresor.txt").isNullOrBlank() }, ou = O_),
                n("fo5", 7, "forge carte \"La grotte de Pixel\"", fs = { j -> File(dossier(j), "mon_jeu/.lieu").isFile }),
                n("fo5", 8, "find mon_jeu", re = "^(tree|find|ls)\\b.*mon_jeu", ou = O_),
            )),
            // le site est servi par l'appli (forge serveur), sur 127.0.0.1
            "fo6" to Lecon("hist.fo6.titre", null, 1, listOf(
                n("fo6", 0, "forge site", re = "${FO}site\\s*$", ou = O_),
                n("fo6", 1, "echo '<h1>Bienvenue chez Pixel</h1>' > site/index.html", fs = { j -> htmlOk(j) }, ou = O_),
                n("fo6", 2, "echo '<p>Ici vit ma créature. Elle adore les cabanes.</p>' >> site/index.html",
                    fs = { j -> contient(j, "site/index.html", "(?i)<p[\\s>]") }, ou = O_),
                n("fo6", 3, "echo 'h1 { color: orange; }' > site/style.css", fs = { j -> contient(j, "site/style.css", "\\{[^}]*:[^}]*\\}") }, ou = O_),
                n("fo6", 4, "echo '<link rel=\"stylesheet\" href=\"style.css\">' >> site/index.html",
                    fs = { j -> contient(j, "site/index.html", "(?i)<link\\b[^>]*style\\.css") }, ou = O_),
                n("fo6", 5, "cat site/index.html", re = "$LIRE.*site/index\\.html", ou = O_),
                n("fo6", 10, "forge serveur", fs = { j -> serveurOk(j) }),
                n("fo6", 7, "curl localhost:8642", re = "^curl\\b.*(localhost|127\\.0\\.0\\.1):\\d{4,5}"),
                n("fo6", 11, "forge serveur stop", fs = { j -> arreteOk(j) }),
                n("fo6", 9, "forge publier", re = "${FO}publi"),
            )),
            // magick, sox, ffmpeg, exiftool : racontés ; la photo d'exemple se lit et se nettoie avec les commandes du jeu
            "fo7" to Lecon("hist.fo7.titre", null, 1, listOf(
                n("fo7", 0, "forge multimedia", re = "${FO}multim[eé]dias?\\s*$", ou = O_),
                n("fo7", 1, "ls multimedia", re = "$LS.*multimedia", ou = O_),
                n("fo7", 5, "forge exif multimedia/photo_exemple.jpg", re = "^(exiftool\\b|(tg\\s+)?forge\\s+exif\\b).*photo_exemple", ou = O_),
                n("fo7", 6, "forge appareil ?", fs = carnetOk("appareil")),
                n("fo7", 7, "forge nettoie multimedia/photo_exemple.jpg", fs = { j -> photoPropre(j) }, ou = O_),
                n("fo7", 8, "forge bilan", fs = carnetOk("bilan")),
            )),
        )
    }

    // ---------------------------------------------------------------- l'arbre du Carrefour
    private fun monde(): JSONObject? {
        val ms = Programme.donnees().optJSONArray("mondes") ?: return null
        return (0 until ms.length()).map { ms.getJSONObject(it) }.firstOrNull { it.optString("id") == "forge" }
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
        if ((0 until deja.length()).any { deja.getString(it) == "forge" } || Histoire.fini(jeu, "forge") || !ouvert(jeu)) return false
        deja.put("forge")
        jeu.log(t("fo.ouvert.log"))
        jeu.dire(Histoire.dire(jeu, "fo.ouvert.dit"), 18)
        return true
    }

    // ---------------------------------------------------------------- les indices
    private val REPONSES = mapOf("forge code ?" to "code", "forge tours ?" to "tours", "forge erreur ?" to "erreur", "forge appareil ?" to "appareil")
    private val TROU = Regex("(^|\\s)(\\?|…|<[^>]*>)(\\s|$)")

    fun indice(jeu: Jeu, e: Etape, tapees: List<Pair<String, String?>>): String? {
        val les = Histoire.leconCourante(jeu)?.id
        if (les !in IDS) return null
        val lignes = tapees.map { it.first.trim() }
        val cmd = e.cmd
        REPONSES[cmd]?.let { et ->
            if (lignes.any { r(FO + et).containsMatchIn(it) && TROU.containsMatchIn(it.substringAfter("forge")) }) return t("fo.indice.trou")
            val der = dernier(jeu, et)
            if (der != null && !der.trimEnd().endsWith("(ok)") && lignes.any { r(FO + et).containsMatchIn(it) }) return t("fo.indice.rep.$et")
        }
        if (cmd.startsWith("echo '#!") && lignes.any { Regex("^echo\\s+\"#!").containsMatchIn(it) }) return t("fo.indice.guillemets_simples")
        val recette = lire(jeu, "cabane.sh")
        if (les == "fo1" && jeu.etape in 2..5 && recette != null && !recetteEtat(recette).getValue("shebang")) return t("fo.indice.efface")
        if (cmd == "sh cabane.sh" && lignes.any { Regex("$SH\\S*cabane\\.sh").containsMatchIn(it) }) {
            val manque = recetteEtat(recette).filter { !it.value }.keys.firstOrNull()
            if (manque != null) return t("fo.indice.recette", "ligne" to t("fo.recette.ligne.$manque"))
        }
        if (cmd.startsWith("sh salut.sh") && lignes.any { Regex("${SH}salut\\.sh\\s*$").containsMatchIn(it) }) return t("fo.indice.prenom")
        if (cmd.startsWith("curl") && lignes.any { it.startsWith("curl") } && portSite() !in Phare.actifs()) return t("fo.tel.indice.serveur")
        if (cmd == "forge serveur" && lignes.any { it.startsWith("curl") } && portSite() !in Phare.actifs()) return t("fo.tel.indice.serveur")
        if (cmd.startsWith("forge carte") && lignes.any { r("${FO}carte\\s*$").containsMatchIn(it) }) return t("fo.carte.aide")
        return null
    }

    // ---------------------------------------------------------------- les commandes du jeu
    private fun bloc(cle: String, vararg p: Pair<String, Any?>) = t(cle, *p).split("\n").map { "  $it" }
    val DESSIN = listOf("   ╔═╗      🔨", "▄▄▄╣ ╠▄▄▄  ✦ ✦", "█▓▓▓▓▓▓▓█  📜", "▀▀▀█▀▀▀█▀▀▀", "   █▄▄▄█   🔥🔥")

    private fun chemin(jeu: Jeu, arg: String?, ici: File): File? {
        val a = (arg ?: "").trim().trim('\'', '"')
        if (a.isEmpty()) return null
        val v = Racine.versVirtuel(jeu.home, a)
        return if (a.startsWith("/") || a.startsWith("~")) Racine.reel(jeu.home, Racine.resoudre(Racine.virtuel(jeu.home, ici.path), v)) else File(ici, a)
    }
    private fun dansLeTerrain(jeu: Jeu, f: File) = try { f.canonicalPath.startsWith(jeu.terrain.canonicalPath + "/") } catch (e: Exception) { false }

    fun lignesExif(jeu: Jeu, arg: String?, ici: File): List<String> {
        val f = chemin(jeu, arg, ici) ?: return listOf(t("fo.exif.aide"))
        if (!dansLeTerrain(jeu, f)) return listOf("✋ " + t("fo.exif.hors_terrain"))
        val o = try { f.readBytes() } catch (e: Exception) { return listOf("✖ " + t("fo.exif.introuvable", "fichier" to f.name)) }
        val ex = exifDe(o) ?: return listOf("✖ " + t("fo.exif.pas_jpeg", "fichier" to f.name))
        noter(jeu, "exif", "${f.name} ${ex.size} (ok)")
        val out = mutableListOf("🔍 " + t("fo.exif.titre", "fichier" to f.name), "")
        if (ex.isEmpty()) return out + ("  " + t("fo.exif.aucune"))
        val w = ex.maxOf { t("fo.exif.${it.first}").length }
        out += ex.map { (k, v) -> "  " + t("fo.exif.$k").padEnd(w) + " : " + v }
        return out + listOf("", "  " + t("fo.exif.morale"))
    }

    fun lignesNettoie(jeu: Jeu, arg: String?, ici: File): List<String> {
        val f = chemin(jeu, arg, ici) ?: return listOf(t("fo.nettoie.aide"))
        if (!dansLeTerrain(jeu, f)) return listOf("✋ " + t("fo.exif.hors_terrain"))
        val o = try { f.readBytes() } catch (e: Exception) { return listOf("✖ " + t("fo.exif.introuvable", "fichier" to f.name)) }
        if (segmentsJpeg(o) == null) return listOf("✖ " + t("fo.exif.pas_jpeg", "fichier" to f.name))
        if (!aExif(o)) return listOf("  " + t("fo.nettoie.deja", "fichier" to f.name))
        try { f.writeBytes(sansExif(o)) } catch (e: Exception) { return listOf("✖ " + t("fo.exif.introuvable", "fichier" to f.name)) }
        noter(jeu, "nettoie", "${f.name} (ok)")
        return listOf("✔ " + t("fo.nettoie.ok", "fichier" to f.name))
    }

    fun manquesBilan(jeu: Jeu): List<String> = listOfNotNull(
        if (!cabaneOk(jeu)) "fo.bilan.m.cabane" else null, if (!villageOk(jeu)) "fo.bilan.m.village" else null,
        if (!dansCarnet(jeu, "erreur")) "fo.bilan.m.serpent" else null,
        if (!File(dossier(jeu), "mon_jeu/.lieu").isFile) "fo.bilan.m.jeu" else null, if (!htmlOk(jeu)) "fo.bilan.m.site" else null,
        if (!photoPropre(jeu)) "fo.bilan.m.photo" else null)

    /** forge [plan|recette|boites|aiguillage|code N|tours N|serpent|erreur MOT|jeu|carte NOM|site|serveur [stop]|publier|
     *  multimedia|exif FICHIER|appareil MOT|nettoie FICHIER|bilan] */
    fun commande(jeu: Jeu, reste: String, ici: File): String {
        val m = reste.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        val sous = asciiId(m.getOrNull(0) ?: "aide")
        val a = m.drop(1).filter { it != "?" && it != "…" }
        val arg = a.joinToString(" ").ifEmpty { null }
        etat(jeu)
        fun atelier(et: String, titre: String, texte: String, icone: String, vararg p: Pair<String, Any?>): List<String> {
            noter(jeu, et, "lu (ok)")
            return listOf("$icone " + t(titre), "") + bloc(texte, *p)
        }
        val l: List<String> = when (sous) {
            "plan", "enclume", "regles" -> DESSIN + t("fo.meuble.enclume").split("\n")
            "recette", "recettes" -> atelier("recette", "fo.recette.titre", "fo.recette.texte", "📜")
            "boites", "boite" -> atelier("boites", "fo.boites.titre", "fo.boites.texte", "📦")
            "aiguillage", "aiguillages" -> atelier("aiguillage", "fo.aiguillage.titre", "fo.aiguillage.texte", "🔀")
            "code" -> when {
                arg == null -> listOf(t("fo.code.aide"))
                Regex("\\d{1,3}").matches(arg.trim()) && arg.trim().toInt() != 0 -> { noter(jeu, "code", "${arg.trim()} (ok)"); listOf("✔ " + t("fo.code.ok", "n" to arg.trim())) }
                else -> { noter(jeu, "code", "${arg.trim().take(12)} (faux)"); listOf("✖ " + t("fo.indice.rep.code")) }
            }
            "tours" -> { val (x, z) = toursQuestion(Histoire.graine(jeu))
                when {
                    arg == null -> listOf(t("fo.tours.aide", "a" to x, "z" to z))
                    arg.trim() == "${toursReponse(x, z)}" -> { noter(jeu, "tours", "${arg.trim()} (ok)"); listOf("✔ " + t("fo.tours.ok", "a" to x, "z" to z, "n" to toursReponse(x, z))) }
                    else -> { noter(jeu, "tours", "${arg.trim().take(12)} (faux)"); listOf("✖ " + t("fo.indice.rep.tours"), "  " + t("fo.tours.aide", "a" to x, "z" to z)) }
                }
            }
            "serpent", "serpents", "python" -> {
                if (!File(dossier(jeu), "serpent.py").exists()) ecrire(jeu, "serpent.py", serpentPy())
                noter(jeu, "serpent", "raconte (ok)")
                listOf("🐍 " + t("fo.serpent.titre"), "") + bloc("fo.serpent.texte") + listOf("", "  " + t("fo.tel.serpent"), "", "  $ python3 serpent.py") +
                    liste(donnees(), "traceback").map { "  $it" }
            }
            "erreur" -> when {
                arg == null -> listOf(t("fo.erreur.aide"))
                asciiId(arg.trim()).replace(":", "") == "indexerror" -> { noter(jeu, "erreur", "IndexError (ok)"); listOf("✔ " + t("fo.erreur.ok")) }
                else -> { noter(jeu, "erreur", "${arg.trim().take(16)} (faux)"); listOf("✖ " + t("fo.indice.rep.erreur")) }
            }
            "jeu" -> { ecrire(jeu, "mon_jeu/devinette.sh", devinetteSh()); noter(jeu, "jeu", "devinette (ok)"); listOf("🎮 " + t("fo.jeu.titre"), "") + bloc("fo.jeu.texte") }
            "carte" -> { val nom = nomDuJeu(reste.trim().substringAfter(' ', "").trim().trim('"', '\''))
                when {
                    nom.isEmpty() -> listOf(t("fo.carte.aide"))
                    !File(dossier(jeu), "mon_jeu").isDirectory -> listOf("✋ " + t("fo.carte.pas_de_jeu"))
                    else -> { ecrire(jeu, "mon_jeu/.lieu", nom + "\n"); etat(jeu).put("jeu", nom); noter(jeu, "carte", "$nom (ok)")
                        listOf("🗺 " + t("fo.carte.ok", "nom" to nom), "") + bloc("fo.carte.texte", "nom" to nom).map { it.replace("tg carte", "carte") } }
                }
            }
            "site" -> { File(dossier(jeu), "site").mkdirs(); noter(jeu, "site", "${portSite()} (ok)")
                listOf("🌐 " + t("fo.site.titre"), "") + bloc("fo.site.texte", "port" to portSite()) + listOf("", "  " + t("fo.tel.site", "port" to portSite())) }
            "serveur" -> if (a.firstOrNull()?.lowercase() in setOf("stop", "arret", "off")) {
                if (portSite() !in Phare.actifs()) listOf(t("fo.tel.serveur.aucun"))
                else { Phare.eteindre(portSite()); listOf(t("fo.tel.serveur.eteint")) }
            } else when {
                !htmlOk(jeu) -> listOf("✋ " + t("fo.indice.pas_de_page"))
                Phare.allumer(portSite(), Phare.Genre.SITE, jeu) -> { noter(jeu, "serveur", "${portSite()} (ok)"); listOf(t("fo.tel.serveur.allume", "port" to portSite())) }
                else -> listOf(t("fo.tel.serveur.rate", "port" to portSite()))
            }
            "publier", "publie", "publication" -> atelier("publier", "fo.publier.titre", "fo.publier.texte", "🌍")
            "multimedia", "multimedias" -> {
                if (!File(dossier(jeu), "multimedia/photo_exemple.jpg").exists() || !dansCarnet(jeu, "multimedia")) ecrire(jeu, "multimedia/photo_exemple.jpg", photoOctets())
                noter(jeu, "multimedia", "photo (ok)")
                listOf("🎞 " + t("fo.multimedia.titre"), "") + bloc("fo.multimedia.texte") + listOf("", "  " + t("fo.tel.multimedia"))
            }
            "exif" -> lignesExif(jeu, arg, ici)
            "appareil" -> { val bon = o("photo").optString("marque")
                when {
                    arg == null -> listOf(t("fo.appareil.aide"))
                    asciiId(arg.trim()) == asciiId(bon) -> { noter(jeu, "appareil", "$bon (ok)"); listOf("✔ " + t("fo.appareil.ok", "marque" to bon)) }
                    else -> { noter(jeu, "appareil", "${arg.trim().take(16)} (faux)"); listOf("✖ " + t("fo.indice.rep.appareil")) }
                }
            }
            "nettoie" -> lignesNettoie(jeu, arg, ici)
            "bilan" -> { val mq = manquesBilan(jeu)
                if (mq.isNotEmpty()) { noter(jeu, "bilan", "pas encore (faux)"); listOf("✋ " + t("fo.bilan.pas_encore")) + mq.map { "   · " + t(it) } }
                else {
                    val nom = etat(jeu).optString("jeu").ifEmpty { lire(jeu, "mon_jeu/.lieu")?.trim() ?: "?" }
                    val certif = t("fo.bilan.texte", "nom" to jeu.nom.ifEmpty { "?" }, "jeu" to nom, "titre" to (titreDuSite(jeu) ?: "?"))
                    ecrire(jeu, "certificat_de_la_forge.txt", certif + "\n"); noter(jeu, "bilan", "certificat (ok)")
                    listOf("🏅 " + t("fo.bilan.titre"), "") + certif.split("\n").map { "  $it" }
                }
            }
            else -> DESSIN + listOf("🔨 " + t("fo.aide.titre")) + t("fo.aide.liste").split("\n").map { "  $it" } + listOf("  forge serveur [stop]")
        }
        return l.joinToString("\n")
    }
}
