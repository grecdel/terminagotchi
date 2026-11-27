package fr.terminagotchi

import org.json.JSONObject
import kotlin.random.Random

/**
 * Les 6 envies de la créature (mêmes règles que pc/tg/envies.py). La faim est gérée par Jeu ;
 * les 5 autres baissent avec le temps et se comblent avec un type de commande différent :
 * 🎲 jeu · 🔎 curiosité · 🧭 exploration · 💤 sommeil · 🧼 propreté.
 */
object Envies {
    class Envie(val id: String, val icone: String, val verbe: String, val cmds: Set<String>, val minutes: Int, val exemples: String)

    val LISTE = listOf(
        Envie("jeu", "🎲", "jouer", setOf("echo", "rev", "figlet", "toilet", "cowsay", "fortune", "sl", "cmatrix", "banner",
            "yes", "lolcat", "doom", "jeu", "defi", "caresse", "danse", "parle", "joue", "devine"), 8, "echo, joue, devine…"),
        Envie("curiosite", "🔎", "apprendre", setOf("man", "help", "info", "tldr", "whatis", "apropos", "cat", "less", "more",
            "head", "tail", "grep", "find", "which", "type", "file", "stat", "wc", "lexique"), 10, "cat, grep, lexique…"),
        Envie("exploration", "🧭", "explorer", setOf("cd", "ls", "tree", "pwd", "dir", "du", "df", "carte", "plan"), 10,
            "cd, ls, tree…"),
        Envie("sommeil", "💤", "dormir", setOf("sleep"), 0, "laisse-moi tranquille un peu, ou tape « sleep 5 »"),
        Envie("proprete", "🧼", "faire le ménage", setOf("rm", "rmdir", "mv", "clear", "gzip", "zip", "tar"), 12,
            "rm, mv, clear…"),
    )
    private const val GAIN = 8.0
    private const val FATIGUE = 0.4
    private const val REPOS = 120_000L          // ms de calme pour regagner 1 point de sommeil

    private fun etat(jeu: Jeu): JSONObject {
        val m = jeu.module("envies")
        for (e in LISTE) if (!m.has(e.id)) m.put(e.id, 80.0)
        return m
    }

    fun valeur(jeu: Jeu, id: String) = etat(jeu).optDouble(id, 80.0)

    /** Le temps passe : les envies baissent, le sommeil remonte pendant le calme. */
    fun tick(jeu: Jeu, now: Long = System.currentTimeMillis()) {
        val m = etat(jeu)
        val dernier = m.optLong("t", now)
        val dt = (now - dernier).coerceAtLeast(0L)
        for (e in LISTE) if (e.minutes > 0) m.put(e.id, (m.optDouble(e.id) - dt / (60_000.0 * e.minutes)).coerceAtLeast(0.0))
        val calme = now - m.optLong("cmd", now)
        if (calme > REPOS) {
            m.put("sommeil", (m.optDouble("sommeil") + minOf(dt, calme - REPOS).toDouble() / REPOS).coerceAtMost(100.0))
        }
        m.put("t", now)
    }

    /** Une commande tapée à la main : comble les envies qui lui correspondent. Renvoie le bonus d'XP. */
    fun commande(jeu: Jeu, cmd: String, ligne: String): Int {
        val m = etat(jeu)
        m.put("cmd", System.currentTimeMillis())
        m.put("sommeil", (m.optDouble("sommeil") - FATIGUE).coerceAtLeast(0.0))
        var bonus = 0
        for (e in LISTE) {
            if (cmd !in e.cmds && !(e.id == "curiosite" && "--help" in ligne)) continue
            val gain = if (e.id == "sommeil") {
                val n = ligne.trim().split(Regex("\\s+")).getOrNull(1)?.toDoubleOrNull()?.toInt()
                if (n == null) 4.0 else 4.0 + minOf(30, n * 2)
            } else GAIN
            val avant = m.optDouble(e.id)
            m.put(e.id, (avant + gain).coerceAtMost(100.0))
            if (avant < 40) {
                bonus += 2
                jeu.log("${e.icone} merci, j'avais envie de ${e.verbe} !")
            }
        }
        return bonus
    }

    fun defiReussi(jeu: Jeu) {
        val m = etat(jeu)
        m.put("jeu", (m.optDouble("jeu") + 15).coerceAtMost(100.0))
    }

    /** Ce que la créature réclame quand une envie est basse, ou null. */
    fun phrase(jeu: Jeu): String? {
        val m = etat(jeu)
        val e = LISTE.minByOrNull { m.optDouble(it.id) } ?: return null
        if (m.optDouble(e.id) >= 30) return null
        return if (Random.nextBoolean()) "${e.icone} J'ai envie de ${e.verbe}… (${e.exemples})"
        else "${e.icone} Et si on allait ${e.verbe} ? (${e.exemples})"
    }

    /** 🎲▰▰▰▱ 🔎▰▰▱▱ … */
    fun barres(jeu: Jeu, largeur: Int = 4): String {
        val m = etat(jeu)
        return LISTE.joinToString(" ") { e ->
            val n = Math.round(largeur * m.optDouble(e.id) / 100).toInt().coerceIn(0, largeur)
            e.icone + "▰".repeat(n) + "▱".repeat(largeur - n)
        }
    }
}
