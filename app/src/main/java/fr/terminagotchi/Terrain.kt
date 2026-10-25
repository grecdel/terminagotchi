package fr.terminagotchi

import java.io.File

/**
 * Le terrain effacé (portage de pc/tg/terrain.py) : si l'enfant fait rm -rf ~/terrain_terminagotchi
 * (ou efface le nid), on le remarque et on l'aide à reconstruire, puis la leçon reprend au bon endroit.
 *
 *  1. Détection : la partie a déjà construit son terrain (leçon « Bâtisseur » finie) mais le dossier
 *     ~/terrain_terminagotchi ou son nid n'existe plus. UN TERRAIN PAR PARTIE (voir Parties.kt) : une
 *     nouvelle partie démarre sans terrain, mais tant que sa leçon 1 n'est pas finie, rien ne manque ;
 *     en changeant de partie, chacune retrouve le sien (rangé dans parties/terrain_<id>).
 *  2. Une bulle claire donne LA commande à taper (mkdir -p ~/terrain_terminagotchi/nid) ; un bandeau reste
 *     affiché tant que ce n'est pas fait (bandeau()). Si l'enfant n'y arrive pas, le jeu reconstruit lui-même
 *     après AIDE_AUTO commandes.
 *  3. Reprise : les fichiers indispensables à l'étape en cours sont remis (repas.txt pour la leçon des droits,
 *     miam.sh pour les scripts…), ou bien la leçon revient à l'étape qui les crée. Les monstres reviennent dès
 *     que le nid existe (Explo.debloquee).
 */
object Terrain {
    /** commandes tapées sans réussir : le jeu reconstruit lui-même */
    const val AIDE_AUTO = 12

    private fun etat(jeu: Jeu) = jeu.module("terrain")

    /** Vrai si la partie a déjà son terrain et son nid (leçon « Bâtisseur » finie). */
    fun aConstruit(jeu: Jeu) = jeu.lecon >= 2 || "Bâtisseur" in jeu.skills

    /** Ce qui a disparu et que l'enfant doit reconstruire (terrain, nid). */
    fun manque(jeu: Jeu): List<String> {
        val m = mutableListOf<String>()
        if (aConstruit(jeu)) {
            if (!jeu.terrain.isDirectory) m.add("terrain")
            if (!File(jeu.terrain, "nid").isDirectory) m.add("nid")
        }
        return m
    }

    fun commande(jeu: Jeu) = "mkdir -p ~/${jeu.terrain.name}/nid"

    /** La commande à taper si le terrain a disparu (pour le bandeau de l'écran principal), sinon null. */
    fun perdu(jeu: Jeu): String? = etat(jeu).optJSONObject("perdu")?.optString("cmd")?.ifEmpty { null }

    /** Le bandeau de l'écran principal tant que le terrain n'est pas reconstruit, ou null. */
    fun bandeau(jeu: Jeu): String? {
        val cmd = perdu(jeu) ?: return null
        return t("app.terrain.titre") + "\n➜ " + Regles.piege(cmd) + "\n" + t("app.terrain.pourquoi")
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
        if (!jeu.troncFini) {
            when (jeu.lecon) {
                1 -> if (etape >= 1 && !jeu.terrain.isDirectory) reculer(0)          // cd terrain : il faut d'abord le refaire
                2 -> if (etape >= 1 && !Indices.contient(repas, "pomme")) reculer(0) // cat / grep : on réécrit le repas
                3 -> if (nid.isDirectory && !repas.isFile) {                          // la leçon des droits a besoin du repas
                    ecrire(repas, "pomme\n"); remis.add("nid/repas.txt")
                }
                4 -> if (nid.isDirectory) {
                    if (etape == 0 && !repas.isFile) {
                        ecrire(repas, "pomme\n"); remis.add("nid/repas.txt")
                    } else if (etape == 1 && !File(nid, "secours.txt").isFile && !File(jeu.terrain, "reserve.txt").isFile) {
                        reculer(0)
                        if (!repas.isFile) { ecrire(repas, "pomme\n"); remis.add("nid/repas.txt") }
                    }
                }
            }
            return remis to recule
        }
        val b = jeu.brancheActive() ?: return remis to recule
        val i = jeu.progresBranche(b)
        when (b) {
            "scripts" -> if (nid.isDirectory) {
                if (i == 0 && etape >= 1 && !trouve("miam.sh")) reculer(0)
                else if (i >= 1 && !trouve("miam.sh")) {
                    ecrire(File(nid, "miam.sh"), "echo \"Miam !\"\n", executable = i >= 2)
                    remis.add("nid/miam.sh")
                }
            }
            // les branches du téléphone : la liste de courses, la carte du Doom
            "tuyaux" -> {
                if (i == 0 && etape >= 2 && !trouve("courses.txt")) reculer(1)
                else if (i == 1 && etape >= 2 && !trouve("triee.txt")) reculer(1)
            }
            "createur" -> if (i == 0 && etape >= 1 && !File(jeu.terrain, "jeu/carte.txt").isFile) reculer(0)
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
