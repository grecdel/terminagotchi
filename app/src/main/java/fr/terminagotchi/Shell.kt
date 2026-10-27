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
        /** chaque ligne dans sa propre session (setsid) : tout ce qu'elle lance s'arrête avec elle (Garde.nettoyer) */
        private val DEBUT: List<String> = listOf("/system/bin/setsid", "/usr/bin/setsid", "/bin/setsid")
            .firstOrNull { File(it).canExecute() }?.let { listOf(it) } ?: emptyList()
        /** temps de calcul par processus, taille des fichiers écrits, nombre de processus (Garde) */
        private val LIMITES = "ulimit -t ${Garde.CPU_S} 2>/dev/null; ulimit -f ${Garde.FICHIER_BLOCS} 2>/dev/null; " +
            "{ ulimit -u ${Garde.PROCESSUS} || ulimit -p ${Garde.PROCESSUS}; } 2>/dev/null\n"
        /** une ligne plus longue ne passe pas (le shell du téléphone la refuserait) */
        const val LIGNE_MAX = 30000
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

    fun executer(brute: String): String {
        // $HOME, ${HOME} et ~ désignent le camp du Terminaworld (/home/explorateur), jamais le vrai dossier de l'appli
        val ligne = Racine.developper(brute)
        val mots = ligne.trim().split(Regex("\\s+"))
        if (mots.firstOrNull() == "cd") {
            val arg = mots.drop(1).joinToString(" ").trim('\'', '"')
            val v = Racine.resoudre(virtuel(), Racine.versVirtuel(home, arg))
            val cible = Racine.reel(home, v).let { f -> try { f.canonicalFile } catch (e: Exception) { f } }
            return if (cible.isDirectory && Racine.atteignable(home, cible)) {
                dossier = cible
                ""
            } else {
                t("mini.cd_introuvable", "cible" to arg)
            }
        }
        if (mots.size == 1 && mots[0] == "pwd") return virtuel()
        if (!dossier.isDirectory || !Racine.atteignable(home, dossier)) dossier = home
        if (ligne.length > LIGNE_MAX) return t("shell.trop_long", "n" to ligne.length)
        Racine.refus(home, dossier, ligne)?.let { return it }
        val vraie = Racine.traduire(home, dossier, ligne)
        if ("log" in ligne || virtuel().startsWith("/var")) Racine.archiver(home, journal())
        val avant = Garde.pids()
        Garde.photo(home)
        var sh = -1
        val sortie = try {
            val pb = ProcessBuilder(DEBUT + listOf(SH, "-c",
                // 1. le numéro du sh (pour arrêter ensuite tout ce qu'il a lancé) ; 2. les limites ;
                // 3. ~/.tgrc est chargé avant chaque commande : on peut y créer ses propres commandes
                "printf '\\001%s\\001' \$\$\n" + LIMITES +
                "[ -f \"\$HOME/.tgrc\" ] && . \"\$HOME/.tgrc\" >/dev/null 2>&1\n" + vraie))
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
            // le numéro du sh est la toute première chose écrite
            for (i in 0 until 20) { if (synchronized(sb) { sb.indexOf("\u0001", 1) } > 0) break; Thread.sleep(5) }
            var brut = synchronized(sb) { sb.toString() }
            if (brut.startsWith("\u0001")) {
                val fin = brut.indexOf('\u0001', 1)
                if (fin > 0) { sh = brut.substring(1, fin).toIntOrNull() ?: -1; brut = brut.substring(fin + 1) }
            }
            val tues = Garde.nettoyer(sh, avant)
            lecteur.join(1000)
            brut = synchronized(sb) { sb.toString() }.let { b -> val f = b.indexOf('\u0001', 1); if (b.startsWith("\u0001") && f > 0) b.substring(f + 1) else b }
            val out = Racine.sortie(home, brut.trimEnd())
            val notes = ArrayList<String>()
            if (!fini) notes.add(t("shell.arrete"))
            else if (tues > 0) {
                notes.add(t("garde.processus", "n" to tues))
                notes.add(t("grand.ligne", "texte" to t("garde.processus.adulte", "s" to Garde.CPU_S)))
            }
            (if (out.isEmpty()) "" else out + "\n") + notes.joinToString("\n")
        } catch (e: Exception) {
            Garde.nettoyer(sh, avant)
            if (e.message?.contains("E2BIG") == true || e.message?.contains("too long") == true) t("shell.trop_long", "n" to ligne.length)
            else t("shell.erreur", "msg" to e.message)
        }
        // le gardien des coulisses : tout ce qui a bougé hors du camp est remis, les liens qui mènent dehors enlevés
        val notes = ArrayList<String>()
        val repare = try { Garde.apres(home) } catch (e: Exception) { emptyList() }
        if (repare.isNotEmpty()) {
            notes.add(t("garde.repare"))
            notes.add(t("grand.ligne", "texte" to t("garde.repare.adulte", "n" to repare.size)))
        }
        val liens = try { Garde.liensDehors(home) } catch (e: Exception) { emptyList() }
        if (liens.isNotEmpty()) {
            notes.add(t("garde.lien", "liens" to liens.joinToString(", ") { Racine.virtuel(home, it).let { v -> if (Racine.dansCamp(v)) "~" + v.removePrefix(Racine.HOME) else v } }))
            notes.add(t("grand.ligne", "texte" to t("garde.lien.adulte")))
        }
        if (!home.isDirectory) home.mkdirs()                // `rm -rf ../*` : le camp lui-même revient (vide)
        if (!dossier.isDirectory || !Racine.atteignable(home, dossier)) dossier = home
        return listOf(sortie.trimEnd(), notes.joinToString("\n")).filter { it.isNotEmpty() }.joinToString("\n")
    }
}
