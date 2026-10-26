package fr.terminagotchi

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.widget.RemoteViews
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * La créature « en direct » dans la barre de notification, comme un tamagotchi de poche.
 *
 *  - une notification « en cours » (ongoing), silencieuse, sur son propre canal (CANAL), séparée des rappels ;
 *  - repliée : le portrait en grande icône, le nom et le niveau, les 3 envies les plus basses (Envies.kt), ⭐ XP,
 *    l'humeur et l'envie du moment ; dépliée : une vue personnalisée (layout notif_vie, comme le widget) avec la
 *    créature en grand, les 6 envies et sa phrase ;
 *  - trois boutons : Nourrir (une petite ration, limitée : le vrai repas reste les commandes), Caresser, Terminal.
 *
 * Pas de service au premier plan : la notification est simplement (re)publiée à chaque changement (après chaque
 * commande, changement de partie ou de langue : partout où le widget se met à jour, voir WidgetCreature.majTous),
 * et en fond par l'alarme existante des Rappels (toutes les 30 min environ). La faim ne baisse que d'un point toutes
 * les 12 minutes, les autres envies encore moins vite : il n'y a rien à animer entre deux mises à jour.
 *
 * Elle suit la partie active (Jeu lit toujours la sauvegarde active, voir Parties.kt).
 * Réglage de l'appareil (pas de la partie) : commande « notif on / notif off », activée par défaut.
 */
class NotifVie : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val action = intent.action ?: return
        val attente = goAsync()
        Thread {
            try {
                synchronized(VERROU) {
                    val jeu = Jeu(context)
                    if (jeu.existe) {
                        jeu.tick()
                        when (action) {
                            NOURRIR -> nourrir(jeu)
                            CARESSER -> caresser(jeu)
                        }
                        jeu.sauver()
                        modifie = System.currentTimeMillis()
                    }
                }
                WidgetCreature.majTous(context)
            } catch (e: Exception) {
                android.util.Log.e("TG", "notification : $action", e)
            } finally {
                attente.finish()
            }
        }.start()
    }

    companion object {
        const val CANAL = "terminagotchi_vie"
        const val ID = 4242
        const val NOURRIR = "fr.terminagotchi.vie.NOURRIR"
        const val CARESSER = "fr.terminagotchi.vie.CARESSER"
        /** rations par jour depuis la notification, ce qu'elles rendent, et la faim au-delà de laquelle elles ne servent plus */
        const val RATIONS = 3
        const val RATION = 10.0
        const val PLAFOND = 60.0
        private const val PREF = "notif_vie"
        private val VERROU = Any()

        /** date du dernier changement fait depuis la notification (le terminal ouvert relit alors la sauvegarde) */
        @Volatile var modifie = 0L
        /** ce qui est affiché (pour ne pas republier la même chose) */
        @Volatile private var affiche: String? = null

        private fun prefs(ctx: Context) = ctx.getSharedPreferences("terminagotchi", Context.MODE_PRIVATE)

        /** La notification est-elle voulue ? (réglage de l'appareil, activé par défaut) */
        fun voulue(ctx: Context): Boolean = try { prefs(ctx).getBoolean(PREF, true) } catch (e: Exception) { true }

        fun regler(ctx: Context, on: Boolean) {
            try { prefs(ctx).edit().putBoolean(PREF, on).apply() } catch (e: Exception) { }
            if (!on) retirer(ctx)
        }

        /** Android 13+ : la permission POST_NOTIFICATIONS est-elle accordée ? */
        fun permise(ctx: Context): Boolean = Build.VERSION.SDK_INT < 33 ||
            ctx.checkSelfPermission("android.permission.POST_NOTIFICATIONS") == PackageManager.PERMISSION_GRANTED

        /** Les notifications de l'appli sont-elles autorisées (permission et réglages du téléphone) ? */
        fun autorisees(ctx: Context): Boolean = permise(ctx) && gestionnaire(ctx)?.areNotificationsEnabled() == true

        private fun gestionnaire(ctx: Context) = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as? NotificationManager

        fun retirer(ctx: Context) {
            affiche = null
            try { gestionnaire(ctx)?.cancel(ID) } catch (e: Exception) { }
        }

        // ------------------------------------------------------------ les boutons
        private fun aujourdhui() = SimpleDateFormat("yyyyMMdd", Locale.ROOT).format(Date())

        /** Rations déjà données aujourd'hui depuis la notification (par créature). */
        fun rationsDuJour(jeu: Jeu): Int {
            val n = jeu.module("notifs")
            return if (n.optString("ration_jour") == aujourdhui()) n.optInt("rations") else 0
        }

        /**
         * Une petite ration sans ouvrir l'appli : +10 de faim, au plus 3 par jour, et jamais au-delà de « repu »
         * (60) : pour grandir et être bien nourrie, la créature a besoin des commandes tapées au terminal. Pas d'XP.
         */
        fun nourrir(jeu: Jeu) {
            val deja = rationsDuJour(jeu)
            when {
                jeu.faim >= PLAFOND -> repondre(jeu, t("notifs.vie.pas_faim"))
                deja >= RATIONS -> repondre(jeu, t("notifs.vie.plus_de_ration"))
                else -> {
                    jeu.faim = (jeu.faim + RATION).coerceAtMost(PLAFOND)
                    jeu.module("notifs").put("ration_jour", aujourdhui()).put("rations", deja + 1)
                    jeu.log(t("notifs.vie.ration.log"))
                    repondre(jeu, t("notifs.vie.miam", "n" to deja + 1, "max" to RATIONS))
                    jeu.animer("mange")
                }
            }
        }

        /** Une caresse : comme la commande « caresse » (rien à manger, rien à gagner : juste du bonheur). */
        fun caresser(jeu: Jeu) {
            jeu.animer("content")
            repondre(jeu, Regles.auHasard("cre.caresse"))
        }

        /** La réponse à un bouton s'affiche tout de suite (sans attendre la fin de la bulle en cours). */
        private fun repondre(jeu: Jeu, texte: String) {
            jeu.bulle = texte
            jeu.bulleFin = System.currentTimeMillis() + 20_000L
        }

        // ------------------------------------------------------------ les textes
        private val BALISE = Regex("¤[^¤]*¤")

        /** La phrase de la créature : la bulle en cours, sinon la prochaine de la file (sans la prendre), sinon une phrase de son caractère. */
        fun phrase(jeu: Jeu): String {
            val now = System.currentTimeMillis()
            val brute = when {
                now < jeu.bulleFin && jeu.bulle.isNotEmpty() -> jeu.bulle
                jeu.bulles.isNotEmpty() -> jeu.bulles.first().first
                jeu.stade > 0 && Envies.phrase(jeu) != null -> "💭 " + Envies.phrase(jeu)   // l'envie du moment
                else -> {
                    val cle = when {
                        jeu.stade == 0 -> Regles.OEUF
                        else -> Regles.TRAITS[jeu.trait] ?: Regles.OEUF
                    }
                    val l = Langue.brutes(cle)
                    // la même phrase pendant un quart d'heure (pas une nouvelle à chaque mise à jour)
                    if (l.isEmpty()) "" else Langue.remplir(l[((now / 900_000L) % l.size).toInt()], mapOf("nom" to jeu.nom))
                }
            }
            return BALISE.replace(brute, "").replace("§", "").replace(Regex("\\s+"), " ").trim()
        }

        /** l'emoji de l'humeur (les 6 envies combinées, voir Envies.humeurCle) */
        fun emojiHumeur(jeu: Jeu) = Envies.emoji(jeu)

        /** « ⭐ ▰▰▱▱▱ » : l'XP jusqu'au niveau suivant. */
        fun xp(jeu: Jeu): String {
            val n = jeu.niveau
            val lo = 10 * (n - 1) * (n - 1)
            val hi = 10 * n * n
            return "⭐ ${Regles.barre((jeu.xp - lo).toDouble(), (hi - lo).toDouble(), 5)}"
        }

        /** Vue réduite : les 3 envies les plus basses et l'XP (« 🎮▰▱▱▱ 😴▰▰▱▱ 📚▰▰▰▱  ⭐ ▰▰▱▱▱ »). */
        fun jauges(jeu: Jeu): String = "${Envies.plusBasses(jeu)}  ${xp(jeu)}"

        /** Vue dépliée : les 6 envies (2 lignes de 3). */
        fun jaugesToutes(jeu: Jeu): String = Envies.compact(jeu)

        // ------------------------------------------------------------ la notification
        private fun canal(ctx: Context, nm: NotificationManager) {
            if (nm.getNotificationChannel(CANAL) != null) return
            val c = NotificationChannel(CANAL, t("notifs.vie.canal"), NotificationManager.IMPORTANCE_LOW)
            c.setDescription(t("notifs.vie.canal.desc"))
            c.setShowBadge(false)
            c.enableVibration(false)
            nm.createNotificationChannel(c)
        }

        private fun bouton(ctx: Context, action: String, code: Int): PendingIntent =
            PendingIntent.getBroadcast(ctx, code, Intent(ctx, NotifVie::class.java).setAction(action),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)

        /** Publie (ou met à jour, ou retire) la notification pour la partie active. Appelé par WidgetCreature.majTous. */
        fun maj(ctx: Context, jeu: Jeu) {
            if (!voulue(ctx) || !jeu.existe) { retirer(ctx); return }
            if (!permise(ctx)) return
            val nm = gestionnaire(ctx) ?: return
            try {
                canal(ctx, nm)
                val titre = jeu.titre()
                val jauges = jauges(jeu)
                val toutes = jaugesToutes(jeu)
                val humeur = "${emojiHumeur(jeu)} ${jeu.humeur()}  ${xp(jeu)}"
                val dit = phrase(jeu)
                val cle = listOf(jeu.partie, titre, jauges, toutes, humeur, dit, jeu.stade, jeu.forme, jeu.shiny, Langue.courante).joinToString("|")
                if (cle == affiche && nm.activeNotifications.any { it.id == ID }) return

                val ouvrir = PendingIntent.getActivity(ctx, 12,
                    Intent(ctx, TerminalActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP),
                    PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)

                // dépliée : la créature en grand (gros pixels, sans lissage : 18×16 px × 16)
                val v = RemoteViews(ctx.packageName, R.layout.notif_vie)
                v.setImageViewBitmap(R.id.n_creature, Sprites.bitmap(jeu, 16))
                v.setTextViewText(R.id.n_titre, titre)
                v.setTextViewText(R.id.n_jauges, toutes)
                v.setTextViewText(R.id.n_humeur, humeur)
                v.setTextViewText(R.id.n_phrase, Vert.rendre(if (dit.isEmpty()) "" else "« $dit »"))
                v.setOnClickPendingIntent(R.id.n_creature, ouvrir)

                val notif = Notification.Builder(ctx, CANAL)
                    .setSmallIcon(R.drawable.ic_notif)
                    .setLargeIcon(Sprites.bitmap(jeu, 10))
                    .setContentTitle(titre)
                    .setContentText(Vert.rendre(if (dit.isEmpty()) jauges else "$jauges  « $dit »"))
                    .setSubText(humeur)
                    .setStyle(Notification.DecoratedCustomViewStyle())
                    .setCustomBigContentView(v)
                    .setContentIntent(ouvrir)
                    .setOngoing(true)
                    .setOnlyAlertOnce(true)
                    .setShowWhen(false)
                    .setCategory(Notification.CATEGORY_STATUS)
                    .addAction(R.drawable.ic_notif, t("notifs.vie.btn.nourrir"), bouton(ctx, NOURRIR, 10))
                    .addAction(R.drawable.ic_notif, t("notifs.vie.btn.caresser"), bouton(ctx, CARESSER, 11))
                    .addAction(R.drawable.ic_notif, t("notifs.vie.btn.ouvrir"), ouvrir)
                    .build()
                nm.notify(ID, notif)
                affiche = cle
            } catch (e: Exception) {
                // notifications refusées, ou vue refusée par le téléphone : on réessaiera à la prochaine mise à jour
                android.util.Log.e("TG", "notification en direct", e)
                affiche = null
            }
        }
    }
}
