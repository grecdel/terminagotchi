package fr.terminagotchi

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews

/** Le widget d'écran d'accueil : la créature, sa faim, ce qu'elle dit, et le bouton du terminal. */
class WidgetCreature : AppWidgetProvider() {
    override fun onUpdate(context: Context, manager: AppWidgetManager, ids: IntArray) {
        majTous(context)
    }

    companion object {
        /** Met à jour les widgets ET la notification en direct (NotifVie) : appelé à chaque changement de la créature. */
        fun majTous(ctx: Context) {
            val mgr = AppWidgetManager.getInstance(ctx)
            val ids = mgr.getAppWidgetIds(ComponentName(ctx, WidgetCreature::class.java))
            if (ids.isEmpty() && !NotifVie.voulue(ctx)) return
            val jeu = Jeu(ctx)
            jeu.tick()
            NotifVie.maj(ctx, jeu)          // avant infoWidget : elle lit la file de bulles sans la vider
            if (ids.isEmpty()) {
                if (jeu.existe) jeu.sauver()
                return
            }

            val v = RemoteViews(ctx.packageName, R.layout.widget)
            v.setImageViewBitmap(R.id.w_creature, Sprites.bitmap(jeu, 10))
            if (jeu.existe) {
                v.setTextViewText(R.id.w_titre, jeu.titre())
                v.setTextViewText(R.id.w_faim, jeu.texteFaim())
                v.setTextViewText(R.id.w_info, Vert.rendre(jeu.infoWidget()))
            } else {
                v.setTextViewText(R.id.w_titre, t("widget.oeuf"))
                v.setTextViewText(R.id.w_faim, "")
                v.setTextViewText(R.id.w_info, t("widget.eclore"))
            }
            v.setTextViewText(R.id.w_bouton, t("widget.bouton"))
            jeu.sauver()                 // après infoWidget : la bulle suivante de la file a pu être prise
            val intent = Intent(ctx, TerminalActivity::class.java)
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
            val pi = PendingIntent.getActivity(ctx, 0, intent,
                PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
            v.setOnClickPendingIntent(R.id.w_bouton, pi)
            v.setOnClickPendingIntent(R.id.w_creature, pi)
            mgr.updateAppWidget(ids, v)
        }
    }
}
