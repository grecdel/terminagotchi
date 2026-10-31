package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.text.Normalizer
import kotlin.math.abs
import kotlin.math.max

/**
 * ⚙ La Salle des Machines — le matériel et l'infrastructure (docs/programme.md § 7.3, § 7.13 M5 bis), portage de
 * pc/tg/machines.py.
 *
 * Mêmes règles que sur PC (les pièces qu'une commande interroge, les interrupteurs, les unités, la mémoire lue dans free,
 * les cartes du réveil, l'orchestre et les boîtes mélangés comme random.shuffle de Python, le besoin et le drapeau de
 * l'épreuve, la vérification d'une machine montée, la maison dans la maison) : vecteurs communs
 * donnees/machines/vecteurs.json, vérifiés par tests/jvm/Machines.kt. LECTURE SEULE : rien n'est écrit hors de
 * terrain_terminagotchi/machines/, aucune donnée personnelle n'est enregistrée ni envoyée. Les réponses (cœurs, mémoire)
 * sont calculées par l'appli sur le même téléphone.
 *
 * Sur le téléphone, beaucoup est RACONTÉ : pas de lspci ni de lsusb (tout est sur une seule puce), pas de conteneur ni
 * de machine virtuelle (M5 bis se raconte avec `machines adulte`, `machines conteneur`, `machines vm`), pas de
 * /proc/1/cgroup lisible. `getprop` remplace lspci et /etc/os-release ; `echo -n A | xxd -b` est intégré (le xxd du
 * téléphone n'a pas -b).
 */
object Machines {
    @Volatile var chargeur: (() -> String?)? = null
    private var d: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("machines.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun donnees(): JSONObject = d ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() }).also { d = it }

    private fun liste(o: JSONObject?, k: String): List<String> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.get(it).toString() } } ?: emptyList()
    private fun objets(o: JSONObject?, k: String): List<JSONObject> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.getJSONObject(it) } } ?: emptyList()
    private fun sha(s: String) = MessageDigest.getInstance("SHA-256").digest(s.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it) }

    // ---------------------------------------------------------------- la spécification pure (vecteurs communs)
    val PIECES: List<String> get() = liste(donnees(), "pieces")
    val CATEGORIES: List<String> get() = liste(donnees(), "categories")
    private val SEPARATEURS = Regex("\\|\\||&&|[|;&]")

    /** Les pièces de l'ordinateur qu'une ligne interroge (nproc → processeur, free → mémoire…). */
    fun piecesDe(ligne: String?): List<String> {
        val al = donnees().optJSONObject("allume") ?: JSONObject()
        val morceaux = (ligne ?: "").split(SEPARATEURS).map { it.trim() }.filter { it.isNotEmpty() }
        return PIECES.filter { p -> val motifs = liste(al, p).map { Regex(it, RegexOption.IGNORE_CASE) }
            morceaux.any { m -> motifs.any { it.containsMatchIn(m) } } }
    }

    fun bits(octet: Int) = Integer.toBinaryString((octet and 255) or 256).substring(1)

    /** [(caractère, [8 bits par octet UTF-8])] : « é » prend deux octets, un emoji quatre. */
    fun interrupteurs(mot: String): List<Pair<String, List<String>>> {
        val out = mutableListOf<Pair<String, List<String>>>()
        var i = 0
        while (i < mot.length) {
            val cp = mot.codePointAt(i)
            val c = String(Character.toChars(cp))
            out.add(c to c.toByteArray(Charsets.UTF_8).map { bits(it.toInt()) })
            i += Character.charCount(cp)
        }
        return out
    }

    fun asciiBas(texte: String) = Normalizer.normalize(texte, Normalizer.Form.NFKD).filter { Character.getType(it) != Character.NON_SPACING_MARK.toInt() }

    /** La lettre du défi des interrupteurs : la première lettre A-Z du nom de la créature (sans accent), sinon A. */
    fun lettreDefi(nom: String): Char = asciiBas(nom).uppercase().firstOrNull { it in 'A'..'Z' } ?: 'A'

    fun unites(n: Long): Map<String, Double> = mapOf("octets" to n.toDouble(), "ko" to n / 1000.0, "kio" to n / 1024.0,
        "mo" to n / 1e6, "mio" to n / 1048576.0, "go" to n / 1e9, "gio" to n / 1073741824.0)

    fun nombre(texte: String?): Pair<Double, String>? {
        val m = Regex("^\\s*(\\d+(?:[.,]\\d+)?)\\s*([A-Za-z]*)").find(texte ?: "") ?: return null
        return m.groupValues[1].replace(",", ".").toDouble() to m.groupValues[2].lowercase()
    }

    /** La réponse de l'enfant (lue dans free -h) est-elle la mémoire du téléphone (MemTotal en Kio), à 10 % près ? */
    fun memoireOk(reponse: String?, kio: Long?): Boolean {
        val (v, u) = nombre(reponse) ?: return false
        if (kio == null || kio == 0L) return false
        val octets = kio * 1024.0
        val grands = listOf(octets / 1073741824.0, octets / 1e9)
        val petits = listOf(octets / 1048576.0, octets / 1e6)
        if (u.startsWith("k") || (u.isEmpty() && v > 50000)) return abs(v - kio) <= 0.1 * kio   // MemTotal de /proc/meminfo, en kB
        val cand = when {
            u.startsWith("m") -> petits
            u.startsWith("g") -> grands
            u.startsWith("t") -> grands.map { it / 1024 }
            else -> grands + (if (octets < 4 * 1073741824.0) petits else emptyList())
        }
        return cand.any { c -> abs(v - c) <= max(if (c < 100) 0.6 else 64.0, 0.1 * c) }
    }

    private fun <T> melange(graine: String, sel: String, l: List<T>): List<T> = l.toMutableList().also { PyHasard("$sel:$graine").melanger(it) }
    const val LETTRES = "ABCDE"

    fun reveilCartes(graine: String): List<Pair<Char, String>> = LETTRES.toList().zip(melange(graine, "reveil", liste(donnees(), "reveil")))
    fun reveilReponse(graine: String): List<Char> { val pos = reveilCartes(graine).associate { it.second to it.first }; return liste(donnees(), "reveil").map { pos[it]!! } }

    fun orchestre(graine: String): List<Triple<Int, String, Char>> {
        val o = donnees().optJSONObject("orchestre") ?: JSONObject()
        val mus = liste(o, "musiciens")
        return melange(graine, "orchestre", objets(o, "taches")).mapIndexed { i, x -> Triple(i + 1, x.optString("id"), LETTRES[mus.indexOf(x.optString("rep"))]) }
    }

    fun rangeBoites(graine: String): List<Triple<Int, String, String>> =
        melange(graine, "range", objets(donnees(), "range")).mapIndexed { i, x -> Triple(i + 1, x.optString("id"), x.optString("rep")) }

    fun besoinEpreuve(graine: String): String { val e = liste(donnees(), "epreuve"); return e[(sha("$graine:besoin").substring(0, 8).toLong(16) % e.size).toInt()] }
    fun drapeau(graine: String) = "TG{" + besoinEpreuve(graine) + "-" + sha("$graine:drapeau").substring(0, 8) + "}"

    /** (catégorie, pièce) d'un identifiant du catalogue, ou null. */
    fun piece(pid: String): Pair<String, JSONObject>? {
        val cat = donnees().optJSONObject("catalogue") ?: return null
        for (c in CATEGORIES) for (x in objets(cat, c)) if (x.optString("id") == pid.uppercase()) return c to x
        return null
    }

    class Montage(val problemes: List<String>, val points: Int, val watts: Int, val fournit: Int, val coeurs: Int, val gio: Int, val go: Int)

    /** Vérifie une machine montée (même spécification que machines.montage sur PC). */
    fun montage(choix: List<String>, besoin: String): Montage {
        val pb = mutableListOf<String>()
        val pris = LinkedHashMap<String, JSONObject>()
        for (pid in choix) {
            val x = piece(pid)
            when {
                x == null -> pb.add("inconnu:" + pid.uppercase())
                x.first in pris -> pb.add("double:" + x.first)
                else -> pris[x.first] = x.second
            }
        }
        for (c in CATEGORIES) if (c !in pris) pb.add("manque:$c")
        val P = pris["processeur"]; val C = pris["carte_mere"]; val M = pris["memoire"]; val S = pris["stockage"]; val G = pris["graphique"]; val A = pris["alimentation"]
        val points = pris.values.sumOf { it.optInt("points") }
        val watts = pris.filter { it.key != "alimentation" }.values.sumOf { it.optInt("watts") }
        val fournit = A?.optInt("fournit") ?: 0
        if (P != null && C != null && P.optString("prise") != C.optString("prise")) pb.add("prise")
        if (M != null && C != null && M.optInt("type") != C.optInt("type")) pb.add("memoire")
        if (A != null && watts > fournit) pb.add("alimentation")
        val b = donnees().optJSONObject("besoins")?.optJSONObject(besoin) ?: JSONObject()
        if (points > b.optInt("budget", 999)) pb.add("budget")
        if (b.optBoolean("graphique") && G != null && G.optBoolean("aucune")) pb.add("besoin:graphique")
        if (b.optBoolean("sans_graphique") && G != null && !G.optBoolean("aucune")) pb.add("besoin:sans_graphique")
        if (M != null && M.optInt("gio") < b.optInt("gio", 0)) pb.add("besoin:gio")
        if (S != null && S.optInt("go") < b.optInt("go", 0)) pb.add("besoin:go")
        if (P != null && P.optInt("coeurs") < b.optInt("coeurs", 0)) pb.add("besoin:coeurs")
        if (b.has("watts_max") && watts > b.optInt("watts_max")) pb.add("besoin:watts")
        if (b.optBoolean("mini") && C != null && !C.optBoolean("mini")) pb.add("besoin:mini")
        return Montage(pb, points, watts, fournit, P?.optInt("coeurs") ?: 0, M?.optInt("gio") ?: 0, S?.optInt("go") ?: 0)
    }

    fun energie(watts: Int, heures: Int): Pair<Long, Double> = (watts.toLong() * heures) to watts.toDouble() * heures / 1000

    /** La maison dans la maison : (vm : le processeur annonce « hypervisor », conteneur : docker / podman / conteneur / null). */
    fun boiteDe(cpuinfo: String, cgroup: String, dockerenv: Boolean = false, containerenv: Boolean = false): Pair<Boolean, String?> {
        val vm = Regex("^flags\\s*:.*\\bhypervisor\\b", RegexOption.MULTILINE).containsMatchIn(cpuinfo)
        val c = when {
            dockerenv -> "docker"
            containerenv -> "podman"
            Regex("(docker|kubepods|containerd|lxc|libpod)").containsMatchIn(cgroup) -> "conteneur"
            else -> null
        }
        return vm to c
    }

    // ---------------------------------------------------------------- le vrai téléphone (lu, jamais modifié)
    private fun lireSys(c: String) = try { File(c).readText() } catch (e: Exception) { "" }
    fun coeurs() = Runtime.getRuntime().availableProcessors()
    fun processeursCpuinfo(): Int? = Regex("^processor\\s*:", RegexOption.MULTILINE).findAll(lireSys("/proc/cpuinfo")).count().takeIf { it > 0 }
    private fun plage(s: String): Int? = try { s.trim().split(",").sumOf { p -> p.split("-").let { if (it.size == 2) it[1].toInt() - it[0].toInt() + 1 else 1 } } } catch (e: Exception) { null }
    /** Les réponses justes à « combien de cœurs ? » : nproc (cœurs en ligne), /proc/cpuinfo, et les cœurs présents
     *  (un téléphone éteint parfois des cœurs pour économiser la batterie). */
    fun coeursJustes(): Set<Int> = setOfNotNull(coeurs(), processeursCpuinfo(), plage(lireSys("/sys/devices/system/cpu/present")),
        plage(lireSys("/sys/devices/system/cpu/online")))
    fun memoireKio(): Long? = Regex("^MemTotal:\\s+(\\d+)\\s*kB", RegexOption.MULTILINE).find(lireSys("/proc/meminfo"))?.groupValues?.get(1)?.toLong()
    fun noyau(): String = System.getProperty("os.version") ?: "?"
    fun allumeeDepuis(): Long? = lireSys("/proc/uptime").split(" ").firstOrNull()?.toDoubleOrNull()?.let { (it / 60).toLong() }

    // ---------------------------------------------------------------- l'état, le terrain, le carnet de la salle
    fun etat(jeu: Jeu): JSONObject {
        val c = jeu.module("machinerie")
        if (c.optJSONArray("faits") == null) c.put("faits", JSONArray())
        if (c.optJSONArray("allumees") == null) c.put("allumees", JSONArray())
        return c
    }

    private fun faits(jeu: Jeu) = liste(etat(jeu), "faits")
    private fun fait(jeu: Jeu, cle: String): Boolean {
        if (cle in faits(jeu)) return true
        etat(jeu).getJSONArray("faits").put(cle)
        return false
    }

    const val CARNET = "carnet_de_la_salle.txt"
    fun dossier(jeu: Jeu) = File(jeu.terrain, "machines")
    fun noter(jeu: Jeu, etiquette: String, texte: String) {
        try { dossier(jeu).mkdirs(); File(dossier(jeu), CARNET).appendText("[$etiquette] $texte\n") } catch (e: Exception) { }
    }
    fun carnet(jeu: Jeu): String = try { File(dossier(jeu), CARNET).readText() } catch (e: Exception) { "" }
    fun dansCarnet(jeu: Jeu, etiquette: String, mot: String = "ok") =
        Regex("^\\[$etiquette].*\\($mot\\)\\s*$", RegexOption.MULTILINE).containsMatchIn(carnet(jeu))
    fun lire(jeu: Jeu, rel: String) = Histoire.lire(jeu, "machines/$rel") ?: ""
    private fun ecrire(jeu: Jeu, rel: String, contenu: Any) = Histoire.ecrire(jeu, "machines/$rel", contenu, finLigne = false)
    private fun sur(s: String) = s.replace(Regex("[\"$`\\\\]"), "'")

    fun photo(): ByteArray { val n = donnees().optJSONObject("photo")?.optInt("octets", 1048576) ?: 1048576; return ByteArray(n) { (it % 256).toByte() } }

    /** la première ligne de la collection, jamais traduite : le jeu reconnaît la collection intacte dans toutes les langues */
    const val MARQUE = "# terminagotchi: collection"

    fun collectionTexte(jeu: Jeu): String {
        val caps = Explo.captures(jeu)
        val noms = (0 until caps.length()).map { caps.getJSONObject(it).optString("espece") }.map { Bestiaire.espece(it)?.nom ?: it }
        val l = listOf(MARQUE, t("ma.collection.titre")) + noms.mapIndexed { i, n -> "${i + 1}. $n" } + (if (noms.isEmpty()) listOf(t("ma.collection.vide")) else emptyList())
        return l.joinToString("\n") + "\n"
    }

    fun conteneurSh(): String {
        val c = donnees().optJSONObject("conteneur") ?: JSONObject()
        val mo = c.optInt("taille_mo", 4)
        return "#!/bin/sh\n# ${sur(t("ma.sh.c1"))}\n# ${sur(t("ma.sh.c2"))}\n# ${sur(t("ma.sh.c3"))}\n" +
            "ICI=\$(cd \"\$(dirname \"\$0\")\" && pwd)\nD=\"\$ICI/${c.optString("dossier", "conteneurs")}\"\nIMAGE=${c.optString("image")}\n" +
            "P=\"podman --root \$D/stockage --runroot \$D/run --tmpdir \$D/tmp\"\n" +
            "absent() {\n  echo \"${sur(t("ma.sh.absent"))}\"\n" +
            "  echo \"[conteneur] podman absent (raconte)\" >> \"\$ICI/$CARNET\"\n  exit 1\n}\n" +
            "case \"\$1\" in\nlancer)\n  command -v podman >/dev/null 2>&1 || absent\n  mkdir -p \"\$D/stockage\" \"\$D/run\" \"\$D/tmp\" \"\$D/xdg\" && chmod 700 \"\$D/run\"\n" +
            "  echo \"${sur(t("ma.sh.lance", "mo" to mo))}\"\n  echo \"  podman run --rm --network=none \$IMAGE echo bonjour\"\n" +
            "  T=\"\"; command -v timeout >/dev/null 2>&1 && T=\"timeout 300\"\n" +
            "  if env XDG_RUNTIME_DIR=\"\$D/run\" XDG_DATA_HOME=\"\$D/xdg\" XDG_CONFIG_HOME=\"\$D/xdg\" \\\n" +
            "       \$T \$P run --rm --network=none \$IMAGE echo bonjour; then\n    echo \"${sur(t("ma.sh.ps"))}\"\n" +
            "    env XDG_RUNTIME_DIR=\"\$D/run\" XDG_DATA_HOME=\"\$D/xdg\" XDG_CONFIG_HOME=\"\$D/xdg\" \$P ps -a\n" +
            "    echo \"[conteneur] alpine (ok)\" >> \"\$ICI/$CARNET\"\n  else\n    echo \"${sur(t("ma.sh.echec"))}\"\n" +
            "    echo \"[conteneur] alpine (echec)\" >> \"\$ICI/$CARNET\"\n    exit 1\n  fi ;;\neffacer)\n" +
            "  command -v podman >/dev/null 2>&1 || absent\n  env XDG_RUNTIME_DIR=\"\$D/run\" XDG_DATA_HOME=\"\$D/xdg\" XDG_CONFIG_HOME=\"\$D/xdg\" \$P system reset --force\n" +
            "  echo \"${sur(t("ma.sh.efface"))}\" ;;\n*)\n  echo \"${sur(t("ma.sh.explique1"))}\"\n" +
            "  echo \"${sur(t("ma.sh.explique2", "mo" to mo))}\"\n  echo \"  \$IMAGE\"\n  echo \"${sur(t("ma.sh.explique3"))}\"\n" +
            "  echo \"  sh conteneur_jetable.sh lancer\"\n" +
            "  command -v podman >/dev/null 2>&1 || echo \"${sur(t("ma.sh.absent"))}\" ;;\nesac\n"
    }

    fun meubles(jeu: Jeu): Map<String, Any> = linkedMapOf(
        "machines/plan_de_la_salle.txt" to t("ma.meuble.plan", "nom" to jeu.nom) + "\n",
        "machines/$CARNET" to t("ma.meuble.carnet") + "\n",
        "machines/photo.bin" to photo(),
        "machines/conteneur_jetable.sh" to conteneurSh(),
        "machines/collection.txt" to collectionTexte(jeu),
        "machines/ferme/disque_2/LISEZMOI.txt" to t("ma.meuble.disque_2") + "\n",
        "machines/ferme/loin/LISEZMOI.txt" to t("ma.meuble.loin") + "\n")

    val BESOINS = mapOf("sm0" to listOf("plan_de_la_salle.txt"), "sm3" to listOf("photo.bin"),
        "sm9" to listOf("collection.txt", "ferme/disque_2/LISEZMOI.txt", "ferme/loin/LISEZMOI.txt"))

    /** Appelé par Histoire.meubler pendant une leçon de la Salle (comme meubler sur PC). */
    fun meubler(jeu: Jeu, lid: String?) {
        val d = dossier(jeu)
        if (!d.isDirectory || lid == null) return
        val tous = meubles(jeu)
        for (r in BESOINS[lid] ?: emptyList()) if (!File(d, r).exists()) tous["machines/$r"]?.let { ecrire(jeu, r, it) }
        if (lid == "sm9" && jeu.etape <= 1 && !lire(jeu, "collection.txt").startsWith(MARQUE))
            ecrire(jeu, "collection.txt", tous["machines/collection.txt"]!!)
        val e = Programme.donnees().optJSONObject("etapes")?.optJSONObject("$lid.${jeu.etape}")
        if (e != null) for (mid in liste(e, "maths")) {
            if (Maths.noeud(mid) != null && !Maths.sait(jeu, mid) && !fait(jeu, "pont:$mid")) {
                jeu.dire(t("ma.pont", "notion" to Maths.titre(mid), "cmd" to "maths $mid"), 16)
                break
            }
        }
    }

    /** À chaque tour (Histoire.tick) : les pièces interrogées s'allument dans l'ordinateur ouvert. */
    fun surveiller(jeu: Jeu, ligne: String?) {
        if (ligne == null || !dossier(jeu).isDirectory) return
        val al = etat(jeu).getJSONArray("allumees")
        val deja = liste(etat(jeu), "allumees")
        for (p in piecesDe(ligne.trim())) if (p !in deja) al.put(p)
    }

    // ---------------------------------------------------------------- ce que les étapes vérifient
    private fun copieValide(jeu: Jeu, rel: String): Boolean = try {
        val dd = if (rel.isEmpty()) dossier(jeu) else File(dossier(jeu), rel)
        val arch = File(dd, "sauvegarde.tar.gz").readBytes()
        val note = File(dd, "sauvegarde.sha256").readText().trim().split(Regex("\\s+"))
        note.isNotEmpty() && note[0] == MessageDigest.getInstance("SHA-256").digest(arch).joinToString("") { "%02x".format(it) } &&
            arch.size > 2 && arch[0] == 0x1f.toByte() && arch[1] == 0x8b.toByte()
    } catch (e: Exception) { false }

    private fun archiveOk(jeu: Jeu) = try { File(dossier(jeu), "sauvegarde.tar.gz").readBytes().let { it.size > 2 && it[0] == 0x1f.toByte() && it[1] == 0x8b.toByte() } } catch (e: Exception) { false }
    private fun restauree(jeu: Jeu) = lire(jeu, "collection.txt").startsWith(MARQUE) && dansCarnet(jeu, "panne")

    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)
    private const val LS = "^(ls|dir)\\b"
    private const val LIRE = "^(cat|less|more|head|tail)\\b"
    private const val MA = "^(tg\\s+)?machines\\s+"

    private fun n(lid: String, i: Any, cmd: String, re: String? = null, fs: ((Jeu) -> Boolean)? = null, ou: String? = null,
                  cree: String? = null, exploit: String? = null, reseau: Boolean = false) =
        Etape("hist.$lid.$i.dit", cmd, "hist.$lid.$i.bravo", re?.let { r(it) }, fs, null, cree, ou, reseau = reseau, exploit = exploit)

    val IDS = (0..10).map { "sm$it" }

    /** Les leçons du téléphone : les mêmes paliers ; ce qui n'existe pas sur un téléphone (lspci, conteneurs, VM) est
     *  remplacé (getprop) ou raconté (machines adulte, conteneur, vm). */
    fun lecons(jeu: Jeu): Map<String, Lecon> {
        val carnetOk = { et: String -> { j: Jeu -> dansCarnet(j, et) } }
        return linkedMapOf(
            "sm0" to Lecon("hist.sm0.titre", null, 1, listOf(
                Etape("hist.entree.dit", "cd ~/terrain_terminagotchi/machines", "hist.entree.bravo", ici = "machines", params = mapOf("piece" to "machines")),
                n("sm0", 1, "ls", re = LS, ou = "machines"),
                n("sm0", 2, "cat plan_de_la_salle.txt", re = "$LIRE.*plan_de_la_salle"),
            )),
            "sm1" to Lecon("hist.sm1.titre", null, 1, listOf(
                n("sm1", 0, "nproc", re = "^(nproc|cat\\s+/proc/cpuinfo)\\b", ou = "machines"),
                n("sm1", 1, "machines coeurs ?", fs = carnetOk("coeurs")),
                n("sm1", 2, "free -h", re = "^(free|cat\\s+/proc/meminfo)\\b"),
                n("sm1", 3, "machines memoire ?", fs = carnetOk("memoire")),
                n("sm1", 4, "df -h", re = "^(df|lsblk)\\b", reseau = true),
                n("sm1", 5, "machines ouvre", re = "${MA}ouvre\\b"),
            )),
            "sm2" to Lecon("hist.sm2.titre", null, 1, listOf(
                n("sm2", 0, "head -5 /proc/cpuinfo", re = "^(cat|head|grep)\\b.*/proc/cpuinfo", ou = "machines", reseau = true),
                n("sm2", 1, "grep -c ^processor /proc/cpuinfo", re = "^grep\\s+-\\w*c\\w*\\s+['\"]?\\^?processor.*/proc/cpuinfo", reseau = true),
                n("sm2", "t2", "getprop ro.product.model", re = "^getprop\\b"),
                n("sm2", 4, "machines monte 1 ? ? ? ? ? ?", fs = carnetOk("monte1")),
            )),
            "sm3" to Lecon("hist.sm3.titre", null, 1, listOf(
                n("sm3", 0, "printf '%x\\n' 65", re = "^printf\\s+['\"]?%x", ou = "machines"),
                n("sm3", 1, "echo -n A | xxd -b", re = "^(echo\\s+-n|printf)\\s+['\"]?A['\"]?\\s*\\|\\s*xxd\\s+-\\w*b"),
                n("sm3", 2, "machines interrupteurs ?", fs = carnetOk("interrupteurs")),
                n("sm3", 3, "machines allume ?", fs = carnetOk("allume")),
                n("sm3", 4, "wc -c photo.bin", re = "^(wc\\s+-c\\b.*photo\\.bin|stat\\b.*%s.*photo\\.bin|ls\\s+-\\w*l\\w*\\b.*photo\\.bin)"),
                n("sm3", 5, "machines unites", re = "${MA}unit[eé]s?\\b"),
            )),
            "sm4" to Lecon("hist.sm4.titre", null, 1, listOf(
                n("sm4", 0, "uname -r", re = "^uname\\s+-\\w*r", ou = "machines"),
                n("sm4", 1, "uptime", re = "^uptime\\b"),
                n("sm4", 4, "machines reveil", re = "${MA}r[eé]veil\\s*$"),
                n("sm4", 5, "machines reveil ? ? ? ? ?", fs = carnetOk("reveil")),
            )),
            "sm5" to Lecon("hist.sm5.titre", null, 1, listOf(
                n("sm5", 0, "uname -srm", re = "^uname\\b", ou = "machines"),
                n("sm5", "t1", "getprop ro.build.version.release", re = "^getprop\\b"),
                n("sm5", 2, "ps", re = "^ps\\b"),
                n("sm5", 3, "which ls", re = "^(which|command\\s+-v|type)\\s+ls\\b"),
                n("sm5", 5, "machines orchestre", re = "${MA}orchestre\\s*$"),
                n("sm5", 6, "machines orchestre ? ? ? ? ?", fs = carnetOk("orchestre")),
                n("sm5", 7, "machines licences", re = "${MA}licences?\\b"),
            )),
            "sm6" to Lecon("hist.sm6.titre", null, 1, listOf(
                n("sm6", 1, "machines boite", re = "${MA}bo[iî]te\\b", ou = "machines"),
                n("sm6", 2, "machines range", re = "${MA}range\\s*$"),
                n("sm6", 3, "machines range ? ? ? ?", fs = carnetOk("range")),
            )),
            "sm7" to Lecon("hist.sm7.titre", null, 1, listOf(
                n("sm7", 0, "machines adulte", re = "${MA}adulte\\b", ou = "machines"),
                n("sm7", 5, "machines conteneur", fs = carnetOk("histoire_conteneur")),
                n("sm7", 9, "machines vm", re = "${MA}vm\\b"),
            )),
            "sm8" to Lecon("hist.sm8.titre", null, 1, listOf(
                n("sm8", 0, "df -h .", re = "^df\\b", ou = "machines"),
                n("sm8", 1, "du -sh .", re = "^du\\b"),
                n("sm8", 2, "machines ferme", re = "${MA}ferme\\b"),
                n("sm8", 3, "machines energie", re = "${MA}[eé]nergie\\b"),
            )),
            "sm9" to Lecon("hist.sm9.titre", null, 1, listOf(
                n("sm9", 0, "ls ferme", re = "$LS.*ferme", ou = "machines"),
                n("sm9", 1, "tar czf sauvegarde.tar.gz collection.txt", fs = { j -> archiveOk(j) }, cree = "machines/sauvegarde.tar.gz"),
                n("sm9", 2, "sha256sum sauvegarde.tar.gz > sauvegarde.sha256", fs = { j -> copieValide(j, "") }, cree = "machines/sauvegarde.sha256"),
                n("sm9", 3, "cp sauvegarde.tar.gz sauvegarde.sha256 ferme/disque_2/", fs = { j -> copieValide(j, "ferme/disque_2") }),
                n("sm9", 4, "cp sauvegarde.tar.gz sauvegarde.sha256 ferme/loin/", fs = { j -> copieValide(j, "ferme/loin") }),
                n("sm9", 5, "machines panne", fs = carnetOk("panne")),
                Etape("hist.sm9.6.dit", "cd ferme/loin", "hist.sm9.6.bravo", ici = "machines/ferme/loin", exact = true),
                n("sm9", 7, "sha256sum -c sauvegarde.sha256", re = "^sha256sum\\s+(-c|--check)\\b.*sauvegarde\\.sha256", ou = "machines/ferme/loin"),
                n("sm9", 8, "tar xzf sauvegarde.tar.gz -C ../..", fs = { j -> restauree(j) }),
            )),
            "sm10" to Lecon("hist.sm10.titre", null, 1, listOf(
                n("sm10", 0, "machines monte", re = "${MA}monte\\s*$", ou = "machines"),
                n("sm10", 1, "machines monte ? ? ? ? ? ?", fs = carnetOk("monte")),
                n("sm10", 2, "machines demarre", fs = carnetOk("demarre")),
                n("sm10", 3, "machines drapeau ?", fs = carnetOk("drapeau")),
            )),
        )
    }

    // ---------------------------------------------------------------- l'arbre du Carrefour
    private fun besoin(): List<String> {
        val P = Programme.donnees()
        val ms = P.optJSONArray("mondes") ?: JSONArray()
        val m = (0 until ms.length()).map { ms.getJSONObject(it) }.firstOrNull { it.optString("id") == "machines" } ?: return emptyList()
        val tronc = P.optJSONObject("tronc") ?: JSONObject()
        return liste(m, "requis").flatMap { liste(tronc, it) }.distinct()
    }

    fun ouvert(jeu: Jeu) = besoin().let { b -> b.isNotEmpty() && b.all { Histoire.fini(jeu, it) } }
    fun manque(jeu: Jeu) = besoin().filter { !Histoire.fini(jeu, it) }.map { Histoire.nomChapitre(it) }

    fun annonce(jeu: Jeu): Boolean {
        val h = Histoire.h(jeu)
        val deja = h.optJSONArray("mondes_annonces") ?: JSONArray().also { h.put("mondes_annonces", it) }
        if ((0 until deja.length()).any { deja.getString(it) == "machinerie" } || Histoire.fini(jeu, "machinerie") || !ouvert(jeu)) return false
        deja.put("machinerie")
        jeu.log(t("ma.ouvert.log"))
        jeu.dire(Histoire.dire(jeu, "ma.ouvert.dit"), 18)
        return true
    }

    private val REPONSES = mapOf("machines coeurs ?" to "coeurs", "machines memoire ?" to "memoire", "machines allume ?" to "allume",
        "machines reveil ? ? ? ? ?" to "reveil", "machines orchestre ? ? ? ? ?" to "orchestre", "machines range ? ? ? ?" to "range",
        "machines monte 1 ? ? ? ? ? ?" to "monte1", "machines monte ? ? ? ? ? ?" to "monte", "machines demarre" to "demarre",
        "machines drapeau ?" to "drapeau")
    private val TROU = Regex("(^|\\s)(\\?|…|<[^>]*>)(\\s|$)")

    /** Un indice de la Salle (Histoire.indice), comme machines.indice sur PC. */
    fun indice(jeu: Jeu, e: Etape, tapees: List<Pair<String, String?>>): String? {
        if (Histoire.leconCourante(jeu)?.id !in IDS) return null
        val lignes = tapees.map { it.first.trim() }
        if (lignes.any { Regex("^sudo\\b").containsMatchIn(it) }) return t("ma.indice.sudo")
        if (e.cmd.startsWith("tar czf") && lignes.any { Regex("^tar\\s+-?c\\w*f\\s+collection\\.txt\\b").containsMatchIn(it) }) return t("ma.indice.tar_sens")
        if ("?" in e.cmd.split(" ") && lignes.filter { r(MA).containsMatchIn(it) }.any { TROU.containsMatchIn(it) }) return t("ma.indice.trou")
        if (e.cmd == "machines interrupteurs ?" && lignes.any { r("${MA}interrupteurs\\s*$").containsMatchIn(it) }) return t("ma.indice.interrupteurs")
        REPONSES[e.cmd]?.let { et ->
            val der = carnet(jeu).lines().lastOrNull { it.startsWith("[$et]") }
            if (der != null && !der.trimEnd().endsWith("(ok)")) return t("ma.indice.$et")
        }
        if (e.cmd.startsWith("cp sauvegarde") && lignes.any { it.startsWith("cp") }) return t("ma.indice.copie")
        return null
    }

    // ---------------------------------------------------------------- les commandes du jeu : machines …
    /** L'ordinateur ouvert en caractères, pour l'écran étroit du téléphone : (caractère, pièce ou null). */
    fun grilleOrdinateur(): List<List<Pair<Char, String?>>> {
        val W = 34; val H = 11
        val g = Array(H) { Array<Pair<Char, String?>>(W) { ' ' to null } }
        fun met(r: Int, c: Int, ch: Char, p: String?) { if (r in 0 until H && c in 0 until W) g[r][c] = ch to p }
        fun boite(r0: Int, c0: Int, r1: Int, c1: Int, p: String, rempli: Char) {
            for (r in r0..r1) for (c in c0..c1) met(r, c, when {
                r == r0 && c == c0 -> '┌'; r == r0 && c == c1 -> '┐'; r == r1 && c == c0 -> '└'; r == r1 && c == c1 -> '┘'
                r == r0 || r == r1 -> '─'; c == c0 || c == c1 -> '│'; else -> rempli }, p)
        }
        for (c in 0 until W) { met(0, c, '═', null); met(H - 1, c, '═', null) }
        for (r in 0 until H) { met(r, 0, '║', null); met(r, W - 1, '║', null) }
        met(0, 0, '╔', null); met(0, W - 1, '╗', null); met(H - 1, 0, '╚', null); met(H - 1, W - 1, '╝', null)
        boite(1, 1, 3, 9, "alimentation", '▒')
        boite(5, 1, 8, 9, "stockage", '▤')
        boite(1, 11, 9, 32, "carte_mere", '·')
        boite(2, 13, 5, 19, "processeur", '▓')
        for (k in 0 until 4) for (r in 2..5) met(r, 22 + 2 * k, '║', "memoire")
        for (c in 13..30) met(7, c, '▬', "graphique")
        for (c in 13..16) met(8, c, '▭', "usb")
        val rang = listOf("processeur", "memoire", "stockage", "carte_mere", "graphique", "usb", "alimentation")
        for ((p, rc) in mapOf("alimentation" to (2 to 3), "stockage" to (6 to 3), "carte_mere" to (1 to 12), "processeur" to (3 to 16),
            "memoire" to (6 to 25), "graphique" to (7 to 31), "usb" to (8 to 17))) met(rc.first, rc.second, '0' + rang.indexOf(p) + 1, p)
        return g.map { it.toList() }
    }

    /** Allumée : la pièce s'écrit ; éteinte : remplacée par des points discrets (le texte du téléphone n'a qu'une couleur). */
    fun dessinOrdinateur(allumees: Collection<String>): List<String> = grilleOrdinateur().map { l ->
        " " + l.joinToString("") { (ch, p) -> if (p == null || p in allumees || ch.isDigit() || ch in "┌┐└┘─│") ch.toString() else "░" } }

    private fun valeurPiece(p: String): String = when (p) {
        "processeur" -> t("ma.ouvre.v.processeur", "n" to coeurs())
        "memoire" -> memoireKio()?.let { t("ma.ouvre.v.memoire", "gio" to "%.1f".format(java.util.Locale.ROOT, it / 1048576.0)) } ?: ""
        "alimentation" -> allumeeDepuis()?.let { t("ma.ouvre.v.alimentation", "h" to it / 60, "m" to it % 60) } ?: ""
        else -> ""
    }

    fun lignesOuvre(jeu: Jeu): List<String> {
        val al = liste(etat(jeu), "allumees")
        val out = (mutableListOf("🔩 " + t("ma.ouvre.titre"), "") + dessinOrdinateur(al) + listOf("")).toMutableList()
        PIECES.forEachIndexed { i, p -> out.add("  ${if (p in al) "●" else "○"} ${i + 1} " + t("ma.piece.$p") + " : " + (if (p in al) valeurPiece(p) else t("ma.ouvre.eteinte"))) }
        val n = PIECES.count { it in al }
        out += listOf("", "  " + t("ma.ouvre.compte", "n" to n, "total" to PIECES.size))
        if (n < PIECES.size) out.add("  " + t("ma.tel.raconte", "outil" to "lspci, lsusb"))
        noter(jeu, "ouvre", "$n (ok)")
        return out
    }

    fun lignesCoeurs(jeu: Jeu, arg: String?): List<String> {
        val n = arg?.toIntOrNull() ?: return listOf(t("ma.coeurs.aide"))
        return if (n in coeursJustes()) { noter(jeu, "coeurs", "$n (ok)"); listOf("✔ " + t("ma.coeurs.ok", "n" to n), "  " + t("ma.coeurs.morale")) }
        else { noter(jeu, "coeurs", "$n (faux)"); listOf("✖ " + t("ma.coeurs.faux", "n" to n)) }
    }

    fun lignesMemoire(jeu: Jeu, arg: String?): List<String> {
        if (arg.isNullOrBlank()) return listOf(t("ma.memoire.aide"))
        val k = memoireKio() ?: run { noter(jeu, "memoire", "inconnue (ok)"); return listOf(t("ma.memoire.inconnue")) }
        return if (memoireOk(arg, k)) {
            noter(jeu, "memoire", "juste (ok)")
            listOf("✔ " + t("ma.memoire.ok", "gio" to "%.1f".format(java.util.Locale.ROOT, k / 1048576.0), "go" to "%.1f".format(java.util.Locale.ROOT, k * 1024 / 1e9)),
                "  " + t("ma.memoire.morale"))
        } else { noter(jeu, "memoire", "loin (faux)"); listOf("✖ " + t("ma.memoire.faux")) }
    }

    private fun ligneInterrupteurs(b: String) = b.map { if (it == '1') "■" else "□" }.joinToString(" ")

    fun lignesInterrupteurs(jeu: Jeu, mot0: String?): List<String> {
        if (mot0.isNullOrBlank()) return listOf(t("ma.interrupteurs.aide"))
        val mot = mot0.take(12)
        val out = mutableListOf("💡 " + t("ma.interrupteurs.titre"), "", "     128 64 32 16 8 4 2 1")
        var total = 0
        val ints = interrupteurs(mot)
        for ((c, octets) in ints) octets.forEachIndexed { i, b -> total++
            out.add(" ${(if (i == 0) c else "").padEnd(3)} " + ligneInterrupteurs(b) + "  ${Integer.parseInt(b, 2)}") }
        out += listOf("", "  " + t("ma.interrupteurs.compte", "lettres" to ints.size, "octets" to total))
        if (ints.any { it.second.size > 1 }) out.add("  " + t("ma.interrupteurs.utf8"))
        out += listOf("", "🎯 " + t("ma.interrupteurs.defi", "lettre" to lettreDefi(jeu.nom)))
        noter(jeu, "interrupteurs", "${ints.size} lettres (ok)")            // jamais le mot lui-même
        return out
    }

    fun lignesAllume(jeu: Jeu, arg: String?): List<String> {
        val lettre = lettreDefi(jeu.nom)
        if (arg.isNullOrBlank()) return listOf(t("ma.allume.aide", "lettre" to lettre))
        val b = arg.replace(Regex("[\\s_]"), "")
        if (!Regex("[01]{8}").matches(b)) return listOf(t("ma.allume.huit"))
        val v = Integer.parseInt(b, 2)
        val out = listOf("  " + ligneInterrupteurs(b) + "  $b = $v")
        return if (b == bits(lettre.code)) { noter(jeu, "allume", "$lettre (ok)"); out + ("✔ " + t("ma.allume.ok", "lettre" to lettre, "n" to lettre.code)) }
        else { noter(jeu, "allume", "$lettre (faux)"); out + ("✖ " + t("ma.allume.faux", "lettre" to lettre, "n" to v, "c" to (if (v in 33..126) v.toChar().toString() else "?"))) }
    }

    private fun fr(x: Double, d: Int = 2) = "%,.${d}f".format(java.util.Locale.ROOT, x).replace(",", " ")

    fun lignesUnites(jeu: Jeu, arg: String?): List<String> {
        val n = arg?.toLongOrNull() ?: File(dossier(jeu), "photo.bin").let { if (it.isFile) it.length() else 1048576L }
        val u = unites(n)
        noter(jeu, "unites", "$n (ok)")
        return listOf("📏 " + t("ma.unites.titre", "n" to fr(n.toDouble(), 0)), "", "  " + t("ma.unites.mille"),
            "    ${fr(u["ko"]!!)} Ko · ${fr(u["mo"]!!)} Mo · ${fr(u["go"]!!, 4)} Go", "  " + t("ma.unites.mil24"),
            "    ${fr(u["kio"]!!)} Kio · ${fr(u["mio"]!!)} Mio · ${fr(u["gio"]!!, 4)} Gio", "", "  " + t("ma.unites.morale"), "  " + t("ma.unites.grands"))
    }

    fun lignesEtages(phase: Double): List<String> {
        val e = liste(donnees(), "reveil")
        val allumes = Math.round(phase * e.size).toInt()
        val v = mapOf("noyau" to noyau(), "init" to "init", "micrologiciel" to "", "chargeur" to "", "session" to "")
        return (e.size - 1 downTo 0).map { i -> val on = i < allumes
            "  ${if (on) "▓▓▓▓" else "░░░░"} ${i + 1}. " + t("ma.etage.${e[i]}") + (if (on && v[e[i]].orEmpty().isNotEmpty()) " (${v[e[i]]})" else "") }
    }

    fun lignesReveil(jeu: Jeu, rep: List<String>): List<String> {
        val gr = Histoire.graine(jeu)
        if (rep.isEmpty()) return listOf("⏰ " + t("ma.reveil.titre"), "") + reveilCartes(gr).map { "  ${it.first}  " + t("ma.reveil.${it.second}") } + listOf("", "  " + t("ma.reveil.aide"))
        val r = rep.map { it.uppercase().first() }
        val bon = reveilReponse(gr)
        if (r != bon) { noter(jeu, "reveil", r.joinToString(" ") + " (faux)"); return listOf("✖ " + t("ma.reveil.faux", "n" to r.zip(bon).count { it.first == it.second }, "total" to bon.size)) }
        noter(jeu, "reveil", r.joinToString(" ") + " (ok)")
        return listOf("✔ " + t("ma.reveil.ok"), "") + lignesEtages(1.0) + listOf("", "  " + t("ma.reveil.morale"))
    }

    fun lignesOrchestre(jeu: Jeu, rep: List<String>): List<String> {
        val o = orchestre(Histoire.graine(jeu))
        val mus = liste(donnees().optJSONObject("orchestre"), "musiciens")
        if (rep.isEmpty()) return listOf("🎼 " + t("ma.orchestre.titre"), "") + mus.mapIndexed { i, m -> "  ${LETTRES[i]} " + t("ma.orchestre.m.$m") } + listOf("") +
            o.map { "  ${it.first}. " + t("ma.orchestre.t.${it.second}") } + listOf("", "  " + t("ma.orchestre.aide"))
        val r = rep.map { it.uppercase().first() }
        if (r.size != o.size) return listOf(t("ma.orchestre.aide"))
        val justes = o.zip(r).filter { it.first.third == it.second }.map { it.first }
        val out = mutableListOf<String>()
        if (justes.size == o.size) { noter(jeu, "orchestre", r.joinToString(" ") + " (ok)"); out.add("✔ " + t("ma.orchestre.ok")) }
        else { noter(jeu, "orchestre", r.joinToString(" ") + " (faux)"); out.add("✖ " + t("ma.orchestre.faux", "n" to justes.size, "total" to o.size)) }
        justes.forEach { out.add("  ✔ ${it.first}. " + t("ma.orchestre.t.${it.second}.pourquoi")) }
        return out
    }

    fun lignesLicences(jeu: Jeu): List<String> {
        noter(jeu, "licences", "lues (ok)")
        return listOf("📜 " + t("ma.licences.titre"), "", "  " + t("ma.licences.toi", "nom" to "Android (Linux ${noyau()})"), "  " + t("ma.licences.libre"),
            "  " + t("ma.licences.proprio"), "  " + t("ma.licences.gpl"), "  " + t("ma.licences.distrib"), "  " + t("ma.licences.grands"))
    }

    fun lignesBoite(jeu: Jeu): List<String> {
        val (vm, c) = boiteDe(lireSys("/proc/cpuinfo"), lireSys("/proc/1/cgroup"))
        val out = mutableListOf("🏠 " + t("ma.boite.titre"), "", "  ⌂ " + t("ma.boite.vraie"), "    └ ⌂ " + t("ma.boite.vm"), "        └ 📦 " + t("ma.boite.app"), "")
        if (c != null) out.add("  📦 " + t("ma.boite.dans_conteneur", "quoi" to c))
        if (vm) out.add("  🏠 " + t("ma.boite.dans_vm"))
        if (!vm && c == null) out.add("  🏠 " + t("ma.boite.vraie_machine"))
        out += listOf("", "  " + t("ma.boite.vm_def"), "  " + t("ma.boite.conteneur_def"), "  " + t("ma.boite.grands"))
        noter(jeu, "boite", "vue (ok)")
        return out
    }

    fun lignesRange(jeu: Jeu, rep: List<String>): List<String> {
        val rr = rangeBoites(Histoire.graine(jeu))
        if (rep.isEmpty()) return listOf("📦 " + t("ma.range.titre"), "") + rr.map { "  ${it.first}. " + t("ma.range.${it.second}") } + listOf("", "  " + t("ma.range.aide"))
        val r = rep.map { it.lowercase().take(1) }
        if (r.size != rr.size || r.any { it !in listOf("c", "v") }) return listOf(t("ma.range.aide"))
        val justes = rr.zip(r).filter { it.first.third == it.second }.map { it.first }
        val out = mutableListOf<String>()
        if (justes.size == rr.size) { noter(jeu, "range", r.joinToString(" ") + " (ok)"); out.add("✔ " + t("ma.range.ok")) }
        else { noter(jeu, "range", r.joinToString(" ") + " (faux)"); out.add("✖ " + t("ma.range.faux", "n" to justes.size, "total" to rr.size)) }
        justes.forEach { out.add("  ✔ ${it.first}. " + t("ma.range.${it.second}.pourquoi")) }
        return out
    }

    fun lignesAdulte(jeu: Jeu): List<String> {
        noter(jeu, "adulte", "lu (ok)")
        val mo = donnees().optJSONObject("conteneur")?.optInt("taille_mo", 4) ?: 4
        return listOf("🧑‍🔧 " + t("ma.adulte.titre"), "") + t("ma.adulte.regles", "mo" to mo).split("\n").map { "  $it" } +
            listOf("", "  " + t("ma.tel.raconte", "outil" to "podman, qemu-img, virsh"))
    }

    fun lignesConteneur(jeu: Jeu): List<String> {
        val vrai = dansCarnet(jeu, "conteneur")
        noter(jeu, "histoire_conteneur", (if (vrai) "vrai" else "raconte") + " (ok)")
        return listOf("📦 " + t("ma.conteneur.titre"), "", "  [📦 alpine]  " + t("ma.conteneur.temps0"), "  [📦 💬]  " + t("ma.conteneur.temps1"),
            "  [ ✨ ✨ ]  " + t("ma.conteneur.temps2"), "", "  " + t(if (vrai) "ma.conteneur.vrai" else "ma.conteneur.raconte"),
            "  " + t("ma.conteneur.image"), "  " + t("ma.conteneur.grands"))
    }

    fun lignesVm(jeu: Jeu): List<String> {
        noter(jeu, "vm", "racontee (ok)")
        return listOf("🖥 " + t("ma.vm.titre"), "") + (1..7).map { "  $it. " + t("ma.vm.etape$it") } + listOf("", "  " + t("ma.vm.adulte"), "  " + t("ma.vm.grands"))
    }

    fun lignesFerme(jeu: Jeu): List<String> {
        noter(jeu, "ferme", "vue (ok)")
        return listOf("🏭 " + t("ma.ferme.titre"), "", "  ❄ ~~~~~~~~~~~~~~~~~~~~~ ❄", "  [▤●▤] [▤●▤] [▤●▤] [▤●▤]", "  [▤●▤] [▤●▤] [▤●▤] [▤●▤]", "  ⚡═════╪═════╪═════⚡", "") +
            listOf("serveur", "datacenter", "cloud", "redondance", "froid").map { "  • " + t("ma.ferme.$it") }
    }

    fun lignesEnergie(jeu: Jeu): List<String> {
        val e = donnees().optJSONObject("energie") ?: JSONObject()
        val w = e.optInt("watts", 300); val h = e.optInt("heures", 8760)
        val (wh, kwh) = energie(w, h)
        noter(jeu, "energie", "vue (ok)")
        return listOf("🌱 " + t("ma.energie.titre"), "", "  " + t("ma.energie.calcul", "w" to w, "h" to fr(h.toDouble(), 0), "wh" to fr(wh.toDouble(), 0), "kwh" to fr(kwh, 0)),
            "  " + t("ma.energie.fabrication"), "") + (1..4).map { "  ✔ " + t("ma.energie.geste$it") } + listOf("", "  " + t("ma.energie.grands"))
    }

    fun lignesPanne(jeu: Jeu): List<String> {
        val ailleurs = listOf("ferme/disque_2", "ferme/loin").filter { copieValide(jeu, it) }
        val original = lire(jeu, "collection.txt").startsWith(MARQUE)
        val copies = ailleurs.size + (if (original || copieValide(jeu, "")) 1 else 0)
        val loin = "ferme/loin" in ailleurs
        val out = mutableListOf("🔥 " + t("ma.panne.titre"), "", "  " + t("ma.panne.bilan", "copies" to copies, "supports" to copies, "loin" to t(if (loin) "ma.oui" else "ma.non")), "")
        if (!loin) { noter(jeu, "panne", "rien au loin (perdu)"); return out + listOf("✖ " + t("ma.panne.perdu"), "  " + t("ma.panne.refais")) }
        for (r in listOf("collection.txt", "sauvegarde.tar.gz", "ferme/disque_2/sauvegarde.tar.gz")) if (File(dossier(jeu), r).exists()) ecrire(jeu, r, t("ma.panne.cendres") + "\n")
        noter(jeu, "panne", "$copies-$copies-1 (ok)")
        return out + listOf("  🔥 " + t("ma.panne.brule"), "✔ " + t("ma.panne.sauvee"), "  " + t("ma.panne.suite"))
    }

    fun textePiece(cat: String, x: JSONObject): String = when (cat) {
        "processeur" -> t("ma.p.processeur", "coeurs" to x.optInt("coeurs"), "prise" to x.optString("prise"), "w" to x.optInt("watts"), "pts" to x.optInt("points"))
        "carte_mere" -> t(if (x.optBoolean("mini")) "ma.p.carte_mere_mini" else "ma.p.carte_mere", "prise" to x.optString("prise"), "type" to x.optInt("type"), "w" to x.optInt("watts"), "pts" to x.optInt("points"))
        "memoire" -> t("ma.p.memoire", "gio" to x.optInt("gio"), "type" to x.optInt("type"), "w" to x.optInt("watts"), "pts" to x.optInt("points"))
        "stockage" -> t(if (x.optBoolean("ssd")) "ma.p.ssd" else "ma.p.disque", "go" to fr(x.optInt("go").toDouble(), 0), "w" to x.optInt("watts"), "pts" to x.optInt("points"))
        "graphique" -> if (x.optBoolean("aucune")) t("ma.p.sans_graphique") else t("ma.p.graphique", "w" to x.optInt("watts"), "pts" to x.optInt("points"))
        else -> t("ma.p.alimentation", "w" to x.optInt("fournit"), "pts" to x.optInt("points"))
    }

    private fun montageLignes(choix: List<String>, besoin: String, r: Montage): List<String> {
        val b = donnees().optJSONObject("besoins")?.optJSONObject(besoin) ?: JSONObject()
        val budget = b.optInt("budget", 99)
        return (if (besoin != "ecole") listOf("  " + t("ma.monte.besoin", "besoin" to t("ma.besoin.$besoin"))) else emptyList()) + CATEGORIES.map { c -> val x = choix.mapNotNull { piece(it) }.firstOrNull { it.first == c }?.second
            "  " + t("ma.cat.$c") + " : " + (if (x != null) x.optString("id") + " " + textePiece(c, x) else "—") } +
            listOf("", "  " + t("ma.monte.totaux", "points" to r.points, "budget" to (if (budget < 99) budget.toString() else "∞"), "watts" to r.watts, "fournit" to r.fournit))
    }

    fun lignesCatalogue(besoin: String): List<String> {
        val b = donnees().optJSONObject("besoins")?.optJSONObject(besoin) ?: JSONObject()
        val budget = b.optInt("budget", 99)
        val out = mutableListOf("🔧 " + t("ma.monte.titre"), "", "  " + t("ma.monte.besoin", "besoin" to t("ma.besoin.$besoin")),
            "  " + (if (budget < 99) t("ma.monte.budget", "budget" to budget) else t("ma.monte.sans_budget")), "")
        val cat = donnees().optJSONObject("catalogue")
        for (c in CATEGORIES) { out.add("  " + t("ma.cat.$c")); objets(cat, c).forEach { out.add("    ${it.optString("id")} " + textePiece(c, it)) } }
        return out + listOf("", "  " + t("ma.monte.regles"), "  " + t(if (besoin == "ecole") "ma.monte.aide1" else "ma.monte.aide"))
    }

    fun lignesProbleme(pb: List<String>): List<String> = pb.map { p ->
        val (k, v) = p.split(":", limit = 2).let { it[0] to it.getOrElse(1) { "" } }
        "  ✖ " + when (k) { "manque", "double" -> t("ma.pb.$k", "cat" to t("ma.cat.$v")); "inconnu" -> t("ma.pb.inconnu", "id" to v); else -> t("ma.pb." + p.replace(":", "_")) }
    }

    fun lignesMonte(jeu: Jeu, args: List<String>): List<String> {
        val c = etat(jeu)
        val niveau1 = args.firstOrNull() == "1"
        val choix = if (niveau1) args.drop(1) else args
        val besoin = if (niveau1) "ecole" else besoinEpreuve(Histoire.graine(jeu))
        if (choix.isEmpty()) { if (!niveau1 && !c.has("chrono")) c.put("chrono", System.currentTimeMillis() / 1000); return lignesCatalogue(besoin) }
        val r = montage(choix, besoin)
        val out = listOf("🔧 " + t("ma.monte.machine"), "") + montageLignes(choix, besoin, r) + listOf("")
        val ids = choix.joinToString(" ") { it.uppercase() }
        if (niveau1) {
            if (r.problemes.isNotEmpty()) { noter(jeu, "monte1", "$ids (faux)"); return out + lignesProbleme(r.problemes) + listOf("", "  " + t("ma.monte.reessaie")) }
            noter(jeu, "monte1", "$ids (ok)")
            return out + listOf("⚡ " + t("ma.demarre.ok"), "  " + t("ma.monte.niveau1_ok"))
        }
        c.put("choix", JSONArray(choix.map { it.uppercase() }))
        noter(jeu, "monte", "$ids (ok)")
        return out + ("  " + t("ma.monte.pret"))
    }

    fun lignesDemarre(jeu: Jeu): List<String> {
        val c = etat(jeu)
        val choix = liste(c, "choix")
        if (choix.isEmpty()) return listOf(t("ma.demarre.rien"))
        val gr = Histoire.graine(jeu)
        val r = montage(choix, besoinEpreuve(gr))
        c.put("demarrages", c.optInt("demarrages") + 1)
        val out = (listOf("🔌 " + t("ma.demarre.titre"), "") + montageLignes(choix, besoinEpreuve(gr), r) + listOf("")).toMutableList()
        if (r.problemes.isNotEmpty()) { noter(jeu, "demarre", choix.joinToString(" ") + " (faux)")
            return out + ("💥 " + t("ma.demarre.rate")) + lignesProbleme(r.problemes) + listOf("", "  " + t("ma.monte.reessaie")) }
        noter(jeu, "demarre", choix.joinToString(" ") + " (ok)")
        out += dessinOrdinateur(PIECES) + listOf("", "⚡ " + t("ma.demarre.ok"))
        if (c.has("chrono")) { val s = maxOf(0L, System.currentTimeMillis() / 1000 - c.optLong("chrono")); out.add("  ⏱ " + t("ma.demarre.chrono", "m" to s / 60, "s" to s % 60)) }
        out.add("🚩 ${drapeau(gr)}  " + t("ma.demarre.drapeau"))
        if (c.optInt("demarrages") == 1 && !fait(jeu, "premier_demarrage"))
            Recompenses.exploit(jeu, "machines.premier_demarrage")?.let { jeu.log(it); jeu.dire(it, 16); out.add("✨ $it") }
        return out
    }

    fun lignesDrapeau(jeu: Jeu, arg: String?): List<String> {
        if (arg.isNullOrBlank()) return listOf(t("ma.drapeau.aide"))
        return if (arg.trim() == drapeau(Histoire.graine(jeu))) { noter(jeu, "drapeau", "TG (ok)"); listOf("🚩 " + t("ma.drapeau.ok")) }
        else { noter(jeu, "drapeau", "faux (faux)"); listOf("✖ " + t("ma.drapeau.faux")) }
    }

    /** L'entrée de la Salle en caractères : le REPLI de l'illustration B9 (le dessin graphique est MachinesDessin.salle). */
    val SALLE_DESSIN = listOf(" ⚙ ╔══════════════════╗ ⚙", "   ║ ▓▓ ║║║ ▤▤ ≋≋≋ ║", " ══╣ ○──○──○──○──○ ╠══", "   ╚══════╦═══╦═══╝", "   ░░░░░░░║01║░░░░░░")

    /** machines [plan|ouvre|coeurs|memoire|interrupteurs|allume|unites|reveil|orchestre|licences|boite|range|adulte|
     *  conteneur|vm|ferme|energie|panne|monte|demarre|drapeau] */
    fun commande(jeu: Jeu, reste: String, ici: File): String {
        val m = reste.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        val sous = asciiBas((m.getOrNull(0) ?: "aide").lowercase()).replace("œ", "oe")
        val a = m.drop(1).filter { it != "?" && it != "…" }
        val l = when (sous) {
            "plan", "regle" -> SALLE_DESSIN + t("ma.meuble.plan", "nom" to jeu.nom).split("\n")
            "ouvre" -> lignesOuvre(jeu)
            "coeurs", "coeur" -> lignesCoeurs(jeu, a.getOrNull(0))
            "memoire" -> lignesMemoire(jeu, a.joinToString(" ").ifEmpty { null })
            "interrupteurs" -> lignesInterrupteurs(jeu, a.joinToString(" ").ifEmpty { null })
            "allume" -> lignesAllume(jeu, a.joinToString("").ifEmpty { null })
            "unites", "unite" -> lignesUnites(jeu, a.getOrNull(0))
            "reveil" -> lignesReveil(jeu, a)
            "orchestre" -> lignesOrchestre(jeu, a)
            "licences", "licence" -> lignesLicences(jeu)
            "boite" -> lignesBoite(jeu)
            "range" -> lignesRange(jeu, a)
            "adulte" -> lignesAdulte(jeu)
            "conteneur" -> lignesConteneur(jeu)
            "vm" -> lignesVm(jeu)
            "ferme" -> lignesFerme(jeu)
            "energie" -> lignesEnergie(jeu)
            "panne" -> lignesPanne(jeu)
            "monte" -> lignesMonte(jeu, a)
            "demarre" -> lignesDemarre(jeu)
            "drapeau" -> lignesDrapeau(jeu, a.getOrNull(0))
            else -> SALLE_DESSIN + listOf("⚙ " + t("ma.aide.titre")) + t("ma.aide.liste").split("\n").map { "  $it" }
        }
        return l.joinToString("\n")
    }

    // ---------------------------------------------------------------- xxd -b intégré (le xxd du téléphone n'a pas -b)
    private val XXD_B = Regex("^(?:echo\\s+-n|printf)\\s+(['\"]?)([^'\"|]*?)\\1\\s*\\|\\s*xxd\\s+-b\\s*$")

    /** `echo -n A | xxd -b` : chaque octet en binaire, comme le vrai xxd -b (6 octets par ligne) ; null : autre chose. */
    fun xxdB(ligne: String): String? {
        val mm = XXD_B.find(ligne.trim()) ?: return null
        val o = mm.groupValues[2].toByteArray(Charsets.UTF_8)
        return (o.indices step 6).joinToString("\n") { i -> val x = o.copyOfRange(i, minOf(o.size, i + 6))
            "%08x: ".format(i) + x.joinToString(" ") { bits(it.toInt()) }.padEnd(54) + " " + x.joinToString("") { b -> val v = b.toInt() and 255; if (v in 32..126) v.toChar().toString() else "." } }
    }
}
