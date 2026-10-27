package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject

/**
 * L'introduction du jeu et le déblocage progressif (portage de pc/tg/intro.py, mêmes règles, mêmes données).
 *
 * Nouvelle partie (le nom tapé dans le terminal de l'appli, TerminalActivity) :
 *  1. quelques écrans dessinés (IntroVue) : le Terminaworld s'est endormi, seules les commandes tapées dans l'invite
 *     de commande peuvent le réveiller ; Suivant ▶ / Passer ⏭ / Entrée, ou taper directement le nom de l'œuf ;
 *  2. l'œuf seul, l'invite et une petite liste de 4 commandes (pwd, ls, echo, whoami) ; chaque bonne commande fait
 *     réagir l'œuf (il remue, brille, se fêle : 3 fêlures) ; un petit tutoriel de l'invite arrive pas à pas
 *     (où taper et Entrée, une erreur n'est pas grave, ↑ rappelle, Tab complète) ;
 *  3. la 4e commande : l'œuf éclot, la créature dit merci, récapitule (le vrai sens des commandes), dit où on est (le
 *     camp de base, ce que pwd a montré) et la suite (le chapitre 1) ;
 *  4. le reste s'ouvre petit à petit (table « deblocages » de intro.json, la même que sur PC) : chaque fonction est
 *     présentée par la créature en un écran au moment où elle s'ouvre ; avant, ses commandes répondent gentiment
 *     « pas encore » et ses éléments d'écran sont cachés.
 * Données : assets/intro.json (copie exacte de donnees/intro.json, comme pc/tg/intro.json).
 * Sauvegarde : jeu.extra « intro » {etat: oeuf | fini, faits, evt, erreur} et « debloc » {mode: progressif | ancien | tout,
 * ouverts, presentes, file}. Une ancienne partie (sans « debloc ») : tout reste ouvert, rien n'est présenté.
 * « debloquer tout » (parents, tests) ouvre tout d'un coup après confirmation. Tests : tests/jvm/Intro.kt.
 * Le dessin passe par un Peintre (comme Carte.kt) : IntroVue sur un Canvas, le test JVM sur une image Java.
 */
object Intro {
    // ---------------------------------------------------------------- les données (intro.json)
    var chargeur: (() -> String?)? = null
    @Volatile private var donnees: JSONObject? = null

    fun init(ctx: android.content.Context) {
        Oeufs.init(ctx)
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("intro.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    fun d(): JSONObject = donnees ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() })
        .also { if (it.has("deblocages")) donnees = it }

    class Fonction(val id: String, val emoji: String, val icone: String, val quand: JSONObject, val commandes: List<String>,
                   val cmdTel: List<String>)

    class Ligne(val id: String, val re: Regex)

    private fun chaines(a: JSONArray?): List<String> = if (a == null) emptyList() else (0 until a.length()).map { a.getString(it) }

    private var fCache: List<Fonction>? = null
    fun fonctions(): List<Fonction> = fCache ?: run {
        val a = d().optJSONArray("deblocages") ?: JSONArray()
        (0 until a.length()).map { a.getJSONObject(it) }.map {
            Fonction(it.getString("id"), it.optString("emoji"), it.optString("icone"), it.optJSONObject("quand") ?: JSONObject(),
                chaines(it.optJSONArray("commandes")), chaines(it.optJSONArray("cmd_tel")))
        }.also { if (it.isNotEmpty()) fCache = it }
    }

    fun fonction(id: String) = fonctions().firstOrNull { it.id == id }

    private var lCache: List<Ligne>? = null
    fun liste(): List<Ligne> = lCache ?: run {
        val a = d().optJSONArray("checklist") ?: JSONArray()
        (0 until a.length()).map { a.getJSONObject(it) }.map { Ligne(it.getString("id"), Regex(it.getString("re"), RegexOption.IGNORE_CASE)) }
            .also { if (it.isNotEmpty()) lCache = it }
    }

    /** La fonction du jeu à laquelle appartient une commande (« carte » → « carte »), ou null. */
    fun fonctionDe(cmd: String): String? = fonctions().firstOrNull { cmd.lowercase() in it.commandes }?.id

    // ---------------------------------------------------------------- l'état
    private fun lst(o: JSONObject, k: String): MutableList<String> = chaines(o.optJSONArray(k)).toMutableList()
    private fun ajouter(o: JSONObject, k: String, v: String) { val l = lst(o, k); if (v !in l) { l.add(v); o.put(k, JSONArray(l)) } }

    /** L'état de l'intro (une ancienne partie n'en a pas : l'intro est finie depuis longtemps). */
    fun i(jeu: Jeu): JSONObject {
        val i = jeu.extra.optJSONObject("intro") ?: JSONObject().put("etat", "fini").also { jeu.extra.put("intro", it) }
        if (!i.has("etat")) i.put("etat", "fini")
        if (!i.has("faits")) i.put("faits", JSONArray())
        return i
    }

    /** L'état du déblocage (une ancienne partie : tout est ouvert, rien n'est présenté). */
    fun deb(jeu: Jeu): JSONObject {
        var o = jeu.extra.optJSONObject("debloc")
        if (o == null) {
            o = JSONObject().put("mode", "ancien").put("ouverts", JSONArray(fonctions().map { it.id }))
                .put("presentes", JSONArray()).put("file", JSONArray())
            jeu.extra.put("debloc", o)
            for (f in fonctions()) if (condition(jeu, f.quand)) ajouter(o, "presentes", f.id)
        }
        for (k in listOf("ouverts", "presentes", "file")) if (!o.has(k)) o.put(k, JSONArray())
        if (!o.has("mode")) o.put("mode", "ancien")
        return o
    }

    /** Une nouvelle partie avec l'intro : l'œuf, la liste de commandes, tout le reste fermé. */
    /** Le nom de l'œuf, sans caractères de contrôle (échappements, retournement du texte), 16 au plus (P1-6). */
    fun nomPropre(nom: String): String = nom.filter { c ->
        val t = Character.getType(c)
        t != Character.CONTROL.toInt() && t != Character.FORMAT.toInt()
    }.trim().take(16)

    fun nouvellePartie(jeu: Jeu) {
        jeu.extra.put("intro", JSONObject().put("etat", "oeuf").put("faits", JSONArray()).put("erreur", false))
        jeu.extra.put("debloc", JSONObject().put("mode", "progressif").put("ouverts", JSONArray()).put("presentes", JSONArray())
            .put("file", JSONArray()))
        Oeufs.choisir(jeu)                      // l'œuf reçoit son type, le compagnon qui en sortira le même
    }

    /** Vrai pendant que l'œuf attend ses commandes : il n'éclot pas avant la fin de la liste (l'XP s'arrête à 9). */
    fun retient(jeu: Jeu) = jeu.extra.optJSONObject("intro")?.optString("etat") == "oeuf"
    fun enCours(jeu: Jeu) = retient(jeu)
    fun eclos(jeu: Jeu) = i(jeu).optString("etat") == "fini"
    fun faits(jeu: Jeu) = lst(i(jeu), "faits")

    fun ouvert(jeu: Jeu, fid: String): Boolean {
        val d = deb(jeu)
        return d.optString("mode") != "progressif" || fid in lst(d, "ouverts")
    }

    /** Le message gentil si la commande appartient à une fonction pas encore ouverte, sinon null.
     *  (« carte » suivie d'un lieu est le plan de la ville du téléphone : toujours là.) */
    fun bloque(jeu: Jeu, cmd: String, reste: String = ""): String? {
        if (!jeu.existe) return null
        if (cmd == "carte" && reste.isNotBlank()) return null
        val fid = fonctionDe(cmd) ?: return null
        return if (ouvert(jeu, fid)) null else t("deb.pas_encore", "cmd" to cmd)
    }

    /** Toutes les conditions de « quand » sont vraies. */
    fun condition(jeu: Jeu, q: JSONObject): Boolean {
        if (q.optBoolean("eclos") && !eclos(jeu)) return false
        if (jeu.niveau < q.optInt("niveau", 0)) return false
        val lecons = chaines(q.optJSONArray("lecons"))
        val chapitres = chaines(q.optJSONArray("chapitres"))
        if (lecons.isNotEmpty() || chapitres.isNotEmpty() || q.has("ailes")) {
            val faits = Histoire.faits(jeu)
            if (lecons.any { it !in faits }) return false
            val ailes = Histoire.ailes(jeu)
            if (chapitres.any { it !in ailes }) return false
            if (Histoire.nbAiles(jeu) < q.optInt("ailes", 0)) return false
        }
        if (Explo.captures(jeu).length() < q.optInt("captures", 0)) return false
        return chaines(q.optJSONArray("apres")).all { ouvert(jeu, it) }
    }

    /** Ouvre (et met en file pour être présentée) chaque fonction dont la condition est maintenant vraie. */
    fun verifier(jeu: Jeu) {
        if (!jeu.existe) return
        val d = deb(jeu)
        for (f in fonctions()) {
            if (f.id in lst(d, "presentes") || !condition(jeu, f.quand)) continue
            ajouter(d, "presentes", f.id)
            ajouter(d, "ouverts", f.id)
            if (f.id == "histoire" || d.optString("mode") != "progressif") continue   // merci la présente ; ancienne partie : rien
            ajouter(d, "file", f.id)
            jeu.log(t("deb.nouveau.log", "nom" to f.emoji + " " + t("deb.${f.id}.titre")))
            jeu.dire(t("deb.nouveau.dit", "nom" to t("deb.${f.id}.titre")), 10)
            jeu.animer("content")
        }
    }

    /** « debloquer tout » : toutes les fonctions ouvertes d'un coup, l'œuf éclos (pour les parents et les tests). */
    fun toutDebloquer(jeu: Jeu) {
        if (retient(jeu)) finir(jeu)
        val d = deb(jeu)
        for (f in fonctions()) { ajouter(d, "ouverts", f.id); ajouter(d, "presentes", f.id) }
        d.put("file", JSONArray(lst(d, "file").filter { it == "merci" || it == "merci2" }))
        d.put("mode", "tout")
    }

    // ---------------------------------------------------------------- la liste de commandes de l'œuf
    /** Après le repas (Jeu.manger) : une commande de la liste fait réagir l'œuf ; la dernière le fait éclore.
     *  Renvoie vrai si l'œuf vient d'éclore avec cette commande (elle ne valide pas déjà la leçon 1). */
    fun apresCommande(jeu: Jeu, ligne: String?, ignoree: Boolean, code: Int? = null): Boolean {
        if (!retient(jeu) || ligne == null || ignoree || Regles.estColle(ligne)) return false
        val i = i(jeu)
        val f = faits(jeu)
        // G-34 : `pwd; ls` compte pour les deux ; `PWD` (majuscules) ou une commande qui a échoué ne compte pas
        val parts = Verif.couper(ligne.trim(), listOf("&&", ";"))
        val trouves = mutableListOf<Ligne>()
        for ((k, p) in parts.withIndex()) {
            val c0 = if (k == parts.size - 1 || code == 0) code else null
            if ((c0 != null && c0 != 0) || !Verif.casseOk(Verif.premier(p.first))) continue
            liste().firstOrNull { it.id !in f && it !in trouves && it.re.containsMatchIn(p.first.trim()) }?.let { trouves.add(it) }
        }
        if (trouves.isEmpty()) return false
        for (c in trouves) {
            f.add(c.id)
            i.put("faits", JSONArray(f))
            val n = f.size
            i.put("evt", JSONArray().put(n).put(System.currentTimeMillis()))
            if (n >= liste().size) { finir(jeu); return true }
            jeu.anim = "oeuf_$n" to System.currentTimeMillis()
            jeu.dire(t("intro.reagit.$n"), 8)
        }
        jeu.log("🥚 ✔ ${ligne.trim()}")
        return false
    }

    /** Une commande inconnue pendant que l'œuf attend : le petit tutoriel dit que ce n'est pas grave. */
    fun signalerErreur(jeu: Jeu) { if (retient(jeu)) i(jeu).put("erreur", true) }

    /** L'œuf éclot : la créature naît (niveau 2), l'histoire s'ouvre, l'écran « merci » attend. */
    fun finir(jeu: Jeu) {
        val i = i(jeu)
        i.put("etat", "fini")
        i.put("evt", JSONArray().put(liste().size).put(System.currentTimeMillis()))
        jeu.bulles.clear()                        // les réactions de l'œuf en attente : l'éclosion passe avant
        jeu.bulle = ""
        jeu.bulleFin = 0L
        jeu.ajouterXp(maxOf(0, 10 - jeu.xp))
        jeu.anim = "eclosion" to System.currentTimeMillis()
        val d = deb(jeu)
        val file = lst(d, "file")
        for ((k, x) in listOf("merci", "merci2").withIndex()) if (x !in file) file.add(minOf(k, file.size), x)
        d.put("file", JSONArray(file))
        verifier(jeu)
    }

    fun prochaine(jeu: Jeu): Ligne? = faits(jeu).let { f -> liste().firstOrNull { it.id !in f } }

    /** La commande à taper d'une ligne de la liste (le passage `…` de son texte). */
    fun commandeDe(l: Ligne): String = Vert.PASSAGE.find(t("intro.l.${l.id}"))?.groupValues?.get(1) ?: l.id

    /** Le petit tutoriel de l'invite, une chose à la fois : Entrée, l'erreur, ↑, Tab. */
    fun astuce(jeu: Jeu): String {
        val n = faits(jeu).size
        if (i(jeu).optBoolean("erreur") && n < 2) return t("intro.astuce.erreur")
        return t("intro.astuce.${minOf(n, 3)}")
    }

    /** La liste en texte (✔ fait, ➜ la prochaine, · les autres), commandes entre ` (en vert à l'écran). */
    fun texteListe(jeu: Jeu): String {
        val f = faits(jeu)
        val p = prochaine(jeu)
        return liste().joinToString("\n") { (if (it.id in f) "✔ " else if (it.id == p?.id) "➜ " else "· ") + t("intro.l.${it.id}") }
    }

    fun titreListe(jeu: Jeu) = t("intro.liste.titre", "n" to faits(jeu).size, "total" to liste().size)

    // ---------------------------------------------------------------- les écrans à présenter (merci, fonctions)
    /** L'écran « Nouveau : … » à montrer, ou null. P2-6 : pas en pleine étape de leçon (il attend qu'elle soit réussie),
     *  sauf l'écran « merci » de l'éclosion. */
    fun aMontrer(jeu: Jeu): String? = if (!jeu.existe || retient(jeu)) null else lst(deb(jeu), "file").firstOrNull()
        ?.takeIf { it == "merci" || it == "merci2" || !Histoire.enPleineEtape(jeu) }

    fun lu(jeu: Jeu) {
        val d = deb(jeu)
        val f = lst(d, "file")
        if (f.isNotEmpty()) { f.removeAt(0); d.put("file", JSONArray(f)) }
    }

    /** (titre, paragraphes) d'un écran : merci, merci2, ou une fonction qui s'ouvre. chemin : ce que pwd montre. */
    fun contenu(jeu: Jeu, cid: String, chemin: String = "~"): Pair<String, List<String>> = when (cid) {
        "merci" -> t("intro.merci.titre", "nom" to jeu.nom) to
            (listOf(t("intro.merci", "nom" to jeu.nom), t("intro.recap")) + liste().map { t("intro.r.${it.id}") })
        "merci2" -> t("intro.ici.titre") to listOf(t("intro.ici", "chemin" to chemin),
            t("intro.suite", "chapitre" to t("hist.reveil.titre")))
        else -> {
            val c = fonction(cid)?.cmdTel ?: emptyList()
            t("deb.nouveau", "nom" to t("deb.$cid.titre")) to
                listOf(t("deb.$cid.texte", "cmd" to c.getOrElse(0) { "" }, "cmd2" to c.getOrElse(1) { "" }))
        }
    }

    // ---------------------------------------------------------------- les dessins en pixels (mêmes que sur PC)
    private fun couleur(h: String): Int = (0xFF000000.toInt()) or h.removePrefix("#").toInt(16)

    private val pixCache = HashMap<String, Carte.Pix>()

    fun pix(rows: List<String>, pal: Map<Char, Int>): Carte.Pix {
        val w = rows.maxOf { it.length }
        return Carte.Pix(w, rows.size, IntArray(w * rows.size) { k -> rows[k / w].getOrNull(k % w)?.let { pal[it] } ?: 0 })
    }

    /** Une scène des écrans du début (28×14 pixels). */
    fun scene(nom: String): Carte.Pix = pixCache.getOrPut("s:$nom") {
        val pal = d().optJSONObject("palette") ?: JSONObject()
        val p = pal.keys().asSequence().associate { it[0] to couleur(pal.getString(it)) }
        pix(chaines(d().optJSONObject("scenes")?.optJSONArray(nom)), p)
    }

    /** Le cadre de l'œuf de l'intro (oeufs.json, taille « grand »). */
    const val W_OEUF = 26
    const val H_OEUF = 26

    /**
     * Une image de l'œuf de type ty (26×26 pixels, lignes de caractères), même calcul que intro.image_oeuf sur PC :
     * fele = nombre de fêlures (0 à 3 : intact, une fêlure qui luit, le dessin fissuré, une grande fêlure) ; nom = remue
     * (il penche), brille (son contour luit, des étincelles), craque (la fêlure éclaire), eclot (il tremble puis s'ouvre ;
     * null à la fin : la créature prend la place). Les dessins : Oeufs.kt.
     */
    fun imageOeuf(fele: Int, nom: String = "", k: Int = 0, ty: String = "feu"): List<String>? = Oeufs.image(ty, fele, nom, k)

    fun pixOeuf(fele: Int, nom: String = "", k: Int = 0, ty: String = "feu"): Carte.Pix? =
        imageOeuf(fele, nom, k, ty)?.let { rows -> pixCache.getOrPut("o:$ty:$fele:$nom:$k") { pix(rows, Oeufs.palette(ty)) } }

    /** Les images d'une réaction de l'œuf à la n-ième bonne commande : (fêlures, nom, k). */
    fun reaction(n: Int): List<Triple<Int, String, Int>> = when (n) {
        1 -> (0 until 8).map { Triple(0, "remue", it) } + (0 until 4).map { Triple(1, "craque", it) }
        2 -> (0 until 6).map { Triple(1, "brille", it) } + (0 until 4).map { Triple(2, "craque", it) }
        3 -> (0 until 4).map { Triple(2, "remue", it) } + (0 until 4).map { Triple(2, "brille", it) } + (0 until 4).map { Triple(3, "craque", it) }
        else -> (0 until 8).map { Triple(3, "eclot", it) }
    }

    /** Le nombre de la réaction d'une animation (« oeuf_2 » → 2, « eclosion » → 4), ou 0. */
    fun numeroAnim(nom: String): Int = when {
        nom == "eclosion" -> 4
        nom.startsWith("oeuf_") -> nom.removePrefix("oeuf_").toIntOrNull() ?: 0
        else -> 0
    }

    // ---------------------------------------------------------------- dessiner (dp, par un Peintre)
    const val MARGE = 14f
    const val ROSE = 0xFFFF87FF.toInt()
    const val FOND_BOUTON = 0xFF1F3A2A.toInt()

    class Bouton(val x: Float, val y: Float, val w: Float, val h: Float, val action: String)
    class Rendu(val l: Float, val h: Float, val boutons: List<Bouton>)

    /** Coupe un texte (avec ses `commandes`) en lignes de largeur l au plus ; coupe aussi un mot trop long (CJK…). */
    fun couper(p: Peintre, s: String, l: Float, taille: Float, gras: Boolean = false): List<String> {
        val out = mutableListOf<String>()
        for (para in s.split("\n")) {
            var cur = ""
            for (mot0 in para.split(" ")) {
                var mot = mot0
                val essai = if (cur.isEmpty()) mot else "$cur $mot"
                if (p.mesure(Vert.sansMarques(essai), taille, gras = gras) <= l) { cur = essai; continue }
                if (cur.isNotEmpty() && p.mesure(Vert.sansMarques(mot), taille, gras = gras) <= l) { out.add(cur); cur = mot; continue }
                // trop long : caractère par caractère
                if (cur.isNotEmpty()) mot = "$cur $mot"
                cur = ""
                for (c in mot) {
                    val e = cur + c
                    if (cur.isNotEmpty() && p.mesure(Vert.sansMarques(e), taille, gras = gras) > l) { out.add(cur); cur = c.toString().trimStart() }
                    else cur = e
                }
            }
            if (cur.isNotEmpty()) out.add(cur)
        }
        var ouvert = false
        return out.map { x ->
            var y = if (ouvert) "`$x" else x
            ouvert = y.count { it == '`' } % 2 == 1
            if (ouvert) y += "`"
            y
        }
    }

    /** Écrit des lignes (commandes en vert) ; renvoie le y suivant. */
    private fun paragraphe(p: Peintre, s: String, x: Float, y0: Float, l: Float, taille: Float, couleur: Int, interligne: Float): Float {
        var y = y0
        for (ligne in couper(p, s, l, taille)) {
            Carte.texteVert(p, ligne, x, y + taille, taille, couleur)
            y += interligne
        }
        return y
    }

    private fun cadre(p: Peintre, l: Float, h: Float) {
        p.rect(0f, 0f, l, h, Carte.FOND)
        var b = 0f
        while (b < h) { p.rect(0f, b, l, 1f, Carte.BALAYAGE); b += 3f }
        p.rect(0f, 0f, l, 2f, Carte.BORD); p.rect(0f, h - 2f, l, 2f, Carte.BORD)
        p.rect(0f, 0f, 2f, h, Carte.BORD); p.rect(l - 2f, 0f, 2f, h, Carte.BORD)
    }

    private fun bouton(p: Peintre, texte: String, x: Float, y: Float, plein: Boolean, action: String): Bouton {
        val w = p.mesure(texte, 13f, gras = true) + 26f
        val h = 34f
        p.rect(x, y, w, h, if (plein) Carte.VERT else Carte.BORD)
        if (!plein) p.rect(x + 2f, y + 2f, w - 4f, h - 4f, FOND_BOUTON)
        p.texte(texte, x + 13f, y + 22f, 13f, if (plein) Carte.FOND else Carte.TEXTE, gras = true)
        return Bouton(x, y, w, h, action)
    }

    /** Un écran du début (n de 1 à total) : la scène, le titre, le texte, les points, Passer / Suivant. */
    fun dessinerEcran(p: Peintre, n: Int, total: Int, l: Float): Rendu {
        val ecr = d().optJSONArray("ecrans")?.optJSONObject(n - 1)
        val sc = scene(ecr?.optString("scene") ?: "monde")
        val haut = 2000f
        // 1. mesurer
        val e = minOf(9f, (l - 2 * MARGE) / sc.w)
        val hScene = sc.h * e
        val titre = couper(p, t("intro.e.titre.$n"), l - 2 * MARGE, 17f, gras = true)
        val texte = couper(p, t("intro.e.texte.$n"), l - 2 * MARGE, 13.5f)
        val dernier = n >= total
        val nom = if (dernier) couper(p, t("intro.nom.tel"), l - 2 * MARGE, 13.5f, gras = true) else emptyList()
        val h = MARGE + hScene + 16f + titre.size * 22f + 6f + texte.size * 19f + nom.size * 19f + 14f + 12f + 44f + MARGE
        // 2. dessiner
        cadre(p, l, h)
        p.pixels(sc, (l - sc.w * e) / 2, MARGE, e)
        var y = MARGE + hScene + 16f
        for (x in titre) { p.texte(x, MARGE, y + 17f, 17f, ROSE, gras = true); y += 22f }
        y += 6f
        for (x in texte) { Carte.texteVert(p, x, MARGE, y + 13.5f, 13.5f, Carte.TEXTE); y += 19f }
        for (x in nom) { p.texte(x, MARGE, y + 13.5f, 13.5f, Carte.VERT, gras = true); y += 19f }
        y += 14f
        for (k in 1..total) p.rect(l / 2 - total * 9f + (k - 1) * 18f + 5f, y, 8f, 8f, if (k == n) Carte.VERT else Carte.BORD)
        y += 12f
        val boutons = mutableListOf<Bouton>()
        if (!dernier) {
            boutons.add(bouton(p, t("intro.passer"), MARGE, y, false, "passer"))
            val s = t("intro.suivant")
            boutons.add(bouton(p, s, l - MARGE - (p.mesure(s, 13f, gras = true) + 26f), y, true, "suivant"))
        }
        return Rendu(l, minOf(h, haut), boutons)
    }

    /**
     * L'écran de l'œuf : l'œuf (image donnée : une image de son animation, sinon l'œuf et ses fêlures), son nom, la
     * liste de commandes (✔ / ➜ / ·, commandes en vert), l'astuce du moment et où taper.
     */
    fun dessinerOeuf(p: Peintre, jeu: Jeu, l: Float, image: Carte.Pix? = null): Rendu {
        val fele = minOf(3, faits(jeu).size)
        val ty = Oeufs.typeDe(jeu)
        val oeuf = image ?: pixOeuf(fele, ty = ty)!!
        val e = 5f
        val xD = MARGE + W_OEUF * e + 12f
        val lD = l - xD - MARGE
        val lignes = liste()
        val f = faits(jeu)
        val pr = prochaine(jeu)
        val textes = lignes.map { couper(p, t("intro.l.${it.id}"), l - 2 * MARGE - 22f, 13.5f) }
        val ast = couper(p, astuce(jeu), l - 2 * MARGE - 22f, 12.5f)
        val ou = couper(p, t("intro.ou.tel"), l - 2 * MARGE, 11.5f)
        val nomL = couper(p, jeu.nom, lD, 16f, gras = true)
        val typeL = couper(p, t("intro.type.$ty"), lD, 12f)
        val hHaut = maxOf(H_OEUF * e, nomL.size * 21f + 20f + typeL.size * 16f + 4f + 18f + 16f)
        val h = MARGE + hHaut + 14f + textes.sumOf { it.size } * 19f + 8f * lignes.size + 8f + ast.size * 17f + 8f + ou.size * 15f + MARGE
        cadre(p, l, h)
        p.pixels(oeuf, MARGE, MARGE, e)
        var y = MARGE
        for (x in nomL) { p.texte(x, xD, y + 16f, 16f, Carte.TEXTE, gras = true); y += 21f }
        p.texte(t("intro.oeuf.titre"), xD, y + 13f, 12f, Carte.DOUX); y += 20f
        for (x in typeL) { p.texte(x, xD, y + 12f, 12f, Carte.AMBRE); y += 16f }
        y += 4f
        p.texte(titreListe(jeu), xD, y + 13f, 12.5f, Carte.AMBRE, gras = true); y += 18f
        for (k in lignes.indices) p.rect(xD + k * 20f, y + 2f, 14f, 8f, if (lignes[k].id in f) Carte.VERT else Carte.BORD)
        y = MARGE + hHaut + 14f
        for ((k, lg) in lignes.withIndex()) {
            val fait = lg.id in f
            val (signe, c) = when { fait -> "✔" to Carte.VERT; lg.id == pr?.id -> "➜" to Carte.JAUNE; else -> "·" to Carte.DOUX }
            p.texte(signe, MARGE, y + 13.5f, 13.5f, c, gras = true)
            for (x in textes[k]) { Carte.texteVert(p, x, MARGE + 22f, y + 13.5f, 13.5f, if (fait) Carte.DOUX else Carte.TEXTE); y += 19f }
            y += 8f
        }
        y += 8f
        p.pixels(Carte.icone("etoile"), MARGE + 2f, y + 1f, 2.4f)
        for (x in ast) { Carte.texteVert(p, x, MARGE + 22f, y + 12.5f, 12.5f, Carte.AMBRE); y += 17f }
        y += 8f
        for (x in ou) { p.texte(x, MARGE, y + 11.5f, 11.5f, Carte.DOUX); y += 15f }
        return Rendu(l, h, emptyList())
    }

    /** Un écran de présentation : la créature (ou son guide) et le titre, les paragraphes, OK ▶. */
    fun dessinerCarte(p: Peintre, jeu: Jeu, cid: String, l: Float, chemin: String = "~"): Rendu {
        val (titre, paras) = contenu(jeu, cid, chemin)
        val icone = fonction(cid)?.icone
        val hC = 64f
        val xT = MARGE + hC + 12f
        val tl = couper(p, titre, l - xT - MARGE, 16f, gras = true)
        val ps = paras.map { couper(p, it, l - 2 * MARGE, 13f) }
        val hHaut = maxOf(hC, tl.size * 21f + (if (icone != null) 30f else 0f))
        val h = MARGE + hHaut + 12f + 4f + ps.sumOf { it.size } * 18f + ps.size * 8f + 10f + 34f + MARGE
        cadre(p, l, h)
        if (!p.creature(MARGE + hC / 2, MARGE + hC, hC)) p.pixels(Carte.icone("oeuf"), MARGE + 8f, MARGE + 8f, 6f)
        var y = MARGE
        for (x in tl) { p.texte(x, xT, y + 16f, 16f, ROSE, gras = true); y += 21f }
        if (icone != null) p.pixels(Carte.icone(icone), xT, y + 4f, 3f)
        y = MARGE + hHaut + 12f
        p.rect(MARGE, y, l - 2 * MARGE, 2f, Carte.BORD)
        y += 4f + 6f
        for (para in ps) {
            for (x in para) { Carte.texteVert(p, x, MARGE, y + 13f, 13f, Carte.TEXTE); y += 18f }
            y += 8f
        }
        y += 2f
        val s = t("intro.ok.tel")
        val b = bouton(p, s, l - MARGE - (p.mesure(s, 13f, gras = true) + 26f), y, true, "ok")
        return Rendu(l, h, listOf(b))
    }
}
