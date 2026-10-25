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

    fun debloquee(jeu: Jeu) = "Bâtisseur" in jeu.skills && File(jeu.terrain, "nid").isDirectory

    /** Un monstre sauvage apparaît (pendant qu'on joue) : le dressage commence aussitôt. */
    fun spawn(jeu: Jeu) {
        if (Dressage.actif(jeu)) return
        val t = Bestiaire.tirer()
        var e = t.espece
        var vid = t.variante
        val caps = captures(jeu)
        val legendaires = (0 until caps.length()).count { Bestiaire.rareteDe(caps.getJSONObject(it)) == "légendaire" }
        if (legendaires >= 3 && Random.nextDouble() < 1.0 / 15 && collection(jeu).optInt("Abyssor") == 0) {
            Bestiaire.espece("Abyssor")?.let { e = it; vid = "classique" }      // la mythique secrète #151
        }
        val zone = Bestiaire.variante(e, vid).zone
        File(jeu.terrain, zone).mkdirs()
        etat(jeu).put("explo_n", etat(jeu).optInt("explo_n") + 1)
        // l'individu est tiré dès son apparition : stats, rareté et stade sont lisibles sur sa fiche (cat)
        val ind = Bestiaire.individu(e, t.shiny, zone, vid)
        ind.put("stade", Bestiaire.choisir(Bestiaire.STADES.take(4), listOf(35.0, 35.0, 20.0, 10.0)))
        if (t.shiny) ind.put("teinte", Bestiaire.arrondi(Random.nextDouble(0.15, 0.85), 3))   // couleur shiny propre à cet individu
        jeu.log(Mots.accorder("⚔ Un monstre sauvage apparaît : {nom} !", "nom" to e.nom))
        jeu.animer("attaque")
        Dressage.commencer(jeu, e, ind)
    }

    /** Ouverture de l'exploration. */
    fun verifier(jeu: Jeu): String? {
        if (!debloquee(jeu)) return null
        val e = etat(jeu)
        if (!e.optBoolean("ouverte")) {
            e.put("ouverte", true)
            jeu.log("🌲 Exploration débloquée !")
            spawn(jeu)
            return "🌲 L'exploration est ouverte : en jouant, des monstres sauvages vont apparaître !"
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
            "  #%03d · $r · ${e.famille}".format(e.numero) + (if (v != "classique") " · $v" else "") + "\n" +
            "   signe particulier : ${ind.optString("marque", "?")}\n" +
            "   humeur ${ind.optString("humeur", "?")} · ${ind.opt("taille") ?: "?"} cm · potentiel ${ind.opt("potentiel") ?: "?"} %"
    }

    fun texteCollection(jeu: Jeu): String {
        val coll = collection(jeu)
        val vues = coll.keys().asSequence().filter { coll.optInt(it) > 0 }.toSet()
        val caps = captures(jeu)
        val parRarete = LinkedHashMap<String, Int>()
        for (i in 0 until caps.length()) Bestiaire.rareteDe(caps.getJSONObject(i)).let { parRarete[it] = (parRarete[it] ?: 0) + 1 }
        val sb = StringBuilder("🐾 Collection de ${jeu.nom}\n")
        sb.append("Espèces découvertes : ${vues.size}/150   ")
            .append(Bestiaire.RARETES.filter { it in parRarete }.joinToString("  ") { "$it ${parRarete[it]}" }).append("\n")
        val shinies = (0 until caps.length()).count { caps.getJSONObject(it).optBoolean("shiny") }
        sb.append("Bestioles dressées : ${caps.length()}" + (if (shinies > 0) " · dont §$shinies shiny§" else "") + "\n")
        if (coll.optInt("Abyssor") > 0) sb.append("§★ Espèce secrète #151 découverte : Abyssor§\n")
        sb.append("\n")
        if (caps.length() > 0) {
            sb.append("Tes dernières captures :\n")
            for (i in caps.length() - 1 downTo maxOf(0, caps.length() - 6)) sb.append(carte(caps.getJSONObject(i))).append("\n\n")
        } else sb.append("Aucune bestiole dressée pour l'instant.\n")
        if (!debloquee(jeu)) {
            sb.append("L'exploration s'ouvre avec la leçon « Construire mon nid ».")
        } else {
            sb.append("Joue avec ton familier : des monstres sauvages finiront par apparaître.")
            sb.append("\nTa troupe : troupe · fiche d'une espèce : bestiaire <nom> · les 150 : site bestiaire")
        }
        return sb.toString()
    }

    /** bestiaire <nom> : fiche détaillée (complète seulement si l'espèce a déjà été capturée). */
    fun fiche(jeu: Jeu, nom: String): String {
        val coll = collection(jeu)
        if (nom.isBlank()) {
            val vues = coll.keys().asSequence().filter { coll.optInt(it) > 0 }.mapNotNull { Bestiaire.espece(it) }
                .sortedBy { it.numero }.toList()
            if (vues.isEmpty()) return "Tu n'as encore capturé aucune bestiole. Exemple : bestiaire Braisillon"
            return "Tes espèces : " + vues.joinToString(", ") { "#%03d ${it.nom}".format(it.numero) } + "\nFiche : bestiaire <nom>"
        }
        val e = Bestiaire.espece(nom)
        val connue = e != null && coll.optInt(e.nom) > 0
        if (e == null || (e.secrete && !connue)) return "Aucune espèce ne s'appelle « $nom ». Les 150 sont sur le site : site bestiaire"
        val entete = "#%03d ".format(e.numero) + (if (connue) Bestiaire.nomAffiche(e) else "???") +
            "  se montre ${e.frequence} · ${e.icone} ${e.famille}"
        if (!connue) {
            return "$entete\nPas encore dans ta troupe.\nHabitat : ${Bestiaire.lieu(e.zone)}  (${e.zone})\n" +
                "Cette espèce se montre ${e.frequence}, attirée par la commande « ${e.attireePar} »."
        }
        val vars = e.variantes.drop(1).map { it.nom }
        return Bestiaire.balise(e, grand = true) + "\n$entete\n${e.description}\n${e.comportement}\n" +
            "Capacité : ${e.capacite} · point fort : ${e.stat}\n" +
            "Taille ~${e.tailleCm} cm · poids ~${e.poidsKo} Ko\n" +
            Mots.texteStats(e.stats, Mots.palier(jeu)) + "\n" +
            "Habitat : ${Bestiaire.lieu(e.zone)} · attirée par « ${e.attireePar} »\n" +
            (if (vars.isNotEmpty()) "Variantes : ${vars.joinToString(", ")}\n" else "") +
            "Tu en as dressé ${coll.optInt(e.nom)}."
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
        jeu.dire("⚡ DÉFI ÉCLAIR ! Tape « ${Regles.piege(cmd)} » en moins de 20 s !", 20)
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
            val m = "⚡ Défi réussi en ${"%.1f".format(t)} s" + if (nouveau) " — NOUVEAU RECORD !" else ""
            jeu.log(m)
            jeu.dire(m, 8)
            return m
        }
        if (ecoule > DUREE) {
            d.put("cmd", "")
            jeu.log("⚡ Défi « $cmd » raté…")
            jeu.dire("Trop lent ! On réessaiera.", 6)
            jeu.animer("confus")
        }
        return null
    }

    fun texteRecords(jeu: Jeu): String {
        val rec = jeu.module("defi").optJSONObject("records") ?: return "Aucun record pour l'instant : tape « defi » !"
        if (rec.length() == 0) return "Aucun record pour l'instant : tape « defi » !"
        return "⚡ Tes records :\n" + rec.keys().asSequence().joinToString("\n") { "  $it : ${"%.1f".format(rec.optDouble(it))} s" }
    }
}
