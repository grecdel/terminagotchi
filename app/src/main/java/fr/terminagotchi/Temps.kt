package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.text.Normalizer

/**
 * ⏳ La Bibliothèque du Temps — git (docs/programme.md § 2.13), portage de pc/tg/temps.py.
 *
 * Le téléphone n'a pas git : l'appli a son PETIT GIT (PetitGit.kt), qui range les photos comme git et retrouve les MÊMES
 * empreintes que le vrai (vérifié contre le vrai git : vecteurs donnees/temps/vecteurs.json, tests/jvm/Temps.kt). Les
 * leçons sont les mêmes que sur PC : l'album (init, l'identité d'EXEMPLE dans le dépôt, status, add, commit), remonter
 * le temps (log, diff, restore, la formule perdue retrouvée avec log -S, show et checkout HASH~1 -- fichier), les mondes
 * parallèles (switch -c, merge et son conflit), partager (clone, pull entre dossiers du terrain, .gitignore, remote -v ;
 * push raconté), les empreintes (hash-object = sha1sum, cat-file ; find -newer de la Citadelle, par le vrai shell).
 * Tout reste dans le terrain : aucun serveur, aucun push, aucun compte, jamais --global.
 */
object Temps {
    @Volatile var chargeur: (() -> String?)? = null
    private var d: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("temps.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun donnees(): JSONObject = d ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() }).also { d = it }
    private fun o(k: String) = donnees().optJSONObject(k) ?: JSONObject()
    private fun liste(o: JSONObject?, k: String): List<String> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.get(it).toString() } } ?: emptyList()

    // ---------------------------------------------------------------- la spécification pure (vecteurs communs)
    fun asciiBas(texte: String?): String = Normalizer.normalize(texte ?: "", Normalizer.Form.NFKD)
        .filter { Character.getType(it) != Character.NON_SPACING_MARK.toInt() }.lowercase()

    private fun sha(s: String) = MessageDigest.getInstance("SHA-256").digest(s.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }
    private fun tire(graine: String, sel: String, n: Int) = (sha("$graine:$sel").substring(0, 8).toLong(16) % n).toInt()

    private val G get() = o("grimoire")
    fun secret(graine: String) = tire(graine, "secret", G.optInt("secrets", 5))
    fun ligneSecrete(graine: String) = "${G.optString("mot", "secret")} : " + t("tp.secret.${secret(graine)}")

    class Photo(val message: String, val date: Long, val fichiers: Map<String, String>)

    fun photos(graine: String): List<Photo> {
        val ps = G.optJSONArray("photos") ?: JSONArray()
        return (0 until ps.length()).map { i ->
            val p = ps.getJSONObject(i)
            val f = p.getJSONObject("fichiers")
            val fich = LinkedHashMap<String, String>()
            for (nom in f.keys()) fich[nom] = liste(f, nom).joinToString("") { c -> (if (c == "S") ligneSecrete(graine) else t(c)) + "\n" }
            Photo(t(p.optString("message")), G.optLong("date0") + i * G.optLong("pas"), fich)
        }
    }

    fun grimoireFinal(graine: String): Map<String, String> { val fin = LinkedHashMap<String, String>(); for (p in photos(graine)) fin.putAll(p.fichiers); return fin }
    fun aLeSecret(texte: String?, graine: String) = ligneSecrete(graine) in (texte ?: "").replace("\r\n", "\n").split("\n")

    private val MARQUES = Regex("^(<{7}|={7}|>{7})( |$)", RegexOption.MULTILINE)
    fun sansBornes(texte: String?) = !MARQUES.containsMatchIn((texte ?: "").replace("\r\n", "\n"))
    fun gardeTout(texte: String?, vararg versions: String?): Boolean {
        val l = (texte ?: "").replace("\r\n", "\n").split("\n").toSet()
        return versions.all { v -> (v ?: "").replace("\r\n", "\n").split("\n").filter { it.isNotBlank() }.all { it in l } }
    }

    fun hashOk(reponse: String?, juste: String?, minimum: Int = 4): Boolean {
        val r = (reponse ?: "").trim().lowercase().substringBefore("~").substringBefore("^")
        return !juste.isNullOrEmpty() && r.length >= minimum && r.matches(Regex("[0-9a-f]+")) && juste.startsWith(r)
    }

    fun blobSha(texte: String) = PetitGit.blobSha(texte)

    class Pellicule(val outil: String, val de: String, val vers: String)
    private val SEPARATEURS = Regex("\\|\\||&&|[|;&]")
    fun pelliculeDe(morceau: String?): Pellicule? {
        val m = (morceau ?: "").trim()
        val rs = o("pellicule").optJSONArray("regles") ?: return null
        for (i in 0 until rs.length()) { val r = rs.getJSONObject(i)
            if (Regex(r.optString("motif")).containsMatchIn(m)) return Pellicule(r.optString("outil"), r.optString("de"), r.optString("vers")) }
        return null
    }
    fun pelliculesDe(ligne: String?): List<Pellicule> = (ligne ?: "").split(SEPARATEURS).mapNotNull { pelliculeDe(it) }

    // ---------------------------------------------------------------- l'état, le terrain, le carnet du temps
    fun etat(jeu: Jeu): JSONObject { val c = jeu.module("temps"); if (c.optJSONArray("faits") == null) c.put("faits", JSONArray()); return c }
    private fun fait(jeu: Jeu, cle: String): Boolean { if (cle in liste(etat(jeu), "faits")) return true; etat(jeu).getJSONArray("faits").put(cle); return false }

    const val CARNET = "carnet_du_temps.txt"
    const val ALBUM = "album"; const val GRIMOIRE = "grimoire"; const val COPIE = "copie_de_mon_ami"; const val EMPREINTES = "empreintes"
    fun dossier(jeu: Jeu) = File(jeu.terrain, "temps")
    fun noter(jeu: Jeu, etiquette: String, texte: String) { try { dossier(jeu).mkdirs(); File(dossier(jeu), CARNET).appendText("[$etiquette] $texte\n") } catch (e: Exception) { } }
    fun carnet(jeu: Jeu): String = try { File(dossier(jeu), CARNET).readText() } catch (e: Exception) { "" }
    fun dansCarnet(jeu: Jeu, etiquette: String, mot: String = "ok") = Regex("^\\[$etiquette].*\\($mot\\)\\s*$", RegexOption.MULTILINE).containsMatchIn(carnet(jeu))
    private fun lire(jeu: Jeu, rel: String): String? = try { File(dossier(jeu), rel).takeIf { it.isFile }?.readText() } catch (e: Exception) { null }

    fun depot(jeu: Jeu, nom: String): PetitGit.Depot? = PetitGit.ouvrir(File(dossier(jeu), nom))
    fun aCommit(jeu: Jeu, nom: String, rev: String = "HEAD") = depot(jeu, nom)?.let { PetitGit.resoudre(it, rev) } != null
    fun nbCommits(jeu: Jeu, nom: String, rev: String = "HEAD"): Int = depot(jeu, nom)?.let { d -> PetitGit.resoudre(d, rev)?.let { PetitGit.ordre(d, listOf(it)).size } } ?: 0
    fun parents(jeu: Jeu, nom: String, rev: String = "HEAD"): List<String> = depot(jeu, nom)?.let { d -> PetitGit.resoudre(d, rev)?.let { d.parents(it) } } ?: emptyList()
    fun principale(jeu: Jeu, nom: String): String = depot(jeu, nom)?.let { d -> listOf("main", "master").firstOrNull { d.branches.has(it) } } ?: "main"
    fun montre(jeu: Jeu, nom: String, rev: String, chemin: String): String? = depot(jeu, nom)?.let { d -> PetitGit.resoudre(d, rev)?.let { h -> d.fichiersDe(h)[chemin]?.let { d.blob(it) } } }
    fun historique(jeu: Jeu, nom: String): List<String> = depot(jeu, nom)?.let { d ->
        val out = ArrayList<String>(); var h = d.head(); while (h != null) { out.add(h); h = d.parents(h).firstOrNull() }; out.reversed() } ?: emptyList()

    /** combien de photos de b ne sont pas dans a (git rev-list --count a..b) */
    fun enPlus(jeu: Jeu, nom: String, a: String, b: String): Int = depot(jeu, nom)?.let { d ->
        val ha = PetitGit.resoudre(d, a); val hb = PetitGit.resoudre(d, b) ?: return 0
        (PetitGit.ordre(d, listOf(hb)).toSet() - (ha?.let { PetitGit.ordre(d, listOf(it)).toSet() } ?: emptySet())).size } ?: 0

    private fun moi(nom: String) = o("identites").optJSONObject(nom) ?: JSONObject()

    /** Le grimoire : 6 photos à dates fixes, signées « Bibliothecaire du Temps », l'identité d'exemple de l'apprenti dans
     *  CE dépôt ; les mêmes empreintes que le vrai git (vecteurs). Renvoie « git », « deja » ou « rate ». */
    fun poserGrimoire(jeu: Jeu, neuf: Boolean = false): String {
        val dd = File(dossier(jeu), GRIMOIRE)
        if (neuf && dd.exists()) {
            var k = 1
            while (File(dossier(jeu), "$GRIMOIRE.ancien$k").exists()) k++
            if (!dd.renameTo(File(dossier(jeu), "$GRIMOIRE.ancien$k"))) return "rate"
        }
        if (aCommit(jeu, GRIMOIRE)) return "deja"
        return poserGrimoireDans(dd, jeu.terrain, Histoire.graine(jeu))
    }

    /** le grimoire d'une partie (graine) dans le dossier dd du terrain (aussi pour les tests : vecteurs du vrai git) */
    fun poserGrimoireDans(dd: File, terrain: File, graine: String): String {
        if (dd.exists() && (dd.list()?.isNotEmpty() == true)) return "rate"
        PetitGit.init(dd, terrain, listOf("-q", "-b", "main"))
        val dep = PetitGit.ouvrir(dd) ?: return "rate"
        dep.config.put("user.name", moi("apprenti").optString("nom")).put("user.email", moi("apprenti").optString("email"))
        val bi = moi("bibliothecaire")
        val fz = G.optString("fuseau", "+0000")
        val tz = (if (fz.startsWith("-")) -1 else 1) * (fz.substring(1, 3).toInt() * 60 + fz.substring(3, 5).toInt())
        for (p in photos(graine)) {
            for ((nom, txt) in p.fichiers) { File(dd, nom).writeText(txt); dep.index.put(nom, dep.ajouterBlob(txt)) }
            PetitGit.photographier(dep, p.message + "\n", listOfNotNull(dep.head()), bi.optString("nom") to bi.optString("email"), p.date to tz)
        }
        dep.sauver()
        return "git"
    }

    fun hashPerte(jeu: Jeu): String = historique(jeu, GRIMOIRE).getOrNull(G.optInt("perte", 4)) ?: ""
    fun hashApparition(jeu: Jeu): String = historique(jeu, GRIMOIRE).getOrNull(G.optInt("apparition", 1)) ?: ""
    fun retrouvee(jeu: Jeu) = aLeSecret(lire(jeu, "$GRIMOIRE/grimoire.txt"), Histoire.graine(jeu))
    fun sauvee(jeu: Jeu): Boolean {
        val n = (G.optJSONArray("photos") ?: JSONArray()).length()
        return nbCommits(jeu, GRIMOIRE) > n && aLeSecret(montre(jeu, GRIMOIRE, "HEAD", "grimoire.txt"), Histoire.graine(jeu))
    }
    fun propre(jeu: Jeu): Boolean {
        val txt = lire(jeu, "$GRIMOIRE/grimoire.txt") ?: return false
        val h = montre(jeu, GRIMOIRE, "HEAD", "grimoire.txt") ?: return false
        return txt.replace("\r\n", "\n") == h && "gribouillis" !in txt
    }

    fun enFusion(jeu: Jeu) = depot(jeu, ALBUM)?.fusion != null
    fun resolu(jeu: Jeu): Boolean {
        val txt = lire(jeu, "$ALBUM/chronique.txt") ?: return false
        if (!sansBornes(txt)) return false
        if (enFusion(jeu)) return gardeTout(txt, montre(jeu, ALBUM, "HEAD", "chronique.txt"), montre(jeu, ALBUM, "MERGE_HEAD", "chronique.txt"))
        return parents(jeu, ALBUM).size == 2
    }

    fun amiDans(jeu: Jeu, nom: String): Boolean {
        val d = depot(jeu, nom) ?: return false
        val am = moi("ami").optString("email")
        return d.head()?.let { PetitGit.ordre(d, listOf(it)).any { h -> d.commit(h)?.optString("author")?.contains("<$am>") == true } } ?: false
    }

    fun poserAmi(jeu: Jeu): String {
        val dep = depot(jeu, COPIE) ?: return "pas_de_copie"
        if (dep.head() == null) return "pas_de_copie"
        if (amiDans(jeu, COPIE)) return "deja"
        val am = moi("ami")
        dep.config.put("user.name", am.optString("nom")).put("user.email", am.optString("email"))
        try { File(dep.racine, "chronique.txt").appendText(t("tp.ami.ligne") + "\n") } catch (e: Exception) { return "rate" }
        dep.index.put("chronique.txt", dep.ajouterBlob(File(dep.racine, "chronique.txt").readText()))
        PetitGit.photographier(dep, t("tp.ami.message") + "\n", listOfNotNull(dep.head()))
        dep.sauver()
        return "ok"
    }

    fun poserEmpreintes(jeu: Jeu): Boolean = try {
        val dd = File(dossier(jeu), EMPREINTES).apply { mkdirs() }
        val E = o("empreintes")
        val mot = File(dd, "mot.txt")
        if (!mot.exists()) mot.writeText(E.optString("mot", "temps\n"))
        val maintenant = System.currentTimeMillis()
        val dates = E.optJSONObject("dates") ?: JSONObject()
        for (nom in dates.keys()) {
            val f = File(dd, nom)
            if (!f.exists()) f.writeText(t("tp.empreintes.fichier", "nom" to nom) + "\n")
            f.setLastModified(maintenant - dates.getLong(nom) * 86400_000L)
        }
        mot.setLastModified(maintenant - 4 * 86400_000L)
        true
    } catch (e: Exception) { false }

    fun meubles(jeu: Jeu): Map<String, Any> = linkedMapOf(
        "temps/registre_du_temps.txt" to t("tp.meuble.registre", "nom" to jeu.nom) + "\n",
        "temps/$CARNET" to t("tp.meuble.carnet") + "\n")

    fun meubler(jeu: Jeu, lid: String?) {
        val dd = dossier(jeu)
        if (!dd.isDirectory || lid == null) return
        if (lid == "tp0" && !File(dd, "registre_du_temps.txt").exists()) Histoire.ecrire(jeu, "temps/registre_du_temps.txt", meubles(jeu)["temps/registre_du_temps.txt"]!!, finLigne = false)
        val e = Programme.donnees().optJSONObject("etapes")?.optJSONObject("$lid.${jeu.etape}")
        if (e != null) for (mid in liste(e, "maths")) {
            if (Maths.noeud(mid) != null && !Maths.sait(jeu, mid) && !fait(jeu, "pont:$mid")) { jeu.dire(t("tp.pont", "notion" to Maths.titre(mid), "cmd" to "maths $mid"), 16); break }
        }
    }

    // ---------------------------------------------------------------- les leçons du téléphone
    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)
    private const val LS = "^(ls|dir)\\b"
    private const val LIRE = "^(cat|less|more|head|tail)\\b"
    private const val TP = "^(tg\\s+)?temps\\s+"
    private const val GIT = "^git\\s+"
    private const val AL = "temps/album"; private const val GR = "temps/grimoire"; private const val CO = "temps/copie_de_mon_ami"; private const val EM = "temps/empreintes"
    const val SED = "sed -i '/^[<=>]\\{7\\}/d' chronique.txt"

    private fun n(lid: String, i: Any, cmd: String, re: String? = null, fs: ((Jeu) -> Boolean)? = null, ou: String? = null, ici: String? = null,
                  exploit: String? = null) =
        Etape("hist.$lid.$i.dit", cmd, "hist.$lid.$i.bravo", re?.let { r(it) }, fs, null, null, ou, ici, exploit = exploit)

    val IDS = (0..5).map { "tp$it" }

    fun lecons(jeu: Jeu): Map<String, Lecon> {
        val carnetOk = { et: String -> { j: Jeu -> dansCarnet(j, et) } }
        return linkedMapOf(
            "tp0" to Lecon("hist.tp0.titre", null, 1, listOf(
                Etape("hist.entree.dit", "cd ~/terrain_terminagotchi/temps", "hist.entree.bravo", ici = "temps", params = mapOf("piece" to "temps")),
                n("tp0", 1, "ls", re = LS, ou = "temps"),
                n("tp0", 2, "cat registre_du_temps.txt", re = "$LIRE.*registre_du_temps", ou = "temps"),
            )),
            "tp1" to Lecon("hist.tp1.titre", null, 1, listOf(
                n("tp1", 0, "temps album", re = "${TP}album\\b", ou = "temps"),
                n("tp1", 1, "git init -b main album", fs = { j -> depot(j, ALBUM) != null }, ou = "temps"),
                n("tp1", 2, "cd album", ici = AL),
                n("tp1", 3, "git config user.name \"Apprenti du Temps\"", fs = { j -> depot(j, ALBUM)?.cfg("user.name") != null }, ou = AL),
                n("tp1", 4, "git config user.email \"apprenti@temps.invalid\"", fs = { j -> depot(j, ALBUM)?.cfg("user.email") != null }, ou = AL),
                n("tp1", 5, "echo \"Jour 1\" > chronique.txt", fs = { j -> !lire(j, "$ALBUM/chronique.txt").isNullOrBlank() }, ou = AL),
                n("tp1", 6, "git status", re = "${GIT}status\\b", ou = AL),
                n("tp1", 7, "git add chronique.txt", re = "${GIT}add\\b", ou = AL),
                n("tp1", 8, "git commit -m \"Jour 1\"", fs = { j -> aCommit(j, ALBUM) }, ou = AL),
            )),
            "tp2" to Lecon("hist.tp2.titre", null, 1, listOf(
                n("tp2", 0, "temps grimoire", re = "${TP}grimoire\\b", ou = "temps"),
                n("tp2", 1, "cd ~/terrain_terminagotchi/temps/grimoire", ici = GR),
                n("tp2", 2, "git log --oneline", re = "${GIT}log\\b", ou = GR),
                n("tp2", 3, "echo \"gribouillis\" >> grimoire.txt", re = "(>>\\s*)grimoire\\.txt", ou = GR),
                n("tp2", 4, "git diff", re = "${GIT}diff\\b", ou = GR),
                n("tp2", 5, "git restore grimoire.txt", fs = { j -> propre(j) }, ou = GR),
                n("tp2", 6, "git log --oneline -S secret", re = "${GIT}log\\b.*-S\\s*\\S", ou = GR),
                n("tp2", 7, "git show ?", re = "${GIT}show\\s+[0-9a-fA-F]{4,}", ou = GR),
                n("tp2", 8, "temps perdu ?", fs = carnetOk("perdu")),
                n("tp2", 9, "git checkout ?~1 -- grimoire.txt", fs = { j -> retrouvee(j) }, ou = GR),
                n("tp2", 10, "git commit -am \"Retrouve la formule secrete\"", fs = { j -> sauvee(j) }, ou = GR, exploit = "temps.version"),
            )),
            "tp3" to Lecon("hist.tp3.titre", null, 1, listOf(
                n("tp3", 0, "temps branches", re = "${TP}branches?\\b"),
                n("tp3", 1, "git switch -c reve", fs = { j -> depot(j, ALBUM)?.branches?.has("reve") == true }, ou = AL),
                n("tp3", 2, "echo \"Jour 2 : un reve\" >> chronique.txt", re = "(>>\\s*)chronique\\.txt", ou = AL),
                n("tp3", 3, "git commit -am \"Le reve\"", fs = { j -> aCommit(j, ALBUM, "reve") && enPlus(j, ALBUM, principale(j, ALBUM), "reve") >= 1 }, ou = AL),
                n("tp3", 4, "git switch main", fs = { j -> depot(j, ALBUM)?.refHead() in setOf("main", "master") }, ou = AL),
                n("tp3", 5, "echo \"Jour 2 : une balade\" >> chronique.txt", re = "(>>\\s*)chronique\\.txt", ou = AL),
                n("tp3", 6, "git commit -am \"La balade\"", fs = { j -> depot(j, ALBUM)?.refHead() in setOf("main", "master") && enPlus(j, ALBUM, "reve", "HEAD") >= 1 }, ou = AL),
                n("tp3", 7, "git merge reve", fs = { j -> enFusion(j) || parents(j, ALBUM).size == 2 }, ou = AL),
                n("tp3", 8, "cat chronique.txt", re = "$LIRE.*chronique\\.txt", ou = AL),
                n("tp3", 9, SED, fs = { j -> resolu(j) }, ou = AL),
                n("tp3", 10, "git commit -am \"Reunit les deux histoires\"", fs = { j -> parents(j, ALBUM).size == 2 && !enFusion(j) }, ou = AL),
                n("tp3", 11, "git log --oneline --graph", re = "${GIT}log\\b.*--graph", ou = AL),
            )),
            "tp4" to Lecon("hist.tp4.titre", null, 1, listOf(
                n("tp4", 0, "temps partage", re = "${TP}partage\\b"),
                n("tp4", 1, "git clone . ../copie_de_mon_ami", fs = { j -> aCommit(j, COPIE) }, ou = AL),
                n("tp4", 2, "temps ami", fs = { j -> amiDans(j, COPIE) }),
                n("tp4", 3, "git log --oneline", re = "${GIT}log\\b", ou = AL),
                n("tp4", 4, "git pull ../copie_de_mon_ami", fs = { j -> amiDans(j, ALBUM) }, ou = AL),
                n("tp4", 5, "echo \"*.tmp\" > .gitignore", fs = { j -> "*.tmp" in (lire(j, "$ALBUM/.gitignore") ?: "").lines().map { it.trim() } }, ou = AL),
                n("tp4", 6, "touch brouillon.tmp", re = "^touch\\b.*brouillon\\.tmp", ou = AL),
                n("tp4", 7, "git status", re = "${GIT}status\\b", ou = AL),
                n("tp4", 8, "cd ../copie_de_mon_ami", ici = CO),
                n("tp4", 9, "git remote -v", re = "${GIT}remote\\s+-v\\b", ou = CO),
                n("tp4", 10, "temps bateau", re = "${TP}bateau\\b"),
            )),
            "tp5" to Lecon("hist.tp5.titre", null, 1, listOf(
                n("tp5", 0, "temps empreintes", fs = { j -> File(dossier(j), "$EMPREINTES/mot.txt").isFile }, ou = "temps"),
                n("tp5", 1, "cd ~/terrain_terminagotchi/temps/empreintes", ici = EM),
                n("tp5", 2, "git hash-object mot.txt", re = "${GIT}hash-object\\b.*mot\\.txt", ou = EM),
                n("tp5", 3, "printf 'blob 6\\0temps\\n' | sha1sum", re = "^printf\\b.*blob.*\\|\\s*sha1sum\\b", ou = EM),
                n("tp5", 4, "echo \"Temps\" > mot.txt", re = "^(echo|printf)\\b.*mot\\.txt", ou = EM),
                n("tp5", 5, "git hash-object mot.txt", re = "${GIT}hash-object\\b.*mot\\.txt", ou = EM),
                n("tp5", 6, "cd ../album", ici = AL),
                n("tp5", 7, "git cat-file -p HEAD", re = "${GIT}cat-file\\s+-p\\b", ou = AL),
                n("tp5", 8, "cd ../empreintes", ici = EM),
                n("tp5", 9, "find . -type f -newer repere.txt", re = "^find\\b.*-newer\\s+\\S*repere", ou = EM),
                n("tp5", 10, "temps bilan", fs = { j -> File(dossier(j), "certificat_archiviste.txt").isFile }),
            )),
        )
    }

    // ---------------------------------------------------------------- l'arbre du Carrefour
    private fun monde(): JSONObject? {
        val ms = Programme.donnees().optJSONArray("mondes") ?: return null
        return (0 until ms.length()).map { ms.getJSONObject(it) }.firstOrNull { it.optString("id") == "temps" }
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
        if ((0 until deja.length()).any { deja.getString(it) == "temps" } || Histoire.fini(jeu, "temps") || !ouvert(jeu)) return false
        deja.put("temps")
        jeu.log(t("tp.ouvert.log"))
        jeu.dire(Histoire.dire(jeu, "tp.ouvert.dit"), 18)
        return true
    }

    // ---------------------------------------------------------------- les indices
    val GLOBAL = Regex("(^|[;&|]\\s*)git\\s+config\\s+(.*\\s)?--(global|system)\\b")
    val POUSSE = Regex("(^|[;&|]\\s*)(git\\s+push\\b|gh\\s+(pr|repo|auth)\\b|git\\s+remote\\s+(add|set-url)\\b)")

    fun indice(jeu: Jeu, e: Etape, tapees: List<Pair<String, String?>>): String? {
        val les = Histoire.leconCourante(jeu)?.id
        if (les !in IDS) return null
        val lignes = tapees.map { it.first.trim() }
        if (lignes.any { GLOBAL.containsMatchIn(it) }) return t("tp.indice.global")
        if (lignes.any { Regex("^sudo\\b").containsMatchIn(it) }) return t("tp.indice.sudo")
        if (lignes.any { POUSSE.containsMatchIn(it) }) return t("tp.indice.push")
        if ("?" in e.cmd && lignes.any { ("?" in it || "…" in it) && (r(TP).containsMatchIn(it) || r(GIT).containsMatchIn(it)) }) return t("tp.indice.trou")
        if (e.cmd == "temps perdu ?") {
            val der = carnet(jeu).lines().lastOrNull { it.startsWith("[perdu]") }
            if (der != null && !der.trimEnd().endsWith("(ok)")) return t(if (der.trimEnd().endsWith("(apparue)")) "tp.indice.apparue" else "tp.indice.perdu")
        }
        if (lignes.any { Regex("^git\\s+checkout\\s+[0-9a-f]{4,}\\S*\\s*$").containsMatchIn(it) }) return t("tp.indice.detache")
        if (e.cmd.startsWith("git init") && lignes.any { Regex("^git\\s+init\\s*$").containsMatchIn(it) }) return t("tp.indice.init_nom")
        if (e.cmd.startsWith("git config") && lignes.any { it.startsWith("git config") }) return t("tp.indice.config")
        if (e.cmd.startsWith("git commit") && lignes.any { Regex("^git\\s+commit\\b").containsMatchIn(it) }) {
            if (les == "tp1" && depot(jeu, ALBUM)?.let { it.cfg("user.name") != null && it.cfg("user.email") != null } != true) return t("tp.indice.identite")
            if (les == "tp2" && !retrouvee(jeu)) return t("tp.indice.pas_retrouvee")
            return t("tp.indice.commit")
        }
        if (e.cmd == "git switch main" && lignes.any { Regex("^git\\s+(switch|checkout)\\s+main\\b").containsMatchIn(it) } && principale(jeu, ALBUM) == "master") return t("tp.indice.master")
        if (e.cmd == SED && lignes.any { Regex("^sed\\b(?!.*\\s-i)").containsMatchIn(it) }) return t("tp.indice.sed_i")
        if (e.cmd == SED && lignes.any { it.startsWith("sed") || it.startsWith("edite") }) return t("tp.indice.bornes")
        if (e.cmd.startsWith("git checkout ?~1") && lignes.any { Regex("^git\\s+(checkout|restore)\\b").containsMatchIn(it) }) return t("tp.indice.retrouve")
        if (e.cmd.startsWith("git pull") && lignes.any { Regex("^git\\s+pull\\s*$").containsMatchIn(it) }) return t("tp.indice.pull")
        return null
    }

    // ---------------------------------------------------------------- git … (le petit git) et temps …
    /** git tapé dans l'appli : le petit git, dans le terrain seulement. */
    fun git(jeu: Jeu, ligne: String, ici: File): String {
        val m = Donnees.motsShell(ligne) ?: return t("tp.tel.tuyau")
        if (m.any { it == ">" || it == ">>" }) return t("tp.tel.tuyau")
        val home = jeu.home
        PetitGit.afficher = { p -> try { Racine.virtuel(home, p) } catch (e: Exception) { p } }
        if (!(ici.canonicalPath + File.separator).startsWith(jeu.terrain.canonicalPath + File.separator) && m.getOrNull(1) !in setOf("help", "version", "--version", "hash-object", "--help")) {
            return t("tp.tel.hors_terrain")
        }
        val res = PetitGit.executer(m.drop(1), ici, jeu.terrain)
        val avert = if (GLOBAL.containsMatchIn(ligne)) "\n⚠ " + t("tp.garde.global") else ""
        return res.texte + avert
    }

    private fun bloc(cle: String, vararg p: Pair<String, Any?>) = t(cle, *p).split("\n").map { "  $it" }
    private fun telGit() = listOf("", "  " + t("tp.tel.git"))

    val BIBLIO = listOf("   ╭─────────────╮   ⏳", "╭──┤ ▥ ▥ ▥ ▥ ▥ ▥ ├──╮", "│▥▥│ ▥ ▥ ╭─╮ ▥ ▥ │▥▥│", "│▥▥│ ▥ ▥ │◷│ ▥ ▥ │▥▥│", "│▁▁│▁▁▁▁▁│▒│▁▁▁▁▁│▁▁│")

    fun lignesPerdu(jeu: Jeu, arg: String?): List<String> {
        if (depot(jeu, GRIMOIRE) == null) return listOf(t("tp.perdu.sans_grimoire"))
        if (arg.isNullOrBlank()) return listOf(t("tp.perdu.aide"))
        val h = hashPerte(jeu); val a = hashApparition(jeu)
        if (hashOk(arg, h)) { noter(jeu, "perdu", "${h.take(7)} (ok)"); return listOf("✔ " + t("tp.perdu.ok", "h" to h.take(7)), "  " + t("tp.perdu.suite", "h" to h.take(7))) }
        if (hashOk(arg, a)) { noter(jeu, "perdu", "${a.take(7)} (apparue)"); return listOf("✖ " + t("tp.indice.apparue")) }
        noter(jeu, "perdu", "${asciiBas(arg).take(12)} (faux)")
        return listOf("✖ " + t("tp.indice.perdu"))
    }

    fun bilanOk(jeu: Jeu): Boolean {
        val d = depot(jeu, ALBUM) ?: return false
        val fusion = d.head()?.let { PetitGit.ordre(d, listOf(it)).any { h -> d.parents(h).size == 2 } } ?: false
        return aCommit(jeu, ALBUM) && sauvee(jeu) && fusion && amiDans(jeu, ALBUM)
    }

    fun lignesBilan(jeu: Jeu): List<String> {
        if (!bilanOk(jeu)) return listOf("✖ " + t("tp.bilan.pas_encore"))
        val date = java.text.SimpleDateFormat("yyyy-MM-dd", java.util.Locale.ROOT).format(java.util.Date())
        val texte = t("tp.bilan.texte", "nom" to jeu.nom, "date" to date, "n" to nbCommits(jeu, ALBUM))
        Histoire.ecrire(jeu, "temps/certificat_archiviste.txt", texte + "\n", finLigne = false)
        noter(jeu, "bilan", "archiviste (ok)")
        return listOf("🏅 " + t("tp.bilan.titre"), "") + texte.split("\n").map { "  $it" } + listOf("", "  " + t("tp.bilan.morale"))
    }

    /** temps [plan|album|grimoire [neuf]|perdu HASH|branches|conflit|partage|ami|bateau|empreintes|bilan] */
    fun commande(jeu: Jeu, reste: String, ici: File): String {
        val m = reste.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        val sous = asciiBas(m.getOrNull(0) ?: "aide").replace("-", "_")
        val a = m.drop(1).filter { it != "?" && it != "…" }
        etat(jeu)
        val l: List<String> = when (sous) {
            "plan", "registre", "regles" -> BIBLIO + t("tp.meuble.registre", "nom" to jeu.nom).split("\n")
            "album" -> { noter(jeu, "album", "lu (ok)"); listOf("📷 " + t("tp.album.titre"), "", "  📁 album ─git init─▶ 📁 album + .git ─git add · git commit─▶ 🖼", "") +
                bloc("tp.album.texte") + listOf("", "  🔏 " + t("tp.album.identite")) + telGit() }
            "grimoire" -> { val e = poserGrimoire(jeu, a.firstOrNull()?.let { asciiBas(it) in setOf("neuf", "new", "nouveau") } == true)
                noter(jeu, "grimoire", e + if (e == "rate") " (faux)" else " (ok)")
                listOf("📖 " + t("tp.grimoire.titre"), "") + bloc("tp.grimoire.texte") + listOf("", "  " + t("tp.grimoire.$e")) + telGit() }
            "perdu", "perdue" -> lignesPerdu(jeu, a.firstOrNull())
            "branches", "branche" -> { noter(jeu, "branches", "lu (ok)"); listOf("🌿 " + t("tp.branches.titre"), "", "  ●──●──● main", "       ╲", "        ●── reve", "") + bloc("tp.branches.texte") }
            "conflit" -> listOf("⚔ " + t("tp.conflit.titre"), "", "  <<<<<<< HEAD      " + t("tp.conflit.ici"), "  Jour 2 : une balade",
                "  =======           " + t("tp.conflit.milieu"), "  Jour 2 : un reve", "  >>>>>>> reve      " + t("tp.conflit.la"), "") + bloc("tp.conflit.texte")
            "partage" -> { noter(jeu, "partage", "lu (ok)"); listOf("📚 " + t("tp.partage.titre"), "", "  📁 album ─git clone─▶ 📁 copie_de_mon_ami ─✎─ 🖼 ─git pull─▶ 📁 album", "") + bloc("tp.partage.texte") }
            "ami" -> { val r = poserAmi(jeu); noter(jeu, "ami", r + if (r == "ok" || r == "deja") " (ok)" else " (faux)")
                if (r == "ok" || r == "deja") listOf("✔ " + t("tp.ami.$r"), "  " + t("tp.ami.suite")) else listOf("✖ " + t("tp.ami.$r")) }
            "bateau", "push" -> { noter(jeu, "bateau", "lu (ok)"); listOf("⛵ " + t("tp.bateau.titre"), "", "  📁 album ─git push─▶ ⛵ ─▶ 🏛  " + t("tp.bateau.etagere"), "") + bloc("tp.bateau.texte") }
            "empreintes", "empreinte" -> { val ok = poserEmpreintes(jeu); noter(jeu, "empreintes", if (ok) "posees (ok)" else "rate (faux)")
                listOf("🔏 " + t("tp.empreintes.titre"), "") + bloc("tp.empreintes.texte") + listOf("", "  " + t(if (ok) "tp.empreintes.pose" else "tp.empreintes.rate")) }
            "bilan" -> lignesBilan(jeu)
            else -> BIBLIO + listOf("⏳ " + t("tp.aide.titre")) + t("tp.aide.liste").split("\n").map { "  $it" } + telGit()
        }
        return l.joinToString("\n")
    }
}
