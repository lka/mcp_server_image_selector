# MCP Server Image Selector

Dieses Projekt stellt einen MCP-kompatiblen Server bereit, mit dem sich interaktiv Bildausschnitte aus Bildern (z.B. JPEG, PNG) oder PDF-Dateien auswählen und als separate Dateien exportieren lassen.

## Features
- Interaktive GUI zur Auswahl von Bild- und Textregionen
- Unterstützung für verschiedene Bildformate (JPEG, PNG)
- Export der ausgewählten Regionen als Bild- und/oder Textdateien
- Automatische Benennung und Ablage der Exportdateien
- Integration in MCP-Workflows

## Voraussetzungen
- Python 3.8+
- Virtuelle Umgebung empfohlen (`python -m venv venv`)
- Abhängigkeiten aus `pyproject.toml` installieren (z.B. mit `pip install -e .`)

## Starten des Servers
1. Virtuelle Umgebung aktivieren:
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
2. Server starten:
   ```
   python src/mcp_server_image_selector/server.py
   ```

## Benutzung
- Nach dem Start kann über die GUI ein Bild geöffnet werden.
- Mit der Maus können Regionen markiert und als Foto oder Text exportiert werden.
- Exportierte Dateien werden im aktuellen Arbeitsverzeichnis abgelegt.

## Konfiguration
Die Datei `claude_desktop_config.json` enthält die Konfiguration für die Integration in MCP-Umgebungen.

## Lizenz
MIT License
