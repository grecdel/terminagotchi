package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Un onglet du terminal : un terminal à lui (son dossier courant, son `cd -`, son code de sortie, son historique ↑ ↓,
 * son écran et ce qui était à moitié tapé), sur le même terrain de jeu et avec la même créature que les autres.
 */
class Onglet(val numero: Int, val shell: Shell, historique: List<String>) {
    /** l'historique de CET onglet (↑ ↓) : au départ, celui de la partie (comme un nouveau bash lit ~/.bash_history) */
    val historique: MutableList<String> = historique.takeLast(Onglets.MAX_HISTO).toMutableList()
    /** ce qu'affichait son écran, gardé quand on passe à un autre onglet */
    var ecran: CharSequence = ""
    /** la ligne à moitié tapée quand on est parti */
    var brouillon: String = ""
    /** la fenêtre d'observation : la pièce et ce qu'il y avait dedans à la dernière commande de CET onglet */
    var dernierDossier: File? = null
    var derniersNoms: Set<String> = emptySet()

    /** Une ligne tapée (Entrée comprise) pendant qu'une commande tournait encore : lancée juste après, telle quelle. */
    class Attente(val ligne: String, val colle: Boolean, val rappel: Boolean)

    /** les lignes mises de côté dans CET onglet, dans l'ordre où elles ont été tapées */
    val attente: ArrayDeque<Attente> = ArrayDeque()

    /** Met une ligne de côté ; faux s'il y en a déjà [Onglets.MAX_ATTENTE] (on n'en empile pas sans fin). */
    fun mettreDeCote(ligne: String, colle: Boolean = false, rappel: Boolean = false): Boolean {
        if (ligne.isBlank() || attente.size >= Onglets.MAX_ATTENTE) return false
        attente.addLast(Attente(ligne.trim(), colle, rappel))
        return true
    }

    /** La prochaine ligne à lancer (la plus ancienne), ou null. */
    fun prochaineAttente(): Attente? = attente.removeFirstOrNull()

    /** « Terminal 1 », « Terminal 2 »… (dans la langue de la partie) */
    fun nom(): String = t("ong.nom", "n" to numero)

    /** Une ligne tapée dans cet onglet (pas deux fois de suite la même, 50 au plus). */
    fun noter(ligne: String) {
        if (ligne.isEmpty() || historique.lastOrNull() == ligne) return
        historique.add(ligne)
        while (historique.size > Onglets.MAX_HISTO) historique.removeAt(0)
    }
}

/**
 * Les onglets du terminal de l'appli (comme plusieurs fenêtres de terminal sur PC : `tg terminal`, la touche [t],
 * `terminal` dans l'espace). Chaque onglet est un terminal indépendant ; la créature mange les commandes de tous,
 * et les leçons voient chaque commande avec le dossier de SON onglet (TerminalActivity passe `actif.shell.dossier`).
 *
 * Comme sur le téléphone chaque ligne a déjà son propre petit terminal (les variables et les tâches `&` s'arrêtent
 * à la fin de la ligne, voir Shell.kt et Garde.kt), un onglet garde ce qu'un terminal garde d'une ligne à l'autre :
 * son dossier, d'où il vient (`cd -`), son code de sortie (`$?` des étapes) et son historique.
 * Le dernier onglet ne se ferme pas (`exit` y referme le jeu, comme avant les onglets) ; [MAX] onglets au plus.
 */
class Onglets(private val creerShell: () -> Shell, private val historiquePartie: () -> List<String> = { emptyList() }) {
    companion object {
        /** assez pour « un terminal qui travaille, un qui regarde » sans perdre un enfant dans les onglets */
        const val MAX = 4
        const val MAX_HISTO = 50
        /** lignes tapées d'avance pendant qu'une commande tourne (au-delà : « attends un peu ») */
        const val MAX_ATTENTE = 5
    }

    /** dans l'ordre des numéros (Terminal 1, 2, 3…) */
    val liste = mutableListOf<Onglet>()
    var actif: Onglet
        private set

    init {
        actif = creer()
        liste.add(actif)
    }

    /** le plus petit numéro libre : fermer Terminal 2 puis en rouvrir un redonne « Terminal 2 » */
    private fun creer(): Onglet = Onglet((1..MAX + 1).first { k -> liste.none { it.numero == k } }, creerShell(), historiquePartie())

    fun plein(): Boolean = liste.size >= MAX

    /** Ouvre un onglet de plus et y va ; null s'il y en a déjà [MAX]. */
    fun ouvrir(): Onglet? {
        if (plein()) return null
        val o = creer()
        liste.add(o)
        liste.sortBy { it.numero }
        actif = o
        return o
    }

    /** Va sur cet onglet. */
    fun choisir(o: Onglet) {
        if (o in liste) actif = o
    }

    /** Ferme cet onglet (et va sur son voisin de gauche) ; faux si c'est le dernier : il reste ouvert. */
    fun fermer(o: Onglet = actif): Boolean {
        if (liste.size <= 1 || o !in liste) return false
        val i = liste.indexOf(o)
        liste.remove(o)
        if (actif === o) actif = liste[maxOf(0, i - 1)]
        return true
    }

    /**
     * Ce qu'il faut garder quand Android recrée l'écran (téléphone tourné, mode sombre changé, appli mise de côté puis
     * rouverte après avoir été arrêtée par le téléphone) : pour chaque onglet, son numéro, son dossier, d'où il vient
     * (`cd -`), son code de sortie, son historique et sa ligne à moitié tapée ; et l'onglet affiché. Les écrans (texte en
     * couleurs) sont gardés à part par TerminalActivity ; les lignes en attente ne sont pas gardées (la commande qui
     * tournait s'est arrêtée avec l'ancien écran).
     */
    fun etat(): String {
        val a = JSONArray()
        for (o in liste) {
            a.put(JSONObject()
                .put("n", o.numero)
                .put("dossier", o.shell.dossier.path)
                .put("precedent", o.shell.precedent?.path ?: "")
                .put("code", o.shell.code)
                .put("historique", JSONArray(o.historique.takeLast(MAX_HISTO)))
                .put("brouillon", o.brouillon))
        }
        return JSONObject().put("onglets", a).put("actif", actif.numero).toString()
    }

    /**
     * Remet les onglets gardés par [etat] (après une recréation de l'écran). Un dossier qui n'existe plus, ou qui n'est
     * pas dans le camp de base [home], redevient le camp ; un texte abîmé ne change rien (faux : on garde un onglet).
     */
    fun reprendre(texte: String?, home: File): Boolean {
        if (texte.isNullOrEmpty()) return false
        val o = try { JSONObject(texte) } catch (e: Exception) { return false }
        val a = o.optJSONArray("onglets") ?: return false
        val camp = try { home.canonicalFile } catch (e: Exception) { home }
        fun dansLeCamp(chemin: String): File? {
            if (chemin.isEmpty()) return null
            val f = try { File(chemin).canonicalFile } catch (e: Exception) { return null }
            return if (f.isDirectory && (f == camp || f.path.startsWith(camp.path + File.separator))) f else null
        }
        val repris = mutableListOf<Onglet>()
        for (i in 0 until a.length()) {
            val x = a.optJSONObject(i) ?: continue
            val n = x.optInt("n")
            if (n !in 1..MAX || repris.any { it.numero == n } || repris.size >= MAX) continue
            val h = x.optJSONArray("historique")
            val histo = if (h == null) historiquePartie() else (0 until h.length()).map { h.optString(it) }.filter { it.isNotEmpty() }
            val og = Onglet(n, creerShell(), histo)
            og.shell.dossier = dansLeCamp(x.optString("dossier")) ?: og.shell.dossier
            og.shell.precedent = dansLeCamp(x.optString("precedent"))
            og.shell.code = x.optInt("code")
            og.brouillon = x.optString("brouillon").take(500)
            repris.add(og)
        }
        if (repris.isEmpty()) return false
        repris.sortBy { it.numero }
        liste.clear()
        liste.addAll(repris)
        actif = liste.firstOrNull { it.numero == o.optInt("actif") } ?: liste[0]
        return true
    }

    /** Une autre partie est chargée : chaque onglet revient au camp de base, avec l'historique de cette partie. */
    fun nouvellePartie(home: File) {
        for (o in liste) {
            o.shell.dossier = home
            o.shell.precedent = null
            o.shell.code = 0
            o.historique.clear()
            o.historique.addAll(historiquePartie().takeLast(MAX_HISTO))
            o.dernierDossier = null
            o.derniersNoms = emptySet()
            o.attente.clear()
        }
    }
}
