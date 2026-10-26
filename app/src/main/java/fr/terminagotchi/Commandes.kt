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
import org.json.JSONObject
import java.io.File
import java.util.Locale

/**
 * Commandes intégrées à l'appli :
 *  - 📱 piloter le téléphone (ouvrir une appli, un site, un SMS, la lampe…)
 *  - 🐾 jouer avec la créature (caresse, joue, devine…)
 * Comme les commandes « termux-… » de Termux : des outils du terminal propres à cette appli.
 */
class Commandes(
    private val act: Activity,
    private val jeu: Jeu,
    private val dossier: () -> File,
    /** pour les réponses qui arrivent plus tard (réseau) */
    private val plusTard: (String, Int?) -> Unit = { _, _ -> },
) {

    /** aller : dossier où emmener le joueur après la commande (donjon, ctf…). */
    /** petit : en plus petit (la carte de la maison tient alors dans la largeur de l'écran). */
    /** carte : ouvrir la carte qui pousse (CarteVue) ; texte est alors la même carte en `tree` annoté. */
    class Reponse(val texte: String, val saut: Int = 0, val couleur: Int? = null, val aller: File? = null, val petit: Boolean = false,
                  val carte: Boolean = false)

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
            // carte tout seul : la carte qui pousse (le Terminaworld) ; carte <lieu> : un plan de la ville (appli de cartes)
            "carte" -> if (reste.isEmpty()) Reponse(Maison.carte(jeu.also { Histoire.h(it) }).joinToString("\n"), couleur = ROSE, petit = true, carte = true)
                else lancer(Intent(Intent.ACTION_VIEW, Uri.parse("geo:0,0?q=" + Uri.encode(reste))),
                t("tel.carte.ok", "q" to reste), "carte gare de lyon", reste)
            "appelle" -> lancer(Intent(Intent.ACTION_DIAL, Uri.parse("tel:" + Uri.encode(reste))),
                t("tel.appelle.ok"), "appelle 0612345678", reste)
            "sms" -> sms(mots)
            "partage" -> partage(reste)
            "lampe" -> lampe(mots.getOrNull(1))
            "vibre" -> vibre(mots.getOrNull(1))
            "batterie" -> batterie()
            "dis" -> dis(reste)
            "reglages" -> reglages(mots.getOrNull(1))
            // ---------------------------------------------------- créature
            "caresse" -> jeu.animer("content").let { Reponse(Regles.auHasard("cre.caresse"), saut = 2, couleur = ROSE) }
            "danse" -> jeu.animer("victoire").let { Reponse(Regles.auHasard("cre.danse"), saut = 8, couleur = ROSE) }
            "parle" -> jeu.animer("parle").let { Reponse("« ${Regles.auHasard(Regles.TRAITS[jeu.trait] ?: Regles.OEUF)} »", couleur = ROSE) }
            "joue" -> joue(mots.getOrNull(1))
            "devine" -> devine(mots.getOrNull(1))
            "etat" -> etat()
            "envies", "envie" -> Reponse(Envies.ecran(jeu), couleur = ROSE)
            // ---------------------------------------------------- salle d'entraînement (Entrainement.kt)
            "entrainement", "exercice" -> Reponse(Entrainement.commande(jeu, reste, dossier()), couleur = JAUNE)
            "badges" -> Reponse(Entrainement.commandeBadges(jeu, reste), couleur = ROSE)
            "renomme" -> renomme(reste)
            // ---------------------------------------------------- progression et jeux
            "arbre", "aile", "ailes", "histoire" -> aile(reste)
            "collection" -> Reponse(Explo.texteCollection(jeu), couleur = ROSE)
            "troupe" -> Reponse(if (reste.isBlank()) Equipe.texte(jeu) else Equipe.choisir(jeu, reste), couleur = ROSE)
            "anime" -> {
                val m = reste.split(Regex("\\s+")).filter { it.isNotEmpty() }
                val e = m.getOrNull(0)?.let { Bestiaire.espece(it) }
                val caps = Explo.captures(jeu)
                val ind = if (e == null) Equipe.active(jeu) else (caps.length() - 1 downTo 0).map { caps.getJSONObject(it) }
                    .firstOrNull { it.optString("espece") == e.nom }
                if (ind == null) Reponse(t("eq.aucune.tel"), couleur = ORANGE)
                else Reponse(Animations.jouer(act, ind, m.getOrNull(1) ?: ""), couleur = ROSE)
            }
            "dressage" -> Reponse(if (reste.trim() == "abandon") Dressage.abandonner(jeu) else t("dressa.abandon.aide"), couleur = ROSE)
            "cherche" -> Reponse(Recherche.chercher(reste), couleur = BLEU)
            "defi" -> if (reste == "records") Reponse(Defis.texteRecords(jeu))
                else { Defis.lancer(jeu); Reponse(t("defi.lance"), saut = 2, couleur = JAUNE) }
            "donjon" -> Donjon.entrer(jeu, reste).let { Reponse(it.texte, saut = 2, couleur = JAUNE, aller = it.aller) }
            "plan" -> Reponse(Donjon.plan(jeu, dossier()), couleur = JAUNE)
            "quetes", "quete", "journal" -> quetes(reste)
            "sac" -> Reponse(Donjon.texteSac(jeu), couleur = JAUNE)
            "equipe" -> Reponse(Donjon.equipe(jeu, reste), saut = 2, couleur = JAUNE)
            "bois" -> Reponse(Donjon.bois(jeu, reste), saut = 2, couleur = JAUNE)
            "attaque" -> Donjon.attaque(jeu, dossier()).let { Reponse(it.texte, saut = 6, couleur = JAUNE, aller = it.aller) }
            "ctf" -> Ctf.ouvrir(jeu, reste).let { Reponse(it.first, couleur = VERT, aller = it.second) }
            "drapeau" -> drapeau(reste)
            "compte" -> compte(reste)
            "site" -> site(reste)
            "bestiaire" -> Reponse(Explo.fiche(jeu, reste), couleur = ROSE)
            "explique" -> Reponse(Explique.fiche(jeu, reste), couleur = BLEU)
            "sync" -> sync()
            "indice" -> Reponse(Ctf.indice(jeu, reste), couleur = VERT)
            "edite" -> edite(reste)
            "doom" -> doom()
            "notifs" -> notifs(reste)
            "notif" -> notifVie(reste)
            else -> null
        }
    }

    // ---------------------------------------------------------------- téléphone
    private fun lancer(intent: Intent, ok: String, exemple: String, arg: String = "x"): Reponse {
        if (arg.isEmpty()) return Reponse(t("tel.manque", "exemple" to exemple), couleur = ORANGE)
        return try {
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            act.startActivity(intent)
            Reponse(ok, saut = 2)
        } catch (e: ActivityNotFoundException) {
            Reponse(t("tel.aucune_appli"), couleur = ORANGE)
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
        if (liste.isEmpty()) return Reponse(t("tel.applis.aucune", "filtre" to filtre), couleur = ORANGE)
        val txt = liste.joinToString("\n") { "• ${it.first}" }
        return Reponse(txt + "\n" + t("tel.applis.pied", "n" to liste.size))
    }

    private fun ouvre(nom: String): Reponse {
        if (nom.isEmpty()) return Reponse(t("tel.ouvre.exemple"), couleur = ORANGE)
        val toutes = applisInstallees()
        val choix = toutes.firstOrNull { it.first.equals(nom, true) }
            ?: toutes.firstOrNull { it.first.startsWith(nom, true) }
            ?: toutes.firstOrNull { it.first.contains(nom, true) }
            ?: toutes.firstOrNull { it.second.contains(nom, true) }
            ?: return Reponse(t("tel.ouvre.introuvable", "nom" to nom), couleur = ORANGE)
        val intent = act.packageManager.getLaunchIntentForPackage(choix.second)
            ?: return Reponse(t("tel.ouvre.impossible", "nom" to choix.first), couleur = ORANGE)
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        act.startActivity(intent)
        return Reponse(t("tel.ouvre.ok", "nom" to choix.first, "paquet" to choix.second), saut = 3)
    }

    private fun web(texte: String): Reponse {
        val url = when {
            texte.isEmpty() -> return Reponse(t("tel.web.exemple"), couleur = ORANGE)
            texte.startsWith("http://") || texte.startsWith("https://") -> texte
            !texte.contains(' ') && texte.contains('.') -> "https://$texte"
            else -> "https://duckduckgo.com/?q=" + Uri.encode(texte)
        }
        return lancer(Intent(Intent.ACTION_VIEW, Uri.parse(url)), t("tel.web.ok", "url" to url), "web wikipedia.org")
    }

    private fun sms(mots: List<String>): Reponse {
        val numero = mots.getOrNull(1) ?: return Reponse(t("tel.sms.exemple"), couleur = ORANGE)
        val message = mots.drop(2).joinToString(" ")
        val i = Intent(Intent.ACTION_SENDTO, Uri.parse("smsto:" + Uri.encode(numero)))
        if (message.isNotEmpty()) i.putExtra("sms_body", message)
        return lancer(i, t("tel.sms.ok"), "sms 0612345678 coucou")
    }

    private fun partage(texte: String): Reponse {
        if (texte.isEmpty()) return Reponse(t("tel.partage.exemple"), couleur = ORANGE)
        val i = Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, texte)
        return lancer(Intent.createChooser(i, t("tel.partage.titre")), t("tel.partage.ok"), "")
    }

    private fun lampe(etat: String?): Reponse {
        val allumer = when (etat?.lowercase()) {
            "on" -> true
            "off" -> false
            else -> return Reponse(t("tel.lampe.exemple"), couleur = ORANGE)
        }
        return try {
            val cm = act.getSystemService(Context.CAMERA_SERVICE) as CameraManager
            val id = cm.cameraIdList.firstOrNull {
                cm.getCameraCharacteristics(it).get(CameraCharacteristics.FLASH_INFO_AVAILABLE) == true
            } ?: return Reponse(t("tel.lampe.aucune"), couleur = ORANGE)
            cm.setTorchMode(id, allumer)
            Reponse(if (allumer) t("tel.lampe.on") else t("tel.lampe.off"), saut = 2)
        } catch (e: Exception) {
            Reponse(t("tel.lampe.erreur", "msg" to e.message), couleur = ORANGE)
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
        val charge = if (bm.isCharging) t("tel.batterie.charge") else t("tel.batterie.batterie")
        return Reponse("🔋 $pct % · $charge")
    }

    private fun dis(texte: String): Reponse {
        if (texte.isEmpty()) return Reponse(t("tel.dis.exemple"), couleur = ORANGE)
        if (tts == null) {
            aDire = texte
            tts = TextToSpeech(act) { statut ->
                if (statut == TextToSpeech.SUCCESS) {
                    ttsPret = true
                    tts?.language = Locale.forLanguageTag(Langue.courante)
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
            else -> return Reponse(t("tel.reglages.possibles"), couleur = ORANGE)
        }
        return lancer(Intent(action), t("tel.reglages.ok", "quoi" to (quoi ?: "")).trim(), "")
    }

    // ---------------------------------------------------------------- recensement (en ligne)
    /** Lance un appel réseau hors de l'écran, puis affiche le résultat dans le terminal. */
    private fun enLigne(travail: () -> JSONObject, ensuite: (JSONObject) -> String) {
        Thread {
            val r = travail()
            act.runOnUiThread {
                val msg = ensuite(r)
                jeu.sauver()
                plusTard(msg, BLEU)
            }
        }.start()
    }

    private fun adresse(): String = Recensement.serveur(Recensement.compte(jeu).optString("serveur"))

    fun sync(forcer: Boolean = true, silencieux: Boolean = false): Reponse {
        val p = Recensement.preparer(jeu, forcer)
            ?: return Reponse(if (Recensement.aUnCompte(jeu)) t("reca.sync.en_cours") else
                t("reca.pas_de_compte"), couleur = BLEU)
        val partie = jeu.partie
        Thread {
            val (r, url) = Recensement.envoyer(p)
            act.runOnUiThread {
                // on a changé de partie pendant la synchro : la réponse n'est pas pour celle-ci
                if (jeu.partie != partie) { Recensement.abandonner(); return@runOnUiThread }
                val msg = Recensement.appliquer(jeu, p, r, url)
                jeu.sauver()
                // synchro automatique : on ne parle que s'il y a du nouveau (XP venue d'ailleurs, badge)
                val nouveau = Recensement.nouveau
                if (!silencieux || nouveau) plusTard(msg, BLEU)
            }
        }.start()
        return Reponse(if (silencieux) "" else t("reca.sync"), couleur = BLEU)
    }

    private fun compte(reste: String): Reponse {
        val mots = reste.split(Regex("\\s+")).filter { it.isNotEmpty() }
        val c = Recensement.compte(jeu)
        val action = mots.firstOrNull()?.lowercase() ?: ""
        when (action) {
            "serveur" -> {
                val u = mots.getOrNull(1) ?: return Reponse(t("rec.adresse", "url" to c.optString("serveur").ifEmpty { t("reca.automatique") }))
                c.put("serveur", u.trimEnd('/'))
                return Reponse(t("rec.adresse.reglee", "url" to u), couleur = BLEU)
            }
            "creer" -> {
                if (Recensement.aUnCompte(jeu)) return Reponse(t("reca.deja_compte", "pseudo" to c.optString("pseudo")), couleur = ORANGE)
                val pseudo = mots.getOrNull(1) ?: return Reponse(t("rec.creer.exemple"), couleur = ORANGE)
                var url = ""
                enLigne({
                    url = adresse()
                    if (url.isEmpty()) JSONObject().put("erreur", t("reca.err.pas_en_ligne"))
                    else Recensement.requete("$url/api/inscription", "POST",
                        JSONObject().put("pseudo", pseudo).put("appareil", Recensement.APPAREIL))
                }) { r ->
                    if (!r.has("cle")) return@enLigne "⚠ " + r.optString("erreur", t("rec.err.inscription"))
                    relier(r, url)
                    t("reca.bienvenue",
                        "pseudo" to r.getString("pseudo"), "url" to "$url/joueur/${r.getString("pseudo")}") + texteSecours(r)
                }
                return Reponse(t("reca.inscription"), couleur = BLEU)
            }
            "lier" -> {
                val code = mots.getOrNull(1) ?: return Reponse(t("reca.lier.exemple"), couleur = ORANGE)
                var url = ""
                enLigne({
                    url = adresse()
                    if (url.isEmpty()) JSONObject().put("erreur", t("reca.err.pas_en_ligne"))
                    else Recensement.requete("$url/api/lier", "POST",
                        JSONObject().put("code", code).put("appareil", Recensement.APPAREIL))
                }) { r ->
                    if (!r.has("cle")) return@enLigne "⚠ " + r.optString("erreur", t("rec.err.liaison"))
                    relier(r, url)
                    t("reca.relie", "pseudo" to r.getString("pseudo"))
                }
                return Reponse(t("reca.liaison"), couleur = BLEU)
            }
            "secours" -> {
                val code = mots.getOrNull(1) ?: return Reponse(t("rec.secours.exemple"), couleur = ORANGE)
                var url = ""
                enLigne({
                    url = adresse()
                    if (url.isEmpty()) JSONObject().put("erreur", t("reca.err.pas_en_ligne"))
                    else Recensement.requete("$url/api/secours/recuperer", "POST",
                        JSONObject().put("code", code).put("appareil", Recensement.APPAREIL))
                }) { r ->
                    if (!r.has("cle")) return@enLigne "⚠ " + r.optString("erreur", t("reca.secours.refuse"))
                    relier(r, url)
                    t("reca.secours.ok", "pseudo" to r.getString("pseudo"))
                }
                return Reponse(t("reca.secours.cherche"), couleur = BLEU)
            }
            "partage" -> {
                val choix = mots.getOrNull(1)?.lowercase()
                if (choix != "on" && choix != "off") {
                    val etat = if (c.optJSONObject("partage")?.optBoolean("actif") == true) t("rec.active") else t("rec.desactive")
                    return Reponse(t("reca.partage.etat", "etat" to etat), couleur = BLEU)
                }
                c.put("partage", JSONObject().put("actif", choix == "on").put("date", System.currentTimeMillis()))
                if (Recensement.aUnCompte(jeu)) sync(forcer = true)
                return Reponse(if (choix == "on") t("reca.partage.on")
                    else t("rec.partage.off"), couleur = BLEU)
            }
            "oublier", "deconnexion", "sortir" -> {
                val cle = c.optString("cle")
                if (cle.isNotEmpty()) Thread {             // le site oublie la clé de ce téléphone
                    try { adresse().takeIf { it.isNotEmpty() }?.let { Recensement.requete("$it/api/deconnexion", "POST", JSONObject(), cle) } }
                    catch (e: Exception) { }
                }.start()
                // on garde l'adresse du site et le point de synchro de cette partie (pas de double envoi si on revient)
                Parties.baseDe(c).takeIf { it.isNotEmpty() }?.let { c.put("base_de", it) }
                c.remove("cle")
                c.remove("pseudo")
                c.remove("parties_cache")
                return Reponse(t("reca.oublie"), couleur = BLEU)
            }
        }
        if (!Recensement.aUnCompte(jeu)) {
            return Reponse(t("reca.sans_compte"), couleur = BLEU)
        }
        val cle = c.optString("cle")
        if (action == "code") {
            enLigne({
                val url = adresse()
                if (url.isEmpty()) JSONObject().put("erreur", t("reca.err.pas_en_ligne"))
                else Recensement.requete("$url/api/code", "POST", JSONObject(), cle)
            }) { r ->
                val jeton = r.optString("jeton", r.optString("code"))
                if (!r.has("code")) "⚠ " + r.optString("erreur", t("rec.err.code"))
                else t("reca.code", "code" to jeton)
            }
            return Reponse(t("reca.code.demande"), couleur = BLEU)
        }
        if (action == "site") {
            enLigne({
                val url = adresse()
                if (url.isEmpty()) JSONObject().put("erreur", t("reca.err.pas_en_ligne"))
                else Recensement.requete("$url/api/lien-site", "POST", JSONObject(), cle).put("_url", url)
            }) { r ->
                val lien = r.optString("lien")
                if (lien.isEmpty()) return@enLigne "⚠ " + r.optString("erreur", t("reca.err.lien"))
                val complet = r.optString("_url") + lien
                try {
                    act.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(complet)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                } catch (e: ActivityNotFoundException) {
                }
                t("rec.lien_site", "lien" to complet)
            }
            return Reponse(t("reca.lien.prepare"), couleur = BLEU)
        }
        val dernier = c.optLong("dernier")
        val quand = if (dernier > 0) java.text.SimpleDateFormat("HH:mm", java.util.Locale.FRANCE).format(java.util.Date(dernier)) else t("rec.jamais")
        val url = c.optString("serveur")
        return Reponse(t("reca.resume", "pseudo" to c.optString("pseudo"), "quand" to quand,
            "profil" to "$url/joueur/${c.optString("pseudo")}", "ctf" to "$url/ctf"), couleur = BLEU)
    }

    /** Le compte arrive dans la partie active (il suivra le joueur dans ses autres parties, voir Parties.kt). */
    private fun relier(r: JSONObject, url: String) {
        val pseudo = r.getString("pseudo")
        val c = Recensement.compte(jeu)
        val base = c.optJSONObject("base")
        val avant = Parties.baseDe(c)
        Recensement.enregistrer(jeu, pseudo, r.getString("cle"), url)
        // cette partie était déjà synchronisée avec CE compte : on n'envoie pas deux fois la même progression
        if (avant == pseudo && base != null) Recensement.compte(jeu).put("base", base)
        Recensement.compte(jeu).put("base_de", pseudo)
        jeu.sauver()
        sync(forcer = true)
    }

    private fun texteSecours(r: JSONObject): String {
        val s = r.optString("secours")
        if (s.isEmpty()) return ""
        return "\n\n" + t("reca.secours.donne", "code" to s)
    }

    /** site [bestiaire|captures|classement|ctf] : ouvre le site du recensement dans le navigateur. */
    private fun site(reste: String): Reponse {
        val c = Recensement.compte(jeu)
        val chemins = mapOf("bestiaire" to "/bestiaire", "captures" to "/captures", "classement" to "/classement", "ctf" to "/ctf")
        val page = reste.trim().lowercase()
        val pseudo = c.optString("pseudo")
        val suite = chemins[page] ?: if (pseudo.isNotEmpty()) "/joueur/$pseudo" else ""
        val connu = c.optString("serveur")
        Thread {
            val url = Recensement.serveur(connu)
            act.runOnUiThread {
                if (url.isEmpty()) {
                    plusTard(t("rec.site.injoignable"), ORANGE)
                } else {
                    try {
                        act.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url + suite)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
                        plusTard("🌍 $url$suite", BLEU)
                    } catch (e: ActivityNotFoundException) {
                        plusTard("🌍 $url$suite  " + t("reca.site.sans_navigateur"), BLEU)
                    }
                }
            }
        }.start()
        return Reponse(t("reca.site.ouvre"), couleur = BLEU)
    }

    private fun drapeau(proposition: String): Reponse {
        val local = Ctf.valider(jeu, proposition)
        if (!local.startsWith("❌") || !Recensement.aUnCompte(jeu) || !proposition.trim().startsWith("TG{")) {
            return Reponse(local, saut = 4, couleur = VERT)
        }
        val cle = Recensement.compte(jeu).optString("cle")
        enLigne({
            val url = adresse()
            Recensement.requete("$url/api/drapeau", "POST", JSONObject().put("drapeau", proposition.trim()), cle)
                .put("_url", url)
        }) { r ->
            if (!r.optBoolean("ok")) return@enLigne "❌ " + r.optString("message", r.optString("erreur", t("rec.drapeau.refuse")))
            val url = r.optString("_url")
            if (r.optBoolean("nouveau")) {
                jeu.ajouterXp(40)
                jeu.stats["Intelligence"] = (jeu.stats["Intelligence"] ?: 0) + 3
                jeu.log(t("rec.drapeau.log", "titre" to r.optString("titre")))
            }
            buildString {
                append(t("reca.drapeau.ok", "titre" to r.optString("titre"), "score" to r.optInt("score"), "sur" to r.optInt("sur")))
                if (!r.optBoolean("nouveau")) append(t("rec.drapeau.deja"))
                append("\n📐 ${r.optString("lecon")}")
                if (!r.isNull("badge") && r.optString("badge").isNotEmpty()) append("\n" + t("reca.badge", "url" to url + r.optString("badge")))
                if (!r.isNull("badgeFinal") && r.optString("badgeFinal").isNotEmpty()) append("\n" + t("rec.drapeau.final", "url" to url + r.optString("badgeFinal")))
            }
        }
        return Reponse(t("reca.drapeau.site"), couleur = VERT)
    }

    // ---------------------------------------------------------------- progression et jeux
    /** aile · aile <nom ou numéro> (aussi arbre, l'ancien nom) : les ailes de la maison, choisir celle qu'on réveille. */
    private fun aile(choix: String): Reponse {
        Histoire.h(jeu)
        if (choix.isEmpty()) return Reponse(Histoire.lignesAiles(jeu).joinToString("\n"), couleur = ROSE)
        val cid = Histoire.chercherChapitre(choix)
            ?: return Reponse(t("hist.aile.inconnue", "nom" to choix) + "\n" + Histoire.lignesAiles(jeu).joinToString("\n"), couleur = ORANGE)
        return Reponse(Histoire.choisir(jeu, cid, dit = false), saut = 3, couleur = ROSE)
    }

    /** quetes · quetes suivre N : le journal des quêtes de la maison (puis celles du donjon, s'il y en a). */
    private fun quetes(reste: String): Reponse {
        val m = reste.split(Regex("\\s+")).filter { it.isNotEmpty() }
        if (m.size >= 2 && m[0].lowercase() in setOf("suivre", "follow", "s")) return Reponse(Quetes.suivre(jeu, m[1]), couleur = JAUNE)
        Histoire.h(jeu)
        var txt = Quetes.journal(jeu).joinToString("\n")
        if (jeu.module("donjon").has("quetes")) txt += "\n\n" + Donjon.texteQuetes(jeu)
        return Reponse(txt, couleur = JAUNE)
    }

    private fun edite(nom: String): Reponse {
        if (nom.isEmpty()) return Reponse(t("edite.exemple"), couleur = ORANGE)
        val f = when {
            nom.startsWith("~/") -> File(jeu.home, nom.removePrefix("~/"))
            nom.startsWith("/") -> File(nom)
            else -> File(dossier(), nom)
        }
        if (!f.canonicalPath.startsWith(jeu.home.canonicalPath)) {
            return Reponse(t("edite.hors_maison"), couleur = ORANGE)
        }
        if (f.isDirectory) return Reponse(t("edite.dossier", "nom" to f.name), couleur = ORANGE)
        act.startActivity(Intent(act, EditeurActivity::class.java).putExtra("chemin", f.absolutePath))
        return Reponse(t("edite.ouvre", "nom" to f.name))
    }

    private fun doom(): Reponse {
        if (!File(jeu.terrain, "nid").isDirectory) {
            return Reponse(t("doom.ferme", "lecon" to t("lec.t1.titre")), couleur = ORANGE)
        }
        Doom.preparer(jeu)
        act.startActivity(Intent(act, DoomActivity::class.java))
        return Reponse(t("doom.lancement"), saut = 4)
    }

    private fun notifs(choix: String): Reponse {
        val n = jeu.module("notifs")
        when (choix.lowercase()) {
            "on" -> n.put("actives", true)
            "off" -> n.put("actives", false)
            else -> return Reponse(if (n.optBoolean("actives", true)) t("notifs.on.etat")
                else t("notifs.off.etat"))
        }
        return Reponse(if (n.optBoolean("actives")) t("notifs.on") else t("notifs.off"))
    }

    /** notif on / off / reglages : la créature en direct dans la barre de notification (NotifVie). */
    private fun notifVie(choix: String): Reponse {
        when (choix.lowercase()) {
            "on" -> {
                NotifVie.regler(act, true)
                if (!NotifVie.permise(act)) {           // Android 13+ : on demande la permission (réponse : TerminalActivity)
                    act.requestPermissions(arrayOf("android.permission.POST_NOTIFICATIONS"), 2)
                    return Reponse(t("notifs.vie.permission"), couleur = ORANGE)
                }
                if (!NotifVie.autorisees(act)) return Reponse(t("notifs.vie.bloquee"), couleur = ORANGE)
                return Reponse(t("notifs.vie.on", "nom" to jeu.nom), saut = 2)
            }
            "off" -> {
                NotifVie.regler(act, false)
                return Reponse(t("notifs.vie.off"))
            }
            "reglages" -> return lancer(Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
                .putExtra(Settings.EXTRA_APP_PACKAGE, act.packageName), t("notifs.vie.reglages"), "")
        }
        val etat = if (NotifVie.voulue(act)) t("notifs.vie.on.etat", "n" to NotifVie.rationsDuJour(jeu), "max" to NotifVie.RATIONS)
            else t("notifs.vie.off.etat")
        return Reponse(if (NotifVie.voulue(act) && !NotifVie.autorisees(act)) etat + "\n" + t("notifs.vie.bloquee") else etat)
    }

    // ---------------------------------------------------------------- créature
    private fun joue(coup: String?): Reponse {
        val coups = listOf("pierre", "feuille", "ciseaux")
        val toi: String = coup?.lowercase() ?: ""
        if (toi !in coups) return Reponse(t("cre.joue.aide"), couleur = ROSE)
        val moi = coups.random()
        Envies.plaisir(jeu, "jeu", "mini")
        val emoji = mapOf("pierre" to "🪨", "feuille" to "📄", "ciseaux" to "✂")
        val resultat = when {
            moi == toi -> t("cre.joue.egalite")
            (toi == "pierre" && moi == "ciseaux") || (toi == "feuille" && moi == "pierre") ||
                (toi == "ciseaux" && moi == "feuille") -> t("cre.joue.gagne")
            else -> t("cre.joue.perdu")
        }
        return Reponse(t("cre.joue.resultat", "toi" to emoji[toi], "nom" to jeu.nom, "moi" to emoji[moi],
            "resultat" to resultat), saut = 3, couleur = ROSE)
    }

    private fun devine(n: String?): Reponse {
        if (nombreSecret == 0) {
            nombreSecret = (1..20).random()
            essais = 0
            if (n == null) return Reponse(t("cre.devine.debut"), couleur = ROSE)
        }
        val k = n?.toIntOrNull() ?: return Reponse(t("cre.devine.nombre"), couleur = ROSE)
        essais++
        return when {
            k < nombreSecret -> Reponse(t("cre.devine.plus"), couleur = ROSE)
            k > nombreSecret -> Reponse(t("cre.devine.moins"), couleur = ROSE)
            else -> {
                nombreSecret = 0
                jeu.ajouterXp(if (essais <= 5) 10 else 5)
                Envies.plaisir(jeu, "jeu", "mini")
                Reponse(t("cre.devine.trouve", "n" to k, "essais" to essais), saut = 8, couleur = ROSE)
            }
        }
    }

    private fun etat(): Reponse {
        val texte = listOf(
            jeu.titre(), jeu.texteFaim(), jeu.texteXp(), jeu.texteStats(),
            t("cre.etat", "trait" to Regles.nomTrait(jeu.trait),
                "total" to jeu.total, "vus" to jeu.vus.size),
            t("app.arbre.competences", "liste" to (if (jeu.skills.isEmpty()) t("app.arbre.aucune") else jeu.skills.joinToString(", ") { Regles.nomSkill(it) })),
        ).joinToString("\n")
        return Reponse(texte, couleur = ROSE)
    }

    private fun renomme(nom: String): Reponse {
        if (nom.isEmpty()) return Reponse(t("cre.renomme.exemple"), couleur = ORANGE)
        val ancien = jeu.nom
        jeu.nom = nom.take(16)
        Recensement.compte(jeu).put("nomDate", System.currentTimeMillis())
        return Reponse(t("cre.renomme.ok", "ancien" to ancien, "nom" to jeu.nom), saut = 3, couleur = ROSE)
    }

    companion object {
        val ROSE = 0xFFFF87FF.toInt()
        val BLEU = 0xFF87AFFF.toInt()
        val JAUNE = 0xFFFFD787.toInt()
        val VERT = 0xFF87FFAF.toInt()
        val ORANGE = 0xFFFFAF5F.toInt()
        val CREATURE = setOf("caresse", "danse", "parle", "joue", "devine", "etat", "renomme", "envies", "envie")
        val TELEPHONE = setOf("applis", "ouvre", "web", "carte", "appelle", "sms", "partage", "lampe", "vibre",
            "batterie", "dis", "reglages")
    }
}
