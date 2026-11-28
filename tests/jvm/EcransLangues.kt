/*
 * Test JVM (hors téléphone) de l'interface traduite : pour chacune des 14 langues, charge
 * app/src/main/assets/langues/xx.json et affiche quelques écrans de l'appli en texte :
 * le menu des parties (et la réponse « nouvelle » + « oui » dans la langue), la leçon 1,
 * un dressage (panneau + fiche du monstre), le début du lexique, l'aide, une recherche.
 * Il vérifie aussi qu'aucun {param} ni aucune clé ne reste à l'écran.
 *
 * Il se compile avec kotlinc contre les classes de l'appli et des imitations d'android.* (qui ne
 * sont pas dans le dépôt) :
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/EcransLangues.kt -d ecrans.jar
 *   java -cp <imitations>:<appli.jar>:ecrans.jar:kotlin-stdlib.jar EcransLanguesKt app/src/main/assets <dossier de sortie>
 */
import fr.terminagotchi.Bestiaire
import fr.terminagotchi.Dressage
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.MenuParties
import fr.terminagotchi.Mots
import fr.terminagotchi.Recherche
import fr.terminagotchi.Regles
import fr.terminagotchi.t
import java.io.File

class Actifs(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class Appareil(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = Actifs(a)
    override fun getApplicationContext(): android.content.Context = this
}

private val RESTE_PARAM = Regex("\\{[a-z_A-Z]+\\}")
private val RESTE_CLE = Regex("(?m)(^|\\s)(term|tel|cre|lexa|lex|arbre|donjon|ctf|part|dress|dressa|reca|rec|rech|eq|exp|expa|app|lec|leca|core|widget|rappel|doom|edite|notifs|defi|jeu|shell)\\.[a-z_]+(\\.[a-z_0-9]+)*(\\s|$)")

fun main(args: Array<String>) {
    val assets = File(args[0])
    val sortie = File(args[1]).apply { mkdirs() }
    var problemes = 0
    for (code in Langue.LANGUES.keys) {
        val dossier = File(System.getProperty("java.io.tmpdir"), "tg_langue_${code}_" + System.nanoTime()).apply { mkdirs() }
        val app = Appareil(dossier, assets)
        Langue.init(app)
        Langue.definir(code)
        val jeu = Jeu(app)
        jeu.changerLangue(code)
        jeu.nom = "Pixel"
        jeu.sauver()
        val sb = StringBuilder("######## $code — ${Langue.LANGUES[code]} ########\n")
        fun ecran(titre: String, texte: String) {
            sb.append("\n== $titre ==\n").append(texte).append("\n")
            RESTE_PARAM.find(texte)?.let { sb.append("!! paramètre non rempli : ${it.value}\n"); problemes++ }
            RESTE_CLE.find(texte)?.let { sb.append("!! clé affichée telle quelle : ${it.value.trim()}\n"); problemes++ }
        }

        // ---- menu des parties : chiffres, mots de la langue, « oui » de la langue
        val messages = mutableListOf<String>()
        val menu = MenuParties(app, jeu, apresChangement = {}, synchroniser = {}, texteCompte = { "(compte)" }, plusTard = { messages.add(it) })
        ecran("menu", menu.ouvrir())
        val motNouvelle = Langue.valeurs("part.mots.nouvelle", code).first()
        val motOui = Langue.valeurs("part.oui", code).first()
        val confirmation = menu.repondre(motNouvelle) ?: "(le menu s'est fermé)"
        ecran("menu > « $motNouvelle »", confirmation)
        if (menu.etat != "nouvelle") { sb.append("!! « $motNouvelle » n'ouvre pas la nouvelle partie\n"); problemes++ }
        ecran("menu > « $motOui »", menu.repondre(motOui) ?: "(le menu s'est fermé)")
        if (jeu.existe) { sb.append("!! « $motOui » n'a pas été compris comme oui\n"); problemes++ }
        jeu.nom = "Pixel"
        jeu.sauver()

        // ---- leçon 1
        ecran("leçon 1", listOf(jeu.titre(), jeu.texteFaim(), jeu.texteXp(), jeu.texteStats(), jeu.texteLecon() ?: "").joinToString("\n"))

        // ---- dressage (premier : sans chrono) puis panneau d'une deuxième rencontre (avec chrono)
        File(jeu.terrain, "nid").mkdirs()
        val e = Bestiaire.espece("Braisillon")!!
        File(jeu.terrain, e.zone).mkdirs()
        Dressage.commencer(jeu, e)
        ecran("dressage (bulle)", jeu.bulleActive())
        ecran("dressage (panneau)", Dressage.panneau(jeu, android.content.res.Resources()).toString())
        ecran("dressage (fiche du monstre : cat)", Dressage.fiche(jeu, e.nom).readText())
        Dressage.abandonner(jeu)

        // ---- lexique (image seule, puis image + vrai mot)
        val lex = StringBuilder(t("term.lexique.entete", "n" to 3, "total" to Regles.LEXIQUE.size) + "\n")
        var section = ""
        for (m in Regles.LEXIQUE.take(14)) {
            if (m.section != section) { section = m.section; lex.append("\n$section\n") }
            lex.append("○ ${m.cmd}  ${Regles.explication(m, 0)}\n")
        }
        lex.append("\n(palier 1) ").append(Regles.explication(Regles.LEXIQUE[1], 1))
        ecran("lexique", lex.toString())
        ecran("aide", t("term.aide", "ctf" to Mots.terme("ctf", 0, true)))

        // ---- recherche dans la langue choisie (description traduite de « rm -r »)
        val q = Langue.valeurs("rech.rm_r", code).firstOrNull() ?: "supprimer un dossier"
        val r = Recherche.chercher(q)
        ecran("cherche $q", r)
        if ("rm" !in r) { sb.append("!! la recherche « $q » ne trouve pas rm -r\n"); problemes++ }

        File(sortie, "$code.txt").writeText(sb.toString())
        dossier.deleteRecursively()
        println("$code : ${sb.lines().count { it.startsWith("!!") }} problème(s)")
    }
    println("$problemes problème(s) en tout")
    if (problemes > 0) System.exit(1)
}
