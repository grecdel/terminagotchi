package fr.terminagotchi

import java.io.File
import java.util.concurrent.TimeUnit

/**
 * Un vrai shell Android (/system/bin/sh), avec « cd » géré par l'appli, dans le Terminaworld simulé (Racine.kt) :
 * `/` est la Racine (lecture seule), ~ = /home/explorateur est le dossier de l'appli, les chemins tapés et la sortie
 * sont traduits, et une commande qui écrirait dans un lieu du système est refusée (expliqué) sans être lancée.
 */
class Shell(private val home: File) {
    var dossier: File = home
    /** le journal du jeu, recopié dans les archives (/var/log/terminaworld.log) quand on va les lire */
    var journal: () -> List<String> = { emptyList() }

    companion object {
        /** le shell du téléphone (sous la JVM des tests : celui de l'ordinateur) */
        val SH: String = if (File("/system/bin/sh").exists()) "/system/bin/sh" else "/bin/sh"
    }

    init {
        Racine.preparer(home)
    }

    /** Le dossier courant pour l'invite : ~/… dans le camp de base, sinon le chemin du Terminaworld (/etc…). */
    fun chemin(): String {
        val v = virtuel()
        return if (Racine.dansCamp(v)) "~" + v.removePrefix(Racine.HOME) else v
    }

    /** Le dossier courant dans le Terminaworld (ce que montre `pwd`) : /home/explorateur/terrain_terminagotchi… */
    fun virtuel(): String = Racine.virtuel(home, dossier.path)

    fun executer(ligne: String): String {
        val mots = ligne.trim().split(Regex("\\s+"))
        if (mots.firstOrNull() == "cd") {
            val arg = mots.drop(1).joinToString(" ").trim('\'', '"')
            val v = Racine.resoudre(virtuel(), Racine.versVirtuel(home, arg))
            val cible = Racine.reel(home, v).let { f -> try { f.canonicalFile } catch (e: Exception) { f } }
            return if (cible.isDirectory) {
                dossier = cible
                ""
            } else {
                t("mini.cd_introuvable", "cible" to arg)
            }
        }
        if (mots.size == 1 && mots[0] == "pwd") return virtuel()
        if (!dossier.isDirectory) dossier = home
        Racine.refus(home, dossier, ligne)?.let { return it }
        val vraie = Racine.traduire(home, dossier, ligne)
        if ("log" in ligne || virtuel().startsWith("/var")) Racine.archiver(home, journal())
        return try {
            val pb = ProcessBuilder(SH, "-c",
                // ~/.tgrc est chargé avant chaque commande : on peut y créer ses propres commandes
                "[ -f \"\$HOME/.tgrc\" ] && . \"\$HOME/.tgrc\" >/dev/null 2>&1\n" + vraie)
                .directory(dossier)
                .redirectErrorStream(true)
            pb.environment()["HOME"] = home.absolutePath
            val p = pb.start()
            p.outputStream.close()
            val sb = StringBuilder()
            val lecteur = Thread {
                try {
                    p.inputStream.bufferedReader().use { r ->
                        val buf = CharArray(4096)
                        while (true) {
                            val n = r.read(buf)
                            if (n < 0) break
                            synchronized(sb) { if (sb.length < 20000) sb.append(buf, 0, n) }
                        }
                    }
                } catch (e: Exception) {
                    // flux fermé : rien à faire
                }
            }
            lecteur.start()
            val fini = p.waitFor(20, TimeUnit.SECONDS)
            if (!fini) p.destroy()
            lecteur.join(1000)
            val out = Racine.sortie(home, synchronized(sb) { sb.toString() }.trimEnd())
            if (fini) out else out + "\n" + t("shell.arrete")
        } catch (e: Exception) {
            t("shell.erreur", "msg" to e.message)
        }
    }
}
