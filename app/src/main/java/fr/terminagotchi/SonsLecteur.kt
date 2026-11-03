package fr.terminagotchi

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioTrack

/**
 * Le mélangeur du téléphone (même logique que sons.Lecteur sur PC) : une piste AudioTrack en flux, attributs « jeu » ;
 * une boucle de musique (fondu de 1 s quand elle change, 20 s de silence après 3 tours) + les sons courts (cris,
 * réussites). Silence si le téléphone est en silencieux ou vibreur, si une autre appli joue de la musique (focus
 * audio), et quand l'appli passe en arrière-plan (pause()). Rien de tiers : seulement le système Android.
 */
object SonsLecteur {
    private const val SR = Sons.SR
    private const val BLOC = 1024
    private var am: AudioManager? = null
    private var piste: AudioTrack? = null
    private var fil: Thread? = null
    @Volatile private var enPause = true
    private val verrou = Object()
    private val courts = mutableListOf<Triple<ShortArray, IntArray, Double>>()   // échantillons, [position], volume
    @Volatile private var voulue: String? = null
    @Volatile private var volMusique = 30
    private var mus: ShortArray? = null
    private var musNom: String? = null
    private var musPos = 0
    private var tours = 0
    private var silence = 0
    private var gain = 0.0
    private var ancienne: ShortArray? = null
    private var ancPos = 0
    private var ancGain = 0.0
    private var focus: AudioFocusRequest? = null
    private val executeur = java.util.concurrent.Executors.newSingleThreadExecutor()

    /** L'appli est au premier plan (onResume). */
    fun reprendre(ctx: Context) {
        try {
            am = ctx.applicationContext.getSystemService(Context.AUDIO_SERVICE) as? AudioManager
        } catch (e: Exception) { am = null }
        enPause = false
        demarrer()
    }

    /** L'appli passe en arrière-plan ou l'écran s'éteint (onPause) : tout se tait. */
    fun pause() {
        enPause = true
        voulue = null
        synchronized(verrou) { courts.clear(); mus = null; musNom = null; ancienne = null }
        rendreFocus()
    }

    /** Le téléphone est-il en silencieux ou en vibreur ? (alors le jeu se tait aussi) */
    private fun silencieux(): Boolean = am?.let { it.ringerMode != AudioManager.RINGER_MODE_NORMAL } ?: false

    /** La bulle (par-dessus les autres applis) : seulement les cris, quand on la touche. */
    fun jouerDepuis(ctx: Context, nom: String, vol: Int) {
        if (am == null) try { am = ctx.applicationContext.getSystemService(Context.AUDIO_SERVICE) as? AudioManager } catch (e: Exception) { }
        jouer(nom, vol, bulle = true)
    }

    fun jouer(nom: String, vol: Int, bulle: Boolean = false) {
        if ((enPause && !bulle) || silencieux()) return
        executeur.execute {
            try {
                val e = Sons.echantillons(nom)
                synchronized(verrou) { courts.add(Triple(e, intArrayOf(0), vol.coerceIn(0, 100) / 100.0)) }
                demarrer()
            } catch (x: Exception) { }
        }
    }

    fun musique(nom: String?, vol: Int) {
        volMusique = vol
        if (enPause) return
        val n = if (nom != null && (silencieux() || am?.isMusicActive == true && musNom == null)) null else nom
        if (n == voulue) return
        voulue = n
        if (n != null) executeur.execute {
            try { Sons.echantillons(n); demarrer() } catch (x: Exception) { }
        }
    }

    @Synchronized
    private fun demarrer() {
        if (fil?.isAlive == true) return
        fil = Thread({ tourner() }, "tg-sons").apply { isDaemon = true; start() }
    }

    private fun ouvrir(): AudioTrack? = try {
        val attr = AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_GAME)
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build()
        val fmt = AudioFormat.Builder().setSampleRate(SR).setEncoding(AudioFormat.ENCODING_PCM_16BIT)
            .setChannelMask(AudioFormat.CHANNEL_OUT_MONO).build()
        val min = AudioTrack.getMinBufferSize(SR, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT)
        AudioTrack.Builder().setAudioAttributes(attr).setAudioFormat(fmt).setTransferMode(AudioTrack.MODE_STREAM)
            .setBufferSizeInBytes(maxOf(min, BLOC * 4)).build().also { it.play() }
    } catch (e: Exception) { null }

    private fun prendreFocus() {
        val a = am ?: return
        if (focus != null) return
        try {
            val f = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
                .setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_GAME).build())
                .setOnAudioFocusChangeListener { c -> if (c == AudioManager.AUDIOFOCUS_LOSS) voulue = null }.build()
            if (a.requestAudioFocus(f) == AudioManager.AUDIOFOCUS_REQUEST_GRANTED) focus = f
        } catch (e: Exception) { }
    }

    private fun rendreFocus() {
        val f = focus ?: return
        try { am?.abandonAudioFocusRequest(f) } catch (e: Exception) { }
        focus = null
    }

    /** Un bloc mélangé (et s'il reste quelque chose à jouer). */
    private fun bloc(): Pair<ShortArray, Boolean> {
        val out = DoubleArray(BLOC)
        var actif: Boolean
        synchronized(verrou) {
            val v = voulue
            if (mus != null && musNom != v) { ancienne = mus; ancPos = musPos; ancGain = 1.0; mus = null; musNom = null }
            if (mus == null && v != null) Sons.enCache(v)?.let { mus = it; musNom = v; musPos = 0; tours = 0; silence = 0; gain = 0.0 }
            val vm = volMusique / 100.0
            val pas = BLOC / SR.toDouble()
            ancienne?.let { e ->
                for (i in 0 until BLOC) out[i] += e[(ancPos + i) % e.size] / 32767.0 * ancGain * vm
                ancPos = (ancPos + BLOC) % e.size
                ancGain -= pas
                if (ancGain <= 0) ancienne = null
            }
            mus?.let { e ->
                if (silence > 0) silence = maxOf(0, silence - BLOC)
                else {
                    for (i in 0 until BLOC) out[i] += e[(musPos + i) % e.size] / 32767.0 * gain * vm
                    gain = minOf(1.0, gain + pas)
                    musPos += BLOC
                    if (musPos >= e.size) {
                        musPos -= e.size
                        tours++
                        if (tours >= 3) { tours = 0; silence = 20 * SR; gain = 0.0 }      // 3 tours, puis 20 s de silence
                    }
                }
            }
            val it = courts.iterator()
            while (it.hasNext()) {
                val (e, p, vol) = it.next()
                val k = minOf(BLOC, e.size - p[0])
                for (i in 0 until k) out[i] += e[p[0] + i] / 32767.0 * vol
                p[0] += k
                if (p[0] >= e.size) it.remove()
            }
            actif = courts.isNotEmpty() || ancienne != null || (mus != null && silence == 0)
        }
        return Sons.pcm(out) to actif
    }

    private fun tourner() {
        var vide = 0
        try {
            while (true) {
                val (b, actif) = bloc()
                if (!actif) {
                    vide++
                    if (vide > 200) break                       // longtemps rien : on rend la piste
                    Thread.sleep(30)
                    continue
                }
                vide = 0
                if (piste == null) { prendreFocus(); piste = ouvrir() ?: break }
                piste?.write(b, 0, b.size)                      // bloquant : le rythme vient de la piste elle-même
            }
        } catch (e: Exception) {
        } finally {
            try { piste?.stop(); piste?.release() } catch (e: Exception) { }
            piste = null
            rendreFocus()
        }
    }
}
