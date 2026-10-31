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
 * Sauvegarde : jeu.extra « intro » {etat: oeuf | fini, faits, evt, erreur, eveil (l'heure de la 1re commande, ms)} et « debloc » {mode: progressif | ancien | tout,
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
        Scenes.init(ctx)
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
        if (Satiete.niveauAppris(jeu) < q.optInt("niveau", 0)) return false   // l'XP mise de côté compte aussi
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
            if (n == 1 && i.optLong("eveil", 0L) == 0L) i.put("eveil", System.currentTimeMillis())   // le camp se rallume
            if (n >= liste().size) { finir(jeu); return true }
            jeu.anim = "oeuf_$n" to System.currentTimeMillis()
            jeu.dire(t("intro.recoit", "pct" to Scenes.cible(n)), 8)
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
    fun dessinerEcranAncien(p: Peintre, n: Int, total: Int, l: Float): Rendu {
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
    fun dessinerOeufAncien(p: Peintre, jeu: Jeu, l: Float, image: Carte.Pix? = null): Rendu {
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
        p.texte(t("intro.oeuf.titre", "type" to Guide.nomType(ty)), xD, y + 13f, 12f, Carte.DOUX); y += 20f
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
    fun dessinerCarte(p: Peintre, jeu: Jeu, cid: String, l: Float, chemin: String = "~", quand: Long = System.currentTimeMillis()): Rendu {
        if ((cid == "merci" || cid == "merci2") && Scenes.disponible()) return dessinerMerci(p, jeu, cid, l, chemin, quand)
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

    // ---------------------------------------------------------------- l'intro en images (maquettes intro_telephone.png)
    // L'illustration en haut (vraies images, Scenes.kt), puis les 5 points des étapes, le titre, le texte, et ce qu'il
    // faut taper ; l'invite de commande du téléphone reste en dessous (TerminalActivity). Sans les images (assets
    // absents) : les anciens dessins en pixels (dessinerEcranAncien, dessinerOeufAncien).
    /** La hauteur (dp) que l'intro peut prendre au-dessus de l'invite (TerminalActivity) ; 0 : pas de limite. */
    @Volatile var hauteurMax = 0f
    const val NB_ETAPES = 5
    const val BLANC = 0xFFF0F0F5.toInt()
    const val GRIS = 0xFFC8C9D4.toInt()
    const val FOND2 = 0xFF0B0D12.toInt()
    const val TRAIT = 0xFF262A36.toInt()
    const val VERT2 = 0xFF5FD787.toInt()
    const val JAUNE2 = 0xFFFFD75F.toInt()

    /** La hauteur de l'illustration : presque carrée (maquette), plus petite s'il faut laisser la place au texte. */
    private fun hIllu(l: Float, hTexte: Float): Float {
        var h = l * 0.95f
        if (hauteurMax > 0f) h = minOf(h, hauteurMax - hTexte)
        return if (h < 110f) 0f else h
    }

    /** Une illustration recadrée (cover) dans (0, 0, l, h) ; renvoie (x, y) d'origine → (x, y) à l'écran. */
    private fun illustration(p: Peintre, img: Carte.Pix, l: Float, h: Float, posx: Float, version: Int = 0): (Float, Float) -> Pair<Float, Float> {
        val e = maxOf(l / img.w, h / img.h)
        val cw = l / e
        val ch = h / e
        val x0 = (img.w - cw) * posx
        val y0 = (img.h - ch) / 2
        p.image(img, x0.toInt(), y0.toInt(), cw.toInt(), ch.toInt(), 0f, 0f, l, h, true, version)
        val s = img.w / Scenes.taille().first
        return { x, y -> (x * s - x0) * e to (y * s - y0) * e }
    }

    private fun points(p: Peintre, n: Int, l: Float, y: Float) {
        val larg = (NB_ETAPES - 1) * 12f + 22f
        var x = l / 2 - larg / 2
        for (k in 1..NB_ETAPES) {
            val w = if (k == n) 18f else 6f
            p.rect(x, y, w, 6f, if (k == n) Carte.VERT else 0xFF333645.toInt())
            x += w + 6f
        }
    }

    /** Le camp de base dessiné au moment m (endormi, qui se réveille, l'œuf qui arrive, qui éclot, le bébé). */
    fun dessinerCamp(p: Peintre, jeu: Jeu, m: Scenes.Moment, l: Float, h: Float) {
        if (h <= 0f) return
        val posx = Scenes.cadrage(jeu, m)
        val img = when (m.phase) {
            "dort" -> Scenes.image("camp_dort")
            "eveil" -> Scenes.eveil(m.te)
            else -> Scenes.image("camp")
        } ?: return
        val vers = illustration(p, img, l, h, posx, if (m.phase == "eveil") (m.te * 30).toInt() else 0)
        val c = Scenes.camp()
        val e = vers(1f, 0f).first - vers(0f, 0f).first           // dp par pixel d'origine
        if (m.phase == "eveil") {
            for ((x, y, f) in Scenes.lumieres(m.te)) {
                val (X, Y) = vers(x, y)
                val a = (f * 230).toInt().coerceIn(0, 255)
                p.lueur(X, Y, 70f * e + 8f, (a shl 24) or 0x5CFF95)
                p.lueur(X, Y, 16f * e + 3f, (a shl 24) or 0xFFFFFF)
            }
            return
        }
        if (m.phase == "dort") return
        val ty = Oeufs.typeDe(jeu)
        val o = c.optJSONObject("oeuf") ?: org.json.JSONObject()
        val (nx, ny) = (c.optJSONArray("nid")?.let { it.optDouble(0).toFloat() to it.optDouble(1).toFloat() } ?: (760f to 545f))
        val ox = o.optDouble("x", 545.0).toFloat(); val oy = o.optDouble("y", 196.0).toFloat(); val cote = o.optDouble("cote", 430.0).toFloat()
        if (m.phase == "ne" || m.phase == "fondu") {
            // la coquille se dissout en pixels verts qui s'envolent ; le bébé apparaît en fondu digital au même endroit ;
            // à la fin, seul le bébé reste dans le nid
            val f = if (m.phase == "fondu") m.f else 1f
            val b = c.optJSONObject("bebe") ?: org.json.JSONObject()
            val (bx, by) = vers(b.optDouble("x", 762.0).toFloat(), b.optDouble("bas", 612.0).toFloat())
            val bh = b.optDouble("haut", 330.0).toFloat() * e
            p.lueur(bx, by - bh * 0.55f, bh * 1.2f, ((0x73 * f).toInt() shl 24) or 0xFFF096)
            if (m.phase == "fondu") {
                p.lueur(bx, by - bh * 0.5f, bh * 0.95f, (((0.75f - 0.55f * f) * 255).toInt() shl 24) or 0x5CFF95)
                val sc = minOf(1f, f / Scenes.FIN_COQUILLE)
                val coq = if (sc < 1f) Scenes.oeuf(ty, m)?.first else null
                if (coq != null) {
                    val d = Scenes.dissoudre(coq, sc, maxOf(1, coq.w / 52))
                    val (X, Y) = vers(ox, oy)
                    val ech = cote * e / coq.h
                    p.image(d, 0, 0, d.w, d.h, X, Y - (d.h - coq.h) * ech, d.w * ech, d.h * ech, false, m.k * 1000 + (sc * 999).toInt())
                }
            }
            val fb = if (m.phase == "fondu") ((f - Scenes.DEBUT_BEBE) / (1 - Scenes.DEBUT_BEBE)).coerceIn(0f, 1f) else 1f
            val bp = if (m.phase == "fondu") p.bebePix() else null
            if (bp != null) {
                val w = bh * bp.w / maxOf(1, bp.h)
                val grain = maxOf(1, bp.h / 34)                   // des « pixels » de fondu bien visibles
                p.image(Scenes.fondu(bp, fb, m.k, grain), 0, 0, bp.w, bp.h, bx - w / 2, by - bh, w, bh, false, m.k * 1000 + (fb * 999).toInt() + 7)
            } else if (m.phase == "ne") p.bebe(bx, by, bh)
            if (m.phase == "fondu") return
            val etincelles = listOf(-170 to -230, 150 to -250, 210 to -120, -230 to -90, 60 to -300, -60 to -280)
            for ((j, dd) in etincelles.withIndex()) {
                val vis = ((m.k / 3 + j) % 3) != 0
                if (!vis) continue
                val (X, Y) = vers(b.optDouble("x", 762.0).toFloat() + dd.first, b.optDouble("bas", 612.0).toFloat() - 60f + dd.second)
                val r = (if (j % 2 == 1) 10f else 14f) * e + 2f
                p.lueur(X, Y, r * 2.2f, 0xCCFFD75F.toInt())
                p.rect(X - r / 2, Y - r / 2, r, r, 0xFFFFF7A0.toInt())
            }
            return
        }
        val (oeuf, _) = Scenes.oeuf(ty, m) ?: return
        val (gx, gy) = vers(nx, ny - 60f)
        val (X, Y) = vers(ox, oy)
        when {
            m.phase == "telech" -> p.lueur(gx, gy, 150f * e, 0x595CFF95)
            m.phase == "eclot" && m.k >= Scenes.OUVERT - 1 ->               // la coquille éclate : un éclair blanc
                p.lueur(gx, gy - 60f * e, 330f * e, if (m.k < Scenes.OUVERT + 1) 0xF2FFFFE6.toInt() else 0x99FFFAD2.toInt())
            else -> p.lueur(gx, gy - 40f * e, 260f * e, if (m.phase == "eclat") 0xB3FFF5B4.toInt() else 0x80FFF096.toInt())
        }
        p.image(oeuf, 0, 0, oeuf.w, oeuf.h, X, Y, cote * e, cote * e, false, if (m.phase == "telech") m.k else 0)
    }

    /** La boîte « réception de l'œuf… 37 % » et sa barre, en bas de l'illustration. */
    private fun reception(p: Peintre, pct: Float, l: Float, h: Float) {
        val x = MARGE; val w = l - 2 * MARGE; val y = h - 54f
        p.rect(x, y, w, 42f, 0x595CFF95)
        p.rect(x + 1f, y + 1f, w - 2f, 40f, 0xE6050709.toInt())
        p.texte(t("intro.recoit", "pct" to pct.toInt()), x + 12f, y + 17f, 12f, JAUNE2, mono = true, gras = true)
        p.rect(x + 12f, y + 26f, w - 24f, 6f, 0xFF1D3326.toInt())
        val f = (w - 24f) * pct / 100f
        if (f > 0) { p.lueur(x + 12f + f, y + 29f, 14f, 0x995CFF95.toInt()); p.rect(x + 12f, y + 26f, f, 6f, Carte.VERT) }
    }

    /** Titre (blanc, gras) puis texte (gris) sous l'illustration ; renvoie le y suivant. mesure seulement si !dessin. */
    private fun titreTexte(p: Peintre, titre: List<String>, texte: List<String>, y0: Float, dessin: Boolean): Float {
        var y = y0
        for (x in titre) { if (dessin) p.texte(x, MARGE, y + 17f, 17f, BLANC, gras = true); y += 23f }
        y += 4f
        for (x in texte) { if (dessin) Carte.texteVert(p, x, MARGE, y + 13f, 13f, GRIS); y += 19f }
        return y
    }

    /** Un écran du début (n de 1 à total) : l'illustration, les points, le titre, le texte, Passer / Suivant. */
    fun dessinerEcran(p: Peintre, n: Int, total: Int, l: Float): Rendu {
        val ecr = d().optJSONArray("ecrans")?.optJSONObject(n - 1)
        val nomImg = ecr?.optString("image") ?: ""
        val img = if (nomImg.isNotEmpty()) Scenes.image(nomImg) else null
        if (img == null) return dessinerEcranAncien(p, n, total, l)
        val titre = couper(p, t("intro.e.titre.$n"), l - 2 * MARGE, 17f, gras = true)
        val dernier = n >= total
        val texte = couper(p, t("intro.e.texte.$n") + if (dernier) " " + t("intro.e.texte.oeuf") else "", l - 2 * MARGE, 13f)
        val nom = if (dernier) couper(p, t("intro.nom.tel"), l - 2 * MARGE, 13.5f, gras = true) else emptyList()
        val hTexte = 14f + 6f + 14f + titre.size * 23f + 4f + texte.size * 19f + nom.size * 20f + 14f + (if (dernier) 0f else 46f) + MARGE
        val hI = hIllu(l, hTexte)
        val h = hI + hTexte
        p.rect(0f, 0f, l, h, FOND2)
        if (hI > 0) {
            illustration(p, img, l, hI, if (nomImg == "camp_dort") 0.12f else 0.5f)
            p.rect(0f, hI, l, 1f, TRAIT)
        }
        var y = hI + 14f
        points(p, n, l, y)
        y = titreTexte(p, titre, texte, y + 20f, true)
        y += 4f
        for (x in nom) { p.texte(x, MARGE, y + 13.5f, 13.5f, Carte.VERT, gras = true); y += 20f }
        y += 10f
        val boutons = mutableListOf<Bouton>()
        if (!dernier) {
            boutons.add(bouton(p, t("intro.passer"), MARGE, y, false, "passer"))
            val s = t("intro.suivant")
            boutons.add(bouton(p, s, l - MARGE - (p.mesure(s, 13f, gras = true) + 26f), y, true, "suivant"))
        }
        return Rendu(l, h, boutons)
    }

    /** « Un œuf Plante ! Il sent bon l'herbe… » → (« Un œuf Plante ! », « Il sent bon l'herbe… ») (comme sur PC). */
    fun titreType(ty: String): Pair<String, String> {
        val x = t("intro.type.$ty")
        val m = Regex("[!！]\\s*").find(x)
        if (m == null || m.range.last + 1 >= x.length) return t("intro.oeuf.titre", "type" to Guide.nomType(ty)) to x
        return x.substring(0, m.range.last + 1).trim() to x.substring(m.range.last + 1).trim()
    }

    /** Le titre et le texte de l'étape (3 : le camp, 4 : l'œuf qui arrive, 5 : né) et le numéro de l'étape. */
    fun etape(jeu: Jeu, m: Scenes.Moment): Triple<Int, String, String> = when (m.phase) {
        "dort" -> Triple(3, t("intro.e.titre.3"), t("intro.camp.dort"))
        "eveil" -> Triple(3, t("intro.e.titre.3"), t("intro.eveil"))
        "ne" -> Triple(5, t("intro.merci.titre", "nom" to jeu.nom), t("intro.merci", "nom" to jeu.nom))
        "eclot", "fondu" -> Triple(5, titreType(Oeufs.typeDe(jeu)).first, "✓ " + t("intro.eclot", "n" to liste().size, "total" to liste().size))
        else -> titreType(Oeufs.typeDe(jeu)).let { (a, b) -> Triple(4, a, b + " " + t("intro.nourris")) }
    }

    /**
     * L'écran de l'œuf (étapes 3 et 4) : le camp (endormi, qui se réveille, l'œuf qui arrive « en téléchargement »),
     * la barre de réception, les points, le titre et le texte de l'étape, la liste en petit (✓ fait, ○ à faire),
     * l'astuce du moment. image : l'ancienne image d'animation (seulement sans les illustrations).
     */
    fun dessinerOeuf(p: Peintre, jeu: Jeu, l: Float, image: Carte.Pix? = null, quand: Long = System.currentTimeMillis()): Rendu {
        if (!Scenes.disponible()) return dessinerOeufAncien(p, jeu, l, image)
        val m = Scenes.moment(jeu, quand)
        val (n, titre0, texte0) = etape(jeu, m)
        val lt = l - 2 * MARGE
        val titre = couper(p, titre0, lt, 17f, gras = true)
        val texte = couper(p, texte0, lt, 13f)
        val f = faits(jeu)
        val items = liste().map { (if (it.id in f) "✓ " else "○ ") + commandeDe(it) }
        val lignesListe = mutableListOf<MutableList<Int>>(mutableListOf())
        var cur = 0f
        for ((k, s) in items.withIndex()) {
            val w = p.mesure(s, 11.5f, mono = true) + 16f
            if (cur + w > lt - 20f && lignesListe.last().isNotEmpty()) { lignesListe.add(mutableListOf()); cur = 0f }
            lignesListe.last().add(k); cur += w
        }
        val ast = couper(p, astuce(jeu), lt - 20f, 12f)
        val ou = if (m.phase == "dort") couper(p, t("intro.ou.tel"), lt - 20f, 11.5f) else emptyList()
        val hListe = 10f + 17f + lignesListe.size * 18f + 6f + ast.size * 16f + (if (ou.isEmpty()) 0f else 4f + ou.size * 15f) + 8f
        val hTexte = 14f + 6f + 14f + titre.size * 23f + 4f + texte.size * 19f + 10f + hListe + 6f
        val hI = hIllu(l, hTexte)
        val h = hI + hTexte
        p.rect(0f, 0f, l, h, FOND2)
        dessinerCamp(p, jeu, m, l, hI)
        if (hI > 0) {
            if (m.phase == "telech" || m.phase == "eclat") reception(p, m.pct, l, hI)
            p.rect(0f, hI, l, 1f, TRAIT)
        }
        var y = hI + 14f
        points(p, n, l, y)
        y = titreTexte(p, titre, texte, y + 20f, true) + 10f
        // la liste, comme une petite fenêtre de terminal
        p.rect(MARGE, y, lt, hListe, TRAIT)
        p.rect(MARGE + 1f, y + 1f, lt - 2f, hListe - 2f, 0xFF090B0F.toInt())
        var yy = y + 10f
        p.texte(titreListe(jeu), MARGE + 10f, yy + 11.5f, 11.5f, Carte.DOUX, mono = true); yy += 17f
        for (ligne in lignesListe) {
            var x = MARGE + 10f
            for (k in ligne) {
                val fait = liste()[k].id in f
                p.texte(items[k], x, yy + 11.5f, 11.5f, if (fait) VERT2 else Carte.DOUX, mono = true)
                x += p.mesure(items[k], 11.5f, mono = true) + 16f
            }
            yy += 18f
        }
        yy += 6f
        for (x in ast) { Carte.texteVert(p, x, MARGE + 10f, yy + 12f, 12f, Carte.AMBRE); yy += 16f }
        if (ou.isNotEmpty()) { yy += 4f; for (x in ou) { p.texte(x, MARGE + 10f, yy + 11.5f, 11.5f, Carte.DOUX); yy += 15f } }
        return Rendu(l, h, emptyList())
    }

    /** L'étape 5 : le camp où le bébé vient d'éclore (merci), puis le récapitulatif et « où sommes-nous » (merci2). */
    fun dessinerMerci(p: Peintre, jeu: Jeu, cid: String, l: Float, chemin: String, quand: Long): Rendu {
        val lt = l - 2 * MARGE
        val m = Scenes.moment(jeu, quand)
        val avecImage = cid == "merci"
        // « … est né ! » seulement quand le bébé est là (après le fondu) ; avant : l'œuf qui éclot
        val (titre0, paras0) = if (avecImage && m.phase != "ne") etape(jeu, m).let { it.second to listOf(it.third) }
            else if (avecImage) t("intro.merci.titre", "nom" to jeu.nom) to listOf(t("intro.merci", "nom" to jeu.nom))
            else t("intro.ici.titre") to (listOf(t("intro.recap")) + liste().map { t("intro.r.${it.id}") } +
                listOf(t("intro.ici", "chemin" to chemin), t("intro.suite", "chapitre" to t("hist.reveil.titre"))))
        val titre = couper(p, titre0, lt, 17f, gras = true)
        val paras = paras0.map { couper(p, it, lt, 13f) }
        val hParas = paras.sumOf { it.size } * 19f + paras.size * 6f
        val hTexte = 14f + 6f + 14f + titre.size * 23f + 4f + hParas + 10f + 40f + MARGE
        val hI = if (avecImage) hIllu(l, hTexte) else 0f
        val h = hI + hTexte
        p.rect(0f, 0f, l, h, FOND2)
        if (hI > 0) {
            dessinerCamp(p, jeu, m, l, hI)
            p.rect(0f, hI, l, 1f, TRAIT)
        }
        var y = hI + 14f
        points(p, NB_ETAPES, l, y)
        y += 20f
        for (x in titre) { p.texte(x, MARGE, y + 17f, 17f, BLANC, gras = true); y += 23f }
        y += 4f
        for (para in paras) { for (x in para) { Carte.texteVert(p, x, MARGE, y + 13f, 13f, GRIS); y += 19f }; y += 6f }
        y += 4f
        val s = t("intro.suivant")
        p.rect(MARGE, y, lt, 38f, 0x805CFF95.toInt())
        p.rect(MARGE + 1f, y + 1f, lt - 2f, 36f, 0xFF143323.toInt())
        p.texte(s, l / 2 - p.mesure(s, 14f, gras = true) / 2, y + 24f, 14f, Carte.VERT, gras = true)
        return Rendu(l, h, listOf(Bouton(MARGE, y, lt, 38f, "ok")))
    }

    /** Vrai tant que l'écran de l'intro bouge (la vue se redessine) ; le délai conseillé avant l'image suivante (ms). */
    fun prochaineImage(jeu: Jeu, mode: String, quand: Long = System.currentTimeMillis()): Long? {
        if (!Scenes.disponible() || !jeu.existe) return null
        if (mode != "oeuf" && mode != "merci") return null
        val m = Scenes.moment(jeu, quand)
        return when (m.phase) {
            "dort" -> null
            "eveil", "eclat", "eclot", "fondu" -> 33L
            "telech" -> 50L
            else -> if (m.te < 8f) 80L else null
        }
    }
}
