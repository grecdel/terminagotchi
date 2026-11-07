package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.text.Normalizer
import java.util.Locale

/**
 * ⛰ Le Sommet — Expert++ (docs/programme.md § 2.18, § 7.6), portage de pc/tg/sommet.py.
 *
 * Il s'ouvre quand TROIS mondes du Carrefour ont leur PALIER 3, comptés sur la liste des mondes de programme.json (ceux
 * qui arriveront plus tard comptent dès qu'ils existent). Les scripts fragiles et cassés sont fournis par le jeu dans le
 * terrain (terrain_terminagotchi/sommet) ; aucun ne sort de ce dossier, ne demande sudo ni n'utilise le réseau.
 * Sur le téléphone, le shell est sh (mksh) : mêmes options -n, -x, set -euo pipefail, trap, getopts. Ce qui manque
 * (<( ), awk sur plusieurs fichiers, shellcheck, man, apropos) est caché ou raconté. Le défi du jour est fait d'exercices
 * de la salle d'entraînement, vérifiés par le site comme les autres. Vecteurs communs donnees/sommet/vecteurs.json.
 */
object Sommet {
    @Volatile var chargeur: (() -> String?)? = null
    private var d: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("sommet.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun donnees(): JSONObject = d ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() }).also { d = it }
    private fun liste(o: JSONObject?, k: String): List<String> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.get(it).toString() } } ?: emptyList()
    private fun objets(o: JSONObject?, k: String): List<JSONObject> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.getJSONObject(it) } } ?: emptyList()
    private fun o(k: String) = donnees().optJSONObject(k) ?: JSONObject()
    /** Le texte d'une clé pour un FICHIER du terrain (script, journal, registre) : sans les marques de sens d'écriture
     *  (arabe, ourdou) que t() ajoute pour l'écran ; le contenu est le même que celui écrit par le jeu PC. */
    private fun tf(cle: String, vararg p: Pair<String, Any?>) = t(cle, *p).replace(Regex("[\u2066\u2069]|(?m)^\u200F"), "")

    // ================================================================ la spécification pure (vecteurs communs)
    private fun sha(s: String) = MessageDigest.getInstance("SHA-256").digest(s.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
    fun tire(graine: String, sel: String, n: Int) = (sha("$graine:$sel").substring(0, 8).toLong(16) % n).toInt()
    fun asciiId(texte: String?): String = Normalizer.normalize(texte ?: "", Normalizer.Form.NFKD)
        .filter { Character.getType(it) != Character.NON_SPACING_MARK.toInt() }.lowercase(Locale.ROOT).trim()
    fun shQuote(s: String) = "'" + s.replace("'", "'\\''") + "'"
    private fun uneLigne(s: String?) = (s ?: "").trim().split(Regex("\\s+")).filter { it.isNotEmpty() }.joinToString(" ")

    /** Un gabarit de script : @@clé@@ → le texte entre apostrophes, ##clé## → le texte brut (commentaire). */
    fun remplir(lignes: List<String>, sh: String = "bash"): String {
        val out = lignes.map { l ->
            Regex("##([\\w.]+)##").replace(Regex("@@([\\w.]+)@@").replace(l) { m -> shQuote(uneLigne(tf(m.groupValues[1], "sh" to sh))) }) { m ->
                uneLigne(tf(m.groupValues[1], "sh" to sh)) }
        }.toMutableList()
        if (sh != "bash") out[0] = "#!/system/bin/sh"
        return out.joinToString("\n") + "\n"
    }
    fun script(nom: String, sh: String = "bash") = remplir(liste(o("scripts"), nom), sh)

    fun <T : Comparable<T>> ordre(graine: String, sel: String, l: List<T>): List<T> =
        l.sortedWith(compareBy<T>({ tire(graine, "$sel:$it", 1 shl 30) }, { it }))

    // ---------------------------------------------------------------- S3 : le journal
    private fun jourDe(debut: String, k: Int) = java.time.LocalDate.parse(debut).plusDays(k.toLong()).toString()

    fun journal(graine: String): List<Pair<String, String>> {
        val J = o("journal")
        val n = J.optInt("lignes"); val jours = J.optInt("jours"); val debut = J.optString("debut")
        val out = mutableListOf<Pair<String, String>>()
        for (i in 0 until n) {
            val r = tire(graine, "l$i", 10)
            val jour = jourDe(debut, minOf(jours - 1, i * jours / n))
            if (i > 0 && r < 2) {
                if (r == 0) out.add("  " + tf("som.log.suite.releve", "date" to jourDe(debut, tire(graine, "d$i", jours + 3))) to "releve")
                else out.add("  " + tf("som.log.suite.fausse") to "fausse")
                continue
            }
            val tag = if (r < 7) "INFO" else if (r < 9) "ALERTE" else "ERREUR"
            val ms = liste(J.optJSONObject("messages"), tag)
            out.add("$jour [$tag] " + tf(ms[tire(graine, "m$i", ms.size)]) to tag)
        }
        return out
    }
    fun journalTexte(graine: String) = journal(graine).joinToString("") { it.first + "\n" }
    private val DATE = Regex("[0-9]{4}-[0-9]{2}-[0-9]{2}")
    fun lignesDatees(graine: String) = journal(graine).map { it.first }.filter { Regex("^[0-9]{4}-[0-9]{2}-[0-9]{2}").containsMatchIn(it) }
    fun dates(graine: String) = journal(graine).flatMap { l -> DATE.findAll(l.first).map { it.value }.toList() }.toSortedSet().toList()
    fun alertesPartout(graine: String) = journal(graine).map { it.first }.filter { "ALERTE" in it || "ERREUR" in it }
    fun alertes(graine: String) = journal(graine).filter { it.second == "ALERTE" || it.second == "ERREUR" }.map { it.first }
    fun dateFr(l: String) = Regex("^([0-9]{4})-([0-9]{2})-([0-9]{2})").replace(l) { "${it.groupValues[3]}/${it.groupValues[2]}/${it.groupValues[1]}" }

    // ---------------------------------------------------------------- S4 : l'éboulis
    val TAILLES = listOf(120, 260, 410, 530, 680, 790, 905, 1040, 1180, 1333)
    fun eboulis(graine: String): LinkedHashMap<String, Pair<String, Int>> {
        val p = ordre(graine, "pierres", liste(donnees(), "pierres"))
        val ta = ordre(graine, "tailles", TAILLES)
        val places = listOf("nord" to p[0], "nord" to p[1], "nord" to p[2], "nord" to p[3], "sud" to p[0], "sud" to p[1],
            "sud" to p[4], "sud" to p[5], "grotte" to p[6], "grotte/profond" to p[7])
        val out = LinkedHashMap<String, Pair<String, Int>>()
        places.forEachIndexed { k, (dd, n) -> out["$dd/$n.txt"] = n to ta[k] }
        return out
    }
    fun contenuPierre(nom: String, taille: Int): String {
        val debut = "$nom\n"
        return debut + "#".repeat(taille - debut.toByteArray().size - 1) + "\n"
    }
    fun plusLourds(graine: String, n: Int = 5): List<Pair<Int, String>> =
        eboulis(graine).map { (rel, v) -> v.second to "eboulis/$rel" }.sortedWith(compareBy({ -it.first }, { it.second })).take(n)
    fun plusLourde(graine: String) = plusLourds(graine, 1)[0].second.substringAfterLast('/').removeSuffix(".txt")
    fun totalEboulis(graine: String) = eboulis(graine).values.sumOf { it.second }
    fun nomsDans(graine: String, dossier: String) = eboulis(graine).keys.filter { it.substringBeforeLast('/') == dossier }.map { it.substringAfterLast('/') }.sorted()

    // ---------------------------------------------------------------- S6 : la boussole
    fun lieu(graine: String, cap: String, pas: Int): String { val l = liste(donnees(), "lieux"); return l[tire(graine, "lieu:$cap:$pas", l.size)] }
    fun mission(graine: String): Pair<String, Int> { val c = liste(donnees(), "caps"); return c[tire(graine, "mission:cap", c.size)] to 2 + tire(graine, "mission:pas", 7) }
    fun scriptBoussole(graine: String, sh: String = "bash"): String {
        val l = mutableListOf("#!/usr/bin/env bash", "# ##som.sc.boussole.role##", "aide() {", "  echo @@som.sc.boussole.usage@@",
            "  echo @@som.sc.boussole.but@@", "  echo '  -c CAP      '@@som.sc.boussole.cap@@",
            "  echo '  -p PAS      '@@som.sc.boussole.pas@@", "  echo '  -h, --help  '@@som.sc.boussole.aide@@", "}",
            "if [ \"\${1:-}\" = \"--help\" ]; then aide; exit 0; fi", "cap=\"\"", "pas=\"\"", "while getopts \"c:p:h\" opt; do",
            "  case \$opt in", "    c) cap=\$OPTARG ;;", "    p) pas=\$OPTARG ;;", "    h) aide; exit 0 ;;",
            "    *) aide >&2; exit 2 ;;", "  esac", "done", "if [ -z \"\$cap\" ] || [ -z \"\$pas\" ]; then aide >&2; exit 2; fi",
            "case \"\$cap:\$pas\" in")
        for (c in liste(donnees(), "caps")) for (p in 1..9) l.add("  $c:$p) lieu=${lieu(graine, c, p)} ;;")
        l += listOf("  *) lieu=brume ;;", "esac", "echo @@som.sc.boussole.arrive@@ \"\$lieu\"", "echo \"\$lieu\" > arrivee.txt")
        return remplir(l, sh)
    }
    fun aideBoussole(sh: String = "bash"): String {
        fun x(k: String) = uneLigne(tf(k, "sh" to sh))
        return listOf(x("som.sc.boussole.usage"), x("som.sc.boussole.but"), "  -c CAP      " + x("som.sc.boussole.cap"),
            "  -p PAS      " + x("som.sc.boussole.pas"), "  -h, --help  " + x("som.sc.boussole.aide")).joinToString("\n")
    }

    // ---------------------------------------------------------------- S7 : le CTF combiné
    fun fragments(graine: String): List<String> = ordre(graine, "fragments", liste(donnees(), "mots")).take(3)
    fun drapeau(graine: String) = "TG{" + fragments(graine).joinToString("-") + "}"
    fun drapeauOk(graine: String, rep: String?): Boolean {
        val r = (rep ?: "").trim().lowercase(Locale.ROOT).replace(" ", "")
        val juste = fragments(graine).joinToString("-")
        return r == juste || r == "tg{$juste}"
    }
    fun registre(graine: String): String {
        val f = fragments(graine)
        val leurres = ordre(graine, "leurres", liste(donnees(), "mots")).filter { it !in f }
        val l = listOf(uneLigne(tf("som.ctf.registre.titre")), "fragment1 = ${leurres[0]}", uneLigne(tf("som.ctf.registre.l1")),
            "fragment1=${leurres[1].uppercase(Locale.ROOT)}", uneLigne(tf("som.ctf.registre.l2")),
            uneLigne("${tf("som.ctf.registre.l3")} fragment1=${f[0]} ;"), uneLigne(tf("som.ctf.registre.l4")))
        return l.joinToString("") { it + "\n" }
    }
    fun scriptPorte(graine: String, sh: String = "bash"): String {
        val f = fragments(graine)
        return remplir(listOf("#!/usr/bin/env bash", "# ##som.sc.porte.role##",
            "aide() { echo @@som.sc.porte.usage@@; echo @@som.sc.porte.cle@@; }",
            "if [ \"\${1:-}\" = \"--help\" ]; then aide; exit 0; fi", "cle=\"\"", "while getopts \"k:h\" opt; do",
            "  case \$opt in", "    k) cle=\$OPTARG ;;", "    h) aide; exit 0 ;;", "    *) aide >&2; exit 2 ;;", "  esac",
            "done", "if [ \"\$cle\" = \"${f[0]}\" ]; then", "  echo fragment3=${f[2]} | tee \"\$(dirname \"\$0\")/porte_ouverte.txt\"", "else",
            "  echo @@som.sc.porte.non@@ >&2", "  exit 1", "fi"), sh)
    }
    fun fichiersCtf(graine: String, sh: String = "bash"): LinkedHashMap<String, String> = linkedMapOf(
        "ctf/registre.log" to registre(graine), "ctf/porte.sh" to scriptPorte(graine, sh),
        "ctf/eboulis/une pierre creuse/cache.frag" to "fragment2=${fragments(graine)[1]}\n",
        "ctf/eboulis/leurre.txt" to "fragment2=" + ordre(graine, "leurre2", liste(donnees(), "mots"))[5] + "\n",
        "ctf/eboulis/vieux sac/notes.txt" to uneLigne(tf("som.ctf.notes")) + "\n")

    // ---------------------------------------------------------------- l'ouverture : 3 mondes au palier 3
    private fun palierOuverture() = o("ouverture").optInt("palier", 3)
    private fun mondes(): List<JSONObject> = objets(Programme.donnees(), "mondes")

    /** Les mondes (programme.json) dont la leçon du palier voulu est faite : (id du monde, chapitre). Ceux qui arriveront
     *  comptent dès qu'ils existent ; le Sommet ne se compte pas. */
    fun mondesAuPalier(jeu: Jeu, palier: Int = palierOuverture()): List<Pair<String, String>> {
        val f = Histoire.h(jeu).optJSONArray("faits")?.let { a -> (0 until a.length()).map { a.getString(it) } }?.toSet() ?: emptySet()
        val out = mutableListOf<Pair<String, String>>()
        for (m in mondes()) {
            val ps = liste(m, "paliers")
            val ch = m.optString("chapitre").ifEmpty { m.optString("id") }
            val c = Histoire.PAR_CHAP[ch]
            if (m.optString("id") == "sommet" || ps.size <= palier || c == null || ps[0] !in c.lecons) continue
            if (ps[palier] in f || Histoire.fini(jeu, ch)) out.add(m.optString("id") to ch)
        }
        return out
    }
    fun leconsQuiOuvrent(): Set<String> { val p = palierOuverture()
        return mondes().filter { it.optString("id") != "sommet" && liste(it, "paliers").size > p }.map { liste(it, "paliers")[p] }.toSet() }
    fun ouvert(jeu: Jeu) = mondesAuPalier(jeu).size >= o("ouverture").optInt("mondes", 3)
    fun manque(jeu: Jeu): List<String> {
        val f = mondesAuPalier(jeu)
        return listOf(t("som.manque", "n" to f.size, "total" to o("ouverture").optInt("mondes", 3), "palier" to palierOuverture(),
            "mondes" to (f.joinToString(", ") { Histoire.nomChapitre(it.second) }.ifEmpty { "—" })))
    }
    fun annonce(jeu: Jeu): Boolean {
        val h = Histoire.h(jeu)
        val deja = h.optJSONArray("mondes_annonces") ?: JSONArray().also { h.put("mondes_annonces", it) }
        if ((0 until deja.length()).any { deja.getString(it) == "sommet" } || Histoire.fini(jeu, "sommet") || !ouvert(jeu)) return false
        deja.put("sommet")
        jeu.log(t("som.ouvert.log"))
        jeu.dire(Histoire.dire(jeu, "som.ouvert.dit", "mondes" to mondesAuPalier(jeu).joinToString(", ") { Histoire.nomChapitre(it.second) }), 18)
        return true
    }

    // ---------------------------------------------------------------- le défi du jour (vérifié par le site)
    fun defiTypes(valeur: String, possibles: List<String>): List<String> {
        val D = o("defi")
        return Entrainement.choisir(Tirage.Hasard(valeur, D.optLong("base")), possibles, minOf(D.optInt("n", 3), possibles.size))
    }
    private fun jourLocal() = java.text.SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).format(java.util.Date(Entrainement.maintenant()))
    fun graineDefi(jeu: Jeu): Pair<String, Boolean> {
        val cache = Recensement.compte(jeu).optJSONObject("graines")
        val id = cache?.keys()?.asSequence()?.firstOrNull { it.substringBefore('.') == jourLocal() }
        val v = id?.let { cache.optString(it) } ?: ""
        if (v.length >= 16) return v to true
        return sha("local:${jourLocal()}:${graine(jeu)}") to false
    }
    fun defiDuJour(jeu: Jeu): Pair<List<String>, Boolean> {
        val (v, ok) = graineDefi(jeu)
        return defiTypes(v, Entrainement.TYPES.keys.filter { Entrainement.typePossible(jeu, it) }) to ok
    }
    fun noterExercice(jeu: Jeu, typ: String, medaille: String, gid: String) {
        val s = etat(jeu)
        var dj = s.optJSONObject("defi")
        if (dj == null || dj.optString("jour") != jourLocal()) dj = JSONObject().put("jour", jourLocal()).put("faits", JSONObject())
        if (medaille in liste(o("defi"), "medailles")) dj.getJSONObject("faits").put(typ, JSONObject().put("m", medaille).put("v", gid.isNotEmpty()))
        s.put("defi", dj)
    }
    fun defiFaits(jeu: Jeu): JSONObject { val dj = etat(jeu).optJSONObject("defi") ?: return JSONObject()
        return if (dj.optString("jour") == jourLocal()) dj.optJSONObject("faits") ?: JSONObject() else JSONObject() }

    // ---------------------------------------------------------------- la cordée (vue déployée)
    class Cordee(val outil: String, val geste: String, val de: String, val vers: String)
    fun cordeeDe(morceau: String?): Cordee? {
        val m = (morceau ?: "").trim()
        for (r in objets(o("cordee"), "regles")) if (Regex(r.optString("motif")).containsMatchIn(m))
            return Cordee(r.optString("outil"), r.optString("geste"), r.optString("de"), r.optString("vers"))
        return null
    }

    // ================================================================ l'état, le terrain, le carnet
    fun etat(jeu: Jeu): JSONObject {
        val c = jeu.module("sommet")
        if (c.optJSONArray("faits") == null) c.put("faits", JSONArray())
        return c
    }
    private fun fait(jeu: Jeu, cle: String): Boolean {
        if (cle in liste(etat(jeu), "faits")) return true
        etat(jeu).getJSONArray("faits").put(cle)
        return false
    }
    fun graine(jeu: Jeu) = Histoire.graine(jeu)
    const val CARNET = "carnet_du_sommet.txt"
    fun dossier(jeu: Jeu) = File(jeu.terrain, "sommet")
    fun noter(jeu: Jeu, etiquette: String, texte: String) { try { dossier(jeu).mkdirs(); File(dossier(jeu), CARNET).appendText("[$etiquette] $texte\n") } catch (e: Exception) { } }
    fun carnet(jeu: Jeu): String = try { File(dossier(jeu), CARNET).readText() } catch (e: Exception) { "" }
    fun dansCarnet(jeu: Jeu, etiquette: String, motCle: String = "ok") = Regex("^\\[$etiquette].*\\($motCle\\)\\s*$", RegexOption.MULTILINE).containsMatchIn(carnet(jeu))
    fun dernier(jeu: Jeu, etiquette: String): String? = carnet(jeu).lines().lastOrNull { it.startsWith("[$etiquette]") }
    private fun ecrire(jeu: Jeu, rel: String, contenu: String) = Histoire.ecrire(jeu, "sommet/$rel", contenu, finLigne = false)
    private fun lire(jeu: Jeu, rel: String): String? = Histoire.lire(jeu, "sommet/$rel")
    private fun lignes(jeu: Jeu, rel: String) = (lire(jeu, rel) ?: "").lines().let { if (it.lastOrNull() == "") it.dropLast(1) else it }

    fun meubles(jeu: Jeu): Map<String, Any> = linkedMapOf("sommet/refuge.txt" to tf("som.meuble.refuge") + "\n",
        "sommet/$CARNET" to tf("som.meuble.carnet") + "\n")

    fun meubler(jeu: Jeu, lid: String?) {
        val dd = dossier(jeu)
        if (!dd.isDirectory || lid == null) return
        if (lid == "som0" && !File(dd, "refuge.txt").exists()) ecrire(jeu, "refuge.txt", tf("som.meuble.refuge") + "\n")
        val e = Programme.donnees().optJSONObject("etapes")?.optJSONObject("$lid.${jeu.etape}")
        if (e != null) for (mid in liste(e, "maths")) {
            if (Maths.noeud(mid) != null && !Maths.sait(jeu, mid) && !fait(jeu, "pont:$mid")) {
                jeu.dire(t("som.pont", "notion" to Maths.titre(mid), "cmd" to "maths $mid"), 16)
                break
            }
        }
    }

    // ---------------------------------------------------------------- les vérifications des étapes
    private val SET_EUO = Regex("^\\s*set\\s+(-euo\\s+pipefail|-eu\\s+-o\\s+pipefail|-e\\s+-u\\s+-o\\s+pipefail|-o\\s+pipefail\\s+-eu)\\s*$")
    fun fragileSet(jeu: Jeu): Boolean {
        val l = lignes(jeu, "fragile.sh")
        val k = l.indexOfFirst { it.trim().startsWith("cp ") }
        return k >= 0 && l.take(k).any { SET_EUO.matches(it) }
    }
    fun fragileGuillemets(jeu: Jeu) = lignes(jeu, "fragile.sh").any { Regex("^\\s*cp\\s+\"\\$\\{?carnet\\}?\"\\s+coffre/?\\s*$").matches(it) }
    fun coffre(jeu: Jeu) = File(dossier(jeu), "coffre/carnet de bord.txt").isFile && fragileSet(jeu) && fragileGuillemets(jeu)
    fun sac(jeu: Jeu) = lignes(jeu, "sac.txt").count { it.isNotBlank() } == 3
    fun brouillons(jeu: Jeu) = (dossier(jeu).list() ?: emptyArray()).filter { it.startsWith("brouillon.") }.sorted()
    fun propre(jeu: Jeu) = dansCarnet(jeu, "bivouac") && brouillons(jeu).isEmpty() && File(dossier(jeu), "bivouac.sh").isFile
    private val ALERTE_ANCREE = Regex("^[0-9]{4}-[0-9]{2}-[0-9]{2} \\[(ALERTE|ERREUR)\\]")
    fun alertesTxt(jeu: Jeu): Boolean {
        val l = lignes(jeu, "alertes.txt").filter { it.isNotBlank() }
        return l.isNotEmpty() && l == lignes(jeu, "journal.log").filter { ALERTE_ANCREE.containsMatchIn(it) }
    }
    fun casseOk(jeu: Jeu): Boolean {
        val l = lignes(jeu, "casse.sh")
        val n = o("casse").optInt("ligne", 6)
        return l.size >= n + 1 && (Regex(";\\s*then\\s*$").containsMatchIn(l[n - 1]) || l[n].trim() == "then")
    }
    fun boucleOk(jeu: Jeu): Boolean { val x = lire(jeu, "boucle.sh") ?: ""; return "totl" !in x && "total=\$((total + alt))" in x }
    fun arriveeOk(jeu: Jeu): Boolean {
        val m = Regex("^\\[boussole] \\S+ \\S+ (\\S+) pose \\(ok\\)").find(dernier(jeu, "boussole") ?: "") ?: return false
        return (lire(jeu, "arrivee.txt") ?: "").trim() == m.groupValues[1]
    }

    // ---------------------------------------------------------------- les leçons du téléphone (sh au lieu de bash)
    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)
    private const val LS = "^(ls|dir)\\b"
    private const val LIRE = "^(cat|less|more|head|tail)\\b"
    private const val SO = "^(tg\\s+)?sommet\\s+"
    private const val SH = "^(bash|sh)\\s+(\\./)?"
    private const val O_ = "sommet"

    private fun n(lid: String, i: Any, cmd: String, re: String? = null, fs: ((Jeu) -> Boolean)? = null, ou: String? = O_,
                  exploit: String? = null, toutCode: Boolean = false) =
        Etape("hist.$lid.$i.dit", cmd, "hist.$lid.$i.bravo", re?.let { r(it) }, fs, null, null, ou, exploit = exploit, toutCode = toutCode)

    val IDS = (0..7).map { "som$it" }

    fun lecons(jeu: Jeu): Map<String, Lecon> {
        val carnetOk = { et: String -> { j: Jeu -> dansCarnet(j, et) } }
        return linkedMapOf(
            "som0" to Lecon("hist.som0.titre", null, 1, listOf(
                Etape("hist.entree.dit", "cd ~/terrain_terminagotchi/sommet", "hist.entree.bravo", ici = "sommet", params = mapOf("piece" to "sommet")),
                n("som0", 1, "ls", re = LS),
                n("som0", 2, "cat refuge.txt", re = "$LIRE.*refuge"),
            )),
            "som1" to Lecon("hist.som1.titre", null, 1, listOf(
                n("som1", 0, "sommet fragile", re = "${SO}fragile"),
                n("som1", 1, "cat fragile.sh", re = "$LIRE.*fragile\\.sh"),
                n("som1", 2, "sh fragile.sh \"carnet de bord.txt\"", re = "${SH}fragile\\.sh\\s+\\S", toutCode = true),
                n("som1", 3, "echo \$?", re = "^echo\\s+\\$\\?\\s*$"),
                n("som1", 4, "sed -i '2i set -euo pipefail' fragile.sh", fs = { j -> fragileSet(j) }),
                n("som1", 5, "sh fragile.sh \"carnet de bord.txt\"; echo \$?", re = "${SH}fragile\\.sh\\s+\\S", toutCode = true),
                n("som1", 6, "sed -i 's/cp \$carnet/cp \"\$carnet\"/' fragile.sh", fs = { j -> fragileGuillemets(j) }),
                n("som1", 7, "sh fragile.sh", re = "${SH}fragile\\.sh\\s*$", toutCode = true),
                n("som1", 8, "sh fragile.sh \"carnet de bord.txt\"", fs = { j -> coffre(j) }),
            )),
            "som2" to Lecon("hist.som2.titre", null, 1, listOf(
                n("som2", 0, "sommet bivouac", re = "${SO}bivouac"),
                n("som2", 1, "sh sale.sh", re = "${SH}sale\\.sh", toutCode = true),
                n("som2", 2, "ls brouillon.*", re = "^ls\\b.*brouillon", toutCode = true),
                n("som2", 3, "cat bivouac.sh", re = "$LIRE.*bivouac\\.sh"),
                n("som2", 4, "sh bivouac.sh -n 3", fs = { j -> sac(j) }),
                n("som2", 5, "ls brouillon.* | wc -l", re = "^ls\\b.*brouillon.*\\|\\s*wc\\s+-l", toutCode = true),
                n("som2", 6, "sh bivouac.sh -x", re = "${SH}bivouac\\.sh\\s+-[a-gi-mo-z]", toutCode = true),
                n("som2", 7, "rm brouillon.*", fs = { j -> propre(j) }),
            )),
            "som3" to Lecon("hist.som3.titre", null, 1, listOf(
                n("som3", 0, "sommet journal", re = "${SO}journal"),
                n("som3", 1, "head -5 journal.log", re = "$LIRE.*journal\\.log"),
                n("som3", 2, "grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}' journal.log | wc -l", re = "^grep\\b.*\\s-\\w*E.*\\^\\[0-9\\].*journal\\.log", toutCode = true),
                n("som3", 3, "grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' journal.log | sort -u | wc -l", re = "^grep\\b.*\\s-\\w*o.*journal\\.log.*\\|\\s*sort\\b"),
                n("som3", 4, "sommet dates ?", fs = carnetOk("dates"), ou = null),
                n("som3", 5, "grep -cE 'ALERTE|ERREUR' journal.log", re = "^grep\\b.*ALERTE\\|ERREUR.*journal\\.log", toutCode = true),
                n("som3", 6, "grep -E '^[0-9-]{10} \\[(ALERTE|ERREUR)\\]' journal.log > alertes.txt", fs = { j -> alertesTxt(j) }),
                n("som3", 7, "sommet alertes ?", fs = carnetOk("alertes"), ou = null),
                n("som3", 8, "sed -E 's/^([0-9]{4})-([0-9]{2})-([0-9]{2})/\\3\\/\\2\\/\\1/' alertes.txt", re = "^sed\\s+(-\\w+\\s+)*-E\\b.*\\\\[123].*alertes\\.txt"),
            )),
            "som4" to Lecon("hist.som4.titre", null, 1, listOf(
                n("som4", 0, "sommet eboulis", re = "${SO}[eé]boulis"),
                n("som4", 1, "find eboulis -type f", re = "^find\\s+eboulis\\b(?!.*print0)"),
                n("som4", 2, "find eboulis -type f | xargs wc -c", re = "^find\\s+eboulis\\b(?!.*print0).*\\|\\s*xargs\\s+(?!.*-0)", toutCode = true),
                n("som4", 3, "find eboulis -type f -print0 | xargs -0 wc -c | sort -nr | head -6", re = "^find\\s+eboulis\\b.*-print0.*\\|\\s*xargs\\s+(-\\w+\\s+)*-0"),
                n("som4", 4, "sommet lourd ?", fs = carnetOk("lourd"), ou = null),
                n("som4", 5, "echo \"pierres : \$(find eboulis -type f | wc -l)\"", re = "^echo\\b.*\\$\\(\\s*find\\b.*eboulis"),
            )),
            "som5" to Lecon("hist.som5.titre", null, 1, listOf(
                n("som5", 0, "sommet casse", re = "${SO}casse"),
                n("som5", 1, "sh -n casse.sh", re = "^(bash|sh)\\s+-n\\s+(\\./)?casse\\.sh", toutCode = true),
                n("som5", 2, "sommet ligne ?", fs = carnetOk("ligne"), ou = null),
                n("som5", 3, "sed -i '6s/\$/; then/' casse.sh", fs = { j -> casseOk(j) }),
                n("som5", 4, "sh -n casse.sh && sh casse.sh", re = "${SH}casse\\.sh\\s*$"),
                n("som5", 5, "sh boucle.sh", re = "${SH}boucle\\.sh\\s*$"),
                n("som5", 6, "sh -x boucle.sh", re = "^(bash|sh)\\s+-x\\s+(\\./)?boucle\\.sh"),
                n("som5", 7, "sommet bug ?", fs = carnetOk("bug"), ou = null),
                n("som5", 8, "sed -i 's/totl=/total=/' boucle.sh && sh boucle.sh", fs = { j -> boucleOk(j) }),
                n("som5", 10, "sommet strace", re = "${SO}strace", ou = null),
            )),
            "som6" to Lecon("hist.som6.titre", null, 1, listOf(
                n("som6", 0, "sommet boussole", re = "${SO}boussole"),
                n("som6", 3, "sh boussole.sh --help", re = "${SH}boussole\\.sh\\s+(--help|-h)\\b"),
                n("som6", 4, "sh boussole.sh -c ? -p ?", fs = { j -> arriveeOk(j) }),
                n("som6", 5, "sommet arrivee ?", fs = carnetOk("arrivee"), ou = null),
                n("som6", 6, "grep --help | grep -- '-o'", re = "^grep\\s+--help\\s*\\|", ou = null, toutCode = true),
            )),
            "som7" to Lecon("hist.som7.titre", null, 1, listOf(
                n("som7", 0, "sommet ctf", re = "${SO}ctf\\s*$"),
                n("som7", 1, "grep -oE 'fragment1=[a-z]+' ctf/registre.log", re = "^grep\\b.*\\s-\\w*o.*registre\\.log"),
                n("som7", 2, "find ctf -name '*.frag' -print0 | xargs -0 cat", re = "^find\\s+ctf\\b.*-print0.*\\|\\s*xargs\\s+(-\\w+\\s+)*-0"),
                n("som7", 3, "sh ctf/porte.sh --help", re = "${SH}ctf/porte\\.sh\\s+(--help|-h)\\b"),
                n("som7", 4, "sh ctf/porte.sh -k ?", fs = { j -> (lire(j, "ctf/porte_ouverte.txt") ?: "").startsWith("fragment3=") }),
                n("som7", 5, "sommet drapeau ?", fs = carnetOk("drapeau"), ou = null),
                n("som7", 6, "sommet defi", re = "${SO}d[eé]fi\\b", ou = null),
                n("som7", 7, "badges grades", re = "^(tg\\s+)?badges\\s+grades?\\b", ou = null),
                n("som7", 8, "sommet records", re = "${SO}records?\\b", ou = null),
            )),
        )
    }

    // ---------------------------------------------------------------- les indices
    private val REPONSES = mapOf("sommet dates ?" to "dates", "sommet alertes ?" to "alertes", "sommet lourd ?" to "lourd",
        "sommet ligne ?" to "ligne", "sommet bug ?" to "bug", "sommet arrivee ?" to "arrivee", "sommet drapeau ?" to "drapeau")
    private val TROU = Regex("(^|\\s|/)(\\?|…|<[^>]*>)(\\s|/|$)")

    fun indice(jeu: Jeu, e: Etape, tapees: List<Pair<String, String?>>): String? {
        if (Histoire.leconCourante(jeu)?.id !in IDS) return null
        val lignes = tapees.map { it.first.trim() }
        val cmd = e.cmd
        if (lignes.any { Regex("^sudo\\b").containsMatchIn(it) }) return t("som.indice.sudo")
        if ("?" in cmd.split(" ") && lignes.any { (r(SO).containsMatchIn(it) || r(SH).containsMatchIn(it)) && TROU.containsMatchIn(it) }) return t("som.indice.trou")
        REPONSES[cmd]?.let { et ->
            val der = dernier(jeu, et)
            if (der != null && !der.trimEnd().endsWith("(ok)") && lignes.any { r(SO + et).containsMatchIn(it) }) return t("som.indice.rep.$et")
        }
        if ((r(SH).containsMatchIn(cmd) || " && sh " in cmd) && lignes.any { Regex("^\\./\\w+\\.sh").containsMatchIn(it) }) return t("som.indice.bash")
        if (cmd.startsWith("sh boussole.sh -c") && lignes.any { r("${SH}boussole\\.sh\\s*$").containsMatchIn(it) }) return t("som.indice.rep.arrivee")
        if ("-print0" in cmd && lignes.any { "xargs" in it && "-0" !in it }) return t("som.indice.zero")
        if (cmd.startsWith("sed -i '2i") && lignes.any { it.startsWith("sed") && "pipefail" in it && "-i" !in it }) return t("som.indice.sed_i")
        return null
    }

    // ---------------------------------------------------------------- les 3 niveaux d'indice (idée 25, AideDouce.kt)
    val INDICES = listOf("dates", "alertes", "lourd", "ligne", "bug", "arrivee", "drapeau", "boussole", "porte")

    /** L'étape à trou (« ? ») d'une commande de leçon (= sommet.trou_de). */
    fun trouDe(cmd: String?): String? {
        val c = (cmd ?: "").trim().split(Regex("\\s+")).filter { it.isNotEmpty() }.joinToString(" ")
        REPONSES[c]?.let { return it }
        if (Regex("^(bash|sh) boussole\\.sh -c \\? -p \\?$").matches(c)) return "boussole"
        if (Regex("^(bash|sh) ctf/porte\\.sh -k \\?$").matches(c)) return "porte"
        return null
    }

    /** La réponse complète (3e niveau), telle que l'enfant la taperait (= sommet.reponse_indice). */
    fun reponseIndice(graine: String, et: String, sh: String = "bash"): String? {
        val (cap, pas) = mission(graine)
        return when (et) {
            "dates" -> "sommet dates ${dates(graine).size}"
            "alertes" -> "sommet alertes ${alertes(graine).size}"
            "lourd" -> "sommet lourd ${plusLourde(graine)}"
            "ligne" -> "sommet ligne ${o("casse").optJSONArray("signale")?.let { it.get(it.length() - 1) } ?: 8}"
            "bug" -> "sommet bug ${o("boucle").optString("faute")}"
            "arrivee" -> "sommet arrivee ${lieu(graine, cap, pas)}"
            "drapeau" -> "sommet drapeau ${drapeau(graine)}"
            "boussole" -> "$sh boussole.sh -c $cap -p $pas"
            "porte" -> "$sh ctf/porte.sh -k ${fragments(graine)[0]}"
            else -> null
        }
    }

    /** La commande montrée au 2e niveau (= sommet.commande_indice). */
    fun commandeIndice(et: String, sh: String = "bash"): String = when (et) {
        "dates" -> "grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' journal.log | sort -u | wc -l"
        "alertes" -> "wc -l alertes.txt"
        "lourd" -> "find eboulis -type f -print0 | xargs -0 wc -c | sort -nr | head -6"
        "ligne" -> "$sh -n casse.sh"
        "bug" -> "$sh -x boucle.sh"
        "arrivee" -> "cat arrivee.txt"
        "drapeau" -> "sommet drapeau TG{fragment1-fragment2-fragment3}"
        "boussole" -> "$sh boussole.sh -c CAP -p PAS"
        else -> "grep -oE 'fragment1=[a-z]+' ctf/registre.log"
    }

    /** (clé, réponse, « sommet:<étape> ») quand la leçon du Sommet attend une réponse à trou. */
    fun cibleIndice(jeu: Jeu): Triple<String, String, String>? {
        val l = Histoire.leconCourante(jeu) ?: return null
        if (l.id !in IDS || jeu.niveau < l.niveau) return null
        val et = trouDe(l.etapes.getOrNull(jeu.etape)?.cmd) ?: return null
        val r = reponseIndice(graine(jeu), et, "sh") ?: return null
        return Triple("som:${l.id}:${jeu.etape}", r, "sommet:$et")
    }

    fun texteIndice(et: String, n: Int, reponse: String, sh: String = "sh"): String = when (n) {
        1 -> t("ad.ind.som.$et.1")
        2 -> t("ad.ind.som.$et.2", "cmd" to "`${commandeIndice(et, sh)}`")
        else -> t("ad.ind.n3", "cmd" to "`$reponse`")
    }

    // ---------------------------------------------------------------- les commandes du jeu
    private fun bloc(cle: String, vararg p: Pair<String, Any?>) = t(cle, *p).split("\n").map { "  $it" }
    val MONTAGNE = listOf("      /\\      ⛰", "     /  \\  /\\", " /\\ / ▲▲ \\/  \\", "/  \\/▲▲▲▲ \\   \\")

    private fun reponse(jeu: Jeu, et: String, arg: String?, justes: List<String>, cleOk: String, vararg p: Pair<String, Any?>): List<String> {
        if (arg == null) return listOf(t("som.$et.aide"))
        val rr = asciiId(arg.trim())
        if (rr in justes.map { asciiId(it) }) { noter(jeu, et, "${rr.take(24)} (ok)"); return listOf("✔ " + t(cleOk, *p)) }
        noter(jeu, et, "${rr.take(24)} (faux)")
        return listOf("✖ " + t("som.indice.rep.$et"))
    }
    private fun duree(s: Double): String { val x = Math.round(s); return "${x / 60} min ${"%02d".format(x % 60)} s" }

    /** sommet [plan|fragile|bivouac|journal|dates|alertes|eboulis|lourd|casse|ligne|bug|strace|boussole|sections|arrivee|ctf|drapeau|defi|records] */
    fun commande(jeu: Jeu, reste: String, ici: File): String {
        val m = reste.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        val sous = asciiId(m.getOrNull(0) ?: "aide")
        val a = m.drop(1).filter { it != "?" && it != "…" }
        val arg = a.joinToString(" ").ifEmpty { null }
        etat(jeu)
        val g = graine(jeu)
        val l: List<String> = when {
            sous in setOf("plan", "refuge", "regles") -> MONTAGNE + t("som.meuble.refuge").split("\n") + "" + manque(jeu)
            !ouvert(jeu) && sous != "aide" -> listOf("✋ " + t("som.ferme")) + manque(jeu)
            sous == "fragile" -> {
                if (!File(dossier(jeu), "fragile.sh").exists() || !dansCarnet(jeu, "fragile")) {
                    ecrire(jeu, "fragile.sh", script("fragile", "sh")); ecrire(jeu, "carnet de bord.txt", t("som.carnet_de_bord") + "\n")
                    File(dossier(jeu), "coffre").mkdirs()
                }
                noter(jeu, "fragile", "pose (ok)"); listOf("🪢 " + t("som.fragile.titre"), "") + bloc("som.fragile.texte") + listOf("", "  " + t("som.tel.sh"))
            }
            sous == "bivouac" -> { for (s in listOf("sale", "bivouac")) ecrire(jeu, "$s.sh", script(s, "sh")); noter(jeu, "bivouac", "pose (ok)")
                listOf("⛺ " + t("som.bivouac.titre"), "") + bloc("som.bivouac.texte") }
            sous == "journal" -> { ecrire(jeu, "journal.log", journalTexte(g)); noter(jeu, "journal", "pose (ok)")
                listOf("📜 " + t("som.journal.titre"), "") + bloc("som.journal.texte") }
            sous == "dates" -> reponse(jeu, "dates", arg, listOf("${dates(g).size}"), "som.dates.ok", "n" to dates(g).size, "lignes" to lignesDatees(g).size)
            sous == "alertes" -> reponse(jeu, "alertes", arg, listOf("${alertes(g).size}"), "som.alertes.ok", "n" to alertes(g).size, "partout" to alertesPartout(g).size)
            sous == "eboulis" -> {
                File(dossier(jeu), "eboulis").deleteRecursively()
                for ((rel, v) in eboulis(g)) ecrire(jeu, "eboulis/$rel", contenuPierre(v.first, v.second))
                noter(jeu, "eboulis", "pose (ok)"); listOf("🪨 " + t("som.eboulis.titre"), "") + bloc("som.eboulis.texte")
            }
            sous == "lourd" -> { val p = plusLourde(g); reponse(jeu, "lourd", arg, listOf(p, "$p.txt"), "som.lourd.ok", "nom" to p, "taille" to plusLourds(g, 1)[0].first) }
            sous == "casse" -> { for (s in listOf("casse", "boucle")) ecrire(jeu, "$s.sh", script(s, "sh")); noter(jeu, "casse", "pose (ok)")
                listOf("🩹 " + t("som.casse.titre"), "") + bloc("som.casse.texte") + listOf("", "  " + t("som.tel.raconte", "outil" to "shellcheck")) }
            sous == "ligne" -> reponse(jeu, "ligne", arg, liste(o("casse"), "signale"), "som.ligne.ok", "ligne" to o("casse").optInt("ligne"))
            sous == "bug" -> { val f = o("boucle").optString("faute"); reponse(jeu, "bug", arg, listOf(f, "\$$f"), "som.bug.ok", "juste" to o("boucle").optInt("juste")) }
            sous == "strace" -> { noter(jeu, "strace", "lu (ok)"); listOf("🔬 " + t("som.strace.titre"), "") + bloc("som.strace.texte") }
            sous == "boussole" -> {
                val (cap, pas) = mission(g)
                ecrire(jeu, "boussole.sh", scriptBoussole(g, "sh")); File(dossier(jeu), "arrivee.txt").delete()
                noter(jeu, "boussole", "$cap $pas ${lieu(g, cap, pas)} pose (ok)")
                listOf("🧭 " + t("som.boussole.titre"), "") + bloc("som.boussole.texte", "cap" to cap, "pas" to pas) +
                    listOf("", "  " + t("som.tel.raconte", "outil" to "man, apropos")) + bloc("som.sections.texte")
            }
            sous == "sections" -> bloc("som.sections.texte")
            sous == "arrivee" -> { val (cap, pas) = mission(g); reponse(jeu, "arrivee", arg, listOf(lieu(g, cap, pas)), "som.arrivee.ok", "lieu" to lieu(g, cap, pas)) }
            sous == "ctf" -> {
                File(dossier(jeu), "ctf").deleteRecursively()
                for ((rel, x) in fichiersCtf(g, "sh")) ecrire(jeu, rel, x)
                etat(jeu).put("ctf_debut", Entrainement.maintenant())
                noter(jeu, "ctf", "pose (ok)")
                listOf("🚩 " + t("som.ctf.titre"), "") + bloc("som.ctf.texte", "mondes" to (mondesAuPalier(jeu).joinToString(", ") { Histoire.nomChapitre(it.second) }.ifEmpty { "—" }))
            }
            sous == "drapeau" -> when {
                arg == null -> listOf(t("som.drapeau.aide"))
                !drapeauOk(g, arg) -> { noter(jeu, "drapeau", "${arg.trim().take(40)} (faux)"); listOf("✖ " + t("som.indice.rep.drapeau")) }
                else -> {
                    val s = etat(jeu)
                    val out = mutableListOf("✔ " + t("som.drapeau.ok", "drapeau" to drapeau(g)))
                    if (s.has("ctf_debut")) {
                        val du = maxOf(1.0, (Entrainement.maintenant() - s.optLong("ctf_debut")) / 1000.0)
                        if (!s.has("record_ctf") || du < s.optDouble("record_ctf")) s.put("record_ctf", Math.round(du * 10) / 10.0)
                        out.add("  " + t("som.drapeau.chrono", "temps" to duree(du), "record" to duree(s.optDouble("record_ctf"))))
                        s.remove("ctf_debut")
                    }
                    noter(jeu, "drapeau", "${drapeau(g)} (ok)")
                    if (ouvert(jeu)) Recompenses.exploit(jeu, "sommet.trois_mondes")?.let { jeu.log(it); jeu.dire(it, 16); out.add(it) }
                    out
                }
            }
            sous == "defi" || sous == "defis" -> {
                val (types, verifiee) = defiDuJour(jeu)
                if (types.isEmpty()) listOf(t("som.defi.aucun", "cmd" to "`entrainement`"))
                else if (arg?.trim()?.toIntOrNull()?.let { it in 1..types.size } == true) listOf(Entrainement.commencer(jeu, null, types[arg.trim().toInt() - 1]))
                else {
                    val f = defiFaits(jeu)
                    val out = mutableListOf("🏔 " + t("som.defi.titre", "jour" to jourLocal()), "")
                    types.forEachIndexed { i, typ -> out.add("  ${i + 1}. " + (if (f.has(typ)) "✔ " else "… ") + t("ent.type.$typ.titre") + "  (sommet defi ${i + 1})") }
                    out += listOf("", "  " + t("som.defi.regle"), "  " + t(if (verifiee) "som.defi.verifie" else "som.defi.local"))
                    if (types.all { f.has(it) }) { if (!dansCarnet(jeu, "defi_${jourLocal()}")) noter(jeu, "defi_${jourLocal()}", "reussi (ok)"); out.add("🏅 " + t("som.defi.reussi")) }
                    out
                }
            }
            sous == "records" || sous == "record" -> {
                val s = etat(jeu); val e = Entrainement.e(jeu).optJSONObject("records") ?: JSONObject()
                val v = e.keys().asSequence().count { e.optJSONObject(it)?.optBoolean("v") == true }
                noter(jeu, "records", "lu (ok)")
                listOf("⏱ " + t("som.records.titre"), "",
                    "  " + (if (s.has("record_ctf")) t("som.records.ctf", "temps" to duree(s.optDouble("record_ctf"))) else t("som.records.ctf_aucun")),
                    "  " + t("som.records.salle", "n" to e.length(), "v" to v, "cmd" to "`badges records`"),
                    "  " + t("som.records.grades", "cmd" to "`badges grades`"))
            }
            else -> MONTAGNE + listOf("⛰ " + t("som.aide.titre")) + t("som.aide.liste").split("\n").map { "  $it" } +
                (if (!ouvert(jeu)) listOf("") + manque(jeu) else emptyList())
        }
        return l.joinToString("\n")
    }
}
