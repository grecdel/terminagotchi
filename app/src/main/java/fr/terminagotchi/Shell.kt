package fr.terminagotchi

import java.io.File
import java.util.concurrent.TimeUnit

/** Un vrai shell Android (/system/bin/sh), avec « cd » géré par l'appli. */
class Shell(private val home: File) {
    var dossier: File = home

    fun chemin(): String {
        val p = dossier.absolutePath
        val h = home.absolutePath
        return if (p.startsWith(h)) "~" + p.removePrefix(h) else p
    }

    fun executer(ligne: String): String {
        val mots = ligne.trim().split(Regex("\\s+"))
        if (mots.firstOrNull() == "cd") {
            val arg = mots.drop(1).joinToString(" ")
            val cible = when {
                arg.isEmpty() || arg == "~" || arg == "~/" -> home
                arg.startsWith("~/") -> File(home, arg.substring(2))
                arg.startsWith("/") -> File(arg)
                else -> File(dossier, arg)
            }.canonicalFile
            return if (cible.isDirectory) {
                dossier = cible
                ""
            } else {
                "cd : dossier introuvable : $arg"
            }
        }
        if (!dossier.isDirectory) dossier = home
        return try {
            val pb = ProcessBuilder("/system/bin/sh", "-c", ligne)
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
            val out = synchronized(sb) { sb.toString() }.trimEnd()
            if (fini) out else "$out\n(arrêté après 20 s : essaie par exemple ping -c 3)"
        } catch (e: Exception) {
            "Erreur : ${e.message}"
        }
    }
}
