# PDF-Unterstützung - Verwendung

Der MCP Server Image Selector unterstützt jetzt auch PDF-Dateien als Input. Das System extrahiert automatisch Bilder aus PDFs oder rendert die erste Seite als Bild.

## Funktionsweise

### Automatische Erkennung
PDFs werden automatisch anhand der Dateiendung `.pdf` erkannt.

### Bildextraktion
1. **Mit eingebettetem Bild**: Wenn ein PDF eingebettete Bilder enthält, wird das erste Bild extrahiert
2. **Ohne eingebettetes Bild**: Die erste Seite wird mit hoher Auflösung (144 DPI) als Bild gerendert

### Speicherort
Extrahierte/gerenderte Bilder werden im `tmp`-Verzeichnis relativ zur `working_dir` gespeichert:
```
working_dir/
  └── tmp/
      ├── document_extracted.png  (bei eingebettetem Bild)
      └── document_rendered.png   (bei gerenderter Seite)
```

## Verwendungsbeispiel

### Via MCP Tool

```python
# Das Tool wird mit einem PDF-Pfad aufgerufen
{
  "name": "select_image_regions",
  "arguments": {
    "image_path": "document.pdf"  # relativ zur working_dir
  }
}
```

### Programmatisch

```python
from mcp_server_image_selector.server import ImageSelectorGUI

# PDF-Pfad relativ oder absolut
pdf_path = "path/to/document.pdf"
working_dir = "path/to/working/directory"

# GUI initialisieren (extrahiert automatisch das Bild)
gui = ImageSelectorGUI(pdf_path, working_dir, create_ui=True)

# Das extrahierte Bild befindet sich jetzt in:
# working_dir/tmp/document_extracted.png oder
# working_dir/tmp/document_rendered.png
```

## Workflow

1. **PDF hochladen/angeben**: Pfad zur PDF-Datei angeben
2. **Automatische Extraktion**: System extrahiert Bild oder rendert Seite → Speicherung in `tmp/`
3. **Regionen markieren**: Wie bei normalen Bildern Bereiche auswählen
4. **Exportieren**: Ausgewählte Regionen werden exportiert

## Voraussetzungen

- PyMuPDF (fitz) >= 1.23.0 (automatisch installiert mit `pip install -e .`)

## Beispiel: Scan-Dokumente verarbeiten

```python
# Typischer Use Case: Gescanntes Dokument als PDF
# 1. PDF wird geladen
gui = ImageSelectorGUI("scan_2025.pdf", "./work", create_ui=False)

# 2. Bild ist jetzt verfügbar unter gui.image_path
print(f"Extrahiertes Bild: {gui.extracted_image_path}")
# Output: ./work/tmp/scan_2025_extracted.png

# 3. Regionen definieren und exportieren
regions = [
    {"coords": (100, 100, 500, 300), "mode": "text"},
    {"coords": (100, 400, 500, 600), "mode": "foto"}
]

from mcp_server_image_selector.server import export_regions
result = export_regions("scan_2025.pdf", regions, "./work", image_object=gui.original_image)

# Exportierte Dateien befinden sich in ./work/
```

## Fehlerbehandlung

Bei Problemen mit der PDF-Verarbeitung:
- Prüfen Sie, ob PyMuPDF installiert ist: `pip list | grep PyMuPDF`
- Stellen Sie sicher, dass die PDF-Datei gültig ist
- Überprüfen Sie die Berechtigungen für das `tmp`-Verzeichnis

## Technische Details

- **Rendering-Auflösung**: 2x Zoom (144 DPI) für hohe Qualität
- **Unterstützte PDF-Versionen**: Alle von PyMuPDF unterstützten Versionen
- **Bildformate**: Extrahierte/gerenderte Bilder sind immer PNG
- **Erste Seite**: Es wird immer nur die erste Seite des PDFs verarbeitet
