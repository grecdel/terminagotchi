package fr.terminagotchi

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlin.math.sqrt

class Etape(
    val dit: String,
    val cmd: String,
    val bravo: String,
    val re: Regex? = null,
    val fs: ((Jeu) -> Boolean)? = null,
    val astuce: String? = null,
)

/** Une commande du lexique : son image (la maison), son explication technique, sa section. */
class Mot(val cmd: String, val image: String, val technique: String, val section: String)

class Lecon(val titre: String, val skill: String, val niveau: Int, val etapes: List<Etape>)

/** Règles communes : catégories, compétences, textes, piège anti copier-coller. */
object Regles {
    val STATS = listOf("Intelligence", "Agilité", "Force", "Endurance")
    val COURT = mapOf("Intelligence" to "INT", "Agilité" to "AGI", "Force" to "FOR", "Endurance" to "END")
    val COULEUR = mapOf("Intelligence" to 39, "Agilité" to 78, "Force" to 203, "Endurance" to 221)

    val CATEGORIES: Map<String, Set<String>> = mapOf(
        "Intelligence" to setOf("git", "python", "python3", "sh", "bash", "alias", "vi", "nano", "awk", "sed"),
        "Agilité" to setOf("ping", "curl", "wget", "ip", "ifconfig", "netstat", "nslookup", "am", "pm",
            "applis", "ouvre", "web", "carte", "appelle", "sms", "partage", "lampe", "vibre", "batterie", "dis",
            "reglages"),
        "Force" to setOf("top", "ps", "kill", "df", "du", "free", "uname", "whoami", "date", "id", "getprop",
            "dumpsys", "uptime"),
        "Endurance" to setOf("ls", "cd", "cp", "mv", "rm", "mkdir", "rmdir", "cat", "touch", "find", "grep",
            "head", "tail", "chmod", "pwd", "echo", "stat", "more", "less", "wc", "sort", "tree"),
    )

    val SKILLS: Map<String, Set<String>> = mapOf(
        "Boussole" to setOf("cd", "ls", "pwd"),
        "Bâtisseur" to setOf("mkdir", "touch", "echo"),
        "Inspecteur" to setOf("cat", "grep", "head", "tail", "find", "more", "less"),
        "Gardien" to setOf("chmod"),
        "Nettoyeur" to setOf("cp", "mv", "rm"),
        "Télécommande" to setOf("lampe", "vibre", "batterie"),
        "Portier" to setOf("ouvre", "applis", "web", "carte"),
        "Messager" to setOf("dis", "partage", "sms", "appelle"),
        "Vigie" to setOf("whoami", "id", "ps"),
        "Intendant" to setOf("df", "du", "uptime"),
        "Détective" to setOf("uname", "getprop", "find"),
        "Plombier" to setOf("wc", "sort"),
        "Tamiseur" to setOf("grep"),
        "Cuistot" to setOf("sh"),
        "Inventeur" to setOf("echo"),
        "Créateur" to setOf("for", "if", "while"),
        "Apprenti" to setOf("doom"),
        "Architecte" to setOf("edite"),
        "Ingénieur" to setOf("doom", "edite"),
    )

    val STADES = listOf("Œuf", "Bébé", "Ado", "Adulte")
    val FORMES = mapOf("Intelligence" to "Hacker", "Force" to "Titan", "Agilité" to "Éclair", "Endurance" to "Carapace")

    val TRAITS = mapOf(
        "curieux" to listOf("Qu'est-ce qu'il y a dans ce dossier ?", "Apprends-moi une nouvelle commande !",
            "Je me demande ce que fait « ls -l »…", "Et si on explorait un peu ?"),
        "farceur" to listOf("Et si on renommait tous tes fichiers ? Je plaisante !", "rm -rf ? Jamais de la vie, hihi.",
            "Tu tapes vite… pour un humain.", "J'ai caché un fichier quelque part. Ou pas."),
        "gourmand" to listOf("Une petite commande, juste une ?", "J'ai un creux de 512 octets.",
            "Miam, un « ls » bien frais.", "Les « grep » sont mes préférés, croustillants !"),
        "philosophe" to listOf("Sommes-nous tous dans le sous-dossier de quelqu'un ?",
            "Un fichier supprimé existe-t-il encore dans nos cœurs ?", "pwd… mais où suis-je VRAIMENT ?",
            "Le terminal est noir, mais l'avenir est clair."),
    )
    val FAIM = listOf("J'ai faim… tape quelque chose !", "Mon ventre fait « segmentation fault ».",
        "Même un petit « pwd » me ferait du bien…")
    val OEUF = listOf("…", "*toc toc*", "*l'œuf bouge un peu*", "*crac ?*")
    val COLLE = listOf("Hé ! Tu as collé du texte… tape-la toi-même, sinon ça ne rentre pas dans ma tête !",
        "Copier-coller détecté : ça n'a aucun goût. Avec tes doigts, s'il te plaît !",
        "Bien essayé ! Mais je ne mange que les commandes tapées à la main.")

    // Lettres cyrilliques identiques à l'œil : une commande affichée puis collée ne fonctionne pas.
    private val HOMO = mapOf('a' to 'а', 'c' to 'с', 'e' to 'е', 'o' to 'о', 'p' to 'р', 'x' to 'х',
        'y' to 'у', 'i' to 'і', 's' to 'ѕ', 'd' to 'ԁ', 'h' to 'һ', 'j' to 'ј')
    private val PIEGES: Set<Char> = HOMO.values.toSet() + '\u00a0'

    fun piege(cmd: String): String {
        val sb = StringBuilder()
        var fait = false
        for (c in cmd) {
            val h = HOMO[c]
            when {
                !fait && h != null -> { sb.append(h); fait = true }
                c == ' ' -> sb.append('\u00a0')
                else -> sb.append(c)
            }
        }
        return sb.toString()
    }

    fun estColle(l: String) = l.any { it in PIEGES }
    fun niveau(xp: Int) = sqrt(xp / 10.0).toInt() + 1
    fun stade(n: Int) = when {
        n < 2 -> 0
        n < 5 -> 1
        n < 10 -> 2
        else -> 3
    }

    fun premierMot(l: String): String =
        l.trim().split(Regex("\\s+")).firstOrNull()?.lowercase()?.substringAfterLast('/') ?: ""

    /**
     * Le lexique : toutes les commandes utiles du terminal Android.
     * Fil rouge : l'ordinateur est une grande maison. Chaque commande a une image (la maison)
     * et une explication technique ; l'affichage suit le palier de vocabulaire (voir Mots.kt).
     * Les mêmes phrases existent sur PC (pc/tg/lexique.py).
     */
    val LEXIQUE: List<Mot> = run {
        val f = "🗂 Fichiers et dossiers"
        val l = "🔎 Lire et chercher"
        val y = "⚙ Système"
        val t = "📱 Ton téléphone (commandes de l'appli)"
        val c = "🐾 Ta créature"
        val j = "🎮 Jeux, aventures et progression"
        val p = "💻 Sur ordinateur ou en mode Linux complet (pas ici)"
        val w = "🌍 Recensement (sur tous tes appareils)"
        listOf(
            Mot("pwd", "le point rouge « vous êtes ici » sur le plan de la maison", "affiche le dossier où tu te trouves", f),
            Mot("ls", "j'ouvre les yeux et je regarde dans la pièce (ls -a : même sous le tapis, ls -l : avec les détails)",
                "liste le contenu (ls -a : avec les cachés, ls -l : les détails)", f),
            Mot("cd", "je passe une porte (cd .. : je recule d'une pièce, cd ~ : je rentre dans ma chambre)",
                "change de dossier (cd nom, cd .. pour remonter, cd ~ pour rentrer)", f),
            Mot("mkdir", "je construis une nouvelle pièce", "crée un dossier", f),
            Mot("touch", "je pose une feuille blanche sur la table", "crée un fichier vide", f),
            Mot("echo", "je dis une phrase (avec > : l'entonnoir la verse dans une boîte)",
                "affiche un texte (echo texte > fichier : l'écrit dedans)", f),
            Mot("cp", "je fais une photocopie d'une feuille (cp -r : de toute une pièce)", "copie un fichier (cp -r : un dossier)", f),
            Mot("mv", "je porte une feuille ailleurs, ou je change son étiquette", "déplace ou renomme", f),
            Mot("rm", "la broyeuse : pas de poubelle, c'est perdu pour toujours ! (rm -r : toute une pièce)",
                "supprime, sans corbeille ! (rm -r : un dossier)", f),
            Mot("rmdir", "je démonte une pièce vide", "supprime un dossier vide", f),
            Mot("chmod", "un cadenas sur la boîte (chmod 444 : on peut lire, plus écrire)",
                "change les droits (chmod 444 : lecture seule)", f),
            Mot("cat", "je lis la lettre à voix haute", "affiche le contenu d'un fichier", l),
            Mot("head", "je lis juste le haut de la lettre", "affiche le début d'un fichier", l),
            Mot("tail", "je lis juste le bas de la lettre", "affiche la fin d'un fichier", l),
            Mot("grep", "la loupe du détective : elle trouve un mot dans les lettres", "cherche un mot dans un fichier", l),
            Mot("find", "je cherche un objet dans toutes les pièces (find . -name \"*.txt\")",
                "trouve des fichiers par leur nom (find . -name \"*.txt\")", l),
            Mot("wc", "je compte les lignes et les mots de la lettre", "compte lignes, mots et caractères", l),
            Mot("sort", "je range les lignes dans l'ordre, comme un dictionnaire", "trie les lignes d'un fichier", l),
            Mot("stat", "la carte d'identité d'une feuille", "tous les détails d'un fichier", l),
            Mot("date", "je regarde l'horloge de la maison", "la date et l'heure", y),
            Mot("whoami", "mon prénom d'habitant de la maison (sur Android, celui de l'appli)",
                "ton nom d'utilisateur (sur Android, celui de l'appli)", y),
            Mot("id", "ma carte d'habitant et mes clubs", "ton identité et tes groupes", y),
            Mot("uptime", "depuis quand la maison est réveillée", "depuis quand le téléphone est allumé", y),
            Mot("uname", "la fiche de la maison : son nom, sa version (uname -a : tout)", "infos sur le système (uname -a : tout)", y),
            Mot("df", "la place qui reste dans les placards (df -h : en Go, Mo)", "espace libre sur le stockage (df -h : lisible)", y),
            Mot("du", "je pèse une pièce et tout ce qu'elle contient (du -sh dossier)", "taille d'un dossier (du -sh dossier)", y),
            Mot("ps", "qui est réveillé dans la maison ?", "programmes en cours (processus)", y),
            Mot("ping", "je crie « Ohé ! » et j'attends l'écho (ping -c 3 example.com)",
                "teste la connexion (ping -c 3 example.com)", y),
            Mot("clear", "je range la table : l'écran redevient tout propre", "efface l'écran du terminal", y),
            Mot("applis", "la liste de toutes les applis qui habitent le téléphone (applis what : filtre)",
                "liste tes applis (applis what : filtre)", t),
            Mot("ouvre", "j'allume une appli, comme on allume la télé : ouvre whatsapp", "lance une appli : ouvre whatsapp", t),
            Mot("web", "j'ouvre la fenêtre sur un site : web météo paris", "ouvre un site ou une recherche : web météo paris", t),
            Mot("carte", "je déplie la carte du monde pour trouver un lieu : carte tour eiffel", "cherche un lieu : carte tour eiffel", t),
            Mot("appelle", "je compose le numéro, c'est toi qui appuies sur Appeler : appelle 0612345678",
                "prépare un appel (sans appeler) : appelle 0612345678", t),
            Mot("sms", "j'écris un petit mot, tu n'as plus qu'à l'envoyer : sms 0612345678 coucou",
                "prépare un SMS : sms 0612345678 coucou", t),
            Mot("partage", "je glisse ton message dans la boîte aux lettres de ton choix : partage salut !",
                "envoie un texte via l'appli de ton choix : partage salut !", t),
            Mot("lampe", "l'interrupteur de la lampe de poche : lampe on / lampe off", "lampe torche : lampe on / lampe off", t),
            Mot("vibre", "le téléphone frissonne : vibre 500", "fait vibrer : vibre 500", t),
            Mot("batterie", "combien il reste à manger dans le ventre du téléphone", "niveau de batterie", t),
            Mot("dis", "le téléphone lit ta phrase à voix haute : dis bonjour", "le téléphone parle : dis bonjour", t),
            Mot("reglages", "le tableau des boutons de la maison : reglages wifi (bluetooth, son, ecran…)",
                "ouvre les réglages : reglages wifi (bluetooth, son, ecran…)", t),
            Mot("caresse", "un câlin pour ta créature", "un câlin pour ta créature", c),
            Mot("danse", "elle danse pour toi", "elle danse pour toi", c),
            Mot("parle", "elle te dit ce qu'elle pense", "elle te dit ce qu'elle pense", c),
            Mot("joue", "pierre-feuille-ciseaux : joue pierre", "pierre-feuille-ciseaux : joue pierre", c),
            Mot("devine", "devine son nombre (1 à 20) : devine 10", "devine son nombre (1 à 20) : devine 10", c),
            Mot("etat", "sa fiche complète", "sa fiche complète", c),
            Mot("renomme", "change son nom : renomme Pixel", "change son nom : renomme Pixel", c),
            Mot("arbre", "l'arbre de ce que tu peux apprendre : arbre (puis arbre scripts…)",
                "l'arbre de compétences : arbre (puis arbre scripts…)", j),
            Mot("cherche", "demande à ta créature la bonne commande : cherche supprimer un dossier",
                "trouve la bonne commande : cherche supprimer un dossier", j),
            Mot("collection", "l'album de tes bestioles", "tes bestioles capturées", j),
            Mot("defi", "un défi éclair (defi records : tes records)", "lance un défi éclair (defi records : tes records)", j),
            Mot("donjon", "une cave aux mille pièces, pleine de trésors (donjon nouveau : recommencer)",
                "entre dans le donjon aléatoire (donjon nouveau : recommencer)", j),
            Mot("plan", "le plan de l'étage du donjon", "la carte de l'étage du donjon", j),
            Mot("quetes", "tes quêtes et tes cœurs", "tes quêtes et tes points de vie (PV)", j),
            Mot("attaque", "combat le monstre caché dans la pièce", "combat le monstre caché dans la salle", j),
            Mot("sac", "ce que tu portes sur ton dos", "ton inventaire", j),
            Mot("equipe", "prends un objet du sac en main : equipe epee_rouillee", "s'équiper d'un objet du sac : equipe epee_rouillee", j),
            Mot("bois", "bois une potion : bois potion_de_soin", "boire une potion : bois potion_de_soin", j),
            Mot("ctf", "la chasse au trésor : 7 énigmes de détective", "le capture the flag (CTF, épreuves de hacker)", j),
            Mot("drapeau", "montre le trésor trouvé : drapeau TG{…}", "valider un drapeau : drapeau TG{…}", j),
            Mot("indice", "un coup de pouce pour une énigme : indice 1", "un indice pour une épreuve : indice 1", j),
            Mot("edite", "mon cahier pour écrire dans une feuille : edite notes.txt", "éditeur de texte (comme nano) : edite notes.txt", j),
            Mot("doom", "un labyrinthe en 3D que tu dessines toi-même (dans ~/terrain_terminagotchi/jeu)",
                "lance TON Doom-like (niveau dans ~/terrain_terminagotchi/jeu)", j),
            Mot("notifs", "je te préviens quand j'ai faim : notifs on / off", "notifications on / off", j),
            Mot("compte", "le registre de la maison : même créature sur PC et téléphone",
                "recensement en ligne : même créature sur PC et téléphone", w),
            Mot("sync", "je mets à jour le registre maintenant", "synchronise ta créature maintenant", w),
            Mot("site", "la vitrine de ta maison sur internet (site bestiaire, site captures…)",
                "ouvre le site : ton profil (site bestiaire, site captures…)", w),
            Mot("bestiaire", "le grand livre des espèces : bestiaire Glitchou", "la fiche d'une espèce : bestiaire Glitchou", j),
            Mot("troupe", "ta troupe de bestioles et celle qui t'accompagne (troupe <nom>)",
                "ta troupe de bestioles : stades et bestiole active (troupe <nom>)", j),
            Mot("anime", "regarde une bestiole bouger : anime abyssor attaque", "voir bouger une bestiole : anime abyssor attaque", j),
            Mot("sudo", "la clé du gardien, pour les gros travaux (pas de clé dans la chambre fermée du téléphone)",
                "agir en administrateur (impossible dans le bac à sable du téléphone)", p),
            Mot("apt", "le magasin de la maison : on y installe des logiciels", "installer des logiciels (Linux / Termux, ou mode Linux complet)", p),
            Mot("nano", "mon cahier pour écrire dans une feuille (ici : edite)", "éditeur de texte du terminal (ici : edite)", p),
            Mot("git", "un appareil photo qui garde une photo de tes fichiers à chaque étape (version PC)",
                "garder l'historique de ses fichiers (version PC)", p),
            Mot("python3", "j'apprends une nouvelle langue à la maison : Python (version PC)",
                "programmer en Python (version PC / mode Linux complet)", p),
            Mot("top", "qui est réveillé, en direct, comme une caméra (version PC)", "programmes en direct, plein écran (version PC)", p),
            Mot("ssh", "un tunnel secret vers une autre maison (version PC)", "se connecter à une autre machine (version PC)", p),
        )
    }

    /** Le texte d'une commande du lexique selon le palier : l'image, puis l'image — la technique, puis la technique (l'image). */
    fun explication(m: Mot, palier: Int): String = when {
        palier <= 0 || m.image == m.technique -> m.image
        palier == 1 -> "${m.image} — ${m.technique}"
        else -> "${m.technique} (${m.image})"
    }

    fun barre(v: Double, max: Double, n: Int): String {
        val k = ((v / max) * n).toInt().coerceIn(0, n)
        return "▰".repeat(k) + "▱".repeat(n - k)
    }
}

/** L'état de la créature, sauvegardé en JSON dans le stockage privé de l'appli. */
class Jeu(ctx: Context) {
    init {
        Bestiaire.charger(ctx.applicationContext)
        Animations.init(ctx)
    }

    // chemin « canonique » : /data/user/0 et /data/data désignent le même dossier sur Android
    val home: File = File(ctx.filesDir, "maison").apply { mkdirs() }.canonicalFile
    val terrain: File get() = File(home, "terrain_terminagotchi")
    private val fichier = File(ctx.filesDir, "sauvegarde.json")

    var nom = ""
    var xp = 0
    var faim = 80.0
    var total = 0
    var dernierTick = System.currentTimeMillis()
    val stats = linkedMapOf<String, Int>().apply { Regles.STATS.forEach { put(it, 0) } }
    val vus = mutableSetOf<String>()
    val journal = mutableListOf<String>()
    val skills = mutableListOf<String>()
    var lecon = 0
    var etape = 0
    var forme: String? = null
    var trait = Regles.TRAITS.keys.random()
    var bulle = ""
    var bulleFin = 0L
    var colles = 0
    /** créature shiny (1 chance sur 64 à la naissance) */
    var shiny = false
    private val dernierJeu = mutableMapOf<String, Long>()
    val historique = mutableListOf<String>()

    /** Données des modules (arbre, exploration, donjon, ctf, défis…), sauvegardées telles quelles. */
    var extra = JSONObject()

    /** Sous-objet d'un module, créé à la demande. */
    fun module(nom: String): JSONObject = extra.optJSONObject(nom) ?: JSONObject().also { extra.put(nom, it) }

    val branches: Map<String, Branche> by lazy { Arbre.creer(this) }

    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)

    val lecons: List<Lecon> = listOf(
        Lecon("Où suis-je ?", "Boussole", 1, listOf(
            Etape("Coucou ! On visite la maison ensemble. Où est le point rouge « vous êtes ici » ?", "pwd",
                "Trouvé, voilà notre point rouge ! Les grands appellent ça *le dossier où tu es* (pwd).", re = r("^pwd\\b")),
            Etape("Ouvre les yeux : qu'est-ce qu'il y a dans cette pièce ?", "ls",
                "Tout ce qu'il y a dans la pièce ! Les grands disent *lister le dossier*.", re = r("^ls\\b")),
            Etape("Allez, on rentre dans ta chambre !", "cd ~",
                "Te revoilà dans ta chambre ! Les grands disent *ton dossier perso* ; son petit nom, c'est ~.", re = r("^cd(\\s+~/?)?\\s*$"),
                astuce = "Le ~ est dans la rangée de touches au-dessus du clavier. (« cd » tout seul marche aussi !)"),
        )),
        Lecon("Construire mon nid", "Bâtisseur", 1, listOf(
            Etape("Il me faut une salle de jeu. Depuis ta chambre, construis une nouvelle pièce !", "mkdir terrain_terminagotchi",
                "Une pièce toute neuve ! Les grands disent *créer un dossier*.", fs = { it.terrain.isDirectory }),
            Etape("Passe la porte de la salle de jeu.", "cd terrain_terminagotchi",
                "On est dans notre salle de jeu ! Passer une porte, les grands disent *changer de dossier*.",
                re = r("^cd\\s+.*terrain_terminagotchi")),
            Etape("Construis-moi un petit nid dans cette pièce !", "mkdir nid",
                "Il est parfait ! Une pièce dans une pièce : les grands disent *un sous-dossier*. Et j'entends du bruit dehors…",
                fs = { File(it.terrain, "nid").isDirectory }),
        )),
        Lecon("Le garde-manger", "Inspecteur", 1, listOf(
            Etape("J'ai faim ! Prends l'entonnoir « > » et verse une pomme dans la boîte repas.txt de mon nid.",
                "echo pomme > nid/repas.txt",
                "Miam ! Attention : l'entonnoir vide la boîte avant de verser. Les grands disent *écrire dans un fichier*.",
                fs = { File(it.terrain, "nid/repas.txt").isFile }),
            Etape("Lis-moi la lettre repas.txt à voix haute.", "cat nid/repas.txt",
                "Une pomme, parfait ! Les grands disent *afficher un fichier*. Toujours vérifier avant d'agir !", re = r("^(cat|more|less|head)\\b.*repas")),
            Etape("Prends la loupe du détective : cherche le mot « pomme » dans la lettre.", "grep pomme nid/repas.txt",
                "La loupe l'a trouvé ! Les grands disent *chercher dans un fichier*.", re = r("^grep\\b.*pomme")),
        )),
        Lecon("Le bouclier", "Gardien", 1, listOf(
            Etape("Qui a le droit de toucher à mon repas ? Regarde les cadenas.", "ls -l nid",
                "r = lire, w = écrire, x = faire marcher. Les grands disent *les droits*.", re = r("^(ls\\s+-\\w*l|stat)\\b")),
            Etape("Mets un cadenas sur la boîte, que personne ne l'abîme !", "chmod 444 nid/repas.txt",
                "Clic ! On peut lire, mais plus écrire. Les grands disent *lecture seule*.",
                fs = { val f = File(it.terrain, "nid/repas.txt"); f.isFile && !f.canWrite() }),
            Etape("Essaie de glisser une poire au fond de la boîte, pour voir…", "echo poire >> nid/repas.txt",
                "Refusé ! « >> » ajoute au fond sans rien vider… mais le cadenas tient bon. Les grands disent *ajouter à la fin*.", re = r(">>.*repas")),
        )),
        Lecon("Grand ménage", "Nettoyeur", 1, listOf(
            Etape("Fais une photocopie de mon repas, au cas où.", "cp nid/repas.txt nid/secours.txt",
                "Deux feuilles pareilles, et l'original n'a pas bougé ! Les grands disent *copier*.", fs = { File(it.terrain, "nid/secours.txt").isFile }),
            Etape("Porte la copie dans la salle de jeu et colle-lui une nouvelle étiquette : reserve.txt.",
                "mv nid/secours.txt reserve.txt",
                "Déménagée et renommée d'un coup ! Les grands disent *déplacer* et *renommer*.", fs = { File(it.terrain, "reserve.txt").isFile }),
            Etape("On n'en a plus besoin. Attention : c'est la broyeuse, pas la poubelle !", "rm reserve.txt",
                "Broyée pour toujours : pas de poubelle pour la rattraper. Les grands disent *supprimer*. Vérifie toujours avant !",
                fs = { !File(it.terrain, "reserve.txt").exists() }),
        )),
    )

    init {
        charger()
    }

    val existe: Boolean get() = nom.isNotEmpty()
    val niveau: Int get() = Regles.niveau(xp)
    val stade: Int get() = Regles.stade(niveau)

    // ------------------------------------------------------------ sauvegarde
    /** Relit la sauvegarde (une autre partie de l'appli, comme le Doom, a pu la modifier). */
    fun recharger() {
        vus.clear()
        journal.clear()
        skills.clear()
        historique.clear()
        extra = JSONObject()
        Regles.STATS.forEach { stats[it] = 0 }
        charger()
    }

    private fun charger() {
        if (!fichier.exists()) return
        try {
            val o = JSONObject(fichier.readText())
            nom = o.optString("nom")
            xp = o.optInt("xp")
            faim = o.optDouble("faim", 80.0)
            total = o.optInt("total")
            dernierTick = o.optLong("dernierTick", dernierTick)
            o.optJSONObject("stats")?.let { s -> Regles.STATS.forEach { stats[it] = s.optInt(it) } }
            o.optJSONArray("vus")?.let { a -> for (i in 0 until a.length()) vus.add(a.getString(i)) }
            o.optJSONArray("journal")?.let { a -> for (i in 0 until a.length()) journal.add(a.getString(i)) }
            o.optJSONArray("skills")?.let { a -> for (i in 0 until a.length()) skills.add(a.getString(i)) }
            o.optJSONArray("historique")?.let { a -> for (i in 0 until a.length()) historique.add(a.getString(i)) }
            lecon = o.optInt("lecon")
            etape = o.optInt("etape")
            forme = if (o.has("forme") && !o.isNull("forme")) o.getString("forme") else null
            trait = o.optString("trait", trait)
            bulle = o.optString("bulle")
            bulleFin = o.optLong("bulleFin")
            colles = o.optInt("colles")
            shiny = o.optBoolean("shiny")
            extra = o.optJSONObject("extra") ?: JSONObject()
        } catch (e: Exception) {
            // sauvegarde illisible : on repart de zéro plutôt que de planter
        }
    }

    fun sauver() {
        val o = JSONObject()
        o.put("nom", nom)
        o.put("xp", xp)
        o.put("faim", faim)
        o.put("total", total)
        o.put("dernierTick", dernierTick)
        o.put("stats", JSONObject(stats.toMap()))
        o.put("vus", JSONArray(vus.toList()))
        o.put("journal", JSONArray(journal))
        o.put("skills", JSONArray(skills))
        o.put("historique", JSONArray(historique))
        o.put("lecon", lecon)
        o.put("etape", etape)
        o.put("forme", forme ?: JSONObject.NULL)
        o.put("trait", trait)
        o.put("bulle", bulle)
        o.put("bulleFin", bulleFin)
        o.put("colles", colles)
        o.put("shiny", shiny)
        o.put("extra", extra)
        val tmp = File(fichier.parentFile, "sauvegarde.tmp")
        tmp.writeText(o.toString())
        tmp.renameTo(fichier)
    }

    // ------------------------------------------------------------ vie de la créature
    fun log(msg: String) {
        val heure = SimpleDateFormat("HH:mm", Locale.FRANCE).format(Date())
        journal.add("$heure $msg")
        while (journal.size > 6) journal.removeAt(0)
    }

    fun dire(texte: String, secondes: Int = 8) {
        bulle = texte
        bulleFin = System.currentTimeMillis() + secondes * 1000L
    }

    fun bulleActive(): String = if (System.currentTimeMillis() < bulleFin) bulle else ""

    fun dominant(): String =
        if (stats.values.all { it == 0 }) Regles.STATS.random() else stats.maxByOrNull { it.value }!!.key

    fun tick() {
        val now = System.currentTimeMillis()
        val rate = if ("Gardien" in skills) 720_000.0 else 360_000.0     // ms par point de faim
        faim = (faim - (now - dernierTick) / rate).coerceAtLeast(0.0)
        dernierTick = now
    }

    fun ajouterXp(n: Int) {
        val avant = niveau
        xp += n
        val apres = niveau
        if (apres <= avant) return
        if (Regles.stade(apres) > Regles.stade(avant)) {
            if (Regles.stade(apres) == 1) {
                log("✨ L'œuf a éclos !")
                dire("Bonjour le monde ! … C'est comme ça qu'on dit, non ?", 10)
            } else {
                if (forme == null) forme = dominant()
                log("✨ ÉVOLUTION → ${Regles.STADES[Regles.stade(apres)]} ${Regles.FORMES[forme ?: ""] ?: ""} !")
                dire("Waouh… je me sens différent !", 10)
            }
        } else {
            log("⬆ Niveau $apres !")
        }
        val l = leconCourante()
        if (l != null && l.niveau == apres) dire("J'ai quelque chose à t'apprendre !", 10)
    }

    /** Mange une commande. Renvoie false si elle a été refusée (collée). */
    fun manger(ligne: String, colle: Boolean, rappel: Boolean = false): Boolean {
        if (colle || Regles.estColle(ligne)) {
            colles++
            log("✖ copier-coller détecté : pas de nourriture")
            dire(Regles.COLLE.random(), 10)
            return false
        }
        val cmd = Regles.premierMot(ligne)
        if (cmd.isEmpty()) return false
        if (rappel) {
            log("a revu « $cmd » (rappel ↑ : pas d'XP)")
            return false
        }
        total++
        var gain = 1
        var msg = "a mangé « $cmd »"
        val stat = Regles.CATEGORIES.entries.firstOrNull { cmd in it.value }?.key
        if (stat != null) {
            stats[stat] = (stats[stat] ?: 0) + 1
            gain += 1
            msg += " +${Regles.COURT[stat]}"
        }
        if (cmd in Commandes.CREATURE) {
            val maintenant = System.currentTimeMillis()
            if (maintenant - (dernierJeu[cmd] ?: 0L) < 60_000) {
                faim = (faim + 1).coerceAtMost(100.0)
                log("$msg (déjà joué il y a peu : pas d'XP)")
                return true
            }
            dernierJeu[cmd] = maintenant
        }
        if (vus.add(cmd)) {
            gain += 5
            msg += " ★ nouveau goût"
        }
        if (skills.any { Regles.SKILLS[it]?.contains(cmd) == true }) {
            gain *= 2
            msg += " ×2"
        }
        faim = (faim + 3).coerceAtMost(100.0)
        module("compte").put("repas", System.currentTimeMillis())
        log(msg)
        ajouterXp(gain)
        return true
    }

    val troncFini: Boolean get() = lecon >= lecons.size

    fun brancheActive(): String? = module("arbre").optString("active", "").ifEmpty { null }

    fun progresBranche(b: String): Int = module("arbre").optJSONObject("progres")?.optInt(b) ?: 0

    fun choisirBranche(b: String) {
        val a = module("arbre")
        if (a.optString("active") != b) {
            a.put("active", b)
            etape = 0
        }
    }

    fun leconCourante(): Lecon? {
        if (lecon < lecons.size) return lecons[lecon]
        val b = brancheActive() ?: return null
        val ls = branches[b]?.lecons ?: return null
        val i = progresBranche(b)
        return if (i < ls.size) ls[i] else null
    }

    fun etapeCourante(): Etape? {
        val l = leconCourante() ?: return null
        return if (niveau >= l.niveau) l.etapes[etape] else null
    }

    private fun avancer(l: Lecon): Boolean {
        val e = l.etapes[etape]
        log("✔ ${e.cmd}")
        dire(e.bravo, 12)
        etape++
        if (etape < l.etapes.size) {
            ajouterXp(5)
            return true
        }
        etape = 0
        if (l.skill !in skills) skills.add(l.skill)
        log("🎓 « ${l.titre} » finie → ${l.skill} !")
        var msg = "Leçon finie ! J'ai appris « ${l.skill} » grâce à toi."
        if (!troncFini) {
            lecon++
            if (troncFini) msg = "Tronc commun terminé, bravo ! L'arbre de compétences est ouvert : tape « arbre »."
        } else {
            val b = brancheActive()
            if (b != null) {
                val a = module("arbre")
                val p = a.optJSONObject("progres") ?: JSONObject().also { a.put("progres", it) }
                p.put(b, p.optInt(b) + 1)
                val br = branches[b]
                if (br != null) {
                    stats[br.stat] = (stats[br.stat] ?: 0) + 5
                    if (p.optInt(b) >= br.lecons.size) {
                        a.put("active", "")
                        log("🌳 Branche ${br.nom} maîtrisée !")
                        msg = "Branche ${br.nom} maîtrisée ! Tape « arbre » pour en choisir une autre."
                    }
                }
            }
        }
        ajouterXp(20)
        dire(msg, 14)
        return false
    }

    fun leconTick(ligne: String?, colle: Boolean) {
        val l = leconCourante() ?: return
        if (niveau < l.niveau) return
        val e = l.etapes[etape]
        if (ligne != null && !colle && !Regles.estColle(ligne) && e.re?.containsMatchIn(ligne.trim()) == true) {
            if (!avancer(l)) return
        }
        val l2 = leconCourante() ?: return
        if (l2 !== l || niveau < l2.niveau) return
        if (l2.etapes[etape].fs?.invoke(this) == true) avancer(l2)
    }

    fun parlerSiSilencieux() {
        if (bulleActive().isNotEmpty()) return
        when {
            stade == 0 -> dire(Regles.OEUF.random())
            faim < 30 -> dire(Regles.FAIM.random())
            else -> dire(Regles.TRAITS[trait]?.random() ?: "…")
        }
    }

    // ------------------------------------------------------------ textes affichés
    fun humeur() = when {
        faim >= 60 -> "repu"
        faim >= 30 -> "petit creux"
        faim > 0 -> "affamé !"
        else -> "NOURRIS-MOI…"
    }

    fun titre(): String {
        val fo = forme
        val f = if (stade >= 2 && fo != null) " ${Regles.FORMES[fo]}" else ""
        return "$nom${if (shiny) " ✨" else ""} · ${Regles.STADES[stade]}$f · niv. $niveau"
    }

    fun texteXp(): String {
        val lo = 10 * (niveau - 1) * (niveau - 1)
        val hi = 10 * niveau * niveau
        return "xp   ${Regles.barre((xp - lo).toDouble(), (hi - lo).toDouble(), 8)}  $xp/$hi"
    }

    fun texteFaim() = "faim ${Regles.barre(faim, 100.0, 8)}  ${humeur()}"

    fun texteStats() = Regles.STATS.joinToString("  ") { "${Regles.COURT[it]} ${stats[it]}" }

    fun texteLecon(): String? {
        val l = leconCourante() ?: return if (troncFini && brancheActive() == null)
            "🌳 Choisis ta prochaine branche d'apprentissage : tape  arbre" else null
        if (niveau < l.niveau) {
            val manque = 10 * (l.niveau - 1) * (l.niveau - 1) - xp
            return "Prochaine leçon au niveau ${l.niveau} : il me manque $manque XP.\n" +
                "Nourris-moi avec des commandes jamais goûtées (📖 Lexique) !"
        }
        val e = l.etapes[etape]
        val astuce = if (e.astuce != null) "\n${e.astuce}" else ""
        return "${l.titre} (${etape + 1}/${l.etapes.size}) · ${e.dit}\n➜ ${Regles.piege(e.cmd)}$astuce"
    }

    fun infoWidget(): String {
        val b = bulleActive()
        if (b.isNotEmpty()) return "« $b »"
        val e = etapeCourante()
        if (e != null) return "Leçon ➜ ${Regles.piege(e.cmd)}"
        return journal.lastOrNull()?.drop(6) ?: "Touche le bouton pour me nourrir !"
    }
}
