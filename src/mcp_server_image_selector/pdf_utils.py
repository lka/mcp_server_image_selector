"""
PDF-Utility-Funktionen für die Bildextraktion
"""

import os
import sys
from typing import Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None


def extract_image_from_pdf(pdf_path: str) -> Optional[str]:
    """
    Extrahiert das erste Bild aus einem PDF oder erstellt ein Rendering der ersten Seite.

    Args:
        pdf_path: Pfad zur PDF-Datei

    Returns:
        Pfad zum extrahierten Bild oder None bei Fehler
    """
    from .utils import create_tmp_dir_if_needed

    if fitz is None:
        raise ImportError("PyMuPDF (fitz) ist nicht installiert. Bitte installieren: pip install PyMuPDF")

    try:
        doc = fitz.open(pdf_path)
        if len(doc) == 0:
            return None

        page = doc[0]  # Erste Seite

        # Versuche zunächst, eingebettete Bilder zu extrahieren
        image_list = page.get_images(full=True)

        output_dir = create_tmp_dir_if_needed()
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]

        if image_list:
            # Nimm das erste Bild
            xref = image_list[0][0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]

            output_path = os.path.join(output_dir, f"{base_name}_extracted.png")

            with open(output_path, "wb") as img_file:
                img_file.write(image_bytes)

            doc.close()
            return output_path
        else:
            # Kein eingebettetes Bild gefunden - rendere die Seite als Bild
            # Hohe Auflösung für bessere Qualität
            mat = fitz.Matrix(2.0, 2.0)  # 2x Zoom = 144 DPI
            pix = page.get_pixmap(matrix=mat)

            output_path = os.path.join(output_dir, f"{base_name}_rendered.png")

            pix.save(output_path)
            doc.close()
            return output_path

    except Exception as e:
        print(f"Fehler beim Extrahieren des Bildes aus PDF: {e}", file=sys.stderr)
        return None
