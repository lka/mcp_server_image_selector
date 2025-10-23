# MCP Server Image Selector

Dieses Projekt stellt einen MCP-kompatiblen Server bereit, mit dem sich interaktiv Bildausschnitte aus Bildern (z.B. JPEG, PNG) und PDF-Dateien auswählen und als separate Dateien exportieren lassen.

## Übersicht

Der MCP Server Image Selector ermöglicht es, **mehrere Bilder in einer Session** zu bearbeiten und gezielt Bereiche als separate Dateien zu exportieren. Perfekt für Workflows, bei denen aus verschiedenen Dokumenten oder Scans bestimmte Bereiche extrahiert werden müssen.

## Features
- Interaktive GUI zur Auswahl von Bild- und Textregionen
- **Multi-Bild-Unterstützung**: Mehrere Bilder in einer GUI-Sitzung bearbeiten
- Unterstützung für verschiedene Bildformate (JPEG, PNG, BMP, GIF)
- **PDF-Unterstützung**: Automatische Extraktion von eingebetteten Bildern oder Rendering der ersten Seite
- **Bild-Rotation**: Bilder können um 90°, -90° oder 180° gedreht werden
- Export der ausgewählten Regionen als Bild- und/oder Textdateien
- Automatische Benennung und Ablage der Exportdateien im tmp-Verzeichnis
- Integration in MCP-Workflows

## Voraussetzungen
- Python 3.8+
- Virtuelle Umgebung empfohlen (`python -m venv venv`)
- Abhängigkeiten aus `pyproject.toml` installieren (z.B. mit `pip install -e .`)

## Starten des Servers

### MCP-Server-Modus (Default)
1. Virtuelle Umgebung aktivieren:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`

2. Server starten:
   ```bash
   # MCP-Server-Modus (default)
   python src/mcp_server_image_selector/server.py
   ```

### Standalone-Modus (nur GUI, ohne MCP)
```bash
# Ohne Bildpfad - öffnet Dateiauswahl-Dialog
python src/mcp_server_image_selector/server.py --standalone

# Mit Bildpfad
python src/mcp_server_image_selector/server.py --standalone pfad/zum/bild.jpg

# Alternative: Beispiel-Script verwenden
python example_standalone.py
```

## Benutzung

### Grundfunktionen
1. **Bild öffnen**: Der Server startet mit einem initial angegebenen Bild oder PDF
2. **Weitere Bilder hinzufügen**: Über den Button "+ Bild hinzufügen" können weitere Bilder zur Session hinzugefügt werden
   - Standardverzeichnis: `working_dir/Eingang` (falls vorhanden)
3. **Zwischen Bildern wechseln**: Klick auf ein Bild in der Bildliste wechselt zum entsprechenden Bild
4. **Regionen auswählen**:
   - Modus wählen: "Foto" oder "Text"
   - Mit der Maus einen Bereich aufziehen
   - "Auswahl speichern" klicken
5. **Bild rotieren**: Buttons zum Drehen um 90° links, 90° rechts oder 180°
6. **Export**: "Fertig & Exportieren" exportiert alle Regionen von allen Bildern

### Details
- Bei PDF-Dateien wird automatisch das erste eingebettete Bild extrahiert oder die erste Seite als Bild gerendert
- Jedes Bild kann unabhängig bearbeitet werden (eigene Regionen, Rotation)
- Die Bildliste zeigt den aktuellen Status: `▶ dateiname.jpg [3 Bereiche]`
- Alle exportierten Dateien werden im `tmp`-Verzeichnis des Working Directory abgelegt
- Dateinamen enthalten den Bildnamen, Timestamp und Region-Nummer für eindeutige Identifikation

### Beispiel-Workflow
1. MCP-Tool mit erstem Bild aufrufen: `select_image_regions("dokument1.jpg")`
2. GUI öffnet sich mit dokument1.jpg
3. Bereiche in dokument1.jpg auswählen und speichern
4. "+ Bild hinzufügen" klicken → dokument2.pdf auswählen
5. In der Bildliste zwischen den Bildern wechseln
6. Bereiche in dokument2.pdf auswählen und speichern
7. "Fertig & Exportieren" klicken
8. Alle Bereiche von beiden Dokumenten werden exportiert

**Ergebnis im tmp-Verzeichnis:**
```
dokument1_20250122_143022_region01_foto.png
dokument1_20250122_143022_region02_text.png
dokument1_20250122_143022_region02_text.txt
dokument2_20250122_143022_region01_foto.png
```

## MCP Tools

Der Server stellt folgende MCP-Tools bereit:

### `select_image_regions`
Öffnet die GUI zur interaktiven Auswahl von Bildausschnitten.

**Parameter:**
- `image_path` (string): Pfad zum Bild oder PDF (relativ zum Working Directory oder absolut)

**Funktionalität:**
- Startet mit dem angegebenen Bild
- Ermöglicht das Hinzufügen weiterer Bilder während der Session
- Exportiert alle Regionen von allen bearbeiteten Bildern
- Gibt eine Zusammenfassung der exportierten Dateien zurück

### `list_exported_regions`
Listet alle exportierten Bildausschnitte aus dem tmp-Verzeichnis auf.

### `get_working_directory`
Zeigt das aktuelle Working Directory an.

## Konfiguration
Die Datei `claude_desktop_config.json` enthält die Konfiguration für die Integration in MCP-Umgebungen.

### Umgebungsvariablen
- `IMAGE_SELECTOR_WORKING_DIR`: Optionales Working Directory (Standard: aktuelles Verzeichnis)

## Tests / CI
- Tests werden mit `pytest` ausgeführt.
- Ein GitHub Actions Workflow (`.github/workflows/ci.yml`) führt Tests bei Push/PR auf `main` aus.

Um lokal zu testen:
```powershell
venv\Scripts\activate
pip install -r requirements.txt  # optional
pip install pytest pillow
pytest -q
```

## Lizenz
MIT License
