package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import kotlin.random.Random

/**
 * Exploration : les zones sont de vrais dossiers du terrain de jeu.
 * Les 150 espèces du bestiaire s'y cachent en fichiers cachés, chacune dans l'habitat de sa famille ;
 * plus elle est rare, plus elle est profonde (recoin → cachette → sanctuaire).
 * Pendant qu'on joue, un monstre sauvage peut apparaître : il faut alors le dresser (voir Dressage.kt).
 * Chaque capture est un individu unique (marque, humeur, taille, potentiel… et parfois shiny ✨).
 */
object Explo {
    private fun etat(jeu: Jeu) = jeu.module("explo")

    private fun sauvages(jeu: Jeu): JSONArray =
        etat(jeu).optJSONArray("sauvages") ?: JSONArray().also { etat(jeu).put("sauvages", it) }

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
        var (e, shiny) = Bestiaire.tirer()
        val legendaires = Bestiaire.especes.count { it.rarete == "légendaire" && collection(jeu).optInt(it.nom) > 0 }
        if (legendaires >= 3 && Random.nextInt(15) == 0 && collection(jeu).optInt("Abyssor") == 0) {
            Bestiaire.espece("Abyssor")?.let { e = it }      // la légendaire secrète #151
        }
        File(jeu.terrain, e.zone).mkdirs()
        Dressage.commencer(jeu, e, shiny)
    }

    /** Ouverture de l'exploration, et fuite si la fiche du monstre a été effacée. */
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
     * Texte d'une capture. ¤id¤ (ou ¤id*¤ pour shiny) = dessin de la bestiole,
     * §texte§ = écriture arc-en-ciel : le terminal de l'appli les remplace à l'affichage.
     */
    fun carte(ind: JSONObject): String {
        val e = Bestiaire.espece(ind.optString("espece")) ?: return ind.optString("espece")
        val shiny = ind.optBoolean("shiny")
        val nom = e.nom + if (shiny) " ✨" else ""
        val titre = if (shiny || e.rarete == "légendaire") "§$nom§" else nom
        return "¤${e.id}${if (shiny) "*" else ""}¤ $titre  #%03d · ${e.rarete} · ${e.famille}\n".format(e.numero) +
            "   signe particulier : §${ind.optString("marque")}§\n" +
            "   humeur ${ind.optString("humeur")} · ${ind.optDouble("taille")} cm · potentiel ${ind.optInt("potentiel")} %"
    }

    fun texteCollection(jeu: Jeu): String {
        val coll = collection(jeu)
        val vues = Bestiaire.especes.filter { coll.optInt(it.nom) > 0 && !it.secrete }
        val caps = captures(jeu)
        val sb = StringBuilder("🐾 Collection de ${jeu.nom}\n")
        sb.append("Espèces découvertes : ${vues.size}/150\n")
        for (r in listOf("commune", "peu commune", "rare", "légendaire")) {
            val tot = Bestiaire.especes.count { it.rarete == r && !it.secrete }
            sb.append("   $r : ${vues.count { it.rarete == r }}/$tot\n")
        }
        val shinies = (0 until caps.length()).count { caps.getJSONObject(it).optBoolean("shiny") }
        sb.append("Bestioles dressées : ${caps.length()}" + (if (shinies > 0) " · dont §$shinies shiny§" else "") + "\n")
        if (coll.optInt("Abyssor") > 0) sb.append("§★ Espèce secrète #151 découverte : Abyssor§\n")
        if (caps.length() > 0) {
            sb.append("\nTes dernières captures :\n")
            for (i in caps.length() - 1 downTo maxOf(0, caps.length() - 5)) sb.append(carte(caps.getJSONObject(i))).append("\n\n")
        }
        if (!debloquee(jeu)) {
            sb.append("L'exploration s'ouvre avec la leçon « Construire mon nid ».")
        } else {
            sb.append("Joue avec ton familier : des monstres sauvages finiront par apparaître.")
            sb.append("\nTon équipe : equipe · fiche d'une espèce : bestiaire <nom> · les 150 : site bestiaire")
        }
        return sb.toString()
    }

    /** bestiaire <nom> : fiche complète seulement si l'espèce a déjà été capturée. */
    fun fiche(jeu: Jeu, nom: String): String {
        val coll = collection(jeu)
        if (nom.isBlank()) {
            val vues = Bestiaire.especes.filter { coll.optInt(it.nom) > 0 }
            if (vues.isEmpty()) return "Tu n'as encore capturé aucune bestiole. Exemple : bestiaire Glitchou"
            return "Tes espèces : " + vues.joinToString(", ") { "#%03d ${it.nom}".format(it.numero) } + "\nFiche : bestiaire <nom>"
        }
        val e = Bestiaire.espece(nom)
        val connue = e != null && coll.optInt(e.nom) > 0
        if (e == null || (e.secrete && !connue)) return "Aucune espèce ne s'appelle « $nom ». Les 150 sont sur le site : site bestiaire"
        val entete = "#%03d ".format(e.numero) + (if (!connue) "???" else if (e.rarete == "légendaire") "§${e.nom}§" else e.nom) +
            " · ${e.rarete} · ${e.icone} ${e.famille}"
        if (!connue) {
            return "$entete\nTu ne l'as pas encore dressée.\nHabitat : ${Bestiaire.lieu(e.zone)} (${e.zone})\n" +
                "Elle se montre ${e.frequence}, attirée par la commande « ${e.attireePar} »."
        }
        val dessin = if (Animations.dispo(e.id)) "¤${e.id}+¤\n" else "¤${e.id}¤ "     // version détaillée pour la fiche
        return "$dessin$entete\n${e.description}\n${e.comportement}\n" +
            "Capacité : ${e.capacite} · stat favorite : ${e.stat}\n" +
            "Taille ~${e.tailleCm} cm · poids ~${e.poidsKo} Ko\n" +
            e.stats.entries.joinToString("  ") { "${it.key} ${it.value}" } + "\n" +
            "Habitat : ${Bestiaire.lieu(e.zone)} · attirée par « ${e.attireePar} »\nTu en as dressé ${coll.optInt(e.nom)}."
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
        }
        return null
    }

    fun texteRecords(jeu: Jeu): String {
        val rec = jeu.module("defi").optJSONObject("records") ?: return "Aucun record pour l'instant : tape « defi » !"
        if (rec.length() == 0) return "Aucun record pour l'instant : tape « defi » !"
        return "⚡ Tes records :\n" + rec.keys().asSequence().joinToString("\n") { "  $it : ${"%.1f".format(rec.optDouble(it))} s" }
    }
}
