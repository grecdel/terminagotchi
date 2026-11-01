package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.text.Normalizer
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

/**
 * 📟 Le Poste de Contrôle — l'administration système (docs/programme.md § 2.15 et § 7.13 « Linux de A à Z »), portage
 * de pc/tg/controle.py.
 *
 * Mêmes règles que sur PC (les caisses de l'entrepôt et la plus lourde, les pourcentages et les jauges, le compte du
 * PATH, le carnet de bord de chaque partie et ses alertes, les réveils cron — champs, équivalences, prochaine sonnerie —,
 * les familles de distributions mélangées comme random.shuffle de Python, la distribution reconnue, le registre de
 * l'équipage, la vague (suspects tirés, numéros simulés, bilan), le tableau de bord de la vue déployée) : vecteurs
 * communs donnees/controle/vecteurs.json, vérifiés par tests/jvm/Controle.kt.
 *
 * LECTURE SEULE : l'appli lit /proc/meminfo et la place du disque, ne change rien et ne garde rien. Sur le téléphone, il
 * n'y a ni session qui dure (les tâches de fond, export et alias se perdent : le ~/.tgrc joue le rôle du ~/.bashrc), ni
 * journalctl, ni crontab, ni gestionnaire de paquets, ni systemctl, ni /etc/passwd : ces étapes sont RACONTÉES. La vague
 * est SIMULÉE (`controle ps`, `kill PID` ou `controle arrete PID`) : aucun vrai processus n'est lancé ni arrêté.
 */
object Controle {
    @Volatile var chargeur: (() -> String?)? = null
    private var d: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("controle.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun donnees(): JSONObject = d ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() }).also { d = it }
    private fun liste(o: JSONObject?, k: String): List<String> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.get(it).toString() } } ?: emptyList()
    private fun objets(o: JSONObject?, k: String): List<JSONObject> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.getJSONObject(it) } } ?: emptyList()
    private fun entiers(o: JSONObject?, k: String): List<Int> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.getInt(it) } } ?: emptyList()
    private fun o(k: String) = donnees().optJSONObject(k) ?: JSONObject()
    private fun hex(b: ByteArray) = b.joinToString("") { "%02x".format(it) }
    private fun sha(s: String) = hex(MessageDigest.getInstance("SHA-256").digest(s.toByteArray(Charsets.UTF_8)))

    // ================================================================ la spécification pure (vecteurs communs)
    fun asciiBas(texte: String?): String = Normalizer.normalize(texte ?: "", Normalizer.Form.NFKD)
        .filter { Character.getType(it) != Character.NON_SPACING_MARK.toInt() }.lowercase()

    private fun <T> melange(graine: String, sel: String, l: List<T>): List<T> = l.toMutableList().also { PyHasard("$sel:$graine").melanger(it) }
    private fun tire(graine: String, sel: String, n: Int) = (sha("$graine:$sel").substring(0, 8).toLong(16) % n).toInt()

    // ---------------------------------------------------------------- K2 l'entrepôt et les jauges
    fun caisses(graine: String): List<Pair<String, Int>> {
        val e = o("entrepot")
        val tailles = melange(graine, "entrepot", entiers(e, "tailles_kio"))
        return liste(e, "caisses").zip(tailles).sortedBy { it.first }
    }
    fun caisseLourde(graine: String): String = caisses(graine).maxByOrNull { it.second }?.first ?: ""

    fun caisseOctets(graine: String, nom: String): ByteArray {
        val kio = caisses(graine).firstOrNull { it.first == nom }?.second ?: 0
        val out = java.io.ByteArrayOutputStream()
        var k = 0
        val md = MessageDigest.getInstance("SHA-256")
        while (out.size() < kio * 1024) { out.write(md.digest("caisse:$nom:$k".toByteArray())); k++ }
        return out.toByteArray().copyOf(kio * 1024)
    }

    fun caisseOk(reponse: String?, graine: String): Boolean {
        var r = asciiBas((reponse ?: "").trim()).replace("\\", "/").trimEnd('/').substringAfterLast("/")
        if (r.endsWith(".bin")) r = r.dropLast(4)
        return r.isNotEmpty() && r == caisseLourde(graine)
    }

    fun pourcentage(utilise: Long, total: Long): Int = if (total == 0L) 0 else Math.floorDiv(utilise * 200 + total, 2 * total).toInt()
    fun jauge(p0: Int, largeur: Int = 20): String {
        val p = p0.coerceIn(0, 100)
        val n = (p * largeur + 50) / 100
        return "▮".repeat(n) + "▯".repeat(largeur - n)
    }

    // ---------------------------------------------------------------- K3 le carnet d'adresses (PATH)
    fun dossiersPath(path: String?, win: Boolean = false): List<String> = (path ?: "").split(if (win) ";" else ":")
    fun pathOk(reponse: String?, path: String?, win: Boolean = false): Boolean {
        val n = (reponse ?: "").trim().toIntOrNull() ?: return false
        val d = dossiersPath(path, win)
        return n == d.size || n == d.toSet().size || n == d.count { it.isNotEmpty() }
    }

    // ---------------------------------------------------------------- K4 le carnet de bord
    fun journalLignes(graine: String): List<String> {
        val j = o("journal")
        val al = entiers(j, "alertes")
        val nAlertes = al[tire(graine, "alertes", al.size)]
        val total = j.optInt("total")
        val places = melange(graine, "places", (1 until total).toList()).take(nAlertes).sorted().toSet()
        val infos = liste(j, "infos")
        val alertes = melange(graine, "alertes_txt", liste(j, "textes_alerte"))
        val ti = tire(graine, "infos", infos.size)
        var a = 0
        return (0 until total).map { i ->
            val h = (6 * 60 + 7 * i) / 60; val m = (6 * 60 + 7 * i) % 60
            val quand = "%s %02d:%02d:%02d".format(j.optString("jour"), h, m, (13 * i) % 60)
            if (i in places) "$quand ALERTE ${alertes[a++ % alertes.size]}" else "$quand INFO ${infos[(i * 5 + ti) % infos.size]}"
        }
    }
    fun nbAlertes(graine: String) = journalLignes(graine).count { " ALERTE " in it }

    // ---------------------------------------------------------------- K5 les réveils (cron)
    private val CHAMPS = listOf(0 to 59, 0 to 23, 1 to 31, 1 to 12, 0 to 7)
    private val MORCEAU = Regex("(\\*|\\d+(?:-\\d+)?)(?:/(\\d+))?")

    fun champCron(texte: String?, bas: Int, haut: Int): Set<Int>? {
        if (texte.isNullOrEmpty()) return null
        val vals = sortedSetOf<Int>()
        for (morceau in texte.split(",")) {
            val m = MORCEAU.matchEntire(morceau) ?: return null
            val g1 = m.groupValues[1]; val g2 = m.groupValues[2]
            var a: Int; var b: Int
            if (g1 == "*") { a = bas; b = haut }
            else if ("-" in g1) { a = g1.substringBefore("-").toIntOrNull() ?: return null; b = g1.substringAfter("-").toIntOrNull() ?: return null }
            else { a = g1.toIntOrNull() ?: return null; b = a; if (g2.isNotEmpty()) b = haut }
            val pas = if (g2.isNotEmpty()) (g2.toIntOrNull() ?: return null) else 1
            if (pas < 1 || a < bas || b > haut || a > b) return null
            var v = a
            while (v <= b) { vals.add(v); v += pas }
        }
        return vals
    }

    fun cron(ligne: String?): List<Set<Int>>? {
        val mots = (ligne ?: "").trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        if (mots.size < 5 || mots[0].startsWith("#")) return null
        val out = mutableListOf<Set<Int>>()
        for (i in 0 until 5) out.add(champCron(mots[i], CHAMPS[i].first, CHAMPS[i].second) ?: return null)
        if (7 in out[4]) out[4] = (out[4] - 7) + 0
        return out
    }
    fun cronPareil(a: String?, b: String?): Boolean { val ca = cron(a); return ca != null && ca == cron(b) }
    fun cronSituation(graine: String): JSONObject { val s = objets(o("cron"), "situations"); return s[tire(graine, "cron", s.size)] }
    fun cronOk(reponse: String?, graine: String): Boolean =
        cronPareil((reponse ?: "").replace('"', ' ').replace('\'', ' ').trim().split(Regex("\\s+")).joinToString(" "), cronSituation(graine).optString("rep"))

    private fun etoiles(ligne: String): Pair<Boolean, Boolean> {
        val m = ligne.trim().split(Regex("\\s+"))
        return m[2].startsWith("*") to m[4].startsWith("*")
    }
    fun jourOk(c: List<Set<Int>>, et: Pair<Boolean, Boolean>, d: LocalDateTime): Boolean {
        val sem = d.dayOfWeek.value % 7
        return if (et.first || et.second) d.dayOfMonth in c[2] && sem in c[4] else d.dayOfMonth in c[2] || sem in c[4]
    }
    fun prochaine(ligne: String, depuis: LocalDateTime): LocalDateTime? {
        val c = cron(ligne) ?: return null
        val et = etoiles(ligne)
        var d = depuis.withSecond(0).withNano(0).plusMinutes(1)
        val fin = d.plusDays(400)
        while (d < fin) {
            if (d.monthValue !in c[3] || !jourOk(c, et, d)) { d = d.plusDays(1).withHour(0).withMinute(0); continue }
            if (d.hour !in c[1]) { d = d.plusHours(1).withMinute(0); continue }
            if (d.minute in c[0]) return d
            d = d.plusMinutes(1)
        }
        return null
    }

    /** Les lignes d'un fichier crontab : (ligne, valide) sans les commentaires ni les lignes vides. */
    fun lignesCrontab(texte: String?): List<Pair<String, Boolean>> = (texte ?: "").lines().map { it.trim() }
        .filter { it.isNotEmpty() && !it.startsWith("#") }.map { it to (cron(it) != null && it.split(Regex("\\s+")).size > 5) }

    // ---------------------------------------------------------------- Linux de A à Z
    class Carte(val n: Int, val id: String, val rep: String)
    fun famillesCartes(graine: String): List<Carte> =
        melange(graine, "familles", objets(o("familles"), "distributions")).mapIndexed { i, x -> Carte(i + 1, x.optString("id"), x.optString("rep")) }

    fun quizJustes(cartes: List<Carte>, rep: List<String>, lettres: String): Pair<Boolean, List<Carte>> {
        val r = rep.map { asciiBas(it).take(1) }
        if (r.size != cartes.size || r.any { it.isEmpty() || it[0] !in lettres }) return false to emptyList()
        return true to cartes.zip(r).filter { it.first.rep == it.second }.map { it.first }
    }

    fun osReleaseDe(texte: String?): Map<String, String> {
        val out = linkedMapOf<String, String>()
        for (l in (texte ?: "").lines()) if ("=" in l && !l.trimStart().startsWith("#"))
            out[l.substringBefore("=").trim()] = l.substringAfter("=").trim().trim('"').trim('\'')
        return out
    }
    private fun alnum(s: String?) = asciiBas(s).replace(Regex("[^a-z0-9]"), "")
    fun distributionOk(reponse: String?, osr: Map<String, String>): Boolean {
        val r = alnum(reponse)
        if (r.isEmpty() || osr.isEmpty()) return false
        val justes = mutableSetOf(alnum(osr["ID"] ?: ""))
        (osr["ID_LIKE"] ?: "").split(Regex("\\s+")).filter { it.isNotEmpty() }.forEach { justes.add(alnum(it)) }
        osr["NAME"]?.trim()?.split(Regex("\\s+"))?.firstOrNull()?.let { if (osr["NAME"]!!.isNotEmpty()) justes.add(alnum(it)) }
        justes.remove("")
        return r in justes
    }

    fun nomValide(nom: String?) = Regex("[a-z_][a-z0-9_-]{0,15}").matches(nom ?: "")
    fun equipageTexte() = liste(o("equipage"), "base").joinToString("\n") + "\n"
    /** (texte, uid) avec un membre de plus, ou (texte, null) si le nom est déjà là ou n'est pas valide. */
    fun equipageAjoute(texte: String?, nom: String): Pair<String?, Int?> {
        val lignes = (texte ?: "").lines().filter { it.isNotBlank() }
        val noms = lignes.map { it.split(":")[0] }.toSet()
        if (!nomValide(nom) || nom in noms) return texte to null
        val uids = lignes.mapNotNull { it.split(":").getOrNull(2)?.toIntOrNull() }
        val uid = ((uids.filter { it >= 1000 }) + (o("equipage").optInt("uid_depart") - 1)).max() + 1
        return ((lignes + "$nom:x:$uid:$uid::/home/$nom:/bin/bash").joinToString("\n") + "\n") to uid
    }
    fun nouveauxMembres(texte: String?): List<String> {
        val base = liste(o("equipage"), "base").map { it.split(":")[0] }.toSet()
        return (texte ?: "").lines().filter { it.isNotBlank() }.map { it.split(":")[0] }.filter { it !in base }
    }

    // ---------------------------------------------------------------- l'alerte : la vague de processus suspects
    private val V get() = o("vague")
    val VEILLEUR: String get() = V.optString("veilleur", "veilleur_fictif")
    fun vagueSuspects(graine: String, n: Int): List<String> = melange(graine, "vague:$n", liste(V, "suspects")).take(V.optInt("par_vague", 3)).sorted()
    fun pidsSimules(graine: String, n: Int): Map<String, Int> {
        val out = linkedMapOf<String, Int>()
        for (nom in vagueSuspects(graine, n) + VEILLEUR) {
            var p = 2000 + (sha("$graine:$n:$nom").substring(0, 6).toLong(16) % 7000).toInt()
            while (p in out.values) p++
            out[nom] = p
        }
        return out
    }
    fun bilanVague(suspectsVivants: Int, veilleurVivant: Boolean): String =
        if (!veilleurVivant) "veilleur" else if (suspectsVivants == 0) "gagne" else "encore"

    // ---------------------------------------------------------------- le tableau de bord (vue déployée)
    val SEPARATEURS = Regex("\\|\\||&&|[|;&]")
    private val regles: List<Triple<Regex, String, String>> by lazy {
        objets(o("tableau"), "regles").map { Triple(Regex(it.optString("motif"), RegexOption.IGNORE_CASE), it.optString("jauge"), it.optString("sens")) }
    }
    fun tableauDe(morceau: String?): Pair<String, String>? {
        val m = (morceau ?: "").trim()
        return regles.firstOrNull { it.first.containsMatchIn(m) }?.let { it.second to it.third }
    }
    fun tableauxDe(ligne: String?): List<Pair<String, String>> = (ligne ?: "").split(SEPARATEURS).mapNotNull { tableauDe(it) }

    // ================================================================ l'état, le terrain, le registre
    fun etat(jeu: Jeu): JSONObject {
        val c = jeu.module("controle")
        if (c.optJSONArray("faits") == null) c.put("faits", JSONArray())
        if (c.optJSONArray("arretes") == null) c.put("arretes", JSONArray())
        if (!c.has("vague")) c.put("vague", 0)
        return c
    }
    private fun fait(jeu: Jeu, cle: String): Boolean {
        if (cle in liste(etat(jeu), "faits")) return true
        etat(jeu).getJSONArray("faits").put(cle)
        return false
    }

    const val REGISTRE = "registre_du_poste.txt"
    fun dossier(jeu: Jeu) = File(jeu.terrain, "controle")
    fun noter(jeu: Jeu, etiquette: String, texte: String) { try { dossier(jeu).mkdirs(); File(dossier(jeu), REGISTRE).appendText("[$etiquette] $texte\n") } catch (e: Exception) { } }
    fun registre(jeu: Jeu): String = try { File(dossier(jeu), REGISTRE).readText() } catch (e: Exception) { "" }
    fun dansRegistre(jeu: Jeu, etiquette: String, mot: String = "ok") = Regex("^\\[$etiquette].*\\($mot\\)\\s*$", RegexOption.MULTILINE).containsMatchIn(registre(jeu))
    fun dernier(jeu: Jeu, etiquette: String): String? = registre(jeu).lines().lastOrNull { it.startsWith("[$etiquette]") }
    private fun ecrire(jeu: Jeu, rel: String, contenu: Any) = Histoire.ecrire(jeu, "controle/$rel", contenu, finLigne = false)
    private fun lire(jeu: Jeu, rel: String): String? = Histoire.lire(jeu, "controle/$rel")

    fun sacADos(): String = "# ${t("ct.sac.entete")}\n" + liste(o("sac"), "lignes").joinToString("\n") + "\n"
    fun reveilsTexte(): String = t("ct.reveils.entete").split("\n").joinToString("\n") { "# $it" } + "\n" + liste(o("cron"), "exemples").joinToString("\n") + "\n"

    fun meubles(jeu: Jeu): Map<String, Any> {
        val g = Histoire.graine(jeu)
        val m = linkedMapOf<String, Any>("controle/consignes_du_poste.txt" to t("ct.meuble.consignes", "nom" to jeu.nom) + "\n",
            "controle/$REGISTRE" to t("ct.meuble.registre") + "\n", "controle/sac_a_dos.sh" to sacADos(),
            "controle/reveils.crontab" to reveilsTexte(), "controle/equipage.txt" to equipageTexte())
        for ((nom, _k) in caisses(g)) m["controle/entrepot/$nom.bin"] = caisseOctets(g, nom)
        return m
    }

    fun meubler(jeu: Jeu, lid: String?) {
        val dd = dossier(jeu)
        if (!dd.isDirectory || lid == null) return
        for ((rel, x) in meubles(jeu)) if (!File(jeu.terrain, rel).exists() && !rel.endsWith(REGISTRE)) Histoire.ecrire(jeu, rel, x, finLigne = false)
        val e = Programme.donnees().optJSONObject("etapes")?.optJSONObject("$lid.${jeu.etape}")
        if (e != null) for (mid in liste(e, "maths")) {
            if (Maths.noeud(mid) != null && !Maths.sait(jeu, mid) && !fait(jeu, "pont:$mid")) {
                jeu.dire(t("ct.pont", "notion" to Maths.titre(mid), "cmd" to "maths $mid"), 16)
                break
            }
        }
    }

    // ---------------------------------------------------------------- la vague simulée
    fun vivants(jeu: Jeu): List<Pair<Int, String>> {
        val c = etat(jeu)
        val n = c.optInt("vague")
        if (n == 0) return emptyList()
        val arretes = liste(c, "arretes")
        return pidsSimules(Histoire.graine(jeu), n).entries.sortedBy { it.value }.filter { it.key !in arretes }.map { it.value to it.key }
    }
    fun suspectsVivants(jeu: Jeu) = vivants(jeu).filter { it.second != VEILLEUR }
    fun veilleurVivant(jeu: Jeu) = vivants(jeu).any { it.second == VEILLEUR }

    /** `kill PID…` sur le téléphone : seulement les habitants de la vague (simulés) ; sinon null (le vrai shell). */
    fun kill(jeu: Jeu, reste: String): String? {
        val pids = reste.split(Regex("\\s+")).filter { !it.startsWith("-") }.mapNotNull { it.toIntOrNull() }
        if (pids.isEmpty()) return null
        val miens = vivants(jeu).filter { it.first in pids }
        if (miens.isEmpty()) return null
        miens.forEach { etat(jeu).getJSONArray("arretes").put(it.second) }
        return ""
    }

    // ---------------------------------------------------------------- les leçons du téléphone
    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)
    private const val LS = "^(ls|dir)\\b"
    private const val LIRE = "^(cat|less|more|head|tail)\\b"
    private const val CT = "^(tg\\s+)?controle\\s+"
    private const val O_ = "controle"

    private fun n(lid: String, i: Any, cmd: String, re: String? = null, fs: ((Jeu) -> Boolean)? = null, ou: String? = null,
                  reseau: Boolean = false, toutCode: Boolean = false) =
        Etape("hist.$lid.$i.dit", cmd, "hist.$lid.$i.bravo", re?.let { r(it) }, fs, null, null, ou, reseau = reseau, toutCode = toutCode)

    val IDS = (0..7).map { "ct$it" }

    private fun fsReveil(j: Jeu): Boolean {
        val ex = liste(o("cron"), "exemples").map { it.split(Regex("\\s+")).joinToString(" ") }.toSet()
        return lignesCrontab(lire(j, "reveils.crontab")).any { it.second && it.first.split(Regex("\\s+")).joinToString(" ") !in ex }
    }

    /** Les leçons du téléphone : les mêmes paliers ; sans session qui dure, la tâche de fond et l'alias sont racontés,
     *  export et source se font sur UNE ligne ; journalctl, crontab, paquets, services et /etc/passwd sont racontés ;
     *  la vague est simulée. */
    fun lecons(jeu: Jeu): Map<String, Lecon> {
        val regOk = { et: String -> { j: Jeu -> dansRegistre(j, et) } }
        return linkedMapOf(
            "ct0" to Lecon("hist.ct0.titre", null, 1, listOf(
                Etape("hist.entree.dit", "cd ~/terrain_terminagotchi/controle", "hist.entree.bravo", ici = "controle", params = mapOf("piece" to "controle")),
                n("ct0", 1, "ls", re = LS, ou = O_),
                n("ct0", 2, "cat consignes_du_poste.txt", re = "$LIRE.*consignes_du_poste", ou = O_),
            )),
            "ct1" to Lecon("hist.ct1.titre", null, 1, listOf(
                n("ct1", 0, "ps", re = "^ps\\b", ou = O_),
                n("ct1", 1, "echo $$", re = "^echo\\s+\\$\\$\\s*$"),
                n("ct1", 2, "ls /proc/$$", re = "^ls\\b.*/proc/(\\$\\$|self|\\d+)\\s*$", reseau = true),
                n("ct1", 3, "head -3 /proc/$$/status", re = "$LIRE.*/proc/(\\$\\$|self|\\d+)/status", reseau = true),
                n("ct1", 4, "controle habitants", re = "${CT}habitants?\\b"),
                n("ct1", 5, "sleep 5", re = "^sleep\\s+\\d+\\s*$"),
                n("ct1", "t9", "top -n 1 | head -5", re = "^(top|htop)\\b", reseau = true),
            )),
            "ct2" to Lecon("hist.ct2.titre", null, 1, listOf(
                n("ct2", 0, "free -h", re = "^(free|cat\\s+/proc/meminfo)\\b", ou = O_),
                n("ct2", 1, "df -h .", re = "^df\\b", reseau = true),
                n("ct2", 2, "du -sh entrepot/*", re = "^du\\b", ou = O_),
                n("ct2", 3, "controle entrepot ?", fs = regOk("entrepot")),
                n("ct2", 4, "uptime", re = "^uptime\\b", reseau = true),
                n("ct2", 5, "nproc", re = "^(nproc|cat\\s+/proc/cpuinfo)\\b"),
                n("ct2", 6, "controle jauges", re = "${CT}jauges?\\b"),
            )),
            "ct3" to Lecon("hist.ct3.titre", null, 1, listOf(
                n("ct3", 0, "echo \$HOME", re = "^echo\\s+.*\\\$home\\b", ou = O_),
                n("ct3", 1, "echo \$PATH | tr ':' '\\n'", re = "^(echo\\s+\"?\\\$PATH\\b|printenv\\s+PATH\\b)"),
                n("ct3", 2, "controle path ?", fs = regOk("path")),
                n("ct3", 3, "which ls", re = "^(which|command\\s+-v|type)\\s+\\S"),
                n("ct3", "t4", "export COULEUR=bleu; sh -c 'echo \$COULEUR'", re = "^export\\s+[A-Za-z_]\\w*="),   // (la ligne est coupée aux « ; » : le morceau export suffit)
                n("ct3", 7, "cat sac_a_dos.sh", re = "$LIRE.*sac_a_dos", ou = O_),
                n("ct3", "t8", ". ./sac_a_dos.sh; echo \$POSTE", re = "^(source|\\.)\\s+(\\./)?\\S*sac_a_dos\\.sh\\s*$", ou = O_),
            )),
            "ct4" to Lecon("hist.ct4.titre", null, 1, listOf(
                n("ct4", 0, "controle journal", fs = { j -> File(dossier(j), "carnet_de_bord.log").isFile }, ou = O_),
                n("ct4", 1, "tail -n 5 carnet_de_bord.log", re = "^tail\\b(?!.*-\\w*f)", ou = O_),
                n("ct4", 2, "grep -c ALERTE carnet_de_bord.log", re = "(^grep\\b.*-\\w*c.*alerte|alerte.*\\|\\s*wc\\s+-l)", ou = O_, toutCode = true),
                n("ct4", 3, "controle alertes ?", fs = regOk("alertes")),
                n("ct4", "t5", "logcat -d -t 5", re = "^logcat\\b", reseau = true, toutCode = true),
            )),
            "ct5" to Lecon("hist.ct5.titre", null, 1, listOf(
                n("ct5", 0, "controle reveils", re = "${CT}r[eé]veils?\\s*$", ou = O_),
                n("ct5", 2, "cat reveils.crontab", re = "$LIRE.*reveils\\.crontab", ou = O_),
                n("ct5", 3, "controle cron \"? ? ? ? ?\"", fs = regOk("cron")),
                n("ct5", 4, "echo \"*/15 * * * * echo RONDE >> ronde.log\" >> reveils.crontab", fs = { j -> fsReveil(j) }, ou = O_),
                n("ct5", 5, "controle reveils", re = "${CT}r[eé]veils?\\s*$"),
            )),
            "ct6" to Lecon("hist.ct6.titre", null, 1, listOf(
                n("ct6", "t0", "getprop ro.build.version.release", re = "^getprop\\b", ou = O_),
                n("ct6", 1, "controle distribution ?", fs = regOk("distribution")),
                n("ct6", 2, "controle familles", re = "${CT}familles?\\s*$"),
                n("ct6", 3, "controle familles ? ? ? ? ?", fs = regOk("familles")),
                n("ct6", 4, "controle installer", re = "${CT}install"),
                n("ct6", 7, "controle magasin", re = "${CT}magasin\\b"),
                n("ct6", 9, "controle services", re = "${CT}services?\\b"),
                n("ct6", 11, "controle useradd ?", fs = { j -> nouveauxMembres(lire(j, "equipage.txt")).isNotEmpty() }),
                n("ct6", 12, "tail -2 equipage.txt", re = "$LIRE.*equipage", ou = O_),
            )),
            "ct7" to Lecon("hist.ct7.titre", null, 1, listOf(
                n("ct7", 0, "controle alerte", re = "${CT}alerte\\b", ou = O_),
                n("ct7", "t1", "controle ps", re = "${CT}ps\\b"),
                n("ct7", 2, "kill ?", fs = { j -> dansRegistre(j, "vague", "lancee") && suspectsVivants(j).isEmpty() }),
                n("ct7", 3, "controle tableau", fs = { j -> dansRegistre(j, "tableau", "gagne") }),
            )),
        )
    }

    // ---------------------------------------------------------------- l'arbre du Carrefour
    private fun monde(): JSONObject? {
        val ms = Programme.donnees().optJSONArray("mondes") ?: return null
        return (0 until ms.length()).map { ms.getJSONObject(it) }.firstOrNull { it.optString("id") == "controle" }
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
        if ((0 until deja.length()).any { deja.getString(it) == "controle" } || Histoire.fini(jeu, "controle") || !ouvert(jeu)) return false
        deja.put("controle")
        jeu.log(t("ct.ouvert.log"))
        jeu.dire(Histoire.dire(jeu, "ct.ouvert.dit"), 18)
        return true
    }

    // ---------------------------------------------------------------- les indices
    private val REPONSES = mapOf("controle entrepot ?" to "entrepot", "controle path ?" to "path", "controle alertes ?" to "alertes",
        "controle cron \"? ? ? ? ?\"" to "cron", "controle distribution ?" to "distribution", "controle familles ? ? ? ? ?" to "familles",
        "controle useradd ?" to "useradd")
    private val TROU = Regex("(^|\\s|\")(\\?|…|<[^>]*>)(\\s|$|\")")
    val SUDO = Regex("(^|[;&|]\\s*)sudo\\b")
    val CHANGE = Regex("(^|[;&|]\\s*)(sudo\\s+)?((dnf|yum|apt|apt-get|zypper|pacman|snap|flatpak|brew|pm)\\s+(install|uninstall|remove|erase|" +
        "upgrade|update|dist-upgrade|-S\\w*|-R\\w*|-U\\w*)\\b|systemctl\\s+(--user\\s+)?(start|stop|restart|reload|enable|disable|mask|kill|poweroff|reboot)\\b|" +
        "(useradd|userdel|usermod|adduser|deluser|passwd|groupadd)\\b|crontab\\s+(-e|-r)\\b|(shutdown|reboot|poweroff|halt)\\b)", RegexOption.IGNORE_CASE)

    fun indice(jeu: Jeu, e: Etape, tapees: List<Pair<String, String?>>): String? {
        val les = Histoire.leconCourante(jeu)?.id
        if (les !in IDS) return null
        val lignes = tapees.map { it.first.trim() }
        val cmd = e.cmd
        if (lignes.any { SUDO.containsMatchIn(it) }) return t("ct.indice.sudo")
        if (lignes.any { CHANGE.containsMatchIn(it) }) return t("ct.indice.adulte")
        if ("?" in cmd.replace("\"", " ").split(" ") && lignes.filter { r(CT).containsMatchIn(it) || it.startsWith("kill") }.any { TROU.containsMatchIn(it) })
            return t("ct.indice.trou")
        if (cmd.startsWith("controle cron") && lignes.any { r("${CT}cron\\s+[^\"']").containsMatchIn(it) }) return t("ct.indice.guillemets")
        REPONSES[cmd]?.let { et ->
            val der = dernier(jeu, et)
            if (der != null && !der.trimEnd().endsWith("(ok)")) return t("ct.indice.rep.$et")
        }
        if (cmd.startsWith("export") && lignes.any { Regex("^export\\s+\\w+(\\s+=|=\\s)").containsMatchIn(it) }) return t("ct.indice.export_espaces")
        if (cmd.startsWith("kill") || cmd == "controle tableau") {
            if (!veilleurVivant(jeu) && dansRegistre(jeu, "vague", "lancee")) return t("ct.indice.veilleur")
            if (suspectsVivants(jeu).isNotEmpty()) return t("ct.indice.encore", "n" to suspectsVivants(jeu).size)
        }
        if (cmd.startsWith("echo \"*/15") && lignes.any { it.startsWith("echo") && ">" !in it }) return t("ct.indice.ajoute")
        return null
    }

    // ---------------------------------------------------------------- les écrans
    private fun bloc(cle: String, vararg p: Pair<String, Any?>) = t(cle, *p).split("\n").map { "  $it" }

    /** L'entrée du Poste en caractères : le REPLI de l'illustration (le dessin graphique est ControleDessin.poste). */
    val POSTE_DESSIN = listOf("┌────────────────────────┐", "│ ▮▮▮▯ ▮▮▯▯   ◉ ◉ ◉  ⏰  │", "│ ╭──╮ ╭──╮   ▤▤▤▤▤▤     │",
        "│ │◐ │ │◓ │   📟 📟      │", "┴─┴──┴─┴──┴──────────────┴")

    private fun memoire(): Pair<Long, Long>? {
        val txt = try { File("/proc/meminfo").readText() } catch (e: Exception) { return null }
        val tot = Regex("^MemTotal:\\s+(\\d+)", RegexOption.MULTILINE).find(txt)?.groupValues?.get(1)?.toLong() ?: return null
        val dispo = Regex("^MemAvailable:\\s+(\\d+)", RegexOption.MULTILINE).find(txt)?.groupValues?.get(1)?.toLong() ?: return null
        return (tot - dispo) to tot
    }

    fun lignesJauges(jeu: Jeu): List<String> {
        val out = mutableListOf("🎛 " + t("ct.jauges.titre"), "")
        memoire()?.let { (u, tt) -> val p = pourcentage(u, tt); out.add("  🥫 ${t("ct.jauge.memoire")} ${jauge(p)} $p %  (${u / 1024} / ${tt / 1024} Mio)") }
        try {
            val f = jeu.terrain.takeIf { it.exists() } ?: jeu.home
            val tot = f.totalSpace; val libre = f.usableSpace
            if (tot > 0) { val p = pourcentage(tot - libre, tot); out.add("  📦 ${t("ct.jauge.disque")} ${jauge(p)} $p %  (${(tot - libre) shr 30} / ${tot shr 30} Gio)") }
        } catch (e: Exception) { }
        if (out.size == 2) out.add("  " + t("ct.jauges.raconte"))
        noter(jeu, "jauges", "vues (ok)")
        return out + listOf("") + bloc("ct.jauges.texte")
    }

    fun lignesHabitants(jeu: Jeu): List<String> {
        val etats = mutableMapOf<Char, Int>()
        try {
            File("/proc").listFiles()?.filter { it.name.all { c -> c.isDigit() } }?.forEach { p ->
                val s = try { File(p, "stat").readText() } catch (e: Exception) { "" }
                Regex("\\)\\s+(\\w)").find(s)?.groupValues?.get(1)?.firstOrNull()?.let { etats[it] = (etats[it] ?: 0) + 1 }
            }
        } catch (e: Exception) { }
        val out = mutableListOf("👻 " + t("ct.habitants.titre"), "")
        if (etats.isNotEmpty()) {
            val travail = etats['R'] ?: 0
            val dort = (etats['S'] ?: 0) + (etats['I'] ?: 0) + (etats['D'] ?: 0)
            out += listOf("  🏃 $travail  " + t("ct.habitants.travaillent"), "  😴 $dort  " + t("ct.habitants.dorment"), "",
                "  " + t("ct.habitants.total", "n" to etats.values.sum()))
        } else out.add("  " + t("ct.habitants.raconte"))
        noter(jeu, "habitants", "vus (ok)")
        return out + listOf("") + bloc("ct.habitants.texte") + listOf("", "  " + t("ct.tel.sac"))
    }

    private fun reponse(jeu: Jeu, et: String, ok: Boolean, vrai: String, arg: String, okCle: String, vararg p: Pair<String, Any?>, morale: String? = null): List<String> {
        if (ok) { noter(jeu, et, "$vrai (ok)"); return listOf("✔ " + t(okCle, *p)) + (morale?.let { listOf("  " + t(it)) } ?: emptyList()) }
        noter(jeu, et, "${asciiBas(arg).take(30)} (faux)")
        return listOf("✖ " + t("ct.indice.rep.$et"))
    }

    fun lignesReveils(jeu: Jeu): List<String> {
        val out = mutableListOf("⏰ " + t("ct.reveils.titre"), "", "  ┌──────── minute (0-59)", "  │ ┌────── heure (0-23)",
            "  │ │ ┌──── ${t("ct.cron.jour")} (1-31)", "  │ │ │ ┌── ${t("ct.cron.mois")} (1-12)",
            "  │ │ │ │ ┌ ${t("ct.cron.semaine")} (0-7, 0 = 7 = ${t("ct.cron.dimanche")})", "  30 7 * * 1-5  echo REVEIL >> reveil.log", "")
        out += bloc("ct.reveils.texte")
        lire(jeu, "reveils.crontab")?.let { txt ->
            out += listOf("", "📄 reveils.crontab")
            val maintenant = LocalDateTime.now()
            for ((l, ok) in lignesCrontab(txt)) out.add(if (ok) "  ✔ $l  → " + t("ct.reveils.prochaine", "quand" to (prochaine(l, maintenant)?.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm")) ?: "—"))
                else "  ✖ $l  → " + t("ct.reveils.fausse"))
            out.add("  " + t("ct.reveils.jamais_lance"))
        }
        noter(jeu, "reveils", "vus (ok)")
        return out
    }

    fun lignesCron(jeu: Jeu, a: List<String>): List<String> {
        val s = cronSituation(Histoire.graine(jeu))
        if (a.isEmpty()) return listOf("⏰ " + t("ct.cron.question", "situation" to t("ct.cron.s." + s.optString("id"))), "  " + t("ct.cron.aide"))
        val arg = a.joinToString(" ")
        if (cronOk(arg, Histoire.graine(jeu))) {
            noter(jeu, "cron", arg.replace('"', ' ').trim().split(Regex("\\s+")).joinToString(" ") + " (ok)")
            return listOf("✔ " + t("ct.cron.ok", "ligne" to s.optString("rep"), "situation" to t("ct.cron.s." + s.optString("id"))), "  " + t("ct.cron.morale"))
        }
        noter(jeu, "cron", "${arg.take(40)} (faux)")
        return listOf("✖ " + t("ct.indice.rep.cron")) + (if (cron(arg.replace('"', ' ').replace('\'', ' ')) == null) listOf("  " + t("ct.cron.cinq")) else emptyList())
    }

    fun lignesFamilles(jeu: Jeu, rep: List<String>): List<String> {
        val c = famillesCartes(Histoire.graine(jeu))
        val noms = objets(o("familles"), "distributions").associate { it.optString("id") to it.optString("nom") }
        if (rep.isEmpty()) return listOf("🌳 " + t("ct.familles.titre"), "") + t("ct.familles.lettres").split("\n").map { "  $it" } + listOf("") +
            c.map { "  ${it.n}. ${noms[it.id]}" } + listOf("", "  " + t("ct.familles.aide"))
        val (bon, justes) = quizJustes(c, rep, o("familles").optString("lettres", "dap"))
        if (!bon) return listOf(t("ct.familles.aide"))
        val out = mutableListOf<String>()
        if (justes.size == c.size) { noter(jeu, "familles", rep.joinToString(" ") + " (ok)"); out += listOf("✔ " + t("ct.familles.ok"), "  " + t("ct.familles.morale")) }
        else { noter(jeu, "familles", rep.joinToString(" ") + " (faux)"); out.add("✖ " + t("ct.quiz.faux", "n" to justes.size, "total" to c.size)) }
        justes.forEach { out.add("  ✔ ${it.n}. ${noms[it.id]} : " + t("ct.famille.${it.rep}")) }
        return out
    }

    fun lignesUseradd(jeu: Jeu, arg: String?): List<String> {
        if (arg.isNullOrBlank()) return listOf(t("ct.useradd.aide"))
        val nom = arg.trim()
        val txt = lire(jeu, "equipage.txt") ?: equipageTexte()
        if (!nomValide(nom)) { noter(jeu, "useradd", "${asciiBas(nom).take(16)} (invalide)"); return listOf("✖ " + t("ct.indice.rep.useradd")) }
        val (nouveau, uid) = equipageAjoute(txt, nom)
        if (uid == null) { noter(jeu, "useradd", "$nom (deja)"); return listOf("✖ " + t("ct.useradd.deja", "nom" to nom)) }
        ecrire(jeu, "equipage.txt", nouveau ?: txt)
        noter(jeu, "useradd", "$nom $uid (ok)")
        return listOf("✔ " + t("ct.useradd.ok", "nom" to nom, "uid" to uid), "  " + (nouveau ?: "").trimEnd().lines().last(), "") + bloc("ct.useradd.texte")
    }

    fun lignesPs(jeu: Jeu): List<String> {
        val v = vivants(jeu)
        return listOf("%-10s %7s %5s  COMMAND".format("USER", "PID", "%CPU")) +
            (if (v.isEmpty()) listOf("  " + t("ct.ps.aucun")) else v.map { (p, n) -> "%-10s %7d %5s  %s %d".format("equipage", p, "0.0", n, V.optInt("secondes", 900)) }) +
            listOf("  " + t("ct.tel.simule"))
    }

    fun lignesAlerte(jeu: Jeu): List<String> {
        val c = etat(jeu)
        val g = Histoire.graine(jeu)
        val out = mutableListOf<String>()
        val noms: List<String>
        if (suspectsVivants(jeu).isNotEmpty() && veilleurVivant(jeu)) {
            noms = vagueSuspects(g, c.optInt("vague")); out += listOf("🚨 " + t("ct.alerte.encore"), "")
        } else {
            c.put("vague", c.optInt("vague") + 1); c.put("arretes", JSONArray())
            noms = vagueSuspects(g, c.optInt("vague"))
            out += listOf("🚨 " + t("ct.alerte.titre", "n" to c.optInt("vague")), "")
            try {
                dossier(jeu).mkdirs()
                val quand = java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss", java.util.Locale.ROOT).format(java.util.Date())
                File(dossier(jeu), "carnet_de_bord.log").appendText(noms.joinToString("") { "$quand ALERTE $it : ${t("ct.suspect.$it")}\n" } +
                    "$quand INFO $VEILLEUR : ${t("ct.veilleur.journal")}\n")
            } catch (e: Exception) { }
            noter(jeu, "vague", "${c.optInt("vague")} (lancee)")
        }
        noms.forEach { out.add("  ⚠ $it : " + t("ct.suspect.$it")) }
        out.add("  🛡 $VEILLEUR : " + t("ct.veilleur.texte"))
        return out + listOf("") + bloc("ct.alerte.simulee")
    }

    fun lignesArrete(jeu: Jeu, arg: String?): List<String> {
        val pid = arg?.trim()?.toIntOrNull() ?: return listOf(t("ct.arrete.aide"))
        val nom = vivants(jeu).firstOrNull { it.first == pid }?.second ?: return listOf("✖ " + t("ct.arrete.inconnu", "pid" to pid))
        etat(jeu).getJSONArray("arretes").put(nom)
        if (nom == VEILLEUR) return listOf("✖ " + t("ct.indice.veilleur"))
        val reste = suspectsVivants(jeu).size
        return listOf("✔ " + t("ct.arrete.ok", "nom" to nom, "pid" to pid), "  " + if (reste > 0) t("ct.indice.encore", "n" to reste) else t("ct.arrete.tous"))
    }

    fun lignesTableau(jeu: Jeu): List<String> {
        val c = etat(jeu)
        if (c.optInt("vague") == 0 || !dansRegistre(jeu, "vague", "lancee")) return listOf(t("ct.tableau.pas_de_vague"))
        val sv = suspectsVivants(jeu).size; val vv = veilleurVivant(jeu)
        val out = mutableListOf("🎛 " + t("ct.tableau.titre", "n" to c.optInt("vague")), "",
            "  ${if (sv == 0) "✔" else "✖"} " + t("ct.tableau.suspects", "n" to sv),
            "  ${if (vv) "✔" else "✖"} " + t("ct.tableau.veilleur." + if (vv) "oui" else "non"), "")
        when (bilanVague(sv, vv)) {
            "gagne" -> {
                if (dernier(jeu, "tableau")?.startsWith("[tableau] ${c.optInt("vague")} ") != true || !dansRegistre(jeu, "tableau", "gagne"))
                    noter(jeu, "tableau", "${c.optInt("vague")} (gagne)")
                out.add("  " + t("ct.tableau.gagne"))
                Recompenses.exploit(jeu, "controle.vague")?.let { jeu.log(it); jeu.dire(it, 16); out.add(" $it") }
            }
            "veilleur" -> { noter(jeu, "tableau", "${c.optInt("vague")} (veilleur)"); out.add("  " + t("ct.indice.veilleur")) }
            else -> out.add("  " + t("ct.indice.encore", "n" to sv))
        }
        return out
    }

    /** controle [consignes|habitants|entrepot|jauges|path|journal|alertes|reveils|cron|distribution|familles|installer|
     *  magasin|services|useradd|equipage|alerte|ps|arrete|tableau] */
    fun commande(jeu: Jeu, reste: String, ici: File): String {
        val m = reste.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        val sous = asciiBas(m.getOrNull(0) ?: "aide").replace("-", "_")
        val a = m.drop(1).filter { it != "?" && it != "…" }
        val arg = a.joinToString(" ").ifEmpty { null }
        val g = Histoire.graine(jeu)
        etat(jeu)
        val l: List<String> = when (sous) {
            "consignes", "regles", "porte" -> POSTE_DESSIN + t("ct.meuble.consignes", "nom" to jeu.nom).split("\n")
            "habitants", "habitant" -> lignesHabitants(jeu)
            "entrepot", "caisse" -> if (arg == null) listOf(t("ct.entrepot.aide")) else
                reponse(jeu, "entrepot", caisseOk(arg, g), caisseLourde(g), arg, "ct.entrepot.ok", "caisse" to caisseLourde(g),
                    "kio" to (caisses(g).firstOrNull { it.first == caisseLourde(g) }?.second ?: 0), morale = "ct.entrepot.morale")
            "jauges", "jauge" -> lignesJauges(jeu)
            "path", "carnet", "adresses" -> if (arg == null) listOf(t("ct.path.aide")) else
                reponse(jeu, "path", pathOk(arg, System.getenv("PATH")), arg.trim(), arg, "ct.path.ok", "n" to arg.trim(), morale = "ct.path.morale")
            "journal" -> { val lj = journalLignes(g); ecrire(jeu, "carnet_de_bord.log", lj.joinToString("\n") + "\n"); noter(jeu, "journal", "pose (ok)")
                listOf("📓 " + t("ct.journal.titre"), "") + bloc("ct.journal.texte", "n" to lj.size) }
            "alertes" -> when {
                !File(dossier(jeu), "carnet_de_bord.log").isFile -> listOf(t("ct.alertes.sans_journal"))
                arg == null -> listOf(t("ct.alertes.aide"))
                else -> reponse(jeu, "alertes", arg.trim() == "${nbAlertes(g)}", "${nbAlertes(g)}", arg, "ct.alertes.ok", "n" to nbAlertes(g), morale = "ct.alertes.morale")
            }
            "reveils", "reveil" -> lignesReveils(jeu)
            "cron" -> lignesCron(jeu, m.drop(1))
            "distribution", "distrib" -> if (arg == null) listOf(t("ct.distribution.aide")) else
                reponse(jeu, "distribution", distributionOk(arg, mapOf("ID" to "android", "NAME" to "Android")), "android", arg,
                    "ct.distribution.ok", "nom" to "Android", morale = "ct.distribution.morale")
            "familles", "famille" -> lignesFamilles(jeu, a)
            "installer", "installation", "install" -> { noter(jeu, "installer", "lu (ok)"); listOf("💿 " + t("ct.installer.titre"), "") + bloc("ct.installer.texte") }
            "magasin", "paquets" -> { noter(jeu, "magasin", "raconte (ok)"); listOf("🏪 " + t("ct.magasin.titre"), "", "  " + t("ct.magasin.raconte"), "") + bloc("ct.magasin.texte") }
            "services", "service" -> { noter(jeu, "services", "lus (ok)"); listOf("🛡 " + t("ct.services.titre"), "", "  " + t("ct.services.raconte"), "") + bloc("ct.services.texte") }
            "useradd" -> lignesUseradd(jeu, arg)
            "equipage" -> listOf("🧑‍🚀 equipage.txt") + (lire(jeu, "equipage.txt") ?: "").lines().filter { it.isNotBlank() }.map { "  $it" }
            "alerte" -> lignesAlerte(jeu)
            "ps" -> lignesPs(jeu)
            "arrete", "arreter", "kill" -> lignesArrete(jeu, arg)
            "tableau" -> lignesTableau(jeu)
            else -> POSTE_DESSIN + listOf("📟 " + t("ct.aide.titre")) + t("ct.aide.liste").split("\n").map { "  $it" }
        }
        return l.joinToString("\n")
    }
}
