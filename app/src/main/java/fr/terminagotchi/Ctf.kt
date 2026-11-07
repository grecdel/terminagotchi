package fr.terminagotchi

import android.util.Base64
import org.json.JSONArray
import java.io.File
import java.security.MessageDigest

/**
 * Capture the flag : chaque épreuve cache un « drapeau » TG{…} qu'on trouve avec les bonnes commandes.
 * Les drapeaux sont tirés au hasard et seule leur empreinte (SHA-256) est gardée :
 * impossible de tricher en lisant la sauvegarde.
 */
object Ctf {
    private class Epreuve(val id: String, private val titreCle: String, private val missionCle: String, private val indicesCle: String,
                          private val schemaCle: String) {
        val titre: String get() = t(titreCle)
        val mission: String get() = t(missionCle)
        val indices: List<String> get() = Langue.liste(indicesCle)
        val schema: String get() = t(schemaCle)
    }

    private val MOTS = listOf("pixel", "kernel", "octet", "glitch", "daemon", "root", "shell", "byte", "cache",
        "socket", "bash", "linux", "stack", "loop", "token", "crypto", "flag", "hack", "zero", "ninja")

    private val EPREUVES = listOf(
        Epreuve("01_cache", "ctf.cache.titre", "ctf.cache.mission",
            "ctf.cache.indices",
            "ctf.cache.schema"),
        Epreuve("02_meule", "ctf.meule.titre", "ctf.meule.mission",
            "ctf.meule.indices",
            "ctf.meule.schema"),
        Epreuve("03_coffre", "ctf.coffre.titre", "ctf.coffre.mission",
            "ctf.coffre.indices",
            "ctf.coffre.schema"),
        Epreuve("04_labyrinthe", "ctf.labyrinthe.titre", "ctf.labyrinthe.mission",
            "ctf.labyrinthe.indices",
            "ctf.labyrinthe.schema"),
        Epreuve("05_code", "ctf.code.titre", "ctf.code.mission",
            "ctf.code.indices",
            "ctf.code.schema"),
        Epreuve("06_miroir", "ctf.miroir.titre", "ctf.miroir.mission",
            "ctf.miroir.indices",
            "ctf.miroir.schema"),
        Epreuve("07_aiguille", "ctf.aiguille.titre", "ctf.aiguille.mission",
            "ctf.aiguille.indices",
            "ctf.aiguille.schema"),
    )

    fun dossier(jeu: Jeu) = File(jeu.terrain, "ctf")
    private fun etat(jeu: Jeu) = jeu.module("ctf")

    private fun empreinte(s: String): String =
        MessageDigest.getInstance("SHA-256").digest(s.trim().toByteArray()).joinToString("") { "%02x".format(it) }

    private fun nouveauDrapeau() = "TG{${MOTS.random()}_${MOTS.random()}_${(100..999).random()}}"

    private fun resolus(jeu: Jeu): JSONArray =
        etat(jeu).optJSONArray("resolus") ?: JSONArray().also { etat(jeu).put("resolus", it) }

    private fun estResolu(jeu: Jeu, id: String): Boolean {
        val r = resolus(jeu)
        return (0 until r.length()).any { r.getString(it) == id }
    }

    private fun preparer(jeu: Jeu) {
        val racine = dossier(jeu)
        racine.walkTopDown().forEach { it.setReadable(true, true); it.setExecutable(true, true) }
        racine.deleteRecursively()
        racine.mkdirs()
        val emp = etat(jeu).optJSONObject("empreintes") ?: org.json.JSONObject().also { etat(jeu).put("empreintes", it) }
        for (ep in EPREUVES) {
            val d = File(racine, ep.id)
            d.mkdirs()
            File(d, "LISEZMOI.txt").writeText("🚩 ${ep.titre}\n${ep.mission}\n" +
                t("ctf.lisezmoi", "n" to ep.id.take(2).trimStart('0')) + "\n")
            val f = nouveauDrapeau()
            emp.put(ep.id, empreinte(f))
            when (ep.id) {
                "01_cache" -> {
                    File(d, "notes.txt").writeText(t("ctf.cache.notes") + "\n")
                    File(d, ".drapeau").writeText("$f\n")
                }
                "02_meule" -> {
                    val cible = (500..2900).random()
                    val sb = StringBuilder()
                    val evts = Langue.liste("ctf.meule.evenements")
                    val secret = t("ctf.meule.secret", "f" to f)
                    for (i in 1..3000) {
                        sb.append("[%04d] ".format(i)).append(if (i == cible) secret else evts.random()).append('\n')
                    }
                    File(d, "journal.log").writeText(sb.toString())
                }
                "03_coffre" -> {
                    val c = File(d, "coffre.txt")
                    c.writeText(t("ctf.coffre.contenu", "f" to f) + "\n")
                    c.setReadable(false, false)
                    c.setWritable(false, false)
                }
                "04_labyrinthe" -> {
                    var p = d
                    val noms = listOf("couloir", "porte", "tunnel", "escalier", "salle", "passage", "impasse")
                    repeat(6) {
                        File(p, noms.random() + "_" + (1..9).random()).mkdirs()   // fausse piste
                        p = File(p, noms.random() + "_" + (10..99).random())
                        p.mkdirs()
                    }
                    File(p, "drapeau.txt").writeText("$f\n")
                }
                "05_code" -> File(d, "message.b64").writeText(
                    Base64.encodeToString(t("ctf.code.contenu", "f" to f).toByteArray(), Base64.NO_WRAP) + "\n")
                "06_miroir" -> File(d, "envers.txt").writeText(t("ctf.miroir.contenu", "f" to f).reversed() + "\n")
                "07_aiguille" -> {
                    val gagnant = (1..40).random()
                    for (i in 1..40) {
                        val nom = "fichier_%02d.txt".format(i)
                        val contenu = if (i == gagnant) {
                            f.padEnd(41, '.') + "\n"   // 42 octets pile
                        } else {
                            val taille = listOf((10..40).random(), (43..120).random()).random()
                            "x".repeat(taille - 1) + "\n"
                        }
                        File(d, nom).writeText(contenu)
                    }
                }
            }
        }
    }

    fun ouvrir(jeu: Jeu, arg: String): Pair<String, File?> {
        if (!File(jeu.terrain, "nid").isDirectory) return t("ctf.ferme", "ctf" to Mots.terme("ctf", Mots.palier(jeu), true),
            "lecon" to t("lec.t1.titre")) to null
        val neuf = arg == "nouveau" || !dossier(jeu).isDirectory
        if (neuf) {
            etat(jeu).put("resolus", JSONArray())
            preparer(jeu)
            jeu.log(t("ctf.prete", "ctf" to Mots.terme("ctf", 0, true)))
        }
        val suite = if (neuf) "\n\n" + t("ctf.emmene") else ""
        val aller: File? = if (neuf) dossier(jeu) else null
        return Pair(texte(jeu) + suite, aller)
    }

    fun texte(jeu: Jeu): String {
        val sb = StringBuilder("🚩 " + Mots.terme("ctf", Mots.palier(jeu), true) + " — ~/terrain_terminagotchi/ctf\n")
        for ((i, ep) in EPREUVES.withIndex()) {
            sb.append(if (estResolu(jeu, ep.id)) "  ✅ " else "  ⬜ ").append("${i + 1}. ${ep.titre} (${ep.id})\n")
        }
        sb.append(t("ctf.tresors", "n" to resolus(jeu).length(), "total" to EPREUVES.size) + "\n")
        sb.append(t("ctf.pied"))
        return sb.toString()
    }

    /** `indice 2` (l'ancienne forme, écrite dans les LISEZMOI) : les 3 niveaux d'AideDouce pour l'épreuve 2. */
    fun indice(jeu: Jeu, n: String): String {
        val i = n.toIntOrNull() ?: return t("ctf.indice.exemple")
        if (EPREUVES.getOrNull(i - 1) == null) return t("ctf.indice.hors", "n" to EPREUVES.size)
        return AideDouce.texteDemandeIndice(jeu, null, i)
    }

    /**
     * Idée 25 (les 3 niveaux d'indice, comme partout ailleurs) : l'épreuve cherchée en ce moment. Avec un numéro
     * (`indice 2`) : cette épreuve ; sinon celle du lieu où l'on est (~/terrain_terminagotchi/ctf/02_meule/…), ou la
     * première pas encore trouvée quand on est à la racine de la chasse. (clé, "", « ctf:<épreuve> ») ou null.
     */
    fun cibleIndice(jeu: Jeu, ici: File?, numero: Int? = null): Triple<String, String, String>? {
        if (etat(jeu).optJSONObject("empreintes") == null || !dossier(jeu).isDirectory) return null
        val ep = if (numero != null) EPREUVES.getOrNull(numero - 1) ?: return null else {
            val racine = try { dossier(jeu).canonicalFile } catch (e: Exception) { return null }
            val la = try { ici?.canonicalFile } catch (e: Exception) { null } ?: return null
            val rel = la.relativeToOrNull(racine)?.path ?: return null
            if (rel.startsWith("..")) return null
            val premier = rel.split('/', '\\').firstOrNull { it.isNotEmpty() }
            if (premier == null) EPREUVES.firstOrNull { !estResolu(jeu, it.id) } else EPREUVES.firstOrNull { it.id == premier }
        } ?: return null
        if (estResolu(jeu, ep.id)) return null
        return Triple("ctf:${ep.id}", "", "ctf:${ep.id}")
    }

    /** Le texte du niveau n : les 3 indices écrits pour l'épreuve (le 3e donne les commandes). */
    fun texteIndice(id: String, n: Int): String {
        val ep = EPREUVES.firstOrNull { it.id == id } ?: return ""
        val l = ep.indices
        return if (l.isEmpty()) "" else ep.titre + " : " + l[(n - 1).coerceIn(0, l.size - 1)]
    }

    fun valider(jeu: Jeu, proposition: String): String {
        if (proposition.isBlank()) return t("ctf.drapeau.exemple")
        val emp = etat(jeu).optJSONObject("empreintes") ?: return t("ctf.drapeau.dabord")
        val h = empreinte(proposition)
        val ep = EPREUVES.firstOrNull { emp.optString(it.id) == h }
            ?: return "❌ " + t("ctf.drapeau.faux")
        if (estResolu(jeu, ep.id)) return t("ctf.drapeau.deja", "titre" to ep.titre)
        resolus(jeu).put(ep.id)
        val gain = 40                                       // idée 25 : les indices ne retirent rien
        jeu.ajouterXp(gain)
        Envies.plaisir(jeu, "jeu", "ctf")                    // la chasse au trésor
        jeu.stats["Intelligence"] = (jeu.stats["Intelligence"] ?: 0) + 3
        jeu.log(t("ctf.capture.log", "titre" to ep.titre))
        val fin = if (resolus(jeu).length() == EPREUVES.size) "\n\n" + t("ctf.tous") else ""
        return t("ctf.trouve", "titre" to ep.titre, "xp" to gain) + "\n\n${ep.schema}$fin"
    }
}
