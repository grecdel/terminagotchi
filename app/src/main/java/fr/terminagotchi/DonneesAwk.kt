package fr.terminagotchi

import java.math.BigDecimal
import java.math.MathContext
import java.math.RoundingMode

/**
 * Le petit awk de l'appli (la Salle des Données, D4 « la calculatrice des savants ») : le téléphone n'a pas toujours un
 * awk (toybox ne l'a ajouté que récemment), alors l'appli apporte le nécessaire, et RIEN de plus :
 *   - options -F SEP (une virgule, un caractère), sans -F : les colonnes séparées par des espaces ;
 *   - règles « motif { actions } », BEGIN, END, motif seul (affiche la ligne) ;
 *   - $N, $(expr), $NF, NR, NF ; variables, tableaux a[k] (for (k in a) dans l'ordre d'arrivée) ;
 *   - print (OFS = espace), if / else, while, for, exit, next ; = += -= *= /= %= ++ -- ;
 *   - + - * / % ! - unaire, < <= > >= == != && || ?: et la concaténation ;
 *   - les nombres écrits comme awk (entier sans virgule, sinon %.6g).
 * Les programmes des leçons et une trentaine d'autres sont comparés à la sortie du VRAI awk (vecteurs communs
 * donnees/donnees/vecteurs.json, tests/jvm/Donnees.kt ; pc/outils/test_donnees.py les rejoue avec l'awk installé).
 */
object DonneesAwk {
    class Erreur(msg: String) : Exception(msg)

    // ---------------------------------------------------------------- les nombres comme Python %g (et awk)
    /** x écrit avec p chiffres significatifs, comme « %.pg » en C et en Python (zéros inutiles retirés). */
    fun formatG(x: Double, p: Int): String {
        if (x.isNaN()) return "nan"
        if (x.isInfinite()) return if (x > 0) "inf" else "-inf"
        if (x == 0.0) return if (1.0 / x < 0) "-0" else "0"
        val r = BigDecimal(x).round(MathContext(p, RoundingMode.HALF_EVEN))
        val e = r.precision() - r.scale() - 1
        fun nettoie(s: String) = if ('.' in s) s.trimEnd('0').trimEnd('.') else s
        if (e >= -4 && e < p) return nettoie(r.setScale(maxOf(0, p - 1 - e), RoundingMode.HALF_EVEN).toPlainString())
        val m = nettoie(r.movePointLeft(e).setScale(p - 1, RoundingMode.HALF_EVEN).toPlainString())
        val ae = Math.abs(e)
        return m + "e" + (if (e < 0) "-" else "+") + (if (ae < 10) "0$ae" else "$ae")
    }

    /** Comment awk écrit un nombre avec print : un entier sans virgule, sinon %.6g. */
    fun nombre(x: Double): String =
        if (x == Math.floor(x) && Math.abs(x) < 1e15) (if (x == 0.0) "0" else x.toLong().toString()) else formatG(x, 6)

    // ---------------------------------------------------------------- les valeurs
    private val NUMERIQUE = Regex("^\\s*[-+]?(\\d+\\.?\\d*([eE][-+]?\\d+)?|\\.\\d+([eE][-+]?\\d+)?)\\s*$")
    private val DEBUT_NOMBRE = Regex("^\\s*[-+]?(\\d+\\.?\\d*([eE][-+]?\\d+)?|\\.\\d+([eE][-+]?\\d+)?)")

    /** Une valeur awk : un nombre, une chaîne, ou une chaîne venue des données qui ressemble à un nombre (strnum). */
    class V(val s: String?, val n: Double?, val strnum: Boolean = false) {
        fun num(): Double = n ?: (DEBUT_NOMBRE.find(s ?: "")?.value?.trim()?.toDoubleOrNull() ?: 0.0)
        fun str(): String = s ?: nombre(n ?: 0.0)
        val numerique: Boolean get() = s == null || strnum
        fun vrai(): Boolean = if (numerique) num() != 0.0 else (s ?: "").isNotEmpty()
    }
    private fun nb(x: Double) = V(null, x)
    private fun ch(s: String) = V(s, null)
    private fun donnee(s: String) = if (NUMERIQUE.matches(s)) V(s, s.trim().toDouble(), true) else V(s, null)
    private val VIDE = V("", 0.0, true)

    // ---------------------------------------------------------------- les jetons
    private class Jeton(val t: String, val v: String)

    private fun jetons(src: String): List<Jeton> {
        val out = mutableListOf<Jeton>()
        var i = 0
        val ops = listOf("+=", "-=", "*=", "/=", "%=", "==", "!=", "<=", ">=", "&&", "||", "++", "--")
        while (i < src.length) {
            val c = src[i]
            when {
                c == '\n' || c == ';' -> { out.add(Jeton("fin", c.toString())); i++ }
                c.isWhitespace() -> i++
                c == '\\' && i + 1 < src.length && src[i + 1] == '\n' -> i += 2
                c == '#' -> { while (i < src.length && src[i] != '\n') i++ }
                c.isDigit() || (c == '.' && i + 1 < src.length && src[i + 1].isDigit()) -> {
                    val m = Regex("^(\\d+\\.?\\d*([eE][-+]?\\d+)?|\\.\\d+([eE][-+]?\\d+)?)").find(src.substring(i))!!
                    out.add(Jeton("nombre", m.value)); i += m.value.length
                }
                c == '"' -> {
                    val sb = StringBuilder(); i++
                    while (i < src.length && src[i] != '"') {
                        if (src[i] == '\\' && i + 1 < src.length) {
                            i++
                            sb.append(when (src[i]) { 'n' -> '\n'; 't' -> '\t'; '"' -> '"'; '\\' -> '\\'; '/' -> '/'; else -> { sb.append('\\'); src[i] } })
                        } else sb.append(src[i])
                        i++
                    }
                    if (i >= src.length) throw Erreur("chaîne non fermée")
                    i++
                    out.add(Jeton("chaine", sb.toString()))
                }
                c.isLetter() || c == '_' -> {
                    val m = Regex("^[A-Za-z_][A-Za-z_0-9]*").find(src.substring(i))!!
                    out.add(Jeton(if (m.value in MOTS) m.value else "nom", m.value)); i += m.value.length
                }
                else -> {
                    val op = ops.firstOrNull { src.startsWith(it, i) }
                    if (op != null) { out.add(Jeton(op, op)); i += 2 }
                    else if (c in "+-*/%!<>=(){}[],?:$") { out.add(Jeton(c.toString(), c.toString())); i++ }
                    else throw Erreur("caractère inattendu : $c")
                }
            }
        }
        out.add(Jeton("eof", ""))
        return out
    }
    private val MOTS = setOf("BEGIN", "END", "print", "if", "else", "while", "for", "in", "exit", "next")

    // ---------------------------------------------------------------- l'arbre du programme
    private sealed class E {
        class Num(val v: Double) : E()
        class Ch(val v: String) : E()
        class Var(val nom: String) : E()
        class Tab(val nom: String, val k: E) : E()
        class Champ(val k: E) : E()
        class Bin(val op: String, val a: E, val b: E) : E()
        class Un(val op: String, val a: E) : E()
        class Aff(val op: String, val cible: E, val v: E) : E()
        class Inc(val op: String, val pre: Boolean, val cible: E) : E()
        class Cond(val c: E, val a: E, val b: E) : E()
        class Concat(val a: E, val b: E) : E()
    }
    private sealed class S {
        class Print(val l: List<E>) : S()
        class Expr(val e: E) : S()
        class Si(val c: E, val a: S, val b: S?) : S()
        class Tant(val c: E, val corps: S) : S()
        class Pour(val init: S?, val c: E?, val incr: S?, val corps: S) : S()
        class PourDans(val v: String, val tab: String, val corps: S) : S()
        class Bloc(val l: List<S>) : S()
        class Sortie(val e: E?) : S()
        object Suivante : S()
    }
    private class Regle(val genre: String, val motif: E?, val action: S?)

    private class Lecteur(val j: List<Jeton>) {
        var i = 0
        fun voit(t: String) = j[i].t == t
        fun prend(t: String): Jeton { if (!voit(t)) throw Erreur("attendu « $t », trouvé « ${j[i].v} »"); return j[i++] }
        fun saute() { while (voit("fin")) i++ }
        var sansPlusGrand = false

        fun programme(): List<Regle> {
            val out = mutableListOf<Regle>()
            saute()
            while (!voit("eof")) {
                when {
                    voit("BEGIN") -> { i++; out.add(Regle("BEGIN", null, bloc())) }
                    voit("END") -> { i++; out.add(Regle("END", null, bloc())) }
                    voit("{") -> out.add(Regle("", null, bloc()))
                    else -> { val m = expr(); out.add(Regle("", m, if (voit("{")) bloc() else null)) }
                }
                saute()
            }
            return out
        }

        fun bloc(): S.Bloc {
            prend("{")
            val l = mutableListOf<S>()
            saute()
            while (!voit("}")) { l.add(instr()); saute() }
            prend("}")
            return S.Bloc(l)
        }

        fun simple(): S? = if (voit("fin") || voit(")")) null else instr()

        fun instr(): S = when {
            voit("{") -> bloc()
            voit("print") -> {
                i++
                val l = mutableListOf<E>()
                if (!voit("fin") && !voit("}") && !voit("eof")) {
                    sansPlusGrand = true
                    l.add(expr()); while (voit(",")) { i++; l.add(expr()) }
                    sansPlusGrand = false
                }
                if (voit(">")) throw Erreur("print > fichier : pas dans le petit awk (redirige toute la commande)")
                S.Print(l)
            }
            voit("if") -> {
                i++; prend("("); val c = expr(); prend(")"); saute()
                val a = instr()
                val k = i; saute()
                if (voit("else")) { i++; saute(); S.Si(c, a, instr()) } else { i = k; S.Si(c, a, null) }
            }
            voit("while") -> { i++; prend("("); val c = expr(); prend(")"); saute(); S.Tant(c, instr()) }
            voit("for") -> {
                i++; prend("(")
                if (j[i].t == "nom" && j[i + 1].t == "in") {
                    val v = prend("nom").v; prend("in"); val t = prend("nom").v; prend(")"); saute()
                    S.PourDans(v, t, instr())
                } else {
                    val a = simple(); prend("fin"); val c = if (voit("fin")) null else expr(); prend("fin")
                    val b = simple(); prend(")"); saute()
                    S.Pour(a, c, b, instr())
                }
            }
            voit("exit") -> { i++; S.Sortie(if (voit("fin") || voit("}")) null else expr()) }
            voit("next") -> { i++; S.Suivante }
            else -> S.Expr(expr())
        }

        fun expr(): E = affectation()

        fun affectation(): E {
            val g = ternaire()
            if ((g is E.Var || g is E.Tab || g is E.Champ) && j[i].t in setOf("=", "+=", "-=", "*=", "/=", "%=")) {
                val op = j[i++].t
                return E.Aff(op, g, affectation())
            }
            return g
        }

        fun ternaire(): E {
            val c = ou()
            if (voit("?")) { i++; val a = ternaire(); prend(":"); return E.Cond(c, a, ternaire()) }
            return c
        }
        fun ou(): E { var a = et(); while (voit("||")) { i++; saute(); a = E.Bin("||", a, et()) }; return a }
        fun et(): E { var a = dans(); while (voit("&&")) { i++; saute(); a = E.Bin("&&", a, dans()) }; return a }
        fun dans(): E = comparaison()
        fun comparaison(): E {
            val a = concat()
            val ops = if (sansPlusGrand) setOf("<", "<=", "==", "!=", ">=") else setOf("<", "<=", "==", "!=", ">", ">=")
            if (j[i].t in ops) { val op = j[i++].t; return E.Bin(op, a, concat()) }
            return a
        }
        fun peutCommencer() = j[i].t in setOf("nombre", "chaine", "nom", "$", "(", "!", "++", "--")
        fun concat(): E { var a = additif(); while (peutCommencer() && j[i].t != "in") a = E.Concat(a, additif()); return a }
        fun additif(): E { var a = multiplicatif(); while (voit("+") || voit("-")) { val op = j[i++].t; a = E.Bin(op, a, multiplicatif()) }; return a }
        fun multiplicatif(): E { var a = unaire(); while (voit("*") || voit("/") || voit("%")) { val op = j[i++].t; a = E.Bin(op, a, unaire()) }; return a }
        fun unaire(): E = when {
            voit("!") -> { i++; E.Un("!", unaire()) }
            voit("-") -> { i++; E.Un("-", unaire()) }
            voit("+") -> { i++; E.Un("+", unaire()) }
            else -> postfixe()
        }
        fun postfixe(): E {
            val a = primaire()
            if ((a is E.Var || a is E.Tab || a is E.Champ) && (voit("++") || voit("--"))) return E.Inc(j[i++].t, false, a)
            return a
        }
        fun primaire(): E {
            val k = j[i]
            return when (k.t) {
                "nombre" -> { i++; E.Num(k.v.toDouble()) }
                "chaine" -> { i++; E.Ch(k.v) }
                "$" -> { i++; E.Champ(primaireChamp()) }
                "(" -> { i++; val g = sansPlusGrand; sansPlusGrand = false; val e = expr(); sansPlusGrand = g; prend(")"); e }
                "++", "--" -> { i++; E.Inc(k.t, true, primaire()) }
                "nom" -> { i++; if (voit("[")) { i++; val e = expr(); prend("]"); E.Tab(k.v, e) } else E.Var(k.v) }
                else -> throw Erreur("erreur de syntaxe près de « ${k.v} »")
            }
        }
        fun primaireChamp(): E {
            val k = j[i]
            return when (k.t) {
                "nombre" -> { i++; E.Num(k.v.toDouble()) }
                "nom" -> { i++; E.Var(k.v) }
                "(" -> { i++; val e = expr(); prend(")"); e }
                "$" -> { i++; E.Champ(primaireChamp()) }
                "-" -> { i++; E.Un("-", primaireChamp()) }
                else -> throw Erreur("erreur de syntaxe après $")
            }
        }
    }

    // ---------------------------------------------------------------- l'exécution
    private class Sortir(val code: Int) : Exception()
    private class Suivant : Exception()

    private class Machine(val fs: String?) {
        val vars = HashMap<String, V>()
        val tabs = HashMap<String, LinkedHashMap<String, V>>()
        var champs: List<String> = emptyList()
        var ligne = ""
        var nr = 0
        val out = StringBuilder()

        fun couper(l: String) {
            ligne = l
            champs = if (fs == null || fs == " ") l.trim().split(Regex("[ \t]+")).filter { it.isNotEmpty() }
            else if (fs.length == 1) l.split(fs[0]) else l.split(Regex(fs))
            if (l.isEmpty()) champs = emptyList()
        }

        fun champ(k: Int): V = when {
            k < 0 -> throw Erreur("champ négatif")
            k == 0 -> donnee(ligne)
            k <= champs.size -> donnee(champs[k - 1])
            else -> VIDE
        }

        fun lire(e: E): V = when (e) {
            is E.Var -> when (e.nom) { "NR" -> nb(nr.toDouble()); "NF" -> nb(champs.size.toDouble()); else -> vars[e.nom] ?: VIDE }
            is E.Tab -> tabs.getOrPut(e.nom) { LinkedHashMap() }.getOrPut(cle(e.k)) { VIDE }
            is E.Champ -> champ(eval(e.k).num().toInt())
            else -> eval(e)
        }

        fun cle(k: E): String { val v = eval(k); return if (v.s == null) nombre(v.n!!) else v.s }

        fun ecrire(e: E, v: V) {
            when (e) {
                is E.Var -> if (e.nom == "NR") nr = v.num().toInt() else vars[e.nom] = v
                is E.Tab -> tabs.getOrPut(e.nom) { LinkedHashMap() }[cle(e.k)] = v
                is E.Champ -> throw Erreur("changer un champ : pas dans le petit awk")
                else -> throw Erreur("affectation impossible")
            }
        }

        fun compare(op: String, a: V, b: V): Boolean {
            val r = if (a.numerique && b.numerique) a.num().compareTo(b.num()) else a.str().compareTo(b.str())
            return when (op) { "<" -> r < 0; "<=" -> r <= 0; ">" -> r > 0; ">=" -> r >= 0; "==" -> r == 0; else -> r != 0 }
        }

        fun arith(op: String, x: Double, y: Double): Double = when (op) {
            "+" -> x + y; "-" -> x - y; "*" -> x * y
            "/" -> { if (y == 0.0) throw Erreur("division par zéro"); x / y }
            "%" -> { if (y == 0.0) throw Erreur("division par zéro dans %"); x % y }
            else -> throw Erreur(op)
        }

        fun eval(e: E): V = when (e) {
            is E.Num -> nb(e.v)
            is E.Ch -> ch(e.v)
            is E.Var, is E.Tab, is E.Champ -> lire(e)
            is E.Concat -> ch(eval(e.a).str() + eval(e.b).str())
            is E.Cond -> if (eval(e.c).vrai()) eval(e.a) else eval(e.b)
            is E.Un -> when (e.op) { "!" -> nb(if (eval(e.a).vrai()) 0.0 else 1.0); "-" -> nb(-eval(e.a).num()); else -> nb(eval(e.a).num()) }
            is E.Bin -> when (e.op) {
                "&&" -> nb(if (eval(e.a).vrai() && eval(e.b).vrai()) 1.0 else 0.0)
                "||" -> nb(if (eval(e.a).vrai() || eval(e.b).vrai()) 1.0 else 0.0)
                "<", "<=", ">", ">=", "==", "!=" -> nb(if (compare(e.op, eval(e.a), eval(e.b))) 1.0 else 0.0)
                else -> nb(arith(e.op, eval(e.a).num(), eval(e.b).num()))
            }
            is E.Aff -> {
                val v = if (e.op == "=") eval(e.v).let { if (it.strnum) V(it.s, it.n, true) else it }
                else nb(arith(e.op.dropLast(1), lire(e.cible).num(), eval(e.v).num()))
                ecrire(e.cible, v); v
            }
            is E.Inc -> {
                val avant = lire(e.cible).num()
                val apres = if (e.op == "++") avant + 1 else avant - 1
                ecrire(e.cible, nb(apres)); nb(if (e.pre) apres else avant)
            }
        }

        fun faire(s: S) {
            when (s) {
                is S.Bloc -> s.l.forEach { faire(it) }
                is S.Expr -> eval(s.e)
                is S.Print -> out.append((if (s.l.isEmpty()) ligne else s.l.joinToString(" ") { eval(it).str() })).append('\n')
                is S.Si -> if (eval(s.c).vrai()) faire(s.a) else s.b?.let { faire(it) }
                is S.Tant -> { var k = 0; while (eval(s.c).vrai()) { faire(s.corps); if (++k > 100000) throw Erreur("boucle trop longue") } }
                is S.Pour -> { s.init?.let { faire(it) }; var k = 0
                    while (s.c == null || eval(s.c).vrai()) { faire(s.corps); s.incr?.let { faire(it) }; if (++k > 100000) throw Erreur("boucle trop longue") } }
                is S.PourDans -> for (k in tabs.getOrPut(s.tab) { LinkedHashMap() }.keys.toList()) { vars[s.v] = donnee(k); faire(s.corps) }
                is S.Sortie -> throw Sortir(s.e?.let { eval(it).num().toInt() } ?: 0)
                S.Suivante -> throw Suivant()
            }
        }
    }

    /** (sortie, code de sortie) du programme sur le texte d'entrée (fs : le séparateur de -F, ou null). */
    fun executer(programme: String, entree: String, fs: String?): Pair<String, Int> {
        val regles = try { Lecteur(jetons(programme)).programme() } catch (e: Erreur) { return "awk: ${e.message}\n" to 2 }
        val m = Machine(fs)
        var code = 0
        try {
            try {
                for (r in regles.filter { it.genre == "BEGIN" }) r.action?.let { m.faire(it) }
                val lignes = entree.split("\n").let { if (entree.endsWith("\n")) it.dropLast(1) else it }.let { if (entree.isEmpty()) emptyList() else it }
                for (l in lignes) {
                    m.nr++
                    m.couper(l)
                    try {
                        for (r in regles.filter { it.genre == "" }) {
                            if (r.motif == null || m.eval(r.motif).vrai()) {
                                if (r.action == null) m.out.append(l).append('\n') else m.faire(r.action)
                            }
                        }
                    } catch (s: Suivant) { }
                }
            } catch (s: Sortir) { code = s.code }
            try { for (r in regles.filter { it.genre == "END" }) r.action?.let { m.faire(it) } } catch (s: Sortir) { code = s.code }
        } catch (e: Erreur) { return m.out.toString() + "awk: ${e.message}\n" to 2 }
        return m.out.toString() to code
    }
}
