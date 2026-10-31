package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.math.BigInteger
import java.security.KeyFactory
import java.security.KeyPairGenerator
import java.security.MessageDigest
import java.security.PrivateKey
import java.security.PublicKey
import java.security.SecureRandom
import java.security.Signature
import java.security.spec.PKCS8EncodedKeySpec
import java.security.spec.RSAPublicKeySpec
import javax.crypto.Cipher
import javax.crypto.spec.IvParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * Le `gpg` intégré de la Crypte des Codes (le téléphone n'a pas gpg) : un OpenPGP RÉDUIT mais réel (RFC 9580 / 4880),
 * compatible avec le vrai GnuPG (tests/jvm/Crypte.kt : gpg vérifie et déchiffre ce que le téléphone produit, et le
 * téléphone vérifie et déchiffre ce que gpg produit avec une clé RSA) :
 *  - clés RSA 2048 (paquet de clé publique v4, identité, autosignature 0x13 ; sous-clé de chiffrement lue à l'import) ;
 *  - signatures en texte clair (--clearsign / --verify, type 0x01, SHA-256 ; SHA-384/512 lus aussi) ;
 *  - chiffrement pour une clé publique (-e -r) : PKESK v3 RSA + SEIPD v1 (AES-256 CFB, MDC) ; déchiffrement (-d),
 *    paquets compressés (ZIP, ZLIB) et longueurs partielles compris.
 * Le trousseau est un fichier JSON (cles.json) dans le dossier --homedir, qui doit être dans le terrain : jamais le
 * trousseau de l'utilisateur. Toutes les clés de la Crypte sont des EXEMPLES.
 */
object CryptePgp {
    class Cle(val uid: String, val cree: Long, val n: BigInteger, val e: BigInteger, val prive: String? = null,
              val sn: BigInteger? = null, val se: BigInteger? = null, val scree: Long = 0, val sprive: String? = null) {
        val corps: ByteArray get() = corpsPublic(cree, n, e)
        val empreinte: ByteArray get() = empreinte(corps)
        val id: ByteArray get() = empreinte.copyOfRange(12, 20)
        val sousId: ByteArray? get() = if (sn != null && se != null) empreinte(corpsPublic(scree, sn, se)).copyOfRange(12, 20) else null
        fun publique(): PublicKey = KeyFactory.getInstance("RSA").generatePublic(RSAPublicKeySpec(n, e))
        fun privee(): PrivateKey? = prive?.let { KeyFactory.getInstance("RSA").generatePrivate(PKCS8EncodedKeySpec(java.util.Base64.getDecoder().decode(it))) }
        fun json(): JSONObject = JSONObject().put("uid", uid).put("cree", cree).put("n", n.toString(16)).put("e", e.toString(16)).also { o ->
            prive?.let { o.put("prive", it) }
            if (sn != null && se != null) { o.put("sn", sn.toString(16)).put("se", se.toString(16)).put("scree", scree); sprive?.let { o.put("sprive", it) } }
        }
        companion object {
            fun de(o: JSONObject) = Cle(o.optString("uid"), o.optLong("cree"), BigInteger(o.optString("n"), 16), BigInteger(o.optString("e"), 16),
                o.optString("prive").ifEmpty { null }, o.optString("sn").ifEmpty { null }?.let { BigInteger(it, 16) },
                o.optString("se").ifEmpty { null }?.let { BigInteger(it, 16) }, o.optLong("scree"), o.optString("sprive").ifEmpty { null })
        }
    }

    /** Un trousseau du terrain : dossier/cles.json. */
    class Trousseau(val dossier: File) {
        private val f = File(dossier, "cles.json")
        fun cles(): List<Cle> = try { JSONArray(f.readText()).let { a -> (0 until a.length()).map { Cle.de(a.getJSONObject(it)) } } } catch (e: Exception) { emptyList() }
        private fun garder(l: List<Cle>) { dossier.mkdirs(); f.writeText(JSONArray().also { a -> l.forEach { a.put(it.json()) } }.toString(1)) }
        fun publique(qui: String) = cles().firstOrNull { qui in it.uid || hexa(it.id).equals(qui, true) || hexa(it.empreinte).equals(qui, true) }
        fun secrete(qui: String) = cles().firstOrNull { it.prive != null && (qui in it.uid || hexa(it.id).equals(qui, true)) }
        fun parId(id: ByteArray) = cles().firstOrNull { it.id.contentEquals(id) || it.sousId?.contentEquals(id) == true }
        fun importer(c: Cle) { garder(cles().filter { !it.empreinte.contentEquals(c.empreinte) } + Cle(c.uid, c.cree, c.n, c.e, null, c.sn, c.se, c.scree)) }
        fun ajouter(c: Cle) { garder(cles().filter { !it.empreinte.contentEquals(c.empreinte) } + c) }
        fun generer(uid: String): Cle {
            val g = KeyPairGenerator.getInstance("RSA"); g.initialize(2048, SecureRandom())
            val p = g.generateKeyPair()
            val pub = p.public as java.security.interfaces.RSAPublicKey
            val c = Cle(uid, System.currentTimeMillis() / 1000, pub.modulus, pub.publicExponent, java.util.Base64.getEncoder().encodeToString(p.private.encoded))
            ajouter(c)
            return c
        }
    }

    // ---------------------------------------------------------------- briques : MPI, paquets, empreintes, armure
    fun hexa(b: ByteArray) = b.joinToString("") { "%02X".format(it) }
    private fun u(b: Byte) = b.toInt() and 255
    private fun be(v: Long, n: Int) = ByteArray(n) { ((v shr (8 * (n - 1 - it))) and 255).toByte() }

    fun mpi(x: BigInteger): ByteArray {
        var m = x.toByteArray()
        if (m.size > 1 && m[0].toInt() == 0) m = m.copyOfRange(1, m.size)
        return be(x.bitLength().toLong(), 2) + m
    }

    fun corpsPublic(cree: Long, n: BigInteger, e: BigInteger) = byteArrayOf(4) + be(cree, 4) + byteArrayOf(1) + mpi(n) + mpi(e)
    fun empreinte(corps: ByteArray): ByteArray = MessageDigest.getInstance("SHA-1").digest(byteArrayOf(0x99.toByte()) + be(corps.size.toLong(), 2) + corps)

    fun paquet(tag: Int, corps: ByteArray): ByteArray {
        val l = corps.size
        val tete = when {
            l < 192 -> byteArrayOf(l.toByte())
            l < 8384 -> byteArrayOf((((l - 192) shr 8) + 192).toByte(), ((l - 192) and 255).toByte())
            else -> byteArrayOf(0xFF.toByte()) + be(l.toLong(), 4)
        }
        return byteArrayOf((0xC0 or tag).toByte()) + tete + corps
    }

    /** Les paquets (étiquette, corps) : format ancien et nouveau, longueurs partielles comprises. */
    fun paquets(b: ByteArray): List<Pair<Int, ByteArray>> {
        val out = mutableListOf<Pair<Int, ByteArray>>()
        var i = 0
        while (i < b.size) {
            val o = u(b[i]); i++
            require(o and 0x80 != 0) { "pas un paquet OpenPGP" }
            if (o and 0x40 != 0) {
                val tag = o and 0x3F
                val corps = ByteArrayOutputStream()
                while (true) {
                    val l1 = u(b[i]); i++
                    when {
                        l1 < 192 -> { corps.write(b, i, l1); i += l1; break }
                        l1 < 224 -> { val l = ((l1 - 192) shl 8) + u(b[i]) + 192; i++; corps.write(b, i, l); i += l; break }
                        l1 == 255 -> { val l = ((u(b[i]) shl 24) or (u(b[i + 1]) shl 16) or (u(b[i + 2]) shl 8) or u(b[i + 3])); i += 4; corps.write(b, i, l); i += l; break }
                        else -> { val l = 1 shl (l1 and 0x1F); corps.write(b, i, l); i += l }
                    }
                }
                out.add(tag to corps.toByteArray())
            } else {
                val tag = (o shr 2) and 0x0F
                val l = when (o and 3) {
                    0 -> u(b[i]).also { i += 1 }
                    1 -> ((u(b[i]) shl 8) or u(b[i + 1])).also { i += 2 }
                    2 -> ((u(b[i]) shl 24) or (u(b[i + 1]) shl 16) or (u(b[i + 2]) shl 8) or u(b[i + 3])).also { i += 4 }
                    else -> b.size - i
                }
                out.add(tag to b.copyOfRange(i, i + l)); i += l
            }
        }
        return out
    }

    fun crc24(b: ByteArray): Int {
        var crc = 0xB704CE
        for (x in b) {
            crc = crc xor (u(x) shl 16)
            repeat(8) { crc = crc shl 1; if (crc and 0x1000000 != 0) crc = crc xor 0x1864CFB }
        }
        return crc and 0xFFFFFF
    }

    fun armure(genre: String, b: ByteArray): String {
        val b64 = java.util.Base64.getEncoder().encodeToString(b).chunked(64).joinToString("\n")
        val c = java.util.Base64.getEncoder().encodeToString(be(crc24(b).toLong(), 3))
        return "-----BEGIN PGP $genre-----\n\n$b64\n=$c\n-----END PGP $genre-----\n"
    }

    fun desarmer(s: String): ByteArray {
        val l = s.replace("\r", "").lines()
        val debut = l.indexOfFirst { it.startsWith("-----BEGIN PGP ") }
        require(debut >= 0) { "pas d'armure" }
        var i = debut + 1
        while (i < l.size && l[i].isNotBlank()) i++
        val corps = StringBuilder()
        i++
        while (i < l.size && !l[i].startsWith("-----END") && !l[i].startsWith("=")) { corps.append(l[i].trim()); i++ }
        return java.util.Base64.getDecoder().decode(corps.toString())
    }

    private fun sous(type: Int, data: ByteArray) = byteArrayOf((data.size + 1).toByte(), type.toByte()) + data

    private fun algoHash(h: Int) = when (h) { 8 -> "SHA256"; 9 -> "SHA384"; 10 -> "SHA512"; 11 -> "SHA224"; 2 -> "SHA1"; else -> null }

    /** Une signature v4 RSA sur `donnees` (déjà préparées selon le type) ; renvoie le corps du paquet 2. */
    fun signature(type: Int, donnees: ByteArray, k: Cle, maintenant: Long = System.currentTimeMillis() / 1000, extra: ByteArray = ByteArray(0)): ByteArray {
        val hach = sous(2, be(maintenant, 4)) + sous(33, byteArrayOf(4) + k.empreinte) + extra
        val tete = byteArrayOf(4, type.toByte(), 1, 8) + be(hach.size.toLong(), 2) + hach
        val entree = donnees + tete + byteArrayOf(4, 0xFF.toByte()) + be(tete.size.toLong(), 4)
        val s = Signature.getInstance("SHA256withRSA"); s.initSign(k.privee()); s.update(entree)
        val sig = s.sign()
        val gauche = MessageDigest.getInstance("SHA-256").digest(entree).copyOf(2)
        val nonHach = sous(16, k.id)
        return tete + be(nonHach.size.toLong(), 2) + nonHach + gauche + mpi(BigInteger(1, sig))
    }

    /** La clé publique armée (clé, identité, autosignature), comme gpg --armor --export. */
    fun exporter(k: Cle): String {
        val uid = k.uid.toByteArray(Charsets.UTF_8)
        val donnees = byteArrayOf(0x99.toByte()) + be(k.corps.size.toLong(), 2) + k.corps + byteArrayOf(0xB4.toByte()) + be(uid.size.toLong(), 4) + uid
        val extra = sous(27, byteArrayOf(0x0F)) + sous(11, byteArrayOf(9, 7)) + sous(21, byteArrayOf(8, 10)) + sous(22, byteArrayOf(0)) + sous(30, byteArrayOf(1))
        val s = signature(0x13, donnees, k, k.cree, extra)
        return armure("PUBLIC KEY BLOCK", paquet(6, k.corps) + paquet(13, uid) + paquet(2, s))
    }

    private fun lireMpi(b: ByteArray, i0: Int): Pair<BigInteger, Int> {
        val bits = (u(b[i0]) shl 8) or u(b[i0 + 1])
        val n = (bits + 7) / 8
        return BigInteger(1, b.copyOfRange(i0 + 2, i0 + 2 + n)) to i0 + 2 + n
    }

    /** Une clé publique armée (ou binaire) : la clé RSA principale, son identité, sa sous-clé RSA de chiffrement. */
    fun importer(s: ByteArray): Cle {
        val b = if (String(s, Charsets.UTF_8).contains("-----BEGIN PGP")) desarmer(String(s, Charsets.UTF_8)) else s
        var principale: Triple<Long, BigInteger, BigInteger>? = null
        var sousCle: Triple<Long, BigInteger, BigInteger>? = null
        var uid = ""
        for ((tag, c) in paquets(b)) {
            if ((tag == 6 || tag == 14) && u(c[0]) == 4 && u(c[5]) in listOf(1, 2, 3)) {
                val cree = ((u(c[1]).toLong() shl 24) or (u(c[2]).toLong() shl 16) or (u(c[3]).toLong() shl 8) or u(c[4]).toLong())
                val (n, i1) = lireMpi(c, 6); val (e, _) = lireMpi(c, i1)
                if (tag == 6) principale = Triple(cree, n, e) else if (sousCle == null) sousCle = Triple(cree, n, e)
            }
            if (tag == 13 && uid.isEmpty()) uid = String(c, Charsets.UTF_8)
        }
        val p = principale ?: throw IllegalArgumentException("pas de clé RSA")
        return Cle(uid, p.first, p.second, p.third, null, sousCle?.second, sousCle?.third, sousCle?.first ?: 0)
    }

    // ---------------------------------------------------------------- signatures en texte clair
    private fun canonique(texte: String) = texte.replace("\r\n", "\n").removeSuffix("\n").split("\n").joinToString("\r\n") { it.trimEnd(' ', '\t') }

    fun signerEnClair(texte: String, k: Cle): String {
        val corps = texte.replace("\r\n", "\n").removeSuffix("\n")
        val s = signature(0x01, canonique(corps).toByteArray(Charsets.UTF_8), k)
        val echappe = corps.split("\n").joinToString("\n") { if (it.startsWith("-")) "- $it" else it }
        return "-----BEGIN PGP SIGNED MESSAGE-----\nHash: SHA256\n\n$echappe\n" + armure("SIGNATURE", paquet(2, s))
    }

    /** (bonne ?, identité) d'un message signé en clair, ou null (pas de clé pour vérifier, format inconnu). */
    fun verifierEnClair(s: String, t: Trousseau): Pair<Boolean, String>? {
        val l = s.replace("\r", "").lines()
        val d = l.indexOfFirst { it == "-----BEGIN PGP SIGNED MESSAGE-----" }
        if (d < 0) return null
        var i = d + 1
        while (i < l.size && l[i].isNotEmpty()) i++
        i++
        val corps = mutableListOf<String>()
        while (i < l.size && l[i] != "-----BEGIN PGP SIGNATURE-----") { corps.add(if (l[i].startsWith("- ")) l[i].substring(2) else l[i]); i++ }
        val sig = paquets(desarmer(l.drop(i).joinToString("\n"))).firstOrNull { it.first == 2 }?.second ?: return null
        if (u(sig[0]) != 4 || u(sig[2]) != 1) return null
        val type = u(sig[1]); val h = algoHash(u(sig[3])) ?: return null
        val lh = (u(sig[4]) shl 8) or u(sig[5])
        val tete = sig.copyOfRange(0, 6 + lh)
        val lnh = (u(sig[6 + lh]) shl 8) or u(sig[7 + lh])
        val nonHach = sig.copyOfRange(8 + lh, 8 + lh + lnh)
        val (m, _) = lireMpi(sig, 10 + lh + lnh)
        val id = idEmetteur(tete.copyOfRange(6, tete.size)) ?: idEmetteur(nonHach) ?: return null
        val k = t.parId(id) ?: return null
        val donnees = if (type == 0x01) canonique(corps.joinToString("\n")).toByteArray(Charsets.UTF_8) else corps.joinToString("\n").toByteArray(Charsets.UTF_8)
        val v = Signature.getInstance("${h}withRSA"); v.initVerify(k.publique())
        v.update(donnees + tete + byteArrayOf(4, 0xFF.toByte()) + be(tete.size.toLong(), 4))
        val octets = m.toByteArray().let { if (it.size > 1 && it[0].toInt() == 0) it.copyOfRange(1, it.size) else it }
        val taille = (k.n.bitLength() + 7) / 8
        val ok = try { v.verify(ByteArray(maxOf(0, taille - octets.size)) + octets) } catch (e: Exception) { false }
        return ok to k.uid
    }

    private fun idEmetteur(zone: ByteArray): ByteArray? {
        var i = 0
        while (i < zone.size) {
            val l1 = u(zone[i])
            val (l, j) = when { l1 < 192 -> l1 to i + 1; l1 < 255 -> (((l1 - 192) shl 8) + u(zone[i + 1]) + 192) to i + 2
                else -> ((u(zone[i + 1]) shl 24) or (u(zone[i + 2]) shl 16) or (u(zone[i + 3]) shl 8) or u(zone[i + 4])) to i + 5 }
            val type = u(zone[j]) and 0x7F
            if (type == 16) return zone.copyOfRange(j + 1, j + 9)
            if (type == 33) return zone.copyOfRange(j + 1 + 1 + 12, j + 1 + 21)
            i = j + l
        }
        return null
    }

    // ---------------------------------------------------------------- chiffrement pour une clé publique
    fun chiffrer(clair: ByteArray, nom: String, k: Cle, maintenant: Long = System.currentTimeMillis() / 1000): ByteArray {
        val r = SecureRandom()
        val cs = ByteArray(32).also { r.nextBytes(it) }
        val somme = cs.fold(0) { a, x -> (a + u(x)) and 0xFFFF }
        val m = byteArrayOf(9) + cs + be(somme.toLong(), 2)
        val (n, e, id) = if (k.sn != null && k.se != null) Triple(k.sn, k.se, k.sousId!!) else Triple(k.n, k.e, k.id)
        val rsa = Cipher.getInstance("RSA/ECB/PKCS1Padding"); rsa.init(Cipher.ENCRYPT_MODE, KeyFactory.getInstance("RSA").generatePublic(RSAPublicKeySpec(n, e)))
        val pkesk = byteArrayOf(3) + id + byteArrayOf(1) + mpi(BigInteger(1, rsa.doFinal(m)))
        val nomB = nom.toByteArray(Charsets.UTF_8).let { it.copyOf(minOf(it.size, 255)) }
        val litteral = paquet(11, byteArrayOf('b'.code.toByte(), nomB.size.toByte()) + nomB + be(maintenant, 4) + clair)
        val prefixe = ByteArray(16).also { r.nextBytes(it) }
        val avant = prefixe + prefixe.copyOfRange(14, 16) + litteral + byteArrayOf(0xD3.toByte(), 0x14)
        val mdc = MessageDigest.getInstance("SHA-1").digest(avant)
        val aes = Cipher.getInstance("AES/CFB/NoPadding"); aes.init(Cipher.ENCRYPT_MODE, SecretKeySpec(cs, "AES"), IvParameterSpec(ByteArray(16)))
        return paquet(1, pkesk) + paquet(18, byteArrayOf(1) + aes.doFinal(avant + mdc))
    }

    /** Le texte clair d'un message (binaire ou armé) pour une clé secrète du trousseau ; null si aucune clé ne va. */
    fun dechiffrer(b0: ByteArray, t: Trousseau): ByteArray? {
        val b = if (String(b0, Charsets.ISO_8859_1).contains("-----BEGIN PGP MESSAGE")) desarmer(String(b0, Charsets.UTF_8)) else b0
        val ps = paquets(b)
        var cleSession: ByteArray? = null
        var algo = 9
        for ((tag, c) in ps.filter { it.first == 1 }) {
            if (u(c[0]) != 3 || u(c[9]) !in listOf(1, 2)) continue
            val k = t.parId(c.copyOfRange(1, 9)) ?: continue
            val sousCle = k.sousId?.contentEquals(c.copyOfRange(1, 9)) == true
            val priv = (if (sousCle) k.sprive else k.prive) ?: continue
            val pk = KeyFactory.getInstance("RSA").generatePrivate(PKCS8EncodedKeySpec(java.util.Base64.getDecoder().decode(priv)))
            val (m, _) = lireMpi(c, 10)
            val rsa = Cipher.getInstance("RSA/ECB/PKCS1Padding"); rsa.init(Cipher.DECRYPT_MODE, pk)
            val taille = ((if (sousCle) k.sn!! else k.n).bitLength() + 7) / 8
            val octets = m.toByteArray().let { if (it.size > 1 && it[0].toInt() == 0) it.copyOfRange(1, it.size) else it }
            val d = try { rsa.doFinal(ByteArray(maxOf(0, taille - octets.size)) + octets) } catch (e: Exception) { continue }
            algo = u(d[0]); cleSession = d.copyOfRange(1, d.size - 2)
            if (tag == 1) break
        }
        val cs = cleSession ?: return null
        if (algo !in listOf(7, 8, 9)) return null
        val sed = ps.firstOrNull { it.first == 18 }?.second ?: return null
        if (u(sed[0]) != 1) return null
        val aes = Cipher.getInstance("AES/CFB/NoPadding"); aes.init(Cipher.DECRYPT_MODE, SecretKeySpec(cs, "AES"), IvParameterSpec(ByteArray(16)))
        val tout = aes.doFinal(sed.copyOfRange(1, sed.size))
        if (tout.size < 18 + 22 || tout[14] != tout[16] || tout[15] != tout[17]) return null
        val mdc = tout.copyOfRange(tout.size - 20, tout.size)
        if (!MessageDigest.getInstance("SHA-1").digest(tout.copyOfRange(0, tout.size - 20)).contentEquals(mdc)) return null
        return litteral(tout.copyOfRange(18, tout.size - 22))
    }

    private fun litteral(b: ByteArray): ByteArray? {
        for ((tag, c) in paquets(b)) {
            if (tag == 11) { val ln = u(c[1]); return c.copyOfRange(2 + ln + 4, c.size) }
            if (tag == 8) {
                val donnees = c.copyOfRange(1, c.size)
                val dec = when (u(c[0])) {
                    0 -> donnees
                    1 -> java.util.zip.InflaterInputStream(donnees.inputStream(), java.util.zip.Inflater(true)).readBytes()
                    2 -> java.util.zip.InflaterInputStream(donnees.inputStream()).readBytes()
                    else -> return null
                }
                return litteral(dec)
            }
        }
        return null
    }

    // ---------------------------------------------------------------- la commande gpg du téléphone
    private fun mots(ligne: String) = Regex("\"([^\"]*)\"|'([^']*)'|(\\S+)").findAll(ligne).map { m ->
        m.groupValues[1].ifEmpty { m.groupValues[2].ifEmpty { m.groupValues[3] } }.let { if (m.value == "\"\"" || m.value == "''") "" else it } }.toList()

    private fun date(s: Long) = java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss", java.util.Locale.ROOT).format(java.util.Date(s * 1000))

    fun commande(ligne: String, ici: File, terrain: File): String {
        val m = mots(ligne.trim()).drop(1)
        var homedir: String? = null; var sortie: String? = null; var armure = false
        val dest = mutableListOf<String>(); var action: String? = null; var arg: String? = null
        val libres = mutableListOf<String>()
        var i = 0
        while (i < m.size) {
            val x = m[i]
            when (x) {
                "--homedir" -> { homedir = m.getOrNull(i + 1); i++ }
                "--passphrase", "--pinentry-mode", "--trust-model", "--status-fd", "--default-key" -> i++
                "-u", "--local-user" -> i++
                "--batch", "--no-tty", "--yes", "-q", "--quiet", "-v" -> {}
                "-a", "--armor" -> armure = true
                "-o", "--output" -> { sortie = m.getOrNull(i + 1); i++ }
                "-r", "--recipient" -> { m.getOrNull(i + 1)?.let { dest.add(it) }; i++ }
                "--quick-gen-key", "--quick-generate-key" -> { action = "gen"; arg = m.getOrNull(i + 1); i++ }
                "-k", "--list-keys", "--fingerprint" -> action = "liste"
                "-K", "--list-secret-keys" -> action = "secretes"
                "--export" -> action = "export"
                "--import" -> action = "import"
                "-e", "--encrypt" -> action = "chiffre"
                "-d", "--decrypt" -> action = "dechiffre"
                "--clearsign", "--clear-sign" -> action = "signe"
                "--verify" -> action = "verifie"
                "-ea", "-ae" -> { action = "chiffre"; armure = true }
                else -> libres.add(x)
            }
            i++
        }
        if (homedir == null) return t("cr.tel.gpg.homedir")
        fun chemin(x: String) = (if (x.startsWith("/")) File(x) else File(ici, x)).canonicalFile
        val dir = chemin(homedir)
        if (!dir.path.startsWith(terrain.canonicalPath + "/")) return t("cr.tel.gpg.dehors")
        val tr = Trousseau(dir)
        fun fichier(nom: String) = chemin(nom).takeIf { it.path.startsWith(terrain.canonicalPath + "/") }
        return try {
            when (action) {
                "gen" -> {
                    val uid = arg ?: return t("cr.tel.gpg.usage")
                    val k = tr.generer(uid)
                    "gpg: key ${hexa(k.id)} marked as ultimately trusted\npub   rsa2048 ${date(k.cree).take(10)} [SCE]\n      ${hexa(k.empreinte)}\nuid                      $uid"
                }
                "liste", "secretes" -> tr.cles().filter { action == "liste" || it.prive != null }.filter { libres.isEmpty() || libres.any { q -> q in it.uid } }
                    .joinToString("\n") { "${if (action == "liste") "pub" else "sec"}   rsa2048 ${date(it.cree).take(10)} [SCE]\n      ${hexa(it.empreinte)}\nuid           [ultimate] ${it.uid}\n" }
                    .ifEmpty { "gpg: error reading key: No public key" }
                "export" -> {
                    val k = (libres.firstOrNull()?.let { tr.secrete(it) ?: tr.publique(it) }) ?: tr.cles().firstOrNull { it.prive != null }
                        ?: return "gpg: WARNING: nothing exported"
                    if (k.prive == null) return "gpg: WARNING: nothing exported"
                    val txt = exporter(k)
                    if (sortie != null) { fichier(sortie)?.writeText(txt) ?: return t("cr.tel.gpg.dehors"); "" } else txt.trimEnd()
                }
                "import" -> {
                    val f = libres.firstOrNull()?.let { fichier(it) } ?: return t("cr.tel.gpg.usage")
                    val k = importer(f.readBytes()); tr.importer(k)
                    "gpg: key ${hexa(k.id)}: public key \"${k.uid}\" imported\ngpg: Total number processed: 1\ngpg:               imported: 1"
                }
                "chiffre" -> {
                    val f = libres.lastOrNull()?.let { fichier(it) } ?: return t("cr.tel.gpg.usage")
                    if (!f.isFile) return "gpg: can't open '${libres.last()}': No such file or directory"
                    val qui = dest.firstOrNull() ?: return "gpg: no valid addressees"
                    val k = tr.publique(qui) ?: return "gpg: $qui: skipped: No public key\ngpg: ${f.name}: encryption failed: No public key"
                    val c = chiffrer(f.readBytes(), f.name, k)
                    val o = fichier(sortie ?: (f.name + if (armure) ".asc" else ".gpg")) ?: return t("cr.tel.gpg.dehors")
                    if (armure) o.writeText(armure("MESSAGE", c)) else o.writeBytes(c)
                    ""
                }
                "dechiffre" -> {
                    val f = libres.lastOrNull()?.let { fichier(it) } ?: return t("cr.tel.gpg.usage")
                    if (!f.isFile) return "gpg: can't open '${libres.last()}': No such file or directory"
                    val c = dechiffrer(f.readBytes(), tr) ?: return "gpg: decryption failed: No secret key"
                    if (sortie != null) { fichier(sortie)?.writeBytes(c) ?: return t("cr.tel.gpg.dehors"); "" } else String(c, Charsets.UTF_8).trimEnd()
                }
                "signe" -> {
                    val f = libres.lastOrNull()?.let { fichier(it) } ?: return t("cr.tel.gpg.usage")
                    if (!f.isFile) return "gpg: can't open '${libres.last()}': No such file or directory"
                    val k = tr.cles().firstOrNull { it.prive != null } ?: return "gpg: no default secret key: No secret key"
                    val o = fichier(sortie ?: (f.name + ".asc")) ?: return t("cr.tel.gpg.dehors")
                    o.writeText(signerEnClair(f.readText(), k))
                    ""
                }
                "verifie" -> {
                    val f = libres.lastOrNull()?.let { fichier(it) } ?: return t("cr.tel.gpg.usage")
                    if (!f.isFile) return "gpg: can't open '${libres.last()}': No such file or directory"
                    val v = verifierEnClair(f.readText(), tr) ?: return "gpg: Can't check signature: No public key"
                    val k = tr.publique(v.second)
                    "gpg: Signature made ${date(System.currentTimeMillis() / 1000)}\ngpg:                using RSA key ${k?.let { hexa(it.empreinte) } ?: ""}\n" +
                        (if (v.first) "gpg: Good signature from \"${v.second}\" [ultimate]" else "gpg: BAD signature from \"${v.second}\" [ultimate]")
                }
                else -> t("cr.tel.gpg.usage")
            }
        } catch (e: Exception) { "gpg: " + t("cr.tel.gpg.erreur", "erreur" to (e.message ?: e.javaClass.simpleName)) }
    }
}
