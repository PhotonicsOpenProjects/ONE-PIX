# ONE-PIX 3.0.0: eine neue Grundlage für die hyperspektrale Bildgebung

[English](../../RELEASE_NOTES_3.0.0.md) · [Français](release_notes.fr.md) · [Español](release_notes.es.md) · **Deutsch**

ONE-PIX 3.0.0 macht aus mehreren Desktop-Anwendungen eine hyperspektrale Kamera, die sich über den Browser steuern und durch Plugins erweitern lässt und deren Daten auch außerhalb des Projekts nutzbar sind. Aufnahme, Rekonstruktion und Analyse bleiben im Mittelpunkt, mit einer Weboberfläche, einem neu organisierten Python-Kern `onepix` und unabhängigen Plugins für Bildgebungsmethoden, Hardware und Analyse.

## Highlights

- **Weboberfläche in 4 Sprachen** (Englisch, Französisch, Spanisch, Deutsch): Aufnahme, Analyse, Daten, Plugins, Protokolle sowie Hardware- und Softwareeinstellungen, mit Dunkelmodus und interaktiven Spektrendiagrammen. Fernsteuerung eines Raspberry Pi ohne Bildschirm.
- **Plugins direkt in der Oberfläche installieren.** Bildgebungsmethoden, Spektrometer, Kameras und Analyseseiten sind pip-Pakete; ein Plugin-Manager installiert, aktualisiert und entfernt sie.
- **Analyse-Pipelines.** Verarbeitungsschritte verketten (Spektralauswahl, Glättung, Normalisierung, Spektralindizes …), auf Reflexion normalisieren anhand einer Referenzzone oder eines gespeicherten Referenz-Hyperkubus und den Verlauf der Schritte in den Metadaten behalten.
- **Sauberere Messungen.** Live-Abstimmung der Integrationszeit mit Hinweisen, dynamische Integrationszeit je Muster, Linearisierung der Graustufenantwort, Kalibrierung der Koregistrierung zwischen Projektor und Kamera und Projektorsteuerung über HDMI-CEC.
- **Wiederverwendbare FAIR-Daten.** Jede Aufnahme speichert eine Kennung, einen Autor, eine Lizenz und die Softwareversionen; Export nach HDF5, NumPy, MATLAB, ENVI und als TIFF-Stapel, als RO-Crate-Pakete mit SHA-256-Prüfsummen, für Python, MATLAB, QGIS oder Fiji.
- **Kleinere Dateien.** Gespeicherte JSON-Messungen sind 3- bis 6-mal kleiner und laden deutlich schneller, ohne Verlust.
- **Fernsteuerung.** Ein Socket.IO-Server mit Token-Authentifizierung konfiguriert und startet Messungen, für vernetzte Anwendungen und IoT.

## Unter der Haube

Über pip installiertes Paket `onepix`; Plugin-Architektur mit Erkennung über Entry Points; mehr als 190 Tests und eine CI auf drei Python-Versionen; Logging; atomares Schreiben der Konfiguration; einheitliches Installationsskript (`install.py`) und systemd-Dienst auf dem Raspberry Pi.

## Wichtige Korrekturen

Deadlock zwischen den Threads für Aufnahme, Projektion und Spektrometer; stiller Datenverlust beim Speichern bestimmter Arrays als JSON; Schreiben in eine geschlossene Datei in zwei Hardwaremodulen; Flask-Debugmodus standardmäßig aus; Socket.IO-Authentifizierung; Cross-Site-Anfragen werden abgelehnt.

## Umstieg von der vorherigen Version

1. Installieren Sie die benötigten Plugins: Das Repository enthält keine Bildgebungsmethode mehr.
2. Ersetzen Sie `core.*` in Ihren Skripten durch `onepix.*`.
3. Nutzen Sie die Weboberfläche: Die Tkinter-Anwendungen wurden entfernt.
4. Ein Programm, das die gespeicherten JSON-Dateien ohne `onepix.utils` liest, muss `ONEPIX_COMPACT_JSON=0` verwenden. Das erneute Einlesen von V2-Ergebnisdateien wurde nicht getestet.

Die Weboberfläche hat keine Anmeldung und lauscht auf allen Netzwerkschnittstellen: Verwenden Sie sie nur in einem vertrauenswürdigen Netzwerk (siehe [SECURITY.md](../../SECURITY.md)).

Alle Details: [CHANGELOG.md](../../CHANGELOG.md) (auf Englisch).
