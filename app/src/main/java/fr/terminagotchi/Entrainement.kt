package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.SecureRandom

/**
 * La salle d'entraînement (portage de pc/tg/entrainement.py : mêmes exercices, même tirage, mêmes médailles,
 * mêmes badges et titres ; la spécification complète y est). Vecteurs communs : donnees/entrainement/vecteurs.json.
 *
 *   entrainement [famille]      un exercice (alias : exercice)
 *   entrainement <réponse>      répondre à un exercice de lecture
 *   entrainement fin            ranger l'exercice
 *   badges · badges titre [n|auto] · badges records · badges grades (Bit, Octet… expliqués)
 *
 * L'exercice se passe dans ~/terrain_terminagotchi/salle_entrainement (le terrain de la partie active) ;
 * rien n'est touché ailleurs. Réussi quand le résultat est là (Tour.apresCommande → apresCommande) ou quand
 * la bonne réponse est donnée. Pas de limite de temps ni de punition ; récompense : de l'XP pour la créature.
 * Sauvegarde : module « entrainement » (cours, compteurs, familles, records, envoyer, sym, titre, hebdo, hebdo_compte).
 */
object Entrainement {
    const val BASE = 1_000_000L
    const val MAX_PAR_GRAINE = 100
    const val SALLE = "salle_entrainement"
    const val XP_BASE = 6
    const val XP_RECORD = 3
    const val MAX_ENVOI = 100
    const val COMMANDE = "entrainement"
    val XP_MEDAILLE = mapOf("bronze" to 0, "argent" to 2, "or" to 4, "diamant" to 6)
    val MEDAILLES = listOf("bronze", "argent", "or", "diamant")
    val ICONE_MEDAILLE = mapOf("bronze" to "🥉", "argent" to "🥈", "or" to "🥇", "diamant" to "💎")

    val PIECES = listOf("grotte", "foret", "lagon", "desert", "prairie", "canyon", "glacier", "marais", "clairiere", "colline",
        "plage", "jungle")
    val COINS = listOf("coffre", "terrier", "creux", "tente", "cabane", "rocher", "panier", "boite")
    val OBJETS = listOf("pomme", "balle", "cle", "lampe", "livre", "carte", "plume", "bougie", "boussole", "flute", "tambour",
        "etoile", "coquillage", "gomme", "crayon", "bille")
    val MOTS = listOf("licorne", "dragon", "fusee", "volcan", "pirate", "robot", "comete", "tortue", "cactus", "biscuit", "nuage",
        "sirene")

    val CMD: Map<String, List<String>> = mapOf(
        "cd" to listOf("cd", "set-location", "sl"), "ls" to listOf("ls", "dir", "gci", "get-childitem"),
        "pwd" to listOf("pwd", "get-location"), "mkdir" to listOf("mkdir", "md", "new-item"),
        "touch" to listOf("touch", "new-item", "ni"), "cp" to listOf("cp", "copy", "copy-item"),
        "mv" to listOf("mv", "move", "move-item"), "rm" to listOf("rm", "del", "remove-item"), "rmdir" to listOf("rmdir", "rd"),
        "cat" to listOf("cat", "type", "get-content", "gc"), "head" to listOf("head"), "tail" to listOf("tail"),
        "grep" to listOf("grep", "select-string", "sls"), "find" to listOf("find"), "echo" to listOf("echo", "write-output"),
        "wc" to listOf("wc", "measure-object"), "sh" to listOf("sh", "bash"), "chmod" to listOf("chmod"),
    )

    class Type(val famille: String, val cmds: List<String>, val syms: List<String>, val par: Int, val reponse: Boolean)

    val TYPES: Map<String, Type> = linkedMapOf(
        "exp_chemin" to Type("explorateur", listOf("cd"), listOf(), 15, false),
        "exp_cle" to Type("explorateur", listOf("cd", "ls"), listOf(), 30, false),
        "bat_pieces" to Type("batisseur", listOf("mkdir"), listOf(), 15, false),
        "bat_objets" to Type("batisseur", listOf("mkdir", "touch"), listOf(), 25, false),
        "dem_mv" to Type("demenageur", listOf("mv"), listOf(), 20, false),
        "dem_cp" to Type("demenageur", listOf("cp"), listOf(), 20, false),
        "net_rm" to Type("nettoyeur", listOf("rm"), listOf(), 20, false),
        "net_rmdir" to Type("nettoyeur", listOf("rmdir"), listOf(), 20, false),
        "net_rmr" to Type("nettoyeur", listOf("rm", "rmdir"), listOf(), 15, false),
        "lec_cat" to Type("lecteur", listOf("cat"), listOf(), 20, true),
        "lec_head" to Type("lecteur", listOf("head"), listOf(), 20, true),
        "lec_tail" to Type("lecteur", listOf("tail"), listOf(), 20, true),
        "det_grep" to Type("detective", listOf("grep"), listOf(), 25, true),
        "det_find" to Type("detective", listOf("find"), listOf(), 25, true),
        "plo_ecrit" to Type("plombier", listOf("echo"), listOf(">"), 20, false),
        "plo_ajout" to Type("plombier", listOf("echo"), listOf(">>"), 20, false),
        "plo_tuyau" to Type("plombier", listOf("grep", "wc"), listOf("|"), 30, true),
        "cui_lancer" to Type("cuisinier", listOf("sh"), listOf(), 20, true),
        "cui_ecrire" to Type("cuisinier", listOf("sh", "chmod", "echo"), listOf(">"), 40, false),
    )
    val FAMILLE_CMDS = mapOf("explorateur" to "cd ls pwd", "batisseur" to "mkdir touch", "demenageur" to "cp mv",
        "nettoyeur" to "rm rmdir", "lecteur" to "cat head tail", "detective" to "grep find", "plombier" to "| > >>",
        "cuisinier" to "sh chmod")
    const val COULEUR_APPRENTI = "#c8b8a0"
    const val COULEUR_TOUCHE = "#ff87ff"
    const val COULEUR_STAR = "#ffaf00"

    /** pour les tests : l'heure (ms) */
    @Volatile var maintenant: () -> Long = { System.currentTimeMillis() }

    // ---------------------------------------------------------------- le tirage (commun PC, appli, site)
    class Params(
        val pieces: List<String> = listOf(), val coins: List<String> = listOf(), val objets: List<String> = listOf(),
        val mots: List<String> = listOf(), val i: Int = 0, val j: Int = 0, val n: Int = 0, val objet: String = "",
        val lignes: List<Int> = listOf(), private val cles: Set<String>,
    ) {
        /** « type|clé=valeurs|… » dans l'ordre des clés (comme le PC) */
        fun empreinte(typ: String): String {
            val m = sortedMapOf<String, String>()
            if ("pieces" in cles) m["pieces"] = pieces.joinToString(",")
            if ("coins" in cles) m["coins"] = coins.joinToString(",")
            if ("objets" in cles) m["objets"] = objets.joinToString(",")
            if ("mots" in cles) m["mots"] = mots.joinToString(",")
            if ("i" in cles) m["i"] = i.toString()
            if ("j" in cles) m["j"] = j.toString()
            if ("n" in cles) m["n"] = n.toString()
            if ("objet" in cles) m["objet"] = objet
            if ("lignes" in cles) m["lignes"] = lignes.joinToString(",")
            return (listOf(typ) + m.map { "${it.key}=${it.value}" }).joinToString("|")
        }
    }

    fun choisir(h: Tirage.Hasard, liste: List<String>, n: Int): List<String> {
        val a = liste.toMutableList()
        for (i in 0 until n) {
            val j = i + h.entier(a.size - i)
            val x = a[i]; a[i] = a[j]; a[j] = x
        }
        return a.take(n)
    }

    fun generer(typ: String, valeur: String, k: Long): Params {
        val h = Tirage.Hasard(valeur, BASE + k)
        return when (typ) {
            "exp_chemin", "exp_cle", "det_find" -> {
                val p = choisir(h, PIECES, 3); val c = choisir(h, COINS, 2); val i = h.entier(3); val j = h.entier(2)
                if (typ == "det_find") Params(pieces = p, coins = c, i = i, j = j, objet = choisir(h, OBJETS, 1)[0], cles = setOf("pieces", "coins", "i", "j", "objet"))
                else Params(pieces = p, coins = c, i = i, j = j, cles = setOf("pieces", "coins", "i", "j"))
            }
            "bat_pieces" -> Params(pieces = choisir(h, PIECES, 2), cles = setOf("pieces"))
            "bat_objets" -> { val p = choisir(h, PIECES, 1); Params(pieces = p, objets = choisir(h, OBJETS, 2), cles = setOf("pieces", "objets")) }
            "dem_mv", "dem_cp" -> { val p = choisir(h, PIECES, 2); Params(pieces = p, objets = choisir(h, OBJETS, 1), cles = setOf("pieces", "objets")) }
            "net_rm" -> { val p = choisir(h, PIECES, 1); val o = choisir(h, OBJETS, 1); Params(pieces = p, objets = o, n = 2 + h.entier(3), cles = setOf("pieces", "objets", "n")) }
            "net_rmdir" -> { val p = choisir(h, PIECES, 3); Params(pieces = p, objets = choisir(h, OBJETS, 1), cles = setOf("pieces", "objets")) }
            "net_rmr" -> { val p = choisir(h, PIECES, 2); Params(pieces = p, objets = choisir(h, OBJETS, 3), cles = setOf("pieces", "objets")) }
            "lec_cat" -> { val m = choisir(h, MOTS, 1); Params(mots = m, n = 1 + h.entier(3), cles = setOf("mots", "n")) }
            "lec_head", "lec_tail" -> { val m = choisir(h, MOTS, 8); Params(mots = m, n = 2 + h.entier(3), cles = setOf("mots", "n")) }
            "det_grep" -> { val o = choisir(h, OBJETS, 5); val m = choisir(h, MOTS, 6); Params(objets = o, mots = m, i = h.entier(5), cles = setOf("objets", "mots", "i")) }
            "plo_ecrit", "cui_lancer", "cui_ecrire" -> Params(mots = choisir(h, MOTS, 1), cles = setOf("mots"))
            "plo_ajout" -> Params(mots = choisir(h, MOTS, 4), cles = setOf("mots"))
            "plo_tuyau" -> {
                val o = choisir(h, OBJETS, 4)
                val n = 8 + h.entier(5)
                val l = MutableList(n) { h.entier(4) }
                if (0 !in l) l[0] = 0
                Params(objets = o, lignes = l, cles = setOf("objets", "lignes"))
            }
            else -> throw IllegalArgumentException(typ)
        }
    }

    fun empreinte(typ: String, valeur: String, k: Long) = generer(typ, valeur, k).empreinte(typ)

    fun reponse(typ: String, p: Params): String? = when (typ) {
        "lec_cat" -> p.mots[0]
        "lec_head" -> p.mots[p.n - 1]
        "lec_tail" -> p.mots[7]
        "det_grep" -> p.objets[p.i]
        "det_find" -> p.pieces[p.i]
        "plo_tuyau" -> p.lignes.count { it == 0 }.toString()
        "cui_lancer" -> p.mots[0]
        else -> null
    }

    fun medaille(typ: String, secondes: Double): String {
        val par = TYPES.getValue(typ).par
        return when {
            secondes <= par -> "diamant"
            secondes <= 2 * par -> "or"
            secondes <= 4 * par -> "argent"
            else -> "bronze"
        }
    }

    /** La semaine ISO (UTC) : « 2026-W43 ». */
    fun semaine(ms: Long = maintenant()): String {
        val d = java.time.Instant.ofEpochMilli(ms).atZone(java.time.ZoneOffset.UTC).toLocalDate()
        return "%d-W%02d".format(d.get(java.time.temporal.IsoFields.WEEK_BASED_YEAR), d.get(java.time.temporal.IsoFields.WEEK_OF_WEEK_BASED_YEAR))
    }

    fun semainePrecedente(ms: Long = maintenant()) = semaine(ms - 7 * 86_400_000L)

    // ---------------------------------------------------------------- l'état
    fun e(jeu: Jeu): JSONObject {
        val e = jeu.module("entrainement")
        for (k in listOf("compteurs", "familles", "records", "hebdo", "hebdo_compte")) if (e.optJSONObject(k) == null) e.put(k, JSONObject())
        for (k in listOf("envoyer", "sym")) if (e.optJSONArray(k) == null) e.put(k, JSONArray())
        e.optString("titre").takeIf { it.isNotEmpty() }?.let { e.put("titre", migrerTitre(it)) }
        return e
    }

    /** Vieilles sauvegardes : le titre choisi « explorateur:argent » devient « explorateur:kilo ». */
    fun migrerTitre(x: String): String {
        val i = x.indexOf(':')
        if (i < 0) return x
        val nouveau = Badges.ANCIENS[x.substring(i + 1)] ?: return x
        return x.substring(0, i + 1) + nouveau
    }

    fun fam(e: JSONObject, f: String): JSONObject {
        val fs = e.getJSONObject("familles")
        val x = fs.optJSONObject(f) ?: JSONObject().also { fs.put(f, it) }
        for (k in listOf("n") + MEDAILLES) if (!x.has(k)) x.put(k, 0)
        return x
    }

    fun connait(jeu: Jeu, groupe: String) = CMD.getValue(groupe).any { it in jeu.vus }

    fun symboleConnu(jeu: Jeu, s: String): Boolean {
        val sym = e(jeu).getJSONArray("sym").let { a -> (0 until a.length()).map { a.optString(it) }.toSet() }
        if (s == ">" && (">" in sym || connait(jeu, "echo"))) return true
        return s in sym
    }

    fun typePossible(jeu: Jeu, typ: String): Boolean {
        val t = TYPES.getValue(typ)
        return t.cmds.all { connait(jeu, it) } && t.syms.all { symboleConnu(jeu, it) }
    }

    fun typesDe(jeu: Jeu, famille: String) = TYPES.filter { it.value.famille == famille && typePossible(jeu, it.key) }.keys.toList()

    fun famillesOuvertes(jeu: Jeu) = Badges.FAMILLES.filter { typesDe(jeu, it).isNotEmpty() }

    /** (exercices de la famille déjà réussis au moins une fois, exercices de la famille) — pour l'Exa. */
    fun typesFaits(e: JSONObject, f: String): Pair<Int, Int> {
        val tous = TYPES.filter { it.value.famille == f }.keys
        val recs = e.optJSONObject("records") ?: JSONObject()
        return tous.count { recs.has(it) } to tous.size
    }

    fun echelon(e: JSONObject, f: String): Int {
        val x = fam(e, f)
        val (a, b) = typesFaits(e, f)
        return Badges.echelonDe(x.optInt("n"), x.optInt("or") + x.optInt("diamant"), x.optInt("diamant"), a == b)
    }

    fun etoiles(e: JSONObject, f: String): Int = Badges.etoilesDe(fam(e, f).optInt("n"), echelon(e, f))

    // ---------------------------------------------------------------- la salle (seulement dans le terrain)
    fun salle(jeu: Jeu) = File(jeu.terrain, SALLE)

    private fun vider(d: File) {
        for (p in d.listFiles() ?: arrayOf()) {
            val lien = try { java.nio.file.Files.isSymbolicLink(p.toPath()) } catch (e: Exception) { true }
            if (lien || p.isFile) p.delete() else { p.setWritable(true); p.deleteRecursively() }
        }
    }

    private fun ecrire(f: File, texte: String, executable: Boolean = false) {
        f.parentFile?.mkdirs()
        f.writeText(texte)
        if (executable) f.setExecutable(true, false)
    }

    fun lettre(): List<String> = Langue.liste("ent.lettre")

    /** Vide la salle et pose ce dont l'exercice a besoin. Renvoie false si c'est impossible. */
    fun preparer(jeu: Jeu, typ: String, p: Params): Boolean {
        val terrain = jeu.terrain
        if (!terrain.isDirectory) return false
        val s = salle(jeu)
        return try {
            if (java.nio.file.Files.isSymbolicLink(s.toPath()) || (s.exists() && !s.isDirectory)) return false
            s.mkdirs()
            if (s.canonicalFile.parentFile != terrain.canonicalFile) return false
            vider(s)
            when (typ) {
                "exp_chemin", "exp_cle", "det_find" -> {
                    for (x in p.pieces) for (c in p.coins) File(s, "$x/$c").mkdirs()
                    val cible = File(s, "${p.pieces[p.i]}/${p.coins[p.j]}")
                    if (typ == "exp_cle") ecrire(File(cible, "cle.txt"), "🔑\n")
                    if (typ == "det_find") ecrire(File(cible, p.objet + ".txt"), p.objet + "\n")
                }
                "dem_mv", "dem_cp" -> {
                    ecrire(File(s, "${p.pieces[0]}/${p.objets[0]}.txt"), p.objets[0] + "\n")
                    File(s, p.pieces[1]).mkdirs()
                }
                "net_rm" -> {
                    for (i in 1..p.n) ecrire(File(s, "${p.pieces[0]}/poussiere_$i.tmp"), t("env.poussiere.contenu") + "\n")
                    ecrire(File(s, "${p.pieces[0]}/${p.objets[0]}.txt"), p.objets[0] + "\n")
                }
                "net_rmdir" -> {
                    File(s, p.pieces[0]).mkdirs(); File(s, p.pieces[1]).mkdirs()
                    ecrire(File(s, "${p.pieces[2]}/${p.objets[0]}.txt"), p.objets[0] + "\n")
                }
                "net_rmr" -> {
                    for (o in p.objets.take(2)) ecrire(File(s, "${p.pieces[0]}/$o.txt"), o + "\n")
                    ecrire(File(s, "${p.pieces[1]}/${p.objets[2]}.txt"), p.objets[2] + "\n")
                }
                "lec_cat" -> {
                    val l = lettre().toMutableList()
                    l.add(p.n.coerceAtMost(l.size), t("ent.lettre.secret", "mot" to p.mots[0]))
                    ecrire(File(s, "lettre.txt"), l.joinToString("\n") + "\n")
                }
                "lec_head", "lec_tail" -> ecrire(File(s, "liste.txt"), p.mots.joinToString("\n") + "\n")
                "det_grep" -> p.objets.forEachIndexed { i, o ->
                    val l = listOf(p.mots[1 + i]) + (if (i == p.i) listOf(p.mots[0]) else listOf())
                    ecrire(File(s, "indices/$o.txt"), l.joinToString("\n") + "\n")
                }
                "plo_ajout" -> ecrire(File(s, "liste.txt"), p.mots.take(3).joinToString("\n") + "\n")
                "plo_tuyau" -> ecrire(File(s, "courses.txt"), p.lignes.joinToString("\n") { p.objets[it] } + "\n")
                "cui_lancer" -> {
                    val m = p.mots[0]
                    val c = m.length / 2
                    ecrire(File(s, "recette.sh"), "a=${m.substring(0, c)}\nb=${m.substring(c)}\necho \"\$a\$b\"\n")
                }
            }
            true
        } catch (e: Exception) {
            false
        }
    }

    private fun txt(f: File) = try { f.readText() } catch (e: Exception) { "" }
    private fun mots(f: File) = txt(f).lines().map { it.trim().lowercase() }.filter { it.isNotEmpty() }
    private fun meme(a: File?, b: File) = a != null && try { a.canonicalFile == b.canonicalFile } catch (e: Exception) { false }

    /** « ok » si l'exercice est réussi, « oups » s'il ne peut plus l'être, sinon null. */
    fun verifier(jeu: Jeu, typ: String, p: Params, cwd: File?): String? {
        val s = salle(jeu)
        fun f(x: String) = File(s, x)
        return when (typ) {
            "exp_chemin", "exp_cle" -> if (meme(cwd, f("${p.pieces[p.i]}/${p.coins[p.j]}"))) "ok" else null
            "bat_pieces" -> if (p.pieces.all { f(it).isDirectory }) "ok" else null
            "bat_objets" -> if (p.objets.all { f("${p.pieces[0]}/$it.txt").isFile }) "ok" else null
            "dem_mv", "dem_cp" -> {
                val a = f("${p.pieces[0]}/${p.objets[0]}.txt"); val b = f("${p.pieces[1]}/${p.objets[0]}.txt")
                if (typ == "dem_mv") (if (b.isFile && !a.exists()) "ok" else null)
                else if (!a.exists() && !b.exists()) "oups" else if (a.isFile && b.isFile) "ok" else null
            }
            "net_rm" -> {
                val d = f(p.pieces[0])
                if (!File(d, p.objets[0] + ".txt").isFile) "oups"
                else if ((d.listFiles() ?: arrayOf()).none { it.name.endsWith(".tmp") }) "ok" else null
            }
            "net_rmdir" -> if (!f("${p.pieces[2]}/${p.objets[0]}.txt").isFile) "oups"
                else if (!f(p.pieces[0]).exists() && !f(p.pieces[1]).exists()) "ok" else null
            "net_rmr" -> if (!f("${p.pieces[1]}/${p.objets[2]}.txt").isFile) "oups" else if (!f(p.pieces[0]).exists()) "ok" else null
            "plo_ecrit" -> if (p.mots[0] in txt(f("note.txt")).lowercase()) "ok" else null
            "plo_ajout" -> if (mots(f("liste.txt")) == p.mots.take(4)) "ok" else null
            "cui_ecrire" -> {
                val m = f("miam.sh")
                val x = txt(m).lowercase()
                if (m.isFile && "echo" in x && p.mots[0] in x && m.canExecute()) "ok" else null
            }
            else -> null
        }
    }

    fun normaliser(r: String?): String {
        var x = (r ?: "").trim().trim('"', '\'', '«', '»', ' ').lowercase()
        for (fin in listOf(".txt", "/")) if (x.endsWith(fin)) x = x.dropLast(fin.length)
        if (x.startsWith("./")) x = x.substring(2)
        return x
    }

    fun bonneReponse(typ: String, p: Params, r: String): Boolean {
        val attendu = reponse(typ, p) ?: return false
        val x = normaliser(r)
        return when (typ) {
            "det_find" -> x.substringBefore('/') == attendu || x == "$attendu/${p.coins[p.j]}"
            "det_grep" -> x.substringAfterLast('/') == attendu
            else -> x == attendu
        }
    }

    // ---------------------------------------------------------------- textes
    private val NOS_COMMANDES = setOf(COMMANDE, "exercice", "badges")

    /** La commande en vert (et piégée contre le copier-coller) si l'enfant l'a déjà rencontrée. */
    fun vert(jeu: Jeu, cmd: String): String {
        val mot = Regles.premierMot(cmd)
        return if (mot in jeu.vus || mot in NOS_COMMANDES) "`${Regles.piege(cmd)}`" else Regles.piege(cmd)
    }

    fun idees(typ: String, p: Params): List<String> {
        val pc = p.pieces; val o = p.objets; val m = p.mots
        return when (typ) {
            "exp_chemin" -> listOf("cd ${pc[p.i]}/${p.coins[p.j]}")
            "exp_cle" -> listOf("ls", "cd ${pc[0]}")
            "bat_pieces" -> listOf("mkdir ${pc[0]} ${pc[1]}")
            "bat_objets" -> listOf("mkdir ${pc[0]}", "touch ${pc[0]}/${o[0]}.txt")
            "dem_mv" -> listOf("mv ${pc[0]}/${o[0]}.txt ${pc[1]}/")
            "dem_cp" -> listOf("cp ${pc[0]}/${o[0]}.txt ${pc[1]}/")
            "net_rm" -> listOf("rm ${pc[0]}/*.tmp")
            "net_rmdir" -> listOf("rmdir ${pc[0]} ${pc[1]}")
            "net_rmr" -> listOf("rm -r ${pc[0]}")
            "lec_cat" -> listOf("cat lettre.txt")
            "lec_head" -> listOf("head -n ${p.n} liste.txt")
            "lec_tail" -> listOf("tail -n 1 liste.txt")
            "det_grep" -> listOf("grep ${m[0]} indices/*")
            "det_find" -> listOf("find . -name ${p.objet}.txt")
            "plo_ecrit" -> listOf("echo ${m[0]} > note.txt")
            "plo_ajout" -> listOf("echo ${m[3]} >> liste.txt")
            "plo_tuyau" -> listOf("grep ${o[0]} courses.txt | wc -l")
            "cui_lancer" -> listOf("sh recette.sh")
            "cui_ecrire" -> listOf("echo 'echo ${m[0]}' > miam.sh", "chmod +x miam.sh")
            else -> listOf()
        }
    }

    fun consigne(typ: String, p: Params): String {
        val pc = p.pieces; val o = p.objets; val m = p.mots
        val v: Array<Pair<String, Any?>> = when (typ) {
            "exp_chemin" -> arrayOf("chemin" to "${pc[p.i]}/${p.coins[p.j]}")
            "bat_pieces" -> arrayOf("a" to pc[0], "b" to pc[1])
            "bat_objets" -> arrayOf("piece" to pc[0], "a" to "${o[0]}.txt", "b" to "${o[1]}.txt")
            "dem_mv", "dem_cp" -> arrayOf("objet" to "${o[0]}.txt", "de" to pc[0], "vers" to pc[1])
            "net_rm" -> arrayOf("piece" to pc[0], "objet" to "${o[0]}.txt")
            "net_rmdir" -> arrayOf("a" to pc[0], "b" to pc[1], "c" to pc[2])
            "net_rmr" -> arrayOf("a" to pc[0], "b" to pc[1])
            "lec_head" -> arrayOf("n" to p.n)
            "det_grep" -> arrayOf("mot" to m[0])
            "det_find" -> arrayOf("objet" to "${p.objet}.txt")
            "plo_ecrit", "cui_ecrire" -> arrayOf("mot" to m[0])
            "plo_ajout" -> arrayOf("mot" to m[3])
            "plo_tuyau" -> arrayOf("objet" to o[0])
            else -> arrayOf()
        }
        return t("ent.type.$typ.dit", *v)
    }

    fun nomFamille(f: String) = t("ent.famille.$f")
    fun nomEchelon(e: String) = t("ent.grade.$e")
    fun nomMedaille(m: String) = t("ent.medaille.$m")

    // ---------------------------------------------------------------- titres
    class Titre(val id: String, val texte: String, val couleur: String)

    fun titres(jeu: Jeu): List<Titre> {
        val e = e(jeu)
        val out = mutableListOf<Titre>()
        val ech = Badges.FAMILLES.associateWith { echelon(e, it) }
        if (ech.values.all { it >= 3 }) out.add(Titre("legende", t("ent.titre.legende"), "arc"))
        val h = e.optJSONObject("hebdo")
        if (h != null && h.optString("semaine") == semainePrecedente()) {
            val fs = h.optJSONArray("familles") ?: JSONArray()
            for (i in 0 until fs.length()) fs.optString(i).takeIf { it in Badges.FAMILLES }?.let {
                out.add(Titre("star:$it", t("ent.titre.star", "badge" to nomFamille(it)), COULEUR_STAR))
            }
        }
        if (ech.values.count { it >= 1 } >= 6) out.add(Titre("touche", t("ent.titre.touche"), COULEUR_TOUCHE))
        for (f in Badges.FAMILLES.sortedWith(compareBy({ -ech.getValue(it) }, { -fam(e, it).optInt("n") }, { Badges.FAMILLES.indexOf(it) }))) {
            val k = ech.getValue(f)
            if (k >= 1) {
                val en = Badges.ECHELONS[k]
                out.add(Titre("$f:$en", t("ent.titre.famille", "badge" to nomFamille(f), "echelon" to nomEchelon(en)), Badges.COULEURS.getValue(en)[2]))
            }
        }
        if (Badges.FAMILLES.any { fam(e, it).optInt("n") > 0 }) out.add(Titre("apprenti", t("ent.titre.apprenti"), COULEUR_APPRENTI))
        return out
    }

    fun titreAffiche(jeu: Jeu): Titre? {
        val tous = titres(jeu)
        val choix = e(jeu).optString("titre")
        return tous.firstOrNull { it.id == choix } ?: tous.firstOrNull()
    }

    /** « « Explorateur Kilo » » pour l'en-tête (ou "" sans titre) ; arc-en-ciel avec §…§ dans le terminal. */
    fun titreTexte(jeu: Jeu, terminal: Boolean = false): String {
        val x = titreAffiche(jeu) ?: return ""
        return if (terminal && x.couleur == "arc") "§« ${x.texte} »§" else "« ${x.texte} »"
    }

    // ---------------------------------------------------------------- commencer, réussir
    private val hasard = SecureRandom()

    private fun hexAuHasard(n: Int): String {
        val b = ByteArray(n)
        hasard.nextBytes(b)
        return b.joinToString("") { "%02x".format(it) }
    }

    private fun jour(): String = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.ROOT).format(java.util.Date(maintenant()))

    /** (identifiant, valeur, compteur) : la graine du jour si elle est là, sinon une graine locale (« »). */
    fun graine(jeu: Jeu): Triple<String, String, Long> {
        val e = e(jeu)
        val cache = Recensement.compte(jeu).optJSONObject("graines")
        val aujourdhui = jour()
        val id = cache?.keys()?.asSequence()?.firstOrNull { it.substringBefore('.') == aujourdhui }
        val valeur = id?.let { cache.optString(it) } ?: ""
        if (id != null && valeur.length >= 16) {
            val cpt = e.getJSONObject("compteurs")
            val n = cpt.optLong(id)
            if (n < MAX_PAR_GRAINE) {
                for (k in cpt.keys().asSequence().toList()) if (k.substringBefore('.') < aujourdhui) cpt.remove(k)
                cpt.put(id, n + 1)
                return Triple(id, valeur, n)
            }
        }
        return Triple("", hexAuHasard(32), 0L)
    }

    fun coursOk(e: JSONObject): Boolean {
        val c = e.optJSONObject("cours") ?: return false
        return c.optString("type") in TYPES && c.optString("v").length >= 16
    }

    fun lignesExercice(jeu: Jeu, c: JSONObject): String {
        val typ = c.getString("type")
        val p = generer(typ, c.getString("v"), c.optLong("n"))
        val ty = TYPES.getValue(typ)
        val out = mutableListOf(t("ent.debut.titre", "famille" to nomFamille(ty.famille)), consigne(typ, p),
            t("ent.depart", "cmd" to vert(jeu, "cd ~/${jeu.terrain.name}/$SALLE")))
        for (x in idees(typ, p)) out.add(t("ent.idee", "cmd" to vert(jeu, x)))
        Guide.indiceExercice(jeu, ty.famille)?.let { out.add(it) }      // le guide du bon type souffle une astuce de plus
        out.add(if (ty.reponse) t("ent.repondre", "cmd" to vert(jeu, COMMANDE)) else t("ent.verifier", "cmd" to vert(jeu, COMMANDE)))
        out.add(t("ent.chrono", "d" to ty.par, "o" to 2 * ty.par, "a" to 4 * ty.par))
        return out.joinToString("\n")
    }

    fun commencer(jeu: Jeu, famille: String? = null, typImpose: String? = null): String {
        val e = e(jeu)
        if (!jeu.terrain.isDirectory) return t("ent.pas_de_terrain")
        val ouvertes = famillesOuvertes(jeu)
        if (ouvertes.isEmpty()) return t("ent.aucune_famille", "cmds" to "cd, ls, mkdir")
        val f = when {
            typImpose != null -> TYPES.getValue(typImpose).famille
            famille == null -> ouvertes.random()
            famille !in ouvertes -> return t("ent.famille_fermee", "badge" to nomFamille(famille), "cmds" to FAMILLE_CMDS[famille])
            else -> famille
        }
        val typ = typImpose ?: typesDe(jeu, f).random()
        val (gid, valeur, n) = graine(jeu)
        val p = generer(typ, valeur, n)
        if (!preparer(jeu, typ, p)) return t("ent.salle_impossible")
        e.put("cours", JSONObject().put("type", typ).put("g", gid).put("v", valeur).put("n", n)
            .put("debut", maintenant()).put("e", p.empreinte(typ)))
        jeu.animer("parle")
        return lignesExercice(jeu, e.getJSONObject("cours"))
    }

    fun reussir(jeu: Jeu): String {
        val e = e(jeu)
        val c = e.getJSONObject("cours")
        val typ = c.getString("type")
        val f = TYPES.getValue(typ).famille
        val s = maxOf(0.1, Math.round((maintenant() - c.optLong("debut")) / 100.0) / 10.0)
        val m = medaille(typ, s)
        val avant = echelon(e, f)
        val etAvant = etoiles(e, f)
        val x = fam(e, f)
        x.put("n", x.optInt("n") + 1)
        x.put(m, x.optInt(m) + 1)
        val recs = e.getJSONObject("records")
        val rec = recs.optJSONObject(typ)
        val nouveau = rec == null || s < rec.optDouble("t", 1e9)
        if (nouveau) recs.put(typ, JSONObject().put("t", s).put("d", maintenant()).put("g", c.optString("g")).put("n", c.optLong("n")))
        val run = JSONObject().put("id", hexAuHasard(6)).put("type", typ).put("g", c.optString("g")).put("n", c.optLong("n"))
            .put("t", s).put("d", maintenant()).put("e", c.optString("e")).put("m", m)
        val env = e.getJSONArray("envoyer")
        env.put(run)
        while (env.length() > MAX_ENVOI) env.remove(0)
        e.remove("cours")
        val xp = XP_BASE + XP_MEDAILLE.getValue(m) + (if (nouveau && rec != null) XP_RECORD else 0)
        jeu.ajouterXp(xp)
        Envies.plaisir(jeu, "jeu", "defi")
        val sec = "%.1f".format(java.util.Locale.ROOT, s)
        val out = mutableListOf(t("ent.reussi", "s" to sec, "icone" to ICONE_MEDAILLE[m], "medaille" to nomMedaille(m), "xp" to xp, "nom" to jeu.nom))
        if (nouveau && rec != null) out.add(t("ent.record", "avant" to "%.1f".format(java.util.Locale.ROOT, rec.optDouble("t"))))
        Guide.bonusExercice(jeu, f, xp)?.let { out.add(it) }            // talent du guide : +25 % d'XP sur sa famille
        val apres = echelon(e, f)
        if (apres > avant) {
            val en = Badges.ECHELONS[apres]
            out.add(Badges.balise(f, en, 0) + " " + t("ent.echelon_monte", "badge" to nomFamille(f), "echelon" to nomEchelon(en), "cmd" to "`badges`"))
            jeu.log("🏅 " + t("ent.echelon_log", "badge" to nomFamille(f), "echelon" to nomEchelon(en)))
        } else if (apres == avant && etoiles(e, f) > etAvant) {
            out.add(t("ent.etoile", "badge" to nomFamille(f), "etoiles" to Badges.texteEtoiles(etoiles(e, f))))
        }
        jeu.log(t("ent.reussi_log", "s" to sec, "icone" to ICONE_MEDAILLE[m]))
        jeu.dire(out[0], 12)
        jeu.animer("victoire")
        return out.joinToString("\n")
    }

    /** Après chaque commande (Tour.apresCommande) : les symboles tapés, et l'exercice en cours. Renvoie un message ou null. */
    fun apresCommande(jeu: Jeu, ligne: String?, colle: Boolean, cwd: File?): String? {
        val e = e(jeu)
        if (ligne != null && !colle && !Regles.estColle(ligne)) {
            val sym = e.getJSONArray("sym")
            val connus = (0 until sym.length()).map { sym.optString(it) }.toMutableSet()
            for (s in listOf(">>", "|", ">")) {
                if (s in ligne && s !in connus && !(s == ">" && ">>" in ligne && ligne.count { it == '>' } == 2)) {
                    sym.put(s); connus.add(s)
                }
            }
        }
        if (!coursOk(e)) { e.remove("cours"); return null }
        val c = e.getJSONObject("cours")
        val typ = c.getString("type")
        if (TYPES.getValue(typ).reponse) return null
        val r = verifier(jeu, typ, generer(typ, c.getString("v"), c.optLong("n")), cwd)
        if (r == "ok") return reussir(jeu)
        if (r == "oups" && !c.optBoolean("oups")) {
            c.put("oups", true)
            val dit = t("ent.oups", "cmd" to "`$COMMANDE`")
            jeu.dire(dit, 12)
            return dit
        }
        return null
    }

    /** entrainement [famille | réponse | fin] */
    fun commande(jeu: Jeu, reste: String, cwd: File?): String {
        val e = e(jeu)
        if (!coursOk(e)) e.remove("cours")
        val mot = reste.trim()
        val cle = normaliser(mot)
        val fams = Badges.FAMILLES.associateBy { normaliser(nomFamille(it)) } + Badges.FAMILLES.associateBy { it }
        if (cle in setOf("fin", "stop", "range")) {
            if (!e.has("cours")) return t("ent.rien", "cmd" to vert(jeu, COMMANDE))
            e.remove("cours")
            return t("ent.range", "cmd" to vert(jeu, COMMANDE))
        }
        val c = e.optJSONObject("cours")
        if (c != null) {
            if (Regles.estColle(mot)) return t("ent.colle")
            val typ = c.getString("type")
            if (!TYPES.getValue(typ).reponse) {
                val r = verifier(jeu, typ, generer(typ, c.getString("v"), c.optLong("n")), cwd)
                if (r == "ok") return reussir(jeu)
            } else if (mot.isNotEmpty() && cle !in fams) {
                if (bonneReponse(typ, generer(typ, c.getString("v"), c.optLong("n")), mot)) return reussir(jeu)
                jeu.animer("confus")
                return t("ent.pas_tout_a_fait")
            }
            if (cle in fams) return t("ent.deja", "cmd" to vert(jeu, "$COMMANDE fin")) + "\n" + lignesExercice(jeu, c)
            return t("ent.en_cours") + "\n" + lignesExercice(jeu, c)
        }
        if (mot.isNotEmpty() && cle !in fams) {
            return t("ent.famille_inconnue", "nom" to mot, "liste" to famillesOuvertes(jeu).joinToString(", ") { nomFamille(it) }.ifEmpty { "…" })
        }
        return commencer(jeu, fams[cle])
    }

    // ---------------------------------------------------------------- badges, titres, records
    fun ecranBadges(jeu: Jeu): String {
        val e = e(jeu)
        val ouvertes = famillesOuvertes(jeu).toSet()
        val out = mutableListOf(t("ent.badges.titre") + "\n" + t("ent.badges.sous"), "")
        for (f in Badges.FAMILLES) {
            val x = fam(e, f)
            val k = echelon(e, f)
            if (f !in ouvertes && x.optInt("n") == 0) {
                out.add(Badges.balise(null, null) + "  " + t("ent.badges.cache"))
                continue
            }
            val en = if (k >= 0) Badges.ECHELONS[k] else null
            if (en == null) {
                out.add(Badges.balise(null, null) + "  " + nomFamille(f) + " · " + t("ent.badges.decouvrir") + "   " +
                    t("ent.badges.progres", "n" to x.optInt("n"), "s" to Badges.SEUILS[0], "echelon" to nomEchelon(Badges.ECHELONS[0])))
                continue
            }
            val n = etoiles(e, f)
            out.add(Badges.balise(f, en, n) + "  " + nomFamille(f) + " · " + nomEchelon(en) + " " + Badges.texteEtoiles(n) + "   " + progres(e, f))
        }
        out.add("")
        titreAffiche(jeu)?.let {
            out.add(t("ent.titre.ligne") + " " + titreTexte(jeu, terminal = true) + "   " + t("ent.titre.changer", "cmd" to "`badges titre`"))
        }
        val hc = e.optJSONObject("hebdo_compte") ?: JSONObject()
        for (f in Badges.FAMILLES) if (hc.optInt(f) > 0) out.add(t("ent.hebdo.compte", "badge" to nomFamille(f), "n" to hc.optInt(f)))
        out.add(t("ent.badges.grades", "cmd" to "`badges grades`"))
        out.add(t("ent.badges.pied", "cmd" to "`$COMMANDE`", "rec" to "`badges records`"))
        return out.joinToString("\n")
    }

    /** Le texte de progression d'un badge gagné : vers le grade suivant, ou vers l'étoile suivante au Giga. */
    fun progres(e: JSONObject, f: String): String {
        val n = fam(e, f).optInt("n")
        val k = echelon(e, f)
        if (k + 1 < Badges.ECHELONS.size) {
            val s = Badges.SEUILS[k + 1]
            return if (k + 1 == 4 && n >= s) t("ent.badges.manque_or")
            else if (n >= s && fam(e, f).optInt("diamant") < Badges.DIAMANTS[k + 1])
                t("ent.badges.manque_diamant", "n" to fam(e, f).optInt("diamant"), "s" to Badges.DIAMANTS[k + 1])
            else if (k + 1 == 7 && n >= s) typesFaits(e, f).let { t("ent.badges.manque_types", "n" to it.first, "s" to it.second) }
            else t("ent.badges.progres", "n" to n, "s" to s, "echelon" to nomEchelon(Badges.ECHELONS[k + 1]))
        }
        val s = Badges.prochaineEtoile(n, k) ?: return t("ent.badges.max")
        return t("ent.badges.etoile", "n" to n, "s" to s)
    }

    /** Les 8 grades expliqués (Bit, Octet… : des tailles d'informatique), avec leurs galons et les étoiles. */
    fun ecranGrades(): String {
        val out = mutableListOf(t("ent.grades.titre"), "")
        Badges.ECHELONS.forEachIndexed { k, en ->
            out.add(Badges.balise("explorateur", en, 0) + "  " + nomEchelon(en) + " · " + t("ent.grades.seuil", "n" to Badges.SEUILS[k]) +
                (if (k == 4) " " + t("ent.badges.manque_or") else if (Badges.DIAMANTS[k] > 0) " " + t("ent.grades.diamants", "n" to Badges.DIAMANTS[k]) else "") +
                (if (k == 7) " " + t("ent.grades.tous_types") else ""))
        }
        out.add("")
        out.add(t("ent.grades.intro"))
        for (en in Badges.ECHELONS) out.add("  " + nomEchelon(en) + " : " + t("ent.grades.$en"))
        out.add("")
        out.add(t("ent.grades.galons"))
        out.add(t("ent.grades.etoiles", "n" to Badges.ETOILES.last()[2]))
        return out.joinToString("\n")
    }

    fun ecranTitres(jeu: Jeu, choix: String?): String {
        val e = e(jeu)
        val tous = titres(jeu)
        if (!choix.isNullOrBlank()) {
            val n = choix.trim().toIntOrNull()
            return when {
                choix.trim().lowercase() in setOf("auto", "0") -> { e.remove("titre"); t("ent.titres.auto") }
                n != null && n in 1..tous.size -> { e.put("titre", tous[n - 1].id); t("ent.titres.choisi", "titre" to tous[n - 1].texte) }
                else -> t("ent.titres.numero", "n" to tous.size)
            }
        }
        if (tous.isEmpty()) return t("ent.titres.aucun", "cmd" to "`$COMMANDE`")
        val choisi = titreAffiche(jeu)
        val out = mutableListOf(t("ent.titres.liste"))
        tous.forEachIndexed { i, x ->
            val texte = if (x.couleur == "arc") "§${x.texte}§" else x.texte
            out.add("  ${if (choisi?.id == x.id) "●" else " "} ${i + 1}. $texte")
        }
        out.add(t("ent.titres.aide", "cmd" to "`badges titre 2`", "auto" to "`badges titre auto`"))
        return out.joinToString("\n")
    }

    fun ecranRecords(jeu: Jeu): String {
        val recs = e(jeu).getJSONObject("records")
        if (recs.length() == 0) return t("ent.records.aucun", "cmd" to "`$COMMANDE`")
        val out = mutableListOf(t("ent.records.titre"))
        for (f in Badges.FAMILLES) {
            val l = recs.keys().asSequence().filter { it in TYPES && TYPES.getValue(it).famille == f }.sorted().toList()
            if (l.isEmpty()) continue
            out.add(nomFamille(f))
            for (typ in l) {
                val r = recs.getJSONObject(typ)
                val tt = r.optDouble("t")
                val etat = when {
                    !r.has("v") || r.isNull("v") -> ""
                    r.optBoolean("v") -> "  " + t("ent.records.verifie")
                    else -> "  " + t("ent.records.non_verifie")
                }
                out.add("   ${ICONE_MEDAILLE[medaille(typ, tt)]} ${t("ent.type.$typ.titre")} : ${"%.1f".format(java.util.Locale.ROOT, tt)} s$etat")
            }
        }
        return out.joinToString("\n")
    }

    fun commandeBadges(jeu: Jeu, reste: String): String {
        val m = reste.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        return when (m.firstOrNull()?.lowercase()) {
            "titre", "titres" -> ecranTitres(jeu, m.getOrNull(1))
            "records", "record" -> ecranRecords(jeu)
            "grades", "grade", "echelons", "echelon", "échelons", "échelon", "aide", "etoiles", "étoiles" -> ecranGrades()
            else -> ecranBadges(jeu)
        }
    }

    // ---------------------------------------------------------------- synchro (Recensement.kt)
    fun instantane(jeu: Jeu): JSONObject {
        val e = e(jeu)
        val o = JSONObject()
        for (f in Badges.FAMILLES) o.put(f, JSONObject(fam(e, f).toString()))
        return o
    }

    /** (ce qui part au site, instantané des compteurs). base : les compteurs du site à la dernière synchro. */
    fun charge(jeu: Jeu, base: JSONObject?): Pair<JSONObject, JSONObject> {
        val e = e(jeu)
        val snap = instantane(jeu)
        val deltas = JSONObject()
        for (f in Badges.FAMILLES) {
            val x = snap.getJSONObject(f)
            val b = base?.optJSONObject(f)
            val d = JSONObject()
            for (k in x.keys()) d.put(k, maxOf(0, x.optInt(k) - (b?.optInt(k) ?: 0)))
            deltas.put(f, d)
        }
        val recs = JSONObject()
        val r = e.getJSONObject("records")
        for (typ in r.keys()) if (typ in TYPES) {
            val x = r.getJSONObject(typ)
            recs.put(typ, JSONObject().put("t", x.optDouble("t")).put("g", x.optString("g")).put("n", x.optLong("n")).put("d", x.optLong("d")))
        }
        val runs = JSONArray(e.getJSONArray("envoyer").toString())
        return JSONObject().put("deltas", deltas).put("runs", runs).put("records", recs) to snap
    }

    /** Recopie les compteurs communs, les records vérifiés, la Star de la semaine. Renvoie la nouvelle base. */
    fun appliquer(jeu: Jeu, srv: JSONObject?, snap: JSONObject, envoyes: JSONArray, extra: JSONObject?): JSONObject {
        val e = e(jeu)
        val fs = srv?.optJSONObject("familles") ?: JSONObject()
        val base = JSONObject()
        for (f in Badges.FAMILLES) {
            val x = fam(e, f)
            val sx = fs.optJSONObject(f) ?: JSONObject()
            val sn = snap.optJSONObject(f) ?: JSONObject()
            val b = JSONObject()
            for (k in x.keys().asSequence().toList()) {
                x.put(k, sx.optInt(k) + (x.optInt(k) - sn.optInt(k)))
                b.put(k, sx.optInt(k))
            }
            base.put(f, b)
        }
        val recs = e.getJSONObject("records")
        srv?.optJSONObject("records")?.let { r ->
            for (typ in r.keys()) {
                if (typ !in TYPES) continue
                val x = r.optJSONObject(typ) ?: continue
                val st = x.optDouble("t", 0.0)
                if (st <= 0) continue
                val ici = recs.optJSONObject(typ)
                if (ici == null || st < ici.optDouble("t") - 0.05) {
                    recs.put(typ, JSONObject().put("t", st).put("d", x.optLong("d")).put("g", "").put("n", 0).put("v", x.optBoolean("v")))
                } else if (Math.abs(st - ici.optDouble("t")) <= 0.05) ici.put("v", x.optBoolean("v"))
            }
        }
        val ids = (0 until envoyes.length()).map { envoyes.getJSONObject(it).optString("id") }.toSet()
        val reste = JSONArray()
        val env = e.getJSONArray("envoyer")
        for (i in 0 until env.length()) env.optJSONObject(i)?.let { if (it.optString("id") !in ids) reste.put(it) }
        e.put("envoyer", reste)
        extra?.optJSONObject("hebdo")?.let { e.put("hebdo", it) }
        extra?.optJSONObject("compte")?.let { e.put("hebdo_compte", it) }
        return base
    }
}
