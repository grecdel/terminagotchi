package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Exploration : les zones sont de vrais dossiers du terrain de jeu.
 * Les 150 espèces du bestiaire s'y cachent en fichiers cachés, chacune dans l'habitat de sa famille ;
 * plus elle est rare, plus elle est profonde (recoin → cachette → sanctuaire).
 * On la trouve avec ls -a, on la lit avec cat, on la capture en la déplaçant dans le nid avec mv.
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

    fun spawn(jeu: Jeu) {
        val s = sauvages(jeu)
        if (s.length() >= 3) return
        val (e, shiny) = Bestiaire.tirer()
        val zone = e.zone
        val dossier = File(jeu.terrain, zone)
        dossier.mkdirs()
        val n = etat(jeu).optInt("n") + 1
        etat(jeu).put("n", n)
        val nomFichier = ".bestiole_${e.id}_$n"
        val retour = "../".repeat(zone.count { it == '/' } + 1) + "nid/"
        val eclat = if (shiny) "\n✨ Elle brille étrangement… une bestiole shiny ?!\n" else ""
        File(dossier, nomFichier).writeText(
            "#%03d ${e.nom} sauvage se cache ici ! (${e.rarete}, famille ${e.famille})\n".format(e.numero) +
                "« ${e.description} »$eclat\n" +
                "Pour la capturer, ramène-la dans le nid de ${jeu.nom} :\n" +
                "   ${Regles.piege("mv $nomFichier $retour")}\n\n" +
                "(Tape la commande toi-même : un copier-coller la ferait fuir !)\n")
        s.put(JSONObject().put("f", "$zone/$nomFichier").put("e", e.nom).put("zone", zone).put("shiny", shiny))
        jeu.log("🐾 Quelque chose bouge dans ${Bestiaire.lieu(zone)}…")
        jeu.dire("Je sens une présence dans ${Bestiaire.lieu(zone)} ($zone) ! Les bestioles se cachent : essaie ${Regles.piege("ls -a")}", 15)
    }

    /** Captures (bestiole déposée dans le nid) et fuites (fichier effacé). Renvoie un message ou null. */
    fun verifier(jeu: Jeu): String? {
        if (!debloquee(jeu)) return null
        val e = etat(jeu)
        if (!e.optBoolean("ouverte")) {
            e.put("ouverte", true)
            jeu.log("🌲 Exploration débloquée !")
            spawn(jeu)
            return "🌲 L'exploration est ouverte : des bestioles se cachent dans le terrain de jeu !"
        }
        val s = sauvages(jeu)
        val nid = File(jeu.terrain, "nid")
        var message: String? = null
        val garder = JSONArray()
        for (i in 0 until s.length()) {
            val b = s.getJSONObject(i)
            val nomFichier = b.getString("f").substringAfterLast('/')
            val dansNid = File(nid, nomFichier)
            val esp = Bestiaire.espece(b.getString("e"))
            when {
                dansNid.exists() -> {
                    dansNid.delete()
                    if (esp == null) continue
                    val shiny = b.optBoolean("shiny")
                    val ind = Bestiaire.individu(esp, shiny, b.optString("zone"))
                    captures(jeu).put(ind)
                    val c = collection(jeu)
                    c.put(esp.nom, c.optInt(esp.nom) + 1)
                    val titre = esp.nom + if (shiny) " ✨ SHINY" else ""
                    jeu.log("🎯 $titre capturé ! (${esp.rarete})")
                    jeu.dire("Bienvenue au nid, ${esp.nom}${if (shiny) " ✨" else ""} ! Signe particulier : ${ind.getString("marque")}.", 14)
                    jeu.stats[esp.stat] = (jeu.stats[esp.stat] ?: 0) + 2
                    jeu.ajouterXp((Bestiaire.XP[esp.rarete] ?: 15) * if (shiny) 3 else 1)
                    message = "🎯 ${carte(ind)}\nElle rejoint ta collection (tape « collection »)."
                }
                File(jeu.terrain, b.getString("f")).exists() -> garder.put(b)
                else -> {
                    val ailleurs = jeu.terrain.walkTopDown().maxDepth(6).firstOrNull { it.name == nomFichier }
                    if (ailleurs != null) {
                        b.put("f", ailleurs.relativeTo(jeu.terrain).path)
                        garder.put(b)
                    } else {
                        val nom = b.getString("e")
                        jeu.log("💨 $nom s'est enfuie (fichier effacé ?)")
                        message = "💨 $nom a disparu… un rm de trop ?"
                    }
                }
            }
        }
        e.put("sauvages", garder)
        return message
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
        val vues = Bestiaire.especes.filter { coll.optInt(it.nom) > 0 }
        val caps = captures(jeu)
        val sb = StringBuilder("🐾 Collection de ${jeu.nom}\n")
        sb.append("Espèces découvertes : ${vues.size}/150\n")
        for (r in listOf("commune", "peu commune", "rare", "légendaire")) {
            val tot = Bestiaire.especes.count { it.rarete == r }
            sb.append("   $r : ${vues.count { it.rarete == r }}/$tot\n")
        }
        val shinies = (0 until caps.length()).count { caps.getJSONObject(it).optBoolean("shiny") }
        sb.append("Captures : ${caps.length()}" + (if (shinies > 0) " · dont §$shinies shiny§" else "") + "\n")
        if (caps.length() > 0) {
            sb.append("\nTes dernières captures :\n")
            for (i in caps.length() - 1 downTo maxOf(0, caps.length() - 5)) sb.append(carte(caps.getJSONObject(i))).append("\n\n")
        }
        if (!debloquee(jeu)) {
            sb.append("L'exploration s'ouvre avec la leçon « Construire mon nid ».")
        } else {
            val s = sauvages(jeu)
            val zones = (0 until s.length()).map { Bestiaire.lieu(s.getJSONObject(it).getString("zone")) }.distinct()
            sb.append("Présences signalées : " + (if (zones.isEmpty()) "aucune pour l'instant" else zones.joinToString(", ")))
            sb.append("\nFiche d'une espèce : bestiaire <nom> · les 150 : site bestiaire")
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
        val e = Bestiaire.espece(nom) ?: return "Aucune espèce ne s'appelle « $nom ». Les 150 sont sur le site : site bestiaire"
        val connue = coll.optInt(e.nom) > 0
        val entete = "#%03d ".format(e.numero) + (if (!connue) "???" else if (e.rarete == "légendaire") "§${e.nom}§" else e.nom) +
            " · ${e.rarete} · ${e.icone} ${e.famille}"
        if (!connue) {
            return "$entete\nTu ne l'as pas encore capturée.\nHabitat : ${Bestiaire.lieu(e.zone)} (${e.zone})\n" +
                "Elle se montre ${e.frequence}, attirée par la commande « ${e.attireePar} »."
        }
        return "¤${e.id}¤ $entete\n${e.description}\n${e.comportement}\n" +
            "Capacité : ${e.capacite} · stat favorite : ${e.stat}\n" +
            "Taille ~${e.tailleCm} cm · poids ~${e.poidsKo} Ko\n" +
            e.stats.entries.joinToString("  ") { "${it.key} ${it.value}" } + "\n" +
            "Habitat : ${Bestiaire.lieu(e.zone)} · attirée par « ${e.attireePar} »\nTu en as capturé ${coll.optInt(e.nom)}."
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
