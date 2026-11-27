package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * La salle d'entraînement (mêmes règles que pc/tg/entrainement.py) : séances de 5 commandes chronométrées,
 * badges Bit → Exa par discipline, 3 galons chacun, ★ pour une séance éclair (< 3 s par commande).
 */
object Entrainement {
    private const val F = "entrainement"
    private const val TX = "$F/texte.txt"
    private const val AT = "$F/atelier"
    private const val TEXTE = "le chat dort\nle chien court\nle chat mange\nla souris danse\nle chat dort encore\n"
    private const val PAR_SEANCE = 5
    private const val ABANDON = 600_000L

    val RANGS = listOf(0 to "Bit", 20 to "Octet", 50 to "Kilo", 100 to "Méga", 180 to "Giga", 300 to "Téra", 480 to "Péta", 750 to "Exa")

    class Discipline(val nom: String, val icone: String, val cmds: List<String>, val ordre: Boolean)

    val DISCIPLINES = linkedMapOf(
        "reperer" to Discipline("Se repérer", "🧭", listOf("pwd", "ls", "ls -a", "ls -l", "cd ..", "cd ~", "whoami"), false),
        "fichiers" to Discipline("Fichiers", "📁", listOf("mkdir -p $AT", "touch $AT/a.txt", "cp $AT/a.txt $AT/b.txt",
            "mv $AT/b.txt $AT/c.txt", "rm $AT/c.txt"), true),
        "lire" to Discipline("Lire et chercher", "🔎", listOf("cat $TX", "head -n 3 $TX", "tail -n 2 $TX", "wc -l $TX",
            "grep chat $TX", "grep -c chat $TX"), false),
        "tuyaux" to Discipline("Tuyaux", "🔧", listOf("ls | wc -l", "cat $TX | sort", "sort $TX | uniq", "grep chat $TX | wc -l",
            "cat $TX | head -n 2"), false),
        "systeme" to Discipline("Système", "⚙", listOf("date", "whoami", "uptime", "df -h", "ps", "uname"), false),
    )

    private fun etat(jeu: Jeu): JSONObject {
        val m = jeu.module("entrainement")
        for (k in listOf("points", "etoiles", "records")) if (!m.has(k)) m.put(k, JSONObject())
        return m
    }

    private fun norm(l: String) = l.trim().trimEnd('/').replace(Regex("\\s+"), " ").lowercase()

    /** (rang, galon 1-3, points manquants ou null) */
    fun rang(points: Int): Triple<String, Int, Int?> {
        val i = RANGS.indices.last { points >= RANGS[it].first }
        val bas = RANGS[i].first
        val haut = RANGS.getOrNull(i + 1)?.first ?: return Triple(RANGS[i].second, 3, null)
        val galon = 1 + minOf(2, 3 * (points - bas) / (haut - bas))
        return Triple(RANGS[i].second, galon, haut - points)
    }

    fun badge(points: Int, etoiles: Int = 0): String {
        val (nom, galon, _) = rang(points)
        return "$nom ${"▮".repeat(galon)}${"▯".repeat(3 - galon)}" +
            if (etoiles > 0) " ${"★".repeat(minOf(etoiles, 5))}${if (etoiles > 5) "+" else ""}" else ""
    }

    fun active(jeu: Jeu) = etat(jeu).optJSONObject("seance") != null

    fun courante(jeu: Jeu): String? {
        val s = etat(jeu).optJSONObject("seance") ?: return null
        return s.getJSONArray("cmds").optString(s.optInt("i"))
    }

    fun commencer(jeu: Jeu, choix: String): String {
        val cle = if (choix in DISCIPLINES) choix else DISCIPLINES.keys.random()
        val d = DISCIPLINES.getValue(cle)
        val cmds = if (d.ordre) d.cmds.take(PAR_SEANCE) else d.cmds.shuffled().take(PAR_SEANCE)
        try {
            File(jeu.terrain, F).mkdirs()
            File(jeu.terrain, TX).let { if (!it.exists()) it.writeText(TEXTE) }
        } catch (e: Exception) {
            // le terrain n'existe pas encore : les commandes de fichiers échoueront, c'est tout
        }
        val now = System.currentTimeMillis()
        etat(jeu).put("seance", JSONObject().put("disc", cle).put("cmds", JSONArray(cmds)).put("i", 0)
            .put("t", now).put("temps", JSONArray()))
        jeu.dire("${d.icone} Entraînement « ${d.nom} » ! Depuis le terrain de jeu, tape « ${Regles.piege(cmds[0])} »", 15)
        return "${d.icone} Séance « ${d.nom} » : ${cmds.size} commandes à taper le plus vite possible (depuis ~/terrain_terminagotchi)."
    }

    fun arreter(jeu: Jeu): String {
        etat(jeu).remove("seance")
        return "Séance arrêtée."
    }

    /** Après chaque commande tapée : avance la séance. Renvoie un message à afficher, ou null. */
    fun verifier(jeu: Jeu, ligne: String, colle: Boolean): String? {
        val e = etat(jeu)
        val s = e.optJSONObject("seance") ?: return null
        val now = System.currentTimeMillis()
        val cmds = s.getJSONArray("cmds")
        var i = s.optInt("i")
        if (now - s.optLong("t") > ABANDON) {
            e.remove("seance")
            return "🏋 Séance abandonnée (trop longue pause)."
        }
        if (colle || Regles.estColle(ligne) || norm(ligne) != norm(cmds.getString(i))) return null
        s.getJSONArray("temps").put(Math.round((now - s.optLong("t")) / 100.0) / 10.0)
        s.put("t", now)
        i++
        s.put("i", i)
        if (i < cmds.length()) {
            jeu.dire("✔ Suivante : « ${Regles.piege(cmds.getString(i))} »", 15)
            return null
        }
        return finir(jeu, s)
    }

    private fun finir(jeu: Jeu, s: JSONObject): String {
        val e = etat(jeu)
        e.remove("seance")
        val cle = s.getString("disc")
        val d = DISCIPLINES.getValue(cle)
        val t = s.getJSONArray("temps")
        val total = Math.round((0 until t.length()).sumOf { t.getDouble(it) } * 10) / 10.0
        val moy = total / maxOf(1, t.length())
        val pts = 10 + (if (moy <= 5) 5 else 0) + (if (moy <= 3) 5 else 0)
        val p = e.getJSONObject("points")
        val avant = rang(p.optInt(cle)).let { it.first to it.second }
        p.put(cle, p.optInt(cle) + pts)
        val etoile = moy <= 3
        if (etoile) e.getJSONObject("etoiles").let { it.put(cle, it.optInt(cle) + 1) }
        val rec = e.getJSONObject("records")
        val nouveau = !rec.has(cle) || total < rec.optDouble(cle)
        if (nouveau) rec.put(cle, total)
        val apres = rang(p.optInt(cle)).let { it.first to it.second }
        var msg = "${d.icone} Séance « ${d.nom} » finie en $total s (+$pts pts)${if (etoile) " ★" else ""}${if (nouveau) " — RECORD !" else ""}"
        jeu.log(msg)
        if (apres != avant) msg += "\n🏅 Nouveau badge ${d.nom} : ${badge(p.optInt(cle), e.getJSONObject("etoiles").optInt(cle))} !"
        jeu.dire(msg, 14)
        jeu.ajouterXp(pts)
        return msg
    }

    fun ligneEcran(jeu: Jeu): String? {
        val s = etat(jeu).optJSONObject("seance") ?: return null
        val d = DISCIPLINES.getValue(s.getString("disc"))
        val cmds = s.getJSONArray("cmds")
        val i = s.optInt("i")
        return "${d.icone} ENTRAÎNEMENT ${d.nom} ${i + 1}/${cmds.length()} : tape « ${Regles.piege(cmds.getString(i))} »"
    }

    fun texte(jeu: Jeu): String {
        val e = etat(jeu)
        val sb = StringBuilder("🏋 Salle d'entraînement\n5 commandes à taper à la main, le plus vite possible.\n" +
            "Badges : ${RANGS.joinToString(" → ") { it.second }} (3 galons chacun) · ★ = séance éclair\n\n")
        for ((cle, d) in DISCIPLINES) {
            val p = e.getJSONObject("points").optInt(cle)
            val manque = rang(p).third
            val rec = e.getJSONObject("records").optDouble(cle, -1.0)
            sb.append("${d.icone} ${d.nom} : ${badge(p, e.getJSONObject("etoiles").optInt(cle))} · $p pts")
                .append(if (manque != null) " · encore $manque" else " · rang maximal !")
                .append(if (rec >= 0) " · record $rec s" else "").append("\n")
        }
        sb.append("\n").append(ligneEcran(jeu) ?: "Commencer : entrainement ${DISCIPLINES.keys.joinToString("|")} · arrêter : entrainement stop")
        return sb.toString()
    }
}
