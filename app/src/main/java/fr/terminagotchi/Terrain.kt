package fr.terminagotchi

import java.io.File

/**
 * Le terrain effacé (portage de pc/tg/terrain.py) : si l'enfant fait rm -rf ~/terrain_terminagotchi
 * (ou efface le nid), on le remarque et on l'aide à reconstruire, puis la leçon reprend au bon endroit.
 *
 *  1. Détection : la partie a déjà son terrain (la vieille porte du chapitre 1 est passée) mais le dossier
 *     ~/terrain_terminagotchi n'existe plus, ou son nid a disparu (leçon « Construire mon nid » finie).
 *     UN TERRAIN PAR PARTIE (voir Parties.kt) : une nouvelle partie démarre sans terrain (le jeu ouvre la
 *     vieille porte au chapitre 1), et tant que ce n'est pas fait, rien ne manque ;
 *     en changeant de partie, chacune retrouve le sien (rangé dans parties/terrain_<id>).
 *  2. Une bulle claire donne LA commande à taper (mkdir -p ~/terrain_terminagotchi/nid) ; un bandeau reste
 *     affiché tant que ce n'est pas fait (bandeau()). Si l'enfant n'y arrive pas, le jeu reconstruit lui-même
 *     après AIDE_AUTO commandes.
 *  3. Reprise : les fichiers indispensables à l'étape en cours sont remis (repas.txt pour la leçon des droits,
 *     miam.sh pour les scripts…), ou bien la leçon revient à l'étape qui les crée. Les portes des pièces et leurs
 *     meubles reviennent aussi (Histoire.meubler). Les monstres reviennent dès que le nid existe (Explo.debloquee).
 */
object Terrain {
    /** commandes tapées sans réussir : le jeu reconstruit lui-même */
    const val AIDE_AUTO = 12

    private fun etat(jeu: Jeu) = jeu.module("terrain")

    /** Vrai si la partie a déjà son terrain et son nid (leçon « Construire mon nid » finie). */
    fun aConstruit(jeu: Jeu) = "nid0" in Histoire.faits(jeu) || "Bâtisseur" in jeu.skills

    /** Ce qui a disparu et que l'enfant doit reconstruire (terrain, nid). */
    fun manque(jeu: Jeu): List<String> {
        val m = mutableListOf<String>()
        if ((aConstruit(jeu) || "reveil1" in Histoire.faits(jeu)) && !jeu.terrain.isDirectory) m.add("terrain")
        if (aConstruit(jeu) && !File(jeu.terrain, "nid").isDirectory) m.add("nid")
        return m
    }

    fun commande(jeu: Jeu) = "mkdir -p ~/${jeu.terrain.name}/nid"

    /** La commande à taper si le terrain a disparu (pour le bandeau de l'écran principal), sinon null. */
    fun perdu(jeu: Jeu): String? = etat(jeu).optJSONObject("perdu")?.optString("cmd")?.ifEmpty { null }

    /** Le bandeau de l'écran principal tant que le terrain n'est pas reconstruit, ou null. */
    fun bandeau(jeu: Jeu): String? {
        val cmd = perdu(jeu) ?: return null
        return t("app.terrain.titre") + "\n➜ `" + Regles.piege(cmd) + "`\n" + t("app.terrain.pourquoi")
    }

    private fun ecrire(f: File, texte: String, executable: Boolean = false) {
        f.parentFile?.mkdirs()
        f.writeText(texte)
        if (executable) f.setExecutable(true, false)
    }

    /** Remet les fichiers dont l'étape en cours a besoin, ou recule à l'étape qui les crée.
     *  Renvoie (fichiers remis, étape reculée ?). */
    fun reparerLecon(jeu: Jeu): Pair<List<String>, Boolean> {
        val remis = mutableListOf<String>()
        var recule = false
        val nid = File(jeu.terrain, "nid")
        val repas = File(nid, "repas.txt")
        val etape = jeu.etape
        fun reculer(vers: Int) {
            if (jeu.etape > vers) { jeu.etape = vers; recule = true }
        }
        fun trouve(nom: String) = Arbre.trouve(jeu, nom) != null
        fun remettreRepas() { ecrire(repas, "pomme\n"); remis.add("nid/repas.txt") }
        when (Histoire.leconId(jeu)) {
            "nid0" -> if (etape >= 2 && !nid.isDirectory) reculer(1)                 // le lit va dans le nid : il faut le refaire
            "nid1" -> if (etape >= 1 && !Indices.contient(repas, "pomme")) reculer(0)  // cat : on réécrit le repas
            "t3" -> if (nid.isDirectory && !repas.isFile) {                          // la leçon des droits a besoin du repas
                remettreRepas()
                reculer(1)          // le repas remis n'a plus son cadenas : on le remet (chmod 444) avant le >> refusé
            }
            "biblio1" -> if (etape == 0 && nid.isDirectory && !repas.isFile) remettreRepas()   // (la loupe aussi)
            "t4" -> if (nid.isDirectory) {
                if (etape == 0 && !repas.isFile) remettreRepas()
                else if (etape == 1 && !File(nid, "secours.txt").isFile && !File(jeu.terrain, "reserve.txt").isFile) {
                    reculer(0)
                    if (!repas.isFile) remettreRepas()
                }
            }
            "scripts0" -> if (nid.isDirectory && etape >= 1 && !trouve("miam.sh")) reculer(0)
            "scripts1", "scripts2" -> if (nid.isDirectory && !trouve("miam.sh")) {
                ecrire(File(nid, "miam.sh"), "echo \"Miam !\"\n", executable = Histoire.leconId(jeu) == "scripts2")
                remis.add("nid/miam.sh")
            }
            // les leçons du téléphone : la liste de courses, la carte du Doom
            "tuyaux0" -> if (etape >= 2 && !trouve("courses.txt")) reculer(1)
            "tuyaux1" -> if (etape >= 2 && !trouve("triee.txt")) reculer(1)
            "createur0" -> if (etape >= 1 && !File(jeu.terrain, "jeu/carte.txt").isFile) reculer(0)
        }
        return remis to recule
    }

    /**
     * À chaque commande (ligne) et de temps en temps (ligne = null), avant les leçons.
     * Renvoie un message pour le terminal, ou null.
     */
    fun verifier(jeu: Jeu, ligne: String?, colle: Boolean): String? {
        val tapee = ligne != null && !colle && !Regles.estColle(ligne)
        val m = manque(jeu)
        val e = etat(jeu)
        val perdu = e.optJSONObject("perdu")
        if (m.isNotEmpty()) {
            val cmd = commande(jeu)
            if (perdu == null || perdu.optString("cmd") != cmd) {
                e.put("perdu", org.json.JSONObject().put("cmd", cmd).put("t", System.currentTimeMillis()).put("n", 0))
                jeu.indiceLecon = null
                val dit = t("lec.terrain.perdu.dit", "cmd" to cmd)
                jeu.log(t("lec.terrain.perdu.log"))
                jeu.dire(dit, 20)
                jeu.animer("confus")
                return "🏚 $dit"
            }
            if (tapee) perdu.put("n", perdu.optInt("n") + 1)
            if (perdu.optInt("n") < AIDE_AUTO) return null
            File(jeu.terrain, "nid").mkdirs()                      // l'enfant n'y arrive pas : on l'aide
            if (manque(jeu).isNotEmpty()) return null
            e.remove("perdu")
            val (remis, _) = reparerLecon(jeu)
            jeu.log(t("lec.terrain.repare.log"))
            val dit = t("lec.terrain.auto.dit")
            jeu.dire(dit, 14)
            var msg = "🏡 $dit"
            if (remis.isNotEmpty()) {
                val r = t("lec.terrain.refait.dit", "fichiers" to remis.joinToString(", "))
                jeu.dire(r, 10)
                msg += "\n$r"
            }
            jeu.animer("content")
            return msg
        }
        val (remis, recule) = reparerLecon(jeu)
        var msg: String? = null
        if (perdu != null) {
            e.remove("perdu")
            jeu.log(t("lec.terrain.repare.log"))
            val dit = t("lec.terrain.repare.dit")
            jeu.dire(dit, 12)
            jeu.animer("content")
            jeu.ajouterXp(5)
            msg = "🏡 $dit"
        }
        val suite = when {
            remis.isNotEmpty() -> t("lec.terrain.refait.dit", "fichiers" to remis.joinToString(", "))
            recule -> t("lec.terrain.recule.dit")
            else -> null
        }
        if (suite != null) {
            jeu.indiceLecon = null
            jeu.dire(suite, 10)
            msg = if (msg == null) suite else "$msg\n$suite"
        }
        return msg
    }
}
