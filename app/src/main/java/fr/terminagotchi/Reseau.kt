package fr.terminagotchi

import android.content.Context
import android.net.ConnectivityManager
import java.io.File
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.URL
import javax.net.ssl.HttpsURLConnection

/**
 * Le Port : des commandes réseau qu'Android ne fournit pas aux applis (curl, nslookup, route…),
 * écrites ici pour qu'elles se comportent comme les vraies. Elles tournent hors de l'écran (réseau).
 */
object Reseau {
    val PORTS = listOf(
        20 to "FTP (données)", 21 to "FTP (commandes)", 22 to "SSH : se connecter à une machine à distance",
        25 to "SMTP : envoyer des mails", 53 to "DNS : l'annuaire d'internet (UDP)", 67 to "DHCP : la box distribue les adresses",
        80 to "HTTP : le web en clair", 123 to "NTP : l'heure exacte", 443 to "HTTPS : le web chiffré",
        993 to "IMAPS : lire ses mails", 1883 to "MQTT : les objets connectés", 3306 to "MySQL : une base de données",
        5353 to "mDNS : trouver les appareils de la maison", 8080 to "HTTP de test",
    )

    fun ports(): String = "⚓ Les quais les plus connus (port → service) :\n" +
        PORTS.joinToString("\n") { (p, s) -> "  %5d  %s".format(p, s) } +
        "\nUne adresse IP = le port ; un numéro de port = le quai où accoste le bateau."

    fun ss(): String = "Android ne laisse pas une appli espionner les connexions des autres (c'est une sécurité).\n" +
        "Sur un PC Linux, « ss -tuln » liste les quais ouverts (LISTEN).\n\n" + ports()

    /** nslookup nom [serveur] : demande au DNS l'adresse d'un nom. */
    fun nslookup(args: List<String>): String {
        val nom = args.firstOrNull { !it.startsWith("-") } ?: return "Exemple : nslookup example.com"
        return try {
            val a = InetAddress.getAllByName(nom)
            "Nom :      $nom\n" + a.joinToString("\n") { "Adresse :  ${it.hostAddress}" } +
                "\n(le DNS voyage en UDP, port 53 : une carte postale, sans poignée de main)"
        } catch (e: Exception) {
            "** le serveur ne trouve pas $nom : NXDOMAIN (ce nom n'existe pas)"
        }
    }

    /** route : la passerelle (la box) et le chemin par défaut. */
    fun route(ctx: Context): String {
        return try {
            val cm = ctx.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
            val lp = cm.getLinkProperties(cm.activeNetwork) ?: return "Pas de réseau actif."
            val l = lp.routes.joinToString("\n") { r ->
                val dest = if (r.isDefaultRoute) "default" else r.destination.toString()
                "  %-22s via %-16s %s".format(dest, r.gateway?.hostAddress ?: "—", lp.interfaceName ?: "")
            }
            val adr = lp.linkAddresses.joinToString(", ") { it.toString() }
            "Mon adresse : $adr\nRoutes :\n$l\n« default via … » = la passerelle : la sortie vers internet, c'est ta box !"
        } catch (e: Exception) {
            "Impossible de lire les routes : ${e.message}"
        }
    }

    /** curl [-I] [-v] [-o fichier] URL : un vrai client web, en petit. */
    fun curl(args: List<String>, dossier: File): String {
        val apresO = args.indexOf("-o").takeIf { it >= 0 }?.let { it + 1 } ?: -1
        val url = args.filterIndexed { i, _ -> i != apresO }
            .firstOrNull { it.startsWith("http://") || it.startsWith("https://") || (!it.startsWith("-") && it.contains('.')) }
            ?.let { if (it.startsWith("http")) it else "http://$it" } ?: return "Exemple : curl -I https://example.com"
        val tete = "-I" in args || "--head" in args
        val bavard = args.any { it == "-v" || it == "--verbose" || it == "-vI" || it == "-Iv" }
        val sortie = args.indexOf("-o").takeIf { it >= 0 }?.let { args.getOrNull(it + 1) }
        val sb = StringBuilder()
        return try {
            val u = URL(url)
            val c = u.openConnection() as HttpURLConnection
            c.instanceFollowRedirects = false
            c.connectTimeout = 8000; c.readTimeout = 8000
            c.requestMethod = if (tete || bavard && "-I" in args) "HEAD" else "GET"
            c.setRequestProperty("User-Agent", "curl/8 (terminagotchi)")
            val port = if (u.port > 0) u.port else u.defaultPort
            if (bavard) sb.append("*   Trying ${u.host}:$port...\n")
            c.connect()
            if (bavard) {
                val ip = try { InetAddress.getByName(u.host).hostAddress } catch (e: Exception) { null }
                sb.append("* Connected to ${u.host}${ip?.let { " ($it)" } ?: ""} port $port  ← poignée de main TCP réussie\n")
            }
            if (bavard && c is HttpsURLConnection) {
                sb.append("* TLS : ${c.cipherSuite}\n")
                (c.serverCertificates.firstOrNull() as? java.security.cert.X509Certificate)?.let { cert ->
                    sb.append("* Server certificate:\n*  subject: ${cert.subjectX500Principal.name}\n" +
                        "*  expire date: ${cert.notAfter}\n*  issuer: ${cert.issuerX500Principal.name}\n" +
                        "*  SSL certificate verify ok.  ← le cadenas : le site est bien celui qu'il prétend\n")
                }
            }
            if (bavard) sb.append("> ${c.requestMethod} ${u.path.ifEmpty { "/" }} HTTP/1.1\n> Host: ${u.host}\n>\n")
            val code = c.responseCode
            val entetes = (listOf("HTTP/1.1 $code ${c.responseMessage ?: ""}") +
                c.headerFields.filterKeys { it != null }.map { (k, v) -> "$k: ${v.joinToString(", ")}" }.take(12))
            if (tete || bavard) sb.append(entetes.joinToString("\n") { (if (bavard) "< " else "") + it }).append("\n")
            if (!tete && c.requestMethod == "GET") {
                val corps = try { (if (code < 400) c.inputStream else c.errorStream)?.bufferedReader()?.use { it.readText() } ?: "" }
                    catch (e: Exception) { "" }
                if (sortie != null) {
                    File(dossier, sortie).writeText(corps)
                    sb.append("  % Total : ${corps.length} octets rangés dans $sortie\n")
                } else sb.append(corps.take(1500)).append(if (corps.length > 1500) "\n… (coupé : ajoute -o fichier.html pour tout garder)" else "")
            }
            if (url.startsWith("http://") && bavard) sb.append("\n⚠ http:// : tout passe en clair, chaque relais du trajet peut lire.")
            sb.toString().trimEnd()
        } catch (e: Exception) {
            sb.append("curl: (6) impossible de joindre ${URL(url).host} : ${e.message ?: e.javaClass.simpleName}").toString()
        }
    }
}
