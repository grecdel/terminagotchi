package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import kotlin.random.Random

/**
 * Exploration : les zones sont de vrais dossiers du terrain de jeu (portage de pc/tg/explo.py).
 * Les 150 espèces du bestiaire s'y cachent, chacune dans l'habitat de sa variante.
 * Pendant qu'on joue, un monstre sauvage peut apparaître : il faut alors le dresser (voir Dressage.kt).
 * Chaque bestiole est un individu unique, tiré dès son apparition : stats, variante, stade, rareté
 * (5 paliers, plus « mythique » pour Abyssor)… et parfois shiny ✨, avec une teinte qui n'est qu'à elle.
 */
object Explo {
    private fun etat(jeu: Jeu) = jeu.module("explo")

    fun collection(jeu: Jeu): JSONObject =
        etat(jeu).optJSONObject("collection") ?: JSONObject().also { etat(jeu).put("collection", it) }

    fun captures(jeu: Jeu): JSONArray =
        etat(jeu).optJSONArray("captures") ?: JSONArray().also { etat(jeu).put("captures", it) }

    fun nbCaptures(jeu: Jeu): Int {
        val c = collection(jeu)
        return c.keys().asSequence().sumOf { c.optInt(it) }
    }

    /** Les monstres arrivent après la mini-leçon des passages secrets (ls -a, fin du chapitre 2 : G-05) ; une partie
     *  où l'exploration était déjà ouverte la garde. */
    fun debloquee(jeu: Jeu) = "Bâtisseur" in jeu.skills && File(jeu.terrain, "nid").isDirectory &&
        (etat(jeu).optBoolean("ouverte") || "secrets" in Histoire.faits(jeu))

    /** La commande « attiree_par » d'une famille la rend plus probable pendant 10 minutes (une apparition). */
    const val DUREE_ATTIRANCE = 600_000L
    /** compteurs de la graine essayés au plus pour un tout premier monstre facile */
    const val ESSAIS_PREMIER = 30

    private fun icone(famille: String) = Bestiaire.publiques().firstOrNull { it.famille == famille }?.icone ?: ""

    /**
     * Attirance (comme explo.attirer sur PC) : une commande « attiree_par » tapée à la main attire sa famille
     * (la dernière tapée gagne). Le serveur exige une commande vraiment goûtée : elle doit être dans jeu.vus.
     */
    fun attirer(jeu: Jeu, ligne: String?, colle: Boolean) {
        if (ligne == null || colle || Regles.estColle(ligne)) return
        val cmd = Regles.premierMot(ligne)
        val f = Bestiaire.familles().entries.firstOrNull { it.value == cmd }?.key ?: return
        if (cmd !in jeu.vus) return
        val avant = attirance(jeu)
        etat(jeu).put("attirance", JSONObject().put("famille", f).put("cmd", cmd).put("t", System.currentTimeMillis()))
        if (avant != f && !Dressage.actif(jeu)) {
            jeu.log(t("exp.attire.log", "cmd" to cmd, "famille" to f))
            jeu.dire(t("exp.attire.dit", "cmd" to cmd, "famille" to f, "icone" to icone(f)), 8)
        }
    }

    /** La famille attirée en ce moment, ou null. */
    fun attirance(jeu: Jeu): String? {
        val a = etat(jeu).optJSONObject("attirance") ?: return null
        val f = a.optString("famille")
        return if (f in Bestiaire.familles() && System.currentTimeMillis() - a.optLong("t") < DUREE_ATTIRANCE) f else null
    }

    /** Un premier monstre facile : espèce courante (« souvent ») et individu de rareté commune. */
    fun facile(e: Bestiaire.Espece, ind: JSONObject) = e.frequence == "souvent" && Bestiaire.rareteDe(ind) == "commune"

    /** Sans graine (pas de compte, longtemps hors ligne…) : au hasard, « non vérifié » sur le site. */
    private fun auHasard(abyssorPermis: Boolean, attire: String?): Pair<Bestiaire.Espece, JSONObject> {
        val t = Bestiaire.tirer(attire = attire)
        var esp = t.espece
        var vid = t.variante
        if (abyssorPermis && Random.nextDouble() < 1.0 / 15) {
            Bestiaire.espece("Abyssor")?.let { esp = it; vid = "classique" }
        }
        // l'individu est tiré dès son apparition : stats, rareté et stade sont lisibles sur sa fiche (cat)
        val ind = Bestiaire.individu(esp, t.shiny, Bestiaire.variante(esp, vid).zone, vid)
        ind.put("stade", Bestiaire.choisir(Bestiaire.STADES.take(4), listOf(35.0, 35.0, 20.0, 10.0)))
        if (t.shiny) ind.put("teinte", Bestiaire.arrondi(Random.nextDouble(0.15, 0.85), 3))   // couleur shiny propre à cet individu
        return esp to ind
    }

    /**
     * Un monstre sauvage apparaît (pendant qu'on joue) : le dressage commence aussitôt.
     * Le tout premier (aucune bestiole dressée) est facile : espèce courante, rareté commune. On passe aux
     * compteurs suivants de la graine jusqu'à en trouver un (chacun reste vérifiable, le tirage ne change pas).
     * Renvoie l'apparition (espèce, individu), ou null s'il n'y en a pas eu.
     */
    fun spawn(jeu: Jeu): Pair<Bestiaire.Espece, JSONObject>? {
        if (Dressage.actif(jeu)) return null          // pas de nouveau monstre pendant un dressage
        val caps = captures(jeu)
        val legendaires = (0 until caps.length()).count { Bestiaire.rareteDe(caps.getJSONObject(it)) == "légendaire" }
        val abyssorPermis = legendaires >= 3 && collection(jeu).optInt("Abyssor") == 0   // la mythique secrète #151
        // la commande d'une famille l'attire ; sinon, le chapitre en cours attire la sienne (Histoire.familleAttiree)
        val attire = attirance(jeu) ?: Histoire.familleAttiree(jeu)
        val premier = caps.length() == 0
        var r: Pair<Bestiaire.Espece, JSONObject>? = null
        for (i in 0 until if (premier) ESSAIS_PREMIER else 1) {
            // anti-triche : tirage vérifiable par le serveur si une graine du jour est en cache (voir Tirage.kt)
            r = Tirage.apparition(jeu, abyssorPermis && !premier, attire) ?: auHasard(abyssorPermis && !premier, attire)
            if (!premier || facile(r.first, r.second)) break
        }
        if (attirance(jeu) != null) etat(jeu).remove("attirance")      // une commande attire UNE apparition
        val (e, ind) = r!!
        File(jeu.terrain, ind.optString("zone")).mkdirs()
        etat(jeu).put("explo_n", etat(jeu).optInt("explo_n") + 1)
        jeu.log(t("dress.apparait", "nom" to e.nom, "eclat" to ""))
        jeu.animer("attaque")
        Dressage.commencer(jeu, e, ind)
        return r
    }

    /** Ouverture de l'exploration. */
    fun verifier(jeu: Jeu): String? {
        if (!debloquee(jeu)) return null
        val e = etat(jeu)
        if (!e.optBoolean("ouverte")) {
            e.put("ouverte", true)
            jeu.log(t("exp.debloquee"))
            spawn(jeu)
            return t("expa.ouverte")
        }
        return null
    }

    /**
     * Texte d'une capture. ¤…¤ = dessin de la bestiole (voir Bestiaire.balise),
     * §texte§ = écriture arc-en-ciel : le terminal de l'appli les remplace à l'affichage.
     */
    fun carte(ind: JSONObject): String {
        val e = Bestiaire.espece(ind.optString("espece")) ?: return ind.optString("espece")
        val r = Bestiaire.rareteDe(ind)
        val v = ind.optString("variante", "classique")
        return Bestiaire.balise(ind) + " " + Bestiaire.nomAffiche(e, ind.optBoolean("shiny"), r) +
            "  #%03d · ".format(e.numero) + Bestiaire.nomRarete(r) + " · ${e.famille}" + (if (v != "classique") " · $v" else "") + "\n" +
            "   " + t("exp.signe") + " ${ind.optString("marque", "?")}\n" +
            "   " + t("exp.humeur", "humeur" to ind.optString("humeur", "?"),
                "cm" to (ind.opt("taille") ?: "?"), "pot" to (ind.opt("potentiel") ?: "?"))
    }

    fun texteCollection(jeu: Jeu): String {
        val coll = collection(jeu)
        val vues = coll.keys().asSequence().filter { coll.optInt(it) > 0 }.toSet()
        val caps = captures(jeu)
        val parRarete = LinkedHashMap<String, Int>()
        for (i in 0 until caps.length()) Bestiaire.rareteDe(caps.getJSONObject(i)).let { parRarete[it] = (parRarete[it] ?: 0) + 1 }
        val sb = StringBuilder("🐾 " + t("exp.collection.titre", "nom" to jeu.nom) + "\n")
        sb.append(t("exp.especes", "n" to "${vues.size}/150") + "   ")
            .append(Bestiaire.RARETES.filter { it in parRarete }.joinToString("  ") { "${Bestiaire.nomRarete(it)} ${parRarete[it]}" }).append("\n")
        val shinies = (0 until caps.length()).count { caps.getJSONObject(it).optBoolean("shiny") }
        sb.append(t("exp.dressees", "n" to caps.length()) +
            (if (shinies > 0) " · " + t("exp.dont_shiny", "shiny" to "§$shinies shiny§") else "") + "\n")
        if (coll.optInt("Abyssor") > 0) sb.append("§" + t("exp.abyssor") + "§\n")
        sb.append("\n")
        if (caps.length() > 0) {
            sb.append(t("exp.dernieres") + "\n")
            for (i in caps.length() - 1 downTo maxOf(0, caps.length() - 6)) sb.append(carte(caps.getJSONObject(i))).append("\n\n")
            sb.append(t("aura.legende") + "\n\n")              // la lueur autour des bestioles (Aura.kt)
        } else sb.append(t("exp.aucune_dressee") + "\n")
        if (!debloquee(jeu)) {
            sb.append(t("exp.s_ouvre", "lecon" to t("lec.t1.titre")))
        } else {
            sb.append(t("expa.joue"))
            val f = attirance(jeu)
            sb.append("\n" + (if (f != null) t("exp.attirance", "icone" to icone(f), "famille" to f, "cmd" to Bestiaire.familles()[f])
                else t("expa.attirance.aucune")))
            sb.append("\n" + t("expa.pied"))
        }
        return sb.toString()
    }

    /** bestiaire <nom> : fiche détaillée (complète seulement si l'espèce a déjà été capturée). */
    fun fiche(jeu: Jeu, nom: String): String {
        val coll = collection(jeu)
        if (nom.isBlank()) {
            val vues = coll.keys().asSequence().filter { coll.optInt(it) > 0 }.mapNotNull { Bestiaire.espece(it) }
                .sortedBy { it.numero }.toList()
            if (vues.isEmpty()) return t("expa.fiche.aucune")
            return t("exp.fiche.tes_especes", "liste" to vues.joinToString(", ") { "#%03d ${it.nom}".format(it.numero) }) +
                "\n" + t("expa.fiche.aide")
        }
        val e = Bestiaire.espece(nom)
        val connue = e != null && coll.optInt(e.nom) > 0
        if (e == null || (e.secrete && !connue)) return t("expa.fiche.inconnue", "nom" to nom)
        val freq = Bestiaire.nomFrequence(e.frequence)
        val entete = "#%03d ".format(e.numero) + (if (connue) Bestiaire.nomAffiche(e) else "???") +
            "  " + t("exp.fiche.se_montre", "frequence" to freq) + " · ${e.icone} ${e.famille}"
        if (!connue) {
            return entete + "\n" + t("exp.fiche.pas_encore") + "\n" +
                t("exp.fiche.habitat", "lieu" to Bestiaire.lieu(e.zone)) + "  (${e.zone})\n" +
                t("exp.fiche.attiree", "frequence" to freq, "cmd" to e.attireePar)
        }
        val vars = e.variantes.drop(1).map { it.nom }
        return Bestiaire.balise(e, grand = true) + "\n$entete\n${e.description}\n${e.comportement}\n" +
            t("exp.fiche.capacite", "capacite" to e.capacite, "stat" to Regles.nomStat(e.stat)) + "\n" +
            t("exp.fiche.taille", "cm" to e.tailleCm, "ko" to e.poidsKo) + "\n" +
            Mots.texteStats(e.stats, Mots.palier(jeu)) + "\n" +
            t("exp.fiche.habitat_attiree", "lieu" to Bestiaire.lieu(e.zone), "cmd" to e.attireePar) + "\n" +
            (if (vars.isNotEmpty()) t("exp.fiche.variantes", "liste" to vars.joinToString(", ")) + "\n" else "") +
            t("exp.fiche.dresses", "n" to coll.optInt(e.nom))
    }
}

/** Défis éclair : « tape cette commande le plus vite possible ». */
object Defis {
    val POOL = listOf("pwd", "ls", "date", "whoami", "id", "uptime")
    const val DUREE = 20_000L

    fun actif(jeu: Jeu): String? = jeu.module("defi").optString("cmd", "").ifEmpty { null }

    fun lancer(jeu: Jeu) {
        val cmd = POOL.random()
        jeu.module("defi").put("cmd", cmd).put("debut", System.currentTimeMillis())
        jeu.dire(t("defi.dit", "cmd" to Regles.piege(cmd)), 20)
        Guide.annonceDefi(jeu)                              // l'épreuve du jour annonce un type (Guide.kt)
    }

    fun resteSecondes(jeu: Jeu): Long {
        val d = jeu.module("defi")
        return ((d.optLong("debut") + DUREE - System.currentTimeMillis()) / 1000).coerceAtLeast(0)
    }

    /** À appeler après chaque commande tapée. Renvoie un message de victoire ou null. */
    fun verifier(jeu: Jeu, ligne: String?): String? {
        val d = jeu.module("defi")
        val cmd = actif(jeu) ?: return null
        val ecoule = System.currentTimeMillis() - d.optLong("debut")
        if (ligne != null && Regles.premierMot(ligne) == cmd && !Regles.estColle(ligne)) {
            val t = ecoule / 1000.0
            val rec = d.optJSONObject("records") ?: JSONObject().also { d.put("records", it) }
            val ancien = rec.optDouble(cmd, Double.MAX_VALUE)
            val nouveau = t < ancien
            if (nouveau) rec.put(cmd, t)
            d.put("cmd", "")
            jeu.stats["Agilité"] = (jeu.stats["Agilité"] ?: 0) + 2
            jeu.animer("victoire")
            jeu.ajouterXp(10)
            Envies.plaisir(jeu, "jeu", "defi")
            Guide.apresDefi(jeu)                            // guide fort contre le type du jour : +5 XP
            val m = t("defi.reussi", "s" to "%.1f".format(t)) + if (nouveau) t("defi.record") else ""
            jeu.log(m)
            jeu.dire(m, 8)
            return m
        }
        if (ecoule > DUREE) {
            d.put("cmd", "")
            jeu.log(t("core.defi.rate.log", "cmd" to cmd))
            jeu.dire(t("core.defi.rate.dit"), 6)
            jeu.animer("confus")
        }
        return null
    }

    fun texteRecords(jeu: Jeu): String {
        val rec = jeu.module("defi").optJSONObject("records") ?: return t("defi.aucun_record")
        if (rec.length() == 0) return t("defi.aucun_record")
        return t("defi.records") + "\n" + rec.keys().asSequence().joinToString("\n") { "  $it : ${"%.1f".format(rec.optDouble(it))} s" }
    }
}
