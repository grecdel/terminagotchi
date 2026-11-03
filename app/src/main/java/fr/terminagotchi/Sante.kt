package fr.terminagotchi

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * La vérification au démarrage (comme pc/tg/sante.py) : à l'ouverture de l'appli, le jeu regarde ses propres fichiers
 * et répare doucement. Rien n'est jamais effacé ; ce qui est remplacé est gardé à côté (….casse-<date>).
 *
 *  1. La sauvegarde active (files/sauvegarde.json) a disparu ou n'est plus bonne, mais une écriture inachevée
 *     (sauvegarde.tmp) est bonne (sceau compris) et plus récente que la copie de secours : elle est remise en place.
 *     (Sans elle, Jeu.charger prend déjà la copie de secours sauvegarde.json.bak, et le dit.)
 *  2. La liste des parties (parties/index.json) est abîmée ou oublie des parties rangées (partie_<id>.json) : elle
 *     est refaite à partir des fichiers présents ([reparerIndex], mêmes vecteurs que sante.py :
 *     donnees/sante/vecteurs.json).
 *  3. Les fichiers du jeu (textes, mondes, langues) sont dans l'APK, vérifié par Android à l'installation : rien à
 *     regarder ici (sur PC, sante.py les relit après une mise à jour).
 */
object Sante {
    /**
     * La liste des parties réparée. [idx] : l'index lu (null : absent ; "abime" : illisible ; sinon ce qui a été lu) ;
     * [actif] : l'id rangé dans la sauvegarde active nommée (null sinon) ; [rangees] : les partie_<id>.json présents,
     * du plus ancien au plus récent. Renvoie (index, réparé ?).
     */
    fun reparerIndex(idx: Any?, actif: String?, rangees: List<String>): Pair<JSONObject, Boolean> {
        val o = idx as? JSONObject
        val a = o?.opt("active") as? String
        val brut = o?.opt("ordre") as? JSONArray
        val valide = o != null && !a.isNullOrEmpty() && brut != null && (0 until brut.length()).all { brut.opt(it) is String }
        if (!valide) {
            val active = actif ?: "1"
            val ordre = mutableListOf<String>()
            if (actif != null) ordre.add(actif)
            for (i in rangees) if (i !in ordre) ordre.add(i)
            return JSONObject().put("active", active).put("ordre", JSONArray(ordre)) to (idx != null || rangees.isNotEmpty())
        }
        val avant = (0 until brut!!.length()).map { brut.getString(it) }
        var active = a!!
        val ordre = mutableListOf<String>()
        for (i in avant) if (i !in ordre) ordre.add(i)
        if (actif != null && actif != active && actif !in rangees) active = actif
        // (la partie active absente de l'ordre est normale : Parties.liste l'ajoute toujours ; ce n'est pas une panne)
        for (i in rangees) if (i !in ordre && i != active) ordre.add(i)
        return JSONObject().put("active", active).put("ordre", JSONArray(ordre)) to (active != a || ordre != avant)
    }

    private fun garder(f: File) {
        if (!f.exists()) return
        val d = java.text.SimpleDateFormat("yyyyMMdd-HHmmss", java.util.Locale.ROOT).format(java.util.Date())
        Garde.pendant {
            val g = File(f.parentFile, f.name + ".casse-" + d)
            f.renameTo(g)
            Garde.noter(f); Garde.noter(g)
        }
    }

    private fun bonne(f: File): Boolean = try {
        if (!f.isFile) false else {
            val txt = f.readText()
            val o = JSONObject(txt)
            o.optString("nom").isNotEmpty() && Garde.acceptable(txt)
        }
    } catch (e: Exception) { false }

    private fun sauvegarde(ctx: Context): String? {
        val f = Parties.fichierActif(ctx)
        val tmp = File(f.parentFile, f.name.removeSuffix(".json") + ".tmp")
        val bak = File(f.parentFile, f.name + ".bak")
        if (bonne(f) || !bonne(tmp)) return null
        if (bak.isFile && bonne(bak) && bak.lastModified() > tmp.lastModified()) return null
        garder(f)
        val ok = Garde.pendant {
            val r = tmp.renameTo(f)
            Garde.noter(f); Garde.noter(tmp)
            r
        }
        return if (ok) t("sante.tmp") else null
    }

    private fun index(ctx: Context): String? = synchronized(Parties.verrou) {
        val d = Parties.dossier(ctx)
        val f = Parties.fIndex(ctx)
        val fichiers = (d.listFiles() ?: emptyArray())
            .filter { it.isFile && it.name.startsWith("partie_") && it.name.endsWith(".json") }
            .sortedWith(compareBy<File>({ it.lastModified() }, { it.name }))
        if (!f.exists() && fichiers.isEmpty()) return null
        val brut: Any? = if (!f.exists()) null else (try { JSONObject(f.readText()) } catch (e: Exception) { "abime" })
        val sauv = Parties.lireJson(Parties.fichierActif(ctx))
        val actif = if (sauv != null && sauv.optString("nom").isNotEmpty()) sauv.optString("partie").ifEmpty { "1" } else null
        val rangees = fichiers.filter { Parties.lireJson(it) != null }.map { it.name.removePrefix("partie_").removeSuffix(".json") }
        val (nouveau, repare) = reparerIndex(brut, actif, rangees)
        if (!repare) return null
        garder(f)
        Parties.ecrire(f, nouveau)
        val n = (0 until nouveau.getJSONArray("ordre").length()).map { nouveau.getJSONArray("ordre").getString(it) }.toSet() + nouveau.getString("active")
        return t("sante.index", "n" to n.size)
    }

    /** À l'ouverture de l'appli : vérifie et répare doucement. Les phrases à dire (vide si tout va bien). Jamais d'erreur. */
    fun auDemarrage(ctx: Context): List<String> {
        val out = mutableListOf<String>()
        for (etape in listOf<(Context) -> String?>(::sauvegarde, ::index)) {
            try { etape(ctx)?.let { out.add(it) } } catch (e: Exception) { android.util.Log.w("TG", "vérification : $e") }
        }
        return out
    }
}
