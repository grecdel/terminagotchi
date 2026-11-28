package fr.terminagotchi

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.util.Base64

/**
 * La sauvegarde exportable (comme pc/tg/sauvegarde.py, même format de fichier) : `sauvegarde exporter` ouvre le
 * sélecteur de fichiers d'Android (« Enregistrer sous » : Téléchargements, carte SD…), `sauvegarde importer` le
 * sélecteur « Ouvrir ». L'appli n'a besoin d'aucune permission : c'est la personne qui choisit le fichier.
 *
 * Le fichier : {"terminagotchi": "sauvegarde", "version": 1, "plateforme": "android", "date", "nom", "niveau",
 * "controle": sha256(contenu), "contenu": "<JSON : {partie, terrain}>"}. La partie est la sauvegarde active sans son
 * sceau (il est propre au téléphone) et sans le compte (sa clé secrète ne quitte jamais l'appareil) ; le terrain :
 * ses fichiers et dossiers avec leurs droits, sans liens, 2 Mo par fichier et 30 Mo en tout au plus.
 * Importer ne remplace jamais rien : la créature arrive comme une partie de plus (Parties.importer).
 * Une sauvegarde faite sur PC ne s'importe pas ici (les deux jeux ne rangent pas la partie pareil).
 */
object Sauvegarde {
    const val FORMAT = "sauvegarde"
    const val VERSION = 1
    const val EXTENSION = ".tgsauve"
    const val PLATEFORME = "android"
    const val MAX_FICHIER = 2 shl 20
    const val MAX_TOTAL = 30 shl 20
    const val MAX_ENTREES = 5000

    class Refus(val cle: String) : Exception(cle)

    private fun sha256(s: String): String =
        MessageDigest.getInstance("SHA-256").digest(s.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }

    private fun mode(f: File): String = try {
        val p = java.nio.file.Files.getPosixFilePermissions(f.toPath(), java.nio.file.LinkOption.NOFOLLOW_LINKS)
        var m = 0
        val ordre = listOf("OWNER_READ", "OWNER_WRITE", "OWNER_EXECUTE", "GROUP_READ", "GROUP_WRITE", "GROUP_EXECUTE",
            "OTHERS_READ", "OTHERS_WRITE", "OTHERS_EXECUTE")
        for ((i, n) in ordre.withIndex()) if (p.any { it.name == n }) m = m or (1 shl (8 - i))
        Integer.toOctalString(m)
    } catch (e: Exception) {
        if (f.isDirectory) "755" else if (f.canWrite()) "644" else "444"
    }

    private fun poserMode(f: File, mode: Int) {
        try {
            val noms = listOf("OWNER_READ", "OWNER_WRITE", "OWNER_EXECUTE", "GROUP_READ", "GROUP_WRITE", "GROUP_EXECUTE",
                "OTHERS_READ", "OTHERS_WRITE", "OTHERS_EXECUTE")
            val p = noms.withIndex().filter { (i, _) -> mode and (1 shl (8 - i)) != 0 }
                .map { java.nio.file.attribute.PosixFilePermission.valueOf(it.value) }.toSet()
            java.nio.file.Files.setPosixFilePermissions(f.toPath(), p)
        } catch (e: Exception) {
            f.setReadable(mode and 256 != 0, true)
            f.setWritable(mode and 128 != 0, true)
            f.setExecutable(mode and 64 != 0, true)
        }
    }

    /** Les entrées du terrain et le nombre de fichiers laissés de côté. */
    fun terrain(racine: File): Pair<JSONArray, Int> {
        val out = JSONArray()
        var total = 0L
        var laisses = 0
        if (!racine.isDirectory || java.nio.file.Files.isSymbolicLink(racine.toPath())) return out to 0
        fun vis(d: File, rel: String) {
            val l = (d.listFiles() ?: return).sortedBy { it.name }
            for (f in l.filter { it.isDirectory || java.nio.file.Files.isSymbolicLink(it.toPath()) }) {
                if (java.nio.file.Files.isSymbolicLink(f.toPath())) { laisses++; continue }
                val r = if (rel.isEmpty()) f.name else "$rel/${f.name}"
                out.put(JSONObject().put("chemin", r).put("dossier", true).put("mode", mode(f)))
            }
            for (f in l.filter { !it.isDirectory && !java.nio.file.Files.isSymbolicLink(it.toPath()) }) {
                val n = f.length()
                if (!f.isFile || n > MAX_FICHIER || total + n > MAX_TOTAL || out.length() >= MAX_ENTREES) { laisses++; continue }
                val octets = try { f.readBytes() } catch (e: Exception) { laisses++; continue }
                total += octets.size
                val r = if (rel.isEmpty()) f.name else "$rel/${f.name}"
                out.put(JSONObject().put("chemin", r).put("mode", mode(f)).put("b64", Base64.getEncoder().encodeToString(octets)))
            }
            for (f in l.filter { it.isDirectory && !java.nio.file.Files.isSymbolicLink(it.toPath()) })
                vis(f, if (rel.isEmpty()) f.name else "$rel/${f.name}")
        }
        vis(racine, "")
        return out to laisses
    }

    /** Le texte du fichier de sauvegarde de la partie active (et le nombre de fichiers du terrain laissés de côté). */
    fun fabriquer(ctx: Context, jeu: Jeu): Pair<String, Int> {
        jeu.sauver()
        val texte = Parties.fichierActif(ctx).readText()
        val partie = JSONObject(texte)
        partie.remove("sceau")
        partie.optJSONObject("extra")?.remove("compte")
        val (t, laisses) = terrain(jeu.terrain)
        val contenu = JSONObject().put("partie", partie).put("terrain", t).toString()
        val entete = JSONObject()
            .put("terminagotchi", FORMAT).put("version", VERSION).put("plateforme", PLATEFORME)
            .put("date", java.text.SimpleDateFormat("yyyy-MM-dd HH:mm", java.util.Locale.ROOT).format(java.util.Date()))
            .put("nom", jeu.nom).put("niveau", jeu.niveau)
            .put("controle", sha256(contenu)).put("contenu", contenu)
        return entete.toString(1) to laisses
    }

    fun nomDeFichier(nom: String): String {
        val n = nom.replace(Regex("[^A-Za-z0-9_-]+"), "-").trim('-').ifEmpty { "creature" }
        val d = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.ROOT).format(java.util.Date())
        return "terminagotchi-$n-$d$EXTENSION"
    }

    /** Le contenu vérifié : (entête, partie, terrain) ; Refus sinon (clé du texte à dire). */
    fun lire(texte: String, plateforme: String = PLATEFORME): Triple<JSONObject, JSONObject, JSONArray> {
        val o = try { JSONObject(texte) } catch (e: Exception) { throw Refus("svg.refus.illisible") }
        if (o.optString("terminagotchi") != FORMAT || o.opt("contenu") !is String) throw Refus("svg.refus.illisible")
        val v = o.opt("version")
        if (v !is Int || v > VERSION) throw Refus("svg.refus.version")
        val contenu = o.getString("contenu")
        if (sha256(contenu) != o.optString("controle")) throw Refus("svg.refus.abime")
        if (o.optString("plateforme") != plateforme) throw Refus("svg.refus.plateforme")
        val c = try { JSONObject(contenu) } catch (e: Exception) { throw Refus("svg.refus.abime") }
        val partie = c.optJSONObject("partie") ?: throw Refus("svg.refus.abime")
        val terrain = c.optJSONArray("terrain") ?: JSONArray()
        if (partie.optString("nom").isEmpty() || !partie.has("xp")) throw Refus("svg.refus.abime")
        return Triple(o, partie, terrain)
    }

    /** Un chemin relatif du terrain, sans « .. » ni racine : ses morceaux, sinon null (jamais écrit). */
    fun cheminSur(chemin: String?): List<String>? {
        if (chemin.isNullOrEmpty() || '\u0000' in chemin || '\\' in chemin || chemin.startsWith("/")) return null
        val m = chemin.split("/")
        if (m.any { it.isEmpty() || it == "." || it == ".." } || ':' in m[0]) return null
        return m
    }

    /** Écrit le terrain dans [racine] (un dossier neuf) : les fichiers, puis les droits (dossiers en dernier). */
    fun poserTerrain(racine: File, terrain: JSONArray) {
        if (!racine.mkdirs()) throw java.io.IOException("$racine")
        val modes = mutableListOf<Triple<File, Int, Boolean>>()
        for (i in 0 until minOf(terrain.length(), MAX_ENTREES)) {
            val e = terrain.optJSONObject(i) ?: continue
            val m = cheminSur(e.optString("chemin")) ?: continue
            val f = m.fold(racine) { d, n -> File(d, n) }
            val mode = e.optString("mode", "644").toIntOrNull(8)?.and(511) ?: 420   // 0777, 0644
            val dossier = e.optBoolean("dossier")
            if (dossier) f.mkdirs() else {
                val octets = try { Base64.getDecoder().decode(e.optString("b64")) } catch (x: Exception) { continue }
                if (octets.size > MAX_FICHIER) continue
                f.parentFile?.mkdirs()
                if (f.isDirectory || java.nio.file.Files.isSymbolicLink(f.toPath())) continue
                f.writeBytes(octets)
            }
            modes.add(Triple(f, mode, dossier))
        }
        for ((f, mode, _) in modes.sortedWith(compareBy({ it.third }, { -it.first.path.count { c -> c == '/' } }))) poserMode(f, mode)
    }

    /** Importe le texte d'un fichier de sauvegarde : la phrase à dire. La partie active est rangée, jamais remplacée. */
    fun importer(ctx: Context, jeu: Jeu, texte: String): String {
        val (entete, partie, terrain) = try { lire(texte) } catch (r: Refus) { return t(r.cle) }
        if (Parties.pleine(ctx)) return t("svg.plein", "max" to Parties.MAX)
        partie.remove("sceau")
        partie.optJSONObject("extra")?.remove("compte")
        jeu.sauver()
        Parties.importer(ctx, partie) { poserTerrain(it, terrain) } ?: return t("svg.refus.place")
        jeu.recharger()
        return t("svg.importe.tel", "nom" to jeu.nom, "niveau" to jeu.niveau, "date" to entete.optString("date", "?"))
    }
}
