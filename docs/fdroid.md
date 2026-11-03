# Terminagotchi sur F-Droid — ce qui est prêt, ce qu'il reste à faire (par le propriétaire)

> 3 novembre 2026 (idée 72). Tout ce qui pouvait être préparé dans le dépôt l'est. **La demande elle-même doit être
> faite par toi** (il faut un compte GitLab à ton nom ; je n'en crée aucun). Rien n'est encore envoyé à F-Droid.

## En une phrase

F-Droid est un « magasin d'applis » libre pour Android : il **reconstruit lui-même l'appli à partir de notre code**,
la vérifie, puis la propose à tout le monde, gratuitement, avec les mises à jour automatiques.

## Ce qui est prêt dans le dépôt

| Fichier | Ce que c'est |
|---|---|
| `fdroid/fr.terminagotchi.yml` | la **fiche technique** que F-Droid demande (licence, adresse du code, comment construire l'appli) |
| `fastlane/metadata/android/fr-FR/` et `en-US/` | les **textes de la fiche** (nom, phrase courte, description), l'**icône** 512 px, **4 captures** du téléphone virtuel, le texte des nouveautés de la version 1 |
| `app/version.properties` | le **numéro de version F-Droid** (1, « 0.1.0 ») : fixe, pour que deux constructions donnent le même APK |
| `app/build.gradle.kts` | `gradle assembleRelease -Ppublication=fdroid` : version fixe, **pas de signature** (F-Droid signe avec sa clé), pas de bloc de dépendances chiffré par Google (F-Droid le refuse) |
| `gradle/wrapper/gradle-wrapper.properties` | dit à F-Droid quelle version de Gradle utiliser (8.9, la même que notre CI) |
| `.github/workflows/fdroid.yml` | à chaque changement : la fiche passe l'outil officiel `fdroid lint` ; le build F-Droid est fait **deux fois** (ailleurs, une minute plus tard) et les deux APK doivent être **identiques** (build reproductible) |

L'appli remplit déjà les règles de F-Droid : code libre (GPL-3.0-or-later), aucune bibliothèque extérieure, aucune
publicité, aucun traqueur, aucun service Google. Internet ne sert qu'au compte du jeu (facultatif), vers **notre**
serveur, dont le code est libre (`site/`).

## Les étapes pour toi (environ 30 minutes, puis de l'attente)

1. **Relire la fiche** : les textes de `fastlane/metadata/android/fr-FR/` (tu peux les changer librement) et les
   captures (elles mélangent pour l'instant français et anglais : voir les questions).
2. **Me dire « oui »** : je pose alors l'**étiquette** `fdroid-0.1.0` sur la version choisie (c'est le repère que
   F-Droid construit). Plus tard, chaque nouvelle version F-Droid = un numéro de plus dans `app/version.properties`
   et une nouvelle étiquette `fdroid-…` : F-Droid la voit tout seul (« UpdateCheckMode: Tags »).
3. **Créer un compte sur gitlab.com** (gratuit, à ton nom ou au nom du projet). F-Droid travaille sur GitLab, pas sur
   GitHub.
4. **Demander l'ajout**, au choix :
   - **le plus simple** : ouvrir une demande sur <https://gitlab.com/fdroid/rfp/-/issues> (« Request For Packaging »)
     avec le lien du dépôt GitHub et une phrase : « Terminagotchi, jeu éducatif libre (GPL-3.0), métadonnées prêtes
     dans `fdroid/fr.terminagotchi.yml` et `fastlane/`. » Un bénévole de F-Droid s'en occupe ;
   - **le plus rapide** : faire soi-même la « merge request » sur <https://gitlab.com/fdroid/fdroiddata> en ajoutant
     notre fichier `fdroid/fr.terminagotchi.yml` sous le nom `metadata/fr.terminagotchi.yml` (je peux te guider pas à
     pas, ou préparer le texte exact à coller).
5. **Répondre aux questions** des relecteurs de F-Droid (souvent quelques jours à quelques semaines). Je peux t'aider
   à chaque réponse.
6. Quand c'est accepté, l'appli apparaît dans F-Droid sous 1 à 3 jours.

## À savoir avant d'envoyer

- **Deux versions de l'appli ne se mélangent pas** : celle de F-Droid est signée par F-Droid, celle de GitHub par
  notre clé. On ne peut pas passer de l'une à l'autre sans désinstaller ; **la créature, elle, se garde** avec
  `sauvegarde exporter` puis `sauvegarde importer` (idée 73), ou avec le compte du jeu.
- **Notre clé de signature GitHub est publique** (`app/terminagotchi.keystore`, mot de passe dans
  `app/build.gradle.kts`) : n'importe qui peut fabriquer un APK qu'Android accepterait comme une « mise à jour » de
  l'APK GitHub. C'est pour cela que je propose que F-Droid **signe avec sa propre clé** (fiche prête ainsi) ; la
  fiche demande aussi à F-Droid de retirer ce fichier avant de construire (`scandelete`). Pour l'APK GitHub, voir la
  question 3.
- F-Droid peut signaler des « anti-fonctions » (étiquettes d'avertissement). Je n'en vois pas d'obligatoire ; au pire,
  ils pourraient demander de préciser que le compte en ligne est facultatif (c'est déjà écrit dans la description).

## Questions

| # | Question | Ma proposition |
|---|---|---|
| 1 | Les captures de la fiche : garder les 4 captures actuelles (vraies, mais français et anglais mélangés) ou en refaire 4 en français seulement (et 4 en anglais) avec le téléphone virtuel ? | **Les refaire** (un scénario « vitrine » du téléphone virtuel, une langue à la fois) avant l'envoi. |
| 2 | Le premier numéro F-Droid : « 0.1.0 » (code 1) ? | **Oui** : simple, et indépendant des numéros automatiques de GitHub. |
| 3 | La clé de signature de l'APK GitHub est publique : la remplacer par une clé secrète (gardée dans les « secrets » de GitHub) ? Attention : les téléphones qui ont l'ancienne version devront **désinstaller une fois** (la créature se garde avec `sauvegarde exporter`). | **Oui, avant la mise en ligne publique** ; pas maintenant (les essais en cours continuent avec l'ancienne). |
| 4 | Demande par « RFP » (un bénévole s'en charge, plus lent) ou « merge request » (plus rapide, un peu plus technique) ? | **Merge request**, je te prépare tout le texte. |
