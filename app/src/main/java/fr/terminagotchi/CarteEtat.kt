package fr.terminagotchi

/**
 * Ce qui vit dans la carte du téléphone (sans rien d'Android, testé sur la JVM : tests/jvm/Reveil.kt), comme
 * Espace._reveil* sur PC (pc/tg/espace.py) : le modèle de CarteDessin, la file des animations (un biome qui se réveille,
 * un lieu qui s'allume, un chemin qui se dessine : une à la fois, « effets : aucun » = aucune), l'événement rare du jour
 * (noté dans le carnet quand on le voit), la météo des dernières commandes, les touchers (fiche, Y aller, livre, zoom).
 * ecrire : TerminalActivity écrit la commande dans la saisie (sans la lancer).
 */
class CarteEtat(private val jeu: Jeu) {
    val m = CarteDessin.Modele()
    var ecrire: ((String) -> Unit)? = null
    var dire: ((String) -> Unit)? = null
    private val file = ArrayDeque<CarteDessin.Anim>()
    private var finSig: String? = null
    private val cmds = mutableListOf<Pair<String, Double>>()
    private var meteo: Pair<String, Double>? = null
    private val albums = HashMap<String, Poses.Album?>()
    private var evtDit: String? = null
    var effets = "tous"

    private fun maintenant() = System.currentTimeMillis() / 1000.0

    private fun album(esp: String): Poses.Album? = albums.getOrPut(esp) {
        try { Bestiaire.espece(esp)?.let { Poses.albumEspece(it, "enfant", false) } } catch (e: Exception) { null }
    }

    fun photo(sig: String, quand: String, sais: String) = "reveil:$sig:$quand:$sais"

    /** Après chaque commande (et à l'ouverture) : relire la partie. heure et mois : ceux de l'appareil. */
    fun rafraichir(heure: Int = java.util.Calendar.getInstance().get(java.util.Calendar.HOUR_OF_DAY),
                   mois: Int = java.util.Calendar.getInstance().get(java.util.Calendar.MONTH) + 1) {
        if (!jeu.existe) return
        val e = try { Reveil.etat(jeu) } catch (x: Exception) { return }
        val sig = Reveil.signature(e)
        val quand = Reveil.moment(heure); val sais = Reveil.saison(mois)
        val (W, H) = Reveil.taille()
        m.moment = quand; m.saison = sais
        m.photo = photo(sig, quand, sais)
        m.lieux = Reveil.lieuxCarte(jeu, e, Reveil.iciRel(jeu))
        m.chemins = Reveil.cheminsCarte(e)
        m.secrets = Reveil.secretsCarte(jeu)
        m.habitants = Reveil.habitantsCarte(jeu).map { h ->
            CarteDessin.HabitantVu(h, Bestiaire.espece(h.espece)?.nom ?: h.espece, Quetes.texte(jeu, h.id), album(h.espece))
        }
        m.gardiens = Reveil.gardiens()
        m.gardAlbums = m.gardiens.associate { it.second to album(it.second) }
        m.livreOuverts = Reveil.livreOuverts(jeu)
        m.livreFichier = Histoire.ouvert(jeu, "temps") || Histoire.fini(jeu, "temps")
        val r = Reveil.r(jeu)
        m.carnetVus = r.getJSONArray("evts").let { a -> (0 until a.length()).map { a.optString(it) } }
        val p = Maison.pieceDe(jeu)
        m.iciLieu = Reveil.lieuDePiece(p)
        val pieces = Reveil.zones().optJSONObject("pieces")
        val pp = if (p != null && m.iciLieu == null) pieces?.optJSONArray(p) else null
        m.iciPiece = pp?.let { (it.getDouble(0).toFloat() / W) to (it.getDouble(1).toFloat() / H) }
        m.iciNom = p?.let { Langue.ou("esp.biome_long.$it", it) } ?: ""
        val cc = Histoire.chapitreCourant(jeu)
        val cp = cc?.piece?.let { pieces?.optJSONArray(it) }
        m.enCours = if (cc != null && cp != null && cc.piece != p) Histoire.nomChapitre(cc.id) to ((cp.getDouble(0).toFloat() / W) to (cp.getDouble(1).toFloat() / H)) else null
        // l'événement rare du jour : noté dans le carnet quand on le voit
        val ev = Reveil.evenement(jeu)
        m.evt = ev
        if (ev != null && evtDit != ev.optString("id")) {
            val eid = ev.optString("id")
            evtDit = eid
            Reveil.noterEvenement(jeu, eid)
            jeu.sauver()
            dire?.invoke(t("reveil.evt.annonce", "nom" to t("reveil.evt.$eid")) + " " + t("reveil.evt.$eid.dit"))
        }
        nouveautes(e, sig, quand, sais, r.optString("carte", "").ifEmpty { null })
    }

    /** Ce qui a changé depuis la dernière carte vue : la file des animations. */
    private fun nouveautes(e: Reveil.Etat, sig: String, quand: String, sais: String, vu: String?) {
        if (m.anim != null || file.isNotEmpty() || vu == sig) return
        if (effets == "aucun") { noter(sig); return }
        val avant = if (vu != null) Reveil.depuisSignature(vu) else Reveil.Etat(emptyList(), Reveil.lieux().associateWith { if (it == "camp") Reveil.ALLUME else Reveil.FERME }, emptyList())
        val nouveaux = e.biomes.filter { it !in avant.biomes }
        if (vu == null && nouveaux.isEmpty()) { noter(sig); return }
        val curB = avant.biomes.toMutableList()
        val curL = LinkedHashMap(avant.lieux)
        fun ph() = photo(Reveil.signature(Reveil.Etat(curB, curL, emptyList())), quand, sais)
        val (W, H) = Reveil.taille()
        if (vu == null || nouveaux.size > 2) {
            file.add(CarteDessin.Anim("resume", ph(), m.photo, Reveil.coeur("racine"), t("reveil.anim.resume"), 3.0))
        } else {
            for (b in nouveaux) {
                val av = ph(); curB.add(b)
                file.add(CarteDessin.Anim("biome", av, ph(), Reveil.coeur(b),
                    if (b == "racine") t("reveil.racine.anim") else t("reveil.biome.anim", "biome" to Reveil.nomBiome(b), "n" to curB.count { it != "racine" }, "total" to Reveil.NB_BIOMES), 2.6))
            }
            val ch = Reveil.zones().optJSONObject("chemins")
            for ((l, v) in e.lieux) {
                if (v <= (curL[l] ?: Reveil.FERME)) continue
                val av = ph(); curL[l] = v
                val el = Reveil.lieu(l).getJSONArray("ellipse")
                file.add(CarteDessin.Anim("lieu", av, ph(), (el.getDouble(0).toFloat() / W) to (el.getDouble(1).toFloat() / H), t("reveil.lieu.dit", "lieu" to Reveil.nomLieu(l)), 1.2))
                val pts = ch?.optJSONArray(l)
                if (v == Reveil.LANTERNE && pts != null) {
                    val ps = (0 until pts.length()).map { pts.getJSONArray(it).getDouble(0).toFloat() / W to pts.getJSONArray(it).getDouble(1).toFloat() / H }
                    file.add(CarteDessin.Anim("chemin", ph(), ph(), ps[0], t("reveil.chemin.dit", "lieu" to Reveil.nomLieu(l)), 2.0, l, ps))
                }
            }
        }
        if (file.isEmpty()) noter(sig) else finSig = sig
    }

    private fun noter(sig: String) { Reveil.noterCarte(jeu, sig); jeu.sauver() }

    /** Une commande tapée (la météo de la carte). */
    fun commande(ligne: String) { cmds.add(ligne to maintenant()); while (cmds.size > 10) cmds.removeAt(0) }

    /** Le temps passe (t : l'horloge de la vue) ; visible : l'onglet Carte est montré. */
    fun tick(t: Double, visible: Boolean) {
        m.t = t
        meteo = Reveil.meteo(cmds, maintenant(), meteo)
        m.meteo = meteo?.first ?: "calme"
        val an = m.anim
        if (an != null && t - an.t0 >= an.duree) m.anim = null
        if (m.anim == null && file.isNotEmpty() && visible) m.anim = file.removeFirst().also { it.t0 = t }
        else if (m.anim == null && file.isEmpty() && finSig != null) { noter(finSig!!); finSig = null }
        m.p = m.anim?.let { ((t - it.t0) / it.duree).toFloat().coerceIn(0f, 1f) } ?: 0f
    }

    /** Un biome s'est réveillé : la carte veut être montrée (TerminalActivity / EspaceEtat ouvre l'onglet). */
    fun veutEtreVue() = file.any { it.type == "biome" || it.type == "resume" }

    fun toucher(a: String): Boolean {
        when {
            a == "rv:passer" -> { m.anim = null; file.clear() }
            a == "rv:rien" || a == "rv:carte" -> {}
            a == "rv:fermer" -> { m.fiche = null; m.livre = false; m.carnet = false; m.livrePage = null; m.plus = false }
            a == "rv:plus" -> m.plus = !m.plus
            a == "rv:livre" -> { m.fiche = null; m.carnet = false; m.livre = true; m.livrePage = null }
            a.startsWith("rv:livre:") -> { m.livre = true; m.livrePage = a.substringAfterLast(':').toIntOrNull()?.takeIf { it > 0 } }
            a == "rv:carnet" -> { m.fiche = null; m.livre = false; m.carnet = true }
            a == "rv:zoom+" -> m.zoom = minOf(3f, m.zoom * 1.4f)
            a == "rv:zoom-" -> m.zoom = maxOf(1f, m.zoom / 1.4f)
            a.startsWith("rv:hab:") -> { m.fiche = "hab:" + a.removePrefix("rv:hab:"); m.livre = false; m.carnet = false }
            a.startsWith("rv:lieu:") -> { m.fiche = a.removePrefix("rv:lieu:"); m.plus = false; m.livre = false; m.carnet = false }
            a.startsWith("rv:aller:") -> {
                val l = m.lieux.firstOrNull { it.id == a.removePrefix("rv:aller:") }
                val c = l?.cmd
                if (c != null) { ecrire?.invoke(c); m.fiche = null }
            }
            else -> return false
        }
        return true
    }

    /** Un doigt fait glisser la carte (dx, dy en pixels de l'écran ; largeur w de la carte). */
    fun glisser(dx: Float, dy: Float, w: Float) {
        val iw = w * m.zoom
        m.cx = (m.cx - dx / iw).coerceIn(0f, 1f)
        m.cy = (m.cy - dy / (iw * 540f / 960f)).coerceIn(0f, 1f)
    }
}
