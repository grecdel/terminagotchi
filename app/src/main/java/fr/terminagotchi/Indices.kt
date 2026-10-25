package fr.terminagotchi

import java.io.File

/**
 * « Presque ! » : des indices clairs quand une commande est presque la bonne (portage des fonctions
 * faute_de_frappe de pc/tg/dressage.py et indice de pc/tg/lecons.py). Les textes sont traduits
 * (clés « dress.indice.* » et « lec.indice.* », communes avec le PC).
 *
 * La ressemblance entre deux mots est celle de difflib en Python (SequenceMatcher.ratio et
 * get_close_matches), recopiée à l'identique : les mêmes fautes donnent les mêmes indices que sur PC.
 */
object Indices {
    // ---------------------------------------------------------------- difflib (sans « junk » : mots courts)
    private class Bloc(val a: Int, val b: Int, val n: Int)

    /** SequenceMatcher(None, a, b).ratio() */
    fun ratio(a: String, b: String): Double {
        val t = a.length + b.length
        if (t == 0) return 1.0
        val b2j = HashMap<Char, MutableList<Int>>()
        for ((j, c) in b.withIndex()) b2j.getOrPut(c) { mutableListOf() }.add(j)
        fun plusLong(alo: Int, ahi: Int, blo: Int, bhi: Int): Bloc {
            var bi = alo; var bj = blo; var bk = 0
            var j2len = HashMap<Int, Int>()
            for (i in alo until ahi) {
                val nouveau = HashMap<Int, Int>()
                for (j in b2j[a[i]] ?: emptyList<Int>()) {
                    if (j < blo) continue
                    if (j >= bhi) break
                    val k = (j2len[j - 1] ?: 0) + 1
                    nouveau[j] = k
                    if (k > bk) { bi = i - k + 1; bj = j - k + 1; bk = k }
                }
                j2len = nouveau
            }
            return Bloc(bi, bj, bk)
        }
        var m = 0
        val file = ArrayDeque<IntArray>()
        file.add(intArrayOf(0, a.length, 0, b.length))
        while (file.isNotEmpty()) {
            val (alo, ahi, blo, bhi) = file.removeLast()
            val x = plusLong(alo, ahi, blo, bhi)
            if (x.n > 0) {
                m += x.n
                if (alo < x.a && blo < x.b) file.add(intArrayOf(alo, x.a, blo, x.b))
                if (x.a + x.n < ahi && x.b + x.n < bhi) file.add(intArrayOf(x.a + x.n, ahi, x.b + x.n, bhi))
            }
        }
        return 2.0 * m / t
    }

    /** difflib.get_close_matches(mot, possibles, n=1, cutoff) : le plus proche, ou null. */
    fun plusProche(mot: String, possibles: List<String>, cutoff: Double): String? =
        possibles.map { ratio(it, mot) to it }.filter { it.first >= cutoff }
            .maxWithOrNull(compareBy<Pair<Double, String>>({ it.first }, { it.second }))?.second

    /** Les mots d'une commande, chemins réduits à leur dernier morceau (~/x/monstre_a.txt → monstre_a.txt). */
    fun mots(ligne: String): List<String> =
        ligne.replace("'", " ").replace("\"", " ").trim().split(Regex("\\s+")).map { m0 ->
            val m = m0.trimEnd('/', '\\')
            if ('/' in m || '\\' in m) m.split(Regex("[/\\\\]")).last() else m
        }.filter { it.isNotEmpty() }

    private fun chiffre(s: String) = s.isNotEmpty() && s.all { it.isDigit() }

    /** (mot tapé, mot attendu) si une ligne ressemble à la commande modèle avec un mot mal écrit.
     *  chiffres = true : les nombres comptent aussi (chmod 44 au lieu de chmod 444). */
    fun fauteDeFrappe(lignes: List<String>, modele: String, chiffres: Boolean = false): Pair<String, String>? {
        val attendus = mots(modele.split("    ")[0])
        if (attendus.isEmpty()) return null
        for (l in lignes) {
            val ms = mots(l)
            if (ms.isEmpty() || ms[0].lowercase() != attendus[0].lowercase()) continue
            for (m in ms.drop(1)) {
                if (chiffres && chiffre(m) && m !in attendus) {
                    val nombres = attendus.drop(1).filter { chiffre(it) }
                    plusProche(m, nombres, 0.6)?.let { return m to it }
                }
                if (m in attendus || m.startsWith("-") || chiffre(m) || m.length < 3) continue
                val cibles = attendus.drop(1).filter { !it.startsWith("-") && !chiffre(it) && it.length >= 3 }
                val p = plusProche(m, cibles, 0.75)
                if (p != null && p != m) return m to p
            }
        }
        return null
    }

    // ---------------------------------------------------------------- leçons
    /** Le fichier contient ce mot (sans tenir compte des majuscules). */
    fun contient(f: File, mot: String) = try { f.isFile && mot in f.readText().lowercase() } catch (e: Exception) { false }

    /** Une étape de leçon PRESQUE réussie : le texte d'un indice clair, ou null (comme lecons.indice sur PC). */
    fun lecon(jeu: Jeu, e: Etape, lignes: List<String>): String? {
        val cmd = e.cmd
        fauteDeFrappe(lignes, cmd, chiffres = true)?.let { return t("dress.indice.faute", "tape" to it.first, "attendu" to it.second) }
        val premier = cmd.split(" ")[0].lowercase()
        val tapee = lignes.any { l -> l.trim().split(Regex("\\s+")).firstOrNull()?.lowercase() == premier }
        val rel = e.cree ?: return null
        if (rel == "nid/repas.txt" && File(jeu.terrain, rel).isFile) return t("lec.indice.pomme", "cmd" to cmd)
        if (tapee && e.fs?.invoke(jeu) != true) {
            val nom = rel.split("/").last()
            val ici = File(jeu.terrain, rel)
            val ailleurs = File(jeu.home, nom).exists() || File(jeu.home, rel).exists() ||
                (jeu.terrain.isDirectory && jeu.terrain.walkTopDown().any { it.name == nom && it != ici })
            if (ailleurs) return t("lec.indice.endroit", "cmd" to "cd ~/${jeu.terrain.name}")
        }
        return null
    }
}
