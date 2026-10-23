package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Exploration : les zones sont de vrais dossiers du terrain de jeu.
 * Des bestioles s'y cachent (fichiers cachés) : on les trouve avec ls -a,
 * on les lit avec cat, et on les capture en les déplaçant dans le nid avec mv.
 */
object Explo {
    class Espece(val nom: String, val rarete: String, val couleur: Int, val desc: String)

    val ESPECES = listOf(
        Espece("Glitchou", "commune", 213, "Petit bug grésillant qui adore les fichiers temporaires."),
        Espece("Octobit", "commune", 39, "Pieuvre à 8 bits, range tout par octets."),
        Espece("Pixelard", "commune", 221, "Raconte des blagues en 16 couleurs."),
        Espece("Segfaulte", "commune", 203, "Se plante partout, mais toujours avec le sourire."),
        Espece("Kernelou", "rare", 78, "Vit au cœur du système, d'un calme absolu."),
        Espece("Daemonet", "rare", 141, "Travaille en arrière-plan sans jamais dormir."),
        Espece("Bugzilla", "rare", 160, "Énorme, mais personne n'arrive à le reproduire."),
        Espece("Cronosaure", "légendaire", 51, "N'apparaît qu'à heure fixe, réglé comme une horloge."),
        Espece("Rootkitsune", "légendaire", 208, "Renarde à neuf queues, maîtresse des droits root."),
    )
    private val ZONES = mapOf(
        "commune" to listOf("foret", "marais"),
        "rare" to listOf("grotte", "marais/bourbier"),
        "légendaire" to listOf("grotte/profondeurs/abysses"),
    )
    private val NOM_ZONE = mapOf("foret" to "la forêt", "marais" to "le marais", "grotte" to "la grotte",
        "marais/bourbier" to "le bourbier du marais", "grotte/profondeurs/abysses" to "les abysses de la grotte")
    private val XP = mapOf("commune" to 15, "rare" to 40, "légendaire" to 100)

    fun espece(nom: String) = ESPECES.firstOrNull { it.nom == nom }

    private fun etat(jeu: Jeu) = jeu.module("explo")

    private fun sauvages(jeu: Jeu): JSONArray =
        etat(jeu).optJSONArray("sauvages") ?: JSONArray().also { etat(jeu).put("sauvages", it) }

    fun collection(jeu: Jeu): JSONObject =
        etat(jeu).optJSONObject("collection") ?: JSONObject().also { etat(jeu).put("collection", it) }

    fun nbCaptures(jeu: Jeu): Int {
        val c = collection(jeu)
        return c.keys().asSequence().sumOf { c.optInt(it) }
    }

    fun debloquee(jeu: Jeu) = "Bâtisseur" in jeu.skills && File(jeu.terrain, "nid").isDirectory

    fun spawn(jeu: Jeu) {
        val s = sauvages(jeu)
        if (s.length() >= 3) return
        val tirage = (1..100).random()
        val rarete = if (tirage <= 70) "commune" else if (tirage <= 95) "rare" else "légendaire"
        val esp = ESPECES.filter { it.rarete == rarete }.random()
        val zone = ZONES.getValue(rarete).random()
        val dossier = File(jeu.terrain, zone)
        dossier.mkdirs()
        val n = etat(jeu).optInt("n") + 1
        etat(jeu).put("n", n)
        val nomFichier = ".bestiole_${esp.nom.lowercase()}_$n"
        val retour = "../".repeat(zone.count { it == '/' } + 1) + "nid/"
        File(dossier, nomFichier).writeText(
            "Un ${esp.nom} sauvage se cache ici ! (${esp.rarete})\n« ${esp.desc} »\n\n" +
                "Pour le capturer, ramène-le dans le nid de ${jeu.nom} :\n" +
                "   ${Regles.piege("mv $nomFichier $retour")}\n\n" +
                "(Tape la commande toi-même : un copier-coller le ferait fuir !)\n")
        s.put(JSONObject().put("f", "$zone/$nomFichier").put("e", esp.nom).put("zone", zone))
        jeu.log("🐾 Quelque chose bouge dans ${NOM_ZONE[zone]}…")
        jeu.dire("Je sens une présence dans ${NOM_ZONE[zone]} ($zone) ! Les bestioles se cachent : essaie ${Regles.piege("ls -a")}", 15)
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
            val nomEsp = b.getString("e")
            when {
                dansNid.exists() -> {
                    dansNid.delete()
                    val c = collection(jeu)
                    c.put(nomEsp, c.optInt(nomEsp) + 1)
                    val rarete = espece(nomEsp)?.rarete ?: "commune"
                    jeu.log("🎯 $nomEsp capturé ! ($rarete)")
                    jeu.dire("Bienvenue au nid, $nomEsp ! (tape « collection »)", 12)
                    val st = Regles.STATS.random()
                    jeu.stats[st] = (jeu.stats[st] ?: 0) + 2
                    jeu.ajouterXp(XP[rarete] ?: 15)
                    message = "🎯 $nomEsp capturé ! Il rejoint ta collection."
                }
                File(jeu.terrain, b.getString("f")).exists() -> garder.put(b)
                else -> {
                    val ailleurs = jeu.terrain.walkTopDown().maxDepth(6).firstOrNull { it.name == nomFichier }
                    if (ailleurs != null) {
                        b.put("f", ailleurs.relativeTo(jeu.terrain).path)
                        garder.put(b)
                    } else {
                        jeu.log("💨 $nomEsp s'est enfui (fichier effacé ?)")
                        message = "💨 $nomEsp a disparu… un rm de trop ?"
                    }
                }
            }
        }
        e.put("sauvages", garder)
        return message
    }

    fun texteCollection(jeu: Jeu): String {
        val c = collection(jeu)
        val sb = StringBuilder("🐾 Collection de ${jeu.nom}\n")
        for (esp in ESPECES) {
            val n = c.optInt(esp.nom)
            sb.append(if (n > 0) "● ${esp.nom} ×$n (${esp.rarete}) — ${esp.desc}\n" else "○ ??? (${esp.rarete})\n")
        }
        sb.append("\nEspèces : ${c.length()}/${ESPECES.size} · captures : ${nbCaptures(jeu)}\n")
        if (!debloquee(jeu)) {
            sb.append("L'exploration s'ouvre avec la leçon « Construire mon nid ».")
        } else {
            val s = sauvages(jeu)
            val zones = (0 until s.length()).map { NOM_ZONE[s.getJSONObject(it).getString("zone")] ?: "?" }.distinct()
            sb.append("Présences signalées : " + (if (zones.isEmpty()) "aucune pour l'instant" else zones.joinToString(", ")))
        }
        return sb.toString()
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
