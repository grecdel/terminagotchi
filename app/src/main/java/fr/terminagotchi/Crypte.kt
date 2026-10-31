package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.security.MessageDigest
import java.security.SecureRandom
import java.text.Normalizer

/**
 * 🗝 La Crypte des Codes — cryptographie et blockchain (docs/programme.md § 7.9), portage de pc/tg/crypte.py.
 *
 * Mêmes règles que sur PC (César et ROT13, fréquences, roue, empreintes, base FICTIVE, peintures, dé pipé, quiz, chaîne
 * d'empreintes, copies des 9 biomes, preuve de travail, carnet de bord) : vecteurs communs donnees/crypte/vecteurs.json,
 * vérifiés par tests/jvm/Crypte.kt. Tout reste HORS LIGNE dans terrain_terminagotchi/crypte/ ; aucune vraie monnaie,
 * aucun jeton, aucun achat ; toutes les clés sont des EXEMPLES.
 *
 * Sur le téléphone, le shell (toybox) fait le vrai travail (base64, xxd, tr, grep, sort, uniq, sha256sum, cut, seq, sh
 * pour les scripts du sphinx), et des commandes intégrées remplacent ce qui manque, sans jamais sortir du terrain :
 *  - `openssl passwd -6 MOT` (SHA-crypt, identique au vrai openssl) et `openssl rand -hex N` ; `openssl enc` reste
 *    celui de la Citadelle ;
 *  - `gpg --homedir DOSSIER …` : un OpenPGP réduit mais RÉEL (CryptePgp.kt : clés RSA, signatures en clair, chiffrement
 *    pour une clé publique), compatible avec le vrai gpg (tests/jvm/Crypte.kt) ; --homedir est obligatoire ;
 *  - `crypte …` : roue, avalanche, donne, peintures, dé, quiz, registre, chaîne, consensus, mine, signe, vitrine,
 *    recensement. `crypte mine 3` remplace `time sh mineur.sh 3` (2615 tours de shell seraient trop lents ici).
 */
object Crypte {
    @Volatile var chargeur: (() -> String?)? = null
    private var d: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("crypte.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun donnees(): JSONObject = d ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() }).also { d = it }

    private fun liste(o: JSONObject?, k: String): List<String> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.get(it).toString() } } ?: emptyList()
    private fun objets(o: JSONObject?, k: String): List<JSONObject> = o?.optJSONArray(k)?.let { a -> (0 until a.length()).map { a.getJSONObject(it) } } ?: emptyList()

    // ---------------------------------------------------------------- la spécification pure (vecteurs communs)
    const val ALPHA = "abcdefghijklmnopqrstuvwxyz"
    val LATINES = setOf("fr", "en", "es", "de", "it", "pt", "id")

    private fun hex(b: ByteArray) = b.joinToString("") { "%02x".format(it) }
    fun sha(s: String) = hex(MessageDigest.getInstance("SHA-256").digest(s.toByteArray(Charsets.UTF_8)))
    fun shaOctets(b: ByteArray) = hex(MessageDigest.getInstance("SHA-256").digest(b))

    fun asciiBas(texte: String): String {
        val s = Normalizer.normalize(texte.lowercase(), Normalizer.Form.NFKD)
        return s.filter { Character.getType(it) != Character.NON_SPACING_MARK.toInt() }.replace("œ", "oe").replace("æ", "ae").replace("ß", "ss")
    }

    fun cesar(texte: String, k0: Int): String {
        val k = ((k0 % 26) + 26) % 26
        return texte.map { c -> val i = ALPHA.indexOf(c); if (i >= 0) ALPHA[(i + k) % 26] else c }.joinToString("")
    }

    /** (nombre, lettre) du plus fréquent au moins fréquent ; égalités : lettre la plus grande d'abord (comme sort -rn). */
    fun frequences(texte: String): List<Pair<Int, Char>> {
        val c = LinkedHashMap<Char, Int>()
        for (x in texte) if (x in ALPHA) c[x] = (c[x] ?: 0) + 1
        return c.entries.map { it.value to it.key }.sortedWith(compareBy({ -it.first }, { -it.second.code }))
    }

    fun decalage(graine: String): Int {
        val evites = (donnees().optJSONObject("cesar")?.optJSONArray("evites") ?: JSONArray()).let { a -> (0 until a.length()).map { a.getInt(it) } }
        val v = sha("$graine:roue").substring(0, 8).toLong(16)
        val choix = (0 until 26).filter { it !in evites }
        return choix[(v % choix.size).toInt()]
    }

    fun deplier(s0: String): List<Char>? {
        val s = s0.trim('\'', '"')
        val out = mutableListOf<Char>()
        var i = 0
        while (i < s.length) {
            if (i + 2 < s.length && s[i + 1] == '-') {
                val a = s[i]; val b = s[i + 2]
                if (b < a) return null
                for (x in a..b) out.add(x)
                i += 3
            } else { out.add(s[i]); i++ }
        }
        return out
    }

    /** Le décalage de `tr DE VERS` si c'est une roue de César sur a-z, sinon null. */
    fun rotation(de: String, vers: String): Int? {
        val a = deplier(de) ?: return null
        val b = deplier(vers) ?: return null
        if (a.isEmpty() || b.isEmpty() || a.size < 26 || b.size < a.size) return null
        val ks = mutableSetOf<Int>()
        for ((x, y) in a.zip(b)) {
            when {
                x in ALPHA && y in ALPHA -> ks.add(((ALPHA.indexOf(y) - ALPHA.indexOf(x)) % 26 + 26) % 26)
                x.lowercaseChar() in ALPHA && y.lowercaseChar() in ALPHA && x.isUpperCase() == y.isUpperCase() ->
                    ks.add(((ALPHA.indexOf(y.lowercaseChar()) - ALPHA.indexOf(x.lowercaseChar())) % 26 + 26) % 26)
                else -> return null
            }
        }
        if (ks.size != 1 || !ALPHA.all { it in a }) return null
        return ks.first()
    }

    fun messageCode(n: Int, texte: String): String {
        val code = objets(donnees(), "messages").firstOrNull { it.optInt("n") == n }?.optString("code") ?: "base64"
        val b = texte.toByteArray(Charsets.UTF_8)
        return when (code) {
            "base64" -> java.util.Base64.getEncoder().encodeToString(b) + "\n"
            "hex" -> hex(b) + "\n"
            else -> cesar(asciiBas(texte), 13) + "\n"
        }
    }

    fun bitsDifferents(a: String, b: String) = java.math.BigInteger(a, 16).xor(java.math.BigInteger(b, 16)).bitCount()
    fun lettresDifferentes(a: String, b: String) = a.zip(b).count { it.first != it.second }

    fun baseFictive() = objets(donnees(), "base").map { "${it.optString("nom")}:${sha(it.optString("passe"))}" }
    fun trouvesParDico(): List<Pair<String, String>> {
        val par = objets(donnees(), "base").associate { sha(it.optString("passe")) to it.optString("nom") }
        return liste(donnees(), "dico").filter { sha(it) in par }.map { par.getValue(sha(it)) to it }
    }

    private fun puissanceMod(b: Int, e: Int, m: Int) = java.math.BigInteger.valueOf(b.toLong()).modPow(java.math.BigInteger.valueOf(e.toLong()), java.math.BigInteger.valueOf(m.toLong())).toInt()

    fun peintures(): Map<String, Int> {
        val p0 = donnees().optJSONObject("peintures") ?: JSONObject()
        val p = p0.optInt("p", 23); val g = p0.optInt("g", 5); val a = p0.optInt("a", 6); val b = p0.optInt("b", 15)
        val A = puissanceMod(g, a, p); val B = puissanceMod(g, b, p)
        return linkedMapOf("p" to p, "g" to g, "a" to a, "b" to b, "A" to A, "B" to B, "s1" to puissanceMod(B, a, p), "s2" to puissanceMod(A, b, p))
    }

    fun deSuite(graine: String, n: Int): List<Int> {
        val d = donnees().optJSONObject("de") ?: JSONObject()
        var x = sha("$graine:de").substring(0, 4).toInt(16) % d.optInt("m", 8)
        return (0 until n).map { x = (d.optInt("a", 5) * x + d.optInt("c", 3)) % d.optInt("m", 8); x }
    }

    fun quiz(graine: String): List<Triple<Int, String, String>> {
        val q = objets(donnees(), "quiz").toMutableList()
        PyHasard("quiz:$graine").melanger(q)
        return q.mapIndexed { i, x -> Triple(i + 1, x.optString("id"), x.optString("rep")) }
    }

    fun bonnesReponses(graine: String) = quiz(graine).map { it.third }

    fun blocTexte(k: Int, precedent: String, donnees: String) = "bloc: $k\nprecedent: $precedent\ndonnees: $donnees\n"

    fun chaine(lignes: List<String>): LinkedHashMap<String, String> {
        val out = LinkedHashMap<String, String>()
        var prec = "0".repeat(64)
        lignes.forEachIndexed { k, d -> val txt = blocTexte(k, prec, d); out["bloc_$k.txt"] = txt; prec = sha(txt) }
        return out
    }

    /** (k, état) pour chaque maillon k → k+1 : « ok », « casse », « douteux » (après une cassure). */
    fun verifierChaine(blocs: List<String>): List<Pair<Int, String>> {
        val out = mutableListOf<Pair<Int, String>>()
        var casse = false
        for (k in 0 until blocs.size - 1) {
            val note = Regex("^precedent: (\\S+)", RegexOption.MULTILINE).find(blocs[k + 1])?.groupValues?.get(1) ?: ""
            when {
                casse -> out.add(k to "douteux")
                note == sha(blocs[k]) -> out.add(k to "ok")
                else -> { out.add(k to "casse"); casse = true }
            }
        }
        return out
    }

    fun tricheur(graine: String): String {
        val b = liste(donnees(), "biomes")
        return b[1 + (sha("$graine:tricheur").substring(0, 6).toInt(16) % (b.size - 1))]
    }

    fun miner(donneesBloc: String, zeros: Int, maximum: Int? = null): Int? {
        val mx = maximum ?: donnees().optJSONObject("mine")?.optInt("max", 100000) ?: 100000
        val z = "0".repeat(zeros)
        for (n in 1..mx) if (sha("$donneesBloc$n").startsWith(z)) return n
        return null
    }

    /** openssl passwd -6 (SHA-crypt, 5000 tours), comme sha512crypt sur PC et le vrai openssl. */
    fun sha512crypt(mot: String, sel0: String, tours: Int = 5000): String {
        val p = mot.toByteArray(Charsets.UTF_8)
        val s = sel0.toByteArray(Charsets.UTF_8).let { it.copyOf(minOf(16, it.size)) }
        fun h(vararg x: ByteArray): ByteArray { val m = MessageDigest.getInstance("SHA-512"); x.forEach { m.update(it) }; return m.digest() }
        val b = h(p, s, p)
        val a = MessageDigest.getInstance("SHA-512")
        a.update(p); a.update(s)
        var n = p.size
        while (n > 64) { a.update(b); n -= 64 }
        a.update(b, 0, n)
        n = p.size
        while (n != 0) { a.update(if (n and 1 != 0) b else p); n = n shr 1 }
        val ad = a.digest()
        val dp = h(ByteArray(0).let { var acc = it; repeat(p.size) { acc += p }; acc })
        val P = ByteArray(p.size) { dp[it % 64] }
        val ds = h(ByteArray(0).let { var acc = it; repeat(16 + (ad[0].toInt() and 255)) { acc += s }; acc })
        val S = ByteArray(s.size) { ds[it % 64] }
        var c = ad
        for (i in 0 until tours) {
            val x = MessageDigest.getInstance("SHA-512")
            x.update(if (i and 1 != 0) P else c)
            if (i % 3 != 0) x.update(S)
            if (i % 7 != 0) x.update(P)
            x.update(if (i and 1 != 0) c else P)
            c = x.digest()
        }
        val car = "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        val ordre = listOf(intArrayOf(0, 21, 42), intArrayOf(22, 43, 1), intArrayOf(44, 2, 23), intArrayOf(3, 24, 45), intArrayOf(25, 46, 4),
            intArrayOf(47, 5, 26), intArrayOf(6, 27, 48), intArrayOf(28, 49, 7), intArrayOf(50, 8, 29), intArrayOf(9, 30, 51),
            intArrayOf(31, 52, 10), intArrayOf(53, 11, 32), intArrayOf(12, 33, 54), intArrayOf(34, 55, 13), intArrayOf(56, 14, 35),
            intArrayOf(15, 36, 57), intArrayOf(37, 58, 16), intArrayOf(59, 17, 38), intArrayOf(18, 39, 60), intArrayOf(40, 61, 19),
            intArrayOf(62, 20, 41))
        val out = StringBuilder()
        fun o(i: Int) = c[i].toInt() and 255
        for (t in ordre) { var v = (o(t[0]) shl 16) or (o(t[1]) shl 8) or o(t[2]); repeat(4) { out.append(car[v and 63]); v = v shr 6 } }
        var v = o(63); repeat(2) { out.append(car[v and 63]); v = v shr 6 }
        return "\$6\$${String(s, Charsets.UTF_8)}\$$out"
    }

    // ---------------------------------------------------------------- l'état, le terrain, le carnet du sphinx
    fun etat(jeu: Jeu): JSONObject {
        val c = jeu.module("crypte")
        if (c.optJSONArray("faits") == null) c.put("faits", JSONArray())
        return c
    }

    private fun faits(jeu: Jeu) = liste(etat(jeu), "faits")
    private fun fait(jeu: Jeu, cle: String): Boolean {
        if (cle in faits(jeu)) return true
        etat(jeu).getJSONArray("faits").put(cle)
        return false
    }

    const val CARNET = "carnet_du_sphinx.txt"
    fun dossier(jeu: Jeu) = File(jeu.terrain, "crypte")

    fun noter(jeu: Jeu, etiquette: String, texte: String) {
        try { dossier(jeu).mkdirs(); File(dossier(jeu), CARNET).appendText("[$etiquette] $texte\n") } catch (e: Exception) { }
    }

    fun carnet(jeu: Jeu): String = try { File(dossier(jeu), CARNET).readText() } catch (e: Exception) { "" }
    fun dansCarnet(jeu: Jeu, etiquette: String, mot: String = "ok", sujet: String? = null): Boolean {
        val debut = if (sujet != null) "^\\[$etiquette] ${Regex.escape(sujet)}\\b" else "^\\[$etiquette]"
        return Regex("$debut.*\\($mot\\)\\s*$", RegexOption.MULTILINE).containsMatchIn(carnet(jeu))
    }

    fun lire(jeu: Jeu, rel: String) = Histoire.lire(jeu, "crypte/$rel") ?: ""

    private fun ecrire(jeu: Jeu, rel: String, texte: String) = Histoire.ecrire(jeu, "crypte/$rel", texte, finLigne = false)

    /** Un texte posé dans un script shell entre guillemets doubles. */
    private fun sur(s: String) = s.replace(Regex("[\"$`\\\\]"), "'")

    fun latin() = if (Langue.courante in LATINES) Langue.courante else "en"
    fun grimoire(cle: String) = asciiBas((Langue.brut(cle, latin()) ?: Langue.brut(cle, "en") ?: "").toString())

    fun lignesRegistre() = (1..4).map { t("cr.registre.$it") }
    fun donneesChaine() = (0 until (donnees().optJSONObject("chaine")?.optInt("blocs", 5) ?: 5)).map { t("cr.bloc.$it") }

    fun mineurSh(): String {
        val m = donnees().optJSONObject("mine") ?: JSONObject()
        return "#!/bin/sh\n# ${sur(t("cr.mine.sh1"))}\n# ${sur(t("cr.mine.sh2"))}\nBLOC=\"${m.optString("donnees")}\"\nd=\${1:-2}\n" +
            "if [ \"\$d\" -gt ${m.optInt("difficulte_max", 3)} ]; then echo \"${sur(t("cr.mine.trop"))}\"; exit 1; fi\n" +
            "z=\$(echo 0000000 | cut -c1-\$d)\nfor n in \$(seq 1 ${m.optInt("max", 100000)}); do\n" +
            "  h=\$(printf '%s%s' \"\$BLOC\" \"\$n\" | sha256sum)\n  case \"\$h\" in\n" +
            "    \"\$z\"*) echo \"nonce = \$n\"; echo \"\$h\"; echo \"${sur(t("cr.mine.essais"))} \$n\"; exit 0 ;;\n  esac\ndone\n" +
            "echo \"${sur(t("cr.mine.rien"))}\"\nexit 1\n"
    }

    fun verifieSh(): String {
        val m = sur(t("cr.verifie.maillon"))
        return "#!/bin/sh\n# ${sur(t("cr.verifie.sh1"))}\nd=\${1:-chaine}\nn=0; casse=0\n" +
            "while [ -f \"\$d/bloc_\$((n+1)).txt\" ]; do\n  vrai=\$(sha256sum \"\$d/bloc_\$n.txt\" | cut -c1-64)\n" +
            "  note=\$(grep '^precedent:' \"\$d/bloc_\$((n+1)).txt\" | cut -d' ' -f2)\n  if [ \"\$casse\" = 1 ]; then\n" +
            "    echo \"$m \$n -> \$((n+1)) : ? ${sur(t("cr.verifie.douteux"))}\"\n  elif [ \"\$vrai\" = \"\$note\" ]; then\n" +
            "    echo \"$m \$n -> \$((n+1)) : OK\"\n  else\n    echo \"$m \$n -> \$((n+1)) : ${sur(t("cr.verifie.casse"))}\"; casse=1\n" +
            "  fi\n  n=\$((n+1))\ndone\nif [ \"\$casse\" = 0 ]; then echo \"${sur(t("cr.verifie.intacte"))}\"; exit 0; fi\n" +
            "echo \"${sur(t("cr.verifie.brisee"))}\"; exit 1\n"
    }

    fun dictionnaireSh() = "#!/bin/sh\n# ${sur(t("cr.dico.sh1"))}\n# ${sur(t("cr.dico.sh2"))}\nwhile read -r mot; do\n" +
        "  e=\$(printf '%s' \"\$mot\" | sha256sum | cut -c1-64)\n  qui=\$(grep \":\$e\\\$\" base_fictive.txt | cut -d: -f1)\n" +
        "  if [ -n \"\$qui\" ]; then echo \"${sur(t("cr.dico.trouve"))} \$qui -> \$mot\"; fi\ndone < dico.txt\n" +
        "echo \"${sur(t("cr.dico.fin"))}\"\n"

    /** Ce que le jeu pose dans la Crypte quand elle s'ouvre (mêmes fichiers que sur PC). */
    fun meubles(jeu: Jeu): Map<String, Any> {
        val gr = Histoire.graine(jeu)
        val m = linkedMapOf<String, Any>(
            "crypte/regle_du_sphinx.txt" to t("cr.meuble.regle", "nom" to jeu.nom),
            "crypte/$CARNET" to t("cr.meuble.carnet") + "\n",
            "crypte/grimoire/cesar.txt" to cesar(grimoire("cr.grimoire.cesar"), 3) + "\n",
            "crypte/grimoire/rot13.txt" to cesar(grimoire("cr.grimoire.rot13"), 13) + "\n",
            "crypte/grimoire/mystere.txt" to cesar(grimoire("cr.grimoire.mystere"), decalage(gr)) + "\n",
            "crypte/base_fictive.txt" to baseFictive().joinToString("\n") + "\n",
            "crypte/dico.txt" to liste(donnees(), "dico").joinToString("\n") + "\n",
            "crypte/dictionnaire.sh" to dictionnaireSh(),
            "crypte/parchemin.txt" to t("cr.meuble.parchemin", "nom" to jeu.nom) + "\n",
            "crypte/secret.txt" to t("cr.meuble.secret") + "\n",
            "crypte/message.txt" to t("cr.meuble.message", "nom" to jeu.nom) + "\n",
            "crypte/registre.txt" to lignesRegistre().joinToString("\n") + "\n",
            "crypte/verifie_chaine.sh" to verifieSh(),
            "crypte/mineur.sh" to mineurSh())
        for (x in objets(donnees(), "messages")) { val n = x.optInt("n"); m["crypte/messages/message_$n.txt"] = messageCode(n, t("cr.msg.$n")) }
        for (i in 1..3) m["crypte/grimoires/sort_$i.txt"] = t("cr.sort.$i") + "\n"
        m["crypte/sceaux.sha256"] = (1..3).joinToString("") { "${sha(m["crypte/grimoires/sort_$it.txt"].toString())}  grimoires/sort_$it.txt\n" }
        for ((nom, txt) in chaine(donneesChaine())) { m["crypte/chaine/$nom"] = txt; m["crypte/archives/$nom"] = txt }
        val reg = donneesChaine().joinToString("\n") + "\n"
        val tr = tricheur(gr)
        for (b in liste(donnees(), "biomes")) m["crypte/copies/$b/registre.txt"] = if (b != tr) reg else reg.replace(t("cr.bloc.2"), t("cr.bloc.2_triche"))
        return m
    }

    val BESOINS = mapOf("cr0" to listOf("regle_du_sphinx.txt"), "cr1" to listOf("messages/message_1.txt", "messages/message_2.txt"),
        "cr2" to listOf("grimoire/cesar.txt", "grimoire/rot13.txt", "grimoire/mystere.txt"),
        "cr3" to listOf("sceaux.sha256", "grimoires/sort_1.txt", "grimoires/sort_3.txt"),
        "cr4" to listOf("base_fictive.txt", "dico.txt", "dictionnaire.sh"), "cr5" to listOf("parchemin.txt"),
        "cr6" to listOf("secret.txt", "message.txt"), "cr9" to listOf("registre.txt"),
        "cr10" to listOf("verifie_chaine.sh") + (0 until 5).map { "archives/bloc_$it.txt" }, "cr12" to listOf("mineur.sh"),
        "cr14" to listOf("verifie_chaine.sh"))

    // ---------------------------------------------------------------- gpg intégré : les trousseaux du terrain
    val G: JSONObject get() = donnees().optJSONObject("gpg") ?: JSONObject()
    val MOI: String get() = G.optString("moi", "explorateur@crypte.example")
    val CREATURE: String get() = G.optString("creature", "creature@crypte.example")
    fun trousseau(jeu: Jeu, creature: Boolean = false) = File(dossier(jeu), if (creature) G.optString("dossier_creature", ".trousseau_creature") else G.optString("dossier", ".trousseau"))

    fun preparerCreature(jeu: Jeu): Boolean {
        val tc = CryptePgp.Trousseau(trousseau(jeu, true))
        if (tc.secrete(CREATURE) == null) tc.generer(CREATURE)
        val t0 = CryptePgp.Trousseau(trousseau(jeu))
        if (t0.publique(CREATURE) == null) tc.publique(CREATURE)?.let { t0.importer(it) }
        return t0.publique(CREATURE) != null
    }

    fun preparerEchanges(jeu: Jeu): Boolean {
        if (!preparerCreature(jeu)) return false
        val tc = CryptePgp.Trousseau(trousseau(jeu, true))
        val k = tc.secrete(CREATURE) ?: return false
        val s = CryptePgp.signerEnClair(t("cr.echange.vrai") + "\n", k)
        ecrire(jeu, "echanges/vrai.txt.asc", s)
        ecrire(jeu, "echanges/faux.txt.asc", s.replace(t("cr.echange.vrai"), t("cr.echange.faux")))
        return true
    }

    // ---------------------------------------------------------------- le carnet de bord, meubler
    fun carnetDeBord(jeu: Jeu): Map<String, String> {
        val f = liste(Histoire.h(jeu), "faits")
        val l = mutableListOf(t("cr.bord.debut", "nom" to jeu.nom))
        for (lid in f) if (lid in IDS) l.add(t("cr.bord.lecon", "titre" to t("hist.$lid.titre")))
        for (c in Histoire.CHAPITRES) if (Histoire.fini(jeu, c.id)) l.add(t("cr.bord.chapitre", "chapitre" to Histoire.nomChapitre(c.id)))
        return chaine(l)
    }

    fun blocs(jeu: Jeu, rel: String = "chaine"): List<String> {
        val out = mutableListOf<String>()
        var k = 0
        while (File(dossier(jeu), "$rel/bloc_$k.txt").isFile) { out.add(lire(jeu, "$rel/bloc_$k.txt").replace("\r\n", "\n")); k++ }
        return out
    }

    fun chaineCassee(jeu: Jeu, rel: String = "chaine") = verifierChaine(blocs(jeu, rel)).any { it.second != "ok" }

    /** Appelé par Histoire.meubler pendant une leçon de la Crypte (comme meubler sur PC). */
    fun meubler(jeu: Jeu, lid: String?) {
        val d = dossier(jeu)
        if (!d.isDirectory || lid == null) return
        val step = jeu.etape
        val tous = meubles(jeu)
        for (r in BESOINS[lid] ?: emptyList()) if (!File(d, r).exists()) tous["crypte/$r"]?.let { ecrire(jeu, r, it.toString()) }
        if (lid == "cr3" && !fait(jeu, "altere")) ecrire(jeu, "grimoires/sort_2.txt", t("cr.sort.2_altere") + "\n")
        if (lid == "cr9" && step >= 2 && !fait(jeu, "registre"))
            ecrire(jeu, "registre.txt", lire(jeu, "registre.txt").replace(t("cr.registre.2"), t("cr.registre.2_triche")))
        if (lid == "cr10") {
            for (k in 0 until 5) if (!File(d, "chaine/bloc_$k.txt").exists()) ecrire(jeu, "chaine/bloc_$k.txt", tous["crypte/archives/bloc_$k.txt"].toString())
            if (chaineCassee(jeu) && !dansCarnet(jeu, "triche", "vu")) noter(jeu, "triche", "chaine (vu)")
            if (!jeu.indiceLecon.isNullOrEmpty() && "indice:cr10" !in faits(jeu)) etat(jeu).getJSONArray("faits").put("indice:cr10")
        }
        if (lid == "cr6" || lid == "cr13") {
            preparerCreature(jeu)
            if (lid == "cr13" && !File(d, "echanges/faux.txt.asc").exists()) preparerEchanges(jeu)
            if (lid == "cr13") CryptePgp.Trousseau(trousseau(jeu)).let { if (it.secrete(MOI) == null) it.generer(MOI) }
        }
        if (lid == "cr14" && !fait(jeu, "bord")) for ((nom, txt) in carnetDeBord(jeu)) ecrire(jeu, "carnet_de_bord/$nom", txt)
        pontMaths(jeu, lid, step)
    }

    private fun pontMaths(jeu: Jeu, lid: String, step: Int) {
        val e = Programme.donnees().optJSONObject("etapes")?.optJSONObject("$lid.$step") ?: return
        for (mid in liste(e, "maths")) {
            if (Maths.noeud(mid) != null && !Maths.sait(jeu, mid) && !fait(jeu, "pont:$mid")) {
                jeu.dire(t("cr.pont", "notion" to Maths.titre(mid), "cmd" to "maths $mid"), 16)
                break
            }
        }
    }

    // ---------------------------------------------------------------- les leçons
    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)
    private const val LS = "^(ls|dir)\\b"
    private const val LIRE = "^(cat|less|more|head|tail)\\b"
    private const val CR = "^(tg\\s+)?crypte\\s+"
    private const val GPG = "^gpg2?\\b(?=.*--homedir\\s+\\S*\\.trousseau\\b)"
    val CLE: String get() = donnees().optString("cle_exemple", "sphinx-de-givre-exemple")
    val HOMEDIR: String get() = "--homedir " + G.optString("dossier", ".trousseau")
    private const val SH = "^((sh|bash)\\s+|\\./)\\S*"

    private fun n(lid: String, i: Int, cmd: String, re: String? = null, fs: ((Jeu) -> Boolean)? = null, ou: String? = null,
                  cree: String? = null, exploit: String? = null, echoue: Boolean = false) =
        Etape("hist.$lid.$i.dit", cmd, "hist.$lid.$i.bravo", re?.let { r(it) }, fs, null, cree, ou, exploit = exploit, echoue = echoue)

    private fun asc(j: Jeu, nom: String) = try { File(dossier(j), nom).readText().startsWith("-----BEGIN PGP SIGNED MESSAGE-----") } catch (e: Exception) { false }

    val IDS = (0..14).map { "cr$it" }

    fun lecons(jeu: Jeu): Map<String, Lecon> {
        val carnetOk = { et: String, s: String? -> { j: Jeu -> dansCarnet(j, et, sujet = s) } }
        return linkedMapOf(
            "cr0" to Lecon("hist.cr0.titre", null, 1, listOf(
                Etape("hist.entree.dit", "cd ~/terrain_terminagotchi/crypte", "hist.entree.bravo", ici = "crypte", params = mapOf("piece" to "crypte")),
                n("cr0", 1, "ls", re = LS, ou = "crypte"),
                n("cr0", 2, "cat regle_du_sphinx.txt", re = "$LIRE.*regle_du_sphinx"),
            )),
            "cr1" to Lecon("hist.cr1.titre", null, 1, listOf(
                n("cr1", 0, "echo bonjour | base64", re = "^(echo|printf)\\b.*\\|\\s*base64\\s*$", ou = "crypte"),
                n("cr1", 1, "base64 -d messages/message_1.txt", re = "^(base64\\s+(-d|--decode)\\b.*message_1|cat\\b.*message_1.*\\|\\s*base64\\s+(-d|--decode))"),
                n("cr1", 2, "xxd -r -p messages/message_2.txt", re = "^(xxd\\b(?=.*-r)(?=.*-p).*message_2|cat\\b.*message_2.*\\|\\s*xxd\\b(?=.*-r))"),
                n("cr1", 3, "crypte demasque", fs = carnetOk("demasque", null)),
            )),
            "cr2" to Lecon("hist.cr2.titre", null, 1, listOf(
                n("cr2", 0, "echo bonjour | tr 'a-z' 'd-za-c'", re = "^(echo|printf)\\b.*\\|\\s*tr\\s+['\"]?a-z['\"]?\\s+['\"]?d-za-c", ou = "crypte"),
                n("cr2", 1, "tr 'd-za-c' 'a-z' < grimoire/cesar.txt", re = "(^tr\\b.*d-za-c['\"]?\\s+['\"]?a-z.*<\\s*\\S*cesar|^cat\\b.*cesar.*\\|\\s*tr\\b.*d-za-c['\"]?\\s+['\"]?a-z)"),
                n("cr2", 2, "tr 'a-z' 'n-za-m' < grimoire/rot13.txt", re = "(^tr\\b.*(a-z['\"]?\\s+['\"]?n-za-m|n-za-m['\"]?\\s+['\"]?a-z).*<\\s*\\S*rot13|^cat\\b.*rot13.*\\|\\s*tr\\b.*n-za-m)"),
                n("cr2", 3, "grep -o '[a-z]' grimoire/mystere.txt | sort | uniq -c | sort -rn | head -3",
                    re = "^(grep\\s+-\\w*o\\b.*mystere|fold\\b.*mystere|cat\\b.*mystere.*\\|\\s*(grep\\s+-\\w*o|fold)\\b).*\\|\\s*sort\\b.*\\|\\s*uniq\\s+-c"),
                n("cr2", 4, "crypte roue ?", fs = carnetOk("roue", null)),
            )),
            "cr3" to Lecon("hist.cr3.titre", null, 1, listOf(
                n("cr3", 0, "echo -n a | sha256sum", re = "^(echo\\s+-n|printf)\\s+['\"]?a['\"]?\\s*\\|\\s*sha256sum\\b", ou = "crypte"),
                n("cr3", 1, "echo -n b | sha256sum", re = "^(echo\\s+-n|printf)\\s+['\"]?b['\"]?\\s*\\|\\s*sha256sum\\b"),
                n("cr3", 2, "crypte avalanche chat chas", re = "${CR}avalanche\\s+\\S+\\s+\\S+"),
                n("cr3", 3, "sha256sum -c sceaux.sha256", re = "^sha256sum\\s+(-c|--check)\\b.*sceaux", echoue = true),
            )),
            "cr4" to Lecon("hist.cr4.titre", null, 1, listOf(
                n("cr4", 0, "cat base_fictive.txt", re = "$LIRE.*base_fictive", ou = "crypte"),
                n("cr4", 1, "cat dictionnaire.sh", re = "$LIRE.*dictionnaire\\.sh"),
                n("cr4", 2, "sh dictionnaire.sh", re = "${SH}dictionnaire\\.sh\\b"),
                n("cr4", 3, "openssl passwd -6 licorne", re = "^openssl\\s+passwd\\s+-6\\b"),
            )),
            "cr5" to Lecon("hist.cr5.titre", null, 1, listOf(
                n("cr5", 0, "cat parchemin.txt", re = "$LIRE.*parchemin\\.txt", ou = "crypte"),
                n("cr5", 1, "openssl enc -aes-256-cbc -pbkdf2 -in parchemin.txt -out parchemin.enc -pass pass:$CLE",
                    fs = { j -> try { File(dossier(j), "parchemin.enc").readBytes().let { b -> b.copyOf(8).contentEquals("Salted__".toByteArray()) &&
                        Citadelle.chiffrer(b, CLE, true).isNotEmpty() } } catch (e: Exception) { false } }, cree = "crypte/parchemin.enc"),
                n("cr5", 2, "head -c 8 parchemin.enc", re = "^(head\\s+-c\\s*8\\b.*parchemin\\.enc|(xxd|od|hexdump)\\b.*parchemin\\.enc)"),
                n("cr5", 3, "crypte donne parchemin.enc", fs = carnetOk("donne", "parchemin.enc")),
            )),
            // le shell du téléphone (mksh) n'a pas ** : la puissance s'écrit avec des multiplications
            "cr6" to Lecon("hist.cr6.titre", null, 1, listOf(
                n("cr6", 0, "crypte peintures", re = "${CR}peintures?\\b", ou = "crypte"),
                n("cr6", 1, "echo $((5*5*5*5*5*5 % 23))", re = "^echo\\s+\\$\\(\\(\\s*5\\s*(\\*\\*\\s*6|(\\*\\s*5\\s*){5})\\s*%\\s*23\\s*\\)\\)"),
                n("cr6", 2, "gpg $HOMEDIR --batch --passphrase \"\" --quick-gen-key $MOI", fs = { j -> CryptePgp.Trousseau(trousseau(j)).secrete(MOI) != null }),
                n("cr6", 3, "gpg $HOMEDIR -e -r $CREATURE -o secret.gpg secret.txt",
                    fs = { j -> File(dossier(j), "secret.gpg").let { it.isFile && it.length() > 0 && it.readBytes()[0].toInt() and 0x80 != 0 } }, cree = "crypte/secret.gpg"),
                n("cr6", 4, "crypte donne secret.gpg", fs = carnetOk("donne", "secret.gpg")),
                n("cr6", 5, "gpg $HOMEDIR --clearsign message.txt", fs = { j -> asc(j, "message.txt.asc") }),
                n("cr6", 6, "gpg $HOMEDIR --verify message.txt.asc", re = "$GPG.*--verify\\b.*message\\.txt\\.asc"),
            )),
            "cr7" to Lecon("hist.cr7.titre", null, 1, listOf(
                n("cr7", 0, "head -c 16 /dev/urandom | xxd", re = "^head\\s+-c\\s*16\\s+/dev/u?random\\s*\\|\\s*(xxd|od|base64|hexdump)\\b", ou = "crypte"),
                n("cr7", 1, "openssl rand -hex 16", re = "^openssl\\s+rand\\s+-hex\\s+16\\s*$"),
                n("cr7", 2, "crypte de", re = "${CR}de\\s*$"),
                n("cr7", 3, "crypte de ?", fs = carnetOk("de", null)),
            )),
            "cr8" to Lecon("hist.cr8.titre", null, 1, listOf(
                n("cr8", 0, "crypte quiz", re = "${CR}quiz\\s*$", ou = "crypte"),
                n("cr8", 1, "crypte quiz ? ? ? ? ? ?", fs = carnetOk("quiz", null)),
            )),
            "cr9" to Lecon("hist.cr9.titre", null, 1, listOf(
                n("cr9", 0, "cat registre.txt", re = "$LIRE.*registre\\.txt", ou = "crypte"),
                n("cr9", 1, "echo \"Lune donne 2 plumes a Pixel\" >> registre.txt",
                    fs = { j -> lire(j, "registre.txt").lines().count { it.isNotBlank() } > lignesRegistre().size }),
                n("cr9", 2, "crypte registre", re = "${CR}registre\\s*$"),
            )),
            "cr10" to Lecon("hist.cr10.titre", null, 1, listOf(
                n("cr10", 0, "cat chaine/bloc_1.txt", re = "$LIRE.*chaine/bloc_1", ou = "crypte"),
                n("cr10", 1, "sha256sum chaine/bloc_0.txt", re = "^sha256sum\\b.*chaine/bloc_0"),
                n("cr10", 2, "sh verifie_chaine.sh", re = "${SH}verifie_chaine\\.sh\\s*$"),
                n("cr10", 3, "echo triche >> chaine/bloc_1.txt", fs = { j -> chaineCassee(j) }),
                n("cr10", 4, "sh verifie_chaine.sh", re = "${SH}verifie_chaine\\.sh\\s*$", echoue = true),
                n("cr10", 5, "cp archives/bloc_1.txt chaine/", fs = { j -> dansCarnet(j, "triche", "vu") && blocs(j).size >= 5 && !chaineCassee(j) }),
                n("cr10", 6, "crypte chaine", re = "${CR}chaine\\s*$"),
            )),
            "cr11" to Lecon("hist.cr11.titre", null, 1, listOf(
                n("cr11", 0, "sha256sum copies/*/registre.txt", re = "^sha256sum\\b.*copies/", ou = "crypte"),
                n("cr11", 1, "sha256sum copies/*/registre.txt | cut -c1-64 | sort | uniq -c", re = "^sha256sum\\b.*copies.*\\|\\s*(cut|awk)\\b.*\\|\\s*sort\\b.*\\|\\s*uniq\\s+-c"),
                n("cr11", 2, "diff copies/feu/registre.txt copies/?/registre.txt", re = "^diff\\b.*copies/.*copies/", echoue = true),
                n("cr11", 3, "crypte consensus ?", fs = carnetOk("consensus", null)),
            )),
            "cr12" to Lecon("hist.cr12.titre", null, 1, listOf(
                n("cr12", 0, "cat mineur.sh", re = "$LIRE.*mineur\\.sh", ou = "crypte"),
                n("cr12", 1, "sh mineur.sh 2", re = "${SH}mineur\\.sh\\s+2\\s*$"),
                n("cr12", 2, "crypte mine 3", re = "^(time\\s+${SH.removePrefix("^")}mineur\\.sh\\s+3|(tg\\s+)?crypte\\s+mine\\s+3)\\b"),
                n("cr12", 3, "crypte mine", re = "${CR}mine\\s*$"),
            )),
            "cr13" to Lecon("hist.cr13.titre", null, 1, listOf(
                n("cr13", 0, "echo \"Pixel donne 2 glands a Lune\" > echange.txt", fs = { j -> lire(j, "echange.txt").isNotBlank() }, ou = "crypte",
                    cree = "crypte/echange.txt"),
                n("cr13", 1, "gpg $HOMEDIR --clearsign echange.txt", fs = { j -> asc(j, "echange.txt.asc") }),
                n("cr13", 2, "gpg $HOMEDIR --verify echanges/faux.txt.asc", re = "$GPG.*--verify\\b.*faux\\.txt\\.asc", echoue = true),
                n("cr13", 3, "crypte signe echange.txt.asc", fs = carnetOk("signe", null)),
            )),
            "cr14" to Lecon("hist.cr14.titre", null, 1, listOf(
                n("cr14", 0, "crypte vitrine", re = "${CR}vitrine\\b", ou = "crypte"),
                n("cr14", 1, "grep -h donnees chaine/bloc_*.txt", re = "^(grep|cat)\\b.*chaine"),
                n("cr14", 2, "sh verifie_chaine.sh carnet_de_bord", re = "${SH}verifie_chaine\\.sh\\s+\\S*carnet_de_bord"),
                n("cr14", 3, "crypte recensement", fs = carnetOk("recensement", null), exploit = "crypte.b6"),
            )),
        )
    }

    // ---------------------------------------------------------------- l'arbre du Carrefour
    private fun besoin(): List<String> {
        val P = Programme.donnees()
        val ms = P.optJSONArray("mondes") ?: JSONArray()
        val m = (0 until ms.length()).map { ms.getJSONObject(it) }.firstOrNull { it.optString("id") == "crypte" } ?: return emptyList()
        val tronc = P.optJSONObject("tronc") ?: JSONObject()
        return liste(m, "requis").flatMap { liste(tronc, it) }.distinct()
    }

    fun ouvert(jeu: Jeu) = besoin().all { Histoire.fini(jeu, it) }
    fun manque(jeu: Jeu) = besoin().filter { !Histoire.fini(jeu, it) }.map { Histoire.nomChapitre(it) }

    fun annonce(jeu: Jeu): Boolean {
        val h = Histoire.h(jeu)
        val deja = h.optJSONArray("mondes_annonces") ?: JSONArray().also { h.put("mondes_annonces", it) }
        if ((0 until deja.length()).any { deja.getString(it) == "crypte" } || Histoire.fini(jeu, "crypte") || !ouvert(jeu)) return false
        deja.put("crypte")
        jeu.log(t("cr.ouvert.log"))
        jeu.dire(Histoire.dire(jeu, "cr.ouvert.dit"), 18)
        return true
    }

    private val SANS_HOMEDIR = Regex("(^|[;&|]\\s*)gpg2?\\s(?!.*--homedir)")

    /** Un indice de la Crypte (Histoire.indice), comme crypte.indice sur PC. */
    fun indice(jeu: Jeu, e: Etape, tapees: List<Pair<String, String?>>): String? {
        if (Histoire.leconCourante(jeu)?.id !in IDS) return null
        val lignes = tapees.map { it.first.trim() }
        if (lignes.any { SANS_HOMEDIR.containsMatchIn(it) }) return t("cr.indice.homedir")
        if (lignes.any { Regex("^sudo\\b").containsMatchIn(it) }) return t("cr.indice.sudo")
        if ("?" in e.cmd.split(" ") && lignes.filter { !it.startsWith("tr ") }.any { Regex("(^|\\s|/)\\?(\\s|/|$)|…|<").containsMatchIn(it) })
            return t("cr.indice.trou")
        for ((et, cle) in listOf("roue" to "cr.indice.roue", "de" to "cr.indice.de", "quiz" to "cr.indice.quiz", "consensus" to "cr.indice.consensus")) {
            if (e.cmd.startsWith("crypte $et ?")) {
                val der = carnet(jeu).lines().lastOrNull { it.startsWith("[$et]") }
                if (der != null && der.endsWith("(faux)")) return t(cle)
                if (lignes.lastOrNull()?.let { Regex("$CR$et\\s*$").containsMatchIn(it) } == true) return t(cle + "_aide")
            }
        }
        if (e.cmd.startsWith("openssl enc") && lignes.any { "pass:" in it && CLE !in it }) return t("cr.indice.cle")
        if (e.cmd.startsWith("cp archives") && lignes.any { Regex("${SH}verifie_chaine").containsMatchIn(it) }) return t("cr.indice.reparer")
        if (e.cmd == "echo triche >> chaine/bloc_1.txt" && lignes.any { Regex("^echo\\b.*>\\s*chaine/").containsMatchIn(it) && ">>" !in it }) return t("cr.indice.ajouter")
        if (e.cmd.startsWith("crypte donne") && lignes.any { it.startsWith("crypte donne") }) return t("cr.indice.donne")
        return null
    }

    // ---------------------------------------------------------------- les commandes du jeu : crypte …
    fun roueLignes(k0: Int): List<String> {
        val k = ((k0 % 26) + 26) % 26
        return listOf("  ${t("cr.roue.clair").padEnd(9)} ${ALPHA.toList().joinToString(" ")}",
            "  ${t("cr.roue.code").padEnd(9)} ${cesar(ALPHA, k).toList().joinToString(" ")}", "  a → ${ALPHA[k]} : +$k (mod 26)")
    }

    fun lignesRoue(jeu: Jeu, arg: String?): List<String> {
        val gr = Histoire.graine(jeu)
        val k = decalage(gr)
        val mystere = lire(jeu, "grimoire/mystere.txt").trim().ifEmpty { cesar(grimoire("cr.grimoire.mystere"), k) }
        val tete = listOf("🎡 " + t("cr.roue.titre"), "")
        if (arg == null) return tete + roueLignes(3) + listOf("", "  " + t("cr.roue.aide"))
        val n = arg.toIntOrNull()?.let { ((it % 26) + 26) % 26 } ?: return listOf(t("cr.roue.aide"))
        val out = tete + roueLignes(n) + listOf("", "  " + cesar(mystere, -n).take(160))
        return if (n == k) { noter(jeu, "roue", "$n (ok)"); out + listOf("", "  ✔ " + t("cr.roue.ok", "n" to n)) }
        else { noter(jeu, "roue", "$n (faux)"); out + listOf("", "  ✖ " + t("cr.roue.faux")) }
    }

    fun lignesDemasque(jeu: Jeu): List<String> {
        val out = mutableListOf("🎭 " + t("cr.demasque.titre"), "")
        for (x in objets(donnees(), "messages")) {
            val n = x.optInt("n"); val code = x.optString("code")
            val b = lire(jeu, "messages/message_$n.txt").trim()
            val clair = try {
                when (code) {
                    "base64" -> String(java.util.Base64.getDecoder().decode(b), Charsets.UTF_8)
                    "hex" -> String(b.chunked(2).map { it.toInt(16).toByte() }.toByteArray(), Charsets.UTF_8)
                    else -> cesar(b, 13)
                }
            } catch (e: Exception) { "?" }
            out.add("  $n. ${code.padEnd(7)} ${b.take(28)}${if (b.length > 28) "…" else ""}")
            out.add("     → $clair")
        }
        noter(jeu, "demasque", "5 (ok)")
        return out + listOf("", "  " + t("cr.demasque.morale"))
    }

    fun lignesAvalanche(jeu: Jeu, a: String, b: String): List<String> {
        val ha = sha(a); val hb = sha(b)
        noter(jeu, "avalanche", "$a $b (ok)")
        return listOf("🏔 " + t("cr.avalanche.titre"), "", "  ${a.padEnd(10)} $ha", "  ${b.padEnd(10)} $hb",
            "  ${"".padEnd(10)} " + ha.zip(hb).joinToString("") { if (it.first != it.second) "^" else " " }, "",
            "  " + t("cr.avalanche.compte", "lettres" to lettresDifferentes(ha, hb), "bits" to bitsDifferents(ha, hb)), "  " + t("cr.avalanche.morale"))
    }

    fun lignesDonne(jeu: Jeu, nom: String?, ici: File): List<String> {
        if (nom == null) return listOf(t("cr.donne.aide"))
        val f = File(ici, nom).let { if (it.isFile) it else File(dossier(jeu), nom) }
        if (!f.isFile || !dans(jeu, f)) return listOf(t("cr.inconnu", "nom" to nom))
        val b = f.readBytes()
        if (b.size >= 8 && String(b, 0, 8, Charsets.US_ASCII) == "Salted__") {
            val r = try { Citadelle.chiffrer(b, CLE, true) } catch (e: Exception) { null }
            if (r == null) { noter(jeu, "donne", "${f.name} (faux)"); return listOf("✖ " + t("cr.donne.ferme")) }
            noter(jeu, "donne", "${f.name} (ok)")
            return listOf("🔓 " + t("cr.donne.ouvert"), "  " + String(r, Charsets.UTF_8).trim(), "", "  " + t("cr.donne.probleme"))
        }
        if (b.isNotEmpty() && b[0].toInt() and 0x80 != 0 || String(b, Charsets.UTF_8).startsWith("-----BEGIN PGP MESSAGE")) {
            preparerCreature(jeu)
            val clair = try { CryptePgp.dechiffrer(b, CryptePgp.Trousseau(trousseau(jeu, true))) } catch (e: Exception) { null }
            if (clair == null) { noter(jeu, "donne", "${f.name} (faux)"); return listOf("✖ " + t("cr.donne.pas_pour_moi")) }
            noter(jeu, "donne", "${f.name} (ok)")
            return listOf("🔓 " + t("cr.donne.gpg"), "  " + String(clair, Charsets.UTF_8).trim(), "", "  " + t("cr.donne.privee"))
        }
        return listOf(t("cr.donne.clair"))
    }

    fun lignesPeintures(): List<String> {
        val p = peintures()
        return listOf("🎨 " + t("cr.peintures.titre"), "", "  " + t("cr.peintures.public", "p" to p["p"], "g" to p["g"]),
            "  " + t("cr.peintures.moi", "a" to p["a"], "g" to p["g"], "p" to p["p"], "A" to p["A"]),
            "  " + t("cr.peintures.elle", "b" to p["b"], "g" to p["g"], "p" to p["p"], "B" to p["B"]),
            "  " + t("cr.peintures.melange", "s" to p["s1"], "A" to p["A"], "B" to p["B"], "a" to p["a"], "b" to p["b"], "p" to p["p"]),
            "", "  " + t("cr.peintures.morale"), "  " + t("cr.peintures.grands"))
    }

    fun lignesDe(jeu: Jeu, arg: String?): List<String> {
        val d = donnees().optJSONObject("de") ?: JSONObject()
        val suite = deSuite(Histoire.graine(jeu), d.optInt("montres", 5) + 1)
        val out = listOf("🎲 " + t("cr.de.titre"), "", "  " + suite.dropLast(1).joinToString("  ") + "  ?", "",
            "  " + t("cr.de.regle", "a" to d.optInt("a"), "c" to d.optInt("c"), "m" to d.optInt("m")))
        val n = arg?.toIntOrNull() ?: return out + listOf("  " + t("cr.de.aide"))
        return if (n == suite.last()) { noter(jeu, "de", "$n (ok)"); out + listOf("", "  ✔ " + t("cr.de.ok")) }
        else { noter(jeu, "de", "$n (faux)"); out + listOf("", "  ✖ " + t("cr.de.faux")) }
    }

    fun lignesQuiz(jeu: Jeu, rep: List<String>): List<String> {
        val q = quiz(Histoire.graine(jeu))
        if (rep.isEmpty()) return listOf("🔮 " + t("cr.quiz.titre"), "") + q.map { "  ${it.first}. " + t("cr.quiz.${it.second}") } + listOf("", "  " + t("cr.quiz.aide"))
        val r = rep.map { it.lowercase().take(1) }
        val bonnes = q.map { it.third }
        if (r.size != bonnes.size || r.any { it !in listOf("v", "f", "s") }) return listOf(t("cr.quiz.aide"))
        val justes = r.zip(bonnes).count { it.first == it.second }
        val out = mutableListOf<String>()
        if (justes == bonnes.size) { noter(jeu, "quiz", r.joinToString(" ") + " (ok)"); out.add("✔ " + t("cr.quiz.ok")) }
        else { noter(jeu, "quiz", r.joinToString(" ") + " (faux)"); out.add("✖ " + t("cr.quiz.faux", "n" to justes, "total" to bonnes.size)) }
        for ((x, rr) in q.zip(r)) if (rr == x.third) out.add("  ✔ ${x.first}. " + t("cr.quiz.${x.second}.pourquoi"))
        return out
    }

    fun lignesRegistre(jeu: Jeu): List<String> {
        val actuel = lire(jeu, "registre.txt").lines().filter { it.isNotBlank() }
        val origine = lignesRegistre()
        val out = mutableListOf("📜 " + t("cr.registre.titre"), "")
        actuel.forEachIndexed { i, l -> out.add("  ${if (i < origine.size && l != origine[i]) "≠" else " "} ${i + 1}. $l") }
        noter(jeu, "registre", "lu (ok)")
        return out + listOf("", "  " + t("cr.registre.morale"))
    }

    fun dessinChaine(etats: List<Pair<Int, String>>) = "  [0]" + etats.joinToString("") { (k, e) ->
        (when (e) { "ok" -> "━━"; "casse" -> "━✖━"; else -> "┄?┄" }) + "[${k + 1}]" }

    fun lignesChaine(jeu: Jeu, rel: String = "chaine"): List<String> {
        val b = blocs(jeu, rel)
        if (b.size < 2) return listOf(t("cr.chaine.vide", "dossier" to rel))
        val etats = verifierChaine(b)
        val out = mutableListOf("⛓ " + t("cr.chaine.titre"), "", dessinChaine(etats), "")
        for ((k, e) in etats) out.add("  ${t("cr.verifie.maillon")} $k → ${k + 1} : " + t("cr.chaine.$e"))
        if (etats.all { it.second == "ok" }) {
            noter(jeu, "chaine", "$rel intacte (ok)")
            out += listOf("", "  ✔ " + t("cr.chaine.intacte"))
            if (rel == "chaine" && Histoire.leconCourante(jeu)?.id == "cr10" && dansCarnet(jeu, "triche", "vu")) {
                if ("indice:cr10" in faits(jeu) || !jeu.indiceLecon.isNullOrEmpty()) out.add("  " + t("cr.chaine.avec_indice"))
                else Recompenses.exploit(jeu, "crypte.chaine")?.let { jeu.log(it); jeu.dire(it, 16); out.add("  ✨ $it") }
            }
        } else {
            noter(jeu, "chaine", "$rel brisee (brisee)")
            out += listOf("", "  ✖ " + t("cr.chaine.brisee"))
        }
        return out
    }

    fun lignesConsensus(jeu: Jeu, arg: String?): List<String> {
        val b = arg?.lowercase() ?: return listOf(t("cr.consensus.aide"))
        if (b !in liste(donnees(), "biomes")) return listOf(t("cr.consensus.inconnu", "liste" to liste(donnees(), "biomes").joinToString(", ")))
        return if (b == tricheur(Histoire.graine(jeu))) {
            noter(jeu, "consensus", "$b (ok)")
            listOf("✔ " + t("cr.consensus.ok", "biome" to b), "  " + t("cr.consensus.morale"))
        } else { noter(jeu, "consensus", "$b (faux)"); listOf("✖ " + t("cr.consensus.faux", "biome" to b)) }
    }

    fun lignesMine(jeu: Jeu, arg: String?): List<String> {
        val m = donnees().optJSONObject("mine") ?: JSONObject()
        val out = mutableListOf("⛏ " + t("cr.mine.titre"), "", "  " + t("cr.mine.entete"))
        val zs = arg?.toIntOrNull()?.takeIf { it in 1..4 }?.let { listOf(it) } ?: (1..m.optInt("table", 5)).toList()
        for (z in zs) {
            val essais = "%9d".format(Math.pow(16.0, z.toDouble()).toLong())
            if (z <= 4) {
                val t0 = System.nanoTime()
                val n = miner(m.optString("donnees"), z)
                val ms = (System.nanoTime() - t0) / 1_000_000
                out.add("  ${"0".repeat(z).padEnd(6)} $essais   ${(n?.toString() ?: "—").padStart(8)}   ${ms.toString().padStart(7)} ms")
                if (arg != null && n != null) out.add("  nonce = $n")
            } else out.add("  ${"0".repeat(z).padEnd(6)} $essais   ${"…".padStart(8)}   " + t("cr.mine.trop_long"))
        }
        noter(jeu, "mine", "table (ok)")
        return out + listOf("", "  " + t("cr.mine.morale"), "  " + t("cr.mine.energie"))
    }

    fun lignesSigne(jeu: Jeu, nom: String?, ici: File): List<String> {
        val f = File(ici, nom ?: "echange.txt.asc").let { if (it.isFile) it else File(dossier(jeu), nom ?: "echange.txt.asc") }
        if (!f.isFile || !dans(jeu, f)) return listOf(t("cr.inconnu", "nom" to (nom ?: "echange.txt.asc")))
        val v = CryptePgp.verifierEnClair(f.readText(), CryptePgp.Trousseau(trousseau(jeu)))
        if (v == null || !v.first) { noter(jeu, "signe", "${f.name} (refuse)"); return listOf("✖ " + t("cr.signe.refuse")) }
        val uid = v.second
        if (MOI !in uid) { noter(jeu, "signe", "${f.name} (pas_moi)"); return listOf("✖ " + t("cr.signe.pas_moi", "uid" to uid)) }
        val ligne = f.readText().lines().firstOrNull { it.isNotBlank() && !it.startsWith("-----") && !it.startsWith("Hash:") } ?: "?"
        val b = blocs(jeu)
        if (b.isNotEmpty() && !chaineCassee(jeu))
            ecrire(jeu, "chaine/bloc_${b.size}.txt", blocTexte(b.size, sha(b.last()), "$ligne [${t("cr.signe.par", "uid" to uid)}]"))
        noter(jeu, "signe", "${f.name} (ok)")
        return listOf("✔ " + t("cr.signe.ok", "uid" to uid), "  " + t("cr.signe.ajoute", "ligne" to ligne))
    }

    fun lignesVitrine(jeu: Jeu): List<String> {
        val out = mutableListOf("🏛 " + t("cr.vitrine.titre"), "", "  " + t("cr.vitrine.regle"), "")
        for (v in liste(donnees(), "vitrine")) out += listOf("  " + t("cr.vitrine.$v"), "     " + t("cr.vitrine.$v.comment"), "     🧱 " + t("cr.vitrine.$v.briques"))
        noter(jeu, "vitrine", "lue (ok)")
        return out + listOf("", "  " + t("cr.vitrine.anonyme"), "  " + t("cr.vitrine.privee"))
    }

    fun lignesRecensement(jeu: Jeu): List<String> {
        val b = blocs(jeu, "carnet_de_bord")
        if (b.size < 2) return listOf(t("cr.chaine.vide", "dossier" to "carnet_de_bord"))
        val etats = verifierChaine(b)
        val out = listOf("📖 " + t("cr.recensement.titre"), "", dessinChaine(etats), "")
        return if (etats.all { it.second == "ok" }) {
            noter(jeu, "recensement", "${b.size} (ok)")
            out + listOf("  ✔ " + t("cr.recensement.ok", "n" to b.size), "  " + t("cr.recensement.morale"))
        } else { noter(jeu, "recensement", "brise (brise)"); out + listOf("  ✖ " + t("cr.recensement.brise")) }
    }

    /** L'entrée de la Crypte en caractères : le REPLI de l'illustration B12 (même dessin que crypte.CRYPTE sur PC ;
     *  le dessin graphique est CrypteDessin.crypte). */
    val CRYPTE_DESSIN = listOf("        ╔═══════════╗", "   🗝   ║ ▓▓  ◈  ▓▓ ║   🗝", "  ▄▄▄▄▄▄╣  ╔═════╗  ╠▄▄▄▄▄▄", "  █▒▒▒▒█║  ║ ▒▒▒ ║  ║█▒▒▒▒█",
        "  █ 📜 █║  ║ ⛓ ║  ║█ 🔒 █", "  ▀▀▀▀▀▀╩══╩═════╩══╩▀▀▀▀▀▀", "   ❄    ░░░ ▒▒▒ ░░░    ❄")

    private fun dans(jeu: Jeu, f: File) = f.canonicalPath.startsWith(jeu.terrain.canonicalPath + "/")

    /** crypte [regle|demasque|roue|avalanche|donne|peintures|de|quiz|registre|chaine|consensus|mine|signe|vitrine|recensement] */
    fun commande(jeu: Jeu, reste: String, ici: File): String {
        val m = reste.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
        val sous = (m.getOrNull(0) ?: "aide").lowercase().replace('î', 'i').replace('é', 'e')
        val a = m.drop(1).filter { it != "?" && it != "…" }
        val l = when (sous) {
            "regle" -> CRYPTE_DESSIN + t("cr.meuble.regle", "nom" to jeu.nom).split("\n")
            "demasque" -> lignesDemasque(jeu)
            "roue" -> lignesRoue(jeu, a.getOrNull(0))
            "avalanche" -> if (a.size >= 2) lignesAvalanche(jeu, a[0], a[1]) else listOf(t("cr.avalanche.aide"))
            "donne" -> lignesDonne(jeu, a.getOrNull(0), ici)
            "peintures", "peinture" -> lignesPeintures()
            "de" -> lignesDe(jeu, a.getOrNull(0))
            "quiz" -> lignesQuiz(jeu, a)
            "registre" -> lignesRegistre(jeu)
            "chaine" -> lignesChaine(jeu, a.getOrNull(0)?.trimEnd('/') ?: "chaine")
            "consensus" -> lignesConsensus(jeu, a.getOrNull(0))
            "mine" -> lignesMine(jeu, a.getOrNull(0))
            "signe" -> lignesSigne(jeu, a.getOrNull(0), ici)
            "vitrine" -> lignesVitrine(jeu)
            "recensement" -> lignesRecensement(jeu)
            "stop" -> listOf(t("cr.stop"))
            else -> CRYPTE_DESSIN + listOf("🗝 " + t("cr.aide.titre")) + t("cr.aide.liste").split("\n").map { "  $it" }
        }
        return l.joinToString("\n")
    }

    // ---------------------------------------------------------------- les commandes intégrées (téléphone)
    /** openssl passwd -6 [-salt S] MOT · openssl rand -hex N ; null : autre chose (openssl enc, la Citadelle). */
    fun openssl(ligne: String): String? {
        val m = ligne.trim().split(Regex("\\s+"))
        when (m.getOrNull(1)) {
            "passwd" -> {
                if ("-6" !in m) return t("cr.tel.openssl.usage")
                var sel: String? = null; var mot: String? = null
                var i = 2
                while (i < m.size) { when (m[i]) { "-6" -> {}; "-salt" -> { sel = m.getOrNull(i + 1); i++ }; else -> mot = m[i].trim('\'', '"') }; i++ }
                if (mot == null) return t("cr.tel.openssl.usage")
                val s = sel ?: SecureRandom().let { r -> (1..16).map { "./0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"[r.nextInt(64)] }.joinToString("") }
                return sha512crypt(mot, s)
            }
            "rand" -> {
                val n = m.lastOrNull()?.toIntOrNull()?.coerceIn(1, 1024) ?: return t("cr.tel.openssl.usage")
                if ("-hex" !in m) return t("cr.tel.openssl.usage")
                return ByteArray(n).also { SecureRandom().nextBytes(it) }.let { hex(it) }
            }
        }
        return null
    }

    /** gpg --homedir DOSSIER … : l'OpenPGP intégré (CryptePgp), seulement dans le terrain. */
    fun gpg(jeu: Jeu, ligne: String, ici: File): String = CryptePgp.commande(ligne, ici, jeu.terrain)
}
