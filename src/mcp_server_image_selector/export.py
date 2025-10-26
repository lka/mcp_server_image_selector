"""
Export-Funktionen für Bildausschnitte
"""

import os
import sys
from datetime import datetime
from PIL import Image

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    pytesseract = None
    TESSERACT_AVAILABLE = False


def format_export_paths(base_name: str, timestamp: str, i: int, mode: str, working_dir: str) -> dict:
    """Erzeugt die Ausgabe-Pfade für einen exportierten Bereich.

    Rückgabe: dict mit keys abhängig vom Modus ('foto' -> file, 'text' -> image_file,text_file).
    """
    if mode == "foto":
        output_file = os.path.join(working_dir, f"{base_name}_{timestamp}_region{i:02d}_foto.png")
        return {"type": "foto", "file": output_file, "region": i}
    else:
        img_file = os.path.join(working_dir, f"{base_name}_{timestamp}_region{i:02d}_text.png")
        text_file = os.path.join(working_dir, f"{base_name}_{timestamp}_region{i:02d}_text.txt")
        return {"type": "text", "image_file": img_file, "text_file": text_file, "region": i}


def export_regions(image_path: str, regions: list, working_dir: str, image_object: Image.Image = None) -> dict:
    """Exportiert die ausgewählten Bereiche

    Args:
        image_path: Pfad zum Originalbild (für Dateinamen)
        regions: Liste der zu exportierenden Bereiche
        working_dir: Ausgabeverzeichnis
        image_object: Optional - bereits geladenes/gedrehtes PIL Image Objekt.
                     Wenn None, wird das Bild von image_path geladen.
    """

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Use provided image object if available (e.g., after rotation),
    # otherwise load from file
    if image_object is not None:
        original_image = image_object
    else:
        original_image = Image.open(image_path)

    # Ermittle scale_factor (falls nötig - hier nehmen wir an, coords sind bereits original)
    # In der GUI werden die Koordinaten bereits umgerechnet

    exported_files = []

    for i, region in enumerate(regions, 1):
        coords = region["coords"]
        mode = region["mode"]

        # coords sind in Display-Koordinaten - hier müssten sie umgerechnet werden
        # Für dieses Beispiel gehen wir davon aus, dass sie bereits korrekt sind
        x1, y1, x2, y2 = coords

        # Direkt als Original-Koordinaten verwenden (GUI sollte diese liefern)
        # Hier vereinfachte Annahme - in Produktion scale_factor übergeben

        try:
            # crop using provided coordinates
            crop = original_image.crop((int(x1), int(y1), int(x2), int(y2)))

            info = format_export_paths(base_name, timestamp, i, mode, working_dir)

            if info["type"] == "foto":
                crop.save(info["file"], "PNG")
                exported_files.append(info)
            else:
                crop.save(info["image_file"], "PNG")

                # OCR mit Tesseract durchführen, falls verfügbar
                ocr_text = ""
                if TESSERACT_AVAILABLE and pytesseract:
                    try:
                        # Tesseract auf dem Crop-Bild ausführen
                        # Sprache: Deutsch + Englisch
                        ocr_text = pytesseract.image_to_string(crop, lang='deu+eng')
                        if ocr_text.strip():
                            ocr_text = ocr_text.strip()
                        else:
                            ocr_text = "[Kein Text erkannt]"
                    except Exception as e:
                        ocr_text = f"[OCR-Fehler: {str(e)}]"
                else:
                    ocr_text = "[Tesseract nicht verfügbar - bitte installieren: pip install pytesseract]"

                with open(info["text_file"], "w", encoding="utf-8") as f:
                    f.write(f"Textbereich {i}\n")
                    f.write(f"Bildquelle: {info['image_file']}\n")
                    f.write(f"Original: {image_path}\n")
                    f.write(f"\n{ocr_text}\n")
                exported_files.append(info)

        except Exception as e:
            print(f"Fehler beim Export von Region {i}: {e}", file=sys.stderr)

    return {
        "success": True,
        "exported_count": len(exported_files),
        "files": exported_files,
        "working_dir": working_dir,
    }
