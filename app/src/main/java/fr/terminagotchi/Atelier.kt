package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.text.Normalizer
import java.util.Locale
import java.util.concurrent.TimeUnit

/**
 * 🤖 L'Atelier (docs/programme.md § 2.16 et § 7.13 « L'embarqué et le temps réel »), portage de pc/tg/atelier.py.
 *
 * Le robot est SIMULÉ : un dossier robot/ dans le terrain (terrain_terminagotchi/robots) dont les fichiers led, moteur et
 * capteur_distance sont lus et écrits comme /sys/class/leds sur un vrai Raspberry Pi ; il vit sur une grille avec des
 * obstacles ; `atelier pas` est la physique (lire le moteur, bouger d'un cran, écrire le capteur et le journal).
 * L'appli ne touche à AUCUN matériel du robot (ni port série, ni flashage, ni GPIO) ; le téléphone, lui, est un vrai
 * robot de poche : sa lampe (une LED), son vibreur (un moteur), sa batterie (un capteur), déjà pilotés par l'appli.
 *
 * Le shell du téléphone ne connaît pas les commandes de l'appli : la boucle de l'enfant
 * `for i in $(seq 20); do sh cerveau.sh; atelier pas; done` est déroulée par l'appli (boucle()), qui lance SON cerveau.sh
 * avec le vrai shell du téléphone (comme s'il le tapait), dans le terrain, avec un délai. Pas de Ctrl+C sur le téléphone :
 * l'étape « while true » n'y est pas montrée. Vecteurs communs donnees/atelier/vecteurs.json (tests/jvm/Atelier.kt).
 */
object Atelier {
    @Volatile var chargeur: (() -> String?)? = null
    private var d: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("atelier.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun donnees(): JSONObject = d ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() }).also { d = it }
    private fun liste(o: JSONObject?, k: String): List<String> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.get(it).toString() } } ?: emptyList()
    private fun o(k: String) = donnees().optJSONObject(k) ?: JSONObject()

    // ================================================================ la spécification pure (vecteurs communs)
    class Robot(val x: Int, val y: Int, val d: String)

    fun asciiBas(texte: String?): String = Normalizer.normalize(texte ?: "", Normalizer.Form.NFKD)
        .filter { Character.getType(it) != Character.NON_SPACING_MARK.toInt() }.lowercase(Locale.ROOT).trim()

    private val ordre: String get() = o("directions").optString("ordre", "NESO")
    private fun pasDir(d: String): Pair<Int, Int> = o("directions").optJSONObject("pas")?.optJSONArray(d)?.let { it.getInt(0) to it.getInt(1) } ?: (0 to 0)
    val caseCm: Int get() = o("robot").optInt("case_cm", 10)

    /** L'arène « e » (l'entraînement) ou celle du défi n° cle. */
    fun arene(cle: String): JSONObject = if (cle == "e") o("entrainement")
        else donnees().getJSONArray("arenes").let { it.getJSONObject((cle.toIntOrNull() ?: 0) % it.length()) }
    fun grille(cle: String): List<String> = liste(arene(cle), "grille")
    fun libre(g: List<String>, x: Int, y: Int) = y in g.indices && x >= 0 && x < g[0].length && g[y][x] != '#'
    fun distanceCases(g: List<String>, x: Int, y: Int, d: String): Int {
        val (dx, dy) = pasDir(d)
        var n = 0
        while (libre(g, x + dx * (n + 1), y + dy * (n + 1))) n++
        return n
    }
    fun distanceCm(g: List<String>, x: Int, y: Int, d: String) = distanceCases(g, x, y, d) * caseCm
    fun tourner(d: String, sens: String): String = ordre[Math.floorMod(ordre.indexOf(d) + (if (sens == "droite") 1 else -1), 4)].toString()
    fun depart(cle: String): Robot = arene(cle).getJSONArray("depart").let { Robot(it.getInt(0), it.getInt(1), it.getString(2)) }

    private val SYNONYMES = mapOf("avance" to "avance", "avancer" to "avance", "forward" to "avance", "go" to "avance", "gauche" to "gauche",
        "left" to "gauche", "droite" to "droite", "right" to "droite", "stop" to "stop", "arret" to "stop", "halt" to "stop")

    /** Le contenu d'un fichier du robot : UTF-8 ou UTF-16 (avec BOM), sans espaces. */
    fun lireValeur(b: ByteArray?): String? {
        if (b == null) return null
        val s = if (b.size >= 2 && ((b[0] == 0xFF.toByte() && b[1] == 0xFE.toByte()) || (b[0] == 0xFE.toByte() && b[1] == 0xFF.toByte())))
            String(b, Charsets.UTF_16) else String(b, Charsets.UTF_8).replace("\u0000", "")
        return s.replace("﻿", "").trim()
    }
    fun moteurDe(texte: String?): String {
        val s = asciiBas(texte?.split("\n")?.get(0) ?: "")
        if (s.isEmpty()) return "stop"
        return SYNONYMES[s] ?: "?"
    }
    fun ledDe(texte: String?): String = (texte ?: "").trim().let { if (it == "0" || it == "1") it else "?" }

    /** Un pas de la physique : (robot après, événement : avance, choc, tourne, stop, inconnu). */
    fun pasRobot(cle: String, r: Robot, moteur: String): Pair<Robot, String> {
        val g = grille(cle)
        return when (moteur) {
            "avance" -> { val (dx, dy) = pasDir(r.d); if (libre(g, r.x + dx, r.y + dy)) Robot(r.x + dx, r.y + dy, r.d) to "avance" else r to "choc" }
            "gauche", "droite" -> Robot(r.x, r.y, tourner(r.d, moteur)) to "tourne"
            "stop" -> r to "stop"
            else -> r to "inconnu"
        }
    }

    fun verdict(cases: Int, chocs: Int, pas: Int): String {
        val df = o("defi")
        if (chocs > 0) return "choc"
        if (pas < df.optInt("pas", 20)) return "en_cours"
        return if (cases >= df.optInt("cases_min", 12)) "ok" else "peu"
    }

    private fun sha(s: String) = MessageDigest.getInstance("SHA-256").digest(s.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
    fun tire(graine: String, sel: String, n: Int) = (sha("$graine:$sel").substring(0, 8).toLong(16) % n).toInt()
    private fun <T> melange(graine: String, sel: String, l: List<T>): List<T> = l.toMutableList().also { PyHasard("$sel:$graine").melanger(it) }

    fun areneDefi(graine: String) = tire(graine, "arene", donnees().getJSONArray("arenes").length())
    fun porte(graine: String): String = liste(o("verite"), "portes").let { it[tire(graine, "porte", it.size)] }
    fun tableVerite(p: String): List<String> = listOf(0 to 0, 0 to 1, 1 to 0, 1 to 1).map { (a, b) -> if (if (p == "et") a == 1 && b == 1 else a == 1 || b == 1) "1" else "0" }
    fun chiffres(args: List<String>): List<String> =
        if (args.filter { it.isNotEmpty() }.all { Regex("[01,;]+").matches(it) }) args.joinToString("").filter { it == '0' || it == '1' }.map { it.toString() } else emptyList()
    fun choixCartes(graine: String): List<Triple<Int, String, String>> {
        val s = o("choix").getJSONArray("situations").let { a -> (0 until a.length()).map { a.getJSONObject(it) } }
        return melange(graine, "choix", s).take(o("choix").optInt("montrees", 3)).mapIndexed { i, x -> Triple(i + 1, x.optString("id"), x.optString("rep")) }
    }
    private val MOTS_PORTES = linkedMapOf("et" to listOf("et", "and", "y", "und", "e", "и", "与", "かつ"),
        "ou" to listOf("ou", "or", "o", "oder", "или", "或", "または"), "non" to listOf("non", "not", "no", "nicht", "nao", "не", "非", "でない"))
    fun porteDe(mot: String): String? {
        val m = asciiBas(mot)
        for ((p, mots) in MOTS_PORTES) if (m in mots || m == asciiBas(t("at.mot.$p"))) return p
        return null
    }
    fun reflexe(graine: String): Triple<Int, Int, Int> {
        val v = o("reflexe").getJSONArray("vitesses").let { it.getInt(tire(graine, "vitesse", it.length())) }
        val ms = o("reflexe").getJSONArray("temps_ms").let { it.getInt(tire(graine, "temps", it.length())) }
        return Triple(v, ms, v * ms / 1000)
    }
    fun nombres(texte: String?): List<Int> = Regex("-?\\d+").findAll(texte ?: "").map { it.value.toInt() }.toList()
    fun coordOk(texte: String, x: Int, y: Int) = nombres(texte).let { it.size == 2 && it == listOf(x, y) }

    /** (pièce, sens) de ce qu'une commande fait au robot (vue déployée), ou null. */
    fun robotDe(morceau: String?): Pair<String, String>? {
        val m = (morceau ?: "").trim()
        val rs = o("vue").optJSONArray("regles") ?: return null
        for (i in 0 until rs.length()) {
            val r = rs.getJSONObject(i)
            if (Regex(r.getString("motif")).containsMatchIn(m)) return r.getString("piece") to r.getString("sens")
        }
        return null
    }
    private val SEPARATEURS = Regex("\\|\\||&&|[|;&]")
    fun robotsDe(ligne: String?): List<Pair<String, String>> = (ligne ?: "").split(SEPARATEURS).mapNotNull { robotDe(it) }

    /** La grille en caractères (x vers la droite, y vers le bas), ▓ obstacle, · déjà visité, la flèche (* : un choc). */
    fun dessinGrille(cle: String, r: Robot, vus: Collection<Pair<Int, Int>> = emptyList(), choc: Boolean = false): List<String> {
        val g = grille(cle)
        val fl = o("directions").optJSONObject("fleches") ?: JSONObject()
        val out = mutableListOf("    " + (0 until g[0].length).joinToString(" ") { "${it % 10}" })
        for ((y, l) in g.withIndex()) {
            val cases = l.mapIndexed { x, c -> when {
                x == r.x && y == r.y -> if (choc) "*" else fl.optString(r.d)
                c == '#' -> "▓"
                (x to y) in vus -> "·"
                else -> "." } }
            out.add(" ${y % 10}  " + cases.joinToString(" "))
        }
        return out
    }

    fun cerveauMalinOk(texte: String?): Boolean {
        val s = texte ?: ""
        return Regex("\\bif\\b").containsMatchIn(s) && Regex("-(lt|le|eq|gt|ge|ne)\\b|[<>]").containsMatchIn(s) && "capteur_distance" in s &&
            Regex("\\b(droite|gauche|right|left)\\b").containsMatchIn(s) && Regex("\\b(avance|forward)\\b").containsMatchIn(s) && Regex("\\bfi\\b").containsMatchIn(s)
    }

    // ================================================================ l'état, le terrain, le carnet
    fun etat(jeu: Jeu): JSONObject {
        val c = jeu.module("atelier")
        if (c.optJSONArray("faits") == null) c.put("faits", JSONArray())
        if (c.optJSONObject("robot") == null) robotVers(c, "e", depart("e"))
        return c
    }
    private fun robotVers(c: JSONObject, cle: String, r: Robot) {
        c.put("robot", JSONObject().put("x", r.x).put("y", r.y).put("d", r.d).put("arene", cle))
    }
    fun robot(jeu: Jeu): Robot = etat(jeu).getJSONObject("robot").let { Robot(it.getInt("x"), it.getInt("y"), it.getString("d")) }
    fun cleArene(jeu: Jeu): String = etat(jeu).getJSONObject("robot").opt("arene")?.toString() ?: "e"
    private fun fait(jeu: Jeu, cle: String): Boolean {
        if (cle in liste(etat(jeu), "faits")) return true
        etat(jeu).getJSONArray("faits").put(cle)
        return false
    }

    const val CARNET = "carnet_de_l_atelier.txt"
    fun dossier(jeu: Jeu) = File(jeu.terrain, "robots")
    fun dossierRobot(jeu: Jeu) = File(dossier(jeu), "robot")
    fun noter(jeu: Jeu, etiquette: String, texte: String) { try { dossier(jeu).mkdirs(); File(dossier(jeu), CARNET).appendText("[$etiquette] $texte\n") } catch (e: Exception) { } }
    fun carnet(jeu: Jeu): String = try { File(dossier(jeu), CARNET).readText() } catch (e: Exception) { "" }
    fun dansCarnet(jeu: Jeu, etiquette: String, motCle: String = "ok") = Regex("^\\[$etiquette].*\\($motCle\\)\\s*$", RegexOption.MULTILINE).containsMatchIn(carnet(jeu))
    fun dernier(jeu: Jeu, etiquette: String): String? = carnet(jeu).lines().lastOrNull { it.startsWith("[$etiquette]") }
    fun pasDepuis(jeu: Jeu, debut: String): Int {
        val txt = carnet(jeu)
        val i = txt.lastIndexOf("[$debut]")
        if (i < 0) return 0
        return Regex("^\\[pas] ", RegexOption.MULTILINE).findAll(txt.substring(i)).count()
    }
    fun graine(jeu: Jeu) = Histoire.graine(jeu)
    fun lireRobot(jeu: Jeu, nom: String): String? = try { lireValeur(File(dossierRobot(jeu), nom).readBytes()) } catch (e: Exception) { null }
    private fun ecrireRobot(jeu: Jeu, nom: String, v: Any) = Histoire.ecrire(jeu, "robots/robot/$nom", "$v\n", finLigne = false)
    fun capteur(jeu: Jeu): Int = robot(jeu).let { distanceCm(grille(cleArene(jeu)), it.x, it.y, it.d) }

    fun cerveauExemple(): String = listOf("#!/bin/sh", "# " + t("at.cerveau.c1"), "# " + t("at.cerveau.c2"), "d=\$(cat robot/capteur_distance)",
        "echo \"" + t("at.cerveau.vois") + " \$d cm\"", "echo avance > robot/moteur", "").joinToString("\n")
    fun cerveauMalin(): String = listOf("#!/bin/sh", "# " + t("at.cerveau.c1"), "d=\$(cat robot/capteur_distance)", "if [ \"\$d\" -lt 10 ]; then",
        "  echo droite > robot/moteur", "else", "  echo avance > robot/moteur", "fi", "").joinToString("\n")

    fun meubles(jeu: Jeu): Map<String, Any> {
        etat(jeu)
        return linkedMapOf("robots/plan_de_l_atelier.txt" to t("at.meuble.plan", "nom" to jeu.nom) + "\n",
            "robots/$CARNET" to t("at.meuble.carnet") + "\n", "robots/robot/led" to "0\n", "robots/robot/moteur" to "stop\n",
            "robots/robot/capteur_distance" to "${capteur(jeu)}\n", "robots/cerveau_exemple.sh" to cerveauExemple())
    }

    fun meubler(jeu: Jeu, lid: String?) {
        if (!dossier(jeu).isDirectory || lid == null) return
        for ((rel, contenu) in meubles(jeu)) {
            val garder = rel.startsWith("robots/robot/") || rel.endsWith("plan_de_l_atelier.txt") || (rel.endsWith("cerveau_exemple.sh") && lid in setOf("at4", "at5"))
            if (garder && !File(jeu.terrain, rel).exists()) Histoire.ecrire(jeu, rel, contenu, finLigne = false)
        }
        val e = Programme.donnees().optJSONObject("etapes")?.optJSONObject("$lid.${jeu.etape}")
        if (e != null) for (mid in liste(e, "maths")) {
            if (Maths.noeud(mid) != null && !Maths.sait(jeu, mid) && !fait(jeu, "pont:$mid")) {
                jeu.dire(t("at.pont", "notion" to Maths.titre(mid), "cmd" to "maths $mid"), 16)
                break
            }
        }
    }

    // ---------------------------------------------------------------- les leçons du téléphone
    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)
    private const val LS = "^(ls|dir)\\b"
    private const val LIRE = "^(cat|less|more|head|tail)\\b"
    private const val AT = "^(tg\\s+)?atelier\\s+"
    private const val O_ = "robots"
    private fun n(lid: String, i: Any, cmd: String, re: String? = null, fs: ((Jeu) -> Boolean)? = null, ou: String? = null,
                  exploit: String? = null, toutCode: Boolean = false) =
        Etape("hist.$lid.$i.dit", cmd, "hist.$lid.$i.bravo", re?.let { r(it) }, fs, null, null, ou, exploit = exploit, toutCode = toutCode)

    val IDS = (0..7).map { "at$it" }
    private fun cerveauTexte(jeu: Jeu): String? = try { File(dossier(jeu), "cerveau.sh").readText() } catch (e: Exception) { null }

    /** Les leçons du téléphone : les mêmes paliers ; pas de Ctrl+C (pas de « while true ») ; le téléphone, robot de poche. */
    fun lecons(jeu: Jeu): Map<String, Lecon> {
        val carnetOk = { et: String -> { j: Jeu -> dansCarnet(j, et) } }
        val boucle = { m: Int -> { j: Jeu -> pasDepuis(j, "essai_debut") >= m } }
        return linkedMapOf(
            "at0" to Lecon("hist.at0.titre", null, 1, listOf(
                Etape("hist.entree.dit", "cd ~/terrain_terminagotchi/robots", "hist.entree.bravo", ici = O_, params = mapOf("piece" to O_)),
                n("at0", 1, "ls", re = LS, ou = O_),
                n("at0", 2, "cat plan_de_l_atelier.txt", re = "$LIRE.*plan_de_l_atelier", ou = O_),
            )),
            "at1" to Lecon("hist.at1.titre", null, 1, listOf(
                n("at1", 0, "ls robot", re = "$LS.*\\brobot\\b", ou = O_),
                n("at1", 1, "cat robot/led", re = "$LIRE.*robot/led\\b", ou = O_),
                n("at1", 2, "echo 1 > robot/led", fs = { j -> ledDe(lireRobot(j, "led")) == "1" }, ou = O_),
                n("at1", 3, "atelier robot", re = "${AT}robot\\s*$"),
                n("at1", 4, "echo 0 > robot/led", fs = { j -> ledDe(lireRobot(j, "led")) == "0" && dansCarnet(j, "led", "1") }, ou = O_),
                n("at1", 5, "cat robot/capteur_distance", re = "$LIRE.*robot/capteur_distance", ou = O_),
            )),
            "at2" to Lecon("hist.at2.titre", null, 1, listOf(
                n("at2", 0, "atelier grille", re = "${AT}grille\\b"),
                n("at2", 1, "echo avance > robot/moteur", fs = { j -> moteurDe(lireRobot(j, "moteur")) == "avance" }, ou = O_),
                n("at2", 2, "atelier pas", fs = { j -> dansCarnet(j, "pas", "avance") }),
                n("at2", 3, "atelier ou ?", fs = carnetOk("ou")),
                n("at2", 4, "echo droite > robot/moteur", fs = { j -> moteurDe(lireRobot(j, "moteur")) == "droite" }, ou = O_),
                n("at2", 5, "atelier pas", fs = { j -> dansCarnet(j, "pas", "tourne") }),
                n("at2", 6, "atelier cases ?", fs = carnetOk("cases")),
            )),
            "at3" to Lecon("hist.at3.titre", null, 1, listOf(
                n("at3", 0, "atelier logique", re = "${AT}logique\\b"),
                n("at3", 1, "[ 5 -lt 10 ] && echo vrai || echo faux", re = "^\\[\\s+\\S+\\s+-(lt|gt|le|ge|eq|ne)\\s+\\S+\\s+\\]\\s*$"),
                n("at3", 2, "d=\$(cat robot/capteur_distance); if [ \"\$d\" -lt 10 ]; then echo obstacle; else echo libre; fi",
                    re = "^if\\s+\\[\\s+\"?\\$\\w+\"?\\s+-(lt|le|gt|ge|eq|ne)\\s+\\d+\\s+\\]", ou = O_),
                n("at3", 3, "atelier verite", re = "${AT}v[eé]rit[eé]\\s*$"),
                n("at3", 4, "atelier verite ? ? ? ?", fs = carnetOk("verite")),
                n("at3", 5, "atelier choix", re = "${AT}choix\\s*$"),
                n("at3", 6, "atelier choix ? ? ?", fs = carnetOk("choix")),
            )),
            "at4" to Lecon("hist.at4.titre", null, 1, listOf(
                n("at4", 0, "for i in 1 2 3; do cat robot/capteur_distance; sleep 1; done", re = "^for\\s+\\w+\\s+in\\s+(\\d|\\{\\d|\\$\\(seq\\b)", ou = O_),
                n("at4", 2, "cat cerveau_exemple.sh", re = "$LIRE.*cerveau_exemple", ou = O_),
                n("at4", 3, "cp cerveau_exemple.sh cerveau.sh", fs = { j -> File(dossier(j), "cerveau.sh").isFile }, ou = O_),
                n("at4", 4, "atelier essai", fs = carnetOk("essai_debut")),
                n("at4", 5, "for i in \$(seq 10); do sh cerveau.sh; atelier pas; done", fs = boucle(o("essai").optInt("pas_min", 5)), ou = O_),
                n("at4", 6, "edite cerveau.sh", fs = { j -> cerveauMalinOk(cerveauTexte(j)) }, ou = O_),
            )),
            "at5" to Lecon("hist.at5.titre", null, 1, listOf(
                n("at5", 0, "atelier defi", fs = carnetOk("defi_debut")),
                n("at5", 1, "for i in \$(seq 20); do sh cerveau.sh; atelier pas; done", fs = carnetOk("defi"), ou = O_, exploit = "atelier.robot"),
            )),
            "at6" to Lecon("hist.at6.titre", null, 1, listOf(
                n("at6", 0, "atelier pi", re = "${AT}pi\\b"),
                n("at6", 3, "atelier gpio", re = "${AT}gpio\\b"),
                n("at6", 4, "atelier autonome", re = "${AT}autonome\\b"),
                n("at6", 5, "tail -5 robot/journal.txt", re = "$LIRE.*robot/journal\\.txt", ou = O_),
            )),
            "at7" to Lecon("hist.at7.titre", null, 1, listOf(
                n("at7", 0, "atelier embarque", re = "${AT}embarqu[eé]\\b"),
                n("at7", 2, "atelier reflexe", re = "${AT}r[eé]flexe\\s*$"),
                n("at7", 3, "atelier reflexe ?", fs = carnetOk("reflexe")),
                n("at7", 4, "atelier arduino", re = "${AT}arduino\\b"),
                n("at7", 7, "lampe on", re = "^lampe\\s+on"),
                n("at7", 8, "vibre 300", re = "^vibre\\b"),
                n("at7", 9, "batterie", re = "^batterie\\b"),
                n("at7", 6, "atelier telephone", re = "${AT}t[eé]l[eé]phone\\b"),
            )),
        )
    }

    // ---------------------------------------------------------------- l'arbre du Carrefour
    private fun monde(): JSONObject? {
        val ms = Programme.donnees().optJSONArray("mondes") ?: return null
        return (0 until ms.length()).map { ms.getJSONObject(it) }.firstOrNull { it.optString("id") == "atelier" }
    }
    private fun besoin(): Pair<List<String>, List<String>> {
        val m = monde() ?: return emptyList<String>() to emptyList()
        val tronc = Programme.donnees().optJSONObject("tronc") ?: JSONObject()
        return liste(m, "requis").flatMap { liste(tronc, it) }.distinct() to liste(m, "requis_lecons")
    }
    fun ouvert(jeu: Jeu): Boolean {
        val (chaps, lecs) = besoin()
        if (chaps.isEmpty() && lecs.isEmpty()) return false
        val f = Histoire.h(jeu).optJSONArray("faits")?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: emptyList()
        return chaps.all { Histoire.fini(jeu, it) } && lecs.all { it in f }
    }
    fun manque(jeu: Jeu): List<String> {
        val (chaps, lecs) = besoin()
        val f = Histoire.h(jeu).optJSONArray("faits")?.let { a -> (0 until a.length()).map { a.getString(it) } } ?: emptyList()
        return chaps.filter { !Histoire.fini(jeu, it) }.map { Histoire.nomChapitre(it) } +
            lecs.filter { it !in f }.map { l -> val ch = Histoire.chapitreDeLecon(l)
                Histoire.tx("hist.$l.titre") + " (" + (ch?.let { Histoire.nomChapitre(it.id) } ?: "?") + ")" }
    }
    fun annonce(jeu: Jeu): Boolean {
        val h = Histoire.h(jeu)
        val deja = h.optJSONArray("mondes_annonces") ?: JSONArray().also { h.put("mondes_annonces", it) }
        if ((0 until deja.length()).any { deja.getString(it) == "robots" } || Histoire.fini(jeu, "robots") || !ouvert(jeu)) return false
        deja.put("robots")
        jeu.log(t("at.ouvert.log"))
        jeu.dire(Histoire.dire(jeu, "at.ouvert.dit"), 18)
        return true
    }

    // ---------------------------------------------------------------- les indices et la surveillance
    private val REPONSES = mapOf("atelier ou ?" to "ou", "atelier cases ?" to "cases", "atelier verite ? ? ? ?" to "verite",
        "atelier choix ? ? ?" to "choix", "atelier reflexe ?" to "reflexe")
    private val TROU = Regex("(^|\\s)(\\?|…|<[^>]*>)(\\s|$)")
    val MATERIEL = Regex("(^|[;&|]\\s*)(sudo\\s+\\S|\\S*arduino-cli\\s+(upload|burn)|\\S*esptool(\\.py)?\\b.*\\b(write_flash|erase_flash|write-flash|erase-flash)\\b|" +
        "gpioset\\b|pinctrl\\s+set\\b|screen\\s+/dev/|minicom\\b|picocom\\b|\\S*(cat|echo|stty)\\b.*\\s/dev/tty(USB|ACM|S)\\w*)")

    fun indice(jeu: Jeu, e: Etape, tapees: List<Pair<String, String?>>): String? {
        val les = Histoire.leconCourante(jeu)?.id
        if (les !in IDS) return null
        val lignes = tapees.map { it.first.trim() }
        val cmd = e.cmd
        if (lignes.any { MATERIEL.containsMatchIn(it) }) return t("at.indice.materiel")
        if ("?" in cmd.split(" ") && lignes.any { r(AT).containsMatchIn(it) && TROU.containsMatchIn(it) }) return t("at.indice.trou")
        REPONSES[cmd]?.let { et ->
            val der = dernier(jeu, et)
            if (der != null && !der.trimEnd().endsWith("(ok)") && lignes.any { r(AT + et).containsMatchIn(it) }) return t("at.indice.$et")
        }
        if (cmd.endsWith("> robot/led") && ledDe(lireRobot(jeu, "led")) == "?") return t("at.indice.led")
        if (cmd.endsWith("> robot/moteur") && moteurDe(lireRobot(jeu, "moteur")) == "?") return t("at.indice.moteur")
        if (cmd.startsWith("echo") && lignes.any { it.startsWith("echo") && ">" !in it }) return t("at.indice.redirection")
        if (cmd.startsWith("for i in \$(seq") && lignes.any { it.startsWith("for") && "atelier" !in it }) return t("at.indice.boucle")
        if (cmd == "edite cerveau.sh" && File(dossier(jeu), "cerveau.sh").isFile && !cerveauMalinOk(cerveauTexte(jeu)))
            return t("at.indice.malin", "cmd" to "atelier aide-cerveau")
        if (cmd.startsWith("for i in \$(seq 20)")) {
            val der = dernier(jeu, "defi") ?: ""
            if (der.endsWith("(choc)")) return t("at.indice.choc")
            if (der.endsWith("(peu)")) return t("at.indice.peu")
        }
        return null
    }

    /** À chaque tour : une commande qui parlerait à du vrai matériel, ou sudo : le rappel « avec un adulte » (une fois). */
    fun surveiller(jeu: Jeu, ligne: String?) {
        if (ligne == null || !dossier(jeu).isDirectory) return
        if (MATERIEL.containsMatchIn(ligne.trim()) && !fait(jeu, "garde:materiel")) jeu.dire(t("at.garde.materiel"), 16)
    }

    // ---------------------------------------------------------------- les commandes
    val ETABLI = listOf("      ┌─┐   ┌───┐", "  💡 ─┤ ├───┤ ⚙ ├─ 🔋", "      └─┘   └─┬─┘", "   ╔══════════╧══╗  🤖", "   ║ ▓▓ ░░ ▓▓ ░░ ║",
        "  ═╩══════════════╩═")
    private fun bloc(cle: String, vararg p: Pair<String, Any?>) = t(cle, *p).split("\n").map { "  $it" }
    private fun fleche(d: String) = o("directions").optJSONObject("fleches")?.optString(d) ?: d
    private fun etatLigne(jeu: Jeu): String {
        val r = robot(jeu)
        return t("at.robot.etat", "x" to r.x, "y" to r.y, "fleche" to fleche(r.d), "led" to if (ledDe(lireRobot(jeu, "led")) == "1") "💡" else "⚫",
            "cm" to capteur(jeu), "moteur" to moteurDe(lireRobot(jeu, "moteur")))
    }
    private fun vus(c: JSONObject, k: String = "vus"): MutableList<Pair<Int, Int>> =
        (c.optJSONArray(k) ?: JSONArray()).let { a -> (0 until a.length()).map { a.getJSONArray(it).let { p -> p.getInt(0) to p.getInt(1) } }.toMutableList() }
    private fun ecrireVus(c: JSONObject, k: String, l: List<Pair<Int, Int>>) = c.put(k, JSONArray(l.map { JSONArray(listOf(it.first, it.second)) }))

    fun lignesPas(jeu: Jeu, compact: Boolean = false): List<String> {
        val c = etat(jeu)
        val cle = cleArene(jeu)
        val r = robot(jeu)
        val m = moteurDe(lireRobot(jeu, "moteur"))
        val (nv, ev) = pasRobot(cle, r, m)
        robotVers(c, cle, nv)
        val v = vus(c).ifEmpty { mutableListOf(r.x to r.y) }
        if ((nv.x to nv.y) !in v) v.add(nv.x to nv.y)
        ecrireVus(c, "vus", v)
        val cm = capteur(jeu)
        ecrireRobot(jeu, "capteur_distance", cm)
        noter(jeu, "pas", "$m → (${nv.x} ; ${nv.y}) ${nv.d} $cm cm (${if (ev == "avance") "avance" else if (ev == "tourne") "tourne" else ev})")
        val nj = c.optInt("journal", 0) + 1
        c.put("journal", nj)
        try { dossierRobot(jeu).mkdirs(); File(dossierRobot(jeu), "journal.txt").appendText(t("at.journal.ligne", "n" to nj, "moteur" to m, "x" to nv.x, "y" to nv.y, "d" to nv.d, "cm" to cm) + "\n") } catch (e: Exception) { }
        val df = c.optJSONObject("defi")
        var titre = ""
        val fin = mutableListOf<String>()
        var dessinVus: List<Pair<Int, Int>> = v
        if (df != null && df.length() > 0 && !df.optBoolean("fini")) {
            df.put("pas", df.optInt("pas") + 1)
            if (ev == "choc") df.put("chocs", df.optInt("chocs") + 1)
            val dv = vus(df)
            if ((nv.x to nv.y) !in dv) dv.add(nv.x to nv.y)
            ecrireVus(df, "vus", dv)
            dessinVus = dv
            val vd = verdict(dv.size, df.optInt("chocs"), df.optInt("pas"))
            titre = t("at.pas.defi", "n" to df.optInt("pas"), "total" to o("defi").optInt("pas", 20), "cases" to dv.size, "min" to o("defi").optInt("cases_min", 12)) + " · "
            if (vd != "en_cours") {
                df.put("fini", true)
                noter(jeu, "defi", "${dv.size} ${t("at.cases_mot")}, ${df.optInt("chocs")} ${t("at.chocs_mot")} ($vd)")
                fin += listOf("", (if (vd == "ok") "🏆 " else "✋ ") + t("at.defi.$vd", "cases" to dv.size, "min" to o("defi").optInt("cases_min", 12)))
                if (vd != "ok") fin.add("  " + t("at.defi.recommence"))
            }
        }
        val tete = "🤖 " + titre + t("at.pas.ev.$ev", "moteur" to m) + " · " + t("at.pas.capteur", "cm" to cm)
        if (compact) return listOf(tete) + fin
        return listOf(tete) + dessinGrille(cle, nv, dessinVus, ev == "choc").map { "  $it" } + fin
    }

    private fun reponse(jeu: Jeu, et: String, juste: Boolean, texteRep: String, ok: String, faux: String): List<String> {
        noter(jeu, et, "$texteRep (${if (juste) "ok" else "faux"})")
        return listOf(if (juste) "✔ $ok" else "✖ $faux")
    }

    fun commande(jeu: Jeu, reste: String, ici: File): String {
        val m = reste.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        val sous = asciiBas(m.getOrNull(0) ?: "aide")
        val a = m.drop(1).filter { it != "?" && it != "…" }
        val aide = ETABLI + listOf("🤖 " + t("at.aide.titre")) + t("at.aide.liste").split("\n").map { "  $it" }
        if (!dossier(jeu).isDirectory) return (aide + listOf("", "  " + t("at.pas_ouvert"))).joinToString("\n")
        val c = etat(jeu)
        val g = graine(jeu)
        val l: List<String> = when (sous) {
            "plan", "regles" -> ETABLI + t("at.meuble.plan", "nom" to jeu.nom).split("\n")
            "robot" -> {
                val led = ledDe(lireRobot(jeu, "led"))
                noter(jeu, "led", "$led ($led)")
                listOf("🤖 " + t("at.robot.titre"), "", "   ┌─────┐", "   │ ${if (led == "1") "💡" else "⚫"}  │ ← led", "   │ ◉ ◉ │ ← capteur_distance",
                    "   └┬───┬┘", "    ◯   ◯  ← moteur", "", "  " + (if (led == "?") t("at.robot.led_inconnue") else t("at.robot.led_$led")),
                    "  " + etatLigne(jeu), "  " + t("at.robot.fichiers"))
            }
            "grille" -> { noter(jeu, "grille", "vue (ok)")
                listOf("🗺 " + t("at.grille.titre"), "") + dessinGrille(cleArene(jeu), robot(jeu), vus(c)).map { "  $it" } + listOf("", "  " + etatLigne(jeu)) + bloc("at.grille.texte") }
            "pas" -> lignesPas(jeu)
            "ou" -> { val r = robot(jeu)
                if (a.isEmpty()) listOf(t("at.ou.aide"))
                else reponse(jeu, "ou", coordOk(a.joinToString(" "), r.x, r.y), if (coordOk(a.joinToString(" "), r.x, r.y)) "${r.x} ${r.y}" else a.joinToString(" "),
                    t("at.ou.ok", "x" to r.x, "y" to r.y), t("at.ou.faux")) }
            "cases" -> { val cm = capteur(jeu)
                if (a.isEmpty()) listOf(t("at.cases.aide", "cm" to cm))
                else { val ok = nombres(a.joinToString(" ")).firstOrNull() == cm / caseCm
                    reponse(jeu, "cases", ok, if (ok) "${cm / caseCm}" else a.joinToString(" "), t("at.cases.ok", "cm" to cm, "n" to cm / caseCm), t("at.cases.faux", "cm" to cm)) } }
            "logique" -> { noter(jeu, "logique", "lu (ok)"); listOf("🔀 " + t("at.logique.titre"), "") + bloc("at.logique.texte") }
            "verite" -> { val p = porte(g); val P = t("at.mot.$p").uppercase()
                if (a.isEmpty()) listOf("🔀 " + t("at.verite.titre", "porte" to P), "") + bloc("at.verite.texte", "porte" to P) +
                    listOf("", "   A B │ A $P B", "   ────┼──────") + listOf(0 to 0, 0 to 1, 1 to 0, 1 to 1).map { (x, y) -> "   $x $y │   ?" } +
                    listOf("", "  " + t("at.verite.repondre"))
                else { val ok = chiffres(a) == tableVerite(p)
                    reponse(jeu, "verite", ok, "$p " + (if (ok) chiffres(a).joinToString("") else a.joinToString(" ")), t("at.verite.ok", "porte" to P), t("at.verite.faux")) } }
            "choix" -> { val cartes = choixCartes(g)
                if (a.isEmpty()) listOf("🔀 " + t("at.choix.titre"), "") + cartes.map { (n, id, _) -> "  $n. " + t("at.choix.$id") } +
                    listOf("", "  " + t("at.choix.repondre", "et" to t("at.mot.et"), "ou" to t("at.mot.ou"), "non" to t("at.mot.non")))
                else { val donne = a.map { porteDe(it) }
                    val ok = donne == cartes.map { it.third }
                    val faux = cartes.mapIndexed { i, x -> if (donne.getOrNull(i) != x.third) "${x.first}" else null }.filterNotNull()
                    reponse(jeu, "choix", ok, if (ok) donne.joinToString(" ") else a.joinToString(" "), t("at.choix.ok"), t("at.choix.faux", "liste" to faux.joinToString(", "))) } }
            "essai" -> { robotVers(c, "e", depart("e")); ecrireVus(c, "vus", listOf(depart("e").let { it.x to it.y })); c.put("defi", JSONObject())
                ecrireRobot(jeu, "capteur_distance", capteur(jeu)); ecrireRobot(jeu, "moteur", "stop"); noter(jeu, "essai_debut", "entrainement (ok)")
                listOf("🧪 " + t("at.essai.titre"), "") + dessinGrille("e", robot(jeu), vus(c)).map { "  $it" } + listOf("") + bloc("at.essai.texte") }
            "defi" -> { val i = areneDefi(g); val dep = depart("$i")
                robotVers(c, "$i", dep); ecrireVus(c, "vus", listOf(dep.x to dep.y))
                c.put("defi", JSONObject().put("arene", i).put("pas", 0).put("chocs", 0).put("vus", JSONArray(listOf(JSONArray(listOf(dep.x, dep.y))))))
                ecrireRobot(jeu, "capteur_distance", capteur(jeu)); ecrireRobot(jeu, "moteur", "stop"); noter(jeu, "defi_debut", "${i + 1} (ok)")
                listOf("🏁 " + t("at.defi.titre", "n" to i + 1), "") + dessinGrille("$i", dep, listOf(dep.x to dep.y)).map { "  $it" } + listOf("") +
                    bloc("at.defi.regles", "pas" to o("defi").optInt("pas", 20), "min" to o("defi").optInt("cases_min", 12)) }
            "aide-cerveau", "aide_cerveau" -> listOf("🧠 " + t("at.aidec.titre"), "") + bloc("at.aidec.texte").map { it.replace("nano cerveau.sh", "edite cerveau.sh") } + listOf("") +
                cerveauMalin().trimEnd('\n').split("\n").map { "    $it" } + listOf("") + bloc("at.aidec.fin")
            "pi" -> raconte(jeu, "pi", "🍓")
            "gpio" -> raconte(jeu, "gpio", "📍").let { it.take(2) + GPIO.map { g_ -> "   $g_" } + listOf("") + it.drop(2) }
            "autonome" -> raconte(jeu, "autonome", "🔁")
            "embarque" -> raconte(jeu, "embarque", "🔌")
            "reflexe" -> { val (v, ms, cm) = reflexe(g)
                if (a.isEmpty()) listOf("⏱ " + t("at.reflexe.titre"), "") + bloc("at.reflexe.texte", "v" to v, "ms" to ms)
                else { val ok = nombres(a.joinToString(" ")).firstOrNull() == cm
                    reponse(jeu, "reflexe", ok, if (ok) "$cm" else a.joinToString(" "), t("at.reflexe.ok", "cm" to cm, "v" to v, "ms" to ms), t("at.reflexe.faux", "v" to v, "ms" to ms)) } }
            "arduino" -> raconte(jeu, "arduino", "🧑‍🔧")
            "telephone" -> raconte(jeu, "telephone", "📱")
            else -> aide
        }
        return l.joinToString("\n")
    }
    private val GPIO = listOf("   3V3 (1) (2) 5V", " GPIO2 (3) (4) 5V", " GPIO3 (5) (6) GND", " GPIO4 (7) (8) GPIO14", "   GND (9) (10) GPIO15",
        "GPIO17 (11) (12) GPIO18", "   …    …    …")
    private fun raconte(jeu: Jeu, cle: String, emoji: String): List<String> { noter(jeu, cle, "lu (ok)"); return listOf("$emoji " + t("at.$cle.titre"), "") + bloc("at.$cle.texte") }

    // ---------------------------------------------------------------- la boucle de l'enfant (le shell du téléphone ne connaît pas `atelier`)
    private val BOUCLE = Regex("^for\\s+\\w+\\s+in\\s+(?:\\$\\(seq\\s+(\\d+)\\)|\\{1\\.\\.(\\d+)\\}|((?:\\d+\\s*)+))\\s*;\\s*do\\s+(.+?)\\s*;?\\s*done\\s*$")
    const val TOURS_MAX = 40

    /** `for i in $(seq N); do …; atelier pas; done` : l'appli déroule la boucle (au plus TOURS_MAX tours) ; les morceaux qui
     *  ne sont pas des commandes de l'appli (sh cerveau.sh…) partent au vrai shell du téléphone, dans le dossier courant.
     *  null si la ligne n'est pas une boucle qui appelle `atelier`. */
    fun boucle(jeu: Jeu, ligne: String, ici: File): String? {
        val mm = BOUCLE.matchEntire(ligne.trim()) ?: return null
        val corps = mm.groupValues[4].split(";").map { it.trim() }.filter { it.isNotEmpty() }
        if (corps.none { Regex("^(tg\\s+)?atelier\\s").containsMatchIn(it) }) return null
        val n = (mm.groupValues[1].ifEmpty { mm.groupValues[2] }).toIntOrNull() ?: mm.groupValues[3].trim().split(Regex("\\s+")).size
        if (n > TOURS_MAX) return "✋ " + t("at.tel.boucle_max", "max" to TOURS_MAX)
        val out = mutableListOf("🔁 " + t("at.tel.boucle", "n" to n))
        var dernierPas: List<String> = emptyList()
        for (k in 1..n) {
            for (p in corps) {
                if (Regex("^(tg\\s+)?atelier\\s+pas\\b").containsMatchIn(p)) {
                    dernierPas = lignesPas(jeu)
                    out.add("$k. " + dernierPas.first())
                    if (dernierPas.size > 1 && dernierPas.any { it.startsWith("🏆") || it.startsWith("✋") }) out += dernierPas.filter { it.startsWith("🏆") || it.startsWith("✋") || it.startsWith("  " + t("at.defi.recommence").take(6)) }
                } else if (Regex("^(tg\\s+)?atelier\\s").containsMatchIn(p)) {
                    out.add(commande(jeu, p.replace(Regex("^(tg\\s+)?atelier\\s+"), ""), ici))
                } else shellUnTour(jeu, p, ici)?.let { if (it.isNotBlank()) out.add("   " + it.trim().lines().last()) }
            }
        }
        if (dernierPas.size > 1) out += listOf("") + dessinGrille(cleArene(jeu), robot(jeu), etat(jeu).optJSONObject("defi")?.takeIf { it.length() > 0 }?.let { vus(it) } ?: vus(etat(jeu))).map { "  $it" }
        return out.joinToString("\n")
    }

    /** Un morceau de la boucle dans le vrai shell du téléphone (comme si l'enfant le tapait) : dans le terrain, 5 s au plus. */
    private fun shellUnTour(jeu: Jeu, cmd: String, ici: File): String? {
        val dossier = if (ici.canonicalPath.startsWith(jeu.terrain.canonicalPath)) ici else dossier(jeu)
        return try {
            val p = ProcessBuilder(Shell.SH, "-c", cmd).directory(dossier).redirectErrorStream(true)
            p.environment()["HOME"] = jeu.home.absolutePath
            val pr = p.start()
            pr.outputStream.close()
            val fini = pr.waitFor(5, TimeUnit.SECONDS)
            if (!fini) { pr.destroyForcibly(); return t("shell.arrete") }
            pr.inputStream.bufferedReader().readText().take(2000)
        } catch (e: Exception) { null }
    }
}
