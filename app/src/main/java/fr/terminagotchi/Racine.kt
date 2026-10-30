package fr.terminagotchi

import java.io.File

/**
 * Le Terminaworld = tout le système de fichiers (docs/programme.md § 2.0 bis, décision du propriétaire), SIMULÉ dans
 * le terminal du téléphone. Le vrai arbre d'Android ne ressemble pas à celui d'un ordinateur (/system, /data, pas de
 * /home) et l'appli vit dans son dossier privé : le shell de l'appli (Shell.kt) montre donc une arborescence
 * virtuelle, cohérente avec le PC :
 *
 *   /                          la Racine (lecture seule)        → files/racine/ (fabriquée par preparer)
 *   /home                      le village                       → files/racine/home/
 *   /home/explorateur = ~      ton camp de base                 → files/maison/ (le vrai dossier de l'appli)
 *   ~/terrain_terminagotchi    la zone d'aventure (le seul lieu où l'on bâtit et casse)
 *   /etc                       la salle des règles : hostname, os-release (un décor expliqué), hosts, motd
 *   /bin, /usr/bin             l'armurerie : un fichier par commande disponible sur le téléphone
 *   /tmp                       le terrain vague (vide)
 *   /var/log                   les archives : le journal du jeu (terminaworld.log)
 *   /dev                       les portails : null, zero, random, urandom (les vrais, pour lire et pour > /dev/null)
 *   /proc                      le miroir des habitants : le VRAI /proc du téléphone (lecture seule)
 *
 * Comment : les chemins tapés sont traduits (virtuel → réel) avant d'aller au vrai sh, et la sortie est traduite
 * dans l'autre sens (réel → virtuel) : `ls /`, `cat /etc/hostname`, `ls /bin | wc -l`, `find /etc` et `pwd`
 * montrent le Terminaworld. Les lieux du système sont en lecture seule : une commande qui voudrait y écrire est
 * refusée avant d'être lancée (« Permission denied », expliqué : le gardien dit non), et leurs fichiers sont de toute
 * façon protégés (r--r--r--, dossiers r-x). sudo n'existe pas.
 */
object Racine {
    const val NOM = "explorateur"
    const val HOME = "/home/$NOM"
    const val VERSION = 1

    /** les lieux du système, repères fixes sous la Racine (chemin virtuel sans le / de tête, lieu) */
    val LIEUX = listOf("bin" to "armurerie", "dev" to "portails", "etc" to "regles", "proc" to "miroir", "tmp" to "vague",
        "usr" to "armurerie", "var/log" to "archives")
    /** leurs icônes (comme pc/tg/maison.py ICONES_LIEUX) */
    val ICONES = mapOf("racine" to "🌳", "village" to "🏡", "camp" to "⛺", "zone" to "🎒", "chemin" to "🌿",
        "armurerie" to "🧰", "portails" to "🔌", "regles" to "📋", "miroir" to "🔮", "vague" to "🍂", "archives" to "📓",
        "systeme" to "📁")
    /** le carnet des lieux (lexique) : chemin, lieu */
    val CARNET = listOf("/" to "racine", "/home" to "village", "~" to "camp", "~/terrain_terminagotchi" to "zone",
        "/etc" to "regles", "/bin, /usr" to "armurerie", "/tmp" to "vague", "/var/log" to "archives", "/dev" to "portails",
        "/proc" to "miroir")
    /** l'armurerie : les outils du shell du téléphone (toybox) */
    val OUTILS = listOf("base64", "cal", "cat", "chmod", "cp", "cut", "date", "df", "du", "echo", "find", "free", "getprop",
        "grep", "head", "hostname", "id", "ifconfig", "ip", "kill", "ls", "mkdir", "mv", "nproc", "ping", "ps", "pwd", "rev",
        "rm", "rmdir", "sed", "sh", "sha256sum", "sleep", "sort", "stat", "tail", "tee", "touch", "tr", "uname", "uniq",
        "uptime", "wc", "whoami", "xargs")
    /** les vrais fichiers de périphériques que l'on peut utiliser (lire, ou jeter dans le trou noir) */
    val VRAIS = setOf("/dev/null", "/dev/zero", "/dev/random", "/dev/urandom")
    /** les commandes qui écrivent (tous leurs chemins comptent, sauf cp et ln : la destination) */
    val ECRIT = setOf("mkdir", "touch", "rm", "rmdir", "mv", "cp", "chmod", "chown", "chgrp", "ln", "tee", "truncate", "dd", "edite",
        "install", "shred", "mkfifo", "mknod", "unlink", "rename")

    fun dossier(home: File): File = File(home.parentFile ?: home, "racine")

    // ---------------------------------------------------------------- les chemins
    /** Un chemin virtuel absolu, normalisé (« . », « .. », doubles /) ; « .. » de la Racine reste la Racine. */
    fun normaliser(v: String): String {
        val pile = ArrayList<String>()
        for (m in v.split('/')) when (m) {
            "", "." -> {}
            ".." -> if (pile.isNotEmpty()) pile.removeAt(pile.size - 1)
            else -> pile.add(m)
        }
        return "/" + pile.joinToString("/")
    }

    /** Le chemin virtuel visé par un mot tapé (relatif au dossier courant virtuel, ~, ~/…, ou absolu). */
    fun resoudre(courant: String, arg: String): String = normaliser(when {
        arg.isEmpty() || arg == "~" -> HOME
        arg.startsWith("~/") -> HOME + "/" + arg.substring(2)
        arg.startsWith("/") -> arg
        else -> courant.trimEnd('/') + "/" + arg
    })

    /** Un vrai chemin du dossier de l'appli (tapé ou collé, ou donné par un test) devient son chemin du Terminaworld. */
    fun versVirtuel(home: File, arg: String): String {
        val h = home.path
        val r = dossier(home).path
        val canon = try { home.canonicalPath } catch (e: Exception) { h }
        return when {
            arg == h || arg.startsWith("$h/") || arg == r || arg.startsWith("$r/") -> virtuel(home, arg)
            arg == canon || arg.startsWith("$canon/") -> virtuel(home, h + arg.substring(canon.length))
            else -> arg
        }
    }

    private fun normalReel(p: String): String = try { java.nio.file.Paths.get(p).normalize().toString() } catch (e: Exception) { p }

    /** Réel → virtuel : files/maison → /home/explorateur, files/racine → /, /proc et /dev/null restent eux-mêmes. */
    fun virtuel(home: File, reel: String): String {
        val c = normalReel(reel)
        val h = home.path
        val r = dossier(home).path
        return when {
            c == h -> HOME
            c.startsWith("$h/") -> HOME + c.substring(h.length)
            c == r -> "/"
            c.startsWith("$r/") -> c.substring(r.length)
            else -> c
        }
    }

    /** Virtuel → réel. */
    fun reel(home: File, virt: String): File {
        val v = normaliser(virt)
        return when {
            v == HOME || v.startsWith("$HOME/") -> File(home.path + v.substring(HOME.length))
            v == "/proc" || v.startsWith("/proc/") || v in VRAIS -> File(v)
            v == "/" -> dossier(home)
            else -> File(dossier(home).path + v)
        }
    }

    /** Vrai si ce chemin virtuel est dans le camp de base (là où le shell peut écrire). */
    fun dansCamp(v: String) = v == HOME || v.startsWith("$HOME/")

    /** Le lieu du Terminaworld d'un chemin virtuel : zone, camp, village, racine, un lieu du système, ou « systeme ». */
    fun lieu(v: String): String {
        val n = normaliser(v)
        return when {
            n == "$HOME/terrain_terminagotchi" || n.startsWith("$HOME/terrain_terminagotchi/") -> "zone"
            dansCamp(n) -> "camp"
            n == "/home" -> "village"
            n == "/" -> "racine"
            else -> LIEUX.firstOrNull { (d, _) -> n == "/$d" || n.startsWith("/$d/") }?.second ?: "systeme"
        }
    }

    // ---------------------------------------------------------------- fabriquer la Racine (une fois par version et par langue)
    private fun verrouiller(f: File) {
        if (f.isDirectory) { f.listFiles()?.forEach { verrouiller(it) }; f.setWritable(false, false); f.setReadable(true, false); f.setExecutable(true, false) }
        else { f.setWritable(false, false); f.setReadable(true, false) }
    }

    /** Remet la Racine en lecture seule (après chaque commande : `chmod -R u+w` ne dure pas). */
    fun reverrouiller(home: File) {
        val r = dossier(home)
        if (r.isDirectory) try { verrouiller(r) } catch (e: Exception) {}
    }

    /** Un dossier où le shell peut se placer : le camp, la Racine simulée, ou le vrai /proc (pas /proc/self/cwd…). */
    fun atteignable(home: File, d: File): Boolean {
        val c = try { d.canonicalPath } catch (e: Exception) { return false }
        val h = try { home.canonicalPath } catch (e: Exception) { home.path }
        val r = try { dossier(home).canonicalPath } catch (e: Exception) { dossier(home).path }
        return c == h || c.startsWith("$h/") || c == r || c.startsWith("$r/") || c == "/proc" ||
            Regex("^/proc/(self|\\d+)(/.*)?$").matches(c)
    }

    /**
     * `$HOME`, `${HOME}` et `~` (en début de mot) deviennent le camp du Terminaworld (/home/explorateur) avant tout :
     * le vrai dossier de l'appli n'est jamais atteint par `$HOME/..`. Rien n'est changé entre apostrophes ('$HOME').
     */
    fun developper(ligne: String): String {
        val sb = StringBuilder()
        var i = 0
        var simple = false
        while (i < ligne.length) {
            val c = ligne[i]
            if (c == '\'' ) { simple = !simple; sb.append(c); i++; continue }
            if (!simple && c == '\\' && i + 1 < ligne.length) { sb.append(c).append(ligne[i + 1]); i += 2; continue }
            if (!simple && c == '$') {
                val m = Regex("^(\\$\\{HOME\\}|\\\$HOME(?![A-Za-z0-9_]))").find(ligne.substring(i))
                if (m != null) { sb.append(HOME); i += m.value.length; continue }
            }
            sb.append(c)
            i++
        }
        return sb.toString()
    }

    private fun deverrouiller(f: File) {
        f.setWritable(true, true)
        if (f.isDirectory) f.listFiles()?.forEach { deverrouiller(it) }
    }

    private fun ecrire(f: File, texte: String) {
        f.parentFile?.mkdirs()
        if (f.exists() && !f.canWrite()) f.setWritable(true, true)
        f.writeText(if (texte.endsWith("\n")) texte else texte + "\n")
    }

    /** Fabrique (ou refait) l'arborescence de la Racine, puis la verrouille (lecture seule). */
    fun preparer(home: File): File {
        val r = dossier(home)
        val marque = File(home.parentFile ?: home, "racine.version")
        val attendu = "$VERSION:${Langue.courante}"
        if (r.isDirectory && marque.isFile && marque.readText().trim() == attendu) return r
        try {
            if (r.exists()) deverrouiller(r)
            for (d in listOf("bin", "dev", "etc", "home/$NOM", "proc", "tmp", "usr/bin", "var/log")) File(r, d).mkdirs()
            ecrire(File(r, "etc/hostname"), "terminaworld")
            ecrire(File(r, "etc/os-release"), "NAME=\"Terminaworld\"\nID=terminaworld\nPRETTY_NAME=\"Terminaworld (Android)\"\n" +
                "# " + t("racine.osrelease"))
            ecrire(File(r, "etc/hosts"), "127.0.0.1 localhost\n::1 localhost")
            ecrire(File(r, "etc/motd"), t("racine.motd"))
            for (o in OUTILS) for (b in listOf("bin", "usr/bin")) ecrire(File(r, "$b/$o"), "#!/system/bin/sh\n# $o : /system/bin/$o (toybox)")
            for (d in listOf("null", "zero", "random", "urandom")) { val f = File(r, "dev/$d"); if (!f.exists()) f.createNewFile() }
            val log = File(r, "var/log/terminaworld.log")
            if (!log.exists()) ecrire(log, "")
            verrouiller(r)
            marque.writeText(attendu)
        } catch (e: Exception) {
            // la Racine reste comme elle est : le terminal marche quand même dans le camp de base
        }
        return r
    }

    /** Les archives : le journal du jeu recopié dans /var/log/terminaworld.log (en lecture seule). */
    fun archiver(home: File, lignes: List<String>) {
        val f = File(dossier(home), "var/log/terminaworld.log")
        val d = f.parentFile ?: return
        if (!d.isDirectory) return
        try {
            d.setWritable(true, true)
            f.setWritable(true, true)
            f.writeText(lignes.takeLast(200).joinToString("\n") + "\n")
        } catch (e: Exception) {
        } finally {
            f.setWritable(false, false); d.setWritable(false, false)
        }
    }

    // ---------------------------------------------------------------- traduire une ligne et sa sortie
    // un chemin absolu, un chemin qui commence par .., ou un chemin relatif qui remonte (./.., nid/../..)
    private val CHEMIN = Regex("(?<=^|[\\s=<>|;&(])(['\"]?)(/[^\\s;|&<>()'\"]*|\\.\\.(?:/[^\\s;|&<>()'\"]*)?|" +
        "(?:[^\\s;|&<>()'\"/=$`]+/)+\\.\\.(?=/|[\\s;|&<>()'\"]|$)(?:/[^\\s;|&<>()'\"]*)?)")
    private val SEP = Regex("\\s*(?:&&|\\|\\||;)\\s*")

    /** Les chemins tapés (absolus, ou qui remontent avec ..) traduits en vrais chemins pour le shell. */
    fun traduire(home: File, cwdReel: File, ligne: String): String {
        val courant = virtuel(home, cwdReel.path)
        return CHEMIN.replace(ligne) { m ->
            val q = m.groupValues[1]
            val mot = m.groupValues[2]
            if (versVirtuel(home, mot) != mot) return@replace m.value      // déjà un vrai chemin de l'appli
            val v = resoudre(courant, mot)
            val vrai = reel(home, v).path + if (mot.length > 1 && mot.endsWith("/")) "/" else ""
            if (mot.startsWith("/")) {
                // /bin/ls tapé comme commande : l'outil du téléphone (l'armurerie n'a que des fiches)
                val debut = m.range.first == 0 || ligne.substring(0, m.range.first).trimEnd().let { it.isEmpty() || it.last() in ";|&(" }
                val outil = Regex("^/(usr/)?bin/([A-Za-z0-9_.-]+)$").find(v)?.groupValues?.get(2)
                if (debut && q.isEmpty() && outil != null) outil else q + vrai
            } else {
                val relatif = normalReel(File(cwdReel, mot).path)
                if (relatif == normalReel(reel(home, v).path)) m.value else q + vrai
            }
        }
    }

    /** La sortie du vrai shell, avec les vrais chemins remplacés par ceux du Terminaworld. */
    fun sortie(home: File, texte: String): String {
        val r = dossier(home).path
        var s = texte.replace(home.path, HOME)
        try { s = s.replace(home.canonicalPath, HOME) } catch (e: Exception) {}
        s = s.replace(Regex(Regex.escape(r) + "(?=/)"), "").replace(r, "/")
        return s
    }

    /** Les chemins qu'une commande va écrire (mot tapé, chemin virtuel) : redirections > >>, et les commandes d'ECRIT. */
    fun cibles(courant: String, ligne: String): List<Pair<String, String>> {
        val out = mutableListOf<Pair<String, String>>()
        for (morceau in ligne.trim().split(SEP)) {
            for (m in Regex(">[>|]?\\s*(?!&)([^\\s|;&<>]+)").findAll(morceau)) {
                val x = m.groupValues[1].trim('\'', '"')
                out.add(x to resoudre(courant, x))
            }
            val premier = morceau.split("|")[0].replace(Regex("\\d?>>?\\s*[^\\s|;&<>]+"), " ")
            val mots = premier.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
            if (mots.isEmpty()) continue
            val cmd = mots[0].lowercase().substringAfterLast('/')
            // sed -i (modifie le fichier sur place) : tous ses fichiers ; sans -i, sed ne fait que lire
            val sedI = cmd == "sed" && mots.drop(1).any { it == "--in-place" || it.startsWith("--in-place=") || Regex("^-[a-zA-Z]*i.*").matches(it) }
            if (cmd !in ECRIT && !sedI) continue
            var args = mots.drop(1).filter { !it.startsWith("-") && !Regex("[0-7]{3,4}|[ugoa]*[+=-][rwxst]+").matches(it) }
            if (cmd == "dd") args = mots.drop(1).filter { it.startsWith("of=") }.map { it.removePrefix("of=") }
            if (sedI && mots.drop(1).none { it == "-e" || it.startsWith("--expression") || it == "-f" }) args = args.drop(1)
            // ln -s : seul le lien compte (sa cible peut être n'importe où : un lien qui mène dehors est enlevé après) ;
            // un lien « dur » (ln sans -s, cp -l) partage le fichier : sa source compte aussi
            val dur = (cmd == "ln" && mots.drop(1).none { it.startsWith("-") && "s" in it && !it.startsWith("--") || it == "--symbolic" }) ||
                (cmd == "cp" && mots.drop(1).any { it == "-l" || it == "--link" || Regex("^-[a-zA-Z]*l[a-zA-Z]*$").matches(it) })
            if ((cmd == "cp" || cmd == "ln") && !dur) args = args.takeLast(1)
            for (a in args) { val x = a.trim('\'', '"'); out.add(x to resoudre(courant, x)) }
        }
        return out
    }

    /** Une commande qui écrirait hors du camp de base (dans un lieu du système) : le refus expliqué, sinon null. */
    fun refus(home: File, cwdReel: File, ligne: String): String? {
        val courant = virtuel(home, cwdReel.path)
        val camp = try { home.canonicalPath } catch (e: Exception) { home.path }
        // le vrai chemin (liens suivis) d'une cible : un lien du camp vers la Racine ne permet pas d'y écrire
        fun vrai(v: String): String {
            var f: File? = reel(home, v)
            while (f != null && !f.exists() && !java.nio.file.Files.isSymbolicLink(f.toPath())) f = f.parentFile
            val c = try { f?.canonicalPath } catch (e: Exception) { null } ?: return v
            if (c == camp || c.startsWith("$camp/")) return v
            val w = virtuel(home, c)
            return if (w != c || c.startsWith("/proc") || c in VRAIS) w else "/" + c.substringAfterLast('/')   // les coulisses : jamais leur vrai chemin
        }
        val v = cibles(courant, ligne).map { (m, v) -> m to (if (versVirtuel(home, m) != m) versVirtuel(home, m) else v) }
            .map { (_, v) -> if (dansCamp(v)) vrai(v) else v }
            .firstOrNull { v -> !dansCamp(v) && v !in VRAIS } ?: return null
        val cmd = Regles.premierMot(ligne).ifEmpty { "sh" }
        return "$cmd: $v: Permission denied\n" +
            t("racine.refus", "lieu" to (if (lieu(v) == "systeme") v else t("lieu.${lieu(v)}.nom")), "cmd" to "cd ~/terrain_terminagotchi") + "\n" +
            // I7 : sur un vrai Linux, /tmp est ouvert à tous ; ici, c'est une particularité du téléphone
            t("grand.ligne", "texte" to t(if (lieu(v) == "vague") "racine.refus.adulte.tmp" else "racine.refus.adulte"))
    }
}
