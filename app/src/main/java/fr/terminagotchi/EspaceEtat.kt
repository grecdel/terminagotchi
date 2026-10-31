package fr.terminagotchi

/**
 * Ce qui vit dans l'espace de travail du téléphone, sans rien d'Android (testé sur la JVM : tests/jvm/Espace.kt) :
 * la créature du bureau (BureauVie : respiration, clignements, poses), son cerveau (Cerveau.kt) qui choisit sa pose,
 * l'île et ses événements, la vue déployée de la dernière commande (Deploie.kt), et le modèle que dessine
 * EspaceDessin. EspaceVue (la View) s'occupe seulement du temps, du dessin et des touchers.
 */
class EspaceEtat(private val jeu: Jeu, private val dossier: () -> java.io.File, private val chemin: () -> String) {
    val modele = EspaceDessin.Modele()
    val cerveau = Cerveau.Vivant()
    val creature = BureauVie.Creature(600f, surPlace = true)
    val ile = BureauVie.Ile()
    private var resume: BureauVie.Resume? = null
    var tourCerveau = -1e9
    private var album: Poses.Album? = null
    private var cleAlbum = ""
    private var avant: Map<String, Double>? = null
    private var totalAvant = -1

    var classe: Boolean
        get() = modele.classe
        set(v) { modele.classe = v; modele.zoom = if (v) 1.3f else 1f }

    /** Après chaque commande (et à l'ouverture) : relire le jeu. code : le code de sortie de la dernière commande. */
    fun rafraichir(code: Int?, maintenant: Double) {
        if (!jeu.existe) return
        val m = modele
        m.nom = jeu.nom
        m.especeStade = Regles.espece(jeu.stade, jeu.forme, jeu.especeCompagnon)
        val p = Maison.pieceDe(jeu)
        m.lieuChip = if (!p.isNullOrEmpty()) "$p · " + Langue.ou("esp.biome.$p", p) else ""
        m.ici = p?.takeIf { it in EspaceDessin.LIEUX_CARTE }
        m.iciNom = p?.let { Langue.ou("esp.biome_long.$it", it) } ?: ""
        m.cwd = chemin()
        // les envies (et ce que la dernière commande a donné)
        val vals = try { Envies.valeurs(jeu) } catch (e: Exception) { emptyMap() }
        val av = avant ?: vals
        m.envies = Envies.ENVIES.map { k -> Triple(Envies.nom(k), k, (vals[k] ?: 0.0) to ((vals[k] ?: 0.0) - (av[k] ?: 0.0) > 0.4)) }
        if (jeu.total != totalAvant) {
            m.gains = if (avant == null) "" else Envies.ENVIES.map { k -> (vals[k] ?: 0.0) - (av[k] ?: 0.0) to k }
                .sortedByDescending { it.first }.take(2).filter { it.first >= 0.5 }
                .joinToString(" · ") { Envies.nom(it.second).lowercase() + " +" + Math.round(it.first) }
            avant = vals
            totalAvant = jeu.total
        }
        // l'album de la créature et de l'équipe
        val cle = "${jeu.especeCompagnon}/${jeu.stade}/${jeu.shiny}"
        if (cle != cleAlbum) { album = try { Poses.album(jeu) } catch (e: Exception) { album }; cleAlbum = cle }
        m.album = album
        // le cerveau relit le jeu (une commande tapée, ratée), et l'île annonce les événements
        val sig = cerveau.lireJeu(jeu, code)
        if (sig["commande_tapee"] == true) {
            cerveau.tour(sig, maintenant)
            tourCerveau = maintenant
            creature.reagir("mange")
        }
        val statut = when (cerveau.etat) { "mange" -> "mange"; "dort" -> "dort"; "faim" -> "faim"; else -> "pret" }
        val eq = mutableListOf(EspaceDessin.Membre(album, jeu.nom, m.especeStade, statut, true))
        try {
            val caps = Explo.captures(jeu)
            for (i in maxOf(0, caps.length() - 4) until caps.length()) {
                val c = caps.optJSONObject(i) ?: continue
                val e = Bestiaire.espece(c.optString("espece")) ?: continue
                val st = c.optString("stade", "bebe").ifEmpty { "bebe" }
                val al = try { Poses.albumEspece(e, st, c.optBoolean("shiny")) } catch (x: Exception) { null }
                eq.add(EspaceDessin.Membre(al, c.optString("nom").ifEmpty { e.nom }, e.nom + " · " + Equipe.nomStade(st), "pret", false))
            }
        } catch (e: Exception) { }
        m.equipe = eq
        // les lieux de la carte
        val lieux = HashMap<String, Pair<String, String>>()
        for (piece in Maison.PIECES) {
            if (!java.io.File(jeu.terrain, piece).isDirectory) continue
            val mq = try { Maison.marques(jeu, piece) } catch (e: Exception) { "" }
            lieux[piece] = Langue.ou("esp.biome.$piece", piece) to when {
                "✓" in mq -> "reveille"; "▶" in mq -> "en_cours"; else -> "brume"
            }
        }
        m.lieux = lieux
        m.cerveau = cerveau
        val r = BureauVie.Resume(jeu.total, jeu.lecon, jeu.etape, jeu.faim, jeu.module("dressage").has("en_cours"))
        for (k in BureauVie.evenements(resume, r)) { ile.annoncer(t(k)); break }
        resume = r
        apparence(maintenant)
    }

    // ------------------------------------------------------------ l'apparence (thème, interface évolutive, rangement)
    val arrivees = HashMap<String, Double>()
    var rangement = false
    var options = false
    /** la petite question des grands (avant « Tout afficher ») : TerminalActivity lit la réponse dans le terminal */
    var question: Pair<String, String>? = null
    var bulleNeuve: String? = null

    fun apparence(maintenant: Double) {
        val m = modele
        m.theme = Apparence.theme(jeu)
        val vis = Apparence.visibles(jeu)
        m.onglets = Apparence.onglets(jeu)
        if (m.onglet !in m.onglets) m.onglet = "terminal"
        m.ordreOnglets = Apparence.ordreOnglets(jeu)
        m.bandes = Apparence.bandes(jeu).filter { it.id != "deploie" || "deploie" in vis }
        m.caches = Apparence.caches(jeu).filter { it != "deploie" || "deploie" in vis }
        m.envies_visibles = "envies" in vis
        if ("equipe" !in vis) m.equipe = emptyList()
        m.dispo = Apparence.nomDisposition(jeu)
        m.tout = Apparence.a(jeu).optBoolean("tout")
        m.mienne = Apparence.a(jeu).has("mienne")
        val neufs = Apparence.prendreAnnonces(jeu)
        for (n in neufs) arrivees[n] = maintenant
        if (neufs.isNotEmpty()) {
            bulleNeuve = t("app.pan.${neufs.last()}.dit")
            ile.annoncer(bulleNeuve!!)
            creature.reagir("salut")
            val de = Apparence.d().getJSONObject("telephone").getJSONObject("onglet_de")
            m.onglets.firstOrNull { de.optString(it, "") in neufs }?.let { m.onglet = it }
            jeu.sauver()
        }
    }

    /** La vue déployée d'une ligne (les lignes des tuyaux : calculer(), à part, car elles lancent des commandes sûres). */
    fun deployer(ligne: String, auto: Boolean = true): Deploie.Vue? {
        val dos = dossier()
        val v = Deploie.vue(ligne, existe(dos), auto) ?: return null
        if (modele.vue?.auto == false) v.auto = false
        v.lieu = v.blocs.firstOrNull { it.g == "chemin" }?.let { Deploie.lieu(jeu, it, dos) }
        modele.vue = v
        return v
    }

    fun existe(dos: java.io.File): (String) -> Boolean = { n -> try { java.io.File(dos, n).exists() } catch (e: Exception) { false } }

    /** Ce qui passe dans les tuyaux de v (un shell à part, dans le même dossier). */
    fun calculer(v: Deploie.Vue) {
        val dos = dossier()
        val s = try {
            val sh = Shell(jeu.home).also { it.dossier = dos }
            Deploie.flux(v.ligne, { sh.executer(it) }, existe(dos))
        } catch (e: Exception) { null }
        v.sorties = s
    }

    /** Le temps passe (dt secondes) : la créature, l'île, la vue déployée, un tour du cerveau toutes les PAS s. */
    fun tick(dt: Double, maintenant: Double) {
        creature.tick(dt)
        ile.tick(dt)
        modele.vue?.avancer(dt)
        if (maintenant - tourCerveau >= cerveau.PAS) {
            cerveau.tour(cerveau.lireJeu(jeu, null), maintenant)
            tourCerveau = maintenant
        }
        poser()
    }

    /** La pose de la créature suit son cerveau (sinon : elle respire, cligne, s'étire). */
    private fun poser() {
        val voulu = cerveau.pose()
        val c = creature
        if (voulu == "dort") { if (c.etat != "dort") c.dormir(); return }
        if (c.etat == "dort") { c.reagir("etire"); return }
        if (voulu != "assis" && c.etat != voulu && (c.etat == "assis" || c.tEtat > c.duree)) c.changer(voulu, cerveau.PAS)
    }

    /** Juste avant de dessiner : ce qui bouge à chaque image. */
    fun preparer(maintenant: Double) {
        val m = modele
        m.t = maintenant
        m.arrivees = arrivees.mapValues { maintenant - it.value }.filterValues { it < EspaceDessin.ARRIVEE }
        m.rangement = rangement
        m.options = options
        m.etat = cerveau.etat
        m.anime = BureauVie.animer(creature)
        m.mini = BureauVie.miniVie(creature, maintenant)
        m.evenement = if (ile.etat == "evenement") ile.evenement else null
    }

    /** Un toucher sur une zone du dessin. Renvoie vrai si la hauteur peut changer (onglet). */
    fun toucher(a: String): Boolean {
        if (a.startsWith("rg:") || a.startsWith("opt:")) { reglerApparence(a); return true }
        when {
            a.startsWith("onglet:") -> { modele.onglet = a.substringAfter(":"); return true }
            a.startsWith("forcer:") -> {
                val et = a.substringAfter(":")
                cerveau.forcer(if (cerveau.force == et) null else et)
                tourCerveau = -1e9
            }
            a == "dep:suivant" -> modele.vue?.let { v -> if (v.auto) v.auto = false; v.suivant() }
            a == "creature" -> creature.reagir("coeur")
            a == "ile" -> ile.fermer()
            a.startsWith("equipe:") -> { modele.onglet = "equipe"; return true }
        }
        return false
    }

    /** Les touches du mode rangement et des options. Renvoie la question des grands à poser, s'il y en a une. */
    fun reglerApparence(a: String) {
        val p = a.split(":")
        when {
            a == "rg:fini" -> rangement = false
            a == "rg:origine" -> Apparence.origine(jeu)
            a == "rg:mienne" -> { Apparence.enregistrerMienne(jeu); ile.annoncer(t("esp.rg.enregistree")) }
            a.startsWith("rg:taille:") -> Apparence.tailler(jeu, p[2], p[3])
            a.startsWith("rg:cacher:") -> Apparence.cacher(jeu, p[2], true)
            a.startsWith("rg:remettre:") -> Apparence.cacher(jeu, p[2], false)
            a.startsWith("rg:onglet:") -> Apparence.avancerOnglet(jeu, p[2])
            a.startsWith("rg:dispo:") -> Apparence.choisirDisposition(jeu, p[2])
            a == "opt:fermer" -> options = false
            a.startsWith("opt:theme:") -> Apparence.choisirTheme(jeu, p[2])
            a.startsWith("opt:dispo:") -> Apparence.choisirDisposition(jeu, p[2])
            a == "opt:ranger" -> { options = false; rangement = true }
            a == "opt:tout" -> if (Apparence.a(jeu).optBoolean("tout")) Apparence.toutAfficher(jeu, false)
                else { question = Apparence.questionAdulte(); options = false }
            else -> return
        }
        jeu.sauver()
        apparence(modele.t)
    }

    /** Une bande tenue (appui long) puis lâchée à la place i. */
    fun deplacerBande(id: String, i: Int) { Apparence.deplacer(jeu, id, i); jeu.sauver(); apparence(modele.t) }
}
