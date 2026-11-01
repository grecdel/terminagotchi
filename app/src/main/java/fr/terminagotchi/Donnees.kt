package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.text.Normalizer
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * 📊 La Salle des Données (docs/programme.md § 2.14 et § 7.13 « D-SQL »), portage de pc/tg/donnees.py.
 *
 * Les données sont la collection de l'enfant, exportée par l'appli (`collection --csv > collection.csv`) dans le terrain
 * (terrain_terminagotchi/donnees) : l'espèce, le type, la famille, les stats, la rareté, shiny, la variante, le jour de
 * la capture ; ni pseudo, ni e-mail, ni identifiant. Rien n'est envoyé. Une collection de moins de 5 bestioles est
 * complétée par le jeu d'exemple (colonne exemple = 1). Chaque bonne réponse est calculée sur le MÊME fichier, au
 * moment de vérifier.
 *
 * Mêmes leçons que sur PC (dn0 → dn6). Sur le téléphone : `collection --csv` (sans tg), un petit awk intégré
 * (DonneesAwk : une commande seule, sans tuyau, comparée au vrai awk) et un petit sqlite3 intégré sur le SQLite du
 * téléphone (DonneesSql : lecture seule, une requête à la fois). Vecteurs communs donnees/donnees/vecteurs.json,
 * vérifiés par tests/jvm/Donnees.kt.
 */
object Donnees {
    @Volatile var chargeur: (() -> String?)? = null
    private var d: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("donnees.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun donnees(): JSONObject = d ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() }).also { d = it }
    private fun liste(o: JSONObject?, k: String): List<String> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.get(it).toString() } } ?: emptyList()
    private fun objets(o: JSONObject?, k: String): List<JSONObject> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.getJSONObject(it) } } ?: emptyList()
    private fun o(k: String) = donnees().optJSONObject(k) ?: JSONObject()
    val colonnes: List<String> get() = liste(donnees(), "colonnes")
    private val STATS = listOf("attaque", "defense", "vitesse", "pv", "intelligence")

    // ================================================================ la spécification pure (vecteurs communs)
    fun asciiId(texte: String?): String = Normalizer.normalize(texte ?: "", Normalizer.Form.NFKD)
        .filter { Character.getType(it) != Character.NON_SPACING_MARK.toInt() }.lowercase(Locale.ROOT).trim().replace(" ", "_").replace("-", "_")

    fun jour(ms: Long): String = SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).format(Date(ms))

    fun ligneIndividu(ind: JSONObject): List<String> {
        val e = Bestiaire.espece(ind.optString("espece"))
        val st = ind.optJSONObject("stats") ?: JSONObject()
        val fam = o("familles").optString(e?.famille ?: "", "?")
        return listOf(ind.optString("espece", "?"), Guide.typeInd(ind), fam) +
            STATS.map { "${st.optDouble(o("stats").optString(it), 0.0).toInt()}" } +
            listOf(asciiId(Bestiaire.rareteDe(ind)), if (ind.optBoolean("shiny")) "1" else "0",
                asciiId(ind.optString("variante").ifEmpty { "classique" }), jour(ind.optLong("date")), "0")
    }

    fun ligneExemple(x: JSONObject): List<String> {
        val e = Bestiaire.espece(x.optString("espece"))
        val st = x.getJSONObject("stats")
        return listOf(x.optString("espece"), Guide.typeDe(e, x.optString("variante")), o("familles").optString(e?.famille ?: "", "?")) +
            STATS.map { "${st.optInt(o("stats").optString(it))}" } +
            listOf(asciiId(x.optString("rarete")), if (x.optBoolean("shiny")) "1" else "0", asciiId(x.optString("variante")), x.optString("jour"), "1")
    }

    /** (lignes du tableau, nombre de lignes d'exemple ajoutées). */
    fun lignesCollection(captures: JSONArray?): Pair<List<List<String>>, Int> {
        val rows = mutableListOf<List<String>>()
        if (captures != null) for (i in 0 until captures.length()) { val c = captures.getJSONObject(i); if (c.optString("espece").isNotEmpty()) rows.add(ligneIndividu(c)) }
        var ajout = 0
        if (rows.size < donnees().optInt("min_collection", 5))
            for (x in objets(donnees(), "exemples").take(maxOf(0, donnees().optInt("taille_completee", 10) - rows.size))) { rows.add(ligneExemple(x)); ajout++ }
        return rows to ajout
    }

    fun csvTexte(rows: List<List<String>>) = colonnes.joinToString(",") + "\n" + rows.joinToString("") { it.joinToString(",") + "\n" }

    fun lireCsv(texte: String?): List<Map<String, String>> {
        val cols = colonnes
        val out = mutableListOf<Map<String, String>>()
        for ((i, l) in (texte ?: "").lines().let { if ((texte ?: "").endsWith("\n")) it.dropLast(1) else it }.withIndex()) {
            val v = l.split(",")
            if (i == 0 && v.isNotEmpty() && v[0] == cols[0]) continue
            if (v.size != cols.size || !Regex("^-?\\d+$").matches(v[3].trim())) continue
            out.add(cols.zip(v).toMap())
        }
        return out
    }

    fun effectifs(valeurs: List<String>): List<Pair<String, Int>> {
        val c = LinkedHashMap<String, Int>()
        for (v in valeurs) c[v] = (c[v] ?: 0) + 1
        return c.entries.map { it.key to it.value }.sortedWith(compareBy({ -it.second }, { it.first }))
    }

    fun attaques(r: List<Map<String, String>>) = r.map { it["attaque"]!!.trim().toInt() }
    fun forcesTxt(r: List<Map<String, String>>) = r.joinToString("") { "${it["attaque"]} ${it["nom"]}\n" }
    fun especesTxt(r: List<Map<String, String>>) = r.joinToString("") { "${it["nom"]}\n" }
    fun top3(r: List<Map<String, String>>) = attaques(r).sortedDescending().take(3)
    fun nbShiny(r: List<Map<String, String>>) = r.count { it["shiny"] == "1" }
    fun somme(r: List<Map<String, String>>) = attaques(r).sum()
    fun moyenne(r: List<Map<String, String>>): Double = attaques(r).let { if (it.isEmpty()) 0.0 else it.sum().toDouble() / it.size }
    fun medianes(r: List<Map<String, String>>): List<Double> {
        val a = attaques(r).sorted()
        if (a.isEmpty()) return emptyList()
        val n = a.size
        if (n % 2 == 1) return listOf(a[n / 2].toDouble())
        val x = a[n / 2 - 1]; val y = a[n / 2]
        return setOf(x.toDouble(), y.toDouble(), (x + y) / 2.0).sorted()
    }
    fun etendue(r: List<Map<String, String>>) = attaques(r).let { if (it.isEmpty()) 0 else it.max() - it.min() }
    fun typesMajoritaires(r: List<Map<String, String>>): List<String> {
        val e = effectifs(r.map { it["type"]!! })
        return e.filter { it.second == e.firstOrNull()?.second }.map { it.first }
    }
    fun nombreAwk(x: Double) = DonneesAwk.nombre(x)
    fun nombreOk(rep: String?, juste: Double, tolerance: Double = 0.5): Boolean {
        val x = (rep ?: "").trim().replace(",", ".").toDoubleOrNull() ?: return false
        return Math.abs(x - juste) <= tolerance
    }

    // ---------------------------------------------------------------- D3 : le nom mal écrit
    fun cibleFaute(r: List<Map<String, String>>) = effectifs(r.map { it["nom"]!! }).firstOrNull()?.first

    fun faute(nom: String, interdits: Set<String> = emptySet()): String {
        val n = nom.length
        val ordre = (1 until n - 1).sortedWith(compareBy({ Math.abs(it - Math.floorDiv(n - 1, 2)) }, { it }))
        for (i in ordre) {
            val a = nom[i]; val b = nom[i + 1]
            if (a != b && a.isLetter() && b.isLetter() && a.lowercaseChar() == a && b.lowercaseChar() == b) {
                val f = nom.substring(0, i) + b + a + nom.substring(i + 2)
                if (f !in interdits && f != nom) return f
            }
        }
        return nom + nom.last()
    }

    private fun sansBidi(s: String) = s.replace(Regex("[‎‏⁦-⁩]"), "")

    /** (texte mal écrit, texte juste, nom mal écrit, bon nom). */
    fun carnetSoigneur(r: List<Map<String, String>>): List<String> {
        val cible = cibleFaute(r) ?: return listOf("", "", "", "")
        val autres = r.map { it["nom"]!! }.distinct().filter { it != cible }.ifEmpty { listOf(cible) }
        val o3 = (0 until 3).map { autres[it % autres.size] }
        val gab = listOf("dn.carnet.l1" to cible, "dn.carnet.l2" to o3[0], "dn.carnet.l3" to cible, "dn.carnet.l4" to o3[1],
            "dn.carnet.double" to cible, "dn.carnet.l5" to o3[2])
        val juste = listOf("# " + sansBidi(t("dn.carnet.titre"))) + gab.map { sansBidi(t(it.first, "nom" to it.second)) }
        val f = faute(cible, Bestiaire.especes.map { it.nom }.toSet())
        val faux = listOf(juste[0]) + gab.zip(juste.drop(1)).map { (g, l) -> if (g.first in setOf("dn.carnet.l1", "dn.carnet.l3", "dn.carnet.double")) l.replace(cible, f) else l }
        return listOf(faux.joinToString("\n") + "\n", juste.joinToString("\n") + "\n", f, cible)
    }

    // ---------------------------------------------------------------- D-SQL
    fun requetesBase(r: List<Map<String, String>>): List<Pair<String, List<Any?>>> {
        val S = o("schema")
        val out = mutableListOf<Pair<String, List<Any?>>>(S.optString("creatures") to emptyList(), S.optString("especes") to emptyList())
        val entiers = setOf("attaque", "defense", "vitesse", "pv", "intelligence", "shiny", "exemple")
        for (x in r) out.add("INSERT INTO creatures VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)" to colonnes.map { c -> if (c in entiers) x[c]!!.trim().toLong() else x[c] })
        for (nom in r.map { it["nom"]!! }.distinct()) {
            val e = Bestiaire.espece(nom) ?: continue
            out.add("INSERT INTO especes VALUES (?,?,?,?)" to listOf(e.nom, e.numero.toLong(), asciiId(e.habitat), e.puissance.toLong()))
        }
        return out
    }

    // ---------------------------------------------------------------- le laboratoire (vue déployée)
    private val SEPARATEURS = Regex("\\|\\||&&|[|;&]")
    class Labo(val outil: String, val instrument: String, val de: String, val vers: String)
    fun laboDe(morceau: String?): Labo? {
        val m = (morceau ?: "").trim()
        for (r in objets(o("labo"), "regles")) if (Regex(r.optString("motif")).containsMatchIn(m))
            return Labo(r.optString("outil"), r.optString("instrument"), r.optString("de"), r.optString("vers"))
        return null
    }
    fun labosDe(ligne: String?): List<Labo> = (ligne ?: "").split(SEPARATEURS).mapNotNull { laboDe(it) }

    // ================================================================ l'état, le terrain, le carnet
    fun etat(jeu: Jeu): JSONObject {
        val c = jeu.module("donnees")
        if (c.optJSONArray("faits") == null) c.put("faits", JSONArray())
        return c
    }
    private fun fait(jeu: Jeu, cle: String): Boolean {
        if (cle in liste(etat(jeu), "faits")) return true
        etat(jeu).getJSONArray("faits").put(cle)
        return false
    }

    const val CARNET = "carnet_des_donnees.txt"
    const val CSV = "collection.csv"
    fun dossier(jeu: Jeu) = File(jeu.terrain, "donnees")
    fun noter(jeu: Jeu, etiquette: String, texte: String) { try { dossier(jeu).mkdirs(); File(dossier(jeu), CARNET).appendText("[$etiquette] $texte\n") } catch (e: Exception) { } }
    fun carnet(jeu: Jeu): String = try { File(dossier(jeu), CARNET).readText() } catch (e: Exception) { "" }
    fun dansCarnet(jeu: Jeu, etiquette: String, motCle: String = "ok") = Regex("^\\[$etiquette].*\\($motCle\\)\\s*$", RegexOption.MULTILINE).containsMatchIn(carnet(jeu))
    fun dernier(jeu: Jeu, etiquette: String): String? = carnet(jeu).lines().lastOrNull { it.startsWith("[$etiquette]") }
    private fun ecrire(jeu: Jeu, rel: String, contenu: String) = Histoire.ecrire(jeu, "donnees/$rel", contenu, finLigne = false)
    private fun lire(jeu: Jeu, rel: String): String? = Histoire.lire(jeu, "donnees/$rel")
    fun lignesDuFichier(jeu: Jeu): List<Map<String, String>>? = lire(jeu, CSV)?.let { lireCsv(it) }

    fun meubles(jeu: Jeu): Map<String, Any> = linkedMapOf("donnees/laboratoire.txt" to t("dn.meuble.laboratoire") + "\n",
        "donnees/$CARNET" to t("dn.meuble.carnet") + "\n")

    fun meubler(jeu: Jeu, lid: String?) {
        val dd = dossier(jeu)
        if (!dd.isDirectory || lid == null) return
        if (lid == "dn0" && !File(dd, "laboratoire.txt").exists()) ecrire(jeu, "laboratoire.txt", t("dn.meuble.laboratoire") + "\n")
        val e = Programme.donnees().optJSONObject("etapes")?.optJSONObject("$lid.${jeu.etape}")
        if (e != null) for (mid in liste(e, "maths")) {
            if (Maths.noeud(mid) != null && !Maths.sait(jeu, mid) && !fait(jeu, "pont:$mid")) {
                jeu.dire(t("dn.pont", "notion" to Maths.titre(mid), "cmd" to "maths $mid"), 16)
                break
            }
        }
    }

    // ---------------------------------------------------------------- les vérifications des étapes
    fun csvOk(jeu: Jeu) = (lire(jeu, CSV) ?: "").startsWith(colonnes.joinToString(",")) && !lignesDuFichier(jeu).isNullOrEmpty()
    fun top3Ok(jeu: Jeu): Boolean {
        val r = lignesDuFichier(jeu) ?: return false
        val l = (lire(jeu, "top3.txt") ?: return false).lines().filter { it.isNotBlank() }
        val v = l.map { it.trim().split(Regex("\\s+"))[0].toIntOrNull() ?: return false }
        return l.size == 3 && v == top3(r)
    }
    fun texteJuste(jeu: Jeu, rel: String): Boolean {
        val r = lignesDuFichier(jeu) ?: return false
        val x = lire(jeu, rel) ?: return false
        return x.trim('\n') == carnetSoigneur(r)[1].trim('\n')
    }
    fun attaquesOk(jeu: Jeu): Boolean {
        val r = lignesDuFichier(jeu) ?: return false
        val x = lire(jeu, "attaques.txt") ?: return false
        return x.split(Regex("\\s+")).filter { it.isNotEmpty() }.map { it.toIntOrNull() ?: return false } == attaques(r).sorted()
    }
    /** noms.txt et types.txt : la colonne 1 et la colonne 2 (avec ou sans la ligne des titres). */
    fun nomsTypesOk(jeu: Jeu): Boolean {
        val r = lignesDuFichier(jeu) ?: return false
        val n = lire(jeu, "noms.txt") ?: return false
        val ty = lire(jeu, "types.txt") ?: return false
        fun sans(t: String, titre: String) = t.lines().filter { it.isNotBlank() && it != titre }
        return sans(n, "nom") == r.map { it["nom"] } && sans(ty, "type") == r.map { it["type"] }
    }

    fun enclosOk(jeu: Jeu): Boolean {
        val r = lignesDuFichier(jeu) ?: return false
        val f = File(dossier(jeu), "enclos").list()?.toSet() ?: return false
        return r.isNotEmpty() && r.all { "${it["nom"]}.txt" in f }
    }
    private fun rapport(jeu: Jeu) = (lire(jeu, "rapport.txt") ?: "").lines().filter { it.isNotBlank() }
    fun rapportTopOk(jeu: Jeu): Boolean {
        val r = lignesDuFichier(jeu) ?: return false
        val l = rapport(jeu)
        if (l.size < 3) return false
        return l.take(3).map { it.split(",").getOrNull(3)?.trim()?.toIntOrNull() ?: return false } == top3(r)
    }
    fun rapportMoyenneOk(jeu: Jeu): Boolean {
        val r = lignesDuFichier(jeu) ?: return false
        if (!rapportTopOk(jeu)) return false
        return rapport(jeu).drop(3).any { val m = it.trim().split(Regex("\\s+")); m.size == 2 && nombreOk(m[1], moyenne(r), 0.01) }
    }

    // ---------------------------------------------------------------- les leçons du téléphone
    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)
    private const val LS = "^(ls|dir)\\b"
    private const val LIRE = "^(cat|less|more|head|tail)\\b"
    private const val DN = "^(tg\\s+)?donnees\\s+"
    private const val SQ = "^(tg\\s+)?(donnees\\s+)?sqlite3\\s+(-\\w+\\s+)*collection\\.db\\s+"
    private const val O_ = "donnees"
    /** le séparateur virgule est obligatoire : sans -d, cut coupe aux tabulations, sans -F, awk coupe aux espaces */
    private const val CUT_D = "^cut\\b(?=.*-d\\s*['\"]?,)"
    private const val AWK_F = "^awk\\b(?=.*-F\\s*['\"]?,)"

    private fun n(lid: String, i: Any, cmd: String, re: String? = null, fs: ((Jeu) -> Boolean)? = null, ou: String? = null,
                  exploit: String? = null, echoue: Boolean = false, toutCode: Boolean = false) =
        Etape("hist.$lid.$i.dit", cmd, "hist.$lid.$i.bravo", re?.let { r(it) }, fs, null, null, ou, exploit = exploit, echoue = echoue, toutCode = toutCode)

    val IDS = (0..6).map { "dn$it" }

    /** Les leçons du téléphone : les mêmes paliers ; `collection --csv` sans tg ; awk et sqlite3 sont ceux de l'appli. */
    fun lecons(jeu: Jeu): Map<String, Lecon> {
        val carnetOk = { et: String -> { j: Jeu -> dansCarnet(j, et) } }
        return linkedMapOf(
            "dn0" to Lecon("hist.dn0.titre", null, 1, listOf(
                Etape("hist.entree.dit", "cd ~/terrain_terminagotchi/donnees", "hist.entree.bravo", ici = "donnees", params = mapOf("piece" to "donnees")),
                n("dn0", 1, "ls", re = LS, ou = O_),
                n("dn0", 2, "cat laboratoire.txt", re = "$LIRE.*laboratoire", ou = O_),
            )),
            "dn1" to Lecon("hist.dn1.titre", null, 1, listOf(
                n("dn1", 0, "collection --csv > collection.csv", fs = { j -> csvOk(j) }, ou = O_),
                n("dn1", 1, "head -3 collection.csv", re = "$LIRE.*collection\\.csv", ou = O_),
                n("dn1", 2, "wc -l collection.csv", re = "^wc\\b.*collection\\.csv", ou = O_),
                n("dn1", 3, "donnees combien ?", fs = carnetOk("combien")),
                n("dn1", 4, "donnees trier", re = "${DN}tri", ou = O_),
                n("dn1", 5, "sort especes.txt | uniq -c | sort -rn | head -3", re = "^sort\\b.*especes\\.txt.*\\|\\s*uniq\\s+-c", ou = O_),
                n("dn1", 6, "sort -nr forces.txt | head -3 > top3.txt", fs = { j -> top3Ok(j) }, ou = O_),
            )),
            "dn2" to Lecon("hist.dn2.titre", null, 1, listOf(
                n("dn2", 0, "donnees colonnes", re = "${DN}colonnes?\\s*$", ou = O_),
                n("dn2", 1, "head -1 collection.csv | tr ',' '\\n'", re = "^head\\b.*collection\\.csv.*\\|\\s*tr\\b", ou = O_),
                n("dn2", 2, "cut -d, -f2 collection.csv | tail -n +2 | sort | uniq -c", re = "$CUT_D(?=.*-f\\s*2\\b).*collection\\.csv.*\\|.*uniq\\s+-c", ou = O_),
                n("dn2", 3, "cut -d, -f10 collection.csv | grep -c 1", re = "$CUT_D(?=.*-f\\s*10\\b).*\\|\\s*grep\\b", ou = O_, toutCode = true),
                n("dn2", 4, "donnees shiny ?", fs = carnetOk("shiny")),
                n("dn2", 5, "cut -d, -f1 collection.csv > noms.txt && cut -d, -f2 collection.csv > types.txt", fs = { j -> nomsTypesOk(j) }, ou = O_),
                n("dn2", 6, "paste -d: noms.txt types.txt | head -5", re = "^paste\\b.*noms\\.txt.*types\\.txt|^paste\\b.*types\\.txt.*noms", ou = O_),
            )),
            "dn3" to Lecon("hist.dn3.titre", null, 1, listOf(
                n("dn3", 0, "donnees copiste", re = "${DN}copiste", ou = O_),
                n("dn3", 1, "cat carnet_du_soigneur.txt", re = "$LIRE.*carnet_du_soigneur", ou = O_),
                n("dn3", 2, "sed 's/?/?/' carnet_du_soigneur.txt", re = "^sed\\s+(-\\w+\\s+)*(['\"])s/[^/?]+/[^/?]+/\\2\\s+carnet_du_soigneur", ou = O_),
                n("dn3", 3, "sed 's/?/?/g' carnet_du_soigneur.txt > carnet_corrige.txt", fs = { j -> texteJuste(j, "carnet_corrige.txt") }, ou = O_),
                n("dn3", 4, "diff carnet_du_soigneur.txt carnet_corrige.txt", re = "^diff\\b.*carnet_du_soigneur.*carnet_corrige|^diff\\b.*carnet_corrige.*carnet_du", ou = O_, echoue = true),
                n("dn3", 5, "sed -n '2,4p' carnet_corrige.txt", re = "^sed\\s+-n\\s+['\"]?\\d+,\\d+p['\"]?\\s+carnet_corrige", ou = O_),
                n("dn3", 6, "sed -i 's/?/?/g' carnet_du_soigneur.txt", fs = { j -> texteJuste(j, "carnet_du_soigneur.txt") }, ou = O_),
            )),
            "dn4" to Lecon("hist.dn4.titre", null, 1, listOf(
                n("dn4", 0, "donnees calcul", re = "${DN}calcul", ou = O_),
                n("dn4", 1, "awk -F, 'NR<=5 {print \$1, \$4}' collection.csv", re = "$AWK_F.*\\$1.*\\$4.*collection\\.csv", ou = O_),
                n("dn4", 2, "awk -F, 'NR>1 {s+=\$4} END {print s}' collection.csv", re = "$AWK_F.*\\+=\\s*\\$4.*END.*collection\\.csv", ou = O_),
                n("dn4", 3, "awk -F, 'NR>1 {s+=\$4; n++} END {print s/n}' collection.csv", re = "$AWK_F.*\\+=\\s*\\$4.*END.*/.*collection\\.csv", ou = O_),
                n("dn4", 4, "donnees moyenne ?", fs = carnetOk("moyenne"), exploit = "donnees.statistique"),
                n("dn4", 5, "cut -d, -f4 collection.csv | tail -n +2 | sort -n > attaques.txt", fs = { j -> attaquesOk(j) }, ou = O_),
                n("dn4", 6, "donnees mediane ?", fs = carnetOk("mediane")),
                n("dn4", 7, "sed -n '1p;\$p' attaques.txt", re = "^(sed\\b.*attaques\\.txt|head\\b.*attaques\\.txt|tail\\b.*attaques\\.txt)", ou = O_),
                n("dn4", 8, "donnees etendue ?", fs = carnetOk("etendue")),
            )),
            "dn5" to Lecon("hist.dn5.titre", null, 1, listOf(
                n("dn5", 0, "donnees chaine", re = "${DN}cha[iî]ne", ou = O_),
                n("dn5", 1, "grep -E 'eau|glace' collection.csv", re = "^grep\\b.*-\\w*E.*\\|.*collection\\.csv|^egrep\\b.*collection\\.csv", ou = O_, toutCode = true),
                n("dn5", 2, "cut -d, -f1 collection.csv | tail -n +2 | sort -u | xargs echo", re = "$CUT_D.*\\|\\s*xargs\\b", ou = O_),
                n("dn5", 3, "mkdir -p enclos && cut -d, -f1 collection.csv | tail -n +2 | sort -u | xargs -I{} touch enclos/{}.txt", fs = { j -> enclosOk(j) }, ou = O_),
                n("dn5", 4, "sort -t, -k4 -nr collection.csv | head -3 | tee rapport.txt", fs = { j -> rapportTopOk(j) }, ou = O_),
                n("dn5", 5, "awk -F, 'NR>1 {s+=\$4; n++} END {print \"moyenne\", s/n}' collection.csv >> rapport.txt", fs = { j -> rapportMoyenneOk(j) }, ou = O_),
                n("dn5", 6, "donnees bilan", fs = carnetOk("bilan")),
            )),
            "dn6" to Lecon("hist.dn6.titre", null, 1, listOf(
                n("dn6", 0, "donnees base", fs = { j -> File(dossier(j), "collection.db").isFile && dansCarnet(j, "base") }, ou = O_),
                n("dn6", 1, "sqlite3 collection.db .tables", re = "$SQ['\"]?\\.tables", ou = O_),
                n("dn6", 2, "sqlite3 collection.db \".schema creatures\"", re = "$SQ['\"]?\\.schema", ou = O_),
                n("dn6", 3, "sqlite3 collection.db \"SELECT nom, attaque FROM creatures ORDER BY attaque DESC LIMIT 3;\"", re = "$SQ['\"]\\s*select\\b.*\\border\\s+by\\b", ou = O_),
                n("dn6", 4, "sqlite3 collection.db \"SELECT nom, variante FROM creatures WHERE type = 'eau';\"", re = "$SQ['\"]\\s*select\\b.*\\bwhere\\b", ou = O_),
                n("dn6", 5, "sqlite3 collection.db \"SELECT type, COUNT(*) FROM creatures GROUP BY type ORDER BY COUNT(*) DESC, type;\"",
                    re = "$SQ['\"]\\s*select\\b.*\\bcount\\s*\\(.*\\bgroup\\s+by\\b", ou = O_),
                n("dn6", 6, "donnees sql ?", fs = carnetOk("sql")),
                n("dn6", 7, "sqlite3 collection.db \"SELECT c.nom, e.habitat FROM creatures c JOIN especes e ON c.nom = e.nom LIMIT 5;\"", re = "$SQ['\"]\\s*select\\b.*\\bjoin\\b", ou = O_),
                n("dn6", 8, "sqlite3 collection.db \"SELECT AVG(attaque) FROM creatures;\"", re = "$SQ['\"]\\s*select\\b.*\\bavg\\s*\\(", ou = O_),
            )),
        )
    }

    // ---------------------------------------------------------------- l'arbre du Carrefour
    private fun monde(): JSONObject? {
        val ms = Programme.donnees().optJSONArray("mondes") ?: return null
        return (0 until ms.length()).map { ms.getJSONObject(it) }.firstOrNull { it.optString("id") == "donnees" }
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
        if ((0 until deja.length()).any { deja.getString(it) == "donnees" } || Histoire.fini(jeu, "donnees") || !ouvert(jeu)) return false
        deja.put("donnees")
        jeu.log(t("dn.ouvert.log"))
        jeu.dire(Histoire.dire(jeu, "dn.ouvert.dit"), 18)
        return true
    }

    // ---------------------------------------------------------------- les indices
    private val REPONSES = mapOf("donnees combien ?" to "combien", "donnees shiny ?" to "shiny", "donnees moyenne ?" to "moyenne",
        "donnees mediane ?" to "mediane", "donnees etendue ?" to "etendue", "donnees sql ?" to "sql")
    private val TROU = Regex("(^|\\s|/)(\\?|…|<[^>]*>)(\\s|/|$)")

    fun indice(jeu: Jeu, e: Etape, tapees: List<Pair<String, String?>>): String? {
        val les = Histoire.leconCourante(jeu)?.id
        if (les !in IDS) return null
        val lignes = tapees.map { it.first.trim() }
        val cmd = e.cmd
        if (!File(dossier(jeu), CSV).isFile && !cmd.startsWith("collection") && lignes.any { "collection.csv" in it }) return t("dn.indice.pas_de_csv")
        if (cmd.startsWith("collection")) {
            if (lignes.any { Regex("^(tg\\s+)?collection\\b").containsMatchIn(it) && "--csv" !in it }) return t("dn.indice.csv_option")
            if (lignes.any { Regex("^(tg\\s+)?collection\\b.*--csv").containsMatchIn(it) && ">" !in it }) return t("dn.indice.redirection")
        }
        if ("?" in cmd.split(" ") || "/?/" in cmd) {
            if (lignes.any { (r(DN).containsMatchIn(it) || it.startsWith("sed")) && (TROU.containsMatchIn(it) || "/?/" in it) }) return t("dn.indice.trou")
        }
        REPONSES[cmd]?.let { et ->                       // seulement juste après une réponse (pas après cat -n…)
            val der = dernier(jeu, et)
            if (der != null && !der.trimEnd().endsWith("(ok)") && lignes.any { r(DN + et).containsMatchIn(it) }) return t("dn.indice.rep.$et")
        }
        if (cmd.startsWith("sort -nr forces") && lignes.any { it.startsWith("sort") && ">" !in it }) return t("dn.indice.redirection")
        if (cmd.startsWith("sed") && "/g" in cmd && lignes.any { it.startsWith("sed") && !Regex("/g['\"]").containsMatchIn(it) }) return t("dn.indice.sed_g")
        if (cmd.startsWith("sed 's/?/?/g' carnet_du_soigneur.txt >") && lignes.any { Regex("^sed\\b.*/g").containsMatchIn(it) && ">" !in it }) return t("dn.indice.redirection")
        if (cmd.startsWith("awk") && lignes.any { it.startsWith("awk") && "-F" !in it }) return t("dn.indice.awk_f")
        if (cmd.startsWith("cut") && lignes.any { it.startsWith("cut") && "-d" !in it }) return t("dn.indice.cut_d")
        if (cmd.startsWith("sqlite3") && lignes.any { Regex("^sqlite3\\b.*\\bselect\\b", RegexOption.IGNORE_CASE).containsMatchIn(it) && !Regex("['\"]").containsMatchIn(it) })
            return t("dn.indice.guillemets")
        return null
    }

    // ---------------------------------------------------------------- les mots d'une ligne (comme le shell, pour awk et sqlite3)
    /** Les mots d'une ligne, guillemets retirés ; « > » et « >> » à part ; null s'il y a un tuyau, un ; ou un & hors guillemets. */
    fun motsShell(ligne: String): List<String>? {
        val out = mutableListOf<String>()
        val cour = StringBuilder()
        var mot = false
        var q: Char? = null
        var i = 0
        while (i < ligne.length) {
            val c = ligne[i]
            when {
                q == '\'' -> if (c == '\'') q = null else cour.append(c)
                q == '"' -> when {
                    c == '"' -> q = null
                    c == '\\' && i + 1 < ligne.length && ligne[i + 1] in "\"\\$`" -> { i++; cour.append(ligne[i]) }
                    else -> cour.append(c)
                }
                c == '\'' || c == '"' -> { q = c; mot = true }
                c == '\\' && i + 1 < ligne.length -> { i++; cour.append(ligne[i]); mot = true }
                c == '|' || c == ';' || c == '&' || c == '<' || c == '`' -> return null
                c == '>' -> {
                    if (mot) { out.add(cour.toString()); cour.clear(); mot = false }
                    if (i + 1 < ligne.length && ligne[i + 1] == '>') { out.add(">>"); i++ } else out.add(">")
                }
                c.isWhitespace() -> if (mot) { out.add(cour.toString()); cour.clear(); mot = false }
                else -> { cour.append(c); mot = true }
            }
            i++
        }
        if (q != null) return null
        if (mot) out.add(cour.toString())
        return out
    }

    /** (mots sans la redirection, fichier, ajout ?) */
    private fun redirection(m: List<String>): Triple<List<String>, String?, Boolean> {
        val k = m.indexOfFirst { it == ">" || it == ">>" }
        if (k < 0) return Triple(m, null, false)
        return Triple(m.subList(0, k) + m.drop(k + 2), m.getOrNull(k + 1), m[k] == ">>")
    }

    private fun versFichier(jeu: Jeu, ici: File, texte: String, nom: String?, ajout: Boolean): String? {
        nom ?: return texte
        val f = File(nom).let { if (it.isAbsolute) it else File(ici, nom) }
        if (!f.canonicalPath.startsWith(jeu.terrain.canonicalPath + "/")) return t("dn.tel.sqlite_lecture")
        try { if (ajout) f.appendText(texte) else f.writeText(texte) } catch (e: Exception) { return e.message ?: "?" }
        return ""
    }

    /** `collection --csv [> fichier]` : la collection en tableau (l'appli fait elle-même la redirection). */
    fun collectionCsv(jeu: Jeu, ligne: String, ici: File): String {
        val m = motsShell(ligne) ?: return t("dn.tel.awk_tuyau")
        val (_, f, ajout) = redirection(m)
        val (rows, aj) = lignesCollection(Explo.captures(jeu))
        val msg = "📊 " + if (aj > 0) t("dn.csv.exemples", "n" to rows.size - aj, "k" to aj) else t("dn.csv.ok", "n" to rows.size)
        val texte = csvTexte(rows)
        if (f == null) return texte + msg
        val r = versFichier(jeu, ici, texte, f, ajout)
        return if (r.isNullOrEmpty()) msg else r
    }

    /** `awk [-F SEP] 'PROGRAMME' FICHIER… [> fichier]` : le petit awk de l'appli ; null si la ligne a un tuyau (le shell). */
    fun awk(jeu: Jeu, ligne: String, ici: File): String? {
        val m0 = motsShell(ligne) ?: return null
        val (m, f, ajout) = redirection(m0.drop(1))
        var fs: String? = null
        var k = 0
        while (k < m.size && m[k].startsWith("-") && m[k].length > 1) {
            if (m[k] == "-F") { fs = m.getOrNull(k + 1); k += 2 } else if (m[k].startsWith("-F")) { fs = m[k].substring(2); k++ } else return t("dn.tel.awk")
        }
        val prog = m.getOrNull(k) ?: return t("dn.tel.awk")
        val fichiers = m.drop(k + 1)
        if (fichiers.isEmpty()) return t("dn.tel.awk_tuyau")
        val entree = StringBuilder()
        for (x in fichiers) {
            val ff = File(x).let { if (it.isAbsolute) it else File(ici, x) }
            try { entree.append(ff.readText()) } catch (e: Exception) { return "awk: $x: No such file or directory" }
        }
        val (sortie, _) = DonneesAwk.executer(prog, entree.toString(), fs?.replace("\\t", "\t"))
        return versFichier(jeu, ici, sortie, f, ajout)?.let { if (f == null) it.trimEnd('\n') else it }
    }

    /** `sqlite3 [-header] collection.db "REQUÊTE"` : le petit sqlite3 de l'appli (lecture seule). */
    fun sqlite3(jeu: Jeu, ligne: String, ici: File): String {
        val m = motsShell(ligne) ?: return t("dn.tel.sqlite")
        val (texte, _) = DonneesSql.cli(m.drop(1), ici, jeu.terrain)
        return texte
    }

    // ---------------------------------------------------------------- les commandes du jeu
    private fun bloc(cle: String, vararg p: Pair<String, Any?>) = t(cle, *p).split("\n").map { "  $it" }
    private fun sansCsv() = listOf("✋ " + t("dn.pas_de_csv"))

    private fun reponseNombre(jeu: Jeu, et: String, arg: String?, justes: List<Double>, cleOk: String, vararg p: Pair<String, Any?>): List<String> {
        lignesDuFichier(jeu) ?: return sansCsv()
        if (arg == null) return listOf(t("dn.$et.aide"))
        if (justes.any { nombreOk(arg, it) }) { noter(jeu, et, "${arg.trim().take(12)} (ok)"); return listOf("✔ " + t(cleOk, *p)) }
        noter(jeu, et, "${arg.trim().take(12)} (faux)")
        return listOf("✖ " + t("dn.indice.rep.$et"))
    }

    val LABO = listOf("╔═══╦═══╦═══╗  📊", "║ ⚗ ║ ✂ ║ ⚙ ║  ▁▃▅▇", "╠═══╬═══╬═══╣", "║ 🔍║ ✎ ║ 🧮║  ▇▅▃▁", "╚═══╩═══╩═══╝")

    /** donnees [plan|combien|trier|colonnes|shiny|copiste|calcul|moyenne|mediane|etendue|chaine|bilan|base|sql] */
    fun commande(jeu: Jeu, reste: String, ici: File): String {
        val m = reste.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        val sous = asciiId(m.getOrNull(0) ?: "aide")
        val a = m.drop(1).filter { it != "?" && it != "…" }
        val arg = a.joinToString(" ").ifEmpty { null }
        etat(jeu)
        if (sous == "sqlite3") return DonneesSql.cli(motsShell(reste)?.drop(1) ?: emptyList(), ici, jeu.terrain).first
        val rows = lignesDuFichier(jeu)
        val l: List<String> = when (sous) {
            "plan", "labo", "laboratoire", "regles" -> LABO + t("dn.meuble.laboratoire").split("\n")
            "combien" -> when {
                rows == null -> sansCsv()
                arg == null -> listOf(t("dn.combien.aide"))
                arg.trim() == "${rows.size}" -> { noter(jeu, "combien", "${rows.size} (ok)"); listOf("✔ " + t("dn.combien.ok", "n" to rows.size, "l" to rows.size + 1)) }
                else -> { noter(jeu, "combien", "${arg.trim().take(12)} (faux)"); listOf("✖ " + t("dn.indice.rep.combien")) }
            }
            "trier", "tri", "trie" -> if (rows == null) sansCsv() else {
                ecrire(jeu, "especes.txt", especesTxt(rows)); ecrire(jeu, "forces.txt", forcesTxt(rows)); noter(jeu, "trier", "especes forces (ok)")
                listOf("⚙ " + t("dn.trier.titre"), "") + bloc("dn.trier.texte")
            }
            "colonnes", "colonne" -> {
                val txt = colonnes.mapIndexed { i, c -> "${"%2d".format(i + 1)}  ${c.padEnd(13)} " + t("dn.col.$c") }
                ecrire(jeu, "colonnes.txt", txt.joinToString("\n") + "\n"); noter(jeu, "colonnes", "lu (ok)")
                listOf("✂ " + t("dn.colonnes.titre"), "") + txt.map { "  $it" } + "" + bloc("dn.colonnes.texte")
            }
            "shiny" -> when {
                rows == null -> sansCsv()
                arg == null -> listOf(t("dn.shiny.aide"))
                arg.trim() == "${nbShiny(rows)}" -> { val n = nbShiny(rows); noter(jeu, "shiny", "$n (ok)")
                    listOf("✔ " + t("dn.shiny.ok", "n" to n, "total" to rows.size, "pc" to if (rows.isEmpty()) 0 else n * 100 / rows.size)) }
                else -> { noter(jeu, "shiny", "${arg.trim().take(12)} (faux)"); listOf("✖ " + t("dn.indice.rep.shiny")) }
            }
            "copiste" -> if (rows == null) sansCsv() else {
                val c = carnetSoigneur(rows)
                if (!File(dossier(jeu), "carnet_du_soigneur.txt").exists() || !dansCarnet(jeu, "copiste")) ecrire(jeu, "carnet_du_soigneur.txt", c[0])
                noter(jeu, "copiste", "${c[2]} ${c[3]} (ok)")
                listOf("✎ " + t("dn.copiste.titre"), "") + bloc("dn.copiste.texte", "faute" to c[2], "bon" to c[3])
            }
            "calcul", "calculatrice" -> { noter(jeu, "calcul", "lu (ok)"); listOf("🧮 " + t("dn.calcul.titre"), "") + bloc("dn.calcul.texte") + listOf("", "  " + t("dn.tel.awk")) }
            "moyenne" -> { val r = rows ?: emptyList(); val mo = moyenne(r)
                reponseNombre(jeu, "moyenne", arg, listOf(mo), "dn.moyenne.ok", "m" to nombreAwk(mo), "s" to somme(r), "n" to r.size) +
                    (if (dansCarnet(jeu, "moyenne")) listOf("  " + t("dn.moyenne.morale")) else emptyList()) }
            "mediane" -> { val r = rows ?: emptyList(); val ms = medianes(r)
                reponseNombre(jeu, "mediane", arg, ms, "dn.mediane.ok", "m" to ms.joinToString(" / ") { nombreAwk(it) }, "n" to r.size, "moy" to nombreAwk(moyenne(r))) }
            "etendue" -> { val r = rows ?: emptyList(); val at = attaques(r).ifEmpty { listOf(0) }
                reponseNombre(jeu, "etendue", arg, listOf(etendue(r).toDouble()), "dn.etendue.ok", "e" to etendue(r), "max" to at.max(), "min" to at.min()) }
            "chaine", "chaines" -> { noter(jeu, "chaine", "lu (ok)"); listOf("🔗 " + t("dn.chaine.titre"), "") + bloc("dn.chaine.texte") }
            "bilan" -> when {
                rows == null -> sansCsv()
                !(rapportTopOk(jeu) && rapportMoyenneOk(jeu)) -> { noter(jeu, "bilan", "pas encore (faux)"); listOf("✋ " + t("dn.bilan.pas_encore")) }
                else -> {
                    val certif = t("dn.bilan.texte", "n" to rows.size, "especes" to rows.map { it["nom"] }.distinct().size, "top" to top3(rows).first(),
                        "m" to nombreAwk(moyenne(rows)), "shiny" to nbShiny(rows))
                    ecrire(jeu, "certificat_du_savant.txt", certif + "\n"); noter(jeu, "bilan", "rapport (ok)")
                    listOf("🏅 " + t("dn.bilan.titre"), "") + certif.split("\n").map { "  $it" }
                }
            }
            "base" -> if (rows == null) sansCsv() else {
                if (!DonneesSql.moteur.creer(File(dossier(jeu), "collection.db"), requetesBase(rows))) listOf("✖ " + t("dn.base.rate"))
                else { noter(jeu, "base", "${rows.size} (ok)"); listOf("🗄 " + t("dn.base.titre"), "") + bloc("dn.base.texte", "n" to rows.size) + listOf("", "  " + t("dn.tel.sqlite")) }
            }
            "sql" -> when {
                rows == null -> sansCsv()
                arg == null -> listOf(t("dn.sql.aide"))
                asciiId(arg) in typesMajoritaires(rows) -> { noter(jeu, "sql", "${asciiId(arg)} (ok)")
                    listOf("✔ " + t("dn.sql.ok", "type" to asciiId(arg), "n" to effectifs(rows.map { it["type"]!! })[0].second, "total" to rows.size)) }
                else -> { noter(jeu, "sql", "${asciiId(arg).take(12)} (faux)"); listOf("✖ " + t("dn.indice.rep.sql")) }
            }
            else -> LABO + listOf("📊 " + t("dn.aide.titre")) + t("dn.aide.liste").replace("tg collection", "collection").split("\n").map { "  $it" }
        }
        return l.joinToString("\n")
    }
}
