package fr.terminagotchi

// Généré par donnees/generer_mondes_android.py à partir de pc/tg/mondes.py — ne pas modifier à la main.

import java.io.File

/** Les mondes avancés du Terminaworld, version téléphone (le Port est dans Arbre.kt). */
object Mondes {
    private fun r(p: String) = Regex(p, RegexOption.IGNORE_CASE)

    val ORDRE = listOf("ondes", "citadelle", "crypte", "machines", "forge", "guilde", "observatoire", "donnees", "controle", "atelier", "nombres")

    fun branches(): Map<String, Branche> = linkedMapOf(
        "ondes" to Branche("ondes", "Tour des Ondes", "📡", "Agilité", "la Tour des Ondes : radio, Wi-Fi, Bluetooth, LoRa et maillage", listOf(
            Lecon("La longueur d'onde", "Sourcier", 1, listOf(
                Etape("Longueur d'onde = vitesse de la lumière ÷ fréquence. En millimètres, pour le Wi-Fi (2 400 MHz) :", "echo \$((300000 / 2400))", "125 mm = 12,5 cm. Les antennes mesurent souvent un quart ou une demie onde.", re = r("300000\\s*/\\s*2400")),
                Etape("Et LoRa, la radio des objets connectés (868 MHz) ?", "echo \$((300000 / 868))", "345 mm : une onde plus longue traverse mieux murs et collines. LoRa porte à des kilomètres !", re = r("300000\\s*/\\s*868")),
            )),
            Lecon("Le réseau maillé", "Mailleur", 1, listOf(
                Etape("Sans antenne ni internet, des radios LoRa (Meshtastic) se relaient. Lis le journal du maillage.", "cat monde/ondes/maillage.txt", "Chaque nœud relaie le message au suivant : c'est un réseau maillé.", re = r("(cat|get-content|gc|type|less|more)\\b.*maillage")),
                Etape("Combien de relais ? Compte les lignes « relayé ».", "grep -c relayé monde/ondes/maillage.txt", "3 relais pour 4 km : en montagne ou après une tempête, ça sauve des vies.", re = r("(grep|select-string).*relay")),
            ), prep = mapOf("monde/ondes/maillage.txt" to "[nœud Pixel]     message « coucou » envoyé (868 MHz, LoRa)\n[nœud Ferme]     reçu de Pixel, relayé (saut 1)\n[nœud Colline]   reçu de Ferme, relayé (saut 2)\n[nœud Village]   reçu de Colline, relayé (saut 3)\n[nœud Zoé]       message « coucou » reçu après 3 sauts, 4,2 km, sans internet !\n")),
        )),
        "citadelle" to Branche("citadelle", "Citadelle", "🛡", "Force", "la Citadelle : cybersécurité défensive, attaques simulées, boîtes à percer puis réparer", listOf(
            Lecon("Le guet", "Guetteur", 1, listOf(
                Etape("Quelqu'un essaie d'entrer dans la Citadelle ! Cherche les échecs de connexion dans le journal.", "grep Failed monde/citadelle/journal_auth.log", "« Failed password » : des mots de passe ratés, à la chaîne…", re = r("(grep|select-string|findstr).*failed")),
                Etape("Qui attaque ? Compte les essais par adresse.", "grep Failed monde/citadelle/journal_auth.log | cut -d' ' -f11 | sort | uniq -c | sort -rn", "203.0.113.7 a essayé 5 fois sur root : une attaque par force brute. On le bloquerait au pare-feu.", re = r("(uniq\\s+-c|group-object)")),
            ), prep = mapOf("monde/citadelle/journal_auth.log" to "Nov 27 09:58:12 citadelle sshd[801]: Accepted password for alice from 192.168.1.20 port 50110 ssh2\nNov 27 10:01:02 citadelle sshd[812]: Failed password for root from 203.0.113.7 port 51234 ssh2\nNov 27 10:01:04 citadelle sshd[812]: Failed password for root from 203.0.113.7 port 51236 ssh2\nNov 27 10:01:06 citadelle sshd[812]: Failed password for admin from 203.0.113.7 port 51240 ssh2\nNov 27 10:02:40 citadelle sshd[820]: Failed password for bob from 198.51.100.23 port 40022 ssh2\nNov 27 10:03:15 citadelle sshd[825]: Accepted publickey for bob from 192.168.1.31 port 50200 ssh2\nNov 27 10:04:01 citadelle sshd[830]: Failed password for root from 203.0.113.7 port 51290 ssh2\nNov 27 10:04:03 citadelle sshd[830]: Failed password for root from 203.0.113.7 port 51292 ssh2\nNov 27 10:05:59 citadelle sshd[841]: Failed password for test from 198.51.100.23 port 40100 ssh2\n")),
            Lecon("Les remparts", "Bâtisseur de remparts", 1, listOf(
                Etape("Qui peut lire le coffre ? Regarde ses droits.", "ls -l monde/citadelle/coffre.txt", "rw-r--r-- : tout le monde peut le lire. Pas terrible pour un code secret !", re = r("^(ls\\s+-l|get-acl|icacls)")),
                Etape("Ferme les remparts : toi seul peux lire et écrire.", "chmod 600 monde/citadelle/coffre.txt", "600 = rw------- : le principe du moindre privilège. Chacun n'a que ce dont il a besoin.", re = r("^(chmod\\s+0?600|icacls\\b.*/inheritance:r)")),
            ), prep = mapOf("monde/citadelle/coffre.txt" to "code du coffre : 4242\n")),
            Lecon("L'empreinte", "Vérificateur", 1, listOf(
                Etape("Prends l'empreinte du rapport (SHA-256).", "sha256sum monde/citadelle/rapport.txt", "64 caractères : l'empreinte unique de ce fichier.", re = r("(sha256sum|get-filehash|shasum).*rapport")),
                Etape("Un espion modifie le rapport…", "echo 'tout va bien, ouvrez les portes' >> monde/citadelle/rapport.txt", "Le texte a l'air innocent…", re = r("(>>|add-content).*rapport")),
                Etape("Reprends l'empreinte et compare.", "sha256sum monde/citadelle/rapport.txt", "Tout a changé ! C'est ainsi qu'on vérifie qu'un fichier téléchargé n'a pas été trafiqué.", re = r("(sha256sum|get-filehash|shasum).*rapport")),
            ), prep = mapOf("monde/citadelle/rapport.txt" to "Rapport du guet : RAS, tout est calme.\n")),
            Lecon("La boîte à percer", "Hacker éthique", 1, listOf(
                Etape("Une « boîte » d'entraînement : un faux serveur à auditer. Montre TOUS ses fichiers, même cachés.", "ls -a monde/citadelle/boite", "Un fichier caché, .config… suspect.", re = r("(ls\\s+-\\w*a|get-childitem.*-force|gci.*-force|dir\\s+/a)")),
                Etape("Cherche un mot de passe oublié dans la boîte.", "grep -r mot_de_passe monde/citadelle/boite", "Percée ! Un mot de passe en clair dans un fichier : la faille la plus courante du monde.", re = r("(grep\\s+-\\w*r|select-string).*mot_de_passe")),
                Etape("Maintenant, répare : supprime ce fichier dangereux.", "rm monde/citadelle/boite/.config", "Percer pour apprendre, réparer pour protéger : c'est le métier de hacker éthique.", fs = { !File(it.terrain, "monde/citadelle/boite/.config").exists() }),
            ), prep = mapOf("monde/citadelle/boite/accueil.txt" to "Bienvenue sur le serveur de la boulangerie.\n", "monde/citadelle/boite/.config" to "utilisateur=admin\nmot_de_passe=tournesol\n")),
        )),
        "crypte" to Branche("crypte", "Crypte des Codes", "🗝", "Intelligence", "la Crypte des Codes : cryptographie, des codes anciens à la blockchain", listOf(
            Lecon("Le code de César", "Centurion", 1, listOf(
                Etape("Jules César décalait chaque lettre de 3. Chiffre BONJOUR.", "echo BONJOUR | tr 'A-Z' 'D-ZA-C'", "ERQMRXU : illisible… sauf pour qui connaît la clé (3).", re = r("(tr\\b.*d-za-c|ord\\(c\\))")),
                Etape("Un message chiffré t'attend dans la crypte. Déchiffre-le !", "tr 'D-ZA-C' 'A-Z' < monde/crypte/message.txt", "26 clés possibles seulement : un ordinateur casse César en un clin d'œil.", re = r("(tr\\b.*a-z.*message|message.*tr\\b|ord\\(c\\).*message|message.*ord\\(c\\))")),
            ), prep = mapOf("monde/crypte/message.txt" to "WHUPLQDJRWFKL HVW XQ JHQLH\n")),
            Lecon("Le colis en base64", "Transcripteur", 1, listOf(
                Etape("Base64 transforme n'importe quoi en lettres simples. Encode un mot.", "echo -n secret | base64", "c2VjcmV0 : ce n'est PAS un chiffrement, juste un emballage.", re = r("(base64|tobase64string)")),
                Etape("Ouvre le colis de la crypte.", "base64 -d monde/crypte/colis.b64", "N'importe qui peut le déballer : base64 sert à transporter, pas à cacher.", re = r("(base64\\s+(-d|--decode)|certutil\\s+-decode).*colis")),
            ), prep = mapOf("monde/crypte/colis.b64" to "TGUgdHLDqXNvciBlc3QgY2FjaMOpIHNvdXMgbGEgUmFjaW5lLgo=\n")),
            Lecon("L'empreinte magique", "Hacheur", 1, listOf(
                Etape("a.txt et b.txt ne diffèrent que d'une lettre. Compare leurs empreintes.", "sha256sum monde/crypte/a.txt monde/crypte/b.txt", "Une lettre change, toute l'empreinte change : l'effet avalanche. Et impossible de revenir en arrière.", re = r("(sha256sum|get-filehash|shasum).*a\\.txt")),
            ), prep = mapOf("monde/crypte/a.txt" to "terminagotchi\n", "monde/crypte/b.txt" to "terminagotchI\n")),
            Lecon("La blockchain à la main", "Forgeron de chaînes", 1, listOf(
                Etape("Écris le premier bloc du registre.", "echo 'bloc 1 : Alice donne 5 pommes à Bob' > monde/crypte/bloc1.txt", "Bloc 1 posé.", fs = { File(it.terrain, "monde/crypte/bloc1.txt").exists() }),
                Etape("Le bloc 2 commence par l'empreinte du bloc 1.", "sha256sum monde/crypte/bloc1.txt > monde/crypte/bloc2.txt", "Le bloc 2 est accroché au bloc 1 par son empreinte.", fs = { File(it.terrain, "monde/crypte/bloc2.txt").exists() }),
                Etape("Ajoute la transaction du bloc 2.", "echo 'bloc 2 : Bob donne 2 pommes à Zoé' >> monde/crypte/bloc2.txt", "Si quelqu'un trafique le bloc 1, son empreinte change et ne correspond plus au bloc 2 : toute la chaîne crie au voleur. C'est ça, une blockchain !", re = r("(>>|add-content).*bloc2")),
            )),
        )),
        "machines" to Branche("machines", "Salle des Machines", "🏭", "Force", "la Salle des Machines : matériel, démarrage, système, machines virtuelles, cloud", listOf(
            Lecon("Ouvrir le capot", "Mécano", 1, listOf(
                Etape("Quel est le cerveau de la machine (processeur) ?", "cat /proc/cpuinfo", "Cœurs (cores) = les ouvriers ; fréquence (GHz) = leur vitesse.", re = r("^(lscpu|get-ciminstance|gcim|sysctl|cat\\s+/proc/cpuinfo|wmic)")),
                Etape("Et la mémoire vive (RAM) ?", "free -h", "La RAM = la table de travail (rapide, s'efface à l'arrêt) ; le disque = l'armoire.", re = r("^(free|get-ciminstance|gcim|vm_stat|cat\\s+/proc/meminfo)")),
            )),
            Lecon("Le réveil", "Réveilleur", 1, listOf(
                Etape("Depuis combien de temps la machine est-elle réveillée ?", "uptime", "Au démarrage : firmware (BIOS/UEFI) → chargeur → noyau → services.", re = r("^(uptime|\\(get-date\\)|get-uptime)")),
                Etape("Quel noyau (le cœur du système) fait tourner tout ça ?", "uname -a", "Le noyau parle au matériel ; tous les programmes passent par lui.", re = r("^(uname|\\[environment\\]|ver\\b|systeminfo)")),
            )),
        )),
        "forge" to Branche("forge", "Forge", "🔨", "Intelligence", "la Forge : programmer, son premier jeu, son site web, du son", listOf(
            Lecon("Mon premier jeu", "Créateur de jeux", 1, listOf(
                Etape("Voici le code d'un petit jeu de dé. Lis-le !", "cat monde/forge/de.sh", "\$RANDOM donne un nombre au hasard ; % 6 garde le reste de la division par 6 (0 à 5), + 1 → 1 à 6.", re = r("cat\\b.*de\\.sh")),
                Etape("Lance le dé !", "sh monde/forge/de.sh", "Tu as lancé ton premier programme de jeu.", re = r("^sh\\b.*de\\.sh")),
                Etape("Fabrique un dé à 20 faces : remplace 6 par 20.", "sed -i 's/% 6/% 20/' monde/forge/de.sh", "Relance-le : tu as modifié un jeu, comme tout programmeur qui commence.", fs = { File(it.terrain, "monde/forge/de.sh").let { f -> f.exists() && "% 20" in f.readText() } }),
            ), prep = mapOf("monde/forge/de.sh" to "echo \"Le dé roule… il tombe sur \$((RANDOM % 6 + 1)) !\"\n")),
            Lecon("Mon premier site", "Tisseur de web", 1, listOf(
                Etape("Écris une page web.", "echo '<h1>Le site de ma créature</h1>' > monde/forge/index.html", "<h1> = un grand titre. Le HTML range le texte dans des balises.", fs = { File(it.terrain, "monde/forge/index.html").exists() }),
                Etape("Regarde le code de ta page.", "cat monde/forge/index.html", "Un navigateur lit ces balises et dessine la page. Sur PC, le jeu t'apprend à l'héberger toi-même !", re = r("cat\\b.*index\\.html")),
            )),
        )),
        "guilde" to Branche("guilde", "Guilde des Bâtisseurs", "🛠", "Endurance", "la Guilde des Bâtisseurs Libres : open source, contribuer, compiler", listOf(
            Lecon("Les règles du libre", "Compagnon", 1, listOf(
                Etape("Chaque projet libre a une licence. Lis le début de celle-ci.", "head -n 3 monde/guilde/LICENSE", "MIT : une des licences les plus simples.", re = r("(head|get-content|gc|cat)\\b.*license")),
                Etape("Que permet-elle ? Cherche le mot « use ».", "grep -i use monde/guilde/LICENSE", "Utiliser, copier, modifier, partager : les 4 libertés du logiciel libre.", re = r("(grep|select-string).*use")),
            ), prep = mapOf("monde/guilde/LICENSE" to "MIT License\n\nCopyright (c) 2026 Les Bâtisseurs Libres\n\nPermission is hereby granted, free of charge, to any person obtaining a copy of this software, to deal in the\nSoftware without restriction, including the rights to use, copy, modify, merge, publish, distribute...\n")),
            Lecon("Ma première contribution", "Contributeur", 1, listOf(
                Etape("Il y a une faute dans le projet. Garde d'abord une copie de l'original.", "cp monde/guilde/projet/bonjour.txt monde/guilde/projet/bonjour.orig", "L'original est à l'abri.", fs = { File(it.terrain, "monde/guilde/projet/bonjour.orig").exists() }),
                Etape("Corrige « Bonjur » en « Bonjour ».", "sed -i 's/Bonjur/Bonjour/' monde/guilde/projet/bonjour.txt", "Corrigé !", fs = { File(it.terrain, "monde/guilde/projet/bonjour.txt").let { f -> f.exists() && "Bonjour" in f.readText() } }),
                Etape("Fabrique le patch : la recette de ta correction.", "diff -u monde/guilde/projet/bonjour.orig monde/guilde/projet/bonjour.txt", "- l'ancienne ligne, + la nouvelle : c'est ce qu'on propose à un projet (une « pull request »). Terminagotchi lui-même est libre : tu peux y contribuer !", re = r("^(diff|compare-object|fc)\\b")),
            ), prep = mapOf("monde/guilde/projet/bonjour.txt" to "Bonjur le monde !\n")),
        )),
        "observatoire" to Branche("observatoire", "Observatoire de l'IA", "🔭", "Intelligence", "l'Observatoire de l'IA : comment une IA apprend, se trompe, et comment la piloter", listOf(
            Lecon("Apprendre en comptant", "Statisticien", 1, listOf(
                Etape("Une IA apprend sur des exemples. Combien d'avis positifs ?", "grep -c positif monde/ia/avis.txt", "5 positifs.", re = r("(grep|select-string).*positif")),
                Etape("Quels mots reviennent le plus ? Compte-les tous.", "tr ' ' '\\n' < monde/ia/avis.txt | sort | uniq -c | sort -rn | head", "« j'adore » est lié aux avis positifs : un modèle apprend ces liens, sur des milliards de textes.", re = r("(uniq\\s+-c|group-object)")),
            ), prep = mapOf("monde/ia/avis.txt" to "positif : j'adore ce jeu, ma créature est trop mignonne\npositif : le terminal devient facile, j'adore apprendre\nnégatif : le défi éclair est trop rapide pour moi\npositif : les dessins sont superbes, j'adore\nnégatif : j'ai perdu mon dressage, trop dur\npositif : super jeu pour apprendre le terminal\nnégatif : ma créature a faim trop souvent\npositif : j'adore le Port et les réseaux\n")),
            Lecon("Prédire le mot suivant", "Devin", 1, listOf(
                Etape("Après « le chat », quel mot vient le plus souvent ?", "grep -o 'le chat [a-z]*' monde/ia/texte.txt | sort | uniq -c | sort -rn", "« dort » (3 fois) : un modèle de langue prédit le mot le plus probable. Il ne « sait » pas, il calcule.", re = r("le chat.*(uniq|group-object)")),
            ), prep = mapOf("monde/ia/texte.txt" to "le chat dort sur le canapé\nle chat mange sa pâtée\nle chat dort au soleil\nle chien court dans le jardin\nle chat dort encore\nle chien mange sa pâtée\nle chat joue avec la ficelle\n")),
            Lecon("Quand l'IA se trompe", "Détecteur de biais", 1, listOf(
                Etape("Les exemples d'entraînement sont-ils équilibrés ? Compte.", "sort monde/ia/biais.txt | uniq -c", "4 « docteur : il » pour 1 « elle » : une IA entraînée là-dessus croira que les docteurs sont des hommes. C'est un biais : l'IA répète les déséquilibres de ses données.", re = r("(uniq\\s+-c|group-object)")),
            ), prep = mapOf("monde/ia/biais.txt" to "docteur : il\ndocteur : il\ndocteur : il\ndocteur : il\ndocteur : elle\ninfirmier : elle\ninfirmier : elle\ninfirmier : elle\ninfirmier : il\n")),
            Lecon("Piloter un assistant", "Pilote d'IA", 1, listOf(
                Etape("Lis cette consigne bien écrite pour un assistant IA.", "cat monde/ia/consigne.txt", "Rôle, contexte, tâche, format, vérification : une bonne consigne. Et toujours vérifier ce que l'IA répond !", re = r("(cat|get-content|gc|less|more)\\b.*consigne")),
            ), prep = mapOf("monde/ia/consigne.txt" to "# Une bonne consigne pour un assistant IA\nRôle      : tu es un professeur de terminal patient, pour une élève de 10 ans.\nContexte  : elle sait déjà utiliser ls et cd, elle découvre grep.\nTâche     : explique-lui grep avec un exemple tiré de la vie de tous les jours.\nFormat    : 5 lignes maximum, puis un petit exercice.\nVérifie   : si tu n'es pas sûr d'une option, dis-le au lieu d'inventer.\n")),
        )),
        "donnees" to Branche("donnees", "Salle des Données", "📊", "Endurance", "la Salle des Données : trier, compter, chercher, les bases de données (SQL)", listOf(
            Lecon("Le tableau", "Archiviste des données", 1, listOf(
                Etape("Un fichier CSV : un tableau en texte. Regarde le début.", "head -n 5 monde/donnees/creatures.csv", "Une ligne = une créature, les virgules séparent les colonnes.", re = r("(head|get-content|gc|cat)\\b.*creatures")),
                Etape("Combien de lignes ?", "wc -l monde/donnees/creatures.csv", "15 lignes : l'en-tête + 14 créatures.", re = r("(wc\\s+-l|\\.count)")),
            ), prep = mapOf("monde/donnees/creatures.csv" to "nom,famille,rarete,taille_cm\nBraisillon,Démons,commune,45\nCornichaud,Démons,commune,90\nInfernarque,Démons,légendaire,900\nGouttelin,Élémentaires,commune,30\nTellurion,Élémentaires,légendaire,1100\nOsselet,Morts-vivants,commune,40\nLichonarque,Morts-vivants,légendaire,240\nGlandouille,Sylvestres,commune,35\nMousselin,Sylvestres,commune,120\nKrillou,Abyssaux,commune,50\nPoulpiot,Abyssaux,commune,60\nAuréolin,Célestes,rare,180\nRunodrake,Constructs,rare,420\nChaosmère,Aberrations,légendaire,1200\n")),
            Lecon("Trier et regrouper", "Trieur", 1, listOf(
                Etape("Combien de créatures par famille ? (colonne 2)", "cut -d, -f2 monde/donnees/creatures.csv | sort | uniq -c", "cut découpe une colonne, sort trie, uniq -c compte : un vrai rapport.", re = r("(cut\\b.*uniq|group-object)")),
                Etape("Les 3 plus grandes créatures (colonne 4, en nombres, à l'envers).", "sort -t, -k4 -n -r monde/donnees/creatures.csv | head -n 3", "Chaosmère, 12 m ! -t, = séparateur, -k4 = colonne 4, -n = nombres.", re = r("(sort\\b.*-k\\s*4|sort-object)")),
            )),
        )),
        "controle" to Branche("controle", "Poste de Contrôle", "🎛", "Force", "le Poste de Contrôle : administrer un système Linux de A à Z", listOf(
            Lecon("Les habitants", "Concierge", 1, listOf(
                Etape("Qui suis-je pour Android, et dans quels groupes ?", "id", "Chaque appli a son propre utilisateur (u0_a…) : c'est le bac à sable d'Android.", re = r("^id\\b")),
                Etape("Quelle version d'Android fait tourner le téléphone ?", "getprop ro.build.version.release", "getprop lit les réglages du système : modèle, version, langue…", re = r("^getprop\\b")),
            )),
            Lecon("Les services", "Régisseur", 1, listOf(
                Etape("Combien de programmes tournent ?", "ps -A | wc -l", "Des centaines : les services d'Android travaillent en permanence en arrière-plan.", re = r("^ps\\b.*\\|\\s*wc")),
                Etape("Lis les derniers messages du journal de l'appli.", "logcat -d -t 10", "Le journal raconte tout : le premier réflexe d'un développeur ou d'un admin en cas de panne.", re = r("^logcat\\b")),
            )),
        )),
        "atelier" to Branche("atelier", "Atelier", "🤖", "Agilité", "l'Atelier : Raspberry Pi, robots, électronique embarquée", listOf(
            Lecon("Allumer une LED", "Électronicien", 1, listOf(
                Etape("Sur un Raspberry Pi, une broche (GPIO) est un simple fichier ! Regarde l'état de la LED branchée sur la broche 17.", "cat monde/atelier/gpio17/value", "0 = éteinte. Sous Linux, « tout est fichier », même une broche électrique.", re = r("(cat|get-content|gc)\\b.*gpio17")),
                Etape("Allume-la : écris 1 dans le fichier.", "echo 1 > monde/atelier/gpio17/value", "💡 Allumée ! Sur un vrai Pi, le courant passe dans la LED.", fs = { File(it.terrain, "monde/atelier/gpio17/value").let { f -> f.exists() && "1" in f.readText() } }),
                Etape("Fais-la clignoter 3 fois.", "for i in 1 2 3; do echo 1 > monde/atelier/gpio17/value; sleep 1; echo 0 > monde/atelier/gpio17/value; sleep 1; done", "Une LED qui clignote : le « Bonjour le monde » de l'électronique.", re = r("(for\\b|1\\.\\.3).*gpio17")),
            ), prep = mapOf("monde/atelier/gpio17/value" to "0\n", "monde/atelier/gpio17/direction" to "out\n")),
            Lecon("Lire un capteur", "Capteur", 1, listOf(
                Etape("Lis le capteur de température.", "cat monde/atelier/capteur/temperature", "21500 = 21,5 °C en millidegrés, comme dans /sys/class/thermal sur un vrai Pi.", re = r("(cat|get-content|gc)\\b.*temperature")),
                Etape("Convertis en degrés.", "echo \$(( \$(cat monde/atelier/capteur/temperature) / 1000 ))", "Un robot fait ça en boucle : lire un capteur, calculer, agir (moteur, LED…).", re = r("/\\s*1000")),
            ), prep = mapOf("monde/atelier/capteur/temperature" to "21500\n")),
        )),
        "nombres" to Branche("nombres", "Ponts des Nombres", "🔢", "Intelligence", "les Ponts des Nombres : binaire, hexadécimal, octets, puissances", listOf(
            Lecon("Le binaire", "Binariste", 1, listOf(
                Etape("Un ordinateur ne connaît que 0 et 1. Que vaut 101010 en binaire ?", "echo \$((2#101010))", "42 ! 32 + 8 + 2 : chaque chiffre vaut le double du précédent.", re = r("(2#[01]+|toint32\\('[01]+',\\s*2\\))")),
                Etape("Et 255 en hexadécimal (base 16) ?", "printf '%x\\n' 255", "ff : les couleurs #ff0000 (rouge) des pages web, c'est de l'hexadécimal !", re = r("(%x|\\{0:x\\})")),
            )),
            Lecon("Les octets", "Peseur d'octets", 1, listOf(
                Etape("Un kilo-octet informatique, c'est 2 puissance 10 octets. Calcule 1024 × 1024.", "echo \$((1024 * 1024))", "1 048 576 octets = 1 Mio. Bit, Octet, Kilo, Méga, Giga, Téra, Péta, Exa : ×1024 à chaque marche.", re = r("1024\\s*\\*\\s*1024")),
                Etape("Les droits 644 de chmod sont un nombre en base 8. Que donne 420 (décimal) en octal ?", "printf '%o\\n' 420", "644 = rw-r--r-- : 6 = 4+2 (lire+écrire), 4 = lire. Les maths sont partout dans le terminal !", re = r("(%o|tostring\\(420,\\s*8\\))")),
            )),
        )),
    )
}
