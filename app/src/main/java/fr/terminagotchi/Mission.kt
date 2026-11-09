package fr.terminagotchi

/**
 * La ligne 🎯 « ce que je dois taper maintenant » (allègement du 9 novembre, variante B « terminal + mission »).
 *
 * Une seule ligne, juste au-dessus de la ligne de saisie. Le détail (le texte de la leçon, « Pour les grands »,
 * « Dans un vrai terminal », les options expliquées…) reste derrière le + (Jeu.texteLecon).
 *
 * Même ordre que pc/tg/mission.py (vecteurs communs donnees/mission/vecteurs.json, tests/jvm/Mission.kt) : le défi
 * éclair, le terrain effacé, la leçon (ou le niveau qu'il manque), le bandeau de l'histoire, la quête suivie.
 */
object Mission {
    /** La ligne (texte avec les commandes entre `…`) d'une mission. Pure : testée par les vecteurs communs. */
    fun formater(genre: String, v: Map<String, Any?>): String = when (genre) {
        "defi" -> if (v["calme"] == true) t("conf.defi", "cmd" to v["cmd"]) else t("app.defi", "cmd" to v["cmd"], "s" to v["s"])
        "terrain" -> t("app.terrain.titre") + " · " + t("mis.tape", "cmd" to "`${v["cmd"]}`")
        "lecon" -> {
            val cmd = v["cmd"].toString()
            "🎯 ${v["titre"]} (${v["k"]}/${v["n"]}) · " + (if (cmd.startsWith("🧩")) cmd else t("mis.tape", "cmd" to cmd))
        }
        "niveau" -> "🎯 " + t("mis.niveau", "n" to v["n"], "xp" to v["xp"])
        "bandeau" -> "🗺 " + v["titre"]
        "quete" -> v["ligne"].toString()
        else -> ""
    }

    /** (genre, valeurs) de la mission du moment, ou null (rien de précis à taper ; l'œuf a sa propre liste). */
    fun choisir(jeu: Jeu): Pair<String, Map<String, Any?>>? {
        if (!jeu.existe) return null
        Defis.actif(jeu)?.let { return "defi" to mapOf("cmd" to Regles.piege(it), "s" to Defis.resteSecondes(jeu), "calme" to Confort.calme(jeu)) }
        Terrain.perdu(jeu)?.let { return "terrain" to mapOf("cmd" to Regles.piege(it)) }
        val c = Histoire.leconCourante(jeu)
        if (c != null) {
            if (jeu.niveau < c.niveau) return "niveau" to mapOf("n" to c.niveau, "xp" to maxOf(0, 10 * (c.niveau - 1) * (c.niveau - 1) - jeu.xp))
            val e = c.etapes[jeu.etape]
            return "lecon" to mapOf("titre" to c.titre, "k" to jeu.etape + 1, "n" to c.etapes.size, "cmd" to Verif.commandeMontree(jeu, e))
        }
        Histoire.bandeau(jeu)?.let { return "bandeau" to mapOf("titre" to it.first) }
        if (Intro.ouvert(jeu, "quetes")) Quetes.ligneSuivie(jeu)?.let { return "quete" to mapOf("ligne" to it) }
        return null
    }

    /** La ligne 🎯 du moment, ou null. */
    fun ligne(jeu: Jeu): String? = try {
        choisir(jeu)?.let { (g, v) -> formater(g, v) }?.ifEmpty { null }
    } catch (e: Exception) { null }

    /** Tout ce qui est derrière le + : la leçon complète, et le terrain effacé ou le défi s'il y en a. */
    fun detail(jeu: Jeu): String {
        val defi = Defis.actif(jeu)?.let {
            if (Confort.calme(jeu)) t("conf.defi", "cmd" to Regles.piege(it)) else t("app.defi", "cmd" to Regles.piege(it), "s" to Defis.resteSecondes(jeu))
        }
        return listOfNotNull(defi, Terrain.bandeau(jeu), jeu.texteLecon()).joinToString("\n\n").ifEmpty { t("ui.lecon.vide") }
    }
}
