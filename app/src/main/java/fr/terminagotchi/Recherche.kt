package fr.terminagotchi

import java.text.Normalizer

/**
 * « cherche supprimer un dossier » : la créature trouve la commande ou la suite de commandes.
 * Aucune IA en ligne : synonymes + racines de mots + score, 100 % hors ligne.
 */
object Recherche {
    /**
     * Une entrée : son titre, ses étapes (commande, explication), et de quoi la retrouver.
     * Les textes sont des clés de langue : on cherche dans le français (toujours) et dans la langue choisie.
     */
    private class Entree(private val titreCle: String?, val etapes: List<Pair<String, String?>>, val kwCle: String?, val noms: Set<String>,
                         private val imageCle: String? = null, val mot: Mot? = null) {
        val titre: String get() = mot?.technique ?: t(titreCle!!)
        val image: String? get() = mot?.image ?: imageCle?.let { t(it) }
        fun explication(i: Int): String = etapes[i].second?.let { t(it) } ?: ""
        /** les textes où chercher, en français et dans la langue choisie */
        fun textes(): List<String> {
            val codes = setOf(Langue.DEFAUT, Langue.courante)
            if (mot != null) return codes.flatMap { mot.textes(it) }
            return codes.flatMap { c -> listOfNotNull(titreCle, kwCle, imageCle).mapNotNull { Langue.brut(it, c)?.toString() } +
                etapes.mapNotNull { e -> e.second?.let { Langue.brut(it, c)?.toString() } } }
        }
    }

    private val SYNONYMES = mapOf(
        "dossier" to "dossier repertoire folder rep",
        "fichier" to "fichier file document doc texte txt",
        "creer" to "creer cree creation fabriquer nouveau nouvelle generer construire",
        "supprimer" to "supprimer supprime effacer efface enlever detruire delete virer jeter",
        "voir" to "voir afficher affiche lister liste montrer regarder",
        "copier" to "copier copie dupliquer duplique",
        "sauvegarde" to "sauvegarde sauvegarder backup",
        "deplacer" to "deplacer deplace bouger ranger move",
        "renommer" to "renommer renomme",
        "chercher" to "chercher cherche trouver trouve rechercher recherche retrouver",
        "lire" to "lire ouvrir lecture",
        "proteger" to "proteger protege verrouiller bloquer securiser",
        "droit" to "droit droits permission acces",
        "internet" to "internet reseau connexion web wifi",
        "processus" to "processus programme tache tourne",
        "espace" to "espace stockage memoire place",
        "taille" to "taille poids gros lourd",
        "aller" to "aller entrer changer naviguer",
        "remonter" to "remonter revenir retour arriere parent",
        "ou" to "ou position emplacement actuel courant",
        "qui" to "qui utilisateur compte",
        "heure" to "heure date jour",
        "application" to "application appli applis app logiciel",
        "lancer" to "lancer demarrer executer",
        "telephone" to "telephone appeler appel numero",
        "sms" to "sms texto",
        "message" to "message envoyer partager",
        "carte" to "carte cartes map itineraire gps lieu",
        "lampe" to "lampe torche flash lumiere",
        "batterie" to "batterie charge",
        "parler" to "parler voix",
        "vibrer" to "vibrer vibration vibreur",
        "reglage" to "reglage reglages parametre parametres",
        "compter" to "compter compte nombre combien",
        "trier" to "trier trie ordre alphabetique",
        "commande" to "commande raccourci alias fonction",
        "script" to "script automatiser recette",
        "repeter" to "repeter boucle plusieurs fois",
        "cache" to "cache caches cachee invisible secret",
        "jouer" to "jouer jeu jeux amuser",
        "donjon" to "donjon aventure quete",
        "drapeau" to "drapeau ctf hacker securite",
        "bestiole" to "bestiole bestioles capturer capture collection",
        "modifier" to "modifier editer changer",
    )
    private val STOP = ("le la les l un une des de du d pour comment je j veux voudrais faire fais mon ma mes " +
        "ton ta tes son sa ses a au aux et en sur dans quel quelle est ce c que qu il y on me m te t se s avec " +
        "par plus peux peut dois faut ca cela the an of to in on my me i want how do can is it").split(" ").toSet()

    private val CJK = Regex("[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\uf900-\ufaff]")

    /**
     * Mots en minuscules sans accents (comme pc/tg/registre.py) : les accents sont retirés seulement sur l'alphabet
     * latin, grec ou cyrillique (en hindi, bengali, ourdou ou arabe, les signes font partie des lettres) ;
     * pour le chinois et le japonais (pas d'espaces) : chaque caractère et chaque paire de caractères.
     */
    fun mots(t: String): List<String> {
        val n = Normalizer.normalize(t.lowercase(), Normalizer.Form.NFD)
        val sb = StringBuilder()
        var prec = 0
        var i = 0
        while (i < n.length) {
            val cp = n.codePointAt(i)
            val type = Character.getType(cp)
            val marque = type == Character.NON_SPACING_MARK.toInt() || type == Character.COMBINING_SPACING_MARK.toInt() ||
                type == Character.ENCLOSING_MARK.toInt()
            if (!(type == Character.NON_SPACING_MARK.toInt() && prec != 0 && prec < 0x530)) {
                if (marque || Character.isLetterOrDigit(cp) || cp == '_'.code) sb.appendCodePoint(cp) else sb.append(' ')
            }
            if (!marque) prec = cp
            i += Character.charCount(cp)
        }
        val out = mutableListOf<String>()
        for (m in sb.toString().split(' ').filter { it.isNotEmpty() }) {
            if (CJK.containsMatchIn(m)) {
                val car = m.filter { CJK.matches(it.toString()) }.map { it.toString() }
                out += car
                out += car.zipWithNext { x, y -> x + y }
                out += CJK.replace(m, " ").split(' ').filter { it.isNotEmpty() }
            } else out += m
        }
        return out
    }

    private fun racine(m: String): String {
        var x = m
        if (x.length > 3 && (x.endsWith("s") || x.endsWith("x"))) x = x.dropLast(1)
        return x.take(6)
    }

    private val RACINE_CONCEPT: Map<String, String> = HashMap<String, String>().apply {
        for ((canon, variantes) in SYNONYMES) for (v in variantes.split(" ")) for (m in mots(v)) putIfAbsent(racine(m), canon)
    }

    fun concepts(t: String): Set<String> =
        mots(t).filter { it !in STOP }.map { RACINE_CONCEPT[racine(it)] ?: racine(it) }.toSet()

    /** Une commande : clé de sa description, clé de ses mots-clés, clé de son image (la maison). */
    private fun cmd(c: String, descCle: String, kwCle: String, imageCle: String? = null) =
        Entree(descCle, listOf(c to null), kwCle, setOf(c.split(" ").first()), imageCle)

    private fun image(c: String) = Regles.LEXIQUE.firstOrNull { it.cmd == c.split(" ").first() }?.image

    private fun recette(titreCle: String, kwCle: String, vararg etapes: Pair<String, String>) =
        Entree(titreCle, etapes.toList(), kwCle, emptySet())

    private val ENTREES: List<Entree> by lazy {
        Regles.LEXIQUE.map { m -> Entree(null, listOf(m.cmd to null), null, setOf(m.cmd), mot = m) } + listOf(
            cmd("ls -a", "rech.ls_a", "rech.ls_a.kw", "rech.ls_a.img"),
            cmd("cd ..", "rech.cd_parent", "rech.cd_parent.kw", "rech.cd_parent.img"),
            cmd("rm -r dossier", "rech.rm_r", "rech.rm_r.kw",
                "rech.rm_r.img"),
            cmd("ls | wc -l", "rech.compter", "rech.compter.kw",
                "rech.compter.img"),
            recette("reg.r.creer_dossier_entrer", "rech.r.dossier.kw",
                "mkdir projet" to "reg.r.creer_dossier_entrer.0", "cd projet" to "reg.r.creer_dossier_entrer.1"),
            recette("reg.r.renommer_fichier_securite", "rech.r.renommer.kw",
                "ls" to "rech.r.renommer.1", "mv ancien.txt nouveau.txt" to "rech.r.renommer.2",
                "ls" to "rech.verifie"),
            recette("reg.r.faire_sauvegarde_avant", "rech.r.sauvegarde.kw",
                "cp fichier.txt fichier.txt.bak" to "reg.r.faire_sauvegarde_avant.0", "edite fichier.txt" to "rech.r.sauvegarde.2"),
            recette("reg.r.supprimer_dossier_sans", "rech.r.supprimer.kw",
                "ls dossier" to "rech.r.supprimer.1", "rm -r dossier" to "rech.r.supprimer.2",
                "ls" to "rech.verifie"),
            recette("reg.r.retrouver_fichier_perdu", "reg.r.retrouver_fichier_perdu.kw",
                "find ~ -name \"*nom*\"" to "rech.r.retrouver.1", "cat chemin/trouvé" to "rech.r.retrouver.2"),
            recette("reg.r.proteger_fichier_important", "rech.r.proteger.kw",
                "chmod 444 fichier" to "rech.r.proteger.1", "ls -l fichier" to "rech.r.proteger.2"),
            recette("reg.r.lancer_appli_dont", "rech.r.appli.kw",
                "applis" to "lex.applis.t", "ouvre nom" to "rech.r.appli.2"),
            recette("rech.r.message", "rech.r.message.kw",
                "partage Coucou !" to "rech.r.message.1", "sms 0612345678 coucou" to "rech.r.message.2"),
            recette("rech.r.commande", "reg.creer_propre_commande_raccourci.kw",
                "echo 'salut() { echo Salut !; }' >> ~/.tgrc" to "rech.r.commande.1", "salut" to "rech.r.commande.2"),
            recette("reg.r.creer_lancer_script", "rech.r.script.kw",
                "echo 'echo Bonjour' > script.sh" to "reg.r.creer_lancer_script.0", "sh script.sh" to "reg.r.creer_lancer_script.2"),
            recette("rech.r.aventure", "rech.r.aventure.kw",
                "donjon" to "rech.r.aventure.1", "plan" to "rech.r.aventure.2", "quetes" to "rech.r.aventure.3"),
            recette("rech.r.ctf", "rech.r.ctf.kw",
                "ctf" to "rech.r.ctf.1", "cd ~/terrain_terminagotchi/ctf" to "rech.r.ctf.2",
                "drapeau TG{…}" to "rech.r.ctf.3"),
            recette("rech.r.capturer", "rech.r.capturer.kw",
                "ls -a" to "rech.r.capturer.1", "cat .bestiole_…" to "rech.r.capturer.2",
                "mv .bestiole_… ../nid/" to "rech.r.capturer.3"),
            recette("rech.r.niveau", "rech.r.niveau.kw",
                "doom" to "rech.r.niveau.1", "edite ~/terrain_terminagotchi/jeu/carte.txt" to "rech.r.niveau.2",
                "doom" to "rech.r.niveau.3"),
        )
    }

    /** Les concepts d'une entrée, calculés une fois par langue. */
    private val index = HashMap<Pair<Int, String>, Set<String>>()
    private fun cles(i: Int, e: Entree): Set<String> = synchronized(index) {
        index.getOrPut(i to Langue.courante) { concepts(e.textes().joinToString(" ")) }
    }

    fun chercher(requete: String): String {
        val q = requete.trim().lowercase()
        if (q.isEmpty()) return t("rech.exemple")
        val premier = q.split(" ").first()
        val qc = concepts(q)
        val scores = ENTREES.mapIndexed { i, e ->
            var s = 0.0
            if (premier in e.noms) {
                s = 100.0 - i * 0.01
            } else if (qc.isNotEmpty()) {
                val ec = cles(i, e)
                val commun = (qc intersect ec).size
                if (commun > 0) {
                    s = commun * 10.0 - (ec - qc).size * 0.5
                    if (ec.containsAll(qc)) s += 5
                    if (e.etapes.size > 1 && commun >= 2) s += 4
                }
            }
            s to e
        }.filter { it.first > 0 }.sortedByDescending { it.first }
        if (scores.isEmpty()) return t("rech.rien")
        val seuil = scores.first().first * 0.5
        val sb = StringBuilder()
        for ((s, e) in scores.take(3)) {
            if (s < seuil) continue
            if (e.etapes.size == 1) {
                sb.append("• ${e.titre}\n   ➜ `${Regles.piege(e.etapes[0].first)}`\n")
                (e.image ?: image(e.etapes[0].first))?.takeIf { it != e.titre }?.let { sb.append("   🏠 $it\n") }
            } else {
                sb.append("• " + t("reg.recette", "titre" to e.titre) + "\n")
                e.etapes.forEachIndexed { i, (c, _) -> sb.append("   ${i + 1}. `${Regles.piege(c)}`   (${e.explication(i)})\n") }
            }
        }
        sb.append(t("rech.tape"))
        return sb.toString()
    }
}
