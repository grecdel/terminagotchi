package fr.terminagotchi

import org.json.JSONObject
import kotlin.math.ceil
import kotlin.math.floor

/**
 * Le guide (portage de pc/tg/guide.py, mêmes règles) : la bestiole qui accompagne l'enfant. Au début, c'est le
 * compagnon sorti de l'œuf ; ensuite, la bestiole que l'enfant met en tête de son équipe (`guide <nom>`,
 * `equipe guide <nom>` ou `troupe <nom>`). Quatre raisons d'en changer, jamais un piège ni une punition :
 *  1. talents par type (TALENTS) : astuce de plus et +25 % d'XP dans les exercices de sa famille, +1 XP par
 *     commande de sa famille, une astuce en bulle au plus toutes les 15 minutes ; l'Ombre : « passages secrets » ;
 *  2. régions gardées (biome/<type>/) : entrer = une bestiole de ce type dans l'équipe ; agrandir (mkdir, touch,
 *     cp, mv, rm dans la région) = un GUIDE de ce type ; un message gentil, au plus toutes les 10 minutes ;
 *  3. combats à type (TABLE) : ×1.5 / ×0.67 sur tes coups, le monstre touche ±0.15 ; l'Ombre est forte contre
 *     tous la nuit ; l'épreuve du jour (typeDuJour) : guide fort contre ce type → +5 XP au défi éclair ;
 *  4. fatigue : +0.5 par commande pour le guide ; au-delà de 30, le sommeil et le jeu s'usent plus vite (jusqu'au
 *     double à 100) ; le banc repose (−20/h), le guide aussi quand on ne joue pas (−10/h après 10 min) ;
 *     « envie de sortir » (💭) après 2 jours sans guider, une bulle au plus toutes les 6 heures.
 * Le type d'une bestiole : biomes.json (copie de donnees/biomes.json). Le compagnon : type de sa forme, sinon
 * TYPES[somme des codes des lettres de son nom % 9], fixé une fois pour toutes.
 * Sauvegarde : jeu.module("guide") (dates en ms) ; une ancienne partie : le compagnon est le guide.
 * Tests : tests/jvm/Guide.kt.
 */
object Guide {
    val TYPES = listOf("feu", "eau", "glace", "plante", "roche", "ciel", "ombre", "machine", "poison")
    val ICONES = mapOf("feu" to "🔥", "eau" to "💧", "glace" to "🧊", "plante" to "🌿", "roche" to "🗻", "ciel" to "⚡",
        "ombre" to "🌙", "machine" to "🔩", "poison" to "🧪")
    val TALENTS = mapOf("ciel" to "explorateur", "plante" to "batisseur", "roche" to "demenageur", "feu" to "nettoyeur",
        "glace" to "lecteur", "poison" to "detective", "eau" to "plombier", "machine" to "cuisinier", "ombre" to "secrets")
    val CMDS_TALENT = mapOf(
        "explorateur" to setOf("cd", "ls", "pwd", "tree", "dir"),
        "batisseur" to setOf("mkdir", "md", "touch"),
        "demenageur" to setOf("cp", "mv", "copy", "move", "ren"),
        "nettoyeur" to setOf("rm", "rmdir", "rd", "del"),
        "lecteur" to setOf("cat", "head", "tail", "less", "more"),
        "detective" to setOf("grep", "find"),
        "cuisinier" to setOf("sh", "bash", "chmod", "zsh"))
    val AFFICHE_TALENT = mapOf("explorateur" to "cd ls pwd", "batisseur" to "mkdir touch", "demenageur" to "cp mv",
        "nettoyeur" to "rm rmdir", "lecteur" to "cat head tail", "detective" to "grep find", "plombier" to "| > >>",
        "cuisinier" to "sh chmod", "secrets" to "ls -a")
    val ASTUCES = mapOf("explorateur" to "cd -", "batisseur" to "mkdir -p a/b/c", "demenageur" to "cp -r",
        "nettoyeur" to "rm -i", "lecteur" to "head -n 3", "detective" to "grep -i", "plombier" to "ls | wc -l",
        "cuisinier" to "chmod +x", "secrets" to "ls -a")
    val TABLE = mapOf("feu" to listOf("plante", "glace"), "eau" to listOf("feu", "roche"), "plante" to listOf("eau", "roche"),
        "glace" to listOf("plante", "ciel"), "roche" to listOf("feu", "ciel"), "ciel" to listOf("eau", "machine"),
        "machine" to listOf("glace", "poison"), "poison" to listOf("plante", "eau"), "ombre" to emptyList())
    const val FORT = 1.5
    const val FAIBLE = 0.67
    const val BONUS_TALENT = 0.25
    const val BONUS_DEFI = 5
    val TYPE_BRANCHE = mapOf("Intelligence" to "machine", "Force" to "feu", "Agilité" to "ciel", "Endurance" to "roche")
    const val FATIGUE_COMMANDE = 0.5
    const val REPOS_BANC = 20.0
    const val REPOS_GUIDE = 10.0
    const val PAUSE = 600_000L
    const val FATIGUE_ALERTE = 70.0
    const val EN_FORME = 30.0
    const val FATIGUE_DELAI = 3_600_000L
    const val ASTUCE_DELAI = 15 * 60_000L
    const val SORTIE_APRES = 2 * 24 * 3_600_000L
    const val SORTIE_DELAI = 6 * 3_600_000L
    const val REGION_DELAI = 600_000L
    val CHANGE = setOf("mkdir", "md", "touch", "cp", "copy", "mv", "move", "rm", "rmdir", "rd", "del")
    private val SEP = Regex("\\s*(?:&&|\\|\\||;)\\s*")

    /** l'horloge en ms et la nuit (remplaçables par un test) */
    var maintenant: () -> Long = { System.currentTimeMillis() }
    var nuit: () -> Boolean = { java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY).let { it >= 20 || it < 7 } }

    // ---------------------------------------------------------------- les types (biomes.json)
    /** Lit assets/biomes.json (réglé par init ; les tests JVM donnent le texte). */
    @Volatile var chargeur: (() -> String?)? = null
    private var biomes: JSONObject? = null

    fun init(ctx: android.content.Context) {
        if (chargeur != null) return
        val app = ctx.applicationContext ?: ctx
        chargeur = { try { app.assets.open("biomes.json").bufferedReader().use { it.readText() } } catch (e: Exception) { null } }
    }

    private fun b(): JSONObject = biomes ?: (try { JSONObject(chargeur?.invoke() ?: "{}") } catch (e: Exception) { JSONObject() })
        .also { biomes = it }

    /** Le type d'une espèce dans une variante (même règle que donnees/verifier_biomes.py). */
    fun typeDe(e: Bestiaire.Espece?, variante: String = "classique"): String {
        if (e == null) return "eau"
        val d = b()
        if (variante.isNotEmpty() && variante != "classique") {
            val ts = d.optJSONArray("types")
            if (ts != null) for (i in 0 until ts.length()) {
                val x = ts.getJSONObject(i)
                val h = x.optJSONArray("habitats") ?: continue
                for (k in 0 until h.length()) if (h.optString(k) == variante) return x.optString("id")
            }
        }
        return d.optJSONObject("classique_par_espece")?.optString(e.id)?.ifEmpty { null }
            ?: d.optJSONObject("classique_par_famille")?.optString(e.famille)?.ifEmpty { null } ?: "eau"
    }

    fun typeInd(ind: JSONObject): String = typeDe(Bestiaire.espece(ind.optString("espece")), ind.optString("variante", "classique"))

    fun nomType(ty: String) = t("type.nom.$ty")
    fun etiquette(ty: String) = "${ICONES[ty]} ${nomType(ty)}"

    /** ×1.5, ×0.67 ou ×1 : la force du type att contre le type def. */
    fun efficacite(att: String, def: String, laNuit: Boolean? = null): Double {
        if (att == "ombre") return if ((laNuit ?: nuit()) && def != "ombre") FORT else 1.0
        if (def in (TABLE[att] ?: emptyList())) return FORT
        if (att in (TABLE[def] ?: emptyList())) return FAIBLE
        return 1.0
    }

    /** Les cœurs d'un coup avec la force du type (1 → 2, 2 → 3 si fort ; au moins 1 si faible). */
    fun degats(n: Int, mult: Double): Int = if (mult == 1.0) n else maxOf(1, floor(n * mult + 0.5).toInt())

    fun fortsContre(ty: String) = TYPES.filter { ty in (TABLE[it] ?: emptyList()) }

    fun typeDuJour(jour: java.time.LocalDate = java.time.LocalDate.now()): String = TYPES[Math.floorMod(jour.toEpochDay(), TYPES.size.toLong()).toInt()]

    // ---------------------------------------------------------------- l'état
    class Membre(val id: String, val nom: String, val type: String, val ind: JSONObject?)

    fun typeCompagnonInitial(nom: String, forme: String?): String =
        TYPE_BRANCHE[forme] ?: TYPES[nom.codePoints().toArray().sum() % TYPES.size]

    /** L'état du guide (une ancienne partie : le compagnon est le guide). */
    fun g(jeu: Jeu): JSONObject {
        val g = jeu.module("guide")
        val now = maintenant()
        if (!g.has("id")) g.put("id", "compagnon")
        for (k in listOf("fatigue", "depuis", "region_t")) if (g.optJSONObject(k) == null) g.put(k, JSONObject())
        if (!g.has("t")) g.put("t", now)
        if (!g.has("sortie_t")) g.put("sortie_t", now)
        if (!g.has("cree")) g.put("cree", now)
        if (g.optString("type_c") !in TYPES) g.put("type_c", typeCompagnonInitial(jeu.nom, jeu.forme))
        val id = g.optString("id")
        if (id != "compagnon" && capture(jeu, id) == null) g.put("id", "compagnon")      // la bestiole n'est plus là
        return g
    }

    private fun capture(jeu: Jeu, id: String): JSONObject? {
        val caps = Explo.captures(jeu)
        for (i in 0 until caps.length()) if (caps.getJSONObject(i).optString("id") == id) return caps.getJSONObject(i)
        return null
    }

    /** L'équipe : le compagnon d'abord, puis les bestioles (les plus récentes d'abord). */
    fun membres(jeu: Jeu): List<Membre> {
        val g = g(jeu)
        val out = mutableListOf(Membre("compagnon", jeu.nom, g.optString("type_c"), null))
        val caps = Explo.captures(jeu)
        for (i in caps.length() - 1 downTo 0) {
            val c = caps.getJSONObject(i)
            val e = Bestiaire.espece(c.optString("espece")) ?: continue
            out.add(Membre(c.optString("id"), e.nom, typeDe(e, c.optString("variante", "classique")), c))
        }
        return out
    }

    fun actuel(jeu: Jeu): Membre {
        val id = g(jeu).optString("id")
        val m = membres(jeu)
        return m.firstOrNull { it.id == id } ?: m[0]
    }

    fun typesEquipe(jeu: Jeu) = membres(jeu).map { it.type }.toSet()
    fun talent(jeu: Jeu) = TALENTS.getValue(actuel(jeu).type)

    /** On peut entrer dans la région ty : une bestiole de ce type est dans l'équipe. */
    fun regionOuverte(jeu: Jeu, ty: String) = ty in typesEquipe(jeu)

    /** On peut agrandir la région ty : le guide est de ce type. */
    fun peutAgrandir(jeu: Jeu, ty: String) = actuel(jeu).type == ty

    fun fatigue(jeu: Jeu, id: String? = null): Double {
        val g = g(jeu)
        return g.getJSONObject("fatigue").optDouble(id ?: g.optString("id"), 0.0)
    }

    private fun depuis(jeu: Jeu, m: Membre): Long {
        val d = g(jeu).getJSONObject("depuis")
        if (d.has(m.id)) return d.optLong(m.id)
        return m.ind?.optLong("date")?.takeIf { it > 0 } ?: g(jeu).optLong("cree", maintenant())
    }

    fun envieDeSortir(jeu: Jeu, m: Membre, now: Long = maintenant()) =
        m.id != g(jeu).optString("id") && now - depuis(jeu, m) >= SORTIE_APRES

    fun cmdGuide(nom: String? = null) = "guide " + (nom?.lowercase() ?: "<nom>")

    // ---------------------------------------------------------------- changer de guide
    private fun simple(s: String) = java.text.Normalizer.normalize(s.lowercase().trim(), java.text.Normalizer.Form.NFD)
        .replace(Regex("\\p{Mn}+"), "")

    fun trouver(jeu: Jeu, nom: String): Membre? {
        val n = simple(nom)
        if (n.isEmpty()) return null
        if (n == "compagnon" || n == simple(jeu.nom) || n == "0") return membres(jeu)[0]
        val e = Bestiaire.espece(nom) ?: return null
        return membres(jeu).drop(1).firstOrNull { it.nom == e.nom }
    }

    /** Met la bestiole nom en tête de l'équipe. Renvoie (texte, membre choisi s'il a changé). */
    fun choisir(jeu: Jeu, nom: String): Pair<String, Membre?> {
        val m = trouver(jeu, nom) ?: return t("guide.inconnu", "nom" to nom, "cmd" to "guide") to null
        val g = g(jeu)
        val avant = actuel(jeu)
        if (m.id == avant.id) return t("guide.deja", "nom" to m.nom) to null
        val now = maintenant()
        g.getJSONObject("depuis").put(avant.id, now).put(m.id, now)
        g.put("id", m.id).put("fatigue_dit", 0L)
        if (m.ind != null) jeu.module("equipe").put("active", m.id)   // le guide est aussi la bestiole active
        jeu.animer("salut")
        jeu.log("🐾 " + t("guide.change.log", "nom" to m.nom, "type" to nomType(m.type)))
        val tal = TALENTS.getValue(m.type)
        return (t("guide.change", "ancien" to avant.nom, "nom" to m.nom, "icone" to ICONES[m.type], "type" to nomType(m.type)) + "\n" +
            t("guide.change.talent", "talent" to t("guide.talent.$tal"), "aide" to aideTalent(tal))) to m
    }

    fun aideTalent(tal: String) = t(if (tal == "secrets") "guide.talent.secrets.aide" else "guide.talent.aide", "cmds" to AFFICHE_TALENT[tal])
    fun astuce(tal: String) = t("guide.astuce.$tal", "cmd" to ASTUCES[tal])

    /** `troupe <nom>` met aussi cette bestiole en tête : elle devient le guide. */
    fun suivreChoixEquipe(jeu: Jeu, id: String) {
        val g = g(jeu)
        if (g.optString("id") == id) return
        val now = maintenant()
        g.getJSONObject("depuis").put(g.optString("id"), now).put(id, now)
        g.put("id", id)
    }

    // ---------------------------------------------------------------- talents
    fun duTalent(tal: String, ligne: String): Boolean {
        if (tal == "plombier") return '|' in ligne || '>' in ligne
        for (m in ligne.trim().split(SEP).filter { it.isNotBlank() }) {
            val mot = Regles.premierMot(m)
            when (tal) {
                "secrets" -> if (Maison.voitCaches(m) || m.trim().split(Regex("\\s+")).drop(1).any {
                        it.startsWith(".") && it != "." && it != ".." && !it.startsWith("./") && !it.startsWith("../") }) return true
                "cuisinier" -> if (mot in CMDS_TALENT.getValue(tal) || m.trim().startsWith("./")) return true
                else -> if (mot in (CMDS_TALENT[tal] ?: emptySet())) return true
            }
        }
        return false
    }

    /** Une ligne d'astuce en plus dans un exercice de la famille du talent du guide (sinon null). */
    fun indiceExercice(jeu: Jeu, famille: String): String? {
        val m = actuel(jeu)
        if (TALENTS[m.type] != famille) return null
        return t("guide.ent.indice", "icone" to ICONES[m.type], "nom" to m.nom, "talent" to t("guide.talent.$famille"), "astuce" to astuce(famille))
    }

    /** +25 % d'XP sur un exercice de la famille du talent du guide : le texte, ou null. */
    fun bonusExercice(jeu: Jeu, famille: String, xp: Int): String? {
        val m = actuel(jeu)
        if (TALENTS[m.type] != famille) return null
        val n = maxOf(1, ceil(xp * BONUS_TALENT).toInt())
        jeu.ajouterXp(n)
        return t("guide.ent.bonus", "icone" to ICONES[m.type], "nom" to m.nom, "xp" to n)
    }

    // ---------------------------------------------------------------- combats et épreuve du jour
    /** Les types du combat : (type de ta bestiole, type du monstre, texte). */
    fun debutCombat(ind: JSONObject, monstre: String, variante: String): Triple<String, String, String> {
        val tm = typeInd(ind)
        val tl = typeDe(Bestiaire.espece(monstre), variante)
        val m = efficacite(tm, tl)
        val effet = when {
            m > 1 -> t("guide.combat.fort")
            efficacite(tl, tm) > 1 -> t("guide.combat.faible")
            else -> t("guide.combat.neutre")
        }
        var texte = t("guide.combat.types", "nom" to ind.optString("espece"), "type_moi" to etiquette(tm), "monstre" to monstre,
            "type_lui" to etiquette(tl), "effet" to effet)
        if (tm == "ombre" && m > 1) texte += " " + t("guide.combat.nuit")
        return Triple(tm, tl, texte)
    }

    /** Défi éclair réussi : si le guide est fort contre le type du jour, +5 XP. */
    fun apresDefi(jeu: Jeu): String? {
        val m = actuel(jeu)
        val ty = typeDuJour()
        if (efficacite(m.type, ty) <= 1) return null
        jeu.ajouterXp(BONUS_DEFI)
        val texte = t("guide.defi.bonus", "icone" to ICONES[m.type], "nom" to m.nom, "type" to nomType(ty), "xp" to BONUS_DEFI)
        jeu.log(texte)
        jeu.dire(texte, 8)
        return texte
    }

    fun annonceDefi(jeu: Jeu) {
        val ty = typeDuJour()
        jeu.dire(t("guide.defi.annonce", "type" to etiquette(ty), "forts" to fortsContre(ty).joinToString(", ") { etiquette(it) }), 12)
    }

    // ---------------------------------------------------------------- le tour de jeu
    /** En pleine forme (fatigue < 30) : rien ; ensuite l'usure du sommeil et du jeu grandit, jusqu'au double à 100. */
    fun usureEnPlus(f: Double) = maxOf(0.0, f - EN_FORME) / (100 - EN_FORME)

    private fun usure(jeu: Jeu, g: JSONObject, now: Long) {
        val dt = (now - g.optLong("t", now)).coerceIn(0L, 7 * 24 * 3_600_000L)
        g.put("t", now)
        if (dt <= 0) return
        val fat = g.getJSONObject("fatigue")
        for (m in membres(jeu)) {
            var f = fat.optDouble(m.id, 0.0)
            if (f == 0.0) continue
            if (m.id != g.optString("id")) f -= REPOS_BANC * dt / 3_600_000.0
            else {
                val debut = maxOf(now - dt, g.optLong("cmd_t") + PAUSE)
                if (now > debut) f -= REPOS_GUIDE * (now - debut) / 3_600_000.0
            }
            fat.put(m.id, Math.round(maxOf(0.0, f) * 1000) / 1000.0)
        }
    }

    private fun region(jeu: Jeu, ligne: String?, cwd: String?, g: JSONObject, now: Long): String? {
        val r = Maison.rel(jeu, cwd ?: Maison.ici(jeu)) ?: return null
        val parts = r.split("/")
        val ty = if (parts.size >= 2 && parts[0] == "biome" && parts[1] in TYPES) parts[1] else return null
        val rt = g.getJSONObject("region_t")
        if (now - rt.optLong(ty) < REGION_DELAI) return null
        val texte = when {
            !regionOuverte(jeu, ty) -> t("guide.region.fermee", "type" to etiquette(ty))
            !peutAgrandir(jeu, ty) && ligne != null && ligne.trim().split(SEP).any { Regles.premierMot(it) in CHANGE } -> {
                val qui = membres(jeu).firstOrNull { it.type == ty }
                t("guide.region.guide", "type" to etiquette(ty), "cmd" to cmdGuide(qui?.nom))
            }
            else -> return null
        }
        rt.put(ty, now)
        jeu.dire(texte, 12)
        return texte
    }

    /** Après chaque commande (Tour.apresCommande), après les envies. Renvoie un message à afficher, ou null. */
    fun apresCommande(jeu: Jeu, ligne: String?, ignoree: Boolean, cwd: java.io.File? = null): String? {
        if (!jeu.existe) return null
        val g = g(jeu)
        val now = maintenant()
        usure(jeu, g, now)
        val tapee = ligne != null && !ignoree && !Regles.estColle(ligne) && Regles.premierMot(ligne).isNotEmpty()
        val m = actuel(jeu)
        val tal = TALENTS.getValue(m.type)
        if (tapee) {
            g.put("cmd_t", now)
            val v = Envies.e(jeu).getJSONObject("v")
            var f = fatigue(jeu)
            for (k in listOf("sommeil", "jeu")) {
                val n = if (k == "sommeil" && Envies.soir()) Envies.SOMMEIL_SOIR else Envies.PAR_COMMANDE.getValue(k)
                v.put(k, maxOf(0.0, v.optDouble(k) - n * usureEnPlus(f)))
            }
            f = minOf(100.0, f + FATIGUE_COMMANDE)
            g.getJSONObject("fatigue").put(m.id, Math.round(f * 1000) / 1000.0)
            if (duTalent(tal, ligne!!)) {
                jeu.ajouterXp(1)
                if (now - g.optLong("astuce_t") >= ASTUCE_DELAI && Intro.ouvert(jeu, "equipe")) {
                    g.put("astuce_t", now)
                    jeu.dire("${ICONES[m.type]} ${m.nom} : " + astuce(tal), 10)
                }
            }
            val equipe = membres(jeu)
            if (f >= FATIGUE_ALERTE && now - g.optLong("fatigue_dit") >= FATIGUE_DELAI && equipe.size > 1) {
                g.put("fatigue_dit", now)
                jeu.dire(t("guide.fatigue.dit", "nom" to m.nom, "cmd" to cmdGuide()), 12)
            }
            if (equipe.size > 1 && !g.optBoolean("annonce")) {
                g.put("annonce", true)
                jeu.dire(t("guide.premiere", "cmd" to "guide", "cmd2" to cmdGuide()), 14)
            } else if (now - g.optLong("sortie_t") >= SORTIE_DELAI) {
                val veut = equipe.filter { envieDeSortir(jeu, it, now) }
                if (veut.isNotEmpty()) {
                    g.put("sortie_t", now)
                    val x = veut[((now / 1000) % veut.size).toInt()]
                    jeu.dire(t("guide.sortie.dit", "nom" to x.nom, "cmd" to cmdGuide(x.nom)), 12)
                }
            }
        }
        if (!Intro.ouvert(jeu, "biomes")) return null        // les régions gardées : après leur présentation (Intro.kt)
        return region(jeu, if (tapee) ligne else null, cwd?.path, g, now)
    }

    // ---------------------------------------------------------------- écrans
    fun barre(v: Double, n: Int = 8): String {
        val k = (v / 100 * n + 0.5).toInt().coerceIn(0, n)
        return "▰".repeat(k) + "▱".repeat(n - k)
    }

    fun etatFatigue(v: Double) = t(when { v < EN_FORME -> "guide.fatigue.repose"; v < FATIGUE_ALERTE -> "guide.fatigue.ok"; else -> "guide.fatigue.fatigue" })

    /** La ligne « 🧭 Guide : … » de l'écran d'équipe. */
    fun ligneEquipe(jeu: Jeu): String {
        val m = actuel(jeu)
        return t("guide.equipe", "icone" to ICONES[m.type], "nom" to m.nom, "type" to nomType(m.type), "cmd" to cmdGuide())
    }

    /** guide : le guide, son talent, sa fatigue, les régions ouvertes, l'épreuve du jour, l'équipe. */
    fun ecran(jeu: Jeu): String {
        val g = g(jeu)
        val m = actuel(jeu)
        val tal = TALENTS.getValue(m.type)
        val out = mutableListOf(t("guide.ecran.titre", "icone" to ICONES[m.type], "nom" to m.nom, "type" to nomType(m.type)), "",
            t("guide.ecran.talent", "talent" to t("guide.talent.$tal"), "aide" to aideTalent(tal)))
        val f = fatigue(jeu)
        out.add(t("guide.ecran.fatigue", "barre" to barre(f), "etat" to etatFatigue(f)))
        out.add(t("guide.ecran.regions", "liste" to TYPES.filter { regionOuverte(jeu, it) }.joinToString(" ") { ICONES.getValue(it) }))
        val ty = typeDuJour()
        out.add(t("guide.ecran.jour", "type" to etiquette(ty), "forts" to fortsContre(ty).joinToString(", ") { etiquette(it) }))
        out.add("")
        val now = maintenant()
        for (x in membres(jeu)) {
            val marque = if (x.id == g.optString("id")) "🧭" else "   "
            val sortie = if (envieDeSortir(jeu, x, now)) "  " + t("guide.ecran.sortir") else ""
            out.add("$marque ${ICONES[x.type]} ${x.nom} · ${nomType(x.type)} · ${t("guide.talent." + TALENTS[x.type])} · ${barre(fatigue(jeu, x.id), 5)}$sortie")
        }
        out.add("")
        out.add(t("guide.ecran.pied", "cmd" to cmdGuide(), "types" to "types"))
        return out.joinToString("\n")
    }

    /** types : la table des types expliquée aux enfants, et les talents. */
    fun ecranTypes(): String {
        val out = mutableListOf(t("types.titre"), t("types.intro"), "")
        for (ty in TYPES) if (ty != "ombre")
            out.add(t("types.ligne", "icone" to ICONES[ty], "type" to nomType(ty), "liste" to TABLE.getValue(ty).joinToString(", ") { etiquette(it) }))
        out.add(t("types.ombre"))
        out.add("")
        out.add(t("types.talents"))
        for (ty in TYPES) {
            val tal = TALENTS.getValue(ty)
            out.add("${ICONES[ty]} ${nomType(ty)} → ${t("guide.talent.$tal")} (${AFFICHE_TALENT[tal]})")
        }
        out.add("")
        out.add(t("types.pied", "cmd" to cmdGuide()))
        return out.joinToString("\n")
    }

    /** guide [nom] / equipe guide <nom> (Commandes.kt). */
    fun commande(jeu: Jeu, reste: String): String {
        if (reste.isBlank()) return ecran(jeu)
        val (texte, m) = choisir(jeu, reste)
        if (m?.ind != null) Combat.animTroupe = JSONObject(m.ind.toString()) to "salut"   // la petite animation du changement
        return texte
    }
}
