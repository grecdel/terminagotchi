/*
 * Non-régression (Android, JVM hors téléphone) des problèmes trouvés par les simulations de joueurs, 3e passage
 * (docs/simulations/rapport_v3.md) :
 *   C5. chapitre 8, « Mon premier niveau » / « Les réglages » : `edite carte.txt` tapé dans un repaire (où un dressage
 *       a emmené l'enfant) ne valide jamais ; l'étape a maintenant son lieu (la salle de jeu) : la leçon montre le cd,
 *       `aide` ne dit plus « c'est le bon endroit », l'indice dit d'y aller ; depuis la salle de jeu, l'étape passe ;
 *   I13. un lieu d'habitat (mecanique, abyssal…) a un vrai nom (« Atelier des engrenages »), jamais la clé brute
 *       « carte.piece.mecanique » ;
 *   I14. « non » à « Ton œuf s'appellera X. C'est bien ça ? » est reconnu (14 langues) et ne devient pas un nom.
 *
 * Même mise en route que SimulationsV2.kt ; se lance SANS être root :
 *   kotlinc -cp <imitations>:<appli.jar> tests/jvm/SimulationsV3.kt -d simv3.jar
 *   java -cp <imitations>:<appli.jar>:simv3.jar:kotlin-stdlib.jar SimulationsV3Kt app/src/main/assets
 */
import fr.terminagotchi.Doom
import fr.terminagotchi.Histoire
import fr.terminagotchi.Jeu
import fr.terminagotchi.Langue
import fr.terminagotchi.Maison
import fr.terminagotchi.MenuParties
import fr.terminagotchi.Tour
import fr.terminagotchi.Vert
import java.io.File

class ActifsV3(private val dir: File) : android.content.res.AssetManager() {
    override fun open(f: String): java.io.InputStream = File(dir, f).inputStream()
}

class AppareilV3(private val d: File, private val a: File) : android.app.Activity() {
    override fun getFilesDir(): File = d
    override fun getAssets(): android.content.res.AssetManager = ActifsV3(a)
    override fun getApplicationContext(): android.content.Context = this
}

var okW = 0
var koW = 0

fun verifierW(c: Boolean, m: String) {
    if (c) okW++ else koW++
    println((if (c) "  ✔ " else "  ✖ ") + m)
}

lateinit var jeuW: Jeu

/** Une commande de l'appli (edite, cat…) tapée dans `ou`, puis le tour du jeu (comme TerminalActivity.apresCommande). */
fun tourW(cmd: String, ou: File, code: Int? = 0) {
    Tour.apresCommande(jeuW, cmd, colle = false, rappel = false, hasard = false, cwd = ou, code = code)
}

fun lecW(): Pair<String?, Int> = Histoire.leconCourante(jeuW)?.id to jeuW.etape

fun main(args: Array<String>) {
    val assets = File(args[0])
    val dossier = File(System.getProperty("java.io.tmpdir"), "tg_simv3_" + System.nanoTime()).apply { mkdirs() }
    val app = AppareilV3(dossier, assets)
    Langue.init(app)
    Langue.definir("fr")
    jeuW = Jeu(app)
    jeuW.changerLangue("fr")
    jeuW.nom = "Pixel"
    jeuW.module("explo").put("ouverte", true)
    jeuW.xp = 10 * 13 * 13

    println("C5. Chapitre 8 : l'éditeur s'ouvre dans la salle de jeu")
    File(jeuW.terrain, "nid").mkdirs()
    val salle = Doom.preparer(jeuW)
    verifierW(salle.canonicalPath == File(jeuW.terrain, "jeu").canonicalPath, "le Doom-like vit dans ~/terrain_terminagotchi/jeu")
    val faits = Histoire.h(jeuW).getJSONArray("faits")
    for (c in Histoire.CHAPITRES.filter { it.id in setOf("reveil", "nid") }) for (l in c.lecons) if (l !in Histoire.faits(jeuW)) faits.put(l)
    Histoire.h(jeuW).put("ailes", org.json.JSONArray().put("reveil").put("nid"))       // chapitres 1 et 2 finis
    Histoire.choisir(jeuW, "atelier", dit = false)
    for (l in listOf("atelier0", "scripts0", "scripts1", "scripts2", "createur0")) if (l !in Histoire.faits(jeuW)) faits.put(l)
    jeuW.etape = 0
    verifierW(lecW() == ("createur1" to 0), "leçon « Mon premier niveau », étape edite carte.txt : ${lecW()}")
    val repaire = File(jeuW.terrain, "mecanique/repaire_engrenaille").apply { mkdirs() }
    tourW("edite carte.txt", repaire)
    File(repaire, "carte.txt").writeText("#####\n#C.B#\n#####\n")       // l'éditeur a ouvert (et créé) un autre fichier
    tourW("edite carte.txt", repaire)
    verifierW(lecW() == ("createur1" to 0), "la carte d'un repaire ne valide pas l'étape (${lecW()})")
    val ind = Vert.sansMarques(jeuW.indiceLecon ?: "")
    verifierW("terrain_terminagotchi/jeu" in ind, "l'indice dit d'aller dans la salle de jeu : $ind")
    val aR = Vert.sansMarques(Histoire.aideLecon(jeuW))
    verifierW("C'est le bon endroit" !in aR && "Salle de jeu" in aR, "aide dans le repaire : pas « le bon endroit », va à la salle de jeu")
    verifierW("carte.piece" !in aR && "Atelier des engrenages" in aR, "I13 : aide nomme le repaire (vrai nom, sans clé brute) : $aR")
    val lec = Vert.sansMarques(jeuW.texteLecon() ?: "")
    verifierW("terrain_terminagotchi/jeu" in lec, "la leçon montre le cd de la salle de jeu")
    val carte = File(salle, "carte.txt")
    carte.writeText(carte.readText().replaceFirst(".", "#"))
    tourW("edite carte.txt", salle)
    verifierW(lecW() == ("createur1" to 1), "depuis la salle de jeu, la carte modifiée valide l'étape (${lecW()})")

    println("I13. Les lieux sans nom traduit")
    // suite du rapport v3 : les lieux d'habitat ont de vrais noms (14 langues) ; un dossier inconnu garde son nom
    verifierW(Maison.nomPiece("mecanique") == "Atelier des engrenages", "mecanique : « ${Maison.nomPiece("mecanique")} »")
    verifierW(Maison.nomPiece("eau_petillante") == "Source pétillante", "eau_petillante : « ${Maison.nomPiece("eau_petillante")} »")
    verifierW(Maison.nomPiece("dossier_perso") == "dossier perso", "un dossier inconnu : « ${Maison.nomPiece("dossier_perso")} »")
    verifierW(Maison.nomPiece("jeu") == "Salle de jeu", "jeu : « ${Maison.nomPiece("jeu")} »")
    verifierW(Maison.nomPiece("grenier") == "Grenier", "grenier : « ${Maison.nomPiece("grenier")} »")

    println("I14. « non » à la confirmation du nom")
    for (r in listOf("non", "Non", "n", "no", "nein", "いいえ")) verifierW(MenuParties.non(r), "« $r » = non")
    for (r in listOf("Krokmou", "oui", "", "nono")) verifierW(!MenuParties.non(r), "« $r » n'est pas non")
    verifierW(MenuParties.oui("oui") && !MenuParties.oui("non"), "oui reste oui")

    println("\n$okW réussis, $koW ratés")
    kotlin.system.exitProcess(if (koW == 0) 0 else 1)
}
