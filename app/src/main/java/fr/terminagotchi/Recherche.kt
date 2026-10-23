package fr.terminagotchi

import java.text.Normalizer

/**
 * « cherche supprimer un dossier » : la créature trouve la commande ou la suite de commandes.
 * Aucune IA en ligne : synonymes + racines de mots + score, 100 % hors ligne.
 */
object Recherche {
    private class Entree(val titre: String, val etapes: List<Pair<String, String>>, val cles: Set<String>, val noms: Set<String>)

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
        "par plus peux peut dois faut ca cela").split(" ").toSet()

    private fun mots(t: String): List<String> {
        val n = Normalizer.normalize(t.lowercase(), Normalizer.Form.NFD).replace(Regex("\\p{Mn}+"), "")
        return Regex("[a-z0-9]+").findAll(n).map { it.value }.toList()
    }

    private fun racine(m: String): String {
        var x = m
        if (x.length > 3 && (x.endsWith("s") || x.endsWith("x"))) x = x.dropLast(1)
        return x.take(6)
    }

    private val RACINE_CONCEPT: Map<String, String> = HashMap<String, String>().apply {
        for ((canon, variantes) in SYNONYMES) for (v in variantes.split(" ")) for (m in mots(v)) putIfAbsent(racine(m), canon)
    }

    private fun concepts(t: String): Set<String> =
        mots(t).filter { it !in STOP }.map { RACINE_CONCEPT[racine(it)] ?: racine(it) }.toSet()

    private fun cmd(c: String, desc: String, kw: String) =
        Entree(desc, listOf(c to ""), concepts("$desc $kw"), setOf(c.split(" ").first()))

    private fun recette(titre: String, kw: String, vararg etapes: Pair<String, String>) =
        Entree(titre, etapes.toList(), concepts("$titre $kw"), emptySet())

    private val ENTREES: List<Entree> by lazy {
        Regles.LEXIQUE.map { (c, desc, _) -> cmd(c, desc, "") } + listOf(
            cmd("ls -a", "voir les fichiers cachés", "cache invisible"),
            cmd("cd ..", "remonter au dossier parent", "revenir retour"),
            cmd("rm -r dossier", "supprimer un dossier et tout son contenu", "supprimer dossier tout"),
            cmd("ls | wc -l", "compter les fichiers d'un dossier", "compter combien"),
            recette("Créer un dossier et entrer dedans", "creer dossier entrer",
                "mkdir projet" to "crée le dossier", "cd projet" to "entre dedans"),
            recette("Renommer un fichier en sécurité", "renommer fichier",
                "ls" to "vérifie le nom exact (ou Tab)", "mv ancien.txt nouveau.txt" to "renomme", "ls" to "vérifie"),
            recette("Faire une sauvegarde avant de modifier", "copier sauvegarde",
                "cp fichier.txt fichier.txt.bak" to "copie de secours", "edite fichier.txt" to "modifie tranquillement"),
            recette("Supprimer un dossier sans faire de bêtise", "supprimer dossier securite",
                "ls dossier" to "regarde ce qu'il contient", "rm -r dossier" to "supprime (définitif !)", "ls" to "vérifie"),
            recette("Retrouver un fichier perdu et le lire", "chercher trouver fichier perdu lire",
                "find ~ -name \"*nom*\"" to "cherche partout chez toi", "cat chemin/trouvé" to "affiche-le"),
            recette("Protéger un fichier important", "proteger fichier",
                "chmod 444 fichier" to "lecture seule", "ls -l fichier" to "vérifie (r--r--r--)"),
            recette("Lancer une appli dont je ne connais pas le nom", "lancer ouvrir application trouver",
                "applis" to "liste tes applis", "ouvre nom" to "lance celle que tu veux"),
            recette("Envoyer un message à quelqu'un", "envoyer message sms whatsapp",
                "partage Coucou !" to "choisis WhatsApp, mail…", "sms 0612345678 coucou" to "ou prépare un SMS"),
            recette("Créer ma propre commande", "creer commande",
                "echo 'salut() { echo Salut !; }' >> ~/.tgrc" to "enregistre-la", "salut" to "utilise-la"),
            recette("Créer et lancer un script", "creer script lancer",
                "echo 'echo Bonjour' > script.sh" to "écris le script", "sh script.sh" to "lance-le"),
            recette("Partir à l'aventure", "jouer donjon aventure",
                "donjon" to "crée un donjon", "plan" to "regarde la carte", "quetes" to "lis tes quêtes"),
            recette("Jouer au hacker (capture the flag)", "jouer drapeau ctf hacker",
                "ctf" to "prépare les épreuves", "cd ~/terrain_terminagotchi/ctf" to "va les voir", "drapeau TG{…}" to "valide un drapeau"),
            recette("Capturer une bestiole", "capturer bestiole",
                "ls -a" to "trouve les fichiers cachés", "cat .bestiole_…" to "lis l'indice", "mv .bestiole_… ../nid/" to "ramène-la au nid"),
            recette("Créer mon propre niveau de jeu", "creer jeu niveau modifier",
                "doom" to "prépare l'atelier", "edite ~/terrain_terminagotchi/jeu/carte.txt" to "dessine", "doom" to "teste"),
        )
    }

    fun chercher(requete: String): String {
        val q = requete.trim().lowercase()
        if (q.isEmpty()) return "Exemple : cherche supprimer un dossier  (ou : cherche grep)"
        val premier = q.split(" ").first()
        val qc = concepts(q)
        val scores = ENTREES.mapIndexed { i, e ->
            var s = 0.0
            if (premier in e.noms) {
                s = 100.0 - i * 0.01
            } else if (qc.isNotEmpty()) {
                val commun = (qc intersect e.cles).size
                if (commun > 0) {
                    s = commun * 10.0 - (e.cles - qc).size * 0.5
                    if (e.cles.containsAll(qc)) s += 5
                    if (e.etapes.size > 1 && commun >= 2) s += 4
                }
            }
            s to e
        }.filter { it.first > 0 }.sortedByDescending { it.first }
        if (scores.isEmpty()) return "Je me gratte la tête… essaie d'autres mots (« supprimer fichier », « ouvrir appli »)."
        val seuil = scores.first().first * 0.5
        val sb = StringBuilder()
        for ((s, e) in scores.take(3)) {
            if (s < seuil) continue
            if (e.etapes.size == 1) {
                sb.append("• ${e.titre}\n   ➜ ${Regles.piege(e.etapes[0].first)}\n")
            } else {
                sb.append("• Recette : ${e.titre}\n")
                e.etapes.forEachIndexed { i, (c, expl) -> sb.append("   ${i + 1}. ${Regles.piege(c)}   ($expl)\n") }
            }
        }
        sb.append("Tape-la toi-même : c'est comme ça qu'on retient !")
        return sb.toString()
    }
}
