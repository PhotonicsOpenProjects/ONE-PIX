# ONE-PIX 3.0.0 : une nouvelle base pour l'imagerie hyperspectrale

[English](../../RELEASE_NOTES_3.0.0.md) · **Français** · [Español](release_notes.es.md) · [Deutsch](release_notes.de.md)

ONE-PIX 3.0.0 transforme un ensemble d'applications de bureau en une caméra hyperspectrale pilotable depuis un navigateur, extensible par des plugins, et dont les données se réutilisent hors du projet. L'acquisition, la reconstruction et l'analyse restent au centre, avec une interface web, un cœur Python `onepix` réorganisé et des plugins indépendants pour les méthodes d'imagerie, le matériel et l'analyse.

## Nouveautés majeures

- **Interface web en 4 langues** (anglais, français, espagnol, allemand) : acquisition, analyse, données, plugins, journaux et réglages matériel/logiciel, avec mode sombre et courbes de spectres interactives. Pilotage à distance d'un Raspberry Pi sans écran.
- **Plugins installés depuis l'interface.** Méthodes d'imagerie, spectromètres, caméras et pages d'analyse sont des paquets pip ; un gestionnaire de plugins les installe, les met à jour et les supprime.
- **Pipelines d'analyse.** Enchaînez des traitements (sélection spectrale, lissage, normalisation, indices spectraux…), normalisez en réflectance à partir d'une zone ou d'un hypercube de référence enregistré, et conservez l'historique des étapes dans les métadonnées.
- **Mesures plus propres.** Réglage du temps d'intégration en direct avec conseils, temps d'intégration dynamique par motif, linéarisation de la réponse en niveaux de gris, calibration de la corégistration projecteur-caméra et contrôle du projecteur par HDMI-CEC.
- **Données FAIR réutilisables.** Chaque acquisition enregistre un identifiant, un auteur, une licence et les versions des logiciels ; export en HDF5, NumPy, MATLAB, ENVI et piles TIFF, sous forme de paquets RO-Crate avec sommes de contrôle SHA-256, pour Python, MATLAB, QGIS ou Fiji.
- **Fichiers plus petits.** Les mesures JSON sont 3 à 6 fois plus petites et se chargent beaucoup plus vite, sans perte.
- **Pilotage à distance.** Un serveur Socket.IO avec authentification par jeton configure et lance des mesures, pour les applications connectées et l'IoT.

## Sous le capot

Paquet `onepix` installé par pip ; architecture à plugins découverts via leurs points d'entrée ; plus de 190 tests et une CI sur trois versions de Python ; journalisation ; écriture atomique de la configuration ; installateur unifié (`install.py`) et service systemd sur Raspberry Pi.

## Corrections à connaître

Interblocage entre threads d'acquisition, de projection et de spectromètre ; perte silencieuse de données lors de la sauvegarde de certains tableaux en JSON ; écriture dans un fichier fermé dans deux modules matériel ; mode debug de Flask désactivé par défaut ; authentification Socket.IO ; requêtes inter-sites refusées.

## Migration depuis la version précédente

1. Installez les plugins nécessaires : plus aucune méthode d'imagerie n'est incluse dans le dépôt.
2. Remplacez `core.*` par `onepix.*` dans vos scripts.
3. Utilisez l'interface web : les applications Tkinter sont supprimées.
4. Un programme qui lit les JSON sauvegardés sans `onepix.utils` doit utiliser `ONEPIX_COMPACT_JSON=0`. La relecture des fichiers de résultats V2 n'a pas été testée.

L'interface web n'a pas d'authentification et écoute sur toutes les interfaces réseau : utilisez-la sur un réseau de confiance (voir [SECURITY.md](../../SECURITY.md)).

Détails complets : [CHANGELOG.md](../../CHANGELOG.md) (en anglais).
