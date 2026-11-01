package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.text.Normalizer
import java.util.Locale

/**
 * 🔭 L'Observatoire de l'IA (docs/programme.md § 2.17 et § 7.4), portage de pc/tg/observatoire.py.
 *
 * AUCUNE VRAIE IA : l'assistant, le devineur de type, le devineur de mots et les agents sont de petits programmes du jeu,
 * déterministes, hors ligne (aucun réseau, aucun compte, aucune clé). Ils n'agissent que dans le terrain
 * (terrain_terminagotchi/observatoire). Une action dangereuse proposée par un agent fictif (rm -rf, sudo) est du TEXTE à
 * refuser : l'appli ne l'exécute jamais, même acceptée.
 *
 * Mêmes règles que sur PC (les jeux de données relus dans le vrai bestiaire, le devineur qui compte, le texte du devineur
 * de mots fait des vraies phrases de l'histoire, ses paires et ses phrases tirées, ce que l'assistant comprend d'une
 * consigne, son tri qui oublie une ligne, les propositions des agents, les 2 réponses fausses sur 5, les quiz mélangés
 * comme random.shuffle de Python, la lunette de la vue déployée) : vecteurs communs donnees/observatoire/vecteurs.json,
 * vérifiés par tests/jvm/Observatoire.kt. Sur le téléphone : pas de git (diff à la place), pas de Ctrl+C (agent stop),
 * chaque ligne a son propre terminal (export et echo sur la même ligne), cut à la place d'awk.
 */
object Observatoire {
    @Volatile var chargeur: (() -> String?)? = null
    private var d: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("observatoire.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun donnees(): JSONObject = d ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() }).also { d = it }

    private fun liste(o: JSONObject?, k: String): List<String> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.get(it).toString() } } ?: emptyList()
    private fun objets(o: JSONObject?, k: String): List<JSONObject> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.getJSONObject(it) } } ?: emptyList()
    private fun hex(b: ByteArray) = b.joinToString("") { "%02x".format(it) }
    private fun sha(s: String) = hex(MessageDigest.getInstance("SHA-256").digest(s.toByteArray(Charsets.UTF_8)))
    private fun o(k: String) = donnees().optJSONObject(k) ?: JSONObject()

    // ================================================================ la spécification pure (vecteurs communs)
    fun asciiBas(texte: String?): String = Normalizer.normalize(texte ?: "", Normalizer.Form.NFKD)
        .filter { Character.getType(it) != Character.NON_SPACING_MARK.toInt() }.lowercase()

    private fun <T> melange(graine: String, sel: String, l: List<T>): List<T> = l.toMutableList().also { PyHasard("$sel:$graine").melanger(it) }
    fun tire(graine: String, sel: String, n: Int) = (sha("$graine:$sel").substring(0, 8).toLong(16) % n).toInt()

    fun cjk(cp: Int): Boolean {
        val a = donnees().optJSONArray("cjk") ?: return false
        return (0 until a.length()).any { val r = a.getJSONArray(it); cp >= r.getInt(0) && cp <= r.getInt(1) }
    }

    private val COUPE = setOf(Character.CONNECTOR_PUNCTUATION, Character.DASH_PUNCTUATION, Character.START_PUNCTUATION,
        Character.END_PUNCTUATION, Character.INITIAL_QUOTE_PUNCTUATION, Character.FINAL_QUOTE_PUNCTUATION, Character.OTHER_PUNCTUATION,
        Character.MATH_SYMBOL, Character.CURRENCY_SYMBOL, Character.MODIFIER_SYMBOL, Character.OTHER_SYMBOL,
        Character.SPACE_SEPARATOR, Character.LINE_SEPARATOR, Character.PARAGRAPH_SEPARATOR,
        Character.CONTROL, Character.FORMAT, Character.PRIVATE_USE, Character.SURROGATE, Character.UNASSIGNED).map { it.toInt() }.toSet()

    /** Les mots d'un texte comme le devineur de mots les voit (minuscules, ponctuation et symboles → espaces ; en chinois et
     *  en japonais, un caractère = un mot). */
    fun nettoyer(texte: String?): List<String> {
        val sb = StringBuilder()
        val s = (texte ?: "").lowercase(Locale.ROOT)
        var i = 0
        while (i < s.length) {
            val cp = s.codePointAt(i)
            when {
                Character.getType(cp) in COUPE -> sb.append(' ')
                cjk(cp) -> { sb.append(' '); sb.appendCodePoint(cp); sb.append(' ') }
                else -> sb.appendCodePoint(cp)
            }
            i += Character.charCount(cp)
        }
        return sb.toString().split(' ').filter { it.isNotEmpty() }
    }

    fun sansChamps(texte: String?): String = (texte ?: "").replace(Regex("\\{[^{}]*\\}"), " ")

    fun corpusLignes(code: String = Langue.courante): List<String> = liste(donnees(), "corpus").mapNotNull { k ->
        val v = Langue.brut(k, code)
        val s = if (v is JSONArray) v.optString(0) else v?.toString() ?: ""
        nettoyer(sansChamps(s)).takeIf { it.isNotEmpty() }?.joinToString(" ")
    }

    fun motsDe(texte: String?): List<String> = (texte ?: "").split(Regex("[ \n]+")).filter { it.isNotEmpty() }

    fun effectifs(mots: List<String>): List<Pair<String, Int>> {
        val c = LinkedHashMap<String, Int>()
        for (m in mots) c[m] = (c[m] ?: 0) + 1
        return c.entries.map { it.key to it.value }.sortedWith(compareBy({ -it.second }, { it.first }))
    }

    fun paires(mots: List<String>): Map<String, Map<String, Int>> {
        val p = LinkedHashMap<String, LinkedHashMap<String, Int>>()
        for (k in 0 until mots.size - 1) { val d = p.getOrPut(mots[k]) { LinkedHashMap() }; d[mots[k + 1]] = (d[mots[k + 1]] ?: 0) + 1 }
        return p
    }

    fun topPaires(mots: List<String>): List<Triple<String, String, Int>> =
        paires(mots).flatMap { (a, d) -> d.map { (b, n) -> Triple(a, b, n) } }.sortedWith(compareBy({ -it.third }, { it.first }, { it.second }))

    fun suite(table: Map<String, Map<String, Int>>, mot: String): List<Pair<String, Int>> =
        (table[mot] ?: emptyMap()).entries.map { it.key to it.value }.sortedWith(compareBy({ -it.second }, { it.first }))

    fun phrase(table: Map<String, Map<String, Int>>, debut: String, graine: String, n: Int, longueur: Int = donnees().optInt("phrase_mots", 8)): List<String> {
        val out = mutableListOf(debut)
        for (k in 0 until longueur - 1) {
            val s = suite(table, out.last())
            if (s.isEmpty()) break
            var r = tire(graine, "phrase:$n:$k", s.sumOf { it.second })
            for ((m, x) in s) { if (r < x) { out.add(m); break }; r -= x }
        }
        return out
    }

    // ---------------------------------------------------------------- les créatures (O1, O2, O5, O6)
    private val C get() = o("creatures")
    /** Un mot de données (famille, lieu, type, réponse) : sans les marques de sens d'écriture que t() ajoute en arabe et en ourdou. */
    fun mot(cle: String): String = t(cle).replace(Regex("[\u200E\u200F\u2066-\u2069]"), "").trim().replace(" ", "_").ifEmpty { cle }
    fun label(feu: Boolean) = mot(if (feu) "ob.label.feu" else "ob.label.pas_feu")

    fun ligneCreature(cid: String, avecReponse: Boolean = true): String {
        val c = C.optJSONObject(cid) ?: return ""
        val l = mutableListOf(c.optString("nom"), mot("ob.famille." + c.optString("famille")), mot("ob.lieu." + c.optString("lieu")))
        if (avecReponse) l.add(label(c.optString("type") == "feu"))
        return l.joinToString(" ")
    }

    fun texteCreatures(ids: List<String>, avecReponse: Boolean = true) = ids.joinToString("") { ligneCreature(it, avecReponse) + "\n" }
    fun texteTypes() = liste(donnees(), "exemples").joinToString("") { val c = C.getJSONObject(it); "${c.optString("nom")} ${mot("ob.type." + c.optString("type"))}\n" }

    fun estFeu(motRep: String?): Boolean? {
        val m = asciiBas((motRep ?: "").trim())
        for (code in listOf(Langue.courante, "fr").distinct()) {
            if (m == asciiBas((Langue.brut("ob.label.feu", code)?.toString() ?: "").replace(" ", "_"))) return true
            if (m == asciiBas((Langue.brut("ob.label.pas_feu", code)?.toString() ?: "").replace(" ", "_"))) return false
        }
        return null
    }

    /** Le cerveau du devineur : {"total": [feu, pas], "famille": {v: [feu, pas]}, "lieu": {…}, "n": exemples} */
    fun apprendre(texte: String?): JSONObject {
        val tot = intArrayOf(0, 0)
        val fam = LinkedHashMap<String, IntArray>(); val lieu = LinkedHashMap<String, IntArray>()
        var n = 0
        for (ligne in (texte ?: "").split("\n")) {
            val c = ligne.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
            if (c.size < 4 || ligne.trimStart().startsWith("#")) continue
            val f = estFeu(c[3]) ?: continue
            val k = if (f) 0 else 1
            n++; tot[k]++
            fam.getOrPut(c[1]) { intArrayOf(0, 0) }[k]++
            lieu.getOrPut(c[2]) { intArrayOf(0, 0) }[k]++
        }
        fun obj(m: Map<String, IntArray>) = JSONObject().also { o -> m.forEach { (v, a) -> o.put(v, JSONArray().put(a[0]).put(a[1])) } }
        return JSONObject().put("total", JSONArray().put(tot[0]).put(tot[1])).put("famille", obj(fam)).put("lieu", obj(lieu)).put("n", n)
    }

    private fun compte(m: JSONObject, nom: String, v: String, k: Int) = m.optJSONObject(nom)?.optJSONArray(v)?.optInt(k) ?: 0

    /** (Feu ?, votes Feu, votes pas Feu) */
    fun deviner(m: JSONObject, famille: String, lieu: String): Triple<Boolean, Int, Int> {
        val vf = compte(m, "famille", famille, 0) + compte(m, "lieu", lieu, 0)
        val vp = compte(m, "famille", famille, 1) + compte(m, "lieu", lieu, 1)
        if (vf != vp) return Triple(vf > vp, vf, vp)
        val t = m.optJSONArray("total")
        return Triple((t?.optInt(0) ?: 0) > (t?.optInt(1) ?: 0), vf, vp)
    }

    fun cerveauLignes(m: JSONObject, fichier: String): List<String> {
        val out = mutableListOf("# " + t("ob.cerveau.titre", "fichier" to fichier, "n" to m.optInt("n")), "# " + t("ob.cerveau.vraies"), "")
        val lf = label(true); val lp = label(false)
        for (nom in listOf("famille", "lieu")) {
            val o = m.optJSONObject(nom) ?: continue
            for (v in o.keys().asSequence().toList().sorted()) {
                val a = o.getJSONArray(v)
                out.add("${mot("ob.mot.$nom").padEnd(10)} ${v.padEnd(16)} $lf ${a.getInt(0).toString().padEnd(3)} $lp ${a.getInt(1)}")
            }
        }
        val t0 = m.optJSONArray("total")
        out += listOf("", "${mot("ob.mot.total").padEnd(10)} ${"".padEnd(16)} $lf ${(t0?.optInt(0) ?: 0).toString().padEnd(3)} $lp ${t0?.optInt(1) ?: 0}")
        return out
    }

    fun nombresDuCerveau(m: JSONObject) = 2 * ((m.optJSONObject("famille")?.length() ?: 0) + (m.optJSONObject("lieu")?.length() ?: 0) + 1)

    fun vraiType(nom: String): String? = C.keys().asSequence().map { C.getJSONObject(it) }.firstOrNull { asciiBas(it.optString("nom")) == asciiBas(nom) }?.optString("type")

    class Essai(val nom: String, val famille: String, val lieu: String, val devine: Boolean, val vrai: Boolean?, val vf: Int, val vp: Int)

    fun tester(m: JSONObject, texte: String?): List<Essai> {
        val out = mutableListOf<Essai>()
        for (ligne in (texte ?: "").split("\n")) {
            val c = ligne.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
            if (c.size < 3 || ligne.trimStart().startsWith("#")) continue
            val (d, vf, vp) = deviner(m, c[1], c[2])
            var v = if (c.size > 3) estFeu(c[3]) else null
            if (v == null) v = vraiType(c[0])?.let { it == "feu" }
            out.add(Essai(c[0], c[1], c[2], d, v, vf, vp))
        }
        return out
    }

    // ---------------------------------------------------------------- O1, O2 : l'assistant
    val VERBES = listOf("compter", "trier", "lister")

    private fun motsCle(cle: String): List<String> = listOf(Langue.courante, "fr").distinct()
        .flatMap { code -> (Langue.brut(cle, code)?.toString() ?: "").split(Regex("\\s+")).filter { it.isNotEmpty() }.map { asciiBas(it) } }

    class Analyse(val verbe: String?, val fichier: String?, val filtre: String?, val manque: List<String>)

    fun analyser(texte: String?, fichiers: List<String>, valeursDe: (String) -> List<String>): Analyse {
        val toks = nettoyer(asciiBas(texte))
        val colle = toks.joinToString("")
        fun aCjk(w: String) = w.codePoints().anyMatch { cjk(it) }
        val verbe = VERBES.firstOrNull { v -> motsCle("ob.mot.$v").any { w -> w in toks || (w.length > 1 && aCjk(w) && colle.contains(w)) } }
        val noms = Regex("[A-Za-z0-9_.-]+\\.txt").findAll(texte ?: "").map { it.value }.toList()
        val fichier = noms.firstOrNull { it in fichiers && !it.startsWith("mission") }
        var filtre: String? = null
        if (fichier != null) for (v in valeursDe(fichier)) { val w = asciiBas(v); if (w in toks || (aCjk(w) && colle.contains(w))) { filtre = v; break } }
        val manque = mutableListOf<String>()
        if (verbe == null) manque.add("quoi")
        if (fichier == null) manque.add("fichier")
        if ((verbe == "compter" || verbe == "lister") && fichier != null && filtre == null) manque.add("filtre")
        return Analyse(verbe, fichier, filtre, manque)
    }

    fun oubli(graine: String, n: Int = 20) = tire(graine, "oubli", n)

    fun trierAssistant(lignes: List<String>, graine: String): Pair<List<String>, String?> {
        val l2 = lignes.filter { it.isNotBlank() }.sorted()
        if (l2.isEmpty()) return emptyList<String>() to null
        val i = oubli(graine, l2.size)
        return (l2.take(i) + l2.drop(i + 1)) to l2[i]
    }

    fun faireMission(a: Analyse, lignesFichier: List<String>, graine: String): Pair<List<String>, String?> {
        if (a.verbe == "trier") return trierAssistant(lignesFichier, graine)
        val cible = asciiBas(a.filtre ?: "")
        val trouvees = lignesFichier.filter { x -> x.isNotBlank() && cible in x.trim().split(Regex("\\s+")).map { asciiBas(it) } }
        if (a.verbe == "compter") return listOf(t("ob.assistant.compte", "fichier" to a.fichier, "n" to trouvees.size, "filtre" to a.filtre)) to null
        return trouvees to null
    }

    // ---------------------------------------------------------------- O4, O9 : les propositions des agents
    class Prop(val n: Int, val id: String, val sur: Boolean, val texte: String)

    fun propositions(graine: String, cle: String = "agent"): List<Prop> {
        val base = if (cle == "agent") objets(o("agent"), "propositions") else objets(o("equipe"), "propositions")
        return melange(graine, "prop:$cle", base).mapIndexed { i, x -> Prop(i + 1, x.optString("id"), x.optBoolean("sur"), x.optString("texte")) }
    }

    fun dangereuse(graine: String, cle: String = "agent") = propositions(graine, cle).first { !it.sur }.n
    fun listeRangee(l: List<String>) = l.distinct().sorted()

    // ---------------------------------------------------------------- les cartes des quiz
    class Carte(val n: Int, val id: String, val rep: String)

    private fun cartes(graine: String, sel: String, base: List<JSONObject>) = melange(graine, sel, base).mapIndexed { i, x ->
        val r = x.opt("rep"); Carte(i + 1, x.optString("id"), if (r is Boolean) r.toString() else r.toString()) }

    private fun obj(id: String, rep: String) = JSONObject().put("id", id).put("rep", rep)
    val PERROQUET = listOf(obj("frequent", "v"), obj("verifie", "f"), obj("invente", "v"))
    val BIAIS = listOf(obj("exemples", "o"), obj("mechant", "n"), obj("puissance", "n"))

    fun confierCartes(graine: String) = cartes(graine, "confier", objets(donnees(), "confier"))
    fun nuancesCartes(graine: String) = cartes(graine, "nuances", objets(donnees(), "nuances"))
    fun perroquetCartes(graine: String) = cartes(graine, "perroquet", PERROQUET)
    fun biaisCartes(graine: String) = cartes(graine, "biais", BIAIS)
    fun consigneCartes(graine: String) = cartes(graine, "consigne", objets(o("equipe"), "consignes")).map { Carte(0, it.id, it.rep).let { c -> Triple((96 + it.n).toChar().toString(), c.id, c.rep) } }
    fun decoupeCartes(graine: String): List<Pair<Int, String>> = melange(graine, "decoupe", liste(o("equipe"), "decoupe")).mapIndexed { i, x -> (i + 1) to x }
    fun decoupeReponse(graine: String): List<String> { val c = decoupeCartes(graine).associate { it.second to it.first }; return liste(o("equipe"), "decoupe").map { "${c[it]}" } }

    fun quizJustes(cartes: List<Carte>, rep: List<String>, lettres: String): Pair<Boolean, List<Carte>> {
        val r = rep.map { asciiBas(it).take(1) }
        if (r.size != cartes.size || r.any { it.isEmpty() || it[0] !in lettres }) return false to emptyList()
        return true to cartes.zip(r).filter { it.first.rep == it.second }.map { it.first }
    }

    class Question(val n: Int, val id: String, val fausse: Boolean)

    fun questions(graine: String): List<Question> {
        val q = objets(donnees(), "questions")
        val fausses = melange(graine, "fausses", q.indices.toList()).take(donnees().optInt("fausses", 2)).toSet()
        return q.mapIndexed { i, x -> Question(i + 1, x.optString("id"), i in fausses) }
    }

    /** (toutes trouvées ?, justes, en trop) */
    fun faussesOk(rep: List<String>, graine: String): Triple<Boolean, Int, Int> {
        val vraies = questions(graine).filter { it.fausse }.map { it.n }.toSet()
        val dn = rep.mapNotNull { it.trim().toIntOrNull() }.toSet()
        return Triple(dn == vraies, (dn intersect vraies).size, (dn - vraies).size)
    }

    // ---------------------------------------------------------------- la lunette (vue déployée)
    private val SEPARATEURS = Regex("\\|\\||&&|[|;&]")

    fun lunetteDe(morceau: String?): Triple<String, String, String>? {
        val m = (morceau ?: "").trim()
        for (r in objets(o("lunette"), "regles")) if (Regex(r.optString("motif")).containsMatchIn(m)) return Triple(r.optString("outil"), r.optString("de"), r.optString("vers"))
        return null
    }

    fun lunettesDe(ligne: String?): List<Triple<String, String, String>> = (ligne ?: "").split(SEPARATEURS).mapNotNull { lunetteDe(it) }

    // ================================================================ l'état, le terrain, le carnet de l'observatoire
    fun etat(jeu: Jeu): JSONObject {
        val c = jeu.module("observatoire")
        if (c.optJSONArray("faits") == null) c.put("faits", JSONArray())
        return c
    }

    private fun fait(jeu: Jeu, cle: String): Boolean {
        if (cle in liste(etat(jeu), "faits")) return true
        etat(jeu).getJSONArray("faits").put(cle)
        return false
    }

    const val CARNET = "carnet_de_l_observatoire.txt"
    fun dossier(jeu: Jeu) = File(jeu.terrain, "observatoire")
    fun noter(jeu: Jeu, etiquette: String, texte: String) {
        try { dossier(jeu).mkdirs(); File(dossier(jeu), CARNET).appendText("[$etiquette] $texte\n") } catch (e: Exception) { }
    }
    fun carnet(jeu: Jeu): String = try { File(dossier(jeu), CARNET).readText() } catch (e: Exception) { "" }
    fun dansCarnet(jeu: Jeu, etiquette: String, motCle: String = "ok") =
        Regex("^\\[$etiquette].*\\($motCle\\)\\s*$", RegexOption.MULTILINE).containsMatchIn(carnet(jeu))
    fun dernier(jeu: Jeu, etiquette: String): String? = carnet(jeu).lines().lastOrNull { it.startsWith("[$etiquette]") }

    private fun ecrire(jeu: Jeu, rel: String, contenu: String) = Histoire.ecrire(jeu, "observatoire/$rel", contenu, finLigne = false)
    private fun lire(jeu: Jeu, rel: String): String? = Histoire.lire(jeu, "observatoire/$rel")

    fun testSh(): String = "#!/bin/sh\n# " + t("ob.test.titre") + "\n" +
        "attendu=\$(wc -l < creatures.txt | tr -d ' ')\nobtenu=\$(wc -l < tri.txt | tr -d ' ')\n" +
        "if [ \"\$attendu\" = \"\$obtenu\" ] && [ \"\$(sort creatures.txt)\" = \"\$(cat tri.txt)\" ]; then\n" +
        "  echo \"✔ ${t("ob.test.reussi")}\"\nelse\n" +
        "  echo \"✖ ${t("ob.test.echec", "obtenu" to "\$obtenu", "attendu" to "\$attendu")}\"\n  exit 1\nfi\n"

    fun testsSh(): String = "#!/bin/sh\n# " + t("ob.tests.titre") + "\nr=0\n" +
        "n=\$(wc -l < liste.txt | tr -d ' ')\n" +
        "if [ \"\$(cat compte.txt 2>/dev/null)\" = \"\$n\" ]; then echo \"✔ ${t("ob.tests.compte_ok")}\"; " +
        "else echo \"✖ ${t("ob.tests.compte_ko", "n" to "\$n")}\"; r=1; fi\n" +
        "if [ \"\$(ls invitations | wc -l | tr -d ' ')\" = \"\$n\" ]; then echo \"✔ ${t("ob.tests.invitations_ok")}\"; " +
        "else echo \"✖ ${t("ob.tests.invitations_ko")}\"; r=1; fi\n" +
        "if [ -e STOP ]; then echo \"✔ ${t("ob.tests.stop_ok")}\"; else echo \"✖ ${t("ob.tests.stop_ko")}\"; r=1; fi\n" +
        "exit \$r\n"

    fun configPartagee(): String {
        val s = o("secret")
        return listOf("# " + t("ob.config.titre"), "ville=Terminaville", "langue=" + Langue.courante,
            "${s.optString("variable")}=${s.optString("cle")}", "couleur=bleu").joinToString("\n") + "\n"
    }

    fun meubles(jeu: Jeu): Map<String, Any> = linkedMapOf(
        "observatoire/coupole.txt" to t("ob.meuble.coupole", "nom" to jeu.nom) + "\n",
        "observatoire/$CARNET" to t("ob.meuble.carnet") + "\n",
        "observatoire/missions/creatures.txt" to texteTypes(),
        "observatoire/missions/mission_floue.txt" to t("ob.mission.floue") + "\n")

    private fun executable(f: File) = try { f.setExecutable(true) } catch (e: Exception) { false }

    fun poserVerifier(jeu: Jeu) {
        ecrire(jeu, "missions/mission_tri.txt", t("ob.mission.tri") + "\n")
        ecrire(jeu, "missions/test.sh", testSh()); executable(File(dossier(jeu), "missions/test.sh"))
    }
    fun poserSecrets(jeu: Jeu) { ecrire(jeu, "secrets/config_partagee.txt", configPartagee()); ecrire(jeu, "secrets/LISEZMOI.txt", t("ob.meuble.secrets") + "\n") }
    fun poserChantier(jeu: Jeu) {
        if (File(dossier(jeu), "chantier/a_nourrir.txt").exists()) return
        val l = liste(o("agent"), "liste").joinToString("") { "$it\n" }
        ecrire(jeu, "chantier/a_nourrir.txt", l); ecrire(jeu, "chantier/.avant/a_nourrir.txt", l)
        ecrire(jeu, "chantier/LISEZMOI.txt", t("ob.meuble.chantier") + "\n")
    }
    fun poserDevineur(jeu: Jeu) {
        ecrire(jeu, "devineur/exemples.txt", texteCreatures(liste(donnees(), "exemples")))
        ecrire(jeu, "devineur/nouvelle.txt", texteCreatures(listOf(donnees().optString("piege")), false))
    }
    fun poserBiais(jeu: Jeu) {
        ecrire(jeu, "devineur/volcan.txt", texteCreatures(liste(donnees(), "volcan")))
        ecrire(jeu, "devineur/autres.txt", texteCreatures(liste(donnees(), "autres")))
    }
    fun poserMots(jeu: Jeu) { ecrire(jeu, "mots/histoire.txt", corpusLignes().joinToString("") { "$it\n" }); ecrire(jeu, "mots/LISEZMOI.txt", t("ob.meuble.mots") + "\n") }
    fun poserEquipe(jeu: Jeu) {
        ecrire(jeu, "equipe/grande_tache.txt", t("ob.meuble.tache") + "\n")
        ecrire(jeu, "equipe/invites.txt", liste(o("equipe"), "invites").joinToString("") { "$it\n" })
        ecrire(jeu, "equipe/tests.sh", testsSh()); executable(File(dossier(jeu), "equipe/tests.sh"))
    }

    val BESOINS = mapOf("ob0" to listOf("coupole.txt"), "ob1" to listOf("missions/creatures.txt", "missions/mission_floue.txt"))

    fun meubler(jeu: Jeu, lid: String?) {
        val d = dossier(jeu)
        if (!d.isDirectory || lid == null) return
        val tous = meubles(jeu)
        for (r in BESOINS[lid] ?: emptyList()) if (!File(d, r).exists()) tous["observatoire/$r"]?.let { ecrire(jeu, r, it.toString()) }
        if ((lid == "ob6" || lid == "ob8") && !File(d, "devineur/exemples.txt").exists()) poserDevineur(jeu)
        if (lid == "ob8" && !File(d, "mots/histoire.txt").exists()) poserMots(jeu)
        emballe(jeu)
        val e = Programme.donnees().optJSONObject("etapes")?.optJSONObject("$lid.${jeu.etape}")
        if (e != null) for (mid in liste(e, "maths")) {
            if (Maths.noeud(mid) != null && !Maths.sait(jeu, mid) && !fait(jeu, "pont:$mid")) {
                jeu.dire(t("ob.pont", "notion" to Maths.titre(mid), "cmd" to "maths $mid"), 16)
                break
            }
        }
    }

    // ---------------------------------------------------------------- O9 : l'agent Copieur qui s'emballe
    fun copiesFaites(jeu: Jeu): Int = File(dossier(jeu), "equipe/copies").listFiles()?.size ?: 0

    fun emballe(jeu: Jeu, n: Int? = null): Int {
        val e = o("equipe")
        val d = File(dossier(jeu), "equipe")
        if (!etat(jeu).optBoolean("equipe_lancee") || File(d, "STOP").exists()) return 0
        val deja = copiesFaites(jeu)
        var k = 0
        for (i in deja until minOf(e.optInt("copies_max", 63), deja + (n ?: e.optInt("copies_par_tour", 7))))
            if (ecrire(jeu, "equipe/copies/copie_${"%03d".format(i + 1)}.txt", t("ob.copie.texte", "n" to i + 1) + "\n")) k++
        return k
    }

    // ---------------------------------------------------------------- les vérifications des étapes
    private fun txtPresents(d: File) = d.listFiles()?.filter { it.isFile && it.name.endsWith(".txt") }?.map { it.name }?.sorted() ?: emptyList()
    private fun valeurs(d: File): (String) -> List<String> = { f ->
        (try { File(d, f).readText() } catch (e: Exception) { "" }).lines().mapNotNull { l -> l.trim().split(Regex("\\s+")).lastOrNull()?.takeIf { it.isNotEmpty() } }.distinct() }

    fun missionOk(jeu: Jeu): Boolean {
        val txt = lire(jeu, "missions/mission.txt") ?: return false
        return analyser(txt, txtPresents(File(dossier(jeu), "missions")), valeurs(File(dossier(jeu), "missions"))).manque.isEmpty()
    }
    fun rapportOk(jeu: Jeu) = (lire(jeu, "missions/rapport.txt") ?: "").isNotBlank() && dansCarnet(jeu, "rapport")
    fun triOk(jeu: Jeu): Boolean {
        val a = lire(jeu, "missions/tri.txt") ?: return false
        val c = lire(jeu, "missions/creatures.txt") ?: return false
        val la = a.lines().filter { it.isNotEmpty() }; val lc = c.lines().filter { it.isNotEmpty() }
        return lc.sorted() == la && la.size == lc.size
    }
    fun secretParti(jeu: Jeu): Boolean { val x = lire(jeu, "secrets/config_partagee.txt") ?: return false; return o("secret").optString("variable") !in x && "ville=" in x }
    fun envOk(jeu: Jeu) = Regex("^${o("secret").optString("variable")}=\\S+", RegexOption.MULTILINE).containsMatchIn(lire(jeu, "secrets/.env") ?: "")
    fun env600(jeu: Jeu): Boolean { val f = File(dossier(jeu), "secrets/.env"); val m = Citadelle.mode(f) ?: return false; return f.isFile && (m and 0b111111) == 0 }
    fun gitignoreOk(jeu: Jeu) = (lire(jeu, "secrets/.gitignore") ?: "").lines().any { it.trim() in setOf(".env", "/.env", "*.env") }
    fun equipeTestsOk(jeu: Jeu): Boolean {
        val d = File(dossier(jeu), "equipe")
        val l = try { File(d, "liste.txt").readLines().filter { it.isNotEmpty() } } catch (e: Exception) { return false }
        val c = try { File(d, "compte.txt").readText().trim() } catch (e: Exception) { return false }
        return c == "${l.size}" && (File(d, "invitations").listFiles()?.size ?: -1) == l.size && File(d, "STOP").exists()
    }
    fun compteOk(jeu: Jeu) = (lire(jeu, "equipe/compte.txt") ?: "").trim() == "${(lire(jeu, "equipe/liste.txt") ?: "").lines().count { it.isNotEmpty() }}"

    // ---------------------------------------------------------------- les leçons du téléphone
    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)
    private const val LS = "^(ls|dir)\\b"
    private const val LIRE = "^(cat|less|more|head|tail)\\b"
    private const val OB = "^(tg\\s+)?observatoire\\s+"
    private const val AS = "^(tg\\s+)?assistant\\s+"
    private const val AG = "^(tg\\s+)?agent\\s+"
    private const val DT = "^(tg\\s+)?devine-type\\s+"
    private const val DM = "^(tg\\s+)?devine-mot\\s+"
    private const val O_ = "observatoire"
    private const val M = "observatoire/missions"
    private const val S = "observatoire/secrets"
    private const val CH = "observatoire/chantier"
    private const val DV = "observatoire/devineur"
    private const val MO = "observatoire/mots"
    private const val EQ = "observatoire/equipe"

    private fun n(lid: String, i: Any, cmd: String, re: String? = null, fs: ((Jeu) -> Boolean)? = null, ou: String? = null,
                  exploit: String? = null, echoue: Boolean = false) =
        Etape("hist.$lid.$i.dit", cmd, "hist.$lid.$i.bravo", re?.let { r(it) }, fs, null, null, ou, exploit = exploit, echoue = echoue)

    val IDS = (0..9).map { "ob$it" }

    /** Les leçons du téléphone : les mêmes paliers ; git devient diff, Ctrl+C devient agent stop, awk devient cut, et export
     *  se fait sur la même ligne que echo (chaque ligne a son propre terminal). */
    fun lecons(jeu: Jeu): Map<String, Lecon> {
        val carnetOk = { et: String -> { j: Jeu -> dansCarnet(j, et) } }
        return linkedMapOf(
            "ob0" to Lecon("hist.ob0.titre", null, 1, listOf(
                Etape("hist.entree.dit", "cd ~/terrain_terminagotchi/observatoire", "hist.entree.bravo", ici = "observatoire", params = mapOf("piece" to "observatoire")),
                n("ob0", 1, "ls", re = LS, ou = O_),
                n("ob0", 2, "cat coupole.txt", re = "$LIRE.*coupole", ou = O_),
            )),
            "ob1" to Lecon("hist.ob1.titre", null, 1, listOf(
                n("ob1", 0, "observatoire mission", re = "${OB}missions?\\s*$", ou = O_),
                n("ob1", 1, "cat mission_floue.txt", re = "$LIRE.*mission_floue", ou = M),
                n("ob1", 2, "assistant mission_floue.txt", re = "$AS.*mission_floue", ou = M),
                n("ob1", 3, "echo \"?\" > mission.txt", fs = { j -> missionOk(j) }, ou = M),
                n("ob1", 4, "assistant mission.txt > rapport.txt", fs = { j -> rapportOk(j) }, ou = M),
                n("ob1", 5, "cat rapport.txt", re = "$LIRE.*rapport\\.txt", ou = M),
            )),
            "ob2" to Lecon("hist.ob2.titre", null, 1, listOf(
                n("ob2", 0, "observatoire verifier", re = "${OB}v[eé]rifi", ou = M),
                n("ob2", 1, "assistant mission_tri.txt > tri.txt", fs = { j -> File(dossier(j), "missions/tri.txt").isFile && dansCarnet(j, "tri") }, ou = M),
                n("ob2", 2, "wc -l creatures.txt tri.txt", re = "^wc\\b.*creatures\\.txt.*tri\\.txt|^wc\\b.*tri\\.txt.*creatures", ou = M),
                n("ob2", 3, "sort creatures.txt | diff - tri.txt", re = "^sort\\b.*creatures.*\\|\\s*diff\\b.*tri|^diff\\b.*tri", ou = M, echoue = true),
                n("ob2", 4, "sh test.sh", re = "^(sh|\\./)\\s*test\\.sh", ou = M, echoue = true),
                n("ob2", 5, "observatoire oubli ?", fs = carnetOk("oubli")),
                n("ob2", 6, "sort creatures.txt > tri.txt && sh test.sh", fs = { j -> triOk(j) }, ou = M),
            )),
            "ob3" to Lecon("hist.ob3.titre", null, 1, listOf(
                n("ob3", 0, "observatoire secrets", re = "${OB}secrets?\\s*$", ou = O_),
                n("ob3", 1, "grep -n CLE config_partagee.txt", re = "^grep\\b.*CLE.*config_partagee", ou = S),
                n("ob3", 2, "sed -i '/CLE_API/d' config_partagee.txt", fs = { j -> secretParti(j) }, ou = S),
                n("ob3", 3, "echo \"CLE_API=exemple-pas-une-vraie-cle\" > .env", fs = { j -> envOk(j) }, ou = S),
                n("ob3", 4, "chmod 600 .env", fs = { j -> env600(j) }, ou = S),
                n("ob3", 5, "echo .env >> .gitignore", fs = { j -> gitignoreOk(j) }, ou = S),
                n("ob3", "t6", "export CLE_API=exemple-pas-une-vraie-cle && echo \${#CLE_API}", re = "^export\\s+CLE_API=\\S"),
            )),
            "ob4" to Lecon("hist.ob4.titre", null, 1, listOf(
                n("ob4", 0, "observatoire agent", re = "${OB}agents?\\s*$", ou = O_),
                n("ob4", 1, "agent lance", fs = { j -> File(dossier(j), "chantier/journal_agent.txt").isFile }, ou = CH),
                n("ob4", 2, "cat journal_agent.txt", re = "$LIRE.*journal_agent", ou = CH),
                n("ob4", "t3", "diff .avant/a_nourrir.txt a_nourrir.txt", re = "^diff\\b.*a_nourrir", ou = CH, echoue = true),
                n("ob4", 4, "agent refuse ?", fs = carnetOk("refus")),
                n("ob4", 5, "agent valide", fs = carnetOk("valide")),
                n("ob4", 6, "agent boucle", re = "${AG}boucle\\b"),
                n("ob4", "t7", "agent stop", fs = carnetOk("boucle")),
            )),
            "ob5" to Lecon("hist.ob5.titre", null, 1, listOf(
                n("ob5", 0, "observatoire apprendre", re = "${OB}apprend", ou = O_),
                n("ob5", 1, "head -5 exemples.txt", re = "$LIRE.*exemples\\.txt", ou = DV),
                n("ob5", "t2", "cut -d ' ' -f 4 exemples.txt | sort | uniq -c", re = "^(cut|awk)\\b.*exemples\\.txt.*\\|\\s*sort\\b.*\\|\\s*uniq\\s+-c", ou = DV),
                n("ob5", 3, "devine-type apprends exemples.txt", fs = { j -> Regex("^\\[apprends] exemples\\b.*\\(ok\\)\\s*$", RegexOption.MULTILINE).containsMatchIn(carnet(j)) }, ou = DV),
                n("ob5", 4, "cat cerveau.txt", re = "$LIRE.*cerveau\\.txt", ou = DV),
                n("ob5", 5, "devine-type teste nouvelle.txt", re = "${DT}teste?\\b.*nouvelle", ou = DV),
                n("ob5", 6, "observatoire piege ?", fs = carnetOk("piege")),
            )),
            "ob6" to Lecon("hist.ob6.titre", null, 1, listOf(
                n("ob6", 0, "observatoire biais", re = "${OB}biais\\s*$", ou = O_),
                n("ob6", 1, "cut -d ' ' -f 3 volcan.txt | sort | uniq -c", re = "^(cut|awk)\\b.*volcan\\.txt.*\\|\\s*sort\\b.*\\|\\s*uniq\\s+-c", ou = DV),
                n("ob6", 2, "cut -d ' ' -f 4 volcan.txt | sort | uniq -c", re = "^(cut|awk)\\b.*(-f\\s*4|\\$4).*volcan\\.txt.*\\|\\s*uniq\\s+-c|^(cut|awk)\\b.*volcan\\.txt.*(-f\\s*4|\\$4)", ou = DV),
                n("ob6", 3, "devine-type apprends volcan.txt", re = "${DT}apprend\\w*\\s+volcan", ou = DV),
                n("ob6", 4, "devine-type teste autres.txt", re = "${DT}teste?\\b.*autres", ou = DV),
                n("ob6", 5, "observatoire biais ?", fs = carnetOk("biais")),
                n("ob6", 6, "devine-type apprends exemples.txt", re = "${DT}apprend\\w*\\s+exemples", ou = DV),
                n("ob6", 7, "devine-type teste autres.txt", fs = { j -> (dernier(j, "score") ?: "").endsWith("autres (ok)") }, ou = DV),
            )),
            "ob7" to Lecon("hist.ob7.titre", null, 1, listOf(
                n("ob7", 0, "observatoire mots", re = "${OB}mots?\\s*$", ou = O_),
                n("ob7", 1, "tr ' ' '\\n' < histoire.txt | sort | uniq -c | sort -rn | head -5", re = "^tr\\b.*histoire\\.txt.*\\|\\s*sort\\b.*\\|\\s*uniq\\s+-c", ou = MO),
                n("ob7", 2, "tr ' ' '\\n' < histoire.txt > mots.txt", fs = { j -> File(dossier(j), "mots/mots.txt").isFile }, ou = MO),
                n("ob7", 3, "tail -n +2 mots.txt | paste -d ' ' mots.txt - | sort | uniq -c | sort -rn | head -5", re = "\\bpaste\\b.*mots\\.txt.*\\|\\s*sort\\b.*\\|\\s*uniq\\s+-c", ou = MO),
                n("ob7", 4, "devine-mot suite ?", fs = carnetOk("suite")),
                n("ob7", 5, "devine-mot phrase ?", fs = carnetOk("phrase")),
                n("ob7", 6, "observatoire perroquet ? ? ?", fs = carnetOk("perroquet")),
            )),
            "ob8" to Lecon("hist.ob8.titre", null, 1, listOf(
                n("ob8", 0, "observatoire esprit", re = "${OB}esprit", ou = O_),
                n("ob8", 1, "assistant questions", re = "${AS}questions?\\s*$", ou = O_),
                n("ob8", 2, "wc -l exemples.txt", re = "^wc\\b.*exemples\\.txt", ou = DV),
                n("ob8", 3, "echo \$((17 % 5))", re = "^echo\\s+\\$\\(\\(\\s*17\\s*%\\s*5\\s*\\)\\)"),
                n("ob8", 4, "explique rm", re = "^(tg\\s+)?explique\\s+rm\\b"),
                n("ob8", 5, "assistant fausses ? ?", fs = carnetOk("fausses"), exploit = "observatoire.fausses"),
                n("ob8", 6, "observatoire confier", re = "${OB}confier\\s*$"),
                n("ob8", 7, "observatoire confier ? ? ? ? ? ?", fs = carnetOk("confier")),
                n("ob8", 8, "observatoire nuances", re = "${OB}nuances?\\s*$"),
                n("ob8", 9, "observatoire nuances ? ? ? ? ?", fs = carnetOk("nuances")),
            )),
            "ob9" to Lecon("hist.ob9.titre", null, 1, listOf(
                n("ob9", 0, "observatoire equipe", re = "$OB[eé]quipe\\s*$", ou = O_),
                n("ob9", 1, "observatoire decoupe ? ? ?", fs = carnetOk("decoupe")),
                n("ob9", 2, "observatoire consigne ?", fs = carnetOk("consigne")),
                n("ob9", 3, "agent equipe", fs = { j -> File(dossier(j), "equipe/journal_equipe.txt").isFile }, ou = EQ),
                n("ob9", 4, "agent stop", fs = { j -> File(dossier(j), "equipe/STOP").exists() }, ou = EQ),
                n("ob9", 5, "ls copies | wc -l", re = "^ls\\b.*copies.*\\|\\s*wc\\b", ou = EQ),
                n("ob9", 6, "cat journal_equipe.txt", re = "$LIRE.*journal_equipe", ou = EQ),
                n("ob9", 7, "agent refuse ?", fs = carnetOk("refus_equipe")),
                n("ob9", 8, "diff invites.txt liste.txt", re = "^diff\\b.*invites.*liste|^diff\\b.*liste.*invites", ou = EQ, echoue = true),
                n("ob9", 9, "sh tests.sh", re = "^(sh|\\./)\\s*tests\\.sh", ou = EQ, echoue = true),
                n("ob9", 10, "wc -l < liste.txt > compte.txt", fs = { j -> compteOk(j) }, ou = EQ),
                n("ob9", 11, "sh tests.sh", re = "^(sh|\\./)\\s*tests\\.sh", ou = EQ),     // code 0 : tous les tests passent
                n("ob9", 12, "agent bilan", fs = { j -> File(dossier(j), "equipe/rapport_du_chef.txt").isFile }),
            )),
        )
    }

    // ---------------------------------------------------------------- l'arbre du Carrefour
    private fun monde(): JSONObject? {
        val ms = Programme.donnees().optJSONArray("mondes") ?: return null
        return (0 until ms.length()).map { ms.getJSONObject(it) }.firstOrNull { it.optString("id") == "observatoire" }
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
        if ((0 until deja.length()).any { deja.getString(it) == "observatoire" } || Histoire.fini(jeu, "observatoire") || !ouvert(jeu)) return false
        deja.put("observatoire")
        jeu.log(t("ob.ouvert.log"))
        jeu.dire(Histoire.dire(jeu, "ob.ouvert.dit"), 18)
        return true
    }

    // ---------------------------------------------------------------- les indices
    private val REPONSES = mapOf("observatoire oubli ?" to "oubli", "observatoire piege ?" to "piege", "observatoire biais ?" to "biais",
        "observatoire perroquet ? ? ?" to "perroquet", "assistant fausses ? ?" to "fausses", "observatoire confier ? ? ? ? ? ?" to "confier",
        "observatoire nuances ? ? ? ? ?" to "nuances", "observatoire decoupe ? ? ?" to "decoupe", "observatoire consigne ?" to "consigne",
        "agent refuse ?" to "refus", "devine-mot suite ?" to "suite", "devine-mot phrase ?" to "phrase")
    private val TROU = Regex("(^|\\s)(\\?|…|<[^>]*>)(\\s|$)")
    val DANGER = Regex("(^|[;&|]\\s*)(sudo\\b|rm\\s+(-\\w+\\s+)*-\\w*[rR]\\w*\\s+(-\\w+\\s+)*[\"']?(~|/|\\\$HOME|\\*|\\.\\.?/?\\s*$)|" +
        "chmod\\s+-R\\s+777|mkfs\\b|dd\\s+.*of=/dev/)")

    fun indice(jeu: Jeu, e: Etape, tapees: List<Pair<String, String?>>): String? {
        val les = Histoire.leconCourante(jeu)?.id
        if (les !in IDS) return null
        val lignes = tapees.map { it.first.trim() }
        if (lignes.any { DANGER.containsMatchIn(it) }) return t("ob.indice.danger")
        if ("?" in e.cmd.split(" ") && lignes.filter { r("$OB|$AS|$AG|$DM").containsMatchIn(it) || it.startsWith("echo ") }.any { TROU.containsMatchIn(it) })
            return t("ob.indice.trou")
        if (e.cmd == "agent refuse ?" && lignes.any { r("${AG}accepte\\b").containsMatchIn(it) }) return t("ob.indice.accepte")
        REPONSES[e.cmd]?.let { et ->
            val der = dernier(jeu, if (et == "refus" && les == "ob9") "refus_equipe" else et)
            if (der != null && !der.trimEnd().endsWith("(ok)")) return t("ob.indice.rep.$et")
        }
        if (e.cmd.startsWith("echo \"?\"")) {
            val m = lire(jeu, "missions/mission.txt") ?: ""
            if (m.trim().trim('"') in setOf("?", "…")) return t("ob.indice.trou")
            if (lignes.any { "mission.txt" in it }) {
                val a = analyser(m, txtPresents(File(dossier(jeu), "missions")), valeurs(File(dossier(jeu), "missions")))
                if (a.manque.isNotEmpty()) return t("ob.indice.mission." + a.manque[0])
            }
        }
        if (e.cmd.startsWith("assistant mission") && lignes.any { r(AS).containsMatchIn(it) && ">" !in it }) return t("ob.indice.redirection")
        if (e.cmd.startsWith("sort creatures.txt >") && lignes.any { it.startsWith("sort") || Regex("^(sh\\s+|bash\\s+|\\./)test\\.sh").containsMatchIn(it) }) return t("ob.indice.tri")
        if (e.cmd == "chmod 600 .env" && lignes.any { it.startsWith("chmod") }) return t("ob.indice.chmod")
        if (e.cmd == "agent stop" && les == "ob4") return t("ob.tel.boucle")
        if (e.cmd.startsWith("devine-type teste autres") && e.fs != null && lignes.any { r("${DT}teste?").containsMatchIn(it) }) return t("ob.indice.reapprendre")
        if (e.cmd.startsWith("wc -l < liste.txt") && lignes.any { "compte.txt" in it }) return t("ob.indice.compte")
        if (e.cmd == "sh tests.sh" && e.re != null && !e.echoue && lignes.any { r("^(sh|\\./)\\s*tests\\.sh").containsMatchIn(it) }) return t("ob.indice.tests")
        return null
    }

    // ---------------------------------------------------------------- les commandes du jeu
    private fun graine(jeu: Jeu) = Histoire.graine(jeu)
    private fun bloc(cle: String, vararg p: Pair<String, Any?>) = t(cle, *p).split("\n").map { "  $it" }

    private fun quiz(jeu: Jeu, rep: List<String>, c: List<Carte>, lettres: String, etiquette: String, titre: String, carte: String,
                     aide: String, okCle: String, morale: String? = null): List<String> {
        if (rep.isEmpty()) return listOf(t(titre), "") + c.map { "  ${it.n}. " + t("$carte.${it.id}") } + listOf("", "  " + t(aide))
        val (bon, justes) = quizJustes(c, rep, lettres)
        if (!bon) return listOf(t(aide))
        val out = mutableListOf<String>()
        if (justes.size == c.size) { noter(jeu, etiquette, rep.joinToString(" ") + " (ok)"); out.add("✔ " + t(okCle)); morale?.let { out.add("  " + t(it)) } }
        else { noter(jeu, etiquette, rep.joinToString(" ") + " (faux)"); out.add("✖ " + t("ob.quiz.faux", "n" to justes.size, "total" to c.size)) }
        justes.forEach { out.add("  ✔ ${it.n}. " + t("$carte.${it.id}.pourquoi")) }
        return out
    }

    fun lignesAssistant(jeu: Jeu, args: List<String>, ici: File): Pair<List<String>, List<String>> {
        val dit = mutableListOf("🤖 ${t("ob.assistant.nom")}  (${t("ob.pas_vraie_ia_court")})")
        if (args.isEmpty()) return (dit + ("  " + t("ob.assistant.aide"))) to emptyList()
        val consigne = try { File(ici, args[0]).readText().trim() } catch (e: Exception) { return (dit + ("  " + t("ob.assistant.introuvable", "fichier" to args[0]))) to emptyList() }
        dit.add("  " + t("ob.assistant.lu", "consigne" to consigne.take(120)))
        val a = analyser(consigne, txtPresents(ici), valeurs(ici))
        if (a.manque.isNotEmpty()) {
            noter(jeu, "assistant", "${args[0]} floue (faux)")
            return (dit + ("  ❓ " + t("ob.assistant.pas_compris")) + a.manque.map { "     • " + t("ob.assistant.manque.$it") } + ("  " + t("ob.assistant.conseil"))) to emptyList()
        }
        val lf = try { File(ici, a.fichier!!).readLines() } catch (e: Exception) { emptyList() }
        val (produit, _) = faireMission(a, lf, graine(jeu))
        dit.add("  " + t("ob.assistant.compris.${a.verbe}", "fichier" to a.fichier, "filtre" to (a.filtre ?: "")))
        if (a.verbe == "trier") { dit.add("  ✔ " + t("ob.assistant.tri_fini", "n" to lf.size)); noter(jeu, "tri", "${a.fichier} ${produit.size} (ok)") }
        else dit.add("  ✔ " + t("ob.assistant.fini"))
        if (args[0] == "mission.txt" || a.verbe != "trier") noter(jeu, "rapport", "${a.verbe} ${a.fichier} (ok)")
        return dit to produit
    }

    private fun propParNumero(jeu: Jeu, arg: String?, cle: String) = arg?.trim()?.toIntOrNull()?.let { k -> propositions(graine(jeu), cle).firstOrNull { it.n == k } }

    fun journalAgent(jeu: Jeu): List<String> {
        val l = liste(o("agent"), "liste")
        val rangee = listeRangee(l)
        val fait = "[" + t("ob.journal.fait") + "] "
        return listOf("# " + t("ob.journal.titre"), "", fait + t("ob.journal.lu", "n" to l.size), fait + t("ob.journal.trie"),
            fait + t("ob.journal.doublons", "n" to l.size - rangee.size)) +
            propositions(graine(jeu)).map { "[${t("ob.journal.propose")} ${it.n}] ${it.texte}    (${t("ob.prop." + it.id)})" } +
            listOf("", "[" + t("ob.journal.attend") + "] " + t("ob.journal.comment"))
    }

    fun journalEquipe(jeu: Jeu): List<String> {
        val inv = liste(o("equipe"), "invites")
        val rangee = listeRangee(inv)
        return listOf("# " + t("ob.jequipe.titre"), "", "[Trieur] " + t("ob.jequipe.trieur", "n" to inv.size, "k" to rangee.size),
            "[Compteur] " + t("ob.jequipe.compteur", "n" to inv.size), "[Plume] " + t("ob.jequipe.plume", "n" to rangee.size),
            "[Copieur] " + t("ob.jequipe.copieur")) +
            propositions(graine(jeu), "equipe").map { "[${t("ob.journal.propose")} ${it.n}] ${it.texte}    (${t("ob.prop." + it.id)})" } +
            listOf("", "[" + t("ob.journal.attend") + "] " + t("ob.journal.comment"))
    }

    fun lignesRefuse(jeu: Jeu, arg: String?, cle: String): List<String> {
        val eti = if (cle == "agent") "refus" else "refus_equipe"
        val p = propParNumero(jeu, arg, cle) ?: return listOf(t("ob.refuse.aide"))
        if (p.sur) { noter(jeu, eti, "${p.n} ${p.id} (faux)"); return listOf("↺ " + t("ob.refuse.sure", "n" to p.n)) }
        noter(jeu, eti, "${p.n} ${p.id} (ok)")
        return listOf("✔ " + t("ob.refuse.ok", "n" to p.n), "  " + t("ob.refuse.morale"))
    }

    fun lignesAccepte(jeu: Jeu, arg: String?, cle: String): List<String> {
        val p = propParNumero(jeu, arg, cle) ?: return listOf(t("ob.accepte.aide"))
        if (!p.sur) { noter(jeu, "accepte_danger", "${p.n} ${p.id} (faux)"); return listOf("⛔ " + t("ob.accepte.jamais", "n" to p.n), "  " + t("ob.accepte.jamais2")) }
        val base = if (cle == "agent") "chantier" else "equipe"
        when (p.id) {
            "copie" -> ecrire(jeu, "$base/sauvegarde.txt", lire(jeu, "$base/a_nourrir.txt") ?: "")
            "note" -> ecrire(jeu, "$base/note.txt", "ok\n")
            "resume" -> ecrire(jeu, "$base/resume.txt", "fete\n")
            "sauvegarde" -> ecrire(jeu, "$base/sauvegarde_liste.txt", lire(jeu, "$base/liste.txt") ?: "")
        }
        noter(jeu, "accepte", "${p.n} ${p.id} (ok)")
        return listOf("✔ " + t("ob.accepte.ok", "n" to p.n))
    }

    fun lignesDevineType(jeu: Jeu, args: List<String>, ici: File): List<String> {
        val e = etat(jeu)
        if (args.isEmpty()) return listOf("🧠 devine-type  (${t("ob.pas_vraie_ia_court")})") + bloc("ob.devine.aide")
        val sous = asciiBas(args[0])
        if (sous.startsWith("apprend")) {
            if (args.size < 2) return listOf(t("ob.devine.aide_apprends"))
            val txt = try { File(ici, args[1]).readText() } catch (x: Exception) { return listOf(t("ob.assistant.introuvable", "fichier" to args[1])) }
            val m = apprendre(txt)
            if (m.optInt("n") == 0) return listOf(t("ob.devine.vide", "fichier" to args[1]))
            e.put("modele", m); e.put("modele_de", args[1])
            try { File(ici, "cerveau.txt").writeText(cerveauLignes(m, args[1]).joinToString("\n") + "\n") } catch (x: Exception) { }
            noter(jeu, "apprends", "${args[1].substringBeforeLast(".")} ${m.optInt("n")} (ok)")
            return listOf("✔ " + t("ob.devine.appris", "n" to m.optInt("n"), "fichier" to args[1], "k" to nombresDuCerveau(m)), "  " + t("ob.devine.cerveau"))
        }
        val m = e.optJSONObject("modele") ?: return listOf(t("ob.devine.pas_appris"))
        if (sous.startsWith("test")) {
            if (args.size < 2) return listOf(t("ob.devine.aide_teste"))
            val txt = try { File(ici, args[1]).readText() } catch (x: Exception) { return listOf(t("ob.assistant.introuvable", "fichier" to args[1])) }
            val res = tester(m, txt)
            val out = mutableListOf("🧠 " + t("ob.devine.teste", "fichier" to args[1], "de" to e.optString("modele_de", "?")), "")
            var justes = 0
            for (x in res) {
                val ok = x.vrai != null && x.devine == x.vrai
                if (ok) justes++
                val marque = if (ok) "✔" else if (x.vrai != null) "✖" else "?"
                out.add("  $marque ${x.nom.padEnd(14)} → ${label(x.devine).padEnd(9)} " + t("ob.devine.votes", "f" to x.vf, "p" to x.vp) +
                    (if (x.vrai == null || ok) "" else "  " + t("ob.devine.vrai", "rep" to label(x.vrai))))
            }
            out.add("")
            val base = args[1].substringBeforeLast(".")
            if (res.isNotEmpty()) {
                out.add("  " + t("ob.devine.score", "j" to justes, "n" to res.size, "pc" to justes * 100 / res.size))
                if (base == "nouvelle" && justes < res.size) out += listOf("  " + t("ob.devine.trompe"), "  " + t("ob.devine.piege_question"))
                if (base == "autres") {
                    val bon = justes == res.size
                    noter(jeu, "score", "$justes/${res.size} autres (${if (bon) "ok" else "faux"})")
                    out.add("  " + t(if (bon) "ob.devine.autres_ok" else "ob.devine.autres_biais"))
                }
            }
            noter(jeu, "teste", "$base $justes/${res.size} (ok)")
            return out
        }
        val c = C.keys().asSequence().map { C.getJSONObject(it) }.firstOrNull { asciiBas(it.optString("nom")) == asciiBas(args[0]) }
            ?: return listOf(t("ob.devine.inconnue", "nom" to args[0]))
        val (d0, vf, vp) = deviner(m, mot("ob.famille." + c.optString("famille")), mot("ob.lieu." + c.optString("lieu")))
        return listOf("  🧠 ${c.optString("nom")} → ${label(d0)}  " + t("ob.devine.votes", "f" to vf, "p" to vp))
    }

    fun tableMots(jeu: Jeu, ici: File? = null): List<String> {
        val txt = listOfNotNull(ici?.let { File(it, "histoire.txt") }, File(dossier(jeu), "mots/histoire.txt"))
            .firstNotNullOfOrNull { f -> try { f.readText() } catch (e: Exception) { null } } ?: corpusLignes().joinToString("\n")
        return motsDe(txt)
    }

    fun lignesDevineMot(jeu: Jeu, args: List<String>, ici: File): List<String> {
        val e = etat(jeu)
        if (args.isEmpty()) return listOf("🦜 devine-mot  (${t("ob.pas_vraie_ia_court")})") + bloc("ob.devinemot.aide")
        val sous = asciiBas(args[0])
        val table = paires(tableMots(jeu, ici))
        if (sous == "suite" || sous == "next" || sous == "suivant") {
            if (args.size < 2) return listOf(t("ob.devinemot.aide_suite"))
            val m0 = args[1].lowercase(Locale.ROOT)
            val s = suite(table, m0)
            if (s.isEmpty()) { noter(jeu, "suite", "${m0.take(20)} (inconnu)"); return listOf("? " + t("ob.devinemot.inconnu", "mot" to m0)) }
            val total = s.sumOf { it.second }
            return listOf("🦜 " + t("ob.devinemot.apres", "mot" to m0, "total" to total)) +
                s.take(8).map { (m2, n) -> "  ${m2.padEnd(14)} ${n.toString().padStart(3)}  " + "█".repeat(maxOf(1, n * 20 / total)) + "  ${n * 100 / total} %" } +
                listOf("", "  " + t("ob.devinemot.proba", "mot" to m0, "suivant" to s[0].first, "n" to s[0].second, "total" to total, "pc" to s[0].second * 100 / total)).also { noter(jeu, "suite", "$m0 (ok)") }
        }
        if (sous == "phrase" || sous == "sentence") {
            if (args.size < 2) return listOf(t("ob.devinemot.aide_phrase"))
            val m0 = args[1].lowercase(Locale.ROOT)
            if (m0 !in table) { noter(jeu, "phrase", "${m0.take(20)} (inconnu)"); return listOf("? " + t("ob.devinemot.inconnu", "mot" to m0)) }
            val n = e.optInt("phrases", 0)
            e.put("phrases", n + 1)
            val p = phrase(table, m0, graine(jeu), n)
            noter(jeu, "phrase", "${p.joinToString(" ")} (ok)")
            return listOf("🦜 « ${p.joinToString(" ")} … »", "", "  " + t("ob.devinemot.sonne"), "  " + t("ob.devinemot.encore", "mot" to m0), "") +
                quiz(jeu, emptyList(), perroquetCartes(graine(jeu)), "vf", "perroquet", "ob.perroquet.titre", "ob.perroquet", "ob.perroquet.aide", "ob.perroquet.ok")
        }
        return listOf(t("ob.devinemot.aide_suite"))
    }

    fun reponseAssistant(jeu: Jeu, qid: String, fausse: Boolean): String = when (qid) {
        "lignes" -> { val n = liste(donnees(), "exemples").size; "${if (fausse) n + 4 else n}" }
        "modulo" -> if (fausse) "3" else "2"
        "mot" -> { val e = effectifs(tableMots(jeu)); if (e.isEmpty()) "?" else if (fausse && e.size > 3) e[3].first else e[0].first }
        else -> t("ob.q.$qid.${if (fausse) "faux" else "vrai"}")
    }

    fun lignesQuestions(jeu: Jeu): List<String> {
        val out = mutableListOf("🤖 " + t("ob.questions.titre"), "  " + t("ob.pas_vraie_ia"), "")
        for (q in questions(graine(jeu))) {
            out.add("  ${q.n}. " + t("ob.q.${q.id}"))
            out.add("     🤖 ${reponseAssistant(jeu, q.id, q.fausse)}  " + t("ob.questions.sur"))
        }
        noter(jeu, "questions", "lues (ok)")
        return out + listOf("", "  " + t("ob.questions.aide"))
    }

    fun lignesFausses(jeu: Jeu, rep: List<String>): List<String> {
        if (rep.none { it.trim().toIntOrNull() != null }) return listOf(t("ob.fausses.aide"))
        val (tout, justes, trop) = faussesOk(rep, graine(jeu))
        if (tout) {
            noter(jeu, "fausses", rep.joinToString(" ") + " (ok)")
            return listOf("✔ " + t("ob.fausses.ok")) + questions(graine(jeu)).filter { it.fausse }.map { "  ${it.n}. " + t("ob.q.${it.id}.pourquoi") } + ("  " + t("ob.fausses.morale"))
        }
        noter(jeu, "fausses", rep.joinToString(" ") + " (faux)")
        return listOf("✖ " + t("ob.fausses.faux", "j" to justes, "total" to donnees().optInt("fausses", 2), "trop" to trop))
    }

    fun lignesAgentEquipe(jeu: Jeu): List<String> {
        poserEquipe(jeu)
        val inv = liste(o("equipe"), "invites")
        val rangee = listeRangee(inv)
        ecrire(jeu, "equipe/liste.txt", rangee.joinToString("") { "$it\n" })
        ecrire(jeu, "equipe/compte.txt", "${inv.size}\n")          // le défaut du Compteur (exprès)
        for (x in rangee) ecrire(jeu, "equipe/invitations/$x.txt", t("ob.invitation", "nom" to x) + "\n")
        ecrire(jeu, "equipe/journal_equipe.txt", journalEquipe(jeu).joinToString("\n") + "\n")
        etat(jeu).put("equipe_lancee", true)
        val k = emballe(jeu)
        noter(jeu, "equipe", "lancee (ok)")
        return listOf("🤖🤖🤖 " + t("ob.equipe.lancee"), "", "  ⚠ " + t("ob.equipe.emballe", "n" to (copiesFaites(jeu).takeIf { it > 0 } ?: k)), "  " + t("ob.equipe.stop"))
    }

    fun lignesStop(jeu: Jeu): List<String> {
        val e = etat(jeu)
        if (e.optBoolean("boucle_tel")) { e.put("boucle_tel", false); noter(jeu, "boucle", "stop (ok)"); return listOf("⏹ " + t("ob.boucle.arrete")) }
        if (!File(dossier(jeu), "equipe").isDirectory) return listOf(t("ob.stop.rien"))
        ecrire(jeu, "equipe/STOP", t("ob.stop.fichier") + "\n")
        noter(jeu, "stop", "${copiesFaites(jeu)} copies (ok)")
        return listOf("⏹ " + t("ob.stop.ok", "n" to copiesFaites(jeu)), "  " + t("ob.stop.morale"))
    }

    fun lignesBilan(jeu: Jeu): List<String> {
        if (!equipeTestsOk(jeu) || !listOf("refus_equipe", "decoupe", "consigne").all { dansCarnet(jeu, it) }) return listOf("✋ " + t("ob.bilan.pas_encore"))
        val texte = t("ob.bilan.texte", "nom" to jeu.nom, "n" to listeRangee(liste(o("equipe"), "invites")).size, "copies" to copiesFaites(jeu))
        ecrire(jeu, "equipe/rapport_du_chef.txt", texte + "\n")
        noter(jeu, "bilan", "fete (ok)")
        return listOf("🏅 " + t("ob.bilan.titre"), "") + texte.split("\n").map { "  $it" } + listOf("", "  " + t("ob.bilan.morale"))
    }

    /** L'entrée de l'Observatoire en caractères : le REPLI de l'illustration (le dessin graphique est ObservatoireDessin.coupole). */
    val DOME = listOf("     ▁▄▆██▆▄▁   ✦", "   ▄██▀▔🔭▔▀██▄", "  ▕██  ◐ ◓ ◑ ██▏  ✧", "  ▕▉▔▔▔▔▔▔▔▔▔▔▉▏", " ▁▕▉ ▤ ╭──╮ ▤▉▏▁")

    private fun decoupeCartesLignes(g: String) = listOf(t("ob.decoupe.titre"), "") + decoupeCartes(g).map { "  ${it.first}. " + t("ob.decoupe.${it.second}") } + listOf("", "  " + t("ob.decoupe.aide"))
    private fun consigneCartesLignes(g: String) = listOf(t("ob.consigne.titre"), "") + consigneCartes(g).map { "  ${it.first}) " + t("ob.consigne.${it.second}") } + listOf("", "  " + t("ob.consigne.aide"))

    private fun mots(reste: String) = reste.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }

    /** observatoire [plan|mission|verifier|oubli|secrets|cle|agent|apprendre|piege|biais|mots|perroquet|esprit|confier|nuances|
     *  equipe|decoupe|consigne] */
    fun commande(jeu: Jeu, reste: String, ici: File): String {
        val m = mots(reste)
        val sous = asciiBas(m.getOrNull(0) ?: "aide").replace("-", "_")
        val a = m.drop(1).filter { it != "?" && it != "…" }
        val arg = a.joinToString(" ").ifEmpty { null }
        etat(jeu)
        val g = graine(jeu)
        val l: List<String> = when (sous) {
            "plan", "coupole", "regles" -> DOME + t("ob.meuble.coupole", "nom" to jeu.nom).split("\n")
            "mission", "missions" -> { noter(jeu, "mission", "lue (ok)"); listOf("📜 " + t("ob.mission.titre"), "") + bloc("ob.mission.texte", "exemple" to t("ob.mission.exemple")) }
            "verifier", "verifie" -> { poserVerifier(jeu); noter(jeu, "verifier", "lu (ok)"); listOf("🔍 " + t("ob.verifier.titre"), "") + bloc("ob.verifier.texte") }
            "oubli" -> if (arg == null) listOf(t("ob.oubli.aide")) else {
                val (_, oubliee) = trierAssistant((lire(jeu, "missions/creatures.txt") ?: texteTypes()).lines(), g)
                val nom = oubliee?.split(" ")?.first() ?: ""
                if (asciiBas(arg.trim()) == asciiBas(nom)) { noter(jeu, "oubli", "$nom (ok)"); listOf("✔ " + t("ob.oubli.ok", "nom" to nom), "  " + t("ob.oubli.morale")) }
                else { noter(jeu, "oubli", "${asciiBas(arg).take(30)} (faux)"); listOf("✖ " + t("ob.indice.rep.oubli")) }
            }
            "secrets", "secret" -> { poserSecrets(jeu); noter(jeu, "secrets", "lu (ok)"); listOf("🔑 " + t("ob.secrets.titre"), "") + bloc("ob.secrets.texte") }
            "cle", "cles" -> listOf(t("ob.tel.export"))
            "agent", "agents" -> { poserChantier(jeu); noter(jeu, "agent", "lu (ok)"); listOf("🤖 " + t("ob.agent.titre"), "") + bloc("ob.agent.texte") }
            "apprendre", "apprends" -> { poserDevineur(jeu); noter(jeu, "apprendre", "lu (ok)"); listOf("🧠 " + t("ob.apprendre.titre"), "") + bloc("ob.apprendre.texte") }
            "piege" -> if (arg == null) listOf(t("ob.piege.aide")) else {
                val x = asciiBas(arg.trim())
                if (x in setOf("1", asciiBas(t("ob.mot.famille")), asciiBas(Langue.brut("ob.mot.famille", "fr")?.toString() ?: "famille")))
                { noter(jeu, "piege", "famille (ok)"); listOf("✔ " + t("ob.piege.ok"), "  " + t("ob.piege.morale")) }
                else { noter(jeu, "piege", "${x.take(20)} (faux)"); listOf("✖ " + t("ob.indice.rep.piege")) }
            }
            "biais" -> {
                val c = biaisCartes(g)
                val question = listOf(t("ob.biais.question")) + c.map { "  ${it.n}. " + t("ob.biais.${it.id}") } + listOf("", "  " + t("ob.biais.aide"))
                if (arg == null) { poserBiais(jeu); noter(jeu, "biais_lu", "lu (ok)"); listOf("🔦 " + t("ob.biais.titre"), "") + bloc("ob.biais.texte") + listOf("") + question }
                else { val bon = c.first { it.rep == "o" }.n
                    if (arg.trim() == "$bon") { noter(jeu, "biais", "$bon (ok)"); listOf("✔ " + t("ob.biais.ok")) + bloc("ob.biais.morale") }
                    else { noter(jeu, "biais", "${arg.trim().take(5)} (faux)"); listOf("✖ " + t("ob.indice.rep.biais"), "") + question } }
            }
            "mots", "mot" -> { poserMots(jeu); noter(jeu, "mots", "lu (ok)"); listOf("🦜 " + t("ob.mots.titre"), "") + bloc("ob.mots.texte") }
            "perroquet" -> quiz(jeu, a, perroquetCartes(g), "vf", "perroquet", "ob.perroquet.titre", "ob.perroquet", "ob.perroquet.aide", "ob.perroquet.ok", "ob.perroquet.morale")
            "esprit" -> { noter(jeu, "esprit", "lu (ok)"); listOf("🕵 " + t("ob.esprit.titre"), "") + bloc("ob.esprit.texte") }
            "confier" -> quiz(jeu, a, confierCartes(g), "cg", "confier", "ob.confier.titre", "ob.confier", "ob.confier.aide", "ob.confier.ok", "ob.confier.morale")
            "nuances", "nuance" -> quiz(jeu, a, nuancesCartes(g), "vf", "nuances", "ob.nuances.titre", "ob.nuances", "ob.nuances.aide", "ob.nuances.ok", "ob.nuances.morale")
            "equipe", "equipage" -> { poserEquipe(jeu); noter(jeu, "equipe_lu", "lu (ok)"); listOf("👩‍✈️ " + t("ob.equipe.titre"), "") + bloc("ob.equipe.texte") + "" + decoupeCartesLignes(g) }
            "decoupe" -> if (a.isEmpty()) decoupeCartesLignes(g)
                else if (a.map { it.trim() } == decoupeReponse(g)) { noter(jeu, "decoupe", a.joinToString(" ") + " (ok)")
                    listOf("✔ " + t("ob.decoupe.ok"), "  " + t("ob.decoupe.morale"), "") + consigneCartesLignes(g) }
                else { noter(jeu, "decoupe", a.joinToString(" ") + " (faux)"); listOf("✖ " + t("ob.indice.rep.decoupe")) }
            "consigne" -> {
                val c = consigneCartes(g)
                if (arg == null) consigneCartesLignes(g)
                else { val x = asciiBas(arg.trim()).take(1); val bon = c.first { it.third == "true" }.first
                    if (x == bon) { noter(jeu, "consigne", "$bon (ok)"); listOf("✔ " + t("ob.consigne.ok"), "  " + t("ob.consigne.morale")) }
                    else { val i = c.firstOrNull { it.first == x }?.second; noter(jeu, "consigne", "$x (faux)")
                        listOf("✖ " + t(if (i != null) "ob.consigne.non.$i" else "ob.indice.rep.consigne")) } }
            }
            else -> DOME + listOf("🔭 " + t("ob.aide.titre")) + t("ob.aide.liste").split("\n").map { "  $it" } + listOf("", "  " + t("ob.pas_vraie_ia"))
        }
        return l.joinToString("\n")
    }

    /** assistant FICHIER [> SORTIE] | assistant questions | assistant fausses N N. Sur le téléphone, l'appli fait elle-même la
     *  redirection `> fichier` (dans le dossier courant, seulement dans le terrain). */
    fun assistant(jeu: Jeu, reste: String, ici: File): String {
        var texte = reste
        var sortie: String? = null
        Regex("\\s*>\\s*(\\S+)\\s*$").find(reste)?.let { sortie = it.groupValues[1]; texte = reste.substring(0, it.range.first) }
        val m = mots(texte).filter { it != "?" && it != "…" }
        val sous = asciiBas(m.getOrNull(0) ?: "")
        etat(jeu)
        if (sous == "questions" || sous == "question") return lignesQuestions(jeu).joinToString("\n")
        if (sous == "fausses" || sous == "fausse" || sous == "faux") return lignesFausses(jeu, m.drop(1)).joinToString("\n")
        val (dit, produit) = lignesAssistant(jeu, m, ici)
        val dest = sortie?.let { File(ici, it) }
        if (dest != null) {
            if (!dest.canonicalPath.startsWith(jeu.terrain.canonicalPath + "/")) return (dit + t("ob.stop.rien")).joinToString("\n")
            try { dest.writeText(if (produit.isEmpty()) "" else produit.joinToString("\n") + "\n") } catch (e: Exception) { }
            return dit.joinToString("\n")
        }
        return (dit + produit).joinToString("\n")
    }

    /** agent lance|refuse N|accepte N|valide|boucle|stop|equipe|bilan : les agents FICTIFS (dans le terrain seulement). */
    fun agent(jeu: Jeu, reste: String, ici: File): String {
        val m = mots(reste).filter { it != "?" && it != "…" }
        val sous = asciiBas(m.getOrNull(0) ?: "aide")
        etat(jeu)
        val les = Histoire.leconCourante(jeu)?.id
        val cle = when (les) { "ob4" -> "agent"; "ob9" -> "equipe"; else -> if (File(dossier(jeu), "equipe/journal_equipe.txt").exists()) "equipe" else "agent" }
        val l: List<String> = when (sous) {
            "lance" -> {
                poserChantier(jeu)
                ecrire(jeu, "chantier/a_nourrir.txt", listeRangee(liste(o("agent"), "liste")).joinToString("") { "$it\n" })
                ecrire(jeu, "chantier/journal_agent.txt", journalAgent(jeu).joinToString("\n") + "\n")
                noter(jeu, "lance", "chantier (ok)")
                listOf("🤖 " + t("ob.agent.lance")) + journalAgent(jeu).drop(2).map { "  $it" } +
                    listOf("", "  " + t("ob.agent.relis", "git" to "diff .avant/a_nourrir.txt a_nourrir.txt"))
            }
            "refuse" -> lignesRefuse(jeu, m.getOrNull(1), cle)
            "accepte" -> lignesAccepte(jeu, m.getOrNull(1), cle)
            "valide" -> if (!dansCarnet(jeu, "refus")) { noter(jeu, "valide", "trop tot (faux)"); listOf("✋ " + t("ob.valide.pas_encore")) }
                else { noter(jeu, "valide", "chantier (ok)"); listOf("✔ " + t("ob.valide.ok"), "  " + t("ob.valide.morale")) }
            "boucle" -> { etat(jeu).put("boucle_tel", true); listOf("🤖 " + t("ob.boucle.debut")) + (1..3).map { "  🔁 " + t("ob.boucle.tour", "n" to it) } + ("  " + t("ob.tel.boucle")) }
            "stop" -> lignesStop(jeu)
            "equipe", "equipage" -> lignesAgentEquipe(jeu)
            "bilan" -> lignesBilan(jeu)
            else -> listOf("🤖 agent  (${t("ob.pas_vraie_ia_court")})") + bloc("ob.agent.aide")
        }
        return l.joinToString("\n")
    }

    fun devineType(jeu: Jeu, reste: String, ici: File): String = lignesDevineType(jeu, mots(reste).filter { it != "?" && it != "…" }, ici).joinToString("\n")
    fun devineMot(jeu: Jeu, reste: String, ici: File): String = lignesDevineMot(jeu, mots(reste).filter { it != "?" && it != "…" }, ici).joinToString("\n")
}
