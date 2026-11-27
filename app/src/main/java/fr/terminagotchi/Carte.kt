package fr.terminagotchi

import org.json.JSONArray
import java.io.File

/**
 * La carte qui pousse (même règle que pc/tg/carte.py) : chaque dossier où tu entres se dévoile ;
 * ses sous-dossiers inconnus restent dans le brouillard (░░ ???).
 */
object Carte {
    private const val PROFONDEUR = 5
    private val ICONES = mapOf(
        "nid" to "🪺", "monde" to "🌍", "citadelle" to "🏰", "crypte" to "🗝", "ondes" to "📡", "forge" to "🔨",
        "guilde" to "🛠", "ia" to "🔭", "donnees" to "📊", "atelier" to "🤖", "entrainement" to "🏋", "donjon" to "🏯",
        "carnet" to "📓", "jeu" to "🎮", "volcan" to "🌋", "sommets" to "🏔", "plaine" to "🌾", "foret" to "🌲",
        "termitiere" to "🐜", "abysses" to "🌊", "nuages" to "☁", "ruines" to "🏛", "faille" to "🌀",
        "recoin" to "🕳", "cachette" to "🕳", "sanctuaire" to "✨",
    )

    private fun vus(jeu: Jeu): JSONArray = jeu.module("carte").optJSONArray("vus") ?: JSONArray().also { jeu.module("carte").put("vus", it) }

    private fun relatif(jeu: Jeu, d: File): String? {
        val t = jeu.terrain.canonicalPath
        val c = try { d.canonicalPath } catch (e: Exception) { return null }
        if (c == t) return ""
        if (!c.startsWith("$t/")) return null
        return c.removePrefix("$t/")
    }

    /** Le joueur est dans ce dossier : il se dévoile (avec ses parents). Renvoie un message s'il y a du nouveau. */
    fun visiter(jeu: Jeu, d: File): String? {
        val r = relatif(jeu, d) ?: return null
        val v = vus(jeu)
        val connus = (0 until v.length()).map { v.getString(it) }.toMutableSet()
        jeu.module("carte").put("ici", r)
        val morceaux = if (r.isEmpty()) emptyList() else r.split("/")
        val nouveaux = mutableListOf<String>()
        for (i in 0..morceaux.size) {
            val p = morceaux.take(i).joinToString("/")
            if (connus.add(p)) {
                v.put(p)
                if (p.isNotEmpty()) nouveaux.add(p)
            }
        }
        if (nouveaux.isEmpty()) return null
        nouveaux.forEach { jeu.log("🗺 Nouveau lieu sur la carte : ${it.substringAfterLast('/')}") }
        jeu.ajouterXp(3 * nouveaux.size)
        return "🗺 Nouveau lieu sur la carte : ${nouveaux.last().substringAfterLast('/')} (tape « carte »)"
    }

    fun texte(jeu: Jeu): String {
        val t = jeu.terrain
        if (!t.isDirectory) return "La carte est vide : le terrain de jeu n'existe pas encore."
        val v = vus(jeu)
        val connus = (0 until v.length()).map { v.getString(it) }.toSet()
        val ici = jeu.module("carte").optString("ici", "?")
        val sb = StringBuilder("🗺 La carte du Terminaworld\n🌳 terrain_terminagotchi" + (if (ici == "") "  ◀ tu es ici" else "") + "\n")
        var vu = 0
        var total = 0
        fun dossiers(d: File) = (d.listFiles()?.filter { it.isDirectory && !it.name.startsWith(".") } ?: emptyList()).sortedBy { it.name }
        fun compter(d: File, prof: Int) {
            for (c in dossiers(d)) { total++; if (prof < PROFONDEUR) compter(c, prof + 1) }
        }
        fun dessiner(d: File, rel: String, prefixe: String, prof: Int) {
            val enfants = dossiers(d)
            enfants.forEachIndexed { i, c ->
                val r = if (rel.isEmpty()) c.name else "$rel/${c.name}"
                val dernier = i == enfants.size - 1
                val branche = if (dernier) "└─ " else "├─ "
                if (r in connus) {
                    vu++
                    sb.append("$prefixe$branche${ICONES[c.name] ?: "📁"} ${c.name}${if (ici == r) "  ◀ tu es ici" else ""}\n")
                    if (prof < PROFONDEUR) dessiner(c, r, prefixe + if (dernier) "   " else "│  ", prof + 1)
                } else sb.append("$prefixe$branche░░ ???\n")
            }
        }
        compter(t, 1)
        if ("" in connus) dessiner(t, "", "", 1)
        val pct = if (total > 0) 100 * vu / total else 0
        sb.append("\nCarte dévoilée : $vu/$total lieux ($pct %)\nEntre dans un lieu (cd) pour le dévoiler.")
        return sb.toString()
    }
}
