package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject

/**
 * Les Ponts des Nombres (docs/programme.md § 7.10), portage de pc/tg/maths.py :
 *   maths                      les passerelles, les ponts allumés
 *   maths <mots>               la fiche la plus proche (moteur de recherche du lexique : Recherche.kt), un exercice
 *   maths <nombre>             la réponse à l'exercice en cours
 *   maths oui | un peu | pas du tout, « je ne connais pas »
 *                              « Tu connais … ? » : on descend dans le graphe des prérequis, puis on revient
 * Jamais bloquant. Vecteurs communs : donnees/maths/vecteurs.json (exercices et recherches).
 */
object Maths {
    const val MASQUE_HEX = 16

    fun noeuds(): JSONObject = Programme.donnees().optJSONObject("maths") ?: JSONObject()
    fun noeud(id: String): JSONObject? = noeuds().optJSONObject(id)
    fun titre(id: String): String = t(noeud(id)?.optString("titre") ?: id)

    private fun liste(o: JSONObject, k: String): MutableList<String> {
        val a = o.optJSONArray(k) ?: JSONArray().also { o.put(k, it) }
        return (0 until a.length()).map { a.getString(it) }.toMutableList()
    }
    private fun mettre(o: JSONObject, k: String, l: List<String>) { o.put(k, JSONArray(l)) }

    fun etat(jeu: Jeu): JSONObject {
        val m = jeu.module("maths")
        for (k in listOf("acquis", "connus", "pile")) if (m.optJSONArray(k) == null) m.put(k, JSONArray())
        if (!m.has("n")) m.put("n", 0)
        return m
    }
    private fun chaine(m: JSONObject, k: String): String? = if (m.isNull(k)) null else m.optString(k).ifEmpty { null }

    // ---------------------------------------------------------------- le graphe des prérequis
    fun prerequis(id: String): List<String> = noeud(id)?.optJSONArray("prerequis")?.let { a -> (0 until a.length()).map { a.getString(it) } }
        ?: emptyList()

    fun tousPrerequis(id: String): List<String> {
        val out = mutableListOf<String>()
        fun visiter(x: String) { for (p in prerequis(x)) if (p !in out) { visiter(p); out.add(p) } }
        visiter(id)
        return out
    }

    fun sait(jeu: Jeu, id: String): Boolean { val m = etat(jeu); return id in liste(m, "acquis") || id in liste(m, "connus") }
    fun manquant(jeu: Jeu, id: String): String? = prerequis(id).firstOrNull { !sait(jeu, it) }

    // ---------------------------------------------------------------- la recherche (moteur du lexique)
    private val index = HashMap<Pair<String, String>, Pair<Set<String>, Set<String>>>()
    /** (concepts du titre et des mots-clés, concepts de la question et de l'image), en français et dans la langue. */
    private fun conceptsDe(id: String): Pair<Set<String>, Set<String>> = synchronized(index) {
        index.getOrPut(id to Langue.courante) {
            val n = noeud(id)!!
            val codes = if (Langue.courante == Langue.DEFAUT) listOf(Langue.DEFAUT) else listOf(Langue.DEFAUT, Langue.courante)
            val forts = listOf(n.getString("titre")) + listOfNotNull(n.optString("mots_cles").ifEmpty { null })
            val doux = listOf("question", "enfant").mapNotNull { k -> n.optString(k).ifEmpty { null } }
            fun c(cles: List<String>) = Recherche.concepts(codes.flatMap { x -> cles.map { (Langue.brut(it, x) ?: "").toString() } }.joinToString(" "))
            c(forts) to c(doux)
        }
    }

    fun chercher(requete: String): String? {
        val q = requete.trim().lowercase()
        if (q.isEmpty()) return null
        if (noeuds().has(q)) return q
        val qc = Recherche.concepts(requete)
        var meilleur: String? = null
        var score = 0.0
        for (id in noeuds().keys()) {
            val (forts, doux) = conceptsDe(id)
            val a = (qc intersect forts).size
            val b = (qc intersect (doux - forts)).size
            if (a == 0 && b == 0) continue
            val s = a * 10 + b * 3 - ((forts + doux) - qc).size * 0.01 + (if (noeud(id)!!.optBoolean("fiche")) 1 else 0)
            if (s > score) { meilleur = id; score = s }
        }
        return meilleur
    }

    // ---------------------------------------------------------------- les exercices (même hasard que le PC)
    class Exo(val params: Map<String, String>, val reponse: String, val verif: String)

    fun generer(typ: String, graine: Long, k: Long): Exo {
        val h = Tirage.Hasard(String.format("%016x", graine), k)
        return when (typ) {
            "comptage" -> { val n = 3 + h.entier(10); Exo(mapOf("etoiles" to "★".repeat(n)), "$n", "seq $n | wc -l") }
            "addition" -> { val a = 2 + h.entier(19); val b = 2 + h.entier(19); Exo(mapOf("a" to "$a", "b" to "$b"), "${a + b}", "echo \$(($a + $b))") }
            "soustraction" -> { val a = 5 + h.entier(16); val b = 1 + h.entier(a - 1); Exo(mapOf("a" to "$a", "b" to "$b"), "${a - b}", "echo \$(($a - $b))") }
            "multiplication" -> { val a = 2 + h.entier(9); val b = 2 + h.entier(9); Exo(mapOf("a" to "$a", "b" to "$b"), "${a * b}", "echo \$(($a * $b))") }
            "division", "modulo" -> {
                val b = 2 + h.entier(8); val q = 1 + h.entier(9); val r = h.entier(b); val a = b * q + r
                if (typ == "division") Exo(mapOf("a" to "$a", "b" to "$b"), "$q", "echo \$(($a / $b))")
                else Exo(mapOf("a" to "$a", "b" to "$b"), "$r", "echo \$(($a % $b))")
            }
            "puissances" -> {
                val a = 2 + h.entier(4); val b = 2 + h.entier(3)
                var p = 1L; repeat(b) { p *= a }
                Exo(mapOf("a" to "$a", "b" to "$b", "calcul" to List(b) { "$a" }.joinToString(" × ")), "$p",
                    "echo \$((" + List(b) { "$a" }.joinToString(" * ") + "))")
            }
            "binaire" -> { val n = 1 + h.entier(31); val bits = Integer.toBinaryString(n); Exo(mapOf("bits" to bits), "$n", "echo \$((2#$bits))") }
            else -> throw IllegalArgumentException(typ)
        }
    }

    private fun graine(jeu: Jeu): Long {
        val m = etat(jeu)
        if (!m.has("graine")) m.put("graine", System.currentTimeMillis() / 1000)
        return m.getLong("graine")
    }

    private fun nouvelExo(jeu: Jeu, id: String): String {
        val m = etat(jeu)
        val ex = noeud(id)!!.getJSONObject("exercice")
        val e = generer(ex.getString("type"), graine(jeu), m.optLong("n"))
        m.put("n", m.optLong("n") + 1)
        val params = JSONObject(); for ((k, v) in e.params) params.put(k, v)
        m.put("exo", JSONObject().put("notion", id).put("params", params).put("reponse", e.reponse).put("verif", e.verif))
        return t(ex.getString("consigne"), *e.params.map { it.key to it.value }.toTypedArray())
    }

    // ---------------------------------------------------------------- l'écran d'une fiche
    /** « oui » / « peu » / « non » (pas du tout, je ne connais pas) / null, en français ou dans la langue choisie. */
    fun motsReponse(texte: String): String? {
        val x = Recherche.mots(texte).joinToString(" ")
        for (code in listOf(Langue.DEFAUT, Langue.courante)) {
            for ((genre, cle) in listOf("non" to "maths.mot.inconnu", "non" to "maths.mot.non", "peu" to "maths.mot.peu", "oui" to "maths.mot.oui")) {
                val v = Langue.brut(cle, code)?.toString() ?: continue
                if (x == Recherche.mots(v).joinToString(" ")) return genre
            }
        }
        return null
    }

    /** La phrase « je ne connais pas » tapée toute seule (sans « maths » devant). */
    fun estInconnu(ligne: String): Boolean {
        val x = Recherche.mots(ligne).joinToString(" ")
        return x.isNotEmpty() && listOf(Langue.DEFAUT, Langue.courante).any { c ->
            Langue.brut("maths.mot.inconnu", c)?.toString()?.let { Recherche.mots(it).joinToString(" ") == x } == true }
    }

    private fun question(jeu: Jeu, id: String?, cmd: String): List<String> {
        val m = etat(jeu)
        val p = id?.let { manquant(jeu, it) }
        m.put("question", p ?: JSONObject.NULL)
        if (p == null) return emptyList()
        return listOf("", " " + t("maths.demande", "notion" to titre(p), "question" to t(noeud(p)!!.getString("question"))),
            " " + t("maths.choix", "oui" to "$cmd ${t("maths.mot.oui")}", "peu" to "$cmd ${t("maths.mot.peu")}",
                "non" to "$cmd ${t("maths.mot.non")}"))
    }

    fun ecranFiche(jeu: Jeu, id: String, cmd: String): List<String> {
        val m = etat(jeu)
        val n = noeud(id)!!
        m.put("courant", id)
        val out = mutableListOf(t("maths.titre") + " · " + titre(id))
        if (!n.optBoolean("fiche")) {
            val base = prerequis(id).map { titre(it) }.ifEmpty { listOf(titre("comptage")) }
            out.add(" " + t("maths.pas_encore", "notion" to titre(id), "liste" to base.joinToString(", ")))
            m.put("question", JSONObject.NULL)
            return out
        }
        out.add(" " + t(n.getString("enfant")))
        out.add(" " + t("grand.ligne", "texte" to t(n.getString("grands"))))
        out.add(" " + t("prog.limite", "texte" to t(n.getString("limite_image"))))
        val idees = n.getJSONArray("idees_fausses")
        for (i in 0 until idees.length()) out.add(" " + t("prog.idee", "texte" to t(idees.getString(i))))
        out.add(" " + t("maths.exemples"))
        val ex = n.getJSONArray("exemples")
        for (i in 0 until ex.length()) out.add("   • " + t(ex.getString(i)))
        if (prerequis(id).isNotEmpty()) out.add(" " + t("maths.prerequis", "liste" to prerequis(id).joinToString(", ") { titre(it) }))
        out.add("")
        out.add(" " + t("maths.exercice", "exo" to nouvelExo(jeu, id)))
        out.add("   " + t("maths.repondre", "cmd" to cmd))
        return out + question(jeu, id, cmd)
    }

    fun apercu(jeu: Jeu, cmd: String): List<String> {
        val m = etat(jeu)
        val fiches = noeuds().keys().asSequence().filter { noeud(it)!!.optBoolean("fiche") }.toList()
        val acquis = liste(m, "acquis")
        val out = mutableListOf(t("maths.titre"), " " + t("maths.aide", "cmd" to cmd),
            " " + t("maths.passerelles", "liste" to fiches.joinToString(", ") { titre(it) }),
            " " + if (acquis.isNotEmpty()) t("maths.allumes", "liste" to acquis.joinToString(", ") { titre(it) }) else t("maths.aucun"))
        chaine(m, "courant")?.let { out.add(" " + t("maths.en_cours", "notion" to titre(it))) }
        return out
    }

    fun repondreNombre(jeu: Jeu, texte: String, cmd: String): List<String> {
        val m = etat(jeu)
        val e = m.optJSONObject("exo") ?: return listOf(t("maths.pas_exo", "cmd" to "$cmd division"))
        val id = e.getString("notion")
        val n = noeud(id)!!
        val verif = " " + t("maths.verifie", "verif" to e.getString("verif"))
        val rep = e.getString("reponse")
        if (texte.trim().trimStart('0') == rep.trimStart('0') || texte.trim() == rep) {
            m.remove("exo")
            val acquis = liste(m, "acquis")
            if (id !in acquis) { acquis.add(id); mettre(m, "acquis", acquis) }
            val out = mutableListOf(t("maths.juste", "notion" to titre(id)), verif)
            val pile = liste(m, "pile")
            if (pile.isNotEmpty()) {
                val haut = pile.removeAt(pile.size - 1)
                mettre(m, "pile", pile)
                out.add(""); out.add(t("maths.retour", "notion" to titre(haut)))
                out.addAll(ecranFiche(jeu, haut, cmd))
            }
            return out
        }
        val params = e.getJSONObject("params")
        val astuce = t(n.getJSONObject("exercice").getString("erreur"), *params.keys().asSequence().map { it to params.getString(it) }.toList().toTypedArray())
        return listOf(t("maths.faux", "reponse" to rep, "astuce" to astuce), verif, " " + t("maths.encore", "exo" to nouvelExo(jeu, id)))
    }

    fun repondreMot(jeu: Jeu, genre: String, cmd: String): List<String> {
        val m = etat(jeu)
        var q = chaine(m, "question")
        val cour = chaine(m, "courant")
        if (q == null) {
            if (genre == "oui") return apercu(jeu, cmd)
            if (cour != null && manquant(jeu, cour) != null) q = manquant(jeu, cour)
            else if (cour != null) return listOf(t("maths.descend", "notion" to titre(cour))) +
                (if (prerequis(cour).isEmpty()) listOf(t("maths.fond")) else emptyList()) + ecranFiche(jeu, cour, cmd)
            else return listOf(t("maths.fond")) + ecranFiche(jeu, "comptage", cmd)
        }
        if (genre == "oui") {
            val connus = liste(m, "connus")
            if (q!! !in connus) { connus.add(q); mettre(m, "connus", connus) }
            m.put("question", JSONObject.NULL)
            val suite = if (cour != null) question(jeu, cour, cmd) else emptyList()
            if (suite.isNotEmpty()) return suite.drop(1)
            return if (cour != null) listOf(t("maths.continue", "notion" to titre(cour))) else apercu(jeu, cmd)
        }
        val pile = liste(m, "pile")
        if (cour != null && cour != q && cour !in pile) { pile.add(cour); mettre(m, "pile", pile) }
        val out = mutableListOf(t("maths.descend", "notion" to titre(q!!)))
        if (prerequis(q).isEmpty()) out.add(t("maths.fond"))
        return out + ecranFiche(jeu, q, cmd)
    }

    /** maths … : les lignes à afficher (l'état « maths » de la partie est mis à jour). */
    fun lignes(jeu: Jeu, texte: String, cmd: String = "maths"): List<String> {
        val x = texte.trim()
        if (x.isEmpty()) return apercu(jeu, cmd)
        if (Regex("-?\\d+").matches(x)) return repondreNombre(jeu, x, cmd)
        motsReponse(x)?.let { return repondreMot(jeu, it, cmd) }
        val id = chercher(x) ?: return listOf(t("maths.rien", "cmd" to cmd))
        return ecranFiche(jeu, id, cmd)
    }

    fun commande(jeu: Jeu, texte: String): String = lignes(jeu, texte).joinToString("\n")
}
