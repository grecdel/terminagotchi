plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val numero = (System.getenv("GITHUB_RUN_NUMBER") ?: "1").toInt()
// versionCode toujours croissant, que l'APK vienne de main ou de la branche d'essai
// (minutes écoulées depuis l'époque Unix, moins une constante) : une mise à jour n'est jamais refusée.
val codeVersion = (System.currentTimeMillis() / 60_000L - 29_000_000L).toInt()

android {
    namespace = "fr.terminagotchi"
    compileSdk = 34

    defaultConfig {
        applicationId = "fr.terminagotchi"
        minSdk = 26
        targetSdk = 34
        versionCode = codeVersion
        versionName = "0.1.$numero"
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
            signingConfig = signingConfigs.getByName("perso")
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
    lint {
        checkReleaseBuilds = false
        abortOnError = false
    }
}
