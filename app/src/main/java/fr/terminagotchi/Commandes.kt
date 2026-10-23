package fr.terminagotchi

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.net.Uri
import android.os.BatteryManager
import android.os.VibrationEffect
import android.os.Vibrator
import android.provider.Settings
import android.speech.tts.TextToSpeech
import java.io.File
import java.util.Locale

/**
 * Commandes intégrées à l'appli :
 *  - 📱 piloter le téléphone (ouvrir une appli, un site, un SMS, la lampe…)
 *  - 🐾 jouer avec la créature (caresse, joue, devine…)
 * Comme les commandes « termux-… » de Termux : des outils du terminal propres à cette appli.
 */
class Commandes(private val act: Activity, private val jeu: Jeu, private val dossier: () -> File) {

    /** aller : dossier où emmener le joueur après la commande (donjon, ctf…). */
    class Reponse(val texte: String, val saut: Int = 0, val couleur: Int? = null, val aller: File? = null)

    private var tts: TextToSpeech? = null
    private var ttsPret = false
    private var aDire: String? = null
    private var nombreSecret = 0
    private var essais = 0

    fun fermer() {
        tts?.shutdown()
    }

    /** Renvoie null si ce n'est pas une commande intégrée (elle part alors au vrai shell). */
    fun executer(ligne: String): Reponse? {
        val mots = ligne.trim().split(Regex("\\s+"))
        val cmd = mots.first().lowercase()
        val reste = ligne.trim().substringAfter(' ', "").trim()
        return when (cmd) {
            // ---------------------------------------------------- téléphone
            "applis" -> applis(reste)
            "ouvre" -> ouvre(reste)
            "web" -> web(reste)
            "carte" -> lancer(Intent(Intent.ACTION_VIEW, Uri.parse("geo:0,0?q=" + Uri.encode(reste))),
                "🗺 Je cherche « $reste » dans les cartes.", "carte gare de lyon", reste)
            "appelle" -> lancer(Intent(Intent.ACTION_DIAL, Uri.parse("tel:" + Uri.encode(reste))),
                "📞 Le numéro est prêt : c'est toi qui appuies sur Appeler.", "appelle 0612345678", reste)
            "sms" -> sms(mots)
            "partage" -> partage(reste)
            "lampe" -> lampe(mots.getOrNull(1))
            "vibre" -> vibre(mots.getOrNull(1))
            "batterie" -> batterie()
            "dis" -> dis(reste)
            "reglages" -> reglages(mots.getOrNull(1))
            // ---------------------------------------------------- créature
            "caresse" -> Reponse(listOf("Rrrrr… 💜", "Hihi, ça chatouille !", "Encore, encore !",
                "*ferme les yeux de bonheur*").random(), saut = 2, couleur = ROSE)
            "danse" -> Reponse(listOf("♪ ┏(・o･)┛ ♪ ┗( ･o･)┓ ♪", "♫ \\(^o^)/ ♫ \\(^o^)/ ♫",
                "*tourne sur lui-même en pixels*").random(), saut = 8, couleur = ROSE)
            "parle" -> Reponse("« ${(Regles.TRAITS[jeu.trait] ?: Regles.OEUF).random()} »", couleur = ROSE)
            "joue" -> joue(mots.getOrNull(1))
            "devine" -> devine(mots.getOrNull(1))
            "etat" -> etat()
            "renomme" -> renomme(reste)
            // ---------------------------------------------------- progression et jeux
            "arbre" -> arbre(reste)
            "collection" -> Reponse(Explo.texteCollection(jeu), couleur = ROSE)
            "cherche" -> Reponse(Recherche.chercher(reste), couleur = BLEU)
            "defi" -> if (reste == "records") Reponse(Defis.texteRecords(jeu))
                else { Defis.lancer(jeu); Reponse("⚡ Défi lancé : regarde la bulle !", saut = 2, couleur = JAUNE) }
            "donjon" -> Donjon.entrer(jeu, reste).let { Reponse(it.texte, saut = 2, couleur = JAUNE, aller = it.aller) }
            "plan" -> Reponse(Donjon.plan(jeu, dossier()), couleur = JAUNE)
            "quetes" -> Reponse(Donjon.texteQuetes(jeu), couleur = JAUNE)
            "sac" -> Reponse(Donjon.texteSac(jeu), couleur = JAUNE)
            "equipe" -> Reponse(Donjon.equipe(jeu, reste), saut = 2, couleur = JAUNE)
            "bois" -> Reponse(Donjon.bois(jeu, reste), saut = 2, couleur = JAUNE)
            "attaque" -> Donjon.attaque(jeu, dossier()).let { Reponse(it.texte, saut = 6, couleur = JAUNE, aller = it.aller) }
            "ctf" -> Ctf.ouvrir(jeu, reste).let { Reponse(it.first, couleur = VERT, aller = it.second) }
            "drapeau" -> Reponse(Ctf.valider(jeu, reste), saut = 4, couleur = VERT)
            "indice" -> Reponse(Ctf.indice(jeu, reste), couleur = VERT)
            "edite" -> edite(reste)
            "doom" -> doom()
            "notifs" -> notifs(reste)
            else -> null
        }
    }

    // ---------------------------------------------------------------- téléphone
    private fun lancer(intent: Intent, ok: String, exemple: String, arg: String = "x"): Reponse {
        if (arg.isEmpty()) return Reponse("Il manque quelque chose après la commande. Exemple : $exemple", couleur = ORANGE)
        return try {
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            act.startActivity(intent)
            Reponse(ok, saut = 2)
        } catch (e: ActivityNotFoundException) {
            Reponse("Aucune appli ne sait faire ça sur ce téléphone.", couleur = ORANGE)
        }
    }

    private fun applisInstallees(): List<Pair<String, String>> {
        val pm = act.packageManager
        val i = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        return pm.queryIntentActivities(i, 0)
            .map { it.loadLabel(pm).toString() to it.activityInfo.packageName }
            .distinctBy { it.second }
            .sortedBy { it.first.lowercase() }
    }

    private fun applis(filtre: String): Reponse {
        val liste = applisInstallees().filter { filtre.isEmpty() || it.first.contains(filtre, true) }
        if (liste.isEmpty()) return Reponse("Aucune appli ne contient « $filtre ».", couleur = ORANGE)
        val txt = liste.joinToString("\n") { "• ${it.first}" }
        return Reponse("$txt\n(${liste.size} applis · lance-en une avec : ouvre <nom>)")
    }

    private fun ouvre(nom: String): Reponse {
        if (nom.isEmpty()) return Reponse("Quelle appli ? Exemple : ouvre whatsapp (la liste : applis)", couleur = ORANGE)
        val toutes = applisInstallees()
        val choix = toutes.firstOrNull { it.first.equals(nom, true) }
            ?: toutes.firstOrNull { it.first.startsWith(nom, true) }
            ?: toutes.firstOrNull { it.first.contains(nom, true) }
            ?: toutes.firstOrNull { it.second.contains(nom, true) }
            ?: return Reponse("Je ne trouve pas « $nom ». Tape « applis » pour voir la liste.", couleur = ORANGE)
        val intent = act.packageManager.getLaunchIntentForPackage(choix.second)
            ?: return Reponse("Impossible d'ouvrir ${choix.first}.", couleur = ORANGE)
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        act.startActivity(intent)
        return Reponse("🚀 J'ouvre ${choix.first} !  (son nom secret : ${choix.second})", saut = 3)
    }

    private fun web(texte: String): Reponse {
        val url = when {
            texte.isEmpty() -> return Reponse("Une adresse ou une recherche ? Exemple : web météo paris", couleur = ORANGE)
            texte.startsWith("http://") || texte.startsWith("https://") -> texte
            !texte.contains(' ') && texte.contains('.') -> "https://$texte"
            else -> "https://duckduckgo.com/?q=" + Uri.encode(texte)
        }
        return lancer(Intent(Intent.ACTION_VIEW, Uri.parse(url)), "🌐 J'ouvre $url", "web wikipedia.org")
    }

    private fun sms(mots: List<String>): Reponse {
        val numero = mots.getOrNull(1) ?: return Reponse("Exemple : sms 0612345678 coucou !", couleur = ORANGE)
        val message = mots.drop(2).joinToString(" ")
        val i = Intent(Intent.ACTION_SENDTO, Uri.parse("smsto:" + Uri.encode(numero)))
        if (message.isNotEmpty()) i.putExtra("sms_body", message)
        return lancer(i, "✉ Ton SMS est prêt : vérifie-le et appuie sur Envoyer.", "sms 0612345678 coucou")
    }

    private fun partage(texte: String): Reponse {
        if (texte.isEmpty()) return Reponse("Quel texte ? Exemple : partage Rendez-vous à 18h !", couleur = ORANGE)
        val i = Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, texte)
        return lancer(Intent.createChooser(i, "Partager avec…"), "📤 Choisis l'appli pour envoyer ton message.", "")
    }

    private fun lampe(etat: String?): Reponse {
        val allumer = when (etat?.lowercase()) {
            "on" -> true
            "off" -> false
            else -> return Reponse("Exemple : lampe on  (ou lampe off)", couleur = ORANGE)
        }
        return try {
            val cm = act.getSystemService(Context.CAMERA_SERVICE) as CameraManager
            val id = cm.cameraIdList.firstOrNull {
                cm.getCameraCharacteristics(it).get(CameraCharacteristics.FLASH_INFO_AVAILABLE) == true
            } ?: return Reponse("Pas de lampe torche sur ce téléphone.", couleur = ORANGE)
            cm.setTorchMode(id, allumer)
            Reponse(if (allumer) "🔦 Lumière !" else "🌑 Lampe éteinte.", saut = 2)
        } catch (e: Exception) {
            Reponse("La lampe n'a pas voulu : ${e.message}", couleur = ORANGE)
        }
    }

    @Suppress("DEPRECATION")
    private fun vibre(duree: String?): Reponse {
        val ms = duree?.toLongOrNull()?.coerceIn(50, 3000) ?: 400L
        val v = act.getSystemService(Context.VIBRATOR_SERVICE) as Vibrator
        v.vibrate(VibrationEffect.createOneShot(ms, VibrationEffect.DEFAULT_AMPLITUDE))
        return Reponse("📳 Bzzz ($ms ms)", saut = 3)
    }

    private fun batterie(): Reponse {
        val bm = act.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
        val pct = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        val charge = if (bm.isCharging) "en charge ⚡" else "sur batterie"
        return Reponse("🔋 $pct % · $charge")
    }

    private fun dis(texte: String): Reponse {
        if (texte.isEmpty()) return Reponse("Quoi dire ? Exemple : dis bonjour tout le monde", couleur = ORANGE)
        if (tts == null) {
            aDire = texte
            tts = TextToSpeech(act) { statut ->
                if (statut == TextToSpeech.SUCCESS) {
                    ttsPret = true
                    tts?.language = Locale.FRANCE
                    aDire?.let { tts?.speak(it, TextToSpeech.QUEUE_FLUSH, null, "tg") }
                    aDire = null
                }
            }
        } else if (ttsPret) {
            tts?.speak(texte, TextToSpeech.QUEUE_FLUSH, null, "tg")
        }
        return Reponse("🗣 « $texte »", saut = 2)
    }

    private fun reglages(quoi: String?): Reponse {
        val action = when (quoi?.lowercase()) {
            null, "" -> Settings.ACTION_SETTINGS
            "wifi" -> Settings.ACTION_WIFI_SETTINGS
            "bluetooth" -> Settings.ACTION_BLUETOOTH_SETTINGS
            "son" -> Settings.ACTION_SOUND_SETTINGS
            "ecran" -> Settings.ACTION_DISPLAY_SETTINGS
            "batterie" -> Intent.ACTION_POWER_USAGE_SUMMARY
            "applis" -> Settings.ACTION_APPLICATION_SETTINGS
            else -> return Reponse("Réglages possibles : wifi, bluetooth, son, ecran, batterie, applis", couleur = ORANGE)
        }
        return lancer(Intent(action), "⚙ J'ouvre les réglages ${quoi ?: ""}".trim(), "")
    }

    // ---------------------------------------------------------------- progression et jeux
    private fun arbre(choix: String): Reponse {
        if (choix.isEmpty()) return Reponse(Arbre.texte(jeu), couleur = ROSE)
        if (!jeu.troncFini) return Reponse("Termine d'abord le tronc commun (la leçon en rose) !", couleur = ORANGE)
        val cle = choix.lowercase().replace("é", "e").replace("è", "e")
        val b = jeu.branches[cle] ?: return Reponse("Branches : ${Arbre.ORDRE.joinToString(", ")}", couleur = ORANGE)
        if (jeu.progresBranche(cle) >= b.lecons.size) return Reponse("Tu maîtrises déjà ${b.nom} !", couleur = ROSE)
        jeu.choisirBranche(cle)
        jeu.dire("Branche ${b.nom} ! Suis la leçon en rose.", 10)
        return Reponse("${b.icone} Branche ${b.nom} choisie : ${b.desc}.", saut = 3, couleur = ROSE)
    }

    private fun edite(nom: String): Reponse {
        if (nom.isEmpty()) return Reponse("Quel fichier ? Exemple : edite notes.txt", couleur = ORANGE)
        val f = when {
            nom.startsWith("~/") -> File(jeu.home, nom.removePrefix("~/"))
            nom.startsWith("/") -> File(nom)
            else -> File(dossier(), nom)
        }
        if (!f.canonicalPath.startsWith(jeu.home.canonicalPath)) {
            return Reponse("Je ne peux modifier que les fichiers de ta maison (~).", couleur = ORANGE)
        }
        if (f.isDirectory) return Reponse("${f.name} est un dossier, pas un fichier.", couleur = ORANGE)
        act.startActivity(Intent(act, EditeurActivity::class.java).putExtra("chemin", f.absolutePath))
        return Reponse("✏ J'ouvre l'éditeur sur ${f.name}… (comme nano sur un ordinateur)")
    }

    private fun doom(): Reponse {
        if (!File(jeu.terrain, "nid").isDirectory) {
            return Reponse("Le jeu s'ouvre après la leçon « Construire mon nid ».", couleur = ORANGE)
        }
        Doom.preparer(jeu)
        act.startActivity(Intent(act, DoomActivity::class.java))
        return Reponse("🎮 Lancement… Ton niveau : ~/terrain_terminagotchi/jeu/carte.txt", saut = 4)
    }

    private fun notifs(choix: String): Reponse {
        val n = jeu.module("notifs")
        when (choix.lowercase()) {
            "on" -> n.put("actives", true)
            "off" -> n.put("actives", false)
            else -> return Reponse("Notifications : ${if (n.optBoolean("actives", true)) "activées" else "coupées"}  (notifs on / notifs off)")
        }
        return Reponse(if (n.optBoolean("actives")) "🔔 Je te préviendrai quand j'aurai faim." else "🔕 Plus de notifications.")
    }

    // ---------------------------------------------------------------- créature
    private fun joue(coup: String?): Reponse {
        val coups = listOf("pierre", "feuille", "ciseaux")
        val toi: String = coup?.lowercase() ?: ""
        if (toi !in coups) return Reponse("On joue à pierre-feuille-ciseaux ! Tape : joue pierre (ou feuille, ciseaux)", couleur = ROSE)
        val moi = coups.random()
        val emoji = mapOf("pierre" to "🪨", "feuille" to "📄", "ciseaux" to "✂")
        val resultat = when {
            moi == toi -> "Égalité !"
            (toi == "pierre" && moi == "ciseaux") || (toi == "feuille" && moi == "pierre") ||
                (toi == "ciseaux" && moi == "feuille") -> "Tu gagnes… je veux ma revanche !"
            else -> "J'ai gagné ! Hihi."
        }
        return Reponse("Toi ${emoji[toi]}  ·  ${jeu.nom} ${emoji[moi]}  →  $resultat", saut = 3, couleur = ROSE)
    }

    private fun devine(n: String?): Reponse {
        if (nombreSecret == 0) {
            nombreSecret = (1..20).random()
            essais = 0
            if (n == null) return Reponse("J'ai choisi un nombre entre 1 et 20. Devine-le : devine 10", couleur = ROSE)
        }
        val k = n?.toIntOrNull() ?: return Reponse("Tape un nombre, par exemple : devine 10", couleur = ROSE)
        essais++
        return when {
            k < nombreSecret -> Reponse("C'est plus ! ⬆", couleur = ROSE)
            k > nombreSecret -> Reponse("C'est moins ! ⬇", couleur = ROSE)
            else -> {
                nombreSecret = 0
                jeu.ajouterXp(if (essais <= 5) 10 else 5)
                Reponse("🎉 Bravo, c'était $k ! Trouvé en $essais essai(s). (+XP) Rejoue avec : devine", saut = 8, couleur = ROSE)
            }
        }
    }

    private fun etat(): Reponse {
        val texte = listOf(
            jeu.titre(), jeu.texteFaim(), jeu.texteXp(), jeu.texteStats(),
            "caractère : ${jeu.trait} · commandes mangées : ${jeu.total} · goûts découverts : ${jeu.vus.size}",
            "compétences : " + (if (jeu.skills.isEmpty()) "aucune" else jeu.skills.joinToString(", ")),
        ).joinToString("\n")
        return Reponse(texte, couleur = ROSE)
    }

    private fun renomme(nom: String): Reponse {
        if (nom.isEmpty()) return Reponse("Exemple : renomme Pixel", couleur = ORANGE)
        val ancien = jeu.nom
        jeu.nom = nom.take(16)
        return Reponse("Je ne m'appelle plus $ancien… je suis ${jeu.nom} !", saut = 3, couleur = ROSE)
    }

    companion object {
        val ROSE = 0xFFFF87FF.toInt()
        val BLEU = 0xFF87AFFF.toInt()
        val JAUNE = 0xFFFFD787.toInt()
        val VERT = 0xFF87FFAF.toInt()
        val ORANGE = 0xFFFFAF5F.toInt()
        val CREATURE = setOf("caresse", "danse", "parle", "joue", "devine", "etat", "renomme")
        val TELEPHONE = setOf("applis", "ouvre", "web", "carte", "appelle", "sms", "partage", "lampe", "vibre",
            "batterie", "dis", "reglages")
    }
}
