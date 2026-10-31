/*
 * Test JVM de la Crypte des Codes (phase 5) sur Android, portage de pc/outils/test_crypte.py :
 *   1. les vecteurs communs donnees/crypte/vecteurs.json (César, roue, fréquences, décalage secret, biome tricheur, dé
 *      pipé, quiz mélangé comme random.shuffle de Python, messages cachés, avalanche, base fictive, dictionnaire,
 *      peintures, chaîne et vérification, preuve de travail, SHA-crypt, roue de la vue déployée) : EXACTEMENT les mêmes
 *      résultats qu'en Python ;
 *   2. les commandes intégrées du téléphone : openssl passwd -6 = le vrai openssl ; le gpg du téléphone et le VRAI gpg
 *      se comprennent dans les deux sens (clé publique importée, signature vérifiée, message chiffré puis déchiffré) ;
 *      gpg sans --homedir, ou hors du terrain : refusé ;
 *   3. l'arbre du Carrefour : la Crypte s'ouvre après les niveaux 0 à 4 ;
 *   4. la traversée cr0 → cr14 comme dans l'appli : la chaîne réparée sans indice (crypte.chaine), le carnet de bord
 *      (crypte.b6), le sceau miniature ;
 *   5. le dessin (roue, chaîne, peintures, mine, crypte de repli) sur une toile d'essai.
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/Crypte.kt -d cry.jar
 *   java -cp <imitations>:<appli.jar>:cry.jar:kotlin-stdlib.jar CrypteKt app/src/main/assets
 */
import fr.terminagotchi.Commandes
import fr.terminagotchi.Crypte
import fr.terminagotchi.CrypteDessin
import fr.terminagotchi.CryptePgp
import fr.terminagotchi.Deploie
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Quetes
import fr.terminagotchi.t
import fr.terminagotchi.Recompenses
import fr.terminagotchi.Shell
import fr.terminagotchi.Toile
import fr.terminagotchi.Tour
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class ActifsCr(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilCr(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsCr(a)
    override fun getApplicationContext(): android.content.Context = this
}

class ToileCr : Toile {
    var n = 0
    val textes = mutableListOf<String>()
    override fun rect(x: Float, y: Float, w: Float, h: Float, c: Int) { n++ }
    override fun rrect(x: Float, y: Float, w: Float, h: Float, r: Float, fond: Int?, bord: Int?, ep: Float) { n++ }
    override fun ellipse(cx: Float, cy: Float, rx: Float, ry: Float, c: Int) { n++ }
    override fun cercle(cx: Float, cy: Float, r: Float, c: Int, ep: Float) { n++ }
    override fun ligne(x1: Float, y1: Float, x2: Float, y2: Float, c: Int, ep: Float, plein: Float, vide: Float, dec: Float) { n++ }
    override fun poly(xs: FloatArray, ys: FloatArray, c: Int) { n++ }
    override fun texte(s: String, x: Float, y: Float, taille: Float, c: Int, gras: Boolean, ancre: Char, mono: Boolean) { n++; textes.add(s) }
    override fun mesure(s: String, taille: Float, gras: Boolean, mono: Boolean) = s.length * taille * 0.6f
    override fun lueur(cx: Float, cy: Float, r: Float, c: Int) { n++ }
    override fun cadre(c: fr.terminagotchi.Poses.Cadre, ax: Float, ay: Float, e: Float, miroir: Boolean, lisse: Boolean, sx: Float, sy: Float, rot: Float, alpha: Float) { n++ }
    override fun photo(nom: String, x: Float, y: Float, w: Float, h: Float, r: Float) { n++ }
}

var okCr = 0
var koCr = 0
fun verifierCr(c: Boolean, m: String) {
    if (c) okCr++ else koCr++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeuCr: Jeu
lateinit var shellCr: Shell
lateinit var cmdCr: Commandes
var cheminCr = System.getenv("PATH") ?: "/usr/bin:/bin"

fun lstCr(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.get(it).toString() }

fun bashCr(cmd: String, ou: File = shellCr.dossier, entree: ByteArray? = null): Pair<String, Int> {
    val pb = ProcessBuilder("bash", "-c", cmd).directory(ou).redirectErrorStream(true)
    pb.environment()["HOME"] = jeuCr.home.absolutePath
    pb.environment()["LC_ALL"] = "C.UTF-8"
    pb.environment()["PATH"] = cheminCr
    pb.environment().remove("GNUPGHOME")
    val p = pb.start()
    if (entree != null) p.outputStream.use { it.write(entree) } else p.outputStream.close()
    val s = p.inputStream.readBytes().toString(Charsets.UTF_8)
    return s to p.waitFor()
}

fun tapeCr(cmd: String): String {
    val mot = cmd.trim().split(" ")[0]
    var sortie = ""
    var code: Int? = null
    if (mot == "cd") shellCr.executer(cmd)
    else {
        val interne = cmdCr.executer(cmd)
        if (interne != null) sortie = interne.texte
        else bashCr(cmd).let { sortie = it.first; code = it.second }
    }
    Tour.apresCommande(jeuCr, cmd, colle = false, rappel = false, hasard = false, cwd = shellCr.dossier, code = code)
    return sortie
}

fun lecCr(): Pair<String?, Int> = Histoire.leconCourante(jeuCr)?.id to jeuCr.etape

fun main(args: Array<String>) {
    val assets = File(args[0])
    val depot = assets.parentFile.parentFile.parentFile.parentFile
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_cry_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilCr(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeuCr = Jeu(app)
    jeuCr.changerLangue("fr")
    jeuCr.nom = "Pixel"
    shellCr = Shell(jeuCr.home)
    cmdCr = Commandes(app, jeuCr, { shellCr.dossier })
    jeuCr.module("explo").put("ouverte", true)
    jeuCr.terrain.mkdirs()
    val aBash = { c: String -> ProcessBuilder("bash", "-c", "command -v $c").start().waitFor() == 0 }
    if (!aBash("xxd")) {                       // une doublure de xxd (-r -p) si l'outil manque sur la machine de test
        val d = File(dossier, "doublures").apply { mkdirs() }
        File(d, "xxd").writeText("#!/usr/bin/env python3\nimport sys\na=[x for x in sys.argv[1:] if not x.startswith('-')]\n" +
            "d=open(a[0],'rb').read() if a else sys.stdin.buffer.read()\n" +
            "sys.stdout.buffer.write(bytes.fromhex(d.decode().replace(chr(10),'').replace(' ',''))) if '-r' in sys.argv else print(d.hex())\n")
        File(d, "xxd").setExecutable(true)
        cheminCr = d.absolutePath + ":" + cheminCr
    }

    println("1. Les vecteurs communs (Python ↔ Kotlin)")
    val v = JSONObject(File(depot, "donnees/crypte/vecteurs.json").readText())
    var ko = 0
    val ce = v.getJSONArray("cesar")
    for (i in 0 until ce.length()) { val x = ce.getJSONObject(i)
        if (Crypte.asciiBas(x.getString("texte")) != x.getString("ascii") || Crypte.cesar(x.getString("ascii"), x.getInt("k")) != x.getString("code")) { ko++; println("    cesar $x") } }
    verifierCr(ko == 0, "${ce.length()} César (accents enlevés, décalages 1, 3, 13, 25)")
    ko = 0
    val ro = v.getJSONArray("rotation")
    for (i in 0 until ro.length()) { val x = ro.getJSONObject(i)
        val k = Crypte.rotation(x.getString("de"), x.getString("vers")); val att = if (x.isNull("k")) null else x.getInt("k")
        if (k != att) { ko++; println("    rotation $x → $k") } }
    verifierCr(ko == 0, "${ro.length()} ensembles de tr : la roue reconnue (ou pas) comme en Python")
    ko = 0
    val frq = v.getJSONArray("frequences")
    for (i in 0 until frq.length()) { val x = frq.getJSONObject(i)
        val f = Crypte.frequences(x.getString("texte")).map { listOf("${it.first}", "${it.second}") }
        val a = (0 until x.getJSONArray("f").length()).map { lstCr(x.getJSONArray("f").getJSONArray(it)) }
        if (f != a) { ko++; println("    freq $f / $a") } }
    verifierCr(ko == 0, "les fréquences des lettres (ordre de sort -rn)")
    ko = 0
    val gs = v.getJSONArray("graines")
    for (i in 0 until gs.length()) { val x = gs.getJSONObject(i); val g = x.getString("graine")
        val q = Crypte.quiz(g).map { listOf("${it.first}", it.second, it.third) }
        val qa = (0 until x.getJSONArray("quiz").length()).map { lstCr(x.getJSONArray("quiz").getJSONArray(it)) }
        if (Crypte.decalage(g) != x.getInt("k") || Crypte.tricheur(g) != x.getString("tricheur") ||
            Crypte.deSuite(g, 6).map { "$it" } != lstCr(x.getJSONArray("de")) || q != qa) { ko++; println("    graine $g") } }
    verifierCr(ko == 0, "${gs.length()} graines : décalage secret, biome tricheur, dé pipé, quiz mélangé (random.shuffle)")
    ko = 0
    val me = v.getJSONArray("messages")
    for (i in 0 until me.length()) { val x = me.getJSONObject(i)
        if (Crypte.messageCode(x.getInt("n"), x.getString("texte")) != x.getString("code")) ko++ }
    val av = v.getJSONArray("avalanche")
    for (i in 0 until av.length()) { val x = av.getJSONObject(i)
        val ha = Crypte.sha(x.getString("a")); val hb = Crypte.sha(x.getString("b"))
        if (Crypte.lettresDifferentes(ha, hb) != x.getInt("lettres") || Crypte.bitsDifferents(ha, hb) != x.getInt("bits")) ko++ }
    verifierCr(ko == 0, "les messages cachés (base64, hexadécimal, ROT13) et l'avalanche")
    val dico = Crypte.trouvesParDico().map { listOf(it.first, it.second) }
    verifierCr(Crypte.baseFictive() == lstCr(v.getJSONArray("base")) &&
        dico == (0 until v.getJSONArray("dico").length()).map { lstCr(v.getJSONArray("dico").getJSONArray(it)) },
        "la base FICTIVE et l'attaque par dictionnaire : $dico")
    val pe = v.getJSONObject("peintures")
    verifierCr(Crypte.peintures().all { (k, x) -> pe.getInt(k) == x }, "les peintures : ${Crypte.peintures()}")
    val ch = v.getJSONObject("chaine")
    val blocs = Crypte.chaine(lstCr(ch.getJSONArray("lignes"))).values.toList()
    ko = 0
    val ve = v.getJSONArray("verifier")
    for (i in 0 until ve.length()) { val x = ve.getJSONObject(i)
        val e = Crypte.verifierChaine(lstCr(x.getJSONArray("blocs"))).map { listOf("${it.first}", it.second) }
        if (e != (0 until x.getJSONArray("etats").length()).map { lstCr(x.getJSONArray("etats").getJSONArray(it)) }) ko++ }
    verifierCr(blocs == lstCr(ch.getJSONArray("blocs")) && ko == 0, "la chaîne d'empreintes et sa vérification (ok, casse, douteux)")
    ko = 0
    val mi = v.getJSONArray("mine")
    for (i in 0 until mi.length()) { val x = mi.getJSONObject(i)
        if (Crypte.miner(x.getString("donnees"), x.getInt("zeros")) != (if (x.isNull("nonce")) null else x.getInt("nonce"))) ko++ }
    verifierCr(ko == 0, "la preuve de travail : les mêmes nonces (bloc5 : 20, 139, 2615)")
    ko = 0
    val sc = v.getJSONArray("sha512crypt")
    for (i in 0 until sc.length()) { val x = sc.getJSONObject(i)
        if (Crypte.sha512crypt(x.getString("mot"), x.getString("sel")) != x.getString("hache")) { ko++; println("    sha512crypt $x") } }
    verifierCr(ko == 0, "${sc.length()} SHA-crypt (openssl passwd -6) identiques")
    ko = 0
    val rd = v.getJSONArray("roue_deploie")
    for (i in 0 until rd.length()) { val x = rd.getJSONObject(i)
        val k = Deploie.roue(x.getString("ligne")).map { listOf("${it.seg}", it.de, it.vers, "${it.decalage}") }
        val a = (0 until x.getJSONArray("roues").length()).map { x.getJSONArray("roues").getJSONObject(it) }
            .map { listOf("${it.getInt("seg")}", it.getString("de"), it.getString("vers"), "${it.getInt("decalage")}") }
        if (k != a) { ko++; println("    roue ${x.getString("ligne")} → $k") } }
    verifierCr(ko == 0, "${rd.length()} lignes : la roue de César de la vue déployée")

    println("2. Les commandes intégrées du téléphone (openssl, gpg) et les vrais outils")
    val tmp = File(jeuCr.terrain, "essai").apply { mkdirs() }
    tapeCr("cd ~/terrain_terminagotchi/essai")
    if (aBash("openssl")) {
        val (vrai, _) = bashCr("openssl passwd -6 -salt sel2026 licorne", tmp)
        verifierCr(cmdCr.executer("openssl passwd -6 -salt sel2026 licorne")!!.texte == vrai.trim(), "openssl passwd -6 du téléphone = le vrai openssl")
    }
    verifierCr(Regex("^[0-9a-f]{32}$").matches(cmdCr.executer("openssl rand -hex 16")!!.texte), "openssl rand -hex 16 : 32 chiffres hexadécimaux")
    verifierCr(cmdCr.executer("openssl enc -aes-256-cbc -pbkdf2 -in x -pass pass:e")!!.texte.isNotEmpty(), "openssl enc : toujours celui de la Citadelle")
    verifierCr(cmdCr.executer("gpg --quick-gen-key a@crypte.example")!!.texte == t("cr.tel.gpg.homedir"),
        "gpg sans --homedir : refusé (le vrai trousseau n'est jamais visé)")
    verifierCr(cmdCr.executer("gpg --homedir /tmp/ailleurs -k")!!.texte == t("cr.tel.gpg.dehors") && !File("/tmp/ailleurs/cles.json").exists(),
        "gpg avec un --homedir hors du terrain : refusé")
    cmdCr.executer("gpg --homedir .trousseau --batch --passphrase \"\" --quick-gen-key tel@crypte.example")
    val trTel = CryptePgp.Trousseau(File(tmp, ".trousseau"))
    verifierCr(trTel.secrete("tel@crypte.example") != null, "gpg --quick-gen-key : une paire RSA d'EXEMPLE dans .trousseau (le terrain)")
    if (aBash("gpg")) {
        // le trousseau du VRAI gpg : un dossier court de /tmp (la prise de gpg-agent ne supporte pas les chemins longs)
        val gh = File("/tmp/tgg${System.nanoTime() % 100000}").apply { mkdirs() }
        bashCr("chmod 700 ${gh.path}", tmp)
        val g = "gpg --homedir ${gh.path} --batch --no-tty --trust-model always"
        // a. le vrai gpg importe la clé du téléphone et vérifie sa signature
        cmdCr.executer("gpg --homedir .trousseau --armor --export tel@crypte.example -o tel.asc")
        val imp = bashCr("$g --import tel.asc", tmp)
        verifierCr(imp.second == 0 && "imported" in imp.first, "le VRAI gpg importe la clé publique du téléphone")
        if (imp.second != 0) println(imp.first)
        File(tmp, "m.txt").writeText("Pixel donne 2 glands à Lune\n-- le sphinx\n")
        cmdCr.executer("gpg --homedir .trousseau --clearsign m.txt")
        val ver = bashCr("$g --verify m.txt.asc", tmp)
        verifierCr(ver.second == 0 && "Good signature" in ver.first, "le VRAI gpg vérifie la signature du téléphone : Good signature")
        File(tmp, "m2.asc").writeText(File(tmp, "m.txt.asc").readText().replace("2 glands", "20 glands"))
        verifierCr(bashCr("$g --verify m2.asc", tmp).let { it.second != 0 && "BAD signature" in it.first } &&
            "BAD signature" in cmdCr.executer("gpg --homedir .trousseau --verify m2.asc")!!.texte, "une lettre changée : BAD signature, chez les deux")
        // b. le vrai gpg chiffre pour le téléphone : le téléphone déchiffre
        File(tmp, "s.txt").writeText("pour le téléphone seulement\n")
        bashCr("$g -e -r tel@crypte.example -o s.gpg s.txt", tmp)
        verifierCr(cmdCr.executer("gpg --homedir .trousseau -d s.gpg")!!.texte == "pour le téléphone seulement",
            "le téléphone déchiffre ce que le VRAI gpg a chiffré pour lui (compression comprise)")
        // c. une clé RSA du vrai gpg : le téléphone l'importe, vérifie ses signatures, chiffre pour elle
        val gen = bashCr("$g --passphrase '' --quick-gen-key pc@crypte.example rsa2048 sign,cert never && " +
            "$g --passphrase '' --quick-add-key \$($g --list-keys --with-colons pc@crypte.example | awk -F: '/^fpr/{print \$10; exit}') rsa2048 encr never && " +
            "$g --armor --export pc@crypte.example > pc.asc && echo 'signé par le PC' > p.txt && $g --clearsign p.txt", tmp)
        if (gen.second != 0) println(gen.first)
        println("    " + cmdCr.executer("gpg --homedir .trousseau --import pc.asc")!!.texte.replace("\n", " ⏎ "))
        verifierCr("Good signature" in cmdCr.executer("gpg --homedir .trousseau --verify p.txt.asc")!!.texte,
            "le téléphone vérifie une signature RSA du VRAI gpg")
        File(tmp, "q.txt").writeText("pour le PC\n")
        cmdCr.executer("gpg --homedir .trousseau -e -r pc@crypte.example -o q.gpg q.txt")
        val dec = bashCr("$g -d q.gpg", tmp)
        verifierCr(dec.second == 0 && dec.first.endsWith("pour le PC\n"), "le VRAI gpg déchiffre ce que le téléphone a chiffré pour lui : ${dec.first.trim()}")
        bashCr("gpgconf --homedir ${gh.path} --kill gpg-agent", tmp)
        gh.deleteRecursively()
    } else println("  · gpg absent : compatibilité avec le vrai gpg non vérifiée ici")

    println("3. L'arbre du Carrefour")
    val h = Histoire.h(jeuCr)
    verifierCr(!Histoire.ouvert(jeuCr, "crypte"), "fermée au début : il manque ${Crypte.manque(jeuCr)}")
    val faits = h.getJSONArray("faits")
    for (c in listOf("reveil", "nid", "bibliotheque")) for (l in Histoire.PAR_CHAP[c]!!.lecons) faits.put(l)
    for (c in listOf("reveil", "nid")) h.getJSONArray("ailes").put(c)
    h.put("chap", "bibliotheque")
    h.put("mondes_annonces", JSONArray().put("port"))
    Histoire.tick(jeuCr, "ls", false, jeuCr.home, 0)
    verifierCr(Histoire.ouvert(jeuCr, "crypte"), "niveaux 0 à 4 finis : la Crypte s'ouvre")
    verifierCr("crypte" in lstCr(h.optJSONArray("mondes_annonces")) && !Crypte.annonce(jeuCr), "annoncée une seule fois")
    verifierCr(File(jeuCr.terrain, "crypte/regle_du_sphinx.txt").readText().contains("Pixel") &&
        File(jeuCr.terrain, "crypte/copies").listFiles()!!.size == 9, "la Crypte est meublée (règle, 9 copies)")

    println("4. La traversée de la Crypte sur le téléphone")
    jeuCr.xp = 10 * 30 * 30
    tapeCr("cd ~/terrain_terminagotchi/crypte")
    verifierCr(lecCr() == ("cr0" to 1), "entrer dans la Crypte choisit le monde : ${lecCr()}")
    val gr = Histoire.graine(jeuCr)
    val H = Crypte.HOMEDIR
    val etapes = listOf<() -> String>(
        { "ls" }, { "cat regle_du_sphinx.txt" },
        { "echo bonjour | base64" }, { "base64 -d messages/message_1.txt" }, { "xxd -r -p messages/message_2.txt" }, { "crypte demasque" },
        { "echo bonjour | tr 'a-z' 'd-za-c'" }, { "tr 'd-za-c' 'a-z' < grimoire/cesar.txt" }, { "tr 'a-z' 'n-za-m' < grimoire/rot13.txt" },
        { "grep -o '[a-z]' grimoire/mystere.txt | sort | uniq -c | sort -rn | head -3" }, { "crypte roue ${Crypte.decalage(gr)}" },
        { "echo -n a | sha256sum" }, { "echo -n b | sha256sum" }, { "crypte avalanche chat chas" }, { "sha256sum -c sceaux.sha256" },
        { "cat base_fictive.txt" }, { "cat dictionnaire.sh" }, { "sh dictionnaire.sh" }, { "openssl passwd -6 licorne" },
        { "cat parchemin.txt" }, { "openssl enc -aes-256-cbc -pbkdf2 -in parchemin.txt -out parchemin.enc -pass pass:${Crypte.CLE}" },
        { "head -c 8 parchemin.enc" }, { "crypte donne parchemin.enc" },
        { "crypte peintures" }, { "echo $((5*5*5*5*5*5 % 23))" }, { "gpg $H --batch --passphrase \"\" --quick-gen-key ${Crypte.MOI}" },
        { "gpg $H -e -r ${Crypte.CREATURE} -o secret.gpg secret.txt" }, { "crypte donne secret.gpg" },
        { "gpg $H --clearsign message.txt" }, { "gpg $H --verify message.txt.asc" },
        { "head -c 16 /dev/urandom | xxd" }, { "openssl rand -hex 16" }, { "crypte de" },
        { "crypte de ${Crypte.deSuite(gr, 6).last()}" },
        { "crypte quiz" }, { "crypte quiz " + Crypte.bonnesReponses(gr).joinToString(" ") },
        { "cat registre.txt" }, { "echo \"Lune donne 2 plumes a Pixel\" >> registre.txt" }, { "crypte registre" },
        { "cat chaine/bloc_1.txt" }, { "sha256sum chaine/bloc_0.txt" }, { "sh verifie_chaine.sh" }, { "echo triche >> chaine/bloc_1.txt" },
        { "sh verifie_chaine.sh" }, { "cp archives/bloc_1.txt chaine/" }, { "crypte chaine" },
        { "sha256sum copies/*/registre.txt" }, { "sha256sum copies/*/registre.txt | cut -c1-64 | sort | uniq -c" },
        { "diff copies/feu/registre.txt copies/${Crypte.tricheur(gr)}/registre.txt" }, { "crypte consensus ${Crypte.tricheur(gr)}" },
        { "cat mineur.sh" }, { "sh mineur.sh 2" }, { "crypte mine 3" }, { "crypte mine" },
        { "echo \"Pixel donne 2 glands a Lune\" > echange.txt" }, { "gpg $H --clearsign echange.txt" },
        { "gpg $H --verify echanges/faux.txt.asc" }, { "crypte signe echange.txt.asc" },
        { "crypte vitrine" }, { "grep -h donnees chaine/bloc_*.txt" }, { "sh verifie_chaine.sh carnet_de_bord" }, { "crypte recensement" },
    )
    val sorties = HashMap<String, String>()
    for (f in etapes) {
        val c = f()
        val avant = lecCr()
        val s = tapeCr(c)
        sorties[c] = s
        if (System.getenv("TG_DEBUG") != null) println("    · $c : $avant → ${lecCr()} ${s.take(80).replace("\n", " ⏎ ")}")
        if (Histoire.fini(jeuCr, "crypte")) break
    }
    verifierCr(Histoire.fini(jeuCr, "crypte"), "la Crypte est traversée jusqu'au bout (cr0 → cr14) : ${lecCr()}")
    verifierCr("givre" in (sorties["crypte donne secret.gpg"] ?: ""), "la créature ouvre le secret avec SA clé privée (gpg du téléphone)")
    verifierCr("BAD signature" in (sorties["gpg $H --verify echanges/faux.txt.asc"] ?: ""), "l'échange trafiqué est rejeté")
    verifierCr("nonce = 2615" in (sorties["crypte mine 3"] ?: ""), "crypte mine 3 : nonce = 2615 (comme le mineur du PC)")
    verifierCr(File(jeuCr.terrain, "crypte/chaine/bloc_5.txt").isFile, "l'échange signé devient le bloc 5 de la chaîne")
    val ex = Recompenses.etat(jeuCr).getJSONObject("exploits").keys().asSequence().toList()
    verifierCr("crypte.chaine" in ex && "crypte.b6" in ex, "les deux exploits : la chaîne réparée sans indice, le carnet de bord ($ex)")
    verifierCr("sceau_miniature" in lstCr(Quetes.q(jeuCr).optJSONArray("objets")), "récompense du monde : un sceau miniature")

    println("5. Les variantes réservées, le dessin")
    val j2 = Jeu(AppareilCr(File(dossier, "j2").apply { mkdirs() }, assets))
    verifierCr(Recompenses.reservee(j2, "crypte", "lichonarque") && Recompenses.reservee(j2, "cristal", "fractalis") &&
        !Recompenses.reservee(j2, "crypte", "osselet"), "la gardienne du registre (lichonarque:crypte) et les variantes Ombre/Glace réservées")
    Recompenses.exploit(j2, "crypte.b6")
    verifierCr(!Recompenses.reservee(j2, "crypte", "lichonarque"), "après un exploit de la Crypte : libérées")
    val tl = ToileCr()
    CrypteDessin.roue(tl, 3, 0.8, 0f, 0f, 400f, 170f, 1f)
    CrypteDessin.chaine(tl, Crypte.verifierChaine(listOf("a", "b", "c")), 0.5, 0f, 0f, 400f, 120f, 1f)
    CrypteDessin.peintures(tl, 0.9, 0f, 0f, 400f, 240f, 1f)
    CrypteDessin.mine(tl, 0f, 0f, 400f, 200f, 1f)
    CrypteDessin.crypte(tl, 0.3, 0f, 0f, 400f, 225f, 1f)
    verifierCr(tl.n > 150 && tl.textes.any { "bonjour → erqmrxu" in it }, "le dessin : roue, chaîne, peintures, mine, crypte de repli (${tl.n} traits)")
    val vue = Deploie.vue("echo bonjour | tr 'a-z' 'd-za-c'")!!
    verifierCr(vue.roueDe(vue.blocs[3])?.decalage == 3 && vue.roueDe(vue.blocs[0]) == null, "la vue déployée sait que le bloc tr a sa roue")

    println("\n$okCr réussis, $koCr échoués")
    kotlin.system.exitProcess(if (koCr == 0) 0 else 1)
}
