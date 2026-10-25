package fr.terminagotchi

import android.util.Base64
import org.json.JSONArray
import java.io.File
import java.security.MessageDigest

/**
 * Capture the flag : chaque épreuve cache un « drapeau » TG{…} qu'on trouve avec les bonnes commandes.
 * Les drapeaux sont tirés au hasard et seule leur empreinte (SHA-256) est gardée :
 * impossible de tricher en lisant la sauvegarde.
 */
object Ctf {
    private class Epreuve(val id: String, val titre: String, val mission: String, val indices: List<String>, val schema: String)

    private val MOTS = listOf("pixel", "kernel", "octet", "glitch", "daemon", "root", "shell", "byte", "cache",
        "socket", "bash", "linux", "stack", "loop", "token", "crypto", "flag", "hack", "zero", "ninja")

    private val EPREUVES = listOf(
        Epreuve("01_cache", "L'invisible", "Un trésor est caché dans cette pièce… mais ls ne le voit pas.",
            listOf("Certaines feuilles se cachent sous le tapis.", "Les fichiers cachés ont un nom qui commence par un point.", "ls -a puis cat .drapeau"),
            "📐 Fichiers cachés (sous le tapis)\n   ls      →  notes.txt\n   ls -a   →  .  ..  .drapeau  notes.txt\n" +
                "   Un nom qui commence par « . » est caché. Les détectives regardent TOUJOURS avec ls -a."),
        Epreuve("02_meule", "La meule de foin", "Le trésor est perdu dans un journal de 3 000 lignes.",
            listOf("Lire 3 000 lignes à la main ? Non merci.", "Prends la loupe du détective : grep cherche un texte dans un fichier.", "grep TG journal.log"),
            "📐 grep\n   journal.log ─┬─ ligne 1   ✗\n                ├─ …         ✗\n                └─ ligne 2047 ✓ TG{…}\n" +
                "   La loupe grep lit chaque ligne et ne garde que celles qui correspondent."),
        Epreuve("03_coffre", "Le coffre", "Le coffre a un cadenas. Mais c'est TON coffre…",
            listOf("cat coffre.txt → accès refusé. Regarde ses cadenas (ses droits).", "ls -l : ---------- = personne ne peut lire.",
                "chmod 644 coffre.txt puis cat coffre.txt"),
            "📐 Droits (les cadenas)\n   ----------  →  chmod 644  →  -rw-r--r--\n   r = lire, w = écrire, x = exécuter\n" +
                "   Le propriétaire a toujours la clé des cadenas de ses fichiers."),
        Epreuve("04_labyrinthe", "Le labyrinthe", "Le trésor est au fond d'un labyrinthe de pièces.",
            listOf("Ouvrir chaque porte à la main serait long.", "find cherche un objet par son nom dans toutes les pièces.",
                "find . -name \"drapeau*\" puis cat le chemin trouvé"),
            "📐 find\n   .  ─ a ─ b ─ c ─ d ─ drapeau.txt ✓\n   find visite TOUTES les pièces (l'arborescence des dossiers) à ta place."),
        Epreuve("05_code", "Le message codé", "Ce message est illisible… il porte un déguisement : le base64.",
            listOf("base64 est un déguisement (un encodage), pas un vrai cadenas (un chiffrement).", "La commande base64 enlève le déguisement avec -d.",
                "base64 -d message.b64"),
            "📐 Déguisement ≠ cadenas (encodage ≠ chiffrement)\n   « TG{…} » ⇄ base64 ⇄ « VEd7…== »\n" +
                "   Tout le monde peut décoder du base64 : ça ne protège rien !"),
        Epreuve("06_miroir", "Le miroir", "Ce texte est écrit à l'envers.",
            listOf("Chaque ligne est retournée, comme dans un miroir.", "La commande rev retourne les lignes.", "rev envers.txt"),
            "📐 rev\n   }…{GT  →  rev  →  TG{…}\n   Les outils simples combinés battent souvent les gros programmes."),
        Epreuve("07_aiguille", "L'aiguille", "40 feuilles. Une seule pèse exactement 42 octets : c'est elle.",
            listOf("Compare le poids des fichiers.", "ls -l montre la taille (5e colonne).",
                "find . -size 42c   (c = octets) puis cat le fichier"),
            "📐 Taille\n   ls -l  →  -rw------- 1 u0 u0  42 fichier_17.txt\n" +
                "   find -size trouve des fichiers par leur poids : utile pour l'enquête du détective."),
    )

    fun dossier(jeu: Jeu) = File(jeu.terrain, "ctf")
    private fun etat(jeu: Jeu) = jeu.module("ctf")

    private fun empreinte(s: String): String =
        MessageDigest.getInstance("SHA-256").digest(s.trim().toByteArray()).joinToString("") { "%02x".format(it) }

    private fun nouveauDrapeau() = "TG{${MOTS.random()}_${MOTS.random()}_${(100..999).random()}}"

    private fun resolus(jeu: Jeu): JSONArray =
        etat(jeu).optJSONArray("resolus") ?: JSONArray().also { etat(jeu).put("resolus", it) }

    private fun estResolu(jeu: Jeu, id: String): Boolean {
        val r = resolus(jeu)
        return (0 until r.length()).any { r.getString(it) == id }
    }

    private fun preparer(jeu: Jeu) {
        val racine = dossier(jeu)
        racine.walkTopDown().forEach { it.setReadable(true, true); it.setExecutable(true, true) }
        racine.deleteRecursively()
        racine.mkdirs()
        val emp = etat(jeu).optJSONObject("empreintes") ?: org.json.JSONObject().also { etat(jeu).put("empreintes", it) }
        for (ep in EPREUVES) {
            val d = File(racine, ep.id)
            d.mkdirs()
            File(d, "LISEZMOI.txt").writeText("🚩 ${ep.titre}\n${ep.mission}\nQuand tu as le trésor (le drapeau) :  drapeau TG{…}\n" +
                "Besoin d'aide :  indice ${ep.id.take(2).trimStart('0')}\n")
            val f = nouveauDrapeau()
            emp.put(ep.id, empreinte(f))
            when (ep.id) {
                "01_cache" -> {
                    File(d, "notes.txt").writeText("Rien d'intéressant ici… ou pas ?\n")
                    File(d, ".drapeau").writeText("$f\n")
                }
                "02_meule" -> {
                    val cible = (500..2900).random()
                    val sb = StringBuilder()
                    val evts = listOf("connexion ok", "lecture disque", "mise à jour cache", "ping réseau", "tâche planifiée")
                    for (i in 1..3000) {
                        sb.append("[%04d] ".format(i)).append(if (i == cible) "secret trouvé : $f" else evts.random()).append('\n')
                    }
                    File(d, "journal.log").writeText(sb.toString())
                }
                "03_coffre" -> {
                    val c = File(d, "coffre.txt")
                    c.writeText("Bravo ! Le drapeau : $f\n")
                    c.setReadable(false, false)
                    c.setWritable(false, false)
                }
                "04_labyrinthe" -> {
                    var p = d
                    val noms = listOf("couloir", "porte", "tunnel", "escalier", "salle", "passage", "impasse")
                    repeat(6) {
                        File(p, noms.random() + "_" + (1..9).random()).mkdirs()   // fausse piste
                        p = File(p, noms.random() + "_" + (10..99).random())
                        p.mkdirs()
                    }
                    File(p, "drapeau.txt").writeText("$f\n")
                }
                "05_code" -> File(d, "message.b64").writeText(
                    Base64.encodeToString("Message secret : $f".toByteArray(), Base64.NO_WRAP) + "\n")
                "06_miroir" -> File(d, "envers.txt").writeText("Le drapeau est : $f".reversed() + "\n")
                "07_aiguille" -> {
                    val gagnant = (1..40).random()
                    for (i in 1..40) {
                        val nom = "fichier_%02d.txt".format(i)
                        val contenu = if (i == gagnant) {
                            f.padEnd(41, '.') + "\n"   // 42 octets pile
                        } else {
                            val taille = listOf((10..40).random(), (43..120).random()).random()
                            "x".repeat(taille - 1) + "\n"
                        }
                        File(d, nom).writeText(contenu)
                    }
                }
            }
        }
    }

    fun ouvrir(jeu: Jeu, arg: String): Pair<String, File?> {
        if (!File(jeu.terrain, "nid").isDirectory) return Mots.accorder("{ctf} s'ouvre après la leçon « Construire mon nid ».", "ctf" to Mots.terme("ctf", Mots.palier(jeu), true)) to null
        val neuf = arg == "nouveau" || !dossier(jeu).isDirectory
        if (neuf) {
            etat(jeu).put("resolus", JSONArray())
            preparer(jeu)
            jeu.log(Mots.accorder("🚩 {ctf} est prête !", "ctf" to Mots.terme("ctf", 0, true)))
        }
        val suite = if (neuf) "\n\nJe t'emmène dans la pièce des énigmes. Commence par : cd 01_cache" else ""
        val aller: File? = if (neuf) dossier(jeu) else null
        return Pair(texte(jeu) + suite, aller)
    }

    fun texte(jeu: Jeu): String {
        val sb = StringBuilder("🚩 " + Mots.terme("ctf", Mots.palier(jeu), true) + " — ~/terrain_terminagotchi/ctf\n")
        for ((i, ep) in EPREUVES.withIndex()) {
            sb.append(if (estResolu(jeu, ep.id)) "  ✅ " else "  ⬜ ").append("${i + 1}. ${ep.titre} (${ep.id})\n")
        }
        sb.append("Trésors : ${resolus(jeu).length()}/${EPREUVES.size} · lis LISEZMOI.txt dans chaque pièce\n")
        sb.append("Montrer un trésor : drapeau TG{…} · coup de pouce : indice <numéro>")
        return sb.toString()
    }

    fun indice(jeu: Jeu, n: String): String {
        val i = n.toIntOrNull() ?: return "Exemple : indice 1"
        val ep = EPREUVES.getOrNull(i - 1) ?: return "Il y a ${EPREUVES.size} épreuves (1 à ${EPREUVES.size})."
        val vus = etat(jeu).optJSONObject("indices") ?: org.json.JSONObject().also { etat(jeu).put("indices", it) }
        val k = vus.optInt(ep.id).coerceAtMost(ep.indices.size - 1)
        vus.put(ep.id, k + 1)
        return "💡 Indice ${k + 1}/${ep.indices.size} (${ep.titre}) : ${ep.indices[k]}"
    }

    fun valider(jeu: Jeu, proposition: String): String {
        if (proposition.isBlank()) return "Exemple : drapeau TG{pixel_root_123}"
        val emp = etat(jeu).optJSONObject("empreintes") ?: return "Tape d'abord « ctf » pour cacher les trésors."
        val h = empreinte(proposition)
        val ep = EPREUVES.firstOrNull { emp.optString(it.id) == h }
            ?: return "❌ Ce n'est pas un vrai trésor. Vérifie chaque caractère (majuscules, accolades)."
        if (estResolu(jeu, ep.id)) return "Tu as déjà validé « ${ep.titre} » !"
        resolus(jeu).put(ep.id)
        val nbIndices = etat(jeu).optJSONObject("indices")?.optInt(ep.id) ?: 0
        val gain = (40 - nbIndices * 10).coerceAtLeast(10)
        jeu.ajouterXp(gain)
        jeu.stats["Intelligence"] = (jeu.stats["Intelligence"] ?: 0) + 3
        jeu.log("🚩 Drapeau « ${ep.titre} » capturé !")
        val fin = if (resolus(jeu).length() == EPREUVES.size) "\n\n🏆 TOUS LES DRAPEAUX ! Tu as l'âme d'un hacker éthique." else ""
        return "🚩 Trésor trouvé : ${ep.titre} ! +$gain XP\n\n${ep.schema}$fin"
    }
}
