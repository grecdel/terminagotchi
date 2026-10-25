package fr.terminagotchi

import org.json.JSONArray
import org.json.JSONObject
import java.io.File

/**
 * Donjon aléatoire : chaque salle est un vrai dossier.
 *  - se déplacer : cd, cd .. · voir : ls, ls -a (monstres cachés) · lire : cat
 *  - ramasser : mv objet ~/terrain_terminagotchi/donjon/sac/ · s'équiper : equipe · soigner : bois
 *  - combattre : attaque · carte : plan · objectifs : quetes
 *  - salle verrouillée : chmod 755 · étage suivant : cd escalier
 */
object Donjon {
    class Res(val texte: String, val aller: File? = null)

    private class Objet(val nom: String, val type: String, val bonus: Int, val desc: String)

    private val OBJETS = listOf(
        Objet("dague", "arme", 1, "Une petite lame rapide."),
        Objet("epee_rouillee", "arme", 2, "Elle a connu des jours meilleurs."),
        Objet("hache_de_combat", "arme", 3, "Lourde mais redoutable."),
        Objet("epee_runique", "arme", 5, "Des runes de code brillent sur la lame."),
        Objet("tunique_epaisse", "armure", 1, "Mieux que rien."),
        Objet("cotte_de_mailles", "armure", 2, "Cliquette à chaque pas."),
        Objet("armure_de_plaques", "armure", 4, "Le top de la protection."),
        Objet("potion_de_soin", "potion", 10, "Rend 10 cœurs."),
    )
    private val SALLES = listOf("salle_des_torches", "crypte", "armurerie", "bibliotheque", "cachot", "cuisine",
        "chapelle", "galerie", "puits", "forge", "jardin_souterrain", "salle_du_trone", "catacombes",
        "observatoire", "laboratoire", "dortoir", "cellier", "salle_des_miroirs")
    private val MONSTRES = listOf("rat_des_cables", "gobelin_glitch", "slime_binaire", "squelette_zombie",
        "chauve_souris_404", "araignee_du_web", "fantome_du_cache")
    private val QUETES = mapOf(
        "objet" to "Ramasse un objet : mv objet ~/terrain_terminagotchi/donjon/sac/",
        "monstre" to "Bats un monstre caché (trouve-le avec ls -a, puis : attaque)",
        "verrou" to "Ouvre la salle verrouillée 🔒 (indice : chmod 755 nom_de_la_salle)",
        "parchemin" to "Lis le parchemin caché (indice : ls -a puis cat)",
        "escalier" to "Trouve l'escalier 🪜 et descends (cd escalier)",
    )

    fun racine(jeu: Jeu) = File(jeu.terrain, "donjon")
    private fun etageDir(jeu: Jeu) = File(racine(jeu), "etage")
    private fun sac(jeu: Jeu) = File(racine(jeu), "sac")
    private fun etat(jeu: Jeu) = jeu.module("donjon")

    fun dedans(jeu: Jeu, d: File) = d.absolutePath.startsWith(racine(jeu).absolutePath)

    private fun pvMax(jeu: Jeu) = 20 + (jeu.stats["Endurance"] ?: 0) / 3 + etat(jeu).optInt("etage", 1) * 2

    private fun deverrouiller(f: File) {
        if (!f.exists()) return
        f.setReadable(true, true)
        f.setWritable(true, true)
        f.setExecutable(true, true)
        if (f.isDirectory) f.listFiles()?.forEach { deverrouiller(it) }
    }

    // ---------------------------------------------------------------- génération
    private fun generer(jeu: Jeu, numero: Int): File {
        val e = etat(jeu)
        val dir = etageDir(jeu)
        deverrouiller(dir)
        dir.deleteRecursively()
        dir.mkdirs()
        sac(jeu).mkdirs()
        e.put("etage", numero)
        e.put("pv", pvMax(jeu))
        e.put("vaincusEtage", 0)
        e.put("sacDepart", sac(jeu).listFiles()?.size ?: 0)

        // arbre de salles
        val noms = SALLES.shuffled().toMutableList()
        val salles = mutableListOf<File>()
        fun creer(parent: File, profondeur: Int) {
            if (profondeur > 3 || noms.isEmpty()) return
            val n = if (profondeur == 1) (2..3).random() else (0..2).random()
            repeat(n) {
                if (noms.isEmpty()) return
                val s = File(parent, noms.removeAt(0))
                s.mkdirs()
                salles.add(s)
                creer(s, profondeur + 1)
            }
        }
        creer(dir, 1)
        if (salles.isEmpty()) salles.add(File(dir, "crypte").apply { mkdirs() })

        // objets
        repeat((2..4).random()) {
            val o = OBJETS.filter { it.type != "arme" || it.bonus <= 2 + numero }.random()
            File(salles.random(), "${o.nom}.objet").writeText("${o.type} : ${o.nom} (+${o.bonus})\n${o.desc}\n")
        }
        // monstres cachés
        salles.shuffled().take((2..3).random()).forEach { s ->
            val m = MONSTRES.random()
            File(s, ".monstre_$m").writeText("${m.replace('_', ' ')}\nCœurs (PV) : ${6 + numero * 3}\nForce (ATTAQUE) : ${2 + numero}\n")
        }
        // parchemin caché
        File(salles.random(), ".parchemin").writeText(
            "📜 Parchemin ancien :\n« Celui qui maîtrise ls -a voit l'invisible.\n" +
                "Celui qui maîtrise chmod ouvre toutes les portes.\n" +
                "Celui qui maîtrise find trouve toujours l'escalier. »\n")
        // salle verrouillée avec un trésor
        val verrou = File(salles.random(), "tresor_scelle")
        verrou.mkdirs()
        val tresor = OBJETS.filter { it.type != "potion" }.maxByOrNull { if (it.bonus <= 3 + numero) it.bonus else 0 }!!
        File(verrou, "${tresor.nom}.objet").writeText("${tresor.type} : ${tresor.nom} (+${tresor.bonus})\n${tresor.desc}\n")
        verrou.setExecutable(false, false)
        verrou.setReadable(false, false)
        // escalier dans la salle la plus profonde
        val profonde = salles.maxByOrNull { it.absolutePath.count { c -> c == '/' } }!!
        File(profonde, "escalier").mkdirs()

        // quêtes : 3 au hasard (l'escalier est toujours la dernière)
        val q = JSONArray()
        (listOf("objet", "monstre", "verrou", "parchemin").shuffled().take(2) + "escalier").forEach {
            q.put(JSONObject().put("id", it).put("fait", false))
        }
        e.put("quetes", q)
        return dir
    }

    // ---------------------------------------------------------------- commandes
    fun entrer(jeu: Jeu, arg: String): Res {
        val e = etat(jeu)
        if (!File(jeu.terrain, "nid").isDirectory) {
            return Res("Le donjon s'ouvre après la leçon « Construire mon nid ».")
        }
        val nouveau = arg == "nouveau" || !etageDir(jeu).isDirectory
        if (nouveau) {
            val d = generer(jeu, 1)
            jeu.log("🏰 Un donjon est apparu !")
            return Res("🏰 Tu entres dans le donjon (étage 1) !\n" +
                "Commandes : ls, ls -a, cd, cat · plan · quetes · attaque · sac · equipe · bois\n" +
                "Tes objets vont dans ~/terrain_terminagotchi/donjon/sac/\n\n" + texteQuetes(jeu), d)
        }
        return Res("🏰 Retour au donjon, étage ${e.optInt("etage", 1)}. (« donjon nouveau » pour recommencer)", etageDir(jeu))
    }

    fun plan(jeu: Jeu, ici: File): String {
        val dir = etageDir(jeu)
        if (!dir.isDirectory) return "Pas de donjon : tape « donjon »."
        val sb = StringBuilder("🗺 Étage ${etat(jeu).optInt("etage", 1)}\n")
        fun dessiner(d: File, prefixe: String) {
            val enfants = (d.listFiles()?.filter { it.isDirectory && !it.name.startsWith(".") } ?: emptyList()).sortedBy { it.name }
            enfants.forEachIndexed { i, c ->
                val dernier = i == enfants.size - 1
                val ico = when {
                    c.name == "escalier" -> "🪜 "
                    !c.canExecute() -> "🔒 "
                    else -> ""
                }
                val nbObj = c.listFiles()?.count { it.name.endsWith(".objet") } ?: 0
                val obj = if (nbObj > 0) " 💎×$nbObj" else ""
                val toi = if (c.absolutePath == ici.absolutePath) "  ◀ toi" else ""
                sb.append("$prefixe${if (dernier) "└─ " else "├─ "}$ico${c.name}$obj$toi\n")
                if (c.canExecute()) dessiner(c, prefixe + if (dernier) "   " else "│  ")
            }
        }
        sb.append("🚪 entrée" + (if (ici.absolutePath == dir.absolutePath) "  ◀ toi" else "") + "\n")
        dessiner(dir, "")
        sb.append("(les monstres 👾 sont cachés : ls -a dans chaque salle)")
        return sb.toString()
    }

    fun texteQuetes(jeu: Jeu): String {
        val q = etat(jeu).optJSONArray("quetes") ?: return "Pas de quête : tape « donjon »."
        val sb = StringBuilder("📜 Quêtes de l'étage ${etat(jeu).optInt("etage", 1)}\n")
        for (i in 0 until q.length()) {
            val o = q.getJSONObject(i)
            sb.append(if (o.optBoolean("fait")) "  ✅ " else "  ⬜ ").append(QUETES[o.getString("id")]).append('\n')
        }
        sb.append("❤ ${etat(jeu).optInt("pv", pvMax(jeu))}/${pvMax(jeu)} · ${texteEquipement(jeu)}")
        return sb.toString()
    }

    private fun texteEquipement(jeu: Jeu): String {
        val e = etat(jeu)
        val a = e.optString("arme", "")
        val p = e.optString("armure", "")
        return "arme : ${a.ifEmpty { "poings" }} · armure : ${p.ifEmpty { "aucune" }}"
    }

    private fun lireObjet(f: File): Objet? {
        val nom = f.name.removeSuffix(".objet")
        return OBJETS.firstOrNull { it.nom == nom }
    }

    fun texteSac(jeu: Jeu): String {
        val objets = sac(jeu).listFiles()?.filter { it.name.endsWith(".objet") } ?: emptyList()
        if (objets.isEmpty()) return "🎒 Sac vide. Ramasse des objets : mv objet ~/terrain_terminagotchi/donjon/sac/\n${texteEquipement(jeu)}"
        return "🎒 Sac :\n" + objets.joinToString("\n") { f ->
            val o = lireObjet(f)
            "  • ${f.name.removeSuffix(".objet")}" + (o?.let { " (${it.type} +${it.bonus})" } ?: "")
        } + "\n${texteEquipement(jeu)}\n(equipe nom · bois potion_de_soin)"
    }

    fun equipe(jeu: Jeu, nom: String): String {
        val f = File(sac(jeu), "${nom.removeSuffix(".objet")}.objet")
        if (!f.isFile) return "Ce n'est pas dans ton sac. Regarde avec : sac"
        val o = lireObjet(f) ?: return "Objet inconnu."
        if (o.type == "potion") return "Une potion se boit : bois ${o.nom}"
        etat(jeu).put(o.type, o.nom)
        return "⚔ ${jeu.nom} s'équipe : ${o.nom} (+${o.bonus} ${if (o.type == "arme") "force" else "bouclier"})"
    }

    fun bois(jeu: Jeu, nom: String): String {
        val f = File(sac(jeu), "${nom.ifEmpty { "potion_de_soin" }.removeSuffix(".objet")}.objet")
        val o = if (f.isFile) lireObjet(f) else null
        if (o == null || o.type != "potion") return "Pas de potion dans le sac."
        f.delete()
        val e = etat(jeu)
        e.put("pv", (e.optInt("pv", pvMax(jeu)) + o.bonus).coerceAtMost(pvMax(jeu)))
        return "🧪 Glou glou… ❤ ${e.optInt("pv")}/${pvMax(jeu)}"
    }

    private fun bonus(type: String, jeu: Jeu): Int {
        val nom = etat(jeu).optString(type, "")
        return OBJETS.firstOrNull { it.nom == nom }?.bonus ?: 0
    }

    fun attaque(jeu: Jeu, ici: File): Res {
        if (!dedans(jeu, ici)) return Res("Il n'y a pas de monstre ici : les monstres vivent dans le donjon (tape « donjon »).")
        val m = ici.listFiles()?.firstOrNull { it.name.startsWith(".monstre_") }
            ?: return Res("Aucun monstre dans cette salle. As-tu bien regardé avec ls -a ?")
        val lignes = m.readLines()
        val nomM = lignes.firstOrNull() ?: "monstre"
        var pvM = lignes.firstOrNull { it.startsWith("PV") || it.startsWith("Cœurs") }?.substringAfter(':')?.trim()?.toIntOrNull() ?: 8
        val atkM = lignes.firstOrNull { it.startsWith("ATTAQUE") || it.startsWith("Force") }?.substringAfter(':')?.trim()?.toIntOrNull() ?: 3
        val e = etat(jeu)
        var pv = e.optInt("pv", pvMax(jeu))
        val atk = 2 + (jeu.stats["Force"] ?: 0) / 4 + bonus("arme", jeu)
        val def = bonus("armure", jeu) + (jeu.stats["Endurance"] ?: 0) / 8
        val sb = StringBuilder("⚔ Combat contre $nomM ! (toi : ❤ $pv, force $atk, bouclier $def)\n")
        var tour = 0
        while (pvM > 0 && pv > 0 && tour < 30) {
            tour++
            val coup = (atk + (0..2).random()).coerceAtLeast(1)
            pvM -= coup
            if (tour <= 3) sb.append("  Tour $tour : ${jeu.nom} frappe ($coup)")
            if (pvM <= 0) { if (tour <= 3) sb.append('\n'); break }
            val subi = (atkM + (0..1).random() - def).coerceAtLeast(1)
            pv -= subi
            if (tour <= 3) sb.append(", le monstre riposte ($subi)\n")
        }
        if (tour > 3) sb.append("  … $tour tours de combat …\n")
        if (pv > 0) {
            m.delete()
            e.put("pv", pv)
            e.put("vaincusEtage", e.optInt("vaincusEtage") + 1)
            e.put("vaincus", e.optInt("vaincus") + 1)
            val gain = 10 + 5 * e.optInt("etage", 1)
            jeu.ajouterXp(gain)
            jeu.stats["Force"] = (jeu.stats["Force"] ?: 0) + 1
            if ((1..3).random() == 1) {
                val butin = OBJETS.filter { it.type == "potion" || it.bonus <= 2 }.random()
                File(ici, "${butin.nom}.objet").writeText("${butin.type} : ${butin.nom} (+${butin.bonus})\n${butin.desc}\n")
                sb.append("💎 Il a laissé tomber : ${butin.nom}.objet\n")
            }
            jeu.log("⚔ $nomM vaincu !")
            sb.append("🏆 Victoire ! +$gain XP · ❤ restants : $pv/${pvMax(jeu)}")
            return Res(sb.toString())
        }
        e.put("pv", pvMax(jeu))
        jeu.log("💫 ${jeu.nom} est KO…")
        sb.append("💫 KO… ${jeu.nom} se réveille à l'entrée de l'étage, soigné. Équipe-toi mieux (sac, equipe) !")
        return Res(sb.toString(), etageDir(jeu))
    }

    /** Après chaque commande : quêtes, escalier. */
    fun verifier(jeu: Jeu, ici: File, ligne: String?): Res? {
        val e = etat(jeu)
        val q = e.optJSONArray("quetes") ?: return null
        if (!etageDir(jeu).isDirectory) return null
        val msgs = mutableListOf<String>()
        var aller: File? = null
        // escalier : étage suivant
        if (ici.name == "escalier" && dedans(jeu, ici)) {
            marquer(q, "escalier")
            val n = e.optInt("etage", 1) + 1
            val reste = (0 until q.length()).count { !q.getJSONObject(it).optBoolean("fait") }
            if (reste == 0) {
                jeu.ajouterXp(30)
                msgs.add("🌟 Toutes les quêtes de l'étage terminées ! +30 XP")
            }
            aller = generer(jeu, n)
            jeu.log("🪜 Étage $n atteint !")
            msgs.add("🪜 Tu descends à l'étage $n… les monstres sont plus forts ici !\n" + texteQuetes(jeu))
            return Res(msgs.joinToString("\n"), aller)
        }
        for (i in 0 until q.length()) {
            val o = q.getJSONObject(i)
            if (o.optBoolean("fait")) continue
            val ok = when (o.getString("id")) {
                "objet" -> (sac(jeu).listFiles()?.size ?: 0) > e.optInt("sacDepart")
                "monstre" -> e.optInt("vaincusEtage") > 0
                "verrou" -> etageDir(jeu).walkTopDown().any { it.name == "tresor_scelle" && it.canExecute() }
                "parchemin" -> ligne != null && Regex("^(cat|head|more|less)\\b.*parchemin").containsMatchIn(ligne)
                else -> false
            }
            if (ok) {
                o.put("fait", true)
                jeu.ajouterXp(15)
                msgs.add("✅ Quête accomplie : ${QUETES[o.getString("id")]} (+15 XP)")
            }
        }
        return if (msgs.isEmpty()) null else Res(msgs.joinToString("\n"), aller)
    }

    private fun marquer(q: JSONArray, id: String) {
        for (i in 0 until q.length()) if (q.getJSONObject(i).getString("id") == id) q.getJSONObject(i).put("fait", true)
    }
}
