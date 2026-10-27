package fr.terminagotchi

/**
 * « Dans un vrai terminal… » (G-10, portage de pc/tg/vrai.py) : à chaque étape, à côté des explications pour l'enfant
 * et pour les grands, une ligne qui dit si la commande marche pareil dans un vrai terminal d'ordinateur (Linux,
 * macOS), ou ce qu'il faut y taper à la place. Clés « vrai.* », communes avec le PC.
 */
object Vrai {
    /** la commande à taper sur macOS quand celle de Linux n'y est pas */
    private val MAC = listOf(Regex("^free\\b") to "top -l 1 | head -n 10", Regex("^ip\\b") to "ifconfig",
        Regex("/etc/hostname") to "hostname")
    /** pas installés sur tous les ordinateurs */
    private val ABSENTS = setOf("tree", "nslookup", "traceroute", "dig", "tracepath")
    /** propres au téléphone ou au jeu : pas de « vrai terminal » d'ordinateur */
    private val TELEPHONE = listOf("termux-", "am ", "pm ", "ouvre", "web ", "miam")

    fun ligne(cmd: String?): String? {
        val c = cmd?.trim() ?: return null
        if (c.isEmpty() || TELEPHONE.any { c.startsWith(it) }) return null
        val premier = c.split(Regex("\\s+"))[0]
        if (premier in ABSENTS) return t("vrai.absent", "cmd" to premier)
        MAC.firstOrNull { it.first.containsMatchIn(c) }?.let { return t("vrai.mac", "mac" to it.second) }
        return t("vrai.pareil", "cmd" to c)
    }
}
