package fr.terminagotchi

import android.app.AlarmManager
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.SystemClock
import android.app.Notification

/**
 * Toutes les 30 minutes environ (même appli fermée) : la faim baisse, le widget se met à jour,
 * et la créature envoie une notification si elle a faim.
 */
class Rappels : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val jeu = Jeu(context)
        if (!jeu.existe) return
        jeu.tick()
        val n = jeu.module("notifs")
        val actives = n.optBoolean("actives", true)
        val maintenant = System.currentTimeMillis()
        if (actives && jeu.faim < 30 && maintenant - n.optLong("faim", 0) > 3 * 3600_000L) {
            n.put("faim", maintenant)
            notifier(context, "${jeu.nom} a faim !", Regles.FAIM.random() + " (touche pour ouvrir le terminal)")
        }
        jeu.sauver()
        WidgetCreature.majTous(context)
    }

    companion object {
        private const val CANAL = "terminagotchi"

        fun programmer(ctx: Context) {
            val am = ctx.getSystemService(Context.ALARM_SERVICE) as AlarmManager
            val pi = PendingIntent.getBroadcast(ctx, 1, Intent(ctx, Rappels::class.java),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
            am.setInexactRepeating(AlarmManager.ELAPSED_REALTIME, SystemClock.elapsedRealtime() + AlarmManager.INTERVAL_HALF_HOUR,
                AlarmManager.INTERVAL_HALF_HOUR, pi)
        }

        fun notifier(ctx: Context, titre: String, texte: String) {
            val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            if (Build.VERSION.SDK_INT >= 26 && nm.getNotificationChannel(CANAL) == null) {
                nm.createNotificationChannel(NotificationChannel(CANAL, "Ta créature", NotificationManager.IMPORTANCE_DEFAULT))
            }
            val ouvrir = PendingIntent.getActivity(ctx, 2,
                Intent(ctx, TerminalActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
            val notif = Notification.Builder(ctx, CANAL)
                .setSmallIcon(R.drawable.ic_notif)
                .setContentTitle(titre)
                .setContentText(texte)
                .setStyle(Notification.BigTextStyle().bigText(texte))
                .setContentIntent(ouvrir)
                .setAutoCancel(true)
                .build()
            try {
                nm.notify(texte.hashCode(), notif)
            } catch (e: SecurityException) {
                // notifications refusées par l'utilisateur
            }
        }
    }
}
