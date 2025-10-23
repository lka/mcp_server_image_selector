#!/usr/bin/env python
"""
Beispiel-Script zum Starten der GUI im Standalone-Modus

Verwendung:
    python example_standalone.py                    # Öffnet Dateiauswahl-Dialog
    python example_standalone.py pfad/zum/bild.jpg  # Öffnet direkt das angegebene Bild
"""

import sys
import os

# Stelle sicher, dass das src-Verzeichnis im Python-Pfad ist
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_server_image_selector.server import run_standalone

if __name__ == "__main__":
    # Optional: Setze Working Directory
    # os.environ['IMAGE_SELECTOR_WORKING_DIR'] = '/pfad/zum/working/dir'

    # Bildpfad aus Kommandozeile oder None (öffnet Dialog)
    image_path = sys.argv[1] if len(sys.argv) > 1 else None

    run_standalone(image_path)
