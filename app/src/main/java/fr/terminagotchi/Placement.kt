package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject

/**
 * Pour ceux qui connaissent déjà un peu le terminal (G-13, portage de pc/tg/placement.py) :
 *  - `placement` : un petit test SANS AIDE (le but seulement) : où es-tu, va à la Racine, reviens au camp de base,
 *    montre les fichiers cachés. Réussi en 10 lignes au plus : le chapitre 1 est validé, la suite se joue sans aide.
 *  - `sansaide on|off` : le mode « défi sans aide » : chaque étape montre son but, pas la commande ; `aide` (ou trois
 *    essais ratés) la montre. Les étapes sont toujours validées sur le résultat (Verif.kt).
 */
object Placement {
    private class Defi(val but: String, val re: Regex? = null, val ici: String? = null)

    private val DEFIS = listOf(
        Defi("plac.but.pwd", re = Regex("^pwd(\\s|$)")),
        Defi("plac.but.racine", ici = "/"),
        Defi("plac.but.camp", ici = Racine.HOME),
        Defi("plac.but.caches", re = Regex(Verif.LS_A)),
    )
    const val ESSAIS_MAX = 10

    private fun p(jeu: Jeu): JSONObject = jeu.module("placement")
    fun actif(jeu: Jeu) = p(jeu).optString("etat") == "en_cours"
    fun etat(jeu: Jeu): String = p(jeu).optString("etat")
    fun sansAide(jeu: Jeu) = jeu.module("sansaide").optBoolean("on")

    fun commencer(jeu: Jeu): String {
        if (Histoire.fini(jeu, "reveil")) return t("plac.deja.tel")
        p(jeu).put("etat", "en_cours").put("i", 0).put("lignes", 0)
        return t("plac.debut", "n" to DEFIS.size, "max" to ESSAIS_MAX) + "\n" + but(jeu)
    }

    fun but(jeu: Jeu): String {
        val i = p(jeu).optInt("i").coerceAtMost(DEFIS.size - 1)
        return t("plac.etape", "n" to i + 1, "total" to DEFIS.size, "but" to t(DEFIS[i].but))
    }

    private fun reussi(jeu: Jeu, d: Defi, m: Verif.Morceau): Boolean {
        if (m.code != null && m.code != 0) return false
        d.re?.let { return it.containsMatchIn(m.texte.trim()) }
        return Racine.virtuel(jeu.home, m.apres.path) == d.ici && m.apres != m.avant
    }

    fun tick(jeu: Jeu, morcs: List<Verif.Morceau>) {
        if (!actif(jeu)) return
        val p = p(jeu)
        for (m in morcs) {
            p.put("lignes", p.optInt("lignes") + 1)
            val d = DEFIS[p.optInt("i")]
            if (reussi(jeu, d, m)) {
                p.put("i", p.optInt("i") + 1)
                if (p.optInt("i") >= DEFIS.size) { reussir(jeu); return }
                jeu.dire(but(jeu), 12)
            }
            if (p.optInt("lignes") >= ESSAIS_MAX) { p.put("etat", "rate"); jeu.dire(t("plac.rate"), 14); return }
        }
    }

    private fun reussir(jeu: Jeu) {
        p(jeu).put("etat", "reussi")
        java.io.File(jeu.terrain, "vestibule").mkdirs()
        Histoire.validerChapitre(jeu, "reveil")
        jeu.module("sansaide").put("on", true)
        jeu.log(t("plac.ok.log"))
        jeu.dire(t("plac.ok"), 16)
    }

    fun commande(jeu: Jeu, args: List<String>): String {
        val a = args.firstOrNull()?.lowercase()
        if (a == "on" || a == "off") {
            jeu.module("sansaide").put("on", a == "on")
            return t(if (a == "on") "sa.on.tel" else "sa.off")
        }
        return commencer(jeu)
    }

    private fun cle(jeu: Jeu, e: Etape) = "${Histoire.chap(jeu)}:${e.cmd}"

    /** Mode sans aide : la commande est cachée tant qu'elle n'a pas été demandée (`aide`) ou ratée 3 fois. */
    fun cache(jeu: Jeu, e: Etape): Boolean {
        if (!sansAide(jeu)) return false
        val s = jeu.module("sansaide")
        val vu = s.optJSONArray("vu") ?: JSONArray()
        for (i in 0 until vu.length()) if (vu.getString(i) == cle(jeu, e)) return false
        return (s.optJSONObject("essais")?.optInt(cle(jeu, e)) ?: 0) < 3
    }

    fun montrer(jeu: Jeu, e: Etape) {
        val s = jeu.module("sansaide")
        val vu = s.optJSONArray("vu") ?: JSONArray().also { s.put("vu", it) }
        for (i in 0 until vu.length()) if (vu.getString(i) == cle(jeu, e)) return
        vu.put(cle(jeu, e))
        while (vu.length() > 50) vu.remove(0)
    }

    fun rateUneFois(jeu: Jeu, e: Etape) {
        if (!sansAide(jeu)) return
        val s = jeu.module("sansaide")
        val es = s.optJSONObject("essais") ?: JSONObject().also { s.put("essais", it) }
        es.put(cle(jeu, e), es.optInt(cle(jeu, e)) + 1)
    }
}
