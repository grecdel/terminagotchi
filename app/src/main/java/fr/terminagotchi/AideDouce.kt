package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject

/**
 * Accueil et aide (idées validées le 3 novembre) : les coups de pouce des premières minutes et l'aide quand on est
 * perdu. Mêmes règles que pc/tg/aide_douce.py (vecteurs communs donnees/accueil/vecteurs.json, tests/jvm/Accueil.kt) :
 * « Qui est avec toi ? » (1), le premier ls (2), la flèche « tape ici » (4), la touche du symbole qui s'allume (5),
 * « Perdu ? » (6), fermer et revenir (9), `ls ?` (22), les 3 niveaux d'indice (25), la fin grisée (66), le menu (79).
 * Sauvegarde : jeu.module("aide_douce").
 */
object AideDouce {
    const val SEUIL_FLECHE = 3
    const val RETOUR_FLECHE = 60
    const val VIF_ERREURS = 2
    const val VIF_ATTENTE = 120
    const val DUREE_LS = 3.0
    const val DUREE_LS_COURTE = 2.0

    val RANGEE1 = listOf("↑", "⇥", "^C", "-", "/", "~", "|", ".", ">", "⋯")
    val RANGEE2 = listOf("↓", ">>", "*", "\"", "'", "$", "&", "_", "=", "⋯")
    val SYMBOLES1 = listOf("-", "/", "~", "|", ".", ">")
    val SYMBOLES2 = listOf(">>", "*", "\"", "'", "$", "&", "_", "=")
    val ORDRE_SYMBOLES = listOf(">>", "|", "~", ">", "*", "/", "$", "&", "\"", "'", "_")

    fun a(jeu: Jeu): JSONObject {
        val a = jeu.module("aide_douce")
        if (!a.has("reussies")) a.put("reussies", 0)
        if (!a.has("erreurs")) a.put("erreurs", 0)
        if (!a.has("derniere")) a.put("derniere", 0L)
        if (a.optJSONArray("symboles") == null) a.put("symboles", JSONArray())
        if (!a.has("premier_ls")) a.put("premier_ls", false)
        return a
    }

    // ================================================================ règles pures (vecteurs communs)
    fun fleche(introEnCours: Boolean, reussies: Int, depuis: Double): Boolean =
        introEnCours && (reussies < SEUIL_FLECHE || depuis >= RETOUR_FLECHE)

    fun perduVif(erreurs: Int, depuis: Double): Boolean = erreurs >= VIF_ERREURS || depuis >= VIF_ATTENTE

    fun toucheAAllumer(attendu: String?, tape: String?): String? {
        val a = attendu ?: ""
        val t0 = tape ?: ""
        var p = 0
        while (p < a.length && p < t0.length && a[p] == t0[p]) p++
        var i = p
        while (i < a.length) {
            if (a.startsWith(">>", i)) return "⋯"
            val c = a[i].toString()
            if (c in SYMBOLES1) return c
            if (c in SYMBOLES2) return "⋯"
            i++
        }
        return null
    }

    fun symboleNouveau(attendu: String?, vus: Collection<String>): String? {
        val a = attendu ?: ""
        val trouves = mutableListOf<String>()
        var i = 0
        while (i < a.length) {
            val s = if (a.startsWith(">>", i)) ">>" else a[i].toString()
            if (s in ORDRE_SYMBOLES && s !in trouves) trouves.add(s)
            i += s.length
        }
        return trouves.firstOrNull { it !in vus }
    }

    private val Q1 = Regex("^\\s*([A-Za-z][A-Za-z0-9_.+-]*)\\s+\\?\\s*$")
    private val Q2 = Regex("^\\s*\\?\\s+([A-Za-z][A-Za-z0-9_.+-]*)\\s*$")

    /** `ls ?` ou `? ls` → « ls » ; sinon null. */
    fun demandeExplique(ligne: String?): String? {
        val l = ligne ?: return null
        return (Q1.find(l) ?: Q2.find(l))?.groupValues?.get(1)?.lowercase()
    }

    fun partiesIndice(attendu: String?): Map<String, String> {
        val a = (attendu ?: "").trim().replace(Regex("\\s+"), " ")
        val mots = if (a.isEmpty()) emptyList() else a.split(" ")
        val cmd = mots.firstOrNull() ?: ""
        val debut = if (cmd.isEmpty()) mutableListOf() else mutableListOf(cmd)
        for (m in mots.drop(1)) { if (m.startsWith("-") && m.length > 1) debut.add(m) else break }
        return mapOf("cmd" to cmd, "debut" to debut.joinToString(" "), "reponse" to a)
    }

    fun fantome(mot: String, candidats: Collection<String>): String {
        if (mot.isEmpty()) return ""
        val ok = candidats.filter { it.startsWith(mot) && it != mot }.toSortedSet().toList()
        if (ok.isEmpty()) return ""
        var commun = ok[0]
        for (c in ok.drop(1)) commun = commun.commonPrefixWith(c)
        return commun.substring(mot.length)
    }

    fun troncFini(ailes: Collection<String>, tronc: JSONObject?): Boolean {
        val besoin = mutableListOf<String>()
        val cles = tronc?.keys()?.asSequence()?.toList()?.sorted() ?: emptyList()
        for (k in cles) {
            if (!k.startsWith("n")) continue
            val v = tronc!!.optJSONArray(k) ?: continue
            for (i in 0 until v.length()) v.getString(i).let { if (it !in besoin) besoin.add(it) }
        }
        return besoin.isNotEmpty() && besoin.all { it in ailes }
    }

    fun dureeLs(campEnMemeTemps: Boolean) = if (campEnMemeTemps) DUREE_LS_COURTE else DUREE_LS

    fun actionMenu(reponse: String?): String? = when ((reponse ?: "").trim().lowercase()) {
        "", "1" -> "continuer"; "2" -> "nouvelle"; "3" -> "charger"; "4" -> "options"; "5" -> "aide"
        "q", "0" -> "quitter"; else -> null
    }

    // ================================================================ après chaque commande
    /** Compte les réussites (la flèche), les erreurs de suite (« Perdu ? »). Renvoie « premier_ls » une fois. */
    fun apresCommande(jeu: Jeu, ligne: String, ok: Boolean, maintenant: Long = System.currentTimeMillis()): String? {
        val a = a(jeu)
        proposerFermer(jeu)
        a.put("derniere", maintenant / 1000)
        if (ok) { a.put("reussies", minOf(99, a.optInt("reussies") + 1)); a.put("erreurs", 0) }
        else a.put("erreurs", minOf(99, a.optInt("erreurs") + 1))
        val mot = Regles.premierMot(ligne).lowercase()
        if (ok && mot in setOf("ls", "dir") && !a.optBoolean("premier_ls")) {
            a.put("premier_ls", true)
            return "premier_ls"
        }
        return null
    }

    fun depuis(jeu: Jeu, maintenant: Long = System.currentTimeMillis()): Double {
        val d = a(jeu).optLong("derniere")
        return if (d <= 0) 0.0 else maintenant / 1000.0 - d
    }

    /** La flèche « tape ici » (téléphone) : (vraie, la commande à taper) */
    fun flecheMaintenant(jeu: Jeu): String? {
        if (!jeu.existe) return null
        val a = a(jeu)
        if (!fleche(Intro.enCours(jeu), a.optInt("reussies"), depuis(jeu))) return null
        return Intro.prochaine(jeu)?.let { Intro.commandeDe(it) } ?: ""
    }

    // ================================================================ 1. parent à côté
    fun conseilsParents(): String = (listOf("🤝 " + t("ad.parent.titre_conseils")) + (1..4).map { "▸ " + t("ad.parent.c$it.t") + " " + t("ad.parent.c$it") } +
        listOf("▸ " + t("ad.parent.debloquer", "cmd" to "`debloquer tout`"), t("ad.parent.relire.tel"))).joinToString("\n")

    // ================================================================ 9. fermer et revenir
    fun proposerFermer(jeu: Jeu) {
        val a = a(jeu)
        if (a.optString("fermer").isNotEmpty() || !jeu.existe || !Intro.eclos(jeu)) return
        val ailes = Quetes.liste(Histoire.h(jeu), "ailes")
        if (!troncFini(ailes, Programme.donnees().optJSONObject("tronc"))) return
        a.put("fermer", "file")
        val d = Intro.deb(jeu)
        val f = d.optJSONArray("file") ?: JSONArray().also { d.put("file", it) }
        if ((0 until f.length()).none { f.getString(it) == "fermer" }) f.put("fermer")
    }

    fun marquerFermer(jeu: Jeu) { a(jeu).put("fermer", "attend") }

    /** L'appli rouverte après « fermer et revenir » : « Te revoilà ! », une fois. */
    fun retour(jeu: Jeu): String? {
        val a = a(jeu)
        if (a.optString("fermer") != "attend") return null
        a.put("fermer", "fait")
        return t("ad.fermer.retour")
    }

    // ================================================================ 22. ls ?
    fun ficheCourte(nom: String): String {
        val m = Regles.LEXIQUE.firstOrNull { it.cmd == nom }
        val opts = Explique.OPTIONS[nom] ?: emptyMap()
        if (m == null && opts.isEmpty()) return t("explique.inconnue", "cmd" to nom, "ex" to "explique rm")
        val out = mutableListOf("📖 " + t("ad.q.titre", "cmd" to nom))
        if (m != null) out.add("  " + m.image)
        (m?.let { Exemples.lexique(it) } ?: Exemples.LEXIQUE[nom]?.let { Exemples.remplir(it) })?.let {
            out.add("  " + t("ad.q.essaie", "ex" to "`$it`"))
        }
        opts.entries.firstOrNull()?.let { (o, cle) -> out.add("  (`$o` : " + t("opt.$cle") + ")") }
        Explique.grandCommande(nom, m?.technique)?.let { out.add("  🧑 $it") }
        out.add("  🧑 " + t("ad.q.joker", "aide" to "`$nom --help`", "man" to "`man $nom`"))
        out.add("  " + t("ad.q.tout", "cmd" to "`explique $nom`"))
        return out.joinToString("\n")
    }

    // ================================================================ 6. perdu
    /** (où es-tu, ta leçon, quoi taper) : les mêmes renseignements que `aide`. */
    fun infosPerdu(jeu: Jeu, dossier: java.io.File? = null): Triple<String, String, String> {
        val ici = dossier?.path ?: Maison.ici(jeu)
        val r = ici?.let { Maison.rel(jeu, it) }
        val virt = ici?.let { try { Racine.virtuel(jeu.home, it) } catch (e: Exception) { it } } ?: "?"
        val ou = if (r != null) Histoire.nomLieu(r) + "  ($virt)" else virt
        if (Intro.enCours(jeu)) {
            val p = Intro.prochaine(jeu)
            return Triple(ou, Intro.titreListe(jeu), p?.let { "`" + Intro.commandeDe(it) + "`" } ?: "")
        }
        val c = Histoire.leconCourante(jeu)
        if (c == null || jeu.niveau < c.niveau) return Triple(ou, t("aide.lecon.aucune"), "")
        val e = c.etapes[jeu.etape]
        Placement.montrer(jeu, e)
        return Triple(ou, t("ad.perdu.lecon", "titre" to c.titre, "n" to jeu.etape + 1, "total" to c.etapes.size) + " · " + e.dit,
            Verif.commandeMontree(jeu, e, ici))
    }

    // ================================================================ 25. trois niveaux d'indice
    fun cible(jeu: Jeu): Triple<String, String, String>? {
        try { Dressage.exempleCourant(jeu)?.let { return Triple(it.first, it.second, "dressage") } } catch (e: Exception) { }
        val e = Entrainement.e(jeu)
        if (Entrainement.coursOk(e)) {
            val c = e.getJSONObject("cours")
            val p = Entrainement.generer(c.getString("type"), c.getString("v"), c.optLong("n"))
            val idees = Entrainement.idees(c.getString("type"), p)
            if (idees.isNotEmpty()) return Triple("ent:${c.optString("g")}:${c.optLong("n")}", idees.joinToString("  "), "exercice")
        }
        val l = Histoire.leconCourante(jeu)
        if (l != null && jeu.niveau >= l.niveau) {
            val st = l.etapes[jeu.etape]
            if (Placement.cache(jeu, st)) return Triple("lecon:${l.id}:${jeu.etape}", st.cmd, "lecon")
        }
        return null
    }

    fun texteIndice(attendu: String, n: Int): String {
        val p = partiesIndice(attendu.split("  ")[0])
        return when (n) {
            1 -> Regles.LEXIQUE.firstOrNull { it.cmd == p["cmd"]!!.lowercase() }?.let { t("ad.ind.n1", "image" to it.image) }
                ?: t("ad.ind.n1_sans", "n" to p["cmd"]!!.length)
            2 -> t("ad.ind.n2", "cmd" to "`${p["debut"]}`")
            else -> t("ad.ind.n3", "cmd" to attendu.split("  ").joinToString("  ") { "`$it`" })
        }
    }

    /** `indice` : le niveau suivant (1, 2 puis 3). (n, titre, texte) ou null s'il n'y a rien à chercher. */
    fun demanderIndice(jeu: Jeu): Triple<Int, String, String>? {
        val (cle, attendu, quoi) = cible(jeu) ?: return null
        val a = a(jeu)
        val i = a.optJSONObject("indice")
        val n = if (i != null && i.optString("cle") == cle) minOf(3, i.optInt("n") + 1) else 1
        a.put("indice", JSONObject().put("cle", cle).put("n", n))
        if (n == 3) reponseVue(jeu, quoi)
        return Triple(n, t("ad.ind.t$n"), texteIndice(attendu, n))
    }

    fun texteDemandeIndice(jeu: Jeu): String {
        val r = demanderIndice(jeu) ?: return "💡 " + t("ad.ind.rien")
        val (n, titre, texte) = r
        return "💡".repeat(n) + " " + titre + " ($n/3)\n   " + texte + "\n   " +
            (if (n < 3) t("ad.ind.encore", "cmd" to "`indice`") else t("ad.ind.rien_retire"))
    }

    private fun reponseVue(jeu: Jeu, quoi: String) {
        val l = Histoire.leconCourante(jeu) ?: return
        if (quoi == "lecon") Placement.montrer(jeu, l.etapes[jeu.etape])
        if (l.id in Forge.SANS_INDICE) Forge.indiceVu(jeu, l.id)
    }

    fun fantomePermis(jeu: Jeu): Boolean = try { cible(jeu) == null } catch (e: Exception) { true }
}
