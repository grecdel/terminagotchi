import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val numero = (System.getenv("GITHUB_RUN_NUMBER") ?: "1").toInt()
// versionCode toujours croissant, que l'APK vienne de main ou de la branche d'essai
// (minutes écoulées depuis l'époque Unix, moins une constante) : une mise à jour n'est jamais refusée.
val codeVersion = (System.currentTimeMillis() / 60_000L - 29_000_000L).toInt()

// Publication sur F-Droid (idée 72, docs/fdroid.md) : `gradle assembleRelease -Ppublication=fdroid`.
// Version FIXE lue dans app/version.properties (la même à chaque construction : build reproductible), aucune
// signature (F-Droid signe avec sa propre clé), rien qui dépende de l'heure ou de la machine.
val fdroid = (findProperty("publication") as String?) == "fdroid"
val versionFixe = Properties().apply {
    val f = file("version.properties")
    if (f.isFile) f.inputStream().use { load(it) }
}

android {
    namespace = "fr.terminagotchi"
    compileSdk = 34

    defaultConfig {
        applicationId = "fr.terminagotchi"
        minSdk = 26
        targetSdk = 34
        versionCode = if (fdroid) versionFixe.getProperty("versionCode").toInt() else codeVersion
        versionName = if (fdroid) versionFixe.getProperty("versionName") else "0.1.$numero"
    }

    // Clé de signature fixe : chaque nouvelle version s'installe par-dessus l'ancienne
    // sans perdre la créature.
    signingConfigs {
        create("perso") {
            storeFile = file("terminagotchi.keystore")
            storePassword = "terminagotchi"
            keyAlias = "terminagotchi"
            keyPassword = "terminagotchi"
        }
    }

    buildTypes {
        getByName("release") {
            isMinifyEnabled = false
            if (!fdroid) signingConfig = signingConfigs.getByName("perso")
        }
        getByName("debug") {
            signingConfig = signingConfigs.getByName("perso")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    // pas de bloc « dépendances » chiffré par Google dans l'APK (F-Droid le refuse ; l'appli n'a aucune dépendance)
    dependenciesInfo {
        includeInApk = false
        includeInBundle = false
    }
    lint {
        checkReleaseBuilds = false
        abortOnError = false
    }
}
