package fr.terminagotchi

import java.io.File

/**
 * Le petit sqlite3 de l'appli (la Salle des Données, D-SQL « la base de données ») : Android a SQLite intégré, l'appli
 * l'utilise pour une commande `sqlite3` limitée au nécessaire, comme pour openssl et gpg :
 *   - `sqlite3 [-header] collection.db "SELECT …;"` (une ou plusieurs requêtes SELECT / WITH), `.tables`, `.schema [table]` ;
 *   - la base est ouverte en LECTURE SEULE (pas de DELETE, pas de DROP : seulement lire) ;
 *   - la sortie est celle du vrai outil en mode « list » : valeurs séparées par |, un réel avec 15 chiffres significatifs
 *     et toujours un point (24.0), NULL vide, .tables en colonnes séparées de deux espaces.
 * Le moteur (MoteurSql) est le SQLite du téléphone ; les tests JVM en branchent un autre (le SQLite de Python). La mise en
 * forme est comparée aux vecteurs communs (donnees/donnees/vecteurs.json), calculés avec le vrai moteur SQLite.
 */
object DonneesSql {
    class Resultat(val colonnes: List<String>, val lignes: List<List<Any?>>)
    class Erreur(msg: String) : Exception(msg)

    interface Moteur {
        /** Fabrique la base (le fichier est remplacé) : les instructions et leurs paramètres. */
        fun creer(f: File, instructions: List<Pair<String, List<Any?>>>): Boolean
        /** Une requête en lecture seule ; lance Erreur avec le message de SQLite. */
        fun requete(f: File, sql: String): Resultat
    }

    /** Le SQLite du téléphone (android.database.sqlite). */
    object MoteurAndroid : Moteur {
        override fun creer(f: File, instructions: List<Pair<String, List<Any?>>>): Boolean = try {
            if (f.exists()) f.delete()
            val db = android.database.sqlite.SQLiteDatabase.openOrCreateDatabase(f, null)
            try {
                db.beginTransaction()
                for ((sql, p) in instructions) db.execSQL(sql, p.toTypedArray())
                db.setTransactionSuccessful()
                db.endTransaction()
            } finally { db.close() }
            true
        } catch (e: Exception) { false }

        override fun requete(f: File, sql: String): Resultat {
            val db = try { android.database.sqlite.SQLiteDatabase.openDatabase(f.path, null, android.database.sqlite.SQLiteDatabase.OPEN_READONLY) }
                catch (e: Exception) { throw Erreur("unable to open database \"${f.name}\"") }
            try {
                val c = db.rawQuery(sql, null)
                try {
                    val cols = c.columnNames.toList()
                    val l = mutableListOf<List<Any?>>()
                    while (c.moveToNext()) l.add(cols.indices.map { i ->
                        when (c.getType(i)) {
                            android.database.Cursor.FIELD_TYPE_NULL -> null
                            android.database.Cursor.FIELD_TYPE_INTEGER -> c.getLong(i)
                            android.database.Cursor.FIELD_TYPE_FLOAT -> c.getDouble(i)
                            else -> c.getString(i)
                        }
                    })
                    return Resultat(cols, l)
                } finally { c.close() }
            } catch (e: Erreur) { throw e
            } catch (e: Exception) { throw Erreur((e.message ?: "erreur").substringBefore(" (code")) }
            finally { db.close() }
        }
    }

    @Volatile var moteur: Moteur = MoteurAndroid

    /** Une valeur comme l'outil sqlite3 l'écrit (mode list) : réel en %!.15g, entier tel quel, NULL vide. */
    fun valeur(v: Any?): String = when (v) {
        null -> ""
        is Long, is Int -> v.toString()
        is Double -> {
            val s = DonneesAwk.formatG(v, 15)
            if (s == "nan" || s.endsWith("inf")) s
            else { val m = s.substringBefore('e'); val e = if ('e' in s) "e" + s.substringAfter('e') else ""
                (if ('.' in m) m else "$m.0") + e }
        }
        else -> v.toString()
    }

    fun lignes(r: Resultat, entete: Boolean = false): List<String> =
        (if (entete && r.colonnes.isNotEmpty()) listOf(r.colonnes.joinToString("|")) else emptyList()) + r.lignes.map { l -> l.joinToString("|") { valeur(it) } }

    /** .tables : les noms rangés, en colonnes séparées de 2 espaces. */
    fun tablesTexte(noms: List<String>): String {
        if (noms.isEmpty()) return ""
        val w = noms.maxOf { it.length }
        return noms.sorted().joinToString("  ") { it.padEnd(w) }.trimEnd()
    }

    private val LECTURE = Regex("^\\s*(select|with)\\b", RegexOption.IGNORE_CASE)

    /** (texte, code) de `sqlite3 [-header] BASE REQUÊTE` ; args : les mots après « sqlite3 », sans guillemets. */
    fun cli(args: List<String>, ici: File, terrain: File): Pair<String, Int> {
        val entete = "-header" in args
        val r = args.filter { !it.startsWith("-") }
        if (r.size < 2) return t("dn.tel.sqlite") + "\n" + t("dn.sql.aide_cli").replace("tg donnees sqlite3", "sqlite3") to 1
        val f = File(r[0]).let { if (it.isAbsolute) it else File(ici, r[0]) }
        if (!f.canonicalPath.startsWith(terrain.canonicalPath + "/")) return t("dn.tel.sqlite_lecture") to 1
        if (!f.isFile) return t("dn.sql.pas_de_base", "fichier" to f.name) to 1
        val sql = r.drop(1).joinToString(" ").trim()
        return try {
            when {
                sql.startsWith(".tables") -> tablesTexte(moteur.requete(f, "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
                    .lignes.map { it[0].toString() }) to 0
                sql.startsWith(".schema") -> {
                    val nom = sql.split(Regex("\\s+")).getOrNull(1)
                    val q = "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL" + (nom?.let { " AND name = '" + it.replace("'", "''") + "'" } ?: "") + " ORDER BY name"
                    moteur.requete(f, q).lignes.joinToString("\n") { it[0].toString() + ";" } to 0
                }
                sql.startsWith(".") -> t("dn.sql.point_inconnu", "cmd" to sql.split(Regex("\\s+"))[0]) to 1
                else -> {
                    val out = mutableListOf<String>()
                    for (q in sql.split(";").map { it.trim() }.filter { it.isNotEmpty() }) {
                        if (!LECTURE.containsMatchIn(q)) return (out + t("dn.tel.sqlite_lecture")).joinToString("\n") to 1
                        out += lignes(moteur.requete(f, q), entete)
                    }
                    out.joinToString("\n") to 0
                }
            }
        } catch (e: Erreur) { "Error: ${e.message}" to 1 }
    }
}
